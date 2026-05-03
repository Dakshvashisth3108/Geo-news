"""Geopolitical event schemas (request/response DTOs)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.event import EventSeverity, EventType


class GeopoliticalEventBase(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    summary: str = Field(min_length=1)
    event_type: EventType
    severity: EventSeverity
    region: str | None = Field(default=None, max_length=128)
    countries: list[str] = Field(
        default_factory=list,
        description="ISO 3166-1 alpha-2 codes, e.g. ['US', 'RU']",
    )
    source: str | None = Field(default=None, max_length=128)
    source_url: HttpUrl | None = None
    occurred_at: datetime
    raw_data: dict | None = None


class GeopoliticalEventCreate(GeopoliticalEventBase):
    pass


class GeopoliticalEventUpdate(BaseModel):
    severity: EventSeverity | None = None
    region: str | None = Field(default=None, max_length=128)
    countries: list[str] | None = None
    summary: str | None = None
    raw_data: dict | None = None


class GeopoliticalEventRead(GeopoliticalEventBase):
    id: UUID
    ingested_at: datetime

    model_config = ConfigDict(from_attributes=True)
