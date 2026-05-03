"""AlertRule model — compound user-defined triggers over signal metrics.

Shape (v2)
----------
Each rule has:
  * `name`              human-readable label
  * `asset`             optional filter (null / "*" matches every asset)
  * `conditions`        list of {metric, operator, threshold} dicts
  * `combinator`        AND  — every condition must pass
                        OR   — any single condition passes
  * `channels`          list of {type, target} dicts (email | webhook)
  * `cooldown_seconds`  minimum gap between consecutive fires
  * `last_triggered_at` / `trigger_count`  bookkeeping
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AlertOperator(str, enum.Enum):
    """Comparison operators used inside individual conditions.

    NOT a Postgres enum anymore — conditions live in JSONB and we
    validate the operator strings at the schema layer.
    """
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    EQ = "EQ"


class AlertCombinator(str, enum.Enum):
    """How the rule combines its individual conditions."""
    AND = "AND"
    OR = "OR"


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Human-facing ---
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # --- Filter ---
    # null or "*" means "this rule fires for any asset". Otherwise exact match
    # against TradingSignal.asset (case-insensitive — see alert_service).
    asset: Mapped[str | None] = mapped_column(String(64), index=True)

    # --- Compound trigger logic ---
    conditions: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list,
    )
    combinator: Mapped[AlertCombinator] = mapped_column(
        Enum(AlertCombinator, name="alert_combinator"),
        nullable=False,
        default=AlertCombinator.AND,
    )

    # --- Notification fan-out ---
    # Each entry: {"type": "email" | "webhook", "target": "<addr-or-url>"}.
    channels: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list,
    )

    # --- Rate limiting / bookkeeping ---
    cooldown_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300,
    )
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trigger_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="alert_rules")  # noqa: F821
