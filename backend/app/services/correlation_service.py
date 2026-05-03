"""Multi-asset correlation engine.

Takes one geopolitical event and returns the basket of assets we expect
to react, with each asset's expected direction, magnitude, lag, and a
derived correlation coefficient relative to the chosen primary asset.

Design (rule-based with smart aggregation)
------------------------------------------
1. **Rules** — three lookup tables keyed by `event_type` / country
   (ISO-2) / region. Each entry is an `AssetReaction(asset, direction,
   base_magnitude, lag_minutes)`.
2. **Severity scaling** — LOW (0.4×) through CRITICAL (2.4×) multiplies
   every magnitude.
3. **Aggregation** — when multiple rules hit the same asset, weighted-vote
   the direction by magnitude, average the magnitude, take the minimum
   lag (the fastest reaction wins).
4. **Primary selection** — highest-magnitude non-neutral asset; caller
   may override via `primary_asset_override`.
5. **Synthetic correlation** — for each non-primary asset, derive a
   Pearson-like value in [-1, 1] from direction agreement + magnitude
   similarity. *Not* a real historical correlation — a structural proxy
   good enough for an MVP UI. Replace with a learned matrix later.
6. **Confidence / GTI** — directional clarity × rule density; GTI blends
   severity weight with confidence (mirrors the NLP service heuristic).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Iterable

from app.models.event import EventSeverity, EventType, GeopoliticalEvent
from app.models.signal import SignalDirection
from app.schemas.signal import CorrelatedAsset

logger = logging.getLogger(__name__)

LONG = SignalDirection.LONG
SHORT = SignalDirection.SHORT
NEUTRAL = SignalDirection.NEUTRAL


@dataclass(frozen=True)
class AssetReaction:
    asset: str
    direction: SignalDirection
    # Expected % move at MEDIUM severity. Severity multiplier scales this.
    base_magnitude: float
    # Typical delay between event and price reaction.
    lag_minutes: int


# ============================================================================
# Severity multipliers
# ============================================================================

SEVERITY_MULTIPLIER: dict[EventSeverity, float] = {
    EventSeverity.LOW: 0.4,
    EventSeverity.MEDIUM: 1.0,
    EventSeverity.HIGH: 1.6,
    EventSeverity.CRITICAL: 2.4,
}

SEVERITY_SCORE: dict[EventSeverity, float] = {
    EventSeverity.LOW: 0.25,
    EventSeverity.MEDIUM: 0.50,
    EventSeverity.HIGH: 0.75,
    EventSeverity.CRITICAL: 1.00,
}


# ============================================================================
# Rule tables — dense, named, auditable.
# Magnitudes are %-move expectations at MEDIUM severity.
# ============================================================================

EVENT_TYPE_RULES: dict[EventType, list[AssetReaction]] = {
    EventType.WAR: [
        AssetReaction("BRENT",  LONG,  4.0, 15),
        AssetReaction("WTI",    LONG,  4.0, 15),
        AssetReaction("GOLD",   LONG,  2.0, 10),
        AssetReaction("USD",    LONG,  0.5, 20),
        AssetReaction("SPX",    SHORT, 2.0, 30),
        AssetReaction("NDX",    SHORT, 2.5, 30),
        AssetReaction("DJI",    SHORT, 1.7, 30),
        AssetReaction("WHEAT",  LONG,  3.0, 30),
        AssetReaction("NATGAS", LONG,  3.5, 25),
    ],
    EventType.CONFLICT: [
        AssetReaction("BRENT",  LONG,  2.0, 20),
        AssetReaction("WTI",    LONG,  2.0, 20),
        AssetReaction("GOLD",   LONG,  1.0, 15),
        AssetReaction("SPX",    SHORT, 0.8, 45),
    ],
    EventType.SANCTION: [
        AssetReaction("BRENT",  LONG,  1.5, 30),
        AssetReaction("WTI",    LONG,  1.5, 30),
        AssetReaction("GOLD",   LONG,  0.8, 20),
        AssetReaction("USD",    LONG,  0.3, 30),
    ],
    EventType.TERRORISM: [
        AssetReaction("SPX",    SHORT, 1.2, 15),
        AssetReaction("GOLD",   LONG,  1.5, 10),
        AssetReaction("USD",    LONG,  0.4, 20),
        AssetReaction("BRENT",  LONG,  0.6, 30),
    ],
    EventType.ELECTION: [
        # Direction is country-dependent; FX comes from country rules.
        # Keep this generic — equity uncertainty.
        AssetReaction("SPX",    NEUTRAL, 0.5, 240),
    ],
    EventType.POLICY: [
        AssetReaction("USD",    NEUTRAL, 0.4, 60),
        AssetReaction("SPX",    NEUTRAL, 0.5, 60),
    ],
    EventType.NATURAL_DISASTER: [
        AssetReaction("BRENT",  LONG,  1.0, 60),
        AssetReaction("WHEAT",  LONG,  1.5, 120),
    ],
    EventType.ECONOMIC: [
        AssetReaction("SPX",    NEUTRAL, 1.0, 5),
        AssetReaction("USD",    NEUTRAL, 0.6, 5),
        AssetReaction("GOLD",   NEUTRAL, 0.5, 10),
    ],
    EventType.DIPLOMATIC: [
        AssetReaction("SPX",    LONG,  0.6, 60),
        AssetReaction("BRENT",  SHORT, 0.4, 60),
    ],
    EventType.OTHER: [],
}

# Country reactions — ISO 3166-1 alpha-2 codes.
# "What happens to this asset when something disruptive hits this country?"
COUNTRY_RULES: dict[str, list[AssetReaction]] = {
    "US": [
        AssetReaction("SPX", SHORT, 1.0, 30),
        AssetReaction("NDX", SHORT, 1.2, 30),
        AssetReaction("USD", LONG,  0.5, 30),
    ],
    "RU": [
        AssetReaction("NATGAS", LONG, 4.0, 30),
        AssetReaction("WHEAT",  LONG, 2.0, 60),
        AssetReaction("BRENT",  LONG, 2.5, 30),
    ],
    "UA": [
        AssetReaction("WHEAT",  LONG, 3.5, 60),
        AssetReaction("NATGAS", LONG, 1.5, 60),
    ],
    "CN": [
        AssetReaction("COPPER", SHORT, 1.5, 60),
        AssetReaction("CNY",    SHORT, 0.8, 30),
    ],
    "IN": [
        AssetReaction("NIFTY", SHORT, 1.5, 30),
        AssetReaction("INR",   SHORT, 0.5, 30),
    ],
    "SA": [
        AssetReaction("BRENT", LONG, 3.5, 15),
        AssetReaction("WTI",   LONG, 3.5, 15),
    ],
    "IR": [
        AssetReaction("BRENT", LONG, 4.0, 10),
        AssetReaction("WTI",   LONG, 4.0, 10),
    ],
    "IL": [
        AssetReaction("BRENT", LONG, 1.5, 30),
        AssetReaction("GOLD",  LONG, 0.8, 30),
    ],
    "VE": [
        AssetReaction("BRENT", LONG, 1.0, 60),
    ],
    "GB": [
        AssetReaction("FTSE", SHORT, 1.0, 30),
        AssetReaction("GBP",  SHORT, 0.5, 30),
    ],
    "DE": [
        AssetReaction("DAX", SHORT, 1.2, 30),
        AssetReaction("EUR", SHORT, 0.4, 30),
    ],
    "JP": [
        AssetReaction("JPY", LONG, 0.6, 30),  # safe-haven
    ],
    "CA": [
        AssetReaction("WTI", LONG, 1.0, 30),
    ],
}

# Region reactions (lowercase keys; we lowercase the input).
REGION_RULES: dict[str, list[AssetReaction]] = {
    "middle east": [
        AssetReaction("BRENT", LONG, 3.0, 15),
        AssetReaction("WTI",   LONG, 3.0, 15),
        AssetReaction("GOLD",  LONG, 1.0, 15),
    ],
    "eastern europe": [
        AssetReaction("NATGAS", LONG, 2.5, 30),
        AssetReaction("WHEAT",  LONG, 2.0, 60),
        AssetReaction("EUR",    SHORT, 0.5, 30),
    ],
    "east asia": [
        AssetReaction("CNY", SHORT, 0.5, 30),
        AssetReaction("JPY", LONG,  0.5, 30),
    ],
    "south asia": [
        AssetReaction("INR",   SHORT, 0.4, 30),
        AssetReaction("NIFTY", SHORT, 1.0, 30),
    ],
}

# Tunables for the synthetic correlation derivation.
# Same-direction match: base 0.5, +0.4 for full magnitude similarity → [0.5, 0.9].
_SAME_DIR_BASE = 0.5
_SAME_DIR_MAG_BONUS = 0.4

# Cap on basket size returned. 32 matches the schema's max_length so the
# engine can't accidentally produce a payload Pydantic will then reject.
_MAX_CORRELATED = 32


# ============================================================================
# Aggregation primitives
# ============================================================================

def _vote_direction(reactions: list[AssetReaction]) -> SignalDirection:
    """Magnitude-weighted directional vote across rules hitting one asset."""
    long_w  = sum(r.base_magnitude for r in reactions if r.direction == LONG)
    short_w = sum(r.base_magnitude for r in reactions if r.direction == SHORT)
    if long_w == short_w:
        return NEUTRAL
    return LONG if long_w > short_w else SHORT


def _aggregate(asset: str, reactions: list[AssetReaction]) -> AssetReaction:
    """Combine multiple rules hitting one asset into a single reaction.

    * direction      — magnitude-weighted vote
    * base_magnitude — average (so identical rules don't double-count)
    * lag_minutes    — min (the earliest reaction wins)
    """
    direction = _vote_direction(reactions)
    avg_mag = sum(r.base_magnitude for r in reactions) / len(reactions)
    min_lag = min(r.lag_minutes for r in reactions)
    return AssetReaction(asset, direction, avg_mag, min_lag)


def _derive_correlation(primary: AssetReaction, other: AssetReaction) -> float:
    """Synthetic Pearson-like correlation between primary and other reactions.

    Real historical correlations would come from price data; this is a
    structural proxy:
      * same direction with similar magnitude  →  strongly positive
      * opposite directions                    →  strongly negative
      * either NEUTRAL                         →  ~0
    """
    if primary.direction == NEUTRAL or other.direction == NEUTRAL:
        return 0.0
    larger = max(primary.base_magnitude, other.base_magnitude, 0.1)
    smaller = min(primary.base_magnitude, other.base_magnitude)
    mag_ratio = smaller / larger                       # [0, 1]
    base = _SAME_DIR_BASE + _SAME_DIR_MAG_BONUS * mag_ratio  # [0.5, 0.9]
    return round(base if primary.direction == other.direction else -base, 3)


# ============================================================================
# Public API
# ============================================================================

@dataclass
class AnalysisOutcome:
    """Final result of running the engine over an event."""
    primary_asset: str
    direction: SignalDirection
    confidence: float        # [0, 1]
    uncertainty: float       # [0, 1]
    gti: float               # [0, 100]
    correlated_assets: list[CorrelatedAsset]
    reasoning: str


def analyze_event(
    event: GeopoliticalEvent | None = None,
    *,
    event_type: EventType | None = None,
    severity: EventSeverity | None = None,
    countries: Iterable[str] | None = None,
    region: str | None = None,
    summary: str | None = None,
    primary_asset_override: str | None = None,
) -> AnalysisOutcome:
    """Run the engine.

    Caller can pass either a full `GeopoliticalEvent` instance, or the
    discrete fields. The latter form is used by the inline-event path on
    POST /signals/analyze-correlation so callers can preview an analysis
    without persisting an event first.
    """
    # ---------- resolve inputs ----------
    if event is not None:
        _event_type = event.event_type
        _severity = event.severity
        _countries = list(event.countries or [])
        _region = event.region
        _summary = (event.title or "") or (event.summary or "")
    else:
        if event_type is None or severity is None:
            raise ValueError(
                "event_type and severity are required when `event` is not provided",
            )
        _event_type = event_type
        _severity = severity
        _countries = list(countries or [])
        _region = region
        _summary = summary or ""

    # ---------- collect rule hits ----------
    raw: list[AssetReaction] = []
    raw.extend(EVENT_TYPE_RULES.get(_event_type, []))
    for c in _countries:
        raw.extend(COUNTRY_RULES.get(c.upper(), []))
    if _region:
        raw.extend(REGION_RULES.get(_region.lower(), []))

    if not raw:
        # No matching rules — return a typed "no signal" payload so the
        # caller doesn't have to handle a None separately.
        return AnalysisOutcome(
            primary_asset="USD",
            direction=NEUTRAL,
            confidence=0.0,
            uncertainty=1.0,
            gti=0.0,
            correlated_assets=[],
            reasoning="No matching correlation rules — engine emitted neutral fallback.",
        )

    # ---------- aggregate per-asset ----------
    by_asset: dict[str, list[AssetReaction]] = {}
    for r in raw:
        by_asset.setdefault(r.asset, []).append(r)

    aggregated: list[AssetReaction] = [
        _aggregate(asset, rs) for asset, rs in by_asset.items()
    ]

    # ---------- severity scaling ----------
    mult = SEVERITY_MULTIPLIER[_severity]
    aggregated = [
        replace(r, base_magnitude=round(r.base_magnitude * mult, 3))
        for r in aggregated
    ]

    # ---------- pick the primary ----------
    primary: AssetReaction
    if primary_asset_override and any(r.asset == primary_asset_override for r in aggregated):
        primary = next(r for r in aggregated if r.asset == primary_asset_override)
    else:
        # Largest non-NEUTRAL magnitude wins; deterministic tiebreak by asset name.
        non_neutral = [r for r in aggregated if r.direction != NEUTRAL]
        candidates = non_neutral or aggregated
        primary = max(candidates, key=lambda r: (r.base_magnitude, -ord(r.asset[0])))

    # ---------- build CorrelatedAsset list (excluding primary) ----------
    correlated = [
        CorrelatedAsset(
            asset=r.asset,
            correlation=_derive_correlation(primary, r),
            expected_impact=r.direction,
            magnitude=round(r.base_magnitude, 2),
            lag_minutes=r.lag_minutes,
        )
        for r in aggregated
        if r.asset != primary.asset
    ]
    correlated.sort(key=lambda c: -abs(c.correlation))
    correlated = correlated[:_MAX_CORRELATED]

    # ---------- confidence / uncertainty / GTI ----------
    long_w  = sum(r.base_magnitude for r in aggregated if r.direction == LONG)
    short_w = sum(r.base_magnitude for r in aggregated if r.direction == SHORT)
    total_w = long_w + short_w
    directional_clarity = abs(long_w - short_w) / total_w if total_w > 0 else 0.0
    rule_density = min(len(aggregated) / 6.0, 1.0)
    confidence = round(0.55 * directional_clarity + 0.45 * rule_density, 3)

    uncertainty_bump = 0.2 if primary.direction == NEUTRAL else 0.0
    uncertainty = round(min(1.0, max(0.0, 1.0 - confidence + uncertainty_bump)), 3)

    severity_score = SEVERITY_SCORE[_severity]
    gti = round(min(100.0, 100.0 * (0.6 * severity_score + 0.4 * confidence)), 2)

    reasoning = _format_reasoning(
        event_type=_event_type,
        severity=_severity,
        countries=_countries,
        region=_region,
        primary=primary,
        rule_hits=len(by_asset),
        summary=_summary,
    )

    return AnalysisOutcome(
        primary_asset=primary.asset,
        direction=primary.direction,
        confidence=confidence,
        uncertainty=uncertainty,
        gti=gti,
        correlated_assets=correlated,
        reasoning=reasoning,
    )


def _format_reasoning(
    *,
    event_type: EventType,
    severity: EventSeverity,
    countries: list[str],
    region: str | None,
    primary: AssetReaction,
    rule_hits: int,
    summary: str,
) -> str:
    parts = [
        f"{event_type.value.replace('_', ' ').title()} event "
        f"(severity {severity.value}) hit {rule_hits} assets",
    ]
    if countries:
        parts.append(f"across {len(countries)} country/region(s): {', '.join(countries[:5])}")
    if region:
        parts.append(f"in region '{region}'")
    parts.append(
        f"Primary: {primary.asset} → {primary.direction.value} "
        f"(magnitude ≈ {primary.base_magnitude:.2f}%, lag {primary.lag_minutes}m).",
    )
    if summary:
        parts.append(f"Summary: {summary[:140]}")
    return " ".join(parts)
