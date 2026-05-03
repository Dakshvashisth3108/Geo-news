"""Email notifications via stdlib smtplib.

Why stdlib instead of an async client like aiosmtplib?
  * Zero extra dependencies — works in the MVP without changes.
  * SMTP send is rare (only on alert fire) so blocking-in-thread is fine.

We build the message synchronously and dispatch the actual SMTP call
through `asyncio.to_thread` so the event loop stays responsive.
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.models.alert import AlertRule
from app.models.signal import TradingSignal

logger = logging.getLogger(__name__)


def _format_body(rule: AlertRule, signal: TradingSignal) -> str:
    return (
        f"Alert fired: {rule.name}\n"
        f"\n"
        f"Triggered by signal {signal.id}\n"
        f"  asset       : {signal.asset}\n"
        f"  direction   : {signal.direction.value}\n"
        f"  confidence  : {signal.confidence:.3f}\n"
        f"  uncertainty : {signal.uncertainty:.3f}\n"
        f"  GTI         : {signal.gti:.2f}\n"
        f"  timestamp   : {signal.timestamp.isoformat()}\n"
        f"\n"
        f"Explanation:\n"
        f"{signal.explanation}\n"
    )


def _build_message(target: str, rule: AlertRule, signal: TradingSignal) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"[GeoIntel] Alert fired: {rule.name}"
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER or "alerts@geointel.local"
    msg["To"] = target
    msg.set_content(_format_body(rule, signal))
    return msg


def _send_sync(msg: EmailMessage) -> None:
    """Blocking SMTP. Wrapped in asyncio.to_thread by the async caller."""
    if not settings.SMTP_HOST:
        # Dev / unconfigured environments: log instead of failing so callers
        # can still test the rest of the pipeline.
        logger.warning(
            "SMTP_HOST not configured — email to %s would have been sent.\n%s",
            msg["To"], msg.get_content(),
        )
        return

    smtp_cls = smtplib.SMTP_SSL if settings.SMTP_PORT == 465 else smtplib.SMTP
    with smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS and smtp_cls is smtplib.SMTP:
            smtp.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


async def send_email(target: str, *, rule: AlertRule, signal: TradingSignal) -> None:
    msg = _build_message(target, rule, signal)
    await asyncio.to_thread(_send_sync, msg)
    logger.info("Email alert delivered to %s for rule %s", target, rule.id)
