"""CRUD repository for TradingSignal.

The composite primary key `(id, timestamp)` (required for TimescaleDB
hypertables) means lookups by id alone need an explicit `where` clause —
`session.get` won't work without the timestamp. This module hides that
detail from callers.
"""

from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import delete as sa_delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import TradingSignal
from app.schemas.signal import TradingSignalCreate


class SignalRepository:
    """Async CRUD over the `trading_signals` table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------ create
    async def create(self, payload: TradingSignalCreate) -> TradingSignal:
        signal = TradingSignal(
            asset=payload.asset,
            direction=payload.direction,
            confidence=payload.confidence,
            uncertainty=payload.uncertainty,
            gti=payload.gti,
            explanation=payload.explanation,
            event_id=payload.event_id,
            # Pydantic models -> dicts for JSONB storage.
            correlated_assets=[c.model_dump() for c in payload.correlated_assets],
        )
        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)
        return signal

    async def bulk_create(
        self, payloads: Sequence[TradingSignalCreate]
    ) -> list[TradingSignal]:
        """Insert many signals in one transaction (ingestion pipeline path)."""
        signals = [
            TradingSignal(
                asset=p.asset,
                direction=p.direction,
                confidence=p.confidence,
                uncertainty=p.uncertainty,
                gti=p.gti,
                explanation=p.explanation,
                event_id=p.event_id,
                correlated_assets=[c.model_dump() for c in p.correlated_assets],
            )
            for p in payloads
        ]
        self.db.add_all(signals)
        await self.db.commit()
        for s in signals:
            await self.db.refresh(s)
        return signals

    # --------------------------------------------------------------------- read
    async def get(self, signal_id: UUID) -> TradingSignal | None:
        """Fetch a single signal by id (no timestamp needed at the API surface)."""
        stmt = select(TradingSignal).where(TradingSignal.id == signal_id).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        asset: str | None = None,
        event_id: UUID | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        min_confidence: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TradingSignal]:
        """Most-recent-first list with common filters."""
        stmt = select(TradingSignal).order_by(desc(TradingSignal.timestamp))

        if asset is not None:
            stmt = stmt.where(TradingSignal.asset == asset)
        if event_id is not None:
            stmt = stmt.where(TradingSignal.event_id == event_id)
        if since is not None:
            stmt = stmt.where(TradingSignal.timestamp >= since)
        if until is not None:
            stmt = stmt.where(TradingSignal.timestamp <= until)
        if min_confidence is not None:
            stmt = stmt.where(TradingSignal.confidence >= min_confidence)

        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def latest_for_asset(self, asset: str) -> TradingSignal | None:
        """Most recent signal for a given asset, if any."""
        stmt = (
            select(TradingSignal)
            .where(TradingSignal.asset == asset)
            .order_by(desc(TradingSignal.timestamp))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self, *, asset: str | None = None) -> int:
        stmt = select(func.count()).select_from(TradingSignal)
        if asset is not None:
            stmt = stmt.where(TradingSignal.asset == asset)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    # ------------------------------------------------------------------ delete
    async def delete(self, signal_id: UUID) -> bool:
        """Delete by id. Returns True if a row was removed."""
        stmt = sa_delete(TradingSignal).where(TradingSignal.id == signal_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return (result.rowcount or 0) > 0
