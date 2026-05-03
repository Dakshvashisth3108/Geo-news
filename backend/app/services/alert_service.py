"""Alert rule evaluation + dispatch.

Two entry points:

  * `evaluate_signal(db, signal)` — load every active rule, fire matches,
    respect cooldowns, update bookkeeping, dispatch notifications.
    Called fire-and-forget from `signal_service.create_signal` so signal
    creation latency stays unaffected.

  * `dispatch_test(rule, signal)` — used by `POST /alerts/{id}/test` to
    deliver a synthetic notification end-to-end (skips condition + cooldown
    checks). Lets users verify their email/webhook setup without waiting
    for a real signal.

Pure-function evaluation
------------------------
`evaluate_rule(rule, signal)` is deliberately side-effect free so the
unit-tests can exercise it without spinning up DB / SMTP / httpx.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertCombinator, AlertOperator, AlertRule
from app.models.signal import TradingSignal
from app.services.notifications import dispatch_notification

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure evaluation
# ---------------------------------------------------------------------------

# Allowed metric names map to attribute getters on a TradingSignal.
# Add new metrics here (e.g. "magnitude") + extend the schema's Literal.
_METRIC_GETTERS = {
    "gti":         lambda s: s.gti,
    "confidence":  lambda s: s.confidence,
    "uncertainty": lambda s: s.uncertainty,
}

# Operator → comparator. Keeping this a flat dict makes it trivial to
# add new ops (NEQ, BETWEEN, ...) without touching the evaluator body.
_OPERATORS = {
    AlertOperator.GT.value:  lambda a, b: a > b,
    AlertOperator.GTE.value: lambda a, b: a >= b,
    AlertOperator.LT.value:  lambda a, b: a < b,
    AlertOperator.LTE.value: lambda a, b: a <= b,
    AlertOperator.EQ.value:  lambda a, b: a == b,
}


def _evaluate_condition(cond: dict, signal: TradingSignal) -> bool:
    """Return True if the condition holds against the signal."""
    metric = str(cond.get("metric", "")).lower()
    op_raw = str(cond.get("operator", "")).upper()

    getter = _METRIC_GETTERS.get(metric)
    comparator = _OPERATORS.get(op_raw)
    if getter is None or comparator is None:
        logger.warning(
            "Skipping malformed alert condition (metric=%r, operator=%r)",
            metric, op_raw,
        )
        return False

    try:
        threshold = float(cond.get("threshold", 0.0))
    except (TypeError, ValueError):
        logger.warning("Non-numeric threshold in alert condition: %r", cond)
        return False

    return bool(comparator(getter(signal), threshold))


def _matches_asset_filter(rule: AlertRule, signal: TradingSignal) -> bool:
    """Asset filter — `null` or `"*"` matches every signal."""
    if not rule.asset or rule.asset == "*":
        return True
    return rule.asset.upper() == signal.asset.upper()


def evaluate_rule(rule: AlertRule, signal: TradingSignal) -> bool:
    """Pure evaluation of a single rule against a single signal.

    Does NOT consider cooldown (that's a separate concern handled at fire
    time). Does NOT mutate the rule.
    """
    if not rule.is_active:
        return False
    if not _matches_asset_filter(rule, signal):
        return False

    conditions: list[dict] = list(rule.conditions or [])
    if not conditions:
        return False  # safety: a rule with no conditions never fires

    results = [_evaluate_condition(c, signal) for c in conditions]
    if rule.combinator == AlertCombinator.OR:
        return any(results)
    return all(results)


def _is_in_cooldown(rule: AlertRule, now: datetime) -> bool:
    """True if the rule fired recently enough that we should suppress it."""
    if rule.cooldown_seconds <= 0 or rule.last_triggered_at is None:
        return False
    last = rule.last_triggered_at
    # SQLAlchemy returns timezone-aware datetimes for `DateTime(timezone=True)`,
    # but keep this defensive in case a naive value sneaks in.
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last) < timedelta(seconds=rule.cooldown_seconds)


# ---------------------------------------------------------------------------
# Fan-out
# ---------------------------------------------------------------------------

async def evaluate_signal(
    db: AsyncSession,
    signal: TradingSignal,
) -> list[AlertRule]:
    """Evaluate all active rules against `signal`. Fire matches.

    Returns the rules that actually fired (post-cooldown). Notification
    failures are logged inside the dispatcher and do NOT prevent later
    rules from firing.
    """
    stmt = select(AlertRule).where(AlertRule.is_active.is_(True))
    result = await db.execute(stmt)
    rules: list[AlertRule] = list(result.scalars().all())

    now = datetime.now(timezone.utc)
    fired: list[AlertRule] = []

    for rule in rules:
        try:
            if not evaluate_rule(rule, signal):
                continue
            if _is_in_cooldown(rule, now):
                logger.debug(
                    "Rule %s matched but is cooling down (cooldown=%ds)",
                    rule.id, rule.cooldown_seconds,
                )
                continue

            # Bookkeeping first so even mid-fire failures still record
            # the trigger (avoids tight loops on a flapping rule).
            rule.last_triggered_at = now
            rule.trigger_count = (rule.trigger_count or 0) + 1
            fired.append(rule)

            await _fan_out(rule, signal)
        except Exception:
            # One bad rule must never prevent siblings from firing.
            logger.exception("Error while evaluating rule %s", rule.id)

    if fired:
        await db.commit()

    return fired


async def _fan_out(rule: AlertRule, signal: TradingSignal) -> int:
    """Dispatch every channel attached to a fired rule."""
    delivered = 0
    for ch in rule.channels or []:
        ok = await dispatch_notification(ch, rule=rule, signal=signal)
        if ok:
            delivered += 1
    logger.info(
        "Alert fired: rule=%s signal=%s channels=%d/%d",
        rule.id, signal.id, delivered, len(rule.channels or []),
    )
    return delivered


async def dispatch_test(rule: AlertRule, signal: TradingSignal) -> int:
    """Force-deliver to every channel without checking conditions / cooldown.

    Used by POST /alerts/{rule_id}/test to verify channel configuration.
    """
    return await _fan_out(rule, signal)


# ---------------------------------------------------------------------------
# Optional: re-evaluate recent signals (used by the scheduler placeholder)
# ---------------------------------------------------------------------------

async def evaluate_recent_signals(
    db: AsyncSession,
    *,
    since: datetime,
    rule_ids: Iterable[str] | None = None,
) -> int:
    """Sweep signals created since `since` and re-fire matching rules.

    Useful when a brand-new rule should retroactively notify the user
    about something that happened in the last few minutes. Wire this into
    the scheduler in app/tasks/scheduler.py to run periodically.

    Returns the total number of (rule, signal) fires.
    """
    sig_stmt = select(TradingSignal).where(TradingSignal.timestamp >= since)
    sig_result = await db.execute(sig_stmt)
    signals: list[TradingSignal] = list(sig_result.scalars().all())

    total = 0
    for signal in signals:
        fired = await evaluate_signal(db, signal)
        if rule_ids is not None:
            fired = [r for r in fired if str(r.id) in set(rule_ids)]
        total += len(fired)
    return total
