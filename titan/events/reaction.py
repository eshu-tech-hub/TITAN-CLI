"""Market Reaction Analyzer.

Determines expected market reaction to news based on sentiment,
entities, and market structure alignment. Pure analyzer — no
API calls, no broker imports.

Integrates with:
  - News Intelligence Engine
  - Sentiment Analyzer
  - Entity Analyzer
"""

from titan.events.models import (
    DetectedEntity,
    MarketReaction,
    MarketReactionResult,
    NewsArticle,
    NewsSentiment,
    SentimentResult,
)


class MarketReactionAnalyzer:
    """Determine expected market reaction to news.

    Combines article sentiment and detected entities to estimate
    likely market response. Does NOT recommend trades.
    """

    name = "MarketReactionAnalyzer"

    BULLISH_ENTITY_TYPES = frozenset(
        {
            "company",
            "sector",
            "index",
        }
    )

    def analyze(
        self,
        sentiment: SentimentResult,
        entities: tuple[DetectedEntity, ...],
        article: NewsArticle | None = None,
    ) -> MarketReactionResult:
        """Determine expected market reaction.

        Args:
            sentiment: Sentiment analysis result.
            entities: Detected entities in the article.
            article: Optional original article for context.

        Returns:
            MarketReactionResult with reaction classification.
        """
        if sentiment.sentiment is NewsSentiment.UNKNOWN and not entities:
            return MarketReactionResult(
                reaction=MarketReaction.UNKNOWN,
                confidence=0.0,
                reasoning="Insufficient data to determine market reaction.",
            )

        if sentiment.sentiment is NewsSentiment.MIXED:
            return MarketReactionResult(
                reaction=MarketReaction.MIXED,
                confidence=sentiment.confidence * 0.8,
                reasoning="Mixed sentiment suggests uncertain market reaction.",
            )

        has_relevant_entity = any(
            e.entity_type.value in self.BULLISH_ENTITY_TYPES for e in entities
        )

        reaction = self._map_reaction(sentiment.sentiment)
        confidence = sentiment.confidence * (1.1 if has_relevant_entity else 0.9)
        confidence = min(1.0, confidence)

        reasoning = self._build_reasoning(sentiment, entities, has_relevant_entity)

        return MarketReactionResult(
            reaction=reaction,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _map_reaction(self, sentiment: NewsSentiment) -> MarketReaction:
        mapping = {
            NewsSentiment.POSITIVE: MarketReaction.LIKELY_BULLISH,
            NewsSentiment.NEGATIVE: MarketReaction.LIKELY_BEARISH,
            NewsSentiment.NEUTRAL: MarketReaction.LIKELY_NEUTRAL,
            NewsSentiment.MIXED: MarketReaction.MIXED,
        }
        return mapping.get(sentiment, MarketReaction.UNKNOWN)

    def _build_reasoning(
        self,
        sentiment: SentimentResult,
        entities: tuple[DetectedEntity, ...],
        has_relevant_entity: bool,
    ) -> str:
        parts: list[str] = []

        parts.append(f"Sentiment is {sentiment.sentiment.value}.")

        if has_relevant_entity:
            relevant = [
                e for e in entities if e.entity_type.value in self.BULLISH_ENTITY_TYPES
            ]
            names = ", ".join(e.name for e in relevant[:3])
            parts.append(f"Relevant entities: {names}.")

        if sentiment.score > 0.3:
            parts.append("Strong positive signals detected.")
        elif sentiment.score < -0.3:
            parts.append("Strong negative signals detected.")

        return " ".join(parts)

    def analyze_collection(
        self,
        sentiments: tuple[SentimentResult, ...],
        article_entities: tuple[tuple[DetectedEntity, ...], ...],
        articles: tuple[NewsArticle, ...] = (),
    ) -> MarketReactionResult:
        """Determine aggregate market reaction for multiple articles.

        Args:
            sentiments: Per-article sentiment results.
            article_entities: Per-article entity detections.
            articles: Original articles.

        Returns:
            Aggregate MarketReactionResult.
        """
        if not sentiments:
            return MarketReactionResult(
                reaction=MarketReaction.UNKNOWN,
                confidence=0.0,
                reasoning="No articles to analyse.",
            )

        reaction_counts: dict[MarketReaction, int] = {}
        total_confidence = 0.0

        for i, s in enumerate(sentiments):
            entities = article_entities[i] if i < len(article_entities) else ()
            r = self.analyze(s, entities)
            reaction_counts[r.reaction] = reaction_counts.get(r.reaction, 0) + 1
            total_confidence += r.confidence

        if len(sentiments) > 1:
            dominant_reaction = max(
                reaction_counts,
                key=reaction_counts.get,  # type: ignore[arg-type]
            )
            dominant_count = reaction_counts[dominant_reaction]
            total = sum(reaction_counts.values())

            if dominant_count / total <= 0.5:
                return MarketReactionResult(
                    reaction=MarketReaction.MIXED,
                    confidence=total_confidence / len(sentiments) * 0.8,
                    reasoning="Conflicting signals across multiple articles.",
                )
        else:
            dominant_reaction = max(
                reaction_counts,
                key=reaction_counts.get,  # type: ignore[arg-type]
            )

        return MarketReactionResult(
            reaction=dominant_reaction,
            confidence=total_confidence / len(sentiments),
            reasoning=f"Aggregate of {len(sentiments)} article(s).",
        )
