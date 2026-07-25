from typing import TypedDict, Any


class TradeRecommendation(TypedDict):
    action: str
    option_symbol: str
    strike: float
    entry_price: float
    target: float
    stop_loss: float
    rationale: str


class AIDecisionSynthesizer:
    """Unifies technicals and options data to produce trade recommendations."""

    def evaluate_technicals(self, sma: float, ema: float, rsi: float) -> str:
        """Returns a bias string based on basic technical indicators."""
        if rsi > 60 and ema > sma:
            return "BULLISH"
        elif rsi < 40 and ema < sma:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def select_contract(
        self, bias: str, chain: dict[str, list[Any]], atm_strike: float
    ) -> Any:
        """Selects the optimal CE or PE contract based on the bias."""
        if bias == "NEUTRAL":
            return None

        opt_type = "CE" if bias == "BULLISH" else "PE"
        contracts = chain.get(opt_type, [])

        # Optimal selection: find the ATM contract
        for contract in contracts:
            if contract.strike == atm_strike:
                return contract

        # Fallback to the closest contract if exact ATM is missing
        if contracts:
            return min(contracts, key=lambda c: abs(c.strike - atm_strike))

        return None

    def generate_trade(
        self,
        spot_price: float,
        technicals: dict[str, float],
        option_chain: dict[str, list[Any]],
    ) -> TradeRecommendation | None:
        """Synthesizes inputs and generates a trade recommendation."""
        sma = technicals.get("sma", 0.0)
        ema = technicals.get("ema", 0.0)
        rsi = technicals.get("rsi", 50.0)

        bias = self.evaluate_technicals(sma, ema, rsi)
        if bias == "NEUTRAL":
            return None

        # We need atm_strike, let's assume it's part of the chain metadata or we can calculate it
        # Since we just have the chain, let's get the median strike or pass it down.
        # But wait, the function signature is defined by the prompt. Let's find ATM by taking closest strike to spot_price

        all_contracts = option_chain.get("CE", []) + option_chain.get("PE", [])
        if not all_contracts:
            return None

        atm_strike = min(all_contracts, key=lambda c: abs(c.strike - spot_price)).strike

        contract = self.select_contract(bias, option_chain, atm_strike)
        if not contract:
            return None

        # Fixed risk-reward simulation (since we don't have real market prices for the option,
        # we'll simulate entry based on a hypothetical premium calculation or just arbitrary numbers for structure).
        # In a real engine, entry_price would be fetched from LTP.
        simulated_entry = 100.0

        if bias == "BULLISH":
            target = simulated_entry * 1.5  # 50% gain
            stop_loss = simulated_entry * 0.75  # 25% loss
            action = "BUY"
        else:
            target = simulated_entry * 1.5
            stop_loss = simulated_entry * 0.75
            action = "BUY"  # We buy PE

        rationale = f"Bias is {bias} (RSI={rsi:.1f}, EMA/SMA cross). Selected {contract.symbol} ATM strike."

        return {
            "action": action,
            "option_symbol": contract.symbol,
            "strike": contract.strike,
            "entry_price": simulated_entry,
            "target": target,
            "stop_loss": stop_loss,
            "rationale": rationale,
        }
