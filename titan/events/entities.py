"""Entity Analyzer.

Detects market-relevant entities in news article content using
pattern matching. Pure analyzer — no API calls, no internet lookups.

Integrates with:
  - News Intelligence Engine
  - Market Reaction Analyzer
"""

import re
from typing import ClassVar

from titan.events.models import DetectedEntity, EntityType, NewsArticle


class EntityAnalyzer:
    """Detect entities in news articles using keyword matching.

    Maintains curated lookup tables for companies, indices, sectors,
    countries, central banks, commodities, currencies, and economic
    indicators. No external data sources required.
    """

    name = "EntityAnalyzer"

    COMPANIES = frozenset(
        {
            "reliance",
            "tcs",
            "infosys",
            "infy",
            "hdfc",
            "icici",
            "sbi",
            "state bank",
            "bharti",
            "airtel",
            "itc",
            "wipro",
            "hcl",
            "tech mahindra",
            "m&m",
            "mahindra",
            "maruti",
            "suzuki",
            "tata motors",
            "tata steel",
            "jsw",
            "adani",
            "bajaj",
            "asian paints",
            "nestle",
            "hul",
            "hindustan unilever",
            "sun pharma",
            "dr reddy",
            "cipla",
            "kotak",
            "axis bank",
            "yes bank",
            "vedanta",
            "coal india",
            "ongc",
            "oil",
            "ntpc",
            "power grid",
            "l&t",
            "larsen",
            "titan",
            "dmart",
            "avenue supermarts",
            "zomato",
            "paytm",
            "policybazaar",
            "nykaa",
            "google",
            "apple",
            "microsoft",
            "amazon",
            "meta",
            "tesla",
            "nvidia",
            "jpmorgan",
            "goldman sachs",
            "berkshire",
            "hathaway",
            "warren buffett",
        }
    )

    INDICES = frozenset(
        {
            "nifty",
            "nifty50",
            "nifty 50",
            "sensex",
            "banknifty",
            "nifty bank",
            "nifty it",
            "nifty pharma",
            "nifty auto",
            "nifty fmcg",
            "nifty metal",
            "nifty energy",
            "nifty realty",
            "nifty midcap",
            "nifty smallcap",
            "nifty next 50",
            "nifty 500",
            "dow jones",
            "dow",
            "s&p 500",
            "sp 500",
            "nasdaq",
            "ftse",
            "dax",
            "nikkei",
            "hangseng",
            "sse",
            "csi 300",
            "euro stoxx 50",
        }
    )

    SECTORS = frozenset(
        {
            "banking",
            "it",
            "pharma",
            "auto",
            "automobile",
            "fmcg",
            "metal",
            "mining",
            "energy",
            "oil & gas",
            "realty",
            "real estate",
            "infrastructure",
            "telecom",
            "media",
            "entertainment",
            "healthcare",
            "insurance",
            "financial services",
            "consumption",
            "consumer goods",
            "retail",
            "e-commerce",
            "technology",
            "software",
            "manufacturing",
            "industrial",
            "chemicals",
            "cement",
            "construction",
            "power",
            "utilities",
            "logistics",
            "shipping",
            "aviation",
            "hospitality",
            "tourism",
            "education",
        }
    )

    COUNTRIES = frozenset(
        {
            "india",
            "united states",
            "us",
            "usa",
            "china",
            "japan",
            "germany",
            "uk",
            "united kingdom",
            "france",
            "europe",
            "european union",
            "eu",
            "russia",
            "brazil",
            "australia",
            "canada",
            "saudi arabia",
            "uae",
            "south korea",
            "singapore",
            "hong kong",
            "switzerland",
            "netherlands",
            "italy",
            "spain",
        }
    )

    CENTRAL_BANKS = frozenset(
        {
            "rbi",
            "reserve bank of india",
            "federal reserve",
            "fed",
            "fomc",
            "ecb",
            "european central bank",
            "bank of japan",
            "boj",
            "bank of england",
            "boe",
            "people's bank of china",
            "pboc",
            "swiss national bank",
            "snb",
            "reserve bank of australia",
            "rba",
        }
    )

    COMMODITIES = frozenset(
        {
            "crude",
            "oil",
            "brent",
            "wti",
            "natural gas",
            "gold",
            "silver",
            "copper",
            "aluminium",
            "zinc",
            "lead",
            "nickel",
            "steel",
            "iron ore",
            "cotton",
            "sugar",
            "wheat",
            "corn",
            "soybean",
            "coffee",
            "tea",
            "rubber",
            "palm oil",
            "platinum",
            "palladium",
            "uranium",
        }
    )

    CURRENCIES = frozenset(
        {
            "usdinr",
            "dollar-rupee",
            "dollar rupee",
            "euro",
            "dollar",
            "pound",
            "yen",
            "rupee",
            "yuan",
            "won",
            "franc",
            "eurusd",
            "gbpusd",
            "usdjpy",
            "inr",
            "usd",
            "eur",
            "gbp",
            "jpy",
            "cny",
            "chf",
            "aud",
            "cad",
        }
    )

    INDICATORS = frozenset(
        {
            "gdp",
            "gross domestic product",
            "cpi",
            "inflation",
            "consumer price index",
            "ppi",
            "producer price index",
            "pmi",
            "purchasing managers index",
            "nfp",
            "non-farm payroll",
            "unemployment",
            "jobless claims",
            "interest rate",
            "repo rate",
            "reverse repo",
            "fiscal deficit",
            "current account deficit",
            "industrial production",
            "ipp",
            "retail sales",
            "iip",
        }
    )

    ENTITY_MAP: ClassVar[list[tuple[frozenset[str], EntityType]]] = [
        (CENTRAL_BANKS, EntityType.CENTRAL_BANK),
        (INDICES, EntityType.INDEX),
        (COMPANIES, EntityType.COMPANY),
        (SECTORS, EntityType.SECTOR),
        (COMMODITIES, EntityType.COMMODITY),
        (CURRENCIES, EntityType.CURRENCY),
        (INDICATORS, EntityType.ECONOMIC_INDICATOR),
        (COUNTRIES, EntityType.COUNTRY),
    ]

    def analyze(self, article: NewsArticle) -> tuple[DetectedEntity, ...]:
        """Detect entities in a news article.

        Args:
            article: News article to analyse.

        Returns:
            Tuple of detected entities, sorted by relevance descending.
        """
        text = f"{article.title} {article.body}".lower()

        detected: dict[str, DetectedEntity] = {}

        included = {e.lower() for e in article.entities}
        for entity_name in included:
            self._add_entity(detected, entity_name)

        words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9&.]*", text))
        multi_words = self._multi_word_phrases(text)

        candidates = words | multi_words

        for token in candidates:
            token_lower = token.lower().strip()
            if token_lower in detected:
                continue
            for keyword_set, entity_type in self.ENTITY_MAP:
                if token_lower in keyword_set:
                    self._add_entity(detected, token_lower, entity_type)
                    break

        if article.entities and not detected:
            for entity_name in article.entities:
                self._add_entity(detected, entity_name)

        result = sorted(detected.values(), key=lambda e: e.relevance, reverse=True)

        return tuple(result)

    def _add_entity(
        self,
        detected: dict[str, DetectedEntity],
        name: str,
        entity_type: EntityType | None = None,
    ) -> None:
        if name in detected:
            return
        if entity_type is None:
            for keyword_set, etype in self.ENTITY_MAP:
                if name in keyword_set:
                    entity_type = etype
                    break
        if entity_type is None:
            entity_type = EntityType.COMPANY

        detected[name] = DetectedEntity(
            entity_type=entity_type,
            name=name.title() if name.islower() else name,
            relevance=1.0,
        )

    def _multi_word_phrases(self, text: str) -> set[str]:
        phrases: set[str] = set()

        multi_word_entries: list[str] = []
        for name in self.COMPANIES:
            if " " in name:
                multi_word_entries.append(name)
        multi_word_entries.extend(name for name in self.INDICES if " " in name)
        multi_word_entries.extend(name for name in self.CENTRAL_BANKS if " " in name)
        multi_word_entries.extend(name for name in self.COUNTRIES if " " in name)
        multi_word_entries.extend(name for name in self.INDICATORS if " " in name)

        for phrase in multi_word_entries:
            if phrase in text:
                phrases.add(phrase)

        return phrases
