"""Alert rule endpoints — compound conditions + multi-channel notifications."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.alert import AlertRule
from app.models.signal import SignalDirection, TradingSignal
from app.schemas.alert import (
    AlertRuleCreate,
    AlertRuleRead,
    AlertRuleUpdate,
    AlertTestResult,
    NotificationChannel,
)
from app.services import alert_service

router = APIRouter()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AlertRuleRead])
async def list_alerts(
    user_id: UUID = Query(..., description="Owner of the rules"),
    is_active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List alert rules for a given user. Auth comes later."""
    stmt = select(AlertRule).where(AlertRule.user_id == user_id)
    if is_active is not None:
        stmt = stmt.where(AlertRule.is_active.is_(is_active))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{rule_id}", response_model=AlertRuleRead)
async def get_alert(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found",
        )
    return rule


@router.post("", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    user_id: UUID,
    payload: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a compound alert rule, e.g. `gti > 70 AND confidence > 0.8`."""
    rule = AlertRule(
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        asset=payload.asset,
        conditions=[c.model_dump() for c in payload.conditions],
        combinator=payload.combinator,
        channels=[ch.model_dump() for ch in payload.channels],
        cooldown_seconds=payload.cooldown_seconds,
        is_active=payload.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=AlertRuleRead)
async def update_alert(
    rule_id: UUID,
    payload: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found",
        )

    # Only persist fields the caller actually sent.
    data = payload.model_dump(exclude_unset=True)

    # Pydantic models in lists need to be dumped to plain dicts for JSONB.
    if "conditions" in data and payload.conditions is not None:
        data["conditions"] = [c.model_dump() for c in payload.conditions]
    if "channels" in data and payload.channels is not None:
        data["channels"] = [ch.model_dump() for ch in payload.channels]

    for field, value in data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found",
        )
    await db.delete(rule)
    await db.commit()


# ---------------------------------------------------------------------------
# Manual test fire — verifies the user's email/webhook setup end-to-end.
# ---------------------------------------------------------------------------

@router.post(
    "/{rule_id}/test",
    response_model=AlertTestResult,
    status_code=status.HTTP_200_OK,
)
async def test_alert(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    """Force-fire a rule with a synthetic signal so the user can verify
    that every notification channel is reachable. Skips condition + cooldown
    checks; does NOT update bookkeeping."""
    rule = await db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found",
        )

    fake_signal = _synthetic_test_signal(rule)
    delivered = await alert_service.dispatch_test(rule, fake_signal)

    # Echo back the parsed channels so the UI can render delivery status.
    channels = [
        NotificationChannel(**ch) for ch in (rule.channels or []) if isinstance(ch, dict)
    ]
    return AlertTestResult(
        rule_id=rule.id,
        channels_attempted=delivered,
        channels=channels,
    )


def _synthetic_test_signal(rule: AlertRule) -> TradingSignal:
    """Build an in-memory TradingSignal that satisfies any reasonable rule
    so the test fires regardless of the rule's threshold settings."""
    return TradingSignal(
        id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        asset=rule.asset or "TEST",
        direction=SignalDirection.LONG,
        confidence=0.95,
        uncertainty=0.05,
        gti=85.0,
        explanation=f"This is a TEST notification for rule '{rule.name}'. "
                    f"Conditions and cooldown were intentionally bypassed.",
        correlated_assets=[],
    )
