"""Tests for News Intelligence Engine (M4.1.2)."""

from datetime import UTC, datetime

import pytest

from titan.core.evidence import (
    Evidence,
    EvidenceCategory,
    EvidenceSignal,
)
from titan.events import (
    ArticleCollection,
    CredibilityAnalyzer,
    CredibilityLevel,
    CredibilityResult,
    DetectedEntity,
    EntityAnalyzer,
    EntityType,
    MarketReaction,
    MarketReactionAnalyzer,
    MarketReactionResult,
    NewsAnalysis,
    NewsArticle,
    NewsDecisionContext,
    NewsExplanation,
    NewsIntelligenceAnalyzer,
    NewsSentiment,
    SentimentAnalyzer,
    SentimentResult,
)

NOW = datetime.now(UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_article(
    title: str = "Test Headline",
    body: str = "Test body content.",
    source: str = "Reuters",
    entities: tuple[str, ...] = (),
    credibility: CredibilityLevel = CredibilityLevel.UNKNOWN,
) -> NewsArticle:
    return NewsArticle(
        title=title,
        body=body,
        source=source,
        timestamp=NOW,
        entities=entities,
        credibility=credibility,
    )


def make_collection(
    articles: tuple[NewsArticle, ...] = (),
) -> ArticleCollection:
    return ArticleCollection(articles=articles)


# ===========================================================================
# SentimentAnalyzer Tests
# ===========================================================================


class TestSentimentAnalyzer:
    def test_positive_sentiment(self) -> None:
        analyzer = SentimentAnalyzer()
        article = make_article(
            title="Company reports strong profit growth",
            body="The company beat estimates with record quarterly profits.",
        )
        result = analyzer.analyze(article)
        assert result.sentiment is NewsSentiment.POSITIVE
        assert result.score > 0
        assert result.confidence > 0

    def test_negative_sentiment(self) -> None:
        analyzer = SentimentAnalyzer()
        article = make_article(
            title="Markets crash on recession fears",
            body="Global markets fell sharply amid recession fears and uncertainty.",
        )
        result = analyzer.analyze(article)
        assert result.sentiment is NewsSentiment.NEGATIVE
        assert result.score < 0

    def test_neutral_sentiment(self) -> None:
        analyzer = SentimentAnalyzer()
        article = make_article(
            title="Company announces new office location",
            body="The company announced a new office in Mumbai.",
        )
        result = analyzer.analyze(article)
        assert result.sentiment is NewsSentiment.NEUTRAL
        assert result.score == 0.0

    def test_mixed_sentiment(self) -> None:
        analyzer = SentimentAnalyzer()
        article = make_article(
            title="Mixed signals in market",
            body="Profits surged but recession fears and weak outlook caused concern with rising costs and declining demand.",
        )
        result = analyzer.analyze(article)
        assert result.sentiment is NewsSentiment.MIXED
        assert result.confidence > 0

    def test_unknown_sentiment_empty(self) -> None:
        analyzer = SentimentAnalyzer()
        article = make_article(title="", body="")
        result = analyzer.analyze(article)
        assert result.sentiment is NewsSentiment.NEUTRAL
        assert result.score == 0.0

    def test_keywords_detected(self) -> None:
        analyzer = SentimentAnalyzer()
        article = make_article(
            title="Bullish rally",
            body="Strong growth and positive outlook.",
        )
        result = analyzer.analyze(article)
        assert len(result.keywords) > 0

    def test_confidence_scales(self) -> None:
        analyzer = SentimentAnalyzer()
        short = make_article(
            title="Great",
            body="Good.",
        )
        long = make_article(
            title="Strong growth positive outlook recovery",
            body="Rally surge gain profit beat upgrade expansion boost.",
        )
        short_result = analyzer.analyze(short)
        long_result = analyzer.analyze(long)
        assert long_result.confidence >= short_result.confidence


# ===========================================================================
# EntityAnalyzer Tests
# ===========================================================================


class TestEntityAnalyzer:
    def test_detect_company(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="Reliance reports quarterly results",
            body="Reliance Industries announced strong profits.",
        )
        entities = analyzer.analyze(article)
        assert any(e.name.lower() == "reliance" for e in entities)
        company_entities = [e for e in entities if e.entity_type is EntityType.COMPANY]
        assert len(company_entities) > 0

    def test_detect_index(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="Nifty hits new all-time high",
            body="The Nifty 50 index reached record levels today.",
        )
        entities = analyzer.analyze(article)
        index_entities = [e for e in entities if e.entity_type is EntityType.INDEX]
        assert len(index_entities) > 0

    def test_detect_central_bank(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="RBI keeps repo rate unchanged",
            body="The Reserve Bank of India maintained the status quo.",
        )
        entities = analyzer.analyze(article)
        cb = [e for e in entities if e.entity_type is EntityType.CENTRAL_BANK]
        assert len(cb) > 0

    def test_detect_commodity(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="Gold prices surge",
            body="Gold and silver rallied on safe-haven demand.",
        )
        entities = analyzer.analyze(article)
        commodities = [e for e in entities if e.entity_type is EntityType.COMMODITY]
        assert len(commodities) > 0

    def test_detect_currency(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="Rupee weakens against dollar",
            body="USDINR moved higher in early trade.",
        )
        entities = analyzer.analyze(article)
        currencies = [e for e in entities if e.entity_type is EntityType.CURRENCY]
        assert len(currencies) > 0

    def test_detect_sector(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="Banking stocks rally",
            body="The banking sector led the rally today.",
        )
        entities = analyzer.analyze(article)
        sectors = [e for e in entities if e.entity_type is EntityType.SECTOR]
        assert len(sectors) > 0

    def test_detect_country(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="India GDP growth accelerates",
            body="India's economy grew faster than expected.",
        )
        entities = analyzer.analyze(article)
        countries = [e for e in entities if e.entity_type is EntityType.COUNTRY]
        assert len(countries) > 0

    def test_detect_indicator(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="CPI inflation rises",
            body="Consumer price index data showed rising inflation.",
        )
        entities = analyzer.analyze(article)
        indicators = [
            e for e in entities if e.entity_type is EntityType.ECONOMIC_INDICATOR
        ]
        assert len(indicators) > 0

    def test_no_entities(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="Weather is nice today",
            body="The weather is pleasant with clear skies.",
        )
        entities = analyzer.analyze(article)
        assert len(entities) == 0

    def test_entities_from_tag(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="Company update",
            body="General text about performance.",
            entities=("RELIANCE", "NIFTY"),
        )
        entities = analyzer.analyze(article)
        assert len(entities) >= 2

    def test_no_duplicate_entities(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="Nifty Nifty Nifty",
            body="Nifty index nifty.",
            entities=("NIFTY",),
        )
        entities = analyzer.analyze(article)
        nifty = [e for e in entities if e.name.lower() == "nifty"]
        assert len(nifty) == 1

    def test_entity_types(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="RBI cuts repo rate, Nifty rallies, Reliance gains",
            body="Gold also surged on the news.",
        )
        entities = analyzer.analyze(article)
        types = {e.entity_type for e in entities}
        assert EntityType.CENTRAL_BANK in types
        assert EntityType.COMMODITY in types


# ===========================================================================
# CredibilityAnalyzer Tests
# ===========================================================================


class TestCredibilityAnalyzer:
    def test_high_credibility_source(self) -> None:
        analyzer = CredibilityAnalyzer()
        article = make_article(source="Reuters")
        result = analyzer.analyze(article)
        assert result.level is CredibilityLevel.HIGH
        assert result.confidence > 0.5

    def test_medium_credibility_source(self) -> None:
        analyzer = CredibilityAnalyzer()
        article = make_article(source="Times of India")
        result = analyzer.analyze(article)
        assert result.level is CredibilityLevel.MEDIUM

    def test_low_credibility_source(self) -> None:
        analyzer = CredibilityAnalyzer()
        article = make_article(source="Twitter")
        result = analyzer.analyze(article)
        assert result.level is CredibilityLevel.LOW

    def test_unknown_credibility_source(self) -> None:
        analyzer = CredibilityAnalyzer()
        article = make_article(source="SomeRandomBlog")
        result = analyzer.analyze(article)
        assert result.level is CredibilityLevel.UNKNOWN

    def test_explicit_high_credibility(self) -> None:
        analyzer = CredibilityAnalyzer()
        article = make_article(
            source="Twitter",
            credibility=CredibilityLevel.HIGH,
        )
        result = analyzer.analyze(article)
        assert result.level is CredibilityLevel.HIGH

    def test_explicit_low_credibility(self) -> None:
        analyzer = CredibilityAnalyzer()
        article = make_article(
            source="Reuters",
            credibility=CredibilityLevel.LOW,
        )
        result = analyzer.analyze(article)
        assert result.level is CredibilityLevel.LOW

    def test_collection_analysis(self) -> None:
        analyzer = CredibilityAnalyzer()
        articles = (
            make_article(source="Reuters"),
            make_article(source="Twitter"),
        )
        results = analyzer.analyze_collection(articles)
        assert len(results) == 2
        assert results[0].level is CredibilityLevel.HIGH
        assert results[1].level is CredibilityLevel.LOW

    def test_reasons_included(self) -> None:
        analyzer = CredibilityAnalyzer()
        article = make_article(source="Bloomberg")
        result = analyzer.analyze(article)
        assert len(result.reasons) > 0


# ===========================================================================
# MarketReactionAnalyzer Tests
# ===========================================================================


class TestMarketReactionAnalyzer:
    def test_positive_reaction(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiment = SentimentResult(
            sentiment=NewsSentiment.POSITIVE,
            score=0.5,
            confidence=0.7,
        )
        result = analyzer.analyze(sentiment, ())
        assert result.reaction is MarketReaction.LIKELY_BULLISH
        assert result.confidence > 0

    def test_negative_reaction(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiment = SentimentResult(
            sentiment=NewsSentiment.NEGATIVE,
            score=-0.5,
            confidence=0.7,
        )
        result = analyzer.analyze(sentiment, ())
        assert result.reaction is MarketReaction.LIKELY_BEARISH

    def test_neutral_reaction(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiment = SentimentResult(
            sentiment=NewsSentiment.NEUTRAL,
            score=0.0,
            confidence=0.5,
        )
        result = analyzer.analyze(sentiment, ())
        assert result.reaction is MarketReaction.LIKELY_NEUTRAL

    def test_mixed_reaction(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiment = SentimentResult(
            sentiment=NewsSentiment.MIXED,
            score=0.0,
            confidence=0.6,
        )
        result = analyzer.analyze(sentiment, ())
        assert result.reaction is MarketReaction.MIXED

    def test_unknown_reaction(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiment = SentimentResult(
            sentiment=NewsSentiment.UNKNOWN,
            score=0.0,
            confidence=0.0,
        )
        result = analyzer.analyze(sentiment, ())
        assert result.reaction is MarketReaction.UNKNOWN

    def test_relevant_entity_boosts_confidence(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiment = SentimentResult(
            sentiment=NewsSentiment.POSITIVE,
            score=0.5,
            confidence=0.5,
        )
        entities = (
            DetectedEntity(
                entity_type=EntityType.COMPANY,
                name="Reliance",
                relevance=1.0,
            ),
        )
        result = analyzer.analyze(sentiment, entities)
        assert result.confidence > 0.5

    def test_reasoning_included(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiment = SentimentResult(
            sentiment=NewsSentiment.POSITIVE,
            score=0.6,
            confidence=0.8,
        )
        result = analyzer.analyze(sentiment, ())
        assert result.reasoning != ""

    def test_collection_unanimous(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiments = (
            SentimentResult(
                sentiment=NewsSentiment.POSITIVE, score=0.5, confidence=0.7
            ),
            SentimentResult(
                sentiment=NewsSentiment.POSITIVE, score=0.4, confidence=0.6
            ),
        )
        result = analyzer.analyze_collection(sentiments, ((), ()))
        assert result.reaction is MarketReaction.LIKELY_BULLISH

    def test_collection_conflicting(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiments = (
            SentimentResult(
                sentiment=NewsSentiment.POSITIVE, score=0.5, confidence=0.7
            ),
            SentimentResult(
                sentiment=NewsSentiment.NEGATIVE, score=-0.5, confidence=0.7
            ),
        )
        result = analyzer.analyze_collection(sentiments, ((), ()))
        assert result.reaction is MarketReaction.MIXED

    def test_collection_empty(self) -> None:
        analyzer = MarketReactionAnalyzer()
        result = analyzer.analyze_collection((), ())
        assert result.reaction is MarketReaction.UNKNOWN
        assert result.confidence == 0.0


# ===========================================================================
# NewsIntelligenceAnalyzer Tests
# ===========================================================================


class TestNewsIntelligenceAnalyzer:
    def test_no_inputs(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        collection = make_collection()
        result = analyzer.analyze(collection)
        assert result.confidence == 0.0
        assert "No articles provided" in result.warnings[0]

    def test_single_article(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Strong growth reported",
            body="The company reported record profits and strong outlook.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert len(result.articles) == 1
        assert result.confidence > 0

    def test_multiple_articles(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(title="Markets rally", body="Positive momentum continues."),
            make_article(title="Economy grows", body="GDP growth accelerates."),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert len(result.articles) == 2

    def test_positive_news_flow(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Bullish rally in markets",
                body="Strong gains and positive outlook for growth.",
            ),
            make_article(
                title="Company profits surge",
                body="Record profits and optimistic guidance boost confidence.",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.overall_sentiment.sentiment is NewsSentiment.POSITIVE

    def test_negative_news_flow(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Markets crash on weak data",
                body="Global markets fell sharply amid recession fears.",
            ),
            make_article(
                title="Recession warning issued",
                body="Economists warn of downturn risk and uncertainty.",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.overall_sentiment.sentiment is NewsSentiment.NEGATIVE

    def test_mixed_news_flow(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Markets rally on strong data",
                body="Positive GDP growth boosts confidence.",
            ),
            make_article(
                title="Recession fears persist",
                body="Weak outlook and rising uncertainty concern investors.",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.overall_sentiment.sentiment is NewsSentiment.MIXED

    def test_conflicting_news_detected(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Strong growth continues",
                body="Positive outlook and rising profits.",
            ),
            make_article(
                title="Major downturn expected",
                body="Recession fears and declining earnings.",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.conflicting_news_detected is True

    def test_duplicate_detection(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(title="Markets rally on strong data"),
            make_article(title="Markets rally on strong data"),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.duplicate_count > 0

    def test_no_duplicates(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(title="Markets rally today"),
            make_article(title="Economy shows growth"),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.duplicate_count == 0

    def test_credibility_aggregation_high(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Market update",
                body="Some text.",
                source="Reuters",
            ),
            make_article(
                title="Economy update",
                body="More text.",
                source="Bloomberg",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.overall_credibility.level is CredibilityLevel.HIGH

    def test_credibility_aggregation_mixed(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Article 1",
                body="Body 1.",
                source="Reuters",
            ),
            make_article(
                title="Article 2",
                body="Body 2.",
                source="Twitter",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.overall_credibility.level is CredibilityLevel.MEDIUM

    def test_entities_detected_across_articles(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Reliance results",
                body="Reliance Industries announced strong profits.",
            ),
            make_article(
                title="Nifty rallies",
                body="The Nifty index hit a new high.",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert len(result.detected_entities) >= 2

    def test_evidence_generated(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test article",
            body="Test body content.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert result.evidence is not None
        assert isinstance(result.evidence, Evidence)

    def test_evidence_category(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test article",
            body="Test body content.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert result.evidence is not None
        assert result.evidence.category is EvidenceCategory.NEWS

    def test_evidence_source(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test article",
            body="Test body content.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert result.evidence is not None
        assert result.evidence.source == "News Intelligence"

    def test_evidence_signal_positive(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Strong growth",
                body="Positive outlook and rising profits.",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.BULLISH

    def test_evidence_signal_negative(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Markets crash",
                body="Recession fears and declining markets.",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.BEARISH

    def test_evidence_signal_neutral(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Company announces new office",
            body="The company opened a new branch.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert result.evidence is not None
        assert result.evidence.signal is EvidenceSignal.NEUTRAL

    def test_evidence_score(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test article",
            body="Test body content.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert result.evidence is not None
        assert 0 <= float(result.evidence.score) <= 100

    def test_evidence_reasons(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test article",
            body="Test body content.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert result.evidence is not None
        assert len(result.evidence.reasons) >= 2

    def test_explanation_generated(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test article",
            body="Test body content.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert result.explanation is not None
        assert isinstance(result.explanation, NewsExplanation)

    def test_explanation_sections(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test article",
            body="Test body content.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert result.explanation is not None
        assert result.explanation.overall_news != ""
        assert result.explanation.sentiment != ""
        assert result.explanation.entities != ""
        assert result.explanation.credibility != ""
        assert result.explanation.expected_reaction != ""
        assert result.explanation.decision_context != ""

    def test_decision_context_high_uncertainty(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Markets rally",
                body="Strong growth and positive outlook.",
                source="Twitter",
            ),
            make_article(
                title="Recession warning",
                body="Economic downturn and weak data.",
                source="Unknown",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.decision_context is not None
        assert result.decision_context.high_news_uncertainty is True

    def test_decision_context_conflicting(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Strong growth",
                body="Positive outlook and rising profits.",
            ),
            make_article(
                title="Major downturn",
                body="Recession fears and declining earnings.",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.decision_context is not None
        assert result.decision_context.conflicting_news is True

    def test_decision_context_institutional_alignment(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Market update",
            body="Some text about markets.",
            source="Reuters",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert result.decision_context is not None
        assert result.decision_context.institutional_alignment is True

    def test_warnings_single_article(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test",
            body="Test body.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert any("Single article" in w for w in result.warnings)

    def test_warnings_low_credibility(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test",
            body="Test body.",
            source="Twitter",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert any("low or unknown" in w for w in result.warnings)

    def test_metadata_present(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        article = make_article(
            title="Test",
            body="Test body.",
        )
        result = analyzer.analyze(make_collection(articles=(article,)))
        assert "analyzer" in result.metadata
        assert result.metadata["analyzer"] == "NewsIntelligenceAnalyzer"
        assert result.metadata["article_count"] == 1

    def test_neutral_placeholder(self) -> None:
        placeholder = NewsAnalysis.neutral_placeholder()
        assert placeholder.confidence == 0.0
        assert "unavailable" in placeholder.warnings[0]

    def test_empty_analysis(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        result = analyzer.analyze(make_collection())
        assert result.explanation is not None
        assert "no articles provided" in result.explanation.overall_news.lower()


# ===========================================================================
# Validation Tests
# ===========================================================================


class TestValidation:
    def test_news_analysis_frozen(self) -> None:
        analysis = NewsAnalysis()
        with pytest.raises(AttributeError):
            analysis.confidence = 0.5  # type: ignore[misc]

    def test_news_article_frozen(self) -> None:
        article = make_article()
        with pytest.raises(AttributeError):
            article.title = "New Title"  # type: ignore[misc]

    def test_sentiment_result_frozen(self) -> None:
        result = SentimentResult()
        with pytest.raises(AttributeError):
            result.score = 0.5  # type: ignore[misc]

    def test_detected_entity_frozen(self) -> None:
        entity = DetectedEntity(entity_type=EntityType.COMPANY, name="Reliance")
        with pytest.raises(AttributeError):
            entity.name = "TCS"  # type: ignore[misc]

    def test_credibility_result_frozen(self) -> None:
        result = CredibilityResult()
        with pytest.raises(AttributeError):
            result.level = CredibilityLevel.HIGH  # type: ignore[misc]

    def test_market_reaction_result_frozen(self) -> None:
        result = MarketReactionResult()
        with pytest.raises(AttributeError):
            result.reaction = MarketReaction.LIKELY_BULLISH  # type: ignore[misc]

    def test_news_decision_context_frozen(self) -> None:
        ctx = NewsDecisionContext()
        with pytest.raises(AttributeError):
            ctx.confidence = 0.5  # type: ignore[misc]

    def test_news_explanation_frozen(self) -> None:
        exp = NewsExplanation()
        with pytest.raises(AttributeError):
            exp.overall_news = "test"  # type: ignore[misc]

    def test_article_collection_frozen(self) -> None:
        col = make_collection()
        with pytest.raises(AttributeError):
            col.articles = ()  # type: ignore[misc]

    def test_news_article_defaults(self) -> None:
        article = make_article()
        assert article.entities == ()
        assert article.credibility is CredibilityLevel.UNKNOWN
        assert article.url == ""

    def test_sentiment_result_defaults(self) -> None:
        result = SentimentResult()
        assert result.sentiment is NewsSentiment.UNKNOWN
        assert result.score == 0.0
        assert result.confidence == 0.0
        assert result.keywords == ()

    def test_credibility_result_defaults(self) -> None:
        result = CredibilityResult()
        assert result.level is CredibilityLevel.UNKNOWN
        assert result.confidence == 0.0

    def test_market_reaction_result_defaults(self) -> None:
        result = MarketReactionResult()
        assert result.reaction is MarketReaction.UNKNOWN
        assert result.confidence == 0.0

    def test_news_decision_context_defaults(self) -> None:
        ctx = NewsDecisionContext()
        assert ctx.high_news_uncertainty is False
        assert ctx.conflicting_news is False
        assert ctx.institutional_alignment is False
        assert ctx.avoid_new_positions is False
        assert ctx.confidence == 0.0

    def test_news_analysis_defaults(self) -> None:
        analysis = NewsAnalysis()
        assert analysis.articles == ()
        assert analysis.article_sentiments == ()
        assert analysis.detected_entities == ()
        assert analysis.conflicting_news_detected is False
        assert analysis.duplicate_count == 0
        assert analysis.decision_context is None
        assert analysis.confidence == 0.0
        assert analysis.evidence is None
        assert analysis.explanation is None


# ===========================================================================
# Edge Case Tests
# ===========================================================================


class TestEdgeCases:
    def test_article_with_url(self) -> None:
        article = NewsArticle(
            title="Test",
            body="Body",
            source="Reuters",
            timestamp=NOW,
            url="https://example.com/article",
        )
        assert article.url == "https://example.com/article"

    def test_article_with_entities(self) -> None:
        article = make_article(entities=("NIFTY", "RELIANCE"))
        assert "NIFTY" in article.entities
        assert "RELIANCE" in article.entities

    def test_explicit_credibility_medium(self) -> None:
        article = make_article(
            source="Twitter",
            credibility=CredibilityLevel.MEDIUM,
        )
        result = CredibilityAnalyzer().analyze(article)
        assert result.level is CredibilityLevel.MEDIUM

    def test_credibility_source_partial_match(self) -> None:
        analyzer = CredibilityAnalyzer()
        article = make_article(source="Bloomberg Terminal")
        result = analyzer.analyze(article)
        assert result.level is CredibilityLevel.HIGH

    def test_market_reaction_entity_confidence_boost(self) -> None:
        analyzer = MarketReactionAnalyzer()
        sentiment = SentimentResult(
            sentiment=NewsSentiment.POSITIVE,
            score=0.3,
            confidence=0.5,
        )
        entities = (
            DetectedEntity(EntityType.COMPANY, "Reliance"),
            DetectedEntity(EntityType.INDEX, "Nifty"),
        )
        no_entity = analyzer.analyze(sentiment, ())
        with_entity = analyzer.analyze(sentiment, entities)
        assert with_entity.confidence >= no_entity.confidence

    def test_sentiment_with_punctuation(self) -> None:
        analyzer = SentimentAnalyzer()
        article = make_article(
            title="Markets rally! Strong growth?",
            body="Record profits - positive outlook!",
        )
        result = analyzer.analyze(article)
        assert result.sentiment is NewsSentiment.POSITIVE

    def test_duplicate_by_similar_title(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(title="Markets Rally on Strong Economic Data"),
            make_article(title="Markets Rally on Strong Economic Data Today"),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        assert result.duplicate_count > 0

    def test_multi_word_entity(self) -> None:
        analyzer = EntityAnalyzer()
        article = make_article(
            title="Reserve Bank of India keeps rates steady",
            body="The central bank maintained status quo.",
        )
        entities = analyzer.analyze(article)
        cb = [e for e in entities if e.entity_type is EntityType.CENTRAL_BANK]
        assert len(cb) > 0

    def test_entity_dedup_across_articles(self) -> None:
        analyzer = NewsIntelligenceAnalyzer()
        articles = (
            make_article(
                title="Reliance results",
                body="Reliance Industries reported profits.",
            ),
            make_article(
                title="Reliance expansion",
                body="Reliance announced new investments.",
            ),
        )
        result = analyzer.analyze(make_collection(articles=articles))
        reliance = [e for e in result.detected_entities if e.name.lower() == "reliance"]
        assert len(reliance) == 1
