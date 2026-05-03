"""Business logic for trading signals.

Routes stay thin; the service orchestrates persistence (via SignalRepository)
and the realtime fan-out (via the WebSocket manager). This separation lets us
unit-test orchestration without spinning up HTTP/WebSocket plumbing.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import TradingSignal
from app.repositories.signal_repository import SignalRepository
from app.schemas.signal import TradingSignalCreate, TradingSignalRead
from app.utils.websocket_manager import manager


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
    db: AsyncSession, payload: TradingSignalCreate
) -> TradingSignal:
    """Persist a signal and broadcast it to every connected WS client."""
    signal = await SignalRepository(db).create(payload)

    await manager.broadcast(
        {
            "event": "signal.created",
            "data": TradingSignalRead.model_validate(signal).model_dump(mode="json"),
        }
    )
    return signal
