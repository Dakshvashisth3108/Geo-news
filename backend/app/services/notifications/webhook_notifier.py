"""Webhook notifications.

POSTs a stable JSON payload to the configured target URL using the
async httpx client (already a top-level dep). Non-2xx responses are
logged but do not raise — the alert pipeline keeps moving.
"""

import logging

import httpx

from app.models.alert import AlertRule
from app.models.signal import TradingSignal

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10.0


def _build_payload(rule: AlertRule, signal: TradingSignal) -> dict:
    """Stable schema for downstream consumers (Slack, Zapier, n8n, ...).

    Keep this shape backwards-compatible — bumping it forces every user's
    receiving endpoint to update.
    """
    return {
        "event": "alert.fired",
        "rule": {
            "id": str(rule.id),
            "name": rule.name,
            "user_id": str(rule.user_id),
            "combinator": rule.combinator.value,
            "conditions": rule.conditions,
            "asset": rule.asset,
        },
        "signal": {
            "id": str(signal.id),
            "asset": signal.asset,
            "direction": signal.direction.value,
            "confidence": signal.confidence,
            "uncertainty": signal.uncertainty,
            "gti": signal.gti,
            "explanation": signal.explanation,
            "timestamp": signal.timestamp.isoformat(),
            "correlated_assets": signal.correlated_assets,
            "event_id": str(signal.event_id) if signal.event_id else None,
        },
    }


async def send_webhook(target: str, *, rule: AlertRule, signal: TradingSignal) -> None:
    payload = _build_payload(rule, signal)

    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        response = await client.post(
            target,
            json=payload,
            headers={"User-Agent": "GeoIntel-Webhook/1.0"},
        )

    if response.status_code >= 400:
        # Log + swallow; we explicitly don't retry here. Retries belong
        # behind a real queue (Celery / SQS / etc.) — see app/tasks/.
        logger.warning(
            "Webhook %s for rule %s returned %d: %s",
            target, rule.id, response.status_code, response.text[:200],
        )
        return

    logger.info("Webhook delivered to %s for rule %s (HTTP %d)", target, rule.id, response.status_code)
