"""Schemas for the multi-asset correlation analysis endpoint."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.signal import SignalDirection
from app.schemas.event import GeopoliticalEventCreate
from app.schemas.signal import CorrelatedAsset


class AnalyzeCorrelationRequest(BaseModel):
    """Caller can either reference an existing persisted event by id,
    or pass an inline event payload (same shape as GeopoliticalEventCreate).
    Exactly one of `event_id` or `event` is required.
    """

    event_id: UUID | None = None
    event: GeopoliticalEventCreate | None = None

    primary_asset: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Force the engine to pick this asset as the primary. "
            "Ignored if it isn't among the rule-derived candidates."
        ),
    )
    persist: bool = Field(
        default=False,
        description=(
            "If true, also create a TradingSignal from the analysis and "
            "broadcast it on the WebSocket stream."
        ),
    )

    @model_validator(mode="after")
    def _exactly_one_event_source(self):
        if (self.event_id is None) == (self.event is None):
            raise ValueError("Provide exactly one of `event_id` or `event`.")
        return self


class CorrelationAnalysis(BaseModel):
    """Engine output. Mirrors `services.correlation_service.AnalysisOutcome`."""

    primary_asset: str
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    gti: float = Field(ge=0.0, le=100.0)
    correlated_assets: list[CorrelatedAsset]
    reasoning: str
    # If `persist=True` was passed, the id of the newly-created TradingSignal.
    signal_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)
