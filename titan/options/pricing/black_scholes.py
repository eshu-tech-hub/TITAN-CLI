import math
from typing import Literal

def _norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def calculate_greeks(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    volatility: float,
    risk_free_rate: float = 0.065,  # RBI 91-day T-Bill rate baseline (~6.5%)
    dividend_yield: float = 0.0,
    option_type: Literal["CE", "PE"] = "CE",
) -> dict[str, float]:
    """Production-hardened Black-Scholes-Merton Greeks calculator.
    
    Returns:
        delta: Sensitivity to 1 pt spot move.
        gamma: Change in delta per 1 pt spot move.
        theta: Daily 1-day calendar decay (INR).
        vega:  Sensitivity to 1% move in implied volatility (INR).
    """
    # Guard against invalid or boundary inputs
    if time_to_expiry_years <= 1e-6 or volatility <= 1e-6 or strike <= 0.0 or spot <= 0.0:
        # Intrinsic value approximation at immediate expiry
        if option_type == "CE":
            delta = 1.0 if spot > strike else 0.0
        else:
            delta = -1.0 if spot < strike else 0.0
        return {"delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    sqrt_t = math.sqrt(time_to_expiry_years)
    vt = volatility * sqrt_t
    df_r = math.exp(-risk_free_rate * time_to_expiry_years)
    df_q = math.exp(-dividend_yield * time_to_expiry_years)

    d1 = (math.log(spot / strike) + (risk_free_rate - dividend_yield + 0.5 * volatility**2) * time_to_expiry_years) / vt
    d2 = d1 - vt

    pdf_d1 = _norm_pdf(d1)
    gamma = (df_q * pdf_d1) / (spot * vt)
    vega = spot * df_q * pdf_d1 * sqrt_t * 0.01

    if option_type == "CE":
        delta = df_q * _norm_cdf(d1)
        theta = (
            -(spot * df_q * pdf_d1 * volatility) / (2.0 * sqrt_t)
            - risk_free_rate * strike * df_r * _norm_cdf(d2)
            + dividend_yield * spot * df_q * _norm_cdf(d1)
        ) / 365.0
    else:
        delta = -df_q * _norm_cdf(-d1)
        theta = (
            -(spot * df_q * pdf_d1 * volatility) / (2.0 * sqrt_t)
            + risk_free_rate * strike * df_r * _norm_cdf(-d2)
            - dividend_yield * spot * df_q * _norm_cdf(-d1)
        ) / 365.0

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
    }