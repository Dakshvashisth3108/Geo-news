"""GeopoliticalEvent — the upstream signal source.

Every event flows through the GTI engine, which then produces zero or more
TradingSignals. We persist the event so signals can link back to their
provenance (auditability + explainability).
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EventType(str, enum.Enum):
    WAR = "WAR"
    CONFLICT = "CONFLICT"
    SANCTION = "SANCTION"
    ELECTION = "ELECTION"
    POLICY = "POLICY"
    TERRORISM = "TERRORISM"
    NATURAL_DISASTER = "NATURAL_DISASTER"
    ECONOMIC = "ECONOMIC"
    DIPLOMATIC = "DIPLOMATIC"
    OTHER = "OTHER"


class EventSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GeopoliticalEvent(Base):
    __tablename__ = "geopolitical_events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type"), nullable=False, index=True
    )
    severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity, name="event_severity"), nullable=False, index=True
    )

    region: Mapped[str | None] = mapped_column(String(128), index=True)
    # ISO 3166-1 alpha-2 codes, e.g. ["US", "RU", "UA"].
    countries: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    source: Mapped[str | None] = mapped_column(String(128))
    source_url: Mapped[str | None] = mapped_column(String(1024))

    # When the event happened in the real world, vs. when we ingested it.
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Free-form payload (raw article, NLP scores, embeddings refs, etc.).
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    # Reverse side of TradingSignal.event_id; lazy by default.
    signals: Mapped[list["TradingSignal"]] = relationship(  # noqa: F821
        back_populates="event"
    )

    # Compound index — most queries are "events of type X in region Y, recent first".
    __table_args__ = (
        Index("ix_events_type_occurred", "event_type", "occurred_at"),
    )
