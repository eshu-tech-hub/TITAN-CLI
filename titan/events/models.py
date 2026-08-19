from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from titan.core.evidence import Evidence

# ===========================================================================
# News Intelligence Enums
# ===========================================================================


class NewsSentiment(str, Enum):
    """Sentiment classification for a news article."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class MarketReaction(str, Enum):
    """Expected market reaction to news."""

    LIKELY_BULLISH = "likely_bullish"
    LIKELY_BEARISH = "likely_bearish"
    LIKELY_NEUTRAL = "likely_neutral"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class CredibilityLevel(str, Enum):
    """Source credibility classification."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Type of detected entity in news content."""

    COMPANY = "company"
    INDEX = "index"
    SECTOR = "sector"
    COUNTRY = "country"
    CENTRAL_BANK = "central_bank"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    ECONOMIC_INDICATOR = "economic_indicator"


# ===========================================================================
# News Intelligence Input Models
# ===========================================================================


@dataclass(frozen=True, slots=True)
class NewsArticle:
    """A single news article for intelligence analysis.

    Supplied by the caller — the engine does NOT fetch news.

    Attributes:
        title: Article headline.
        body: Article body text.
        source: Publisher / news source name.
        timestamp: Publication time.
        entities: Optional pre-tagged entity names.
        credibility: Optional pre-assigned credibility level.
        url: Optional article URL.
    """

    title: str
    body: str
    source: str
    timestamp: datetime
    entities: tuple[str, ...] = field(default_factory=tuple)
    credibility: CredibilityLevel = CredibilityLevel.UNKNOWN
    url: str = ""


@dataclass(frozen=True, slots=True)
class ArticleCollection:
    """A collection of news articles for aggregated analysis.

    Attributes:
        articles: News articles to analyse.
        metadata: Optional collection-level metadata.
    """

    articles: tuple[NewsArticle, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)


# ===========================================================================
# News Intelligence Output Models
# ===========================================================================


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """Sentiment analysis result for a single article.

    Attributes:
        sentiment: Classified sentiment.
        score: Sentiment score (-1 to 1).
        confidence: Confidence in assessment (0-1).
        keywords: Key sentiment-bearing phrases.
    """

    sentiment: NewsSentiment = NewsSentiment.UNKNOWN
    score: float = 0.0
    confidence: float = 0.0
    keywords: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class DetectedEntity:
    """An entity detected in news content.

    Attributes:
        entity_type: Classification of the entity.
        name: Entity name as detected.
        relevance: Relevance score (0-1).
    """

    entity_type: EntityType
    name: str
    relevance: float = 1.0


@dataclass(frozen=True, slots=True)
class CredibilityResult:
    """Credibility assessment for a news article.

    Attributes:
        level: Assessed credibility level.
        confidence: Confidence in assessment (0-1).
        reasons: Human-readable reasoning.
    """

    level: CredibilityLevel = CredibilityLevel.UNKNOWN
    confidence: float = 0.0
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class MarketReactionResult:
    """Expected market reaction to news.

    Does NOT recommend trades. Describes likely market response.

    Attributes:
        reaction: Expected market reaction.
        confidence: Confidence in assessment (0-1).
        reasoning: Explanation of the expected reaction.
    """

    reaction: MarketReaction = MarketReaction.UNKNOWN
    confidence: float = 0.0
    reasoning: str = ""


@dataclass(frozen=True, slots=True)
class NewsDecisionContext:
    """Contextual guidance for news-driven decision-making.

    Communicates news environment considerations WITHOUT recommending
    specific actions. All fields describe the news context, not an
    entry or exit signal.

    Attributes:
        high_news_uncertainty: Whether news environment is uncertain.
        conflicting_news: Whether articles conflict with each other.
        institutional_alignment: Whether news aligns with market structure.
        avoid_new_positions: Whether new positions carry elevated risk.
        confidence: Confidence in the context assessment (0-1).
    """

    high_news_uncertainty: bool = False
    conflicting_news: bool = False
    institutional_alignment: bool = False
    avoid_new_positions: bool = False
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class NewsExplanation:
    """Structured explanation for News Intelligence.

    Attributes:
        overall_news: Summary of news flow.
        sentiment: Sentiment assessment explanation.
        entities: Entity detection explanation.
        credibility: Credibility assessment explanation.
        expected_reaction: Expected market reaction explanation.
        decision_context: Decision context explanation.
    """

    overall_news: str = ""
    sentiment: str = ""
    entities: str = ""
    credibility: str = ""
    expected_reaction: str = ""
    decision_context: str = ""


@dataclass(frozen=True, slots=True)
class NewsAnalysis:
    """Combined News Intelligence output.

    Synthesises sentiment, entity, credibility, and reaction analysis
    into a unified institutional assessment of news flow.
    Does NOT recommend trades.

    Attributes:
        articles: Analysed news articles.
        article_sentiments: Per-article sentiment results.
        detected_entities: All detected entities across articles.
        overall_sentiment: Aggregate sentiment assessment.
        overall_credibility: Aggregate credibility assessment.
        overall_reaction: Aggregate market reaction.
        conflicting_news_detected: Whether conflicts exist.
        duplicate_count: Number of duplicates detected.
        decision_context: News-driven decision context.
        confidence: Aggregate confidence (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    articles: tuple[NewsArticle, ...] = field(default_factory=tuple)
    article_sentiments: tuple[SentimentResult, ...] = field(default_factory=tuple)
    detected_entities: tuple[DetectedEntity, ...] = field(default_factory=tuple)
    overall_sentiment: SentimentResult = field(default_factory=SentimentResult)
    overall_credibility: CredibilityResult = field(default_factory=CredibilityResult)
    overall_reaction: MarketReactionResult = field(default_factory=MarketReactionResult)
    conflicting_news_detected: bool = False
    duplicate_count: int = 0
    decision_context: NewsDecisionContext | None = None
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: NewsExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> NewsAnalysis:
        return cls(
            confidence=0.0,
            warnings=("News intelligence data unavailable.",),
        )


class EventImportance(str, Enum):
    """Importance level for scheduled market events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventRisk(str, Enum):
    """Risk level for event-driven market impact."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class AssetClass(str, Enum):
    """Asset classes that can be affected by events."""

    EQUITY = "equity"
    INDEX = "index"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    RATES = "rates"
    CREDIT = "credit"
    BROAD = "broad"


class EconomicEventType(str, Enum):
    """Supported scheduled economic event types."""

    RBI_POLICY = "rbi_policy"
    FOMC = "fomc"
    ECB = "ecb"
    BOJ = "boj"
    GDP = "gdp"
    CPI = "cpi"
    PPI = "ppi"
    PMI = "pmi"
    NFP = "nfp"
    UNEMPLOYMENT = "unemployment"
    INTEREST_RATE_DECISION = "interest_rate_decision"
    HOLIDAY = "holiday"


class CorporateEventType(str, Enum):
    """Supported corporate action event types."""

    QUARTERLY_RESULTS = "quarterly_results"
    DIVIDEND = "dividend"
    BONUS = "bonus"
    SPLIT = "split"
    RIGHTS_ISSUE = "rights_issue"
    BUYBACK = "buyback"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    GUIDANCE = "guidance"
    PROMOTER_ACTIVITY = "promoter_activity"
    BLOCK_DEAL = "block_deal"


@dataclass(frozen=True, slots=True)
class EconomicEvent:
    """A scheduled economic event with consensus expectations.

    Attributes:
        event_type: The type of economic event.
        timestamp: Scheduled event time.
        importance: Market importance level.
        description: Human-readable event description.
        country: Affected country/region.
        previous: Previous value/outcome.
        forecast: Consensus forecast.
        actual: Actual outcome (None if not yet released).
        affected_asset_classes: Asset classes likely affected.
        affected_sectors: Sectors likely affected.
    """

    event_type: EconomicEventType
    timestamp: datetime
    importance: EventImportance = EventImportance.MEDIUM
    description: str = ""
    country: str = ""
    previous: float | None = None
    forecast: float | None = None
    actual: float | None = None
    affected_asset_classes: tuple[AssetClass, ...] = field(
        default_factory=lambda: (AssetClass.BROAD,)
    )
    affected_sectors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CorporateEvent:
    """A scheduled corporate action event.

    Attributes:
        event_type: The type of corporate event.
        timestamp: Scheduled event time.
        company: Company/entity name.
        importance: Market importance level.
        description: Human-readable event description.
        details: Additional event-specific details.
    """

    event_type: CorporateEventType
    timestamp: datetime
    company: str = ""
    importance: EventImportance = EventImportance.MEDIUM
    description: str = ""
    details: str = ""


@dataclass(frozen=True, slots=True)
class EventImpact:
    """Expected market impact from an event.

    Attributes:
        expected_volatility: Expected volatility level (0-1).
        expected_liquidity: Expected liquidity level (0-1).
        expected_gap_risk: Expected gap risk level (0-1).
        affected_asset_class: Primary affected asset class.
        affected_sector: Primary affected sector (empty if broad).
        expected_duration: Expected impact duration description.
    """

    expected_volatility: float = 0.0
    expected_liquidity: float = 0.0
    expected_gap_risk: float = 0.0
    affected_asset_class: AssetClass = AssetClass.BROAD
    affected_sector: str = ""
    expected_duration: str = ""


@dataclass(frozen=True, slots=True)
class EventRiskAssessment:
    """Multi-dimensional event risk assessment.

    Attributes:
        risk_level: Overall risk level.
        gap_risk: Gap risk component.
        volatility_risk: Volatility risk component.
        liquidity_risk: Liquidity risk component.
        confidence: Confidence in the assessment (0-1).
    """

    risk_level: EventRisk = EventRisk.MODERATE
    gap_risk: EventRisk = EventRisk.MODERATE
    volatility_risk: EventRisk = EventRisk.MODERATE
    liquidity_risk: EventRisk = EventRisk.MODERATE
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """Contextual guidance for event-driven decision-making.

    Communicates event environment considerations WITHOUT recommending
    specific actions. All fields describe the event context, not an
    entry or exit signal.

    Attributes:
        avoid_new_positions: Whether new positions carry elevated risk.
        reduce_position_size: Whether existing positions should be reduced.
        expect_high_volatility: Whether elevated volatility is expected.
        expect_gap_open: Whether a gap open is likely.
        allow_intraday_only: Whether only intraday trades are advisable.
        confidence: Confidence in the context assessment (0-1).
    """

    avoid_new_positions: bool = False
    reduce_position_size: bool = False
    expect_high_volatility: bool = False
    expect_gap_open: bool = False
    allow_intraday_only: bool = False
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class EventExplanation:
    """Structured explanation for Event Intelligence.

    Attributes:
        upcoming_events: Summary of upcoming events.
        importance: Importance assessment explanation.
        market_impact: Market impact explanation.
        risk_assessment: Risk assessment explanation.
        trading_implications: Trading implications explanation.
        overall_assessment: Overall assessment explanation.
    """

    upcoming_events: str = ""
    importance: str = ""
    market_impact: str = ""
    risk_assessment: str = ""
    trading_implications: str = ""
    overall_assessment: str = ""


@dataclass(frozen=True, slots=True)
class EventAnalysis:
    """Combined Event Intelligence output.

    Synthesises economic, corporate, impact, and risk analysis into a
    unified institutional assessment of scheduled market events.
    Does NOT recommend trades.

    Attributes:
        economic_events: Analyzed economic events.
        corporate_events: Analyzed corporate events.
        highest_importance: Highest importance level across all events.
        overall_risk: Aggregate risk assessment.
        decision_context: Event-driven decision context.
        confidence: Aggregate confidence (0-1).
        warnings: Non-fatal warnings.
        metadata: Producer context.
        evidence: Evidence for the Intelligence Fusion Engine.
        explanation: Structured human-readable explanation.
    """

    economic_events: tuple[EconomicEvent, ...] = field(default_factory=tuple)
    corporate_events: tuple[CorporateEvent, ...] = field(default_factory=tuple)
    highest_importance: EventImportance = EventImportance.LOW
    overall_risk: EventRisk = EventRisk.LOW
    decision_context: DecisionContext | None = None
    confidence: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evidence: Evidence | None = None
    explanation: EventExplanation | None = None

    @classmethod
    def neutral_placeholder(cls) -> EventAnalysis:
        return cls(
            confidence=0.0,
            warnings=("Event intelligence data unavailable.",),
        )
