"""What-If Scenario Simulator.

Composes existing services:

  raw text  -->  nlp_service.analyze()  -->  structured facts
  facts     -->  correlation_service.analyze_event()  -->  asset projection
  both      -->  templated narrative explanation

If NLP deps (transformers, spaCy, torch) aren't installed or model load
fails, we fall through to a keyword-based heuristic so the simulator
still produces a useful response in dev / CI environments. The
`source` field on ExtractedFacts ('nlp' vs 'heuristic') tells the UI
which path was taken so it can label the result honestly.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.models.event import EventSeverity, EventType
from app.models.signal import SignalDirection
from app.schemas.correlation import CorrelationAnalysis
from app.schemas.scenario import ExtractedFacts, ScenarioSimulateResponse
from app.services import correlation_service

logger = logging.getLogger(__name__)


# ============================================================================
# Country name <-> ISO 3166-1 alpha-2  (same coverage as the heatmap)
# ============================================================================

NAME_TO_ISO2: dict[str, str] = {
    "united states": "US", "united states of america": "US", "usa": "US", "us": "US",
    "russia": "RU", "russian federation": "RU",
    "ukraine": "UA",
    "china": "CN", "prc": "CN",
    "india": "IN",
    "iran": "IR",
    "israel": "IL",
    "saudi arabia": "SA",
    "uk": "GB", "united kingdom": "GB", "britain": "GB", "england": "GB",
    "germany": "DE",
    "france": "FR",
    "italy": "IT",
    "spain": "ES",
    "japan": "JP",
    "south korea": "KR", "korea": "KR",
    "north korea": "KP", "dprk": "KP",
    "canada": "CA",
    "australia": "AU",
    "brazil": "BR",
    "mexico": "MX",
    "turkey": "TR", "türkiye": "TR",
    "egypt": "EG",
    "pakistan": "PK",
    "afghanistan": "AF",
    "syria": "SY",
    "iraq": "IQ",
    "yemen": "YE",
    "lebanon": "LB",
    "venezuela": "VE",
    "nigeria": "NG",
    "south africa": "ZA",
    "indonesia": "ID",
    "thailand": "TH",
    "vietnam": "VN",
    "philippines": "PH",
    "taiwan": "TW",
    "argentina": "AR",
    "chile": "CL",
    "colombia": "CO",
}


def _country_names_to_iso(names: list[str]) -> list[str]:
    """Map a list of human country names (any casing) to unique ISO-2 codes."""
    seen: list[str] = []
    for name in names:
        iso = NAME_TO_ISO2.get(name.strip().lower())
        if iso and iso not in seen:
            seen.append(iso)
    return seen


# Demonyms — adjective and people-noun forms that NER catches naturally
# (e.g. spaCy tags "Russian forces" as GPE) but a naive substring scan
# would miss. Mapping them to the same ISO codes is enough for the fallback.
DEMONYM_TO_ISO2: dict[str, str] = {
    "russian": "RU", "russians": "RU",
    "ukrainian": "UA", "ukrainians": "UA",
    "chinese": "CN",
    "indian": "IN", "indians": "IN",
    "iranian": "IR", "iranians": "IR",
    "israeli": "IL", "israelis": "IL",
    "saudi": "SA", "saudis": "SA",
    "british": "GB", "english": "GB",
    "american": "US", "americans": "US",
    "german": "DE", "germans": "DE",
    "french": "FR",
    "italian": "IT", "italians": "IT",
    "spanish": "ES",
    "japanese": "JP",
    "korean": "KR",
    "canadian": "CA", "canadians": "CA",
    "australian": "AU", "australians": "AU",
    "brazilian": "BR", "brazilians": "BR",
    "mexican": "MX", "mexicans": "MX",
    "turkish": "TR",
    "egyptian": "EG", "egyptians": "EG",
    "pakistani": "PK", "pakistanis": "PK",
    "afghan": "AF", "afghans": "AF",
    "syrian": "SY", "syrians": "SY",
    "iraqi": "IQ", "iraqis": "IQ",
    "yemeni": "YE", "yemenis": "YE",
    "lebanese": "LB",
    "venezuelan": "VE", "venezuelans": "VE",
    "nigerian": "NG", "nigerians": "NG",
    "indonesian": "ID", "indonesians": "ID",
    "thai": "TH",
    "vietnamese": "VN",
    "filipino": "PH",
    "taiwanese": "TW",
    "argentine": "AR", "argentinian": "AR",
    "chilean": "CL",
    "colombian": "CO", "colombians": "CO",
}

# Reverse-lookup so we can show a friendly country name when only the
# demonym appeared in the text.
_ISO2_TO_FRIENDLY: dict[str, str] = {
    iso: name.title()
    for name, iso in NAME_TO_ISO2.items()
    if " " not in name or name in {"united states", "united kingdom",
                                    "saudi arabia", "south korea", "north korea",
                                    "south africa"}
}


def _heuristic_extract_countries(text: str) -> tuple[list[str], list[str]]:
    """Whole-word case-insensitive scan over country names + demonyms.

    Returns (named, iso). Used by the no-NLP fallback path. Country
    names are tried first so "Russia" wins over "Russian" when both are
    present (we still merge into the same ISO row).
    """
    lower = text.lower()
    iso: list[str] = []
    named: list[str] = []

    # Pass 1: full country names (e.g. "United States", "Russia").
    for name, code in NAME_TO_ISO2.items():
        if re.search(rf"\b{re.escape(name)}\b", lower):
            if code not in iso:
                iso.append(code)
                named.append(name.title())

    # Pass 2: demonyms (e.g. "Russian", "Ukrainian", "Iranian").
    for demonym, code in DEMONYM_TO_ISO2.items():
        if code in iso:
            continue                # already captured via the name pass
        if re.search(rf"\b{re.escape(demonym)}\b", lower):
            iso.append(code)
            named.append(_ISO2_TO_FRIENDLY.get(code, code))

    return named, iso


# ============================================================================
# Heuristic event-type / severity classification
# ============================================================================

_EVENT_KEYWORDS: dict[EventType, list[str]] = {
    EventType.WAR:              ["war", "invasion", "invade", "missile", "airstrike", "bombing", "shelling"],
    EventType.CONFLICT:         ["clash", "skirmish", "border fighting", "engagement"],
    EventType.SANCTION:         ["sanction", "embargo", "tariff"],
    EventType.TERRORISM:        ["terror", "hostage", "extremist", "suicide bomber"],
    EventType.ELECTION:         ["election", "vote", "referendum", "ballot", "polls"],
    EventType.POLICY:           ["policy", "regulation", "rate hike", "rate cut", "central bank"],
    EventType.NATURAL_DISASTER: ["earthquake", "tsunami", "hurricane", "flood", "wildfire", "volcano"],
    EventType.ECONOMIC:         ["cpi", "gdp", "unemployment", "inflation", "recession", "default"],
    EventType.DIPLOMATIC:       ["summit", "treaty", "agreement", "negotiation", "peace deal"],
}

# Intentionally heavy-handed — these tokens override default severity.
_SEVERITY_KEYWORDS: dict[EventSeverity, list[str]] = {
    EventSeverity.CRITICAL: ["nuclear", "catastrophic", "massive casualties", "unprecedented", "all-out war"],
    EventSeverity.HIGH:     ["severe", "major", "casualties", "strike", "explosion", "crisis"],
    EventSeverity.LOW:      ["minor", "limited", "small-scale", "minimal"],
}


def _heuristic_classify(text: str) -> tuple[EventType, EventSeverity]:
    lower = text.lower()

    # Score each event type by keyword hits; fall back to OTHER.
    best_type: EventType = EventType.OTHER
    best_score = 0
    for et, keywords in _EVENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > best_score:
            best_score = score
            best_type = et

    # Severity: explicit keywords win, otherwise default to MEDIUM.
    severity: EventSeverity = EventSeverity.MEDIUM
    for sev, keywords in _SEVERITY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            severity = sev
            break

    # If the event type implies a high baseline (war/terror), bump severity
    # up unless explicitly overridden as LOW.
    if best_type in (EventType.WAR, EventType.TERRORISM) and severity == EventSeverity.MEDIUM:
        severity = EventSeverity.HIGH

    return best_type, severity


def _heuristic_sentiment(text: str) -> tuple[str, float]:
    """Lightweight polarity from a tiny lexicon. Replaced by FinBERT when available."""
    lower = text.lower()
    neg_words = {"crisis", "attack", "invasion", "war", "casualties", "fall", "drop",
                 "sanction", "default", "recession", "shock", "loss", "down", "shortfall"}
    pos_words = {"deal", "peace", "agreement", "rally", "rebound", "recovery", "growth",
                 "treaty", "boost", "surge", "stable", "optimism"}
    neg = sum(1 for w in neg_words if w in lower)
    pos = sum(1 for w in pos_words if w in lower)
    if neg == 0 and pos == 0:
        return "neutral", 0.0
    if neg > pos:
        score = min(1.0, neg / 5.0)
        return "negative", round(-score, 3)
    if pos > neg:
        score = min(1.0, pos / 5.0)
        return "positive", round(score, 3)
    return "neutral", 0.0


# ============================================================================
# Glue layer
# ============================================================================

@dataclass
class _NLPSummary:
    """Subset of NLPAnalysisResult we actually consume here."""
    event_type: EventType
    severity: EventSeverity
    sentiment_label: str
    sentiment_polarity: float
    gti: float
    countries_named: list[str]
    assets: list[str]
    persons: list[str]
    organizations: list[str]
    partial_failures: list[str]


async def _run_nlp(text: str) -> _NLPSummary | None:
    """Try the heavy NLP pipeline. Return None on any failure (caller falls back)."""
    try:
        # Imported lazily so a missing torch/transformers install doesn't kill
        # the whole module at import time.
        from app.services.nlp_service import get_nlp_service

        result = await get_nlp_service().analyze(text)
        return _NLPSummary(
            event_type=result.classification.event_type,
            severity=result.classification.severity,
            sentiment_label=result.sentiment.label,
            sentiment_polarity=result.sentiment.polarity,
            gti=result.gti,
            countries_named=list(result.entities.countries),
            assets=list(result.entities.assets),
            persons=list(result.entities.persons),
            organizations=list(result.entities.organizations),
            partial_failures=list(result.partial_failures),
        )
    except Exception as exc:  # noqa: BLE001
        # Any failure in the NLP path -> fall back. Logged so ops can see
        # whether scenarios are running on the heuristic vs. the real models.
        logger.warning("NLP analyze unavailable, using heuristic: %s", exc)
        return None


def _build_narrative(text: str, facts: ExtractedFacts, projection: CorrelationAnalysis) -> str:
    """Templated, deterministic explanation paragraph.

    Reads naturally for traders and is reproducible (same inputs -> same
    output) so we don't need an LLM round-trip for the MVP.
    """
    sev = facts.severity.value.lower()
    et = facts.event_type.value.replace("_", " ").lower()
    src_note = "via NLP pipeline" if facts.source == "nlp" else "via keyword heuristic"

    parts: list[str] = []

    parts.append(
        f"Read {src_note}: this scenario classifies as a "
        f"{sev}-severity {et} event with {facts.sentiment_label} sentiment "
        f"({facts.sentiment_polarity:+.2f} polarity)."
    )

    if facts.countries_named:
        parts.append(
            f"Affected countries detected: {', '.join(facts.countries_named[:5])}."
        )
    if facts.assets_mentioned:
        parts.append(
            f"Assets explicitly mentioned: {', '.join(facts.assets_mentioned[:6])}."
        )

    parts.append(
        f"Historical-pattern engine projects {projection.primary_asset} to "
        f"move {projection.direction.value} as the primary reaction "
        f"(GTI {projection.gti:.0f}/100, confidence {projection.confidence:.0%})."
    )

    top = projection.correlated_assets[:3]
    if top:
        descs = []
        for c in top:
            mag = f", ~{c.magnitude}%" if c.magnitude is not None else ""
            lag = f", lag {c.lag_minutes}m" if c.lag_minutes is not None else ""
            descs.append(
                f"{c.asset} {c.expected_impact.value} (corr {c.correlation:+.2f}{mag}{lag})"
            )
        parts.append(f"Strongest correlated movements: {'; '.join(descs)}.")

    return " ".join(parts)


async def simulate(
    text: str,
    *,
    severity_hint: EventSeverity | None = None,
    region_hint: str | None = None,
    primary_asset_override: str | None = None,
) -> ScenarioSimulateResponse:
    """End-to-end: text → structured facts → asset projection → narrative."""

    nlp = await _run_nlp(text)

    # ---------- Extract structured facts ----------
    if nlp is not None:
        countries_named = nlp.countries_named
        countries_iso = _country_names_to_iso(countries_named)
        # If NLP didn't pick up any country we recognise, fall back to a
        # keyword scan over the same curated table — strictly additive.
        if not countries_iso:
            heur_named, heur_iso = _heuristic_extract_countries(text)
            countries_named = countries_named or heur_named
            countries_iso = heur_iso

        facts = ExtractedFacts(
            source="nlp",
            event_type=nlp.event_type,
            severity=severity_hint or nlp.severity,
            sentiment_label=nlp.sentiment_label,
            sentiment_polarity=nlp.sentiment_polarity,
            gti_nlp=nlp.gti,
            countries_iso=countries_iso,
            countries_named=countries_named,
            assets_mentioned=nlp.assets,
            persons=nlp.persons,
            organizations=nlp.organizations,
        )
        partial_failures = nlp.partial_failures
    else:
        event_type, heuristic_severity = _heuristic_classify(text)
        sent_label, sent_polarity = _heuristic_sentiment(text)
        named, iso = _heuristic_extract_countries(text)
        # Heuristic GTI: severity score + breadth. Coarse but bounded.
        sev_score = {EventSeverity.LOW: 25, EventSeverity.MEDIUM: 50,
                     EventSeverity.HIGH: 75, EventSeverity.CRITICAL: 100}[heuristic_severity]
        breadth = min(len(iso), 5) * 4  # 0..20
        gti = float(min(100, sev_score * 0.6 + 20 * max(-sent_polarity, 0.0) + breadth))

        facts = ExtractedFacts(
            source="heuristic",
            event_type=event_type,
            severity=severity_hint or heuristic_severity,
            sentiment_label=sent_label,
            sentiment_polarity=sent_polarity,
            gti_nlp=round(gti, 2),
            countries_iso=iso,
            countries_named=named,
            assets_mentioned=[],
            persons=[],
            organizations=[],
        )
        partial_failures = ["nlp"]  # whole pipeline fell back

    # ---------- Project assets via the correlation engine ----------
    outcome = correlation_service.analyze_event(
        event_type=facts.event_type,
        severity=facts.severity,
        countries=facts.countries_iso,
        region=region_hint,
        summary=text[:200],
        primary_asset_override=primary_asset_override,
    )

    projection = CorrelationAnalysis(
        primary_asset=outcome.primary_asset,
        direction=outcome.direction,
        confidence=outcome.confidence,
        uncertainty=outcome.uncertainty,
        gti=outcome.gti,
        correlated_assets=outcome.correlated_assets,
        reasoning=outcome.reasoning,
        signal_id=None,  # scenario simulator never persists; preview only
    )

    narrative = _build_narrative(text, facts, projection)

    return ScenarioSimulateResponse(
        text=text,
        extracted=facts,
        projection=projection,
        narrative=narrative,
        partial_failures=partial_failures,
    )
