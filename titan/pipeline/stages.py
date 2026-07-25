from enum import Enum


class PipelineStage(str, Enum):
    """Ordered stages in the TITAN trade pipeline."""

    PREPARE = "prepare"
    MARKET = "market"
    OPTIONS = "options"
    VOLATILITY = "volatility"
    DEALER = "dealer"
    NEWS = "news"
    EVENTS = "events"
    FUSION = "fusion"
    QUALIFICATION = "qualification"
    RISK = "risk"
    DECISION = "decision"
    PORTFOLIO = "portfolio"
    EXECUTION = "execution"
    OMS = "oms"
    BROKER = "broker"
    COMPLETE = "complete"
    FAILED = "failed"

    @classmethod
    def execution_order(cls) -> tuple["PipelineStage", ...]:
        """Return stages in execution order (excluding COMPLETE and FAILED)."""
        return (
            cls.PREPARE,
            cls.MARKET,
            cls.OPTIONS,
            cls.VOLATILITY,
            cls.DEALER,
            cls.NEWS,
            cls.EVENTS,
            cls.FUSION,
            cls.QUALIFICATION,
            cls.RISK,
            cls.DECISION,
            cls.PORTFOLIO,
            cls.EXECUTION,
            cls.OMS,
            cls.BROKER,
            cls.COMPLETE,
        )

    @classmethod
    def terminal_stages(cls) -> tuple["PipelineStage", ...]:
        return (cls.COMPLETE, cls.FAILED)
