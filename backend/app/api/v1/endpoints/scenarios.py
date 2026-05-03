"""What-If Scenario Simulator endpoint."""

from fastapi import APIRouter, status

from app.schemas.scenario import ScenarioSimulateRequest, ScenarioSimulateResponse
from app.services import scenario_service

router = APIRouter()


@router.post(
    "/simulate",
    response_model=ScenarioSimulateResponse,
    status_code=status.HTTP_200_OK,
)
async def simulate_scenario(payload: ScenarioSimulateRequest) -> ScenarioSimulateResponse:
    """Project the asset impact of a hypothetical event described in plain English.

    Pipeline:
      1. NLP service extracts entities, sentiment, event type, and an
         NLP-derived GTI from the input text. If the NLP deps aren't
         installed, a keyword-based heuristic takes over (the response's
         `extracted.source` field tells you which path ran).
      2. The correlation engine projects asset impact from the structured
         facts (event_type, severity, countries, region).
      3. A templated narrative explains the projection in human-readable
         form — deterministic, no LLM round-trip needed.

    Use `severity_hint` for sensitivity analysis ("what if this is CRITICAL?")
    and `primary_asset_override` to pin a specific instrument as the anchor.
    """
    return await scenario_service.simulate(
        payload.text,
        severity_hint=payload.severity_hint,
        region_hint=payload.region_hint,
        primary_asset_override=payload.primary_asset_override,
    )
