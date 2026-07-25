"""News Intelligence Engine — Orchestrator.

Provides institutional-grade news analysis from supplied articles.
Synthesises sentiment, entity detection, credibility, and market
reaction into a unified assessment.

Pure orchestrator — no API calls, no news ingestion, no LLM.

Integrates with:
  - Evidence Engine
  - Intelligence Fusion Engine
"""

from typing import Any

from titan.core.evidence import (
    Confidence,
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
    Score,
)

from titan.events.credibility import CredibilityAnalyzer
from titan.events.entities import EntityAnalyzer
from titan.events.models import (
    ArticleCollection,
    CredibilityLevel,
    CredibilityResult,
    DetectedEntity,
    MarketReaction,
    NewsAnalysis,
    NewsArticle,
    NewsDecisionContext,
    NewsExplanation,
    NewsSentiment,
    SentimentResult,
)
from titan.events.reaction import MarketReactionAnalyzer
from titan.events.sentiment import SentimentAnalyzer

POSITIVE_SCORE = 65.0
NEGATIVE_SCORE = 35.0
NEUTRAL_SCORE = 50.0

CONFIDENCE_HIGH = 0.7
CONFIDENCE_MODERATE = 0.5
CONFIDENCE_LOW = 0.3

UNCERTAINTY_THRESHOLD = 0.4
CONFLICT_THRESHOLD = 0.5
DUP_TITLE_SIMILARITY = 0.8


class NewsIntelligenceAnalyzer:
    """Orchestrate News Intelligence.

    Consumes NewsArticle(s) and delegates to SentimentAnalyzer,
    EntityAnalyzer, CredibilityAnalyzer, and MarketReactionAnalyzer
    to produce a unified institutional assessment of news flow.
    Pure orchestrator — does not fetch or scrape news.
    """

    name = "NewsIntelligenceAnalyzer"

    def __init__(
        self,
        sentiment_analyzer: SentimentAnalyzer | None = None,
        entity_analyzer: EntityAnalyzer | None = None,
        credibility_analyzer: CredibilityAnalyzer | None = None,
        reaction_analyzer: MarketReactionAnalyzer | None = None,
    ) -> None:
        self._sentiment = sentiment_analyzer or SentimentAnalyzer()
        self._entities = entity_analyzer or EntityAnalyzer()
        self._credibility = credibility_analyzer or CredibilityAnalyzer()
        self._reaction = reaction_analyzer or MarketReactionAnalyzer()

    def analyze(
        self,
        collection: ArticleCollection,
    ) -> NewsAnalysis:
        """Execute news intelligence analysis.

        Args:
            collection: Article collection to analyse.

        Returns:
            Combined NewsAnalysis.
        """
        articles = collection.articles
        if not articles:
            return self._empty_analysis("No articles provided for analysis.")

        sentiments = tuple(self._sentiment.analyze(a) for a in articles)
        entities_list = tuple(self._entities.analyze(a) for a in articles)
        credibilities = tuple(self._credibility.analyze(a) for a in articles)

        credibility_result = self._aggregate_credibility(credibilities)
        sentiment_result = self._aggregate_sentiment(sentiments, credibilities)
        all_entities = self._merge_entities(entities_list)
        reaction = self._reaction.analyze_collection(
            sentiments, entities_list, articles
        )
        duplicate_count = self._count_duplicates(articles)
        conflicting = self._detect_conflicts(sentiments, credibilities)
        decision = self._decision_context(
            sentiment_result, credibility_result, conflicting, reaction
        )

        confidence = self._calculate_confidence(sentiments, credibilities, reaction)

        analysis = NewsAnalysis(
            articles=articles,
            article_sentiments=sentiments,
            detected_entities=all_entities,
            overall_sentiment=sentiment_result,
            overall_credibility=credibility_result,
            overall_reaction=reaction,
            conflicting_news_detected=conflicting,
            duplicate_count=duplicate_count,
            decision_context=decision,
            confidence=confidence,
            warnings=self._combine_warnings(articles, sentiments, credibilities),
            metadata=self._metadata(articles, sentiments, credibilities),
        )

        evidence = self._to_evidence(analysis)
        explanation = self._explanation(
            analysis,
            sentiment_result,
            all_entities,
            credibility_result,
            reaction,
            decision,
        )

        object.__setattr__(analysis, "evidence", evidence)
        object.__setattr__(analysis, "explanation", explanation)

        return analysis

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate_sentiment(
        self,
        sentiments: tuple[SentimentResult, ...],
        credibilities: tuple[CredibilityResult, ...],
    ) -> SentimentResult:
        if not sentiments:
            return SentimentResult()

        weighted_score = 0.0
        total_weight = 0.0
        sentiment_counts: dict[NewsSentiment, int] = {}

        for i, s in enumerate(sentiments):
            weight = 1.0
            if i < len(credibilities):
                cred = credibilities[i]
                if cred.level is CredibilityLevel.HIGH:
                    weight = 1.5
                elif cred.level is CredibilityLevel.LOW:
                    weight = 0.5
            weighted_score += s.score * weight
            total_weight += weight
            sentiment_counts[s.sentiment] = sentiment_counts.get(s.sentiment, 0) + 1

        avg_score = weighted_score / total_weight if total_weight > 0 else 0.0

        if not sentiment_counts:
            return SentimentResult()

        dominant = max(sentiment_counts, key=sentiment_counts.get)  # type: ignore[arg-type]

        if len(sentiments) > 1:
            total = sum(sentiment_counts.values())
            dominant_count = sentiment_counts[dominant]
            if dominant_count / total <= CONFLICT_THRESHOLD:
                if avg_score > 0.1:
                    dominant = NewsSentiment.MIXED
                elif avg_score < -0.1:
                    dominant = NewsSentiment.MIXED
                else:
                    dominant = NewsSentiment.MIXED

        avg_confidence = sum(s.confidence for s in sentiments) / len(sentiments)

        return SentimentResult(
            sentiment=dominant,
            score=avg_score,
            confidence=avg_confidence,
        )

    def _aggregate_credibility(
        self,
        credibilities: tuple[CredibilityResult, ...],
    ) -> CredibilityResult:
        if not credibilities:
            return CredibilityResult()

        levels = [c.level for c in credibilities]
        if all(lv is CredibilityLevel.HIGH for lv in levels):
            level = CredibilityLevel.HIGH
        elif all(lv is CredibilityLevel.LOW for lv in levels):
            level = CredibilityLevel.LOW
        elif CredibilityLevel.HIGH in levels:
            level = CredibilityLevel.MEDIUM
        else:
            level = CredibilityLevel.UNKNOWN

        avg_confidence = sum(c.confidence for c in credibilities) / len(credibilities)

        reasons = [f"Aggregate across {len(credibilities)} source(s)."]

        return CredibilityResult(
            level=level,
            confidence=avg_confidence,
            reasons=tuple(reasons),
        )

    def _merge_entities(
        self,
        entities_list: tuple[tuple[DetectedEntity, ...], ...],
    ) -> tuple[DetectedEntity, ...]:
        seen: dict[str, DetectedEntity] = {}
        for entities in entities_list:
            for entity in entities:
                key = f"{entity.entity_type.value}:{entity.name.lower()}"
                if key not in seen:
                    seen[key] = entity
        return tuple(
            sorted(
                seen.values(),
                key=lambda e: e.relevance,
                reverse=True,
            )
        )

    def _count_duplicates(
        self,
        articles: tuple[NewsArticle, ...],
    ) -> int:
        count = 0
        for i in range(len(articles)):
            for j in range(i + 1, len(articles)):
                t1 = articles[i].title.lower().strip()
                t2 = articles[j].title.lower().strip()
                if self._title_similar(t1, t2):
                    count += 1
        return count

    def _title_similar(self, t1: str, t2: str) -> bool:
        if t1 == t2:
            return True
        words1 = set(t1.split())
        words2 = set(t2.split())
        if not words1 or not words2:
            return False
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) >= DUP_TITLE_SIMILARITY

    def _detect_conflicts(
        self,
        sentiments: tuple[SentimentResult, ...],
        credibilities: tuple[CredibilityResult, ...],
    ) -> bool:
        if len(sentiments) < 2:
            return False

        positive = sum(1 for s in sentiments if s.sentiment is NewsSentiment.POSITIVE)
        negative = sum(1 for s in sentiments if s.sentiment is NewsSentiment.NEGATIVE)

        if positive > 0 and negative > 0:
            total = positive + negative
            if positive / total >= 0.3 and negative / total >= 0.3:
                return True

        return False

    # ------------------------------------------------------------------
    # Decision context
    # ------------------------------------------------------------------

    def _decision_context(
        self,
        sentiment: SentimentResult,
        credibility: CredibilityResult,
        conflicting: bool,
        reaction: Any,
    ) -> NewsDecisionContext:
        low_cred = credibility.level in (
            CredibilityLevel.LOW,
            CredibilityLevel.UNKNOWN,
        )
        low_conf = credibility.confidence < CONFIDENCE_MODERATE
        high_uncertainty = (
            sentiment.sentiment is NewsSentiment.MIXED
            or sentiment.sentiment is NewsSentiment.UNKNOWN
            or conflicting
            or (low_cred and low_conf)
        )

        avoid_new = high_uncertainty and reaction.reaction in (
            MarketReaction.LIKELY_BEARISH,
            MarketReaction.MIXED,
        )

        return NewsDecisionContext(
            high_news_uncertainty=high_uncertainty,
            conflicting_news=conflicting,
            institutional_alignment=(
                credibility.level is CredibilityLevel.HIGH and not conflicting
            ),
            avoid_new_positions=avoid_new,
            confidence=credibility.confidence,
        )

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        sentiments: tuple[SentimentResult, ...],
        credibilities: tuple[CredibilityResult, ...],
        reaction: Any,
    ) -> float:
        confidences: list[float] = []
        weights: list[float] = []

        if sentiments:
            avg_sent_conf = sum(s.confidence for s in sentiments) / len(sentiments)
            confidences.append(avg_sent_conf)
            weights.append(0.35)

        if credibilities:
            avg_cred_conf = sum(c.confidence for c in credibilities) / len(
                credibilities
            )
            confidences.append(avg_cred_conf)
            weights.append(0.35)

        if reaction.confidence > 0:
            confidences.append(reaction.confidence)
            weights.append(0.30)

        if not confidences:
            return 0.0

        total = sum(c * w for c, w in zip(confidences, weights))
        total_w = sum(weights)
        return total / total_w if total_w > 0 else 0.0

    # ------------------------------------------------------------------
    # Warnings
    # ------------------------------------------------------------------

    def _combine_warnings(
        self,
        articles: tuple[NewsArticle, ...],
        sentiments: tuple[SentimentResult, ...],
        credibilities: tuple[CredibilityResult, ...],
    ) -> tuple[str, ...]:
        combined: list[str] = []

        if len(articles) < 2:
            combined.append("Single article — limited context for aggregation.")

        low_cred_count = sum(
            1
            for c in credibilities
            if c.level in (CredibilityLevel.LOW, CredibilityLevel.UNKNOWN)
        )
        if low_cred_count > 0:
            combined.append(
                f"{low_cred_count} article(s) have low or unknown credibility."
            )

        low_sent_conf = sum(1 for s in sentiments if s.confidence < CONFIDENCE_LOW)
        if low_sent_conf > 0:
            combined.append(
                f"{low_sent_conf} article(s) have low sentiment confidence."
            )

        return tuple(combined)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _metadata(
        self,
        articles: tuple[NewsArticle, ...],
        sentiments: tuple[SentimentResult, ...],
        credibilities: tuple[CredibilityResult, ...],
    ) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "article_count": len(articles),
            "sources": list(set(a.source for a in articles)),
        }

    # ------------------------------------------------------------------
    # Evidence generation
    # ------------------------------------------------------------------

    def _evidence_signal(
        self,
        sentiment: SentimentResult,
        reaction: Any,
    ) -> EvidenceSignal:
        if reaction.reaction is MarketReaction.LIKELY_BULLISH:
            return EvidenceSignal.BULLISH
        if reaction.reaction is MarketReaction.LIKELY_BEARISH:
            return EvidenceSignal.BEARISH
        if sentiment.sentiment is NewsSentiment.MIXED:
            return EvidenceSignal.NEUTRAL
        return EvidenceSignal.NEUTRAL

    def _evidence_score(
        self,
        analysis: NewsAnalysis,
    ) -> float:
        base = NEUTRAL_SCORE

        if analysis.overall_reaction.reaction is MarketReaction.LIKELY_BULLISH:
            base = POSITIVE_SCORE
        elif analysis.overall_reaction.reaction is MarketReaction.LIKELY_BEARISH:
            base = NEGATIVE_SCORE

        adj = 0.0
        if analysis.confidence >= CONFIDENCE_HIGH:
            adj += 5.0
        elif analysis.confidence >= CONFIDENCE_MODERATE:
            adj += 3.0

        return max(0.0, min(100.0, base + adj))

    def _evidence_reasons(
        self,
        analysis: NewsAnalysis,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        article_count = len(analysis.articles)
        reasons.append(f"{article_count} article(s) analysed.")

        sent = analysis.overall_sentiment.sentiment.value
        reasons.append(f"Overall sentiment: {sent}.")

        cred = analysis.overall_credibility.level.value
        reasons.append(f"Overall credibility: {cred}.")

        if analysis.conflicting_news_detected:
            reasons.append("Conflicting news signals detected.")

        return tuple(reasons)

    def _to_evidence(
        self,
        analysis: NewsAnalysis,
    ) -> Evidence:
        signal = self._evidence_signal(
            analysis.overall_sentiment,
            analysis.overall_reaction,
        )
        score = self._evidence_score(analysis)
        confidence = analysis.confidence

        return Evidence(
            source="News Intelligence",
            category=EvidenceCategory.NEWS,
            signal=signal,
            score=Score(score),
            confidence=Confidence(confidence),
            weight=1.0,
            reasons=self._evidence_reasons(analysis),
            warnings=analysis.warnings,
            metadata={
                "analyzer": self.name,
                "article_count": len(analysis.articles),
                "overall_sentiment": analysis.overall_sentiment.sentiment.value,
                "overall_credibility": analysis.overall_credibility.level.value,
                "overall_reaction": analysis.overall_reaction.reaction.value,
                "conflicting_news": analysis.conflicting_news_detected,
                "duplicate_count": analysis.duplicate_count,
            },
        )

    # ------------------------------------------------------------------
    # Explanation generation
    # ------------------------------------------------------------------

    def _explanation(
        self,
        analysis: NewsAnalysis,
        sentiment: SentimentResult,
        entities: tuple[DetectedEntity, ...],
        credibility: CredibilityResult,
        reaction: Any,
        context: NewsDecisionContext | None,
    ) -> NewsExplanation:
        return NewsExplanation(
            overall_news=self._overall_section(analysis),
            sentiment=self._sentiment_section(sentiment),
            entities=self._entities_section(entities),
            credibility=self._credibility_section(credibility),
            expected_reaction=self._reaction_section(reaction),
            decision_context=self._context_section(context),
        )

    def _overall_section(self, analysis: NewsAnalysis) -> str:
        article_count = len(analysis.articles)
        return (
            f"Overall News: {article_count} article(s) analysed. "
            f"{'Conflicting signals detected.' if analysis.conflicting_news_detected else 'No conflicting signals.'} "
            f"{analysis.duplicate_count} duplicate(s) found."
        )

    def _sentiment_section(self, sentiment: SentimentResult) -> str:
        return (
            f"Sentiment: Overall sentiment is {sentiment.sentiment.value} "
            f"(score: {sentiment.score:.2f}, confidence: {sentiment.confidence:.2f})."
        )

    def _entities_section(
        self,
        entities: tuple[DetectedEntity, ...],
    ) -> str:
        parts: list[str] = ["Entities:"]
        if entities:
            names = ", ".join(f"{e.name} ({e.entity_type.value})" for e in entities[:8])
            parts.append(names)
        else:
            parts.append("No market-relevant entities detected.")
        return " ".join(parts)

    def _credibility_section(self, credibility: CredibilityResult) -> str:
        return (
            f"Credibility: Overall credibility is {credibility.level.value} "
            f"(confidence: {credibility.confidence:.2f})."
        )

    def _reaction_section(self, reaction: Any) -> str:
        return (
            f"Expected Market Reaction: {reaction.reaction.value} "
            f"(confidence: {reaction.confidence:.2f})."
        )

    def _context_section(
        self,
        context: NewsDecisionContext | None,
    ) -> str:
        parts: list[str] = ["Decision Context:"]

        if context is None:
            parts.append("No news-driven context available.")
            return " ".join(parts)

        if context.high_news_uncertainty:
            parts.append("High news uncertainty.")
        if context.conflicting_news:
            parts.append("Conflicting news signals.")
        if context.institutional_alignment:
            parts.append("News aligns with known institutional positioning.")
        if context.avoid_new_positions:
            parts.append("Avoid new positions due to news uncertainty.")

        if not any(
            [
                context.high_news_uncertainty,
                context.conflicting_news,
                context.institutional_alignment,
                context.avoid_new_positions,
            ]
        ):
            parts.append("No significant news-driven restrictions.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Empty / fallback analysis
    # ------------------------------------------------------------------

    def _empty_analysis(self, reason: str) -> NewsAnalysis:
        analysis = NewsAnalysis.neutral_placeholder()
        object.__setattr__(analysis, "warnings", (reason,))
        explanation = NewsExplanation(
            overall_news="News assessment unavailable: no articles provided.",
            sentiment="Sentiment assessment unavailable: no articles provided.",
            entities="Entity detection unavailable: no articles provided.",
            credibility="Credibility assessment unavailable: no articles provided.",
            expected_reaction="Market reaction unavailable: no articles provided.",
            decision_context="Decision Context: News intelligence data is unavailable.",
        )
        object.__setattr__(analysis, "explanation", explanation)
        return analysis
