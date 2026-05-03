"""Notification fan-out for fired alerts.

A single `dispatch_notification` entrypoint hides the channel-specific
transports. Each transport never raises — failures are logged so a
flaky webhook can't take the alert pipeline (or signal creation) down.
"""

import logging
from typing import Any

from app.models.alert import AlertRule
from app.models.signal import TradingSignal

from .email_notifier import send_email
from .webhook_notifier import send_webhook

logger = logging.getLogger(__name__)


async def dispatch_notification(
    channel: dict[str, Any],
    *,
    rule: AlertRule,
    signal: TradingSignal,
) -> bool:
    """Deliver one notification. Returns True if the transport call succeeded.

    `channel` must look like {"type": "email"|"webhook", "target": "..."}
    (validated upstream by NotificationChannel — but we re-check here so
    a malformed JSONB row doesn't crash dispatch).
    """
    ctype = (channel.get("type") or "").lower()
    target = channel.get("target") or ""
    if not ctype or not target:
        logger.warning("Dropping malformed notification channel: %r", channel)
        return False

    try:
        if ctype == "email":
            await send_email(target, rule=rule, signal=signal)
        elif ctype == "webhook":
            await send_webhook(target, rule=rule, signal=signal)
        else:
            logger.warning("Unknown notification channel type %r; dropping", ctype)
            return False
    except Exception as exc:
        logger.exception(
            "Notification dispatch failed (rule=%s, channel=%s): %s",
            rule.id, ctype, exc,
        )
        return False

    return True


__all__ = ["dispatch_notification", "send_email", "send_webhook"]
