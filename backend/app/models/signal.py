"""TradingSignal model — the core artefact produced by the GTI engine.

Fields explained:
  * asset             — ticker / instrument the signal is about (e.g. "BRENT").
  * direction         — LONG / SHORT / NEUTRAL.
  * confidence        — model confidence in [0, 1].
  * uncertainty       — epistemic uncertainty in [0, 1] (1 - confidence-ish but
                        kept independent so we can surface multiple metrics).
  * explanation       — human-readable rationale (LLM output).
  * gti               — Geopolitical Tension Index score in [0, 100].
  * correlated_assets — JSONB list of {asset, correlation} pairs.
  * timestamp         — when the signal was generated (server-side default).
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Float, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SignalDirection(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class TradingSignal(Base):
    __tablename__ = "trading_signals"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    asset: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    direction: Mapped[SignalDirection] = mapped_column(
        Enum(SignalDirection, name="signal_direction"), nullable=False
    )

    # Bounded scores; we validate ranges at the schema layer.
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    gti: Mapped[float] = mapped_column(Float, nullable=False)

    explanation: Mapped[str] = mapped_column(String, nullable=False)

    # JSONB so we can index/query individual correlated assets later if needed.
    correlated_assets: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
