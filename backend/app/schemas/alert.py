"""Alert rule schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.alert import AlertOperator


class AlertRuleBase(BaseModel):
    asset: str = Field(max_length=64)
    metric: str = Field(max_length=32, description="e.g. 'gti', 'confidence'")
    operator: AlertOperator
    threshold: float
    is_active: bool = True


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    metric: str | None = Field(default=None, max_length=32)
    operator: AlertOperator | None = None
    threshold: float | None = None
    is_active: bool | None = None


class AlertRuleRead(AlertRuleBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
