"""Business logic for trading signals.

Routes stay thin; the service orchestrates persistence, the realtime
WebSocket fan-out, and (asynchronously) alert-rule evaluation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import TradingSignal
from app.repositories.signal_repository import SignalRepository
from app.schemas.signal import TradingSignalCreate, TradingSignalRead
from app.utils.websocket_manager import manager

logger = logging.getLogger(__name__)


async def list_signals(
    db: AsyncSession,
    *,
    asset: str | None = None,
    event_id: UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    min_confidence: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TradingSignal]:
    repo = SignalRepository(db)
    return await repo.list(
        asset=asset,
        event_id=event_id,
        since=since,
        until=until,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )


async def get_signal(db: AsyncSession, signal_id: UUID) -> TradingSignal | None:
    return await SignalRepository(db).get(signal_id)


async def create_signal(
    db: AsyncSession, payload: TradingSignalCreate,
) -> TradingSignal:
    """Persist a signal, broadcast over WS, and trigger alert evaluation.

    Alert evaluation runs as a fire-and-forget asyncio task on a fresh
    session so it never blocks the HTTP response and can't be tied to
    the request session's lifecycle. Errors are logged inside the task.
    """
    signal = await SignalRepository(db).create(payload)

    # Realtime broadcast
    await manager.broadcast(
        {
            "event": "signal.created",
            "data": TradingSignalRead.model_validate(signal).model_dump(mode="json"),
        }
    )

    # Background alert evaluation. We pass only the id; the task opens
    # its own session and re-fetches the row to avoid using a session
    # that may already be closed by the time we get scheduled.
    asyncio.create_task(
        _evaluate_alerts_for_signal(signal.id),
        name=f"alert-eval:{signal.id}",
    )

    return signal


async def _evaluate_alerts_for_signal(signal_id: UUID) -> None:
    """Open a fresh session, re-load the signal, evaluate alert rules.

    Imported lazily so the module-level imports of this file stay tight
    and to dodge a potential cycle with alert_service.
    """
    from app.core.database import AsyncSessionLocal
    from app.services import alert_service

    try:
        async with AsyncSessionLocal() as db:
            signal = await SignalRepository(db).get(signal_id)
            if signal is None:
                logger.warning("Signal %s vanished before alert eval", signal_id)
                return
            await alert_service.evaluate_signal(db, signal)
    except Exception:  # noqa: BLE001
        # Notification failures are already logged inside the dispatcher,
        # but a top-level catch protects the event loop from a stray.
        logger.exception("Alert evaluation task failed for signal %s", signal_id)
