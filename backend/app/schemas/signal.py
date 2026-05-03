"""Trading signal schemas — including richer multi-asset correlation entries."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.signal import SignalDirection


class CorrelatedAsset(BaseModel):
    """One entry in the JSONB `correlated_assets` list.

    Captures *how* a secondary asset is expected to move when this signal
    fires — not just the historical correlation coefficient, but the
    direction/magnitude/lag the model expects in this regime.
    """
    asset: str = Field(max_length=64, description="Ticker / instrument code")
    correlation: float = Field(
        ge=-1.0, le=1.0, description="Pearson correlation in current regime"
    )
    expected_impact: SignalDirection = Field(
        description="Direction the correlated asset is expected to take"
    )
    magnitude: float | None = Field(
        default=None,
        ge=0.0,
        description="Expected % move; None if model is undecided",
    )
    lag_minutes: int | None = Field(
        default=None,
        ge=0,
        description="Expected lag from primary asset move, in minutes",
    )


class TradingSignalBase(BaseModel):
    asset: str = Field(max_length=64)
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    gti: float = Field(ge=0.0, le=100.0, description="Geopolitical Tension Index")
    explanation: str = Field(min_length=1)
    correlated_assets: list[CorrelatedAsset] = Field(default_factory=list)
    event_id: UUID | None = None


class TradingSignalCreate(TradingSignalBase):
    """Used by the ingestion pipeline / admin endpoints to publish signals."""
    pass


class TradingSignalRead(TradingSignalBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
