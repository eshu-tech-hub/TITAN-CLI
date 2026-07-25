"""Sentiment Analyzer.

Analyses supplied news article text and classifies sentiment.
Pure analyzer — no API calls, no NLP libraries.

Integrates with:
  - News Intelligence Engine
  - Market Reaction Analyzer
"""

import re

from titan.events.models import NewsArticle, NewsSentiment, SentimentResult


class SentimentAnalyzer:
    """Analyse news article sentiment using keyword-based classification.

    Uses curated positive/negative keyword lists to determine article
    sentiment. No external NLP libraries, no API calls.
    """

    name = "SentimentAnalyzer"

    POSITIVE_KEYWORDS = frozenset(
        {
            "upgrade",
            "upgraded",
            "outperform",
            "beat",
            "beats",
            "beating",
            "bullish",
            "positive",
            "growth",
            "surge",
            "surges",
            "surged",
            "rally",
            "rallies",
            "rallied",
            "gain",
            "gains",
            "gained",
            "profit",
            "profits",
            "profitable",
            "record",
            "strong",
            "stronger",
            "strongest",
            "recovery",
            "recover",
            "recovered",
            "expansion",
            "expand",
            "expanding",
            "boost",
            "boosts",
            "breakthrough",
            "innovation",
            "launch",
            "launches",
            "approval",
            "approved",
            "clearance",
            "greenlight",
            "dividend",
            "buyback",
            "bonus",
            "split",
            "partnership",
            "collaboration",
            "alliance",
            "rising",
            "soar",
            "soars",
            "soared",
            "boom",
            "optimistic",
            "confidence",
            "confident",
            "momentum",
            "accelerate",
            "accelerating",
            "outlook",
            "guidance",
            "raised",
        }
    )

    NEGATIVE_KEYWORDS = frozenset(
        {
            "downgrade",
            "downgraded",
            "underperform",
            "miss",
            "misses",
            "bearish",
            "negative",
            "decline",
            "declines",
            "declined",
            "fall",
            "falls",
            "fell",
            "fallen",
            "drop",
            "drops",
            "dropped",
            "loss",
            "losses",
            "losing",
            "cut",
            "cuts",
            "cutting",
            "weak",
            "weaker",
            "weakest",
            "slowdown",
            "slowing",
            "recession",
            "recessionary",
            "crisis",
            "crash",
            "bankruptcy",
            "default",
            "defaults",
            "defaulted",
            "layoff",
            "layoffs",
            "firing",
            "fired",
            "investigation",
            "probe",
            "scrutiny",
            "penalty",
            "fine",
            "fines",
            "sanction",
            "sanctions",
            "volatile",
            "volatility",
            "uncertainty",
            "uncertain",
            "downside",
            "risk",
            "risks",
            "risky",
            "debt",
            "deficit",
            "liability",
            "liabilities",
            "fraud",
            "scam",
            "manipulation",
            "warning",
            "warn",
            "warns",
            "warned",
            "selloff",
            "sell-off",
            "plunge",
            "plunges",
            "plunged",
            "tumble",
            "tumbles",
            "tumbled",
            "slump",
            "slumps",
            "lowered",
            "dismal",
            "gloomy",
            "pessimistic",
            "impairment",
            "write-off",
            "writeoff",
            "restructuring",
        }
    )

    def analyze(self, article: NewsArticle) -> SentimentResult:
        """Analyse sentiment for a single article.

        Args:
            article: News article to analyse.

        Returns:
            SentimentResult with classification and confidence.
        """
        text = f"{article.title} {article.body}".lower()
        words = set(re.findall(r"[a-z]+(?:[-'][a-z]+)*", text))

        positive_count = sum(1 for w in words if w in self.POSITIVE_KEYWORDS)
        negative_count = sum(1 for w in words if w in self.NEGATIVE_KEYWORDS)
        total = positive_count + negative_count

        if total == 0:
            return SentimentResult(
                sentiment=NewsSentiment.NEUTRAL,
                score=0.0,
                confidence=0.3,
                keywords=(),
            )

        score = (positive_count - negative_count) / max(1, total)
        confidence = min(1.0, total / 10)

        if positive_count > 0 and negative_count > 0:
            ratio = positive_count / max(1, negative_count)
            if 1 / 3 <= ratio <= 3:
                sentiment = NewsSentiment.MIXED
            elif positive_count > negative_count:
                sentiment = NewsSentiment.POSITIVE
            else:
                sentiment = NewsSentiment.NEGATIVE
        elif positive_count > 0:
            sentiment = NewsSentiment.POSITIVE
        elif negative_count > 0:
            sentiment = NewsSentiment.NEGATIVE
        else:
            sentiment = NewsSentiment.NEUTRAL

        keywords = tuple(
            w
            for w in words
            if w in self.POSITIVE_KEYWORDS or w in self.NEGATIVE_KEYWORDS
        )[:5]

        return SentimentResult(
            sentiment=sentiment,
            score=score,
            confidence=confidence,
            keywords=keywords,
        )
