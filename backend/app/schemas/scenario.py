"""Schemas for the What-If Scenario Simulator endpoint."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.event import EventSeverity, EventType
from app.schemas.correlation import CorrelationAnalysis


class ScenarioSimulateRequest(BaseModel):
    """Hypothetical event description + optional structuring hints."""

    text: str = Field(
        min_length=10,
        max_length=4000,
        description="Plain-English description of the hypothetical event.",
    )
    severity_hint: EventSeverity | None = Field(
        default=None,
        description=(
            "Override the severity the engine would otherwise infer. "
            "Useful for sensitivity analysis ('what if this is CRITICAL?')."
        ),
    )
    region_hint: str | None = Field(
        default=None,
        max_length=128,
        description=(
            "Optional geographic region to feed the correlation engine "
            "(e.g. 'middle east', 'eastern europe')."
        ),
    )
    primary_asset_override: str | None = Field(
        default=None,
        max_length=64,
        description="Force the correlation engine to pick this asset as primary.",
    )


class ExtractedFacts(BaseModel):
    """Structured facts derived from the input text — either by the NLP
    service or, when ML deps are unavailable, by the heuristic fallback.
    `source` indicates which path produced these values."""

    source: str = Field(
        description="'nlp' (full HF pipeline) or 'heuristic' (keyword fallback)",
    )
    event_type: EventType
    severity: EventSeverity

    sentiment_label: str = Field(description="positive | neutral | negative")
    sentiment_polarity: float = Field(
        ge=-1.0, le=1.0,
        description="+score for positive, -score for negative, 0 for neutral",
    )
    gti_nlp: float = Field(
        ge=0.0, le=100.0,
        description="GTI from the NLP heuristic (independent of correlation GTI)",
    )

    countries_iso: list[str] = Field(default_factory=list)
    countries_named: list[str] = Field(default_factory=list)
    assets_mentioned: list[str] = Field(default_factory=list)
    persons: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)


class ScenarioSimulateResponse(BaseModel):
    text: str
    extracted: ExtractedFacts
    projection: CorrelationAnalysis
    narrative: str = Field(
        description="Plain-English explanation of the projected impact.",
    )
    partial_failures: list[str] = Field(
        default_factory=list,
        description=(
            "Names of pipeline stages that degraded gracefully "
            "(e.g. 'sentiment' if FinBERT failed but the rest worked)."
        ),
    )

    model_config = ConfigDict(from_attributes=True)
