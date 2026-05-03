"""Trading signal endpoints."""

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
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Most-recent-first list of trading signals."""
    return await signal_service.list_signals(
        db, asset=asset, limit=limit, offset=offset
    )


@router.get("/{signal_id}", response_model=TradingSignalRead)
async def get_signal(signal_id: UUID, db: AsyncSession = Depends(get_db)):
    signal = await signal_service.get_signal(db, signal_id)
    if signal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found")
    return signal


@router.post("", response_model=TradingSignalRead, status_code=status.HTTP_201_CREATED)
async def create_signal(
    payload: TradingSignalCreate,
    db: AsyncSession = Depends(get_db),
):
    """Publish a new signal. Also broadcasts to WS subscribers."""
    return await signal_service.create_signal(db, payload)
