"""Trading signal endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.event import GeopoliticalEvent
from app.schemas.correlation import AnalyzeCorrelationRequest, CorrelationAnalysis
from app.schemas.signal import TradingSignalCreate, TradingSignalRead
from app.services import correlation_service, signal_service

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


@router.post("", response_model=TradingSignalRead, status_code=status.HTTP_201_CREATED)
async def create_signal(
    payload: TradingSignalCreate,
    db: AsyncSession = Depends(get_db),
):
    """Publish a new signal. Also broadcasts to WS subscribers."""
    return await signal_service.create_signal(db, payload)


@router.post(
    "/analyze-correlation",
    response_model=CorrelationAnalysis,
    status_code=status.HTTP_200_OK,
)
async def analyze_correlation(
    payload: AnalyzeCorrelationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run the multi-asset correlation engine on a geopolitical event.

    Accepts either:
      * `event_id` — analyse a persisted event by id, or
      * `event`    — pass an inline GeopoliticalEventCreate payload (no
        DB write required, useful for "what if?" preview from the UI).

    Returns the basket of correlated assets plus a draft signal. If
    `persist=True`, also creates a `TradingSignal` from the result and
    broadcasts it on the WebSocket stream.
    """
    # Resolve the event the engine analyses.
    if payload.event_id is not None:
        event = await db.get(GeopoliticalEvent, payload.event_id)
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
            )
        outcome = correlation_service.analyze_event(
            event=event,
            primary_asset_override=payload.primary_asset,
        )
        event_id_for_signal: UUID | None = event.id
    else:
        # Caller validation guarantees `payload.event` is set here.
        ev = payload.event
        assert ev is not None
        outcome = correlation_service.analyze_event(
            event_type=ev.event_type,
            severity=ev.severity,
            countries=ev.countries,
            region=ev.region,
            summary=ev.title or ev.summary,
            primary_asset_override=payload.primary_asset,
        )
        event_id_for_signal = None

    signal_id: UUID | None = None
    if payload.persist:
        sig_payload = TradingSignalCreate(
            asset=outcome.primary_asset,
            direction=outcome.direction,
            confidence=outcome.confidence,
            uncertainty=outcome.uncertainty,
            gti=outcome.gti,
            explanation=outcome.reasoning,
            correlated_assets=outcome.correlated_assets,
            event_id=event_id_for_signal,
        )
        signal = await signal_service.create_signal(db, sig_payload)
        signal_id = signal.id

    return CorrelationAnalysis(
        primary_asset=outcome.primary_asset,
        direction=outcome.direction,
        confidence=outcome.confidence,
        uncertainty=outcome.uncertainty,
        gti=outcome.gti,
        correlated_assets=outcome.correlated_assets,
        reasoning=outcome.reasoning,
        signal_id=signal_id,
    )


@router.get("/{signal_id}", response_model=TradingSignalRead)
async def get_signal(signal_id: UUID, db: AsyncSession = Depends(get_db)):
    signal = await signal_service.get_signal(db, signal_id)
    if signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found"
        )
    return signal
