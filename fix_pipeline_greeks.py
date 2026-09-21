
path = 'titan/pipeline/pipeline.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def _handle_options(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        \"\"\"Run options intelligence engines.\"\"\"
        result: dict[str, Any] = {}
        snapshot = ctx.metadata.get("option_chain_snapshot")
        if snapshot is None:
            return result"""

replacement = """    def _handle_options(
        self, ctx: PipelineContext, risk_profile: RiskProfile
    ) -> dict[str, Any]:
        \"\"\"Run options intelligence engines.\"\"\"
        result: dict[str, Any] = {}
        snapshot = ctx.metadata.get("option_chain_snapshot")
        if snapshot is None:
            return result
            
        # Black-Scholes Greeks Auto-Calculator Injection
        if snapshot.underlying_price is not None:
            try:
                from titan.options.pricing.black_scholes import calculate_greeks
                from datetime import UTC, datetime
                import dataclasses
                
                spot = snapshot.underlying_price
                time_to_expiry_years = max(0.001, (snapshot.expiry - datetime.now(UTC)).total_seconds() / (365.25 * 86400))
                risk_free_rate = 0.05
                
                new_strikes = []
                for strike in snapshot.strikes:
                    strike_dict = dataclasses.asdict(strike)
                    K = strike.strike_price
                    
                    # Compute Call Greeks if IV is present and delta is missing
                    if strike.call_implied_volatility and strike.call_delta is None:
                        cg = calculate_greeks(spot, K, time_to_expiry_years, strike.call_implied_volatility, risk_free_rate, "CE")
                        strike_dict.update({"call_delta": cg["delta"], "call_gamma": cg["gamma"], "call_theta": cg["theta"], "call_vega": cg["vega"]})
                        
                    # Compute Put Greeks if IV is present and delta is missing
                    if strike.put_implied_volatility and strike.put_delta is None:
                        pg = calculate_greeks(spot, K, time_to_expiry_years, strike.put_implied_volatility, risk_free_rate, "PE")
                        strike_dict.update({"put_delta": pg["delta"], "put_gamma": pg["gamma"], "put_theta": pg["theta"], "put_vega": pg["vega"]})
                        
                    from titan.options.analytics.models import OptionStrikeSnapshot
                    new_strikes.append(OptionStrikeSnapshot(**strike_dict))
                    
                snapshot = dataclasses.replace(snapshot, strikes=tuple(new_strikes))
                ctx.metadata["option_chain_snapshot"] = snapshot
            except Exception as e:
                from titan.core.logger import logger
                logger.warning(f"Failed to auto-calculate Greeks: {e}")"""

content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
