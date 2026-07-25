from enum import Enum


class EvidenceCategory(str, Enum):
    """Universal categories for evidence producers."""

    MARKET_BREADTH = "market_breadth"
    MARKET_REGIME = "market_regime"
    OPTION_CHAIN = "option_chain"
    INDICATOR = "indicator"
    PRICE_ACTION = "price_action"
    MARKET_STRUCTURE = "market_structure"
    VOLUME = "volume"
    NEWS = "news"
    RISK = "risk"
    VOLATILITY = "volatility"
    MACRO = "macro"
    BROKER = "broker"
    SYSTEM = "system"
    EVENT = "event"
    TRADE_QUALIFICATION = "trade_qualification"
    PORTFOLIO = "portfolio"
    EXECUTION = "execution"


class EvidenceSignal(str, Enum):
    """Directional signal represented by an evidence item."""

    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"
    UNKNOWN = "unknown"
