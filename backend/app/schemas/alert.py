"""Alert rule schemas (compound-condition shape)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.alert import AlertCombinator, AlertOperator


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class AlertCondition(BaseModel):
    """One condition in a rule. Multiple conditions combine via the rule's
    `combinator` (AND / OR).

    Allowed metric names map to attributes on a TradingSignal:
      * `gti`         — Geopolitical Tension Index, [0, 100]
      * `confidence`  — model confidence, [0, 1]
      * `uncertainty` — epistemic uncertainty, [0, 1]
    """
    metric: Literal["gti", "confidence", "uncertainty"]
    operator: AlertOperator
    threshold: float


class NotificationChannel(BaseModel):
    """One delivery target. `target` shape depends on `type`:

      * email   — RFC 5321 address
      * webhook — fully-qualified https URL
    """
    type: Literal["email", "webhook"]
    target: str = Field(min_length=1, max_length=512)


# ---------------------------------------------------------------------------
# AlertRule schemas
# ---------------------------------------------------------------------------

class AlertRuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    asset: str | None = Field(
        default=None,
        max_length=64,
        description="Filter to a single asset, or null/'*' for any asset.",
    )
    conditions: list[AlertCondition] = Field(min_length=1, max_length=8)
    combinator: AlertCombinator = AlertCombinator.AND
    channels: list[NotificationChannel] = Field(default_factory=list, max_length=8)
    cooldown_seconds: int = Field(default=300, ge=0, le=86400)
    is_active: bool = True


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    """All fields optional — `exclude_unset=True` is used at the endpoint."""
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    asset: str | None = Field(default=None, max_length=64)
    conditions: list[AlertCondition] | None = Field(default=None, min_length=1, max_length=8)
    combinator: AlertCombinator | None = None
    channels: list[NotificationChannel] | None = Field(default=None, max_length=8)
    cooldown_seconds: int | None = Field(default=None, ge=0, le=86400)
    is_active: bool | None = None


class AlertRuleRead(AlertRuleBase):
    id: UUID
    user_id: UUID
    last_triggered_at: datetime | None
    trigger_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertTestResult(BaseModel):
    """Response for POST /alerts/{rule_id}/test."""
    rule_id: UUID
    channels_attempted: int
    channels: list[NotificationChannel]
