"""Trading signal endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.signal import TradingSignalCreate, TradingSignalRead
from app.services import signal_service

router = APIRouter()


@router.get("", response_model=list[TradingSignalRead])
async def list_signals(
    asset: str | None = Query(default=None, description="Filter by ticker"),
    event_id: UUID | None = Query(default=None, description="Filter by event"),
    since: datetime | None = Query(default=None, description="ISO8601 lower bound"),
    until: datetime | None = Query(default=None, description="ISO8601 upper bound"),
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Most-recent-first list of trading signals with common filters."""
    return await signal_service.list_signals(
        db,
        asset=asset,
        event_id=event_id,
        since=since,
        until=until,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )


@router.get("/{signal_id}", response_model=TradingSignalRead)
async def get_signal(signal_id: UUID, db: AsyncSession = Depends(get_db)):
    signal = await signal_service.get_signal(db, signal_id)
    if signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found"
        )
    return signal


@router.post("", response_model=TradingSignalRead, status_code=status.HTTP_201_CREATED)
async def create_signal(
    payload: TradingSignalCreate,
    db: AsyncSession = Depends(get_db),
):
    """Publish a new signal. Also broadcasts to WS subscribers."""
    return await signal_service.create_signal(db, payload)
