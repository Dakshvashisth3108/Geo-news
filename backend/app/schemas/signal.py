"""Trading signal schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.signal import SignalDirection


class CorrelatedAsset(BaseModel):
    """One entry inside the JSONB `correlated_assets` array."""
    asset: str = Field(max_length=64)
    correlation: float = Field(ge=-1.0, le=1.0)


class TradingSignalBase(BaseModel):
    asset: str = Field(max_length=64)
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    gti: float = Field(ge=0.0, le=100.0, description="Geopolitical Tension Index")
    explanation: str = Field(min_length=1)
    correlated_assets: list[CorrelatedAsset] = Field(default_factory=list)


class TradingSignalCreate(TradingSignalBase):
    """Used by the ingestion pipeline / admin endpoints to publish signals."""
    pass


class TradingSignalRead(TradingSignalBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
