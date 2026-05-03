"""Business logic for trading signals.

Keeping persistence + side-effects (broadcasting on the WS bus) together here
means routes stay thin and orchestration is testable in isolation.
"""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import TradingSignal
from app.schemas.signal import TradingSignalCreate, TradingSignalRead
from app.utils.websocket_manager import manager


async def list_signals(
    db: AsyncSession,
    *,
    asset: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TradingSignal]:
    stmt = select(TradingSignal).order_by(desc(TradingSignal.timestamp))
    if asset:
        stmt = stmt.where(TradingSignal.asset == asset)
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_signal(db: AsyncSession, signal_id: UUID) -> TradingSignal | None:
    return await db.get(TradingSignal, signal_id)


async def create_signal(
    db: AsyncSession, payload: TradingSignalCreate
) -> TradingSignal:
    signal = TradingSignal(
        asset=payload.asset,
        direction=payload.direction,
        confidence=payload.confidence,
        uncertainty=payload.uncertainty,
        gti=payload.gti,
        explanation=payload.explanation,
        # Pydantic models -> plain dicts for JSONB storage.
        correlated_assets=[c.model_dump() for c in payload.correlated_assets],
    )
    db.add(signal)
    await db.commit()
    await db.refresh(signal)

    # Push to every connected WS client.
    await manager.broadcast(
        {"event": "signal.created", "data": TradingSignalRead.model_validate(signal).model_dump()}
    )

    return signal
