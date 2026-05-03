"""Geopolitical event endpoints — ingestion + read."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.event import EventSeverity, EventType, GeopoliticalEvent
from app.schemas.event import GeopoliticalEventCreate, GeopoliticalEventRead

router = APIRouter()


@router.get("", response_model=list[GeopoliticalEventRead])
async def list_events(
    event_type: EventType | None = Query(default=None),
    severity: EventSeverity | None = Query(default=None),
    region: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(GeopoliticalEvent).order_by(desc(GeopoliticalEvent.occurred_at))
    if event_type is not None:
        stmt = stmt.where(GeopoliticalEvent.event_type == event_type)
    if severity is not None:
        stmt = stmt.where(GeopoliticalEvent.severity == severity)
    if region is not None:
        stmt = stmt.where(GeopoliticalEvent.region == region)
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{event_id}", response_model=GeopoliticalEventRead)
async def get_event(event_id: UUID, db: AsyncSession = Depends(get_db)):
    event = await db.get(GeopoliticalEvent, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return event


@router.post(
    "", response_model=GeopoliticalEventRead, status_code=status.HTTP_201_CREATED
)
async def create_event(
    payload: GeopoliticalEventCreate,
    db: AsyncSession = Depends(get_db),
):
    event = GeopoliticalEvent(
        **payload.model_dump(exclude={"source_url"}),
        source_url=str(payload.source_url) if payload.source_url else None,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
