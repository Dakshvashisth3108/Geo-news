"""NLP service for raw geopolitical news text.

Pipeline
--------
1. Entity extraction
   * spaCy NER for PERSON / GPE (countries, regions) / ORG / EVENT / DATE / MONEY
   * Curated keyword scan for tradeable assets (commodities, indices, FX, crypto)
2. Financial sentiment
   * FinBERT (`ProsusAI/finbert`) — labels: positive / neutral / negative
3. Event classification
   * Zero-shot classification (`facebook/bart-large-mnli`) over a small label
     set that maps cleanly onto our `EventType` enum
4. GTI (Global / Geopolitical Tension Index, 0–100)
   * Deterministic weighted blend of event severity, sentiment, country
     breadth, and explicit-tension keyword density. Cheap and explainable.

Performance / deployment
------------------------
* Models are loaded lazily on first use behind an `asyncio.Lock` so concurrent
  cold-start callers don't redundantly load weights.
* Every model call is dispatched to a worker thread via `asyncio.to_thread`
  so the event loop is never blocked by inference.
* If `REDIS_URL` is set, results are cached by SHA-256(text) for
  `NLP_CACHE_TTL_SECONDS`. Falls back transparently when Redis is absent
  or unreachable.

Component-level resilience
--------------------------
Each component (entities / sentiment / classification) is wrapped so a
failure degrades only that field — the call still returns a usable result
plus a `partial_failures` list naming the broken steps.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.event import EventSeverity, EventType

logger = logging.getLogger(__name__)


# ============================================================================
# Constants — kept at module level so they're cheap to reference and easy
# to override in tests by monkey-patching.
# ============================================================================

# Hard input cap — BERT-family tokenizers max at 512 tokens; ~3500 chars is
# a safe upper bound after tokenization, with headroom for special tokens.
MAX_INPUT_CHARS = 3500

# Curated tradeable-asset dictionary. spaCy doesn't recognise tickers as
# entities, so we scan separately. Keep this conservative — false positives
# here propagate into trading decisions downstream.
ASSET_KEYWORDS: dict[str, list[str]] = {
    "BRENT":   ["brent", "brent crude"],
    "WTI":     ["wti", "west texas intermediate"],
    "GOLD":    ["gold", "xau"],
    "SILVER":  ["silver", "xag"],
    "COPPER":  ["copper"],
    "NATGAS":  ["natural gas", "natgas"],
    "WHEAT":   ["wheat"],
    "SPX":     ["s&p 500", "s&p500", "spx"],
    "NDX":     ["nasdaq 100", "ndx"],
    "DJI":     ["dow jones", "djia"],
    "FTSE":    ["ftse 100", "ftse"],
    "NIFTY":   ["nifty 50", "nifty"],
    "DAX":     ["dax"],
    "BTC":     ["bitcoin", "btc"],
    "ETH":     ["ethereum", "eth"],
    "USD":     ["us dollar", "usd"],
    "EUR":     ["euro", "eur"],
    "INR":     ["indian rupee", "inr"],
    "RUB":     ["russian ruble", "rub"],
    "CNY":     ["chinese yuan", "cny", "renminbi"],
}

# Zero-shot label -> our EventType enum. We phrase labels as the model would
# describe an article, then map back to the canonical enum value.
ZSC_LABEL_TO_EVENT: dict[str, EventType] = {
    "armed conflict or war":              EventType.WAR,
    "military escalation or skirmish":    EventType.CONFLICT,
    "economic sanctions":                 EventType.SANCTION,
    "election or political vote":         EventType.ELECTION,
    "government policy change":           EventType.POLICY,
    "terrorist attack":                   EventType.TERRORISM,
    "natural disaster":                   EventType.NATURAL_DISASTER,
    "macroeconomic news":                 EventType.ECONOMIC,
    "diplomatic meeting or negotiation":  EventType.DIPLOMATIC,
    "other geopolitical event":           EventType.OTHER,
}

# Severity weight per event type — drives the GTI base score.
EVENT_TYPE_WEIGHT: dict[EventType, float] = {
    EventType.WAR: 1.00,
    EventType.CONFLICT: 0.90,
    EventType.TERRORISM: 0.85,
    EventType.SANCTION: 0.70,
    EventType.NATURAL_DISASTER: 0.55,
    EventType.POLICY: 0.50,
    EventType.ELECTION: 0.45,
    EventType.DIPLOMATIC: 0.40,
    EventType.ECONOMIC: 0.45,
    EventType.OTHER: 0.30,
}

# Words whose presence escalates the GTI regardless of sentiment scores.
TENSION_KEYWORDS = {
    "war", "invasion", "missile", "airstrike", "casualties",
    "nuclear", "embargo", "sanction", "attack", "terror",
    "coup", "crisis", "blockade", "escalation", "retaliation",
}
TENSION_KEYWORD_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in TENSION_KEYWORDS) + r")\b",
    flags=re.IGNORECASE,
)


# ============================================================================
# Result schemas
# ============================================================================

class ExtractedEntities(BaseModel):
    countries: list[str] = Field(default_factory=list)
    persons: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    assets: list[str] = Field(
        default_factory=list,
        description="Detected asset/ticker codes (BRENT, GOLD, BTC, …)",
    )


class SentimentResult(BaseModel):
    label: str = Field(description="positive | neutral | negative")
    score: float = Field(ge=0.0, le=1.0, description="Confidence of the chosen label")
    polarity: float = Field(
        ge=-1.0, le=1.0,
        description="Signed polarity: +score for positive, -score for negative, 0 for neutral",
    )


class EventClassification(BaseModel):
    event_type: EventType
    severity: EventSeverity
    confidence: float = Field(ge=0.0, le=1.0)


class NLPAnalysisResult(BaseModel):
    entities: ExtractedEntities
    sentiment: SentimentResult
    classification: EventClassification
    gti: float = Field(ge=0.0, le=100.0)
    # Names of pipeline stages that errored out and were filled with fallbacks.
    partial_failures: list[str] = Field(default_factory=list)


# ============================================================================
# Exceptions
# ============================================================================

class NLPServiceError(Exception):
    """Base error type for the NLP service."""


class ModelLoadError(NLPServiceError):
    """Raised when one or more underlying models fail to initialise."""


class InvalidInputError(NLPServiceError):
    """Raised when caller-supplied text is empty or otherwise unusable."""


# ============================================================================
# Optional Redis cache wrapper
# ============================================================================

class _RedisCache:
    """Thin async wrapper around redis.asyncio with graceful degradation.

    All errors are swallowed and logged — the cache must never break the
    NLP pipeline. If redis-py isn't installed or the URL is unset, the
    cache is a silent no-op.
    """

    def __init__(self, url: str | None, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._client = None
        if not url:
            return
        try:
            import redis.asyncio as redis  # type: ignore
            self._client = redis.from_url(url, encoding="utf-8", decode_responses=True)
        except ImportError:
            logger.warning("redis package not installed; NLP cache disabled")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Redis init failed (%s); NLP cache disabled", exc)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def get(self, key: str) -> dict[str, Any] | None:
        if not self._client:
            return None
        try:
            raw = await self._client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            logger.warning("Redis GET failed (%s); skipping cache read", exc)
            return None

    async def set(self, key: str, value: dict[str, Any]) -> None:
        if not self._client:
            return
        try:
            await self._client.set(key, json.dumps(value), ex=self._ttl)
        except Exception as exc:
            logger.warning("Redis SET failed (%s); skipping cache write", exc)


# ============================================================================
# Service
# ============================================================================

class NLPService:
    """Loads HuggingFace + spaCy models lazily and exposes a single
    `analyze(text)` entrypoint."""

    def __init__(self) -> None:
        self._spacy_nlp = None
        self._sentiment_pipeline = None
        self._zsc_pipeline = None
        self._load_lock = asyncio.Lock()
        self._loaded = False

        self._cache = _RedisCache(
            url=getattr(settings, "REDIS_URL", None),
            ttl_seconds=getattr(settings, "NLP_CACHE_TTL_SECONDS", 3600),
        )

    # ------------------------------------------------------------------ load
    async def _ensure_loaded(self) -> None:
        """Lazily load every model exactly once per process."""
        if self._loaded:
            return
        async with self._load_lock:
            if self._loaded:           # double-checked under lock
                return
            try:
                await asyncio.to_thread(self._load_models_sync)
            except Exception as exc:
                # Wrap so callers get a typed error.
                raise ModelLoadError(f"NLP model load failed: {exc}") from exc
            self._loaded = True

    def _load_models_sync(self) -> None:
        """Blocking model load. Run via to_thread."""
        # --- spaCy NER ---
        try:
            import spacy
            try:
                self._spacy_nlp = spacy.load(settings.NLP_NER_MODEL)
            except OSError:
                # Model not downloaded — fall back to a blank pipeline so the
                # service still starts. Caller will see empty entities.
                logger.warning(
                    "spaCy model '%s' not found. Run: python -m spacy download %s",
                    settings.NLP_NER_MODEL, settings.NLP_NER_MODEL,
                )
                self._spacy_nlp = spacy.blank("en")
        except ImportError as exc:
            raise ModelLoadError("spaCy is not installed") from exc

        # --- HuggingFace pipelines ---
        try:
            from transformers import pipeline  # type: ignore

            self._sentiment_pipeline = pipeline(
                task="sentiment-analysis",
                model=settings.NLP_FINBERT_MODEL,
                truncation=True,
            )
            self._zsc_pipeline = pipeline(
                task="zero-shot-classification",
                model=settings.NLP_ZSC_MODEL,
            )
        except ImportError as exc:
            raise ModelLoadError("transformers is not installed") from exc

    # ---------------------------------------------------------------- analyze
    async def analyze(self, text: str, *, use_cache: bool = True) -> NLPAnalysisResult:
        """Run the full NLP pipeline against `text` and return a structured result."""
        clean = self._validate_and_clean(text)
        cache_key = self._cache_key(clean)

        if use_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                try:
                    return NLPAnalysisResult.model_validate(cached)
                except Exception as exc:
                    # Cache poisoned with a stale shape — log and recompute.
                    logger.warning("NLP cache miss (validation): %s", exc)

        await self._ensure_loaded()
        result = await asyncio.to_thread(self._analyze_sync, clean)

        if use_cache:
            await self._cache.set(cache_key, result.model_dump(mode="json"))
        return result

    # ----------------------------------------------------------- sync workers
    def _analyze_sync(self, text: str) -> NLPAnalysisResult:
        """All blocking model calls live here. Called from a worker thread."""
        partial: list[str] = []

        # --- entities ---
        try:
            entities = self._extract_entities(text)
        except Exception as exc:
            logger.exception("entity extraction failed: %s", exc)
            entities = ExtractedEntities()
            partial.append("entities")

        # --- sentiment ---
        try:
            sentiment = self._analyze_sentiment(text)
        except Exception as exc:
            logger.exception("sentiment analysis failed: %s", exc)
            sentiment = SentimentResult(label="neutral", score=0.5, polarity=0.0)
            partial.append("sentiment")

        # --- event classification ---
        try:
            classification = self._classify_event(text)
        except Exception as exc:
            logger.exception("event classification failed: %s", exc)
            classification = EventClassification(
                event_type=EventType.OTHER,
                severity=EventSeverity.LOW,
                confidence=0.0,
            )
            partial.append("classification")

        gti = self._compute_gti(
            text=text,
            sentiment=sentiment,
            classification=classification,
            country_count=len(entities.countries),
        )

        return NLPAnalysisResult(
            entities=entities,
            sentiment=sentiment,
            classification=classification,
            gti=gti,
            partial_failures=partial,
        )

    # ---------------------------------------------------------- entity stage
    def _extract_entities(self, text: str) -> ExtractedEntities:
        countries: list[str] = []
        persons: list[str] = []
        orgs: list[str] = []
        events: list[str] = []

        if self._spacy_nlp is not None:
            doc = self._spacy_nlp(text)
            for ent in doc.ents:
                label = ent.label_
                value = ent.text.strip()
                if not value:
                    continue
                if label == "GPE":
                    countries.append(value)
                elif label == "PERSON":
                    persons.append(value)
                elif label == "ORG":
                    orgs.append(value)
                elif label == "EVENT":
                    events.append(value)

        return ExtractedEntities(
            countries=_dedupe_preserve_order(countries),
            persons=_dedupe_preserve_order(persons),
            organizations=_dedupe_preserve_order(orgs),
            events=_dedupe_preserve_order(events),
            assets=self._detect_assets(text),
        )

    @staticmethod
    def _detect_assets(text: str) -> list[str]:
        """Match against the curated asset keyword dictionary, case-insensitively."""
        lowered = text.lower()
        hits: list[str] = []
        for ticker, aliases in ASSET_KEYWORDS.items():
            if any(re.search(rf"\b{re.escape(a)}\b", lowered) for a in aliases):
                hits.append(ticker)
        return hits

    # ------------------------------------------------------- sentiment stage
    def _analyze_sentiment(self, text: str) -> SentimentResult:
        if self._sentiment_pipeline is None:
            raise NLPServiceError("sentiment pipeline not initialised")
        # FinBERT returns: [{"label": "positive|neutral|negative", "score": 0.x}]
        out = self._sentiment_pipeline(text[:MAX_INPUT_CHARS])[0]
        label = str(out["label"]).lower()
        score = float(out["score"])
        polarity = score if label == "positive" else (-score if label == "negative" else 0.0)
        return SentimentResult(label=label, score=score, polarity=polarity)

    # --------------------------------------------------- classification stage
    def _classify_event(self, text: str) -> EventClassification:
        if self._zsc_pipeline is None:
            raise NLPServiceError("zero-shot pipeline not initialised")

        labels = list(ZSC_LABEL_TO_EVENT.keys())
        out = self._zsc_pipeline(
            text[:MAX_INPUT_CHARS],
            candidate_labels=labels,
            multi_label=False,
        )
        # Top label by score.
        top_label = out["labels"][0]
        top_score = float(out["scores"][0])
        event_type = ZSC_LABEL_TO_EVENT.get(top_label, EventType.OTHER)
        severity = self._severity_from_event(event_type, confidence=top_score)
        return EventClassification(
            event_type=event_type, severity=severity, confidence=top_score
        )

    @staticmethod
    def _severity_from_event(event_type: EventType, *, confidence: float) -> EventSeverity:
        """Map (event_type, classification confidence) -> severity bucket."""
        weight = EVENT_TYPE_WEIGHT.get(event_type, 0.3)
        score = weight * confidence
        if score >= 0.75:
            return EventSeverity.CRITICAL
        if score >= 0.55:
            return EventSeverity.HIGH
        if score >= 0.30:
            return EventSeverity.MEDIUM
        return EventSeverity.LOW

    # ------------------------------------------------------------- GTI stage
    @staticmethod
    def _compute_gti(
        *,
        text: str,
        sentiment: SentimentResult,
        classification: EventClassification,
        country_count: int,
    ) -> float:
        """Deterministic 0–100 tension score.

        Components (max contributions):
            base       0–60   from event_type weight × classification confidence
            sentiment  0–20   negative-sentiment magnitude
            breadth    0–10   distinct countries mentioned (capped at 5)
            keywords   0–10   density of explicit-tension keywords (capped)
        """
        weight = EVENT_TYPE_WEIGHT.get(classification.event_type, 0.3)
        base = 60.0 * weight * classification.confidence

        # `polarity` is in [-1, 1]; only negative sentiment escalates GTI.
        sentiment_component = 20.0 * max(-sentiment.polarity, 0.0)

        breadth_component = min(country_count, 5) * 2.0  # 0–10

        keyword_hits = len(TENSION_KEYWORD_RE.findall(text))
        keyword_component = min(keyword_hits, 5) * 2.0   # 0–10

        gti = base + sentiment_component + breadth_component + keyword_component
        return round(max(0.0, min(100.0, gti)), 2)

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _validate_and_clean(text: str) -> str:
        if not isinstance(text, str):
            raise InvalidInputError("text must be a string")
        cleaned = text.strip()
        if not cleaned:
            raise InvalidInputError("text must not be empty")
        # Keep input bounded — protects tokenizers and cache key hashing.
        return cleaned[:MAX_INPUT_CHARS]

    @staticmethod
    def _cache_key(text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"nlp:analyze:{digest}"


# ============================================================================
# Module-level helpers
# ============================================================================

def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        norm = item.strip()
        key = norm.casefold()
        if not norm or key in seen:
            continue
        seen.add(key)
        out.append(norm)
    return out


@lru_cache
def get_nlp_service() -> NLPService:
    """Process-wide singleton. Use as a FastAPI dependency:

        from fastapi import Depends
        from app.services.nlp_service import NLPService, get_nlp_service

        @router.post("/analyze")
        async def analyze(text: str, nlp: NLPService = Depends(get_nlp_service)):
            return await nlp.analyze(text)
    """
    return NLPService()
