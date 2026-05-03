"""TradingSignal — the GTI engine's output.

TimescaleDB compatibility notes
-------------------------------
TimescaleDB requires the partitioning column (here: `timestamp`) to be part
of every UNIQUE/PRIMARY KEY constraint. We therefore use a *composite*
primary key `(id, timestamp)`. UUIDv4 collisions are vanishingly rare, so
this preserves practical row uniqueness while letting us promote the table
to a hypertable with:

    SELECT create_hypertable('trading_signals', 'timestamp');

The schema also works fine on vanilla PostgreSQL (e.g. Render's managed
Postgres, which does NOT ship the timescaledb extension).

Fields
------
* `asset`             — primary instrument the signal is about.
* `direction`         — LONG / SHORT / NEUTRAL.
* `confidence`        — model confidence in [0, 1].
* `uncertainty`       — epistemic uncertainty in [0, 1].
* `gti`               — Geopolitical Tension Index, [0, 100].
* `explanation`       — LLM-generated rationale.
* `correlated_assets` — JSONB array of richer correlation entries
                        (asset, correlation, expected_impact, magnitude, lag).
* `event_id`          — optional FK to the upstream GeopoliticalEvent.
* `timestamp`         — generation time (also the hypertable partition key).
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SignalDirection(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class TradingSignal(Base):
    __tablename__ = "trading_signals"

    # NOTE: composite PK (id, timestamp) — required for TimescaleDB hypertable.
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        server_default=func.now(),
        nullable=False,
    )

    asset: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[SignalDirection] = mapped_column(
        Enum(SignalDirection, name="signal_direction"), nullable=False
    )

    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    gti: Mapped[float] = mapped_column(Float, nullable=False)

    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # JSONB array — each entry is a CorrelatedAsset (see schemas/signal.py).
    correlated_assets: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # Optional provenance link. Nullable because some signals come from
    # aggregated state, not a single discrete event.
    event_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("geopolitical_events.id", ondelete="SET NULL"),
    )

    event: Mapped["GeopoliticalEvent | None"] = relationship(  # noqa: F821
        back_populates="signals", lazy="joined"
    )

    # Most-frequent query: latest-first signals for a given asset.
    # `timestamp DESC` matches the query ORDER BY exactly.
    __table_args__ = (
        Index(
            "ix_signals_asset_timestamp",
            "asset",
            "timestamp",
            postgresql_using="btree",
        ),
        Index("ix_signals_timestamp", "timestamp"),
    )
