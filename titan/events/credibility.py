"""Credibility Analyzer.

Assesses news source credibility using supplied source metadata.
Pure analyzer — no API calls, no internet lookups.

Integrates with:
  - News Intelligence Engine
"""

import re

from titan.events.models import (
    CredibilityLevel,
    CredibilityResult,
    NewsArticle,
)


def _source_match(source: str, keyword: str) -> bool:
    """Match source against a keyword using word boundaries."""
    return bool(re.search(rf"\b{re.escape(keyword)}\b", source))


class CredibilityAnalyzer:
    """Assess news article credibility from source metadata.

    Uses curated source credibility tiers and article characteristics.
    No external lookups — relies entirely on supplied metadata.
    """

    name = "CredibilityAnalyzer"

    HIGH_CREDIBILITY_SOURCES = frozenset(
        {
            "reuters",
            "bloomberg",
            "financial times",
            "ft",
            "wall street journal",
            "wsj",
            "the economist",
            "barron's",
            "barrons",
            "mint",
            "livemint",
            "economic times",
            "et",
            "business standard",
            "business line",
            "the hindu business",
            "cnbc",
            "cnbc tv18",
            "moneycontrol",
            "ndtv profit",
            "bq prime",
            "bloombergquint",
        }
    )

    MEDIUM_CREDIBILITY_SOURCES = frozenset(
        {
            "times of india",
            "toi",
            "hindustan times",
            "the hindu",
            "indian express",
            "the print",
            "ndtv",
            "news18",
            "india today",
            "outlook",
            "firstpost",
            "scroll",
            "the wire",
            "forbes india",
            "inc42",
            "yourstory",
            "entrackr",
            "techcircle",
            "vccircle",
            "zee business",
            "zeebiz",
            "investing.com",
            "marketwatch",
        }
    )

    LOW_CREDIBILITY_SOURCES = frozenset(
        {
            "twitter",
            "x",
            "reddit",
            "facebook",
            "telegram",
            "whatsapp",
            "youtube",
            "blog",
            "wordpress",
            "medium",
            "unknown",
            "anonymous",
        }
    )

    def analyze(
        self,
        article: NewsArticle,
    ) -> CredibilityResult:
        """Assess credibility of a single article.

        Args:
            article: News article to assess.

        Returns:
            CredibilityResult with level and confidence.
        """
        source = article.source.strip().lower()

        if article.credibility is not CredibilityLevel.UNKNOWN:
            if article.credibility is CredibilityLevel.HIGH:
                return CredibilityResult(
                    level=CredibilityLevel.HIGH,
                    confidence=0.8,
                    reasons=("Credibility explicitly set to HIGH.",),
                )
            if article.credibility is CredibilityLevel.LOW:
                return CredibilityResult(
                    level=CredibilityLevel.LOW,
                    confidence=0.8,
                    reasons=("Credibility explicitly set to LOW.",),
                )
            if article.credibility is CredibilityLevel.MEDIUM:
                return CredibilityResult(
                    level=CredibilityLevel.MEDIUM,
                    confidence=0.7,
                    reasons=("Credibility explicitly set to MEDIUM.",),
                )

        if any(_source_match(source, s) for s in self.HIGH_CREDIBILITY_SOURCES):
            return CredibilityResult(
                level=CredibilityLevel.HIGH,
                confidence=0.8,
                reasons=(f"Source '{article.source}' is a high-credibility outlet.",),
            )

        if any(_source_match(source, s) for s in self.MEDIUM_CREDIBILITY_SOURCES):
            return CredibilityResult(
                level=CredibilityLevel.MEDIUM,
                confidence=0.6,
                reasons=(f"Source '{article.source}' is a medium-credibility outlet.",),
            )

        if any(_source_match(source, s) for s in self.LOW_CREDIBILITY_SOURCES):
            return CredibilityResult(
                level=CredibilityLevel.LOW,
                confidence=0.7,
                reasons=(f"Source '{article.source}' is a low-credibility outlet.",),
            )

        has_title = bool(article.title.strip())
        has_body = bool(article.body.strip())
        confidence = 0.3
        if has_title and has_body:
            confidence = 0.4

        return CredibilityResult(
            level=CredibilityLevel.UNKNOWN,
            confidence=confidence,
            reasons=(f"Source '{article.source}' is not in credibility database.",),
        )

    def analyze_collection(
        self,
        articles: tuple[NewsArticle, ...],
    ) -> tuple[CredibilityResult, ...]:
        """Assess credibility for a collection of articles.

        Args:
            articles: Articles to assess.

        Returns:
            Tuple of credibility results, one per article.
        """
        return tuple(self.analyze(a) for a in articles)
