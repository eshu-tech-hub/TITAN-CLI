from dataclasses import dataclass
from typing import Any


@dataclass
class OptionContract:
    symbol: str
    token: str
    strike: float
    option_type: str  # 'CE' or 'PE'
    expiry: str


class OptionChainManager:
    """Manages the filtering and mapping of option chains."""

    def fetch_and_filter(
        self, scrip_data: list[dict[str, Any]], underlying_symbol: str
    ) -> list[OptionContract]:
        """Filters scrip master data for OPTIDX and specific underlying symbol."""
        contracts = []
        for item in scrip_data:
            if (
                item.get("instrumenttype") == "OPTIDX"
                and item.get("name") == underlying_symbol
            ):
                try:
                    strike = float(item.get("strike", 0))
                    # Usually "CE" or "PE" is inferred from symbol or explicitly available
                    symbol = item.get("symbol", "")
                    opt_type = (
                        "CE"
                        if "CE" in symbol.upper()
                        else "PE"
                        if "PE" in symbol.upper()
                        else "UNKNOWN"
                    )

                    if opt_type != "UNKNOWN":
                        contracts.append(
                            OptionContract(
                                symbol=symbol,
                                token=str(item.get("token", "")),
                                strike=strike,
                                option_type=opt_type,
                                expiry=item.get("expiry", ""),
                            )
                        )
                except (ValueError, TypeError):
                    continue
        return contracts

    def get_atm_strike(self, spot_price: float, strike_gap: float) -> float:
        """Rounds the spot price to the nearest strike gap to find the ATM strike."""
        if strike_gap <= 0:
            raise ValueError("Strike gap must be strictly positive.")
        return round(spot_price / strike_gap) * strike_gap

    def get_option_chain(
        self,
        spot_price: float,
        strike_gap: float,
        distance: int,
        scrip_data: list[dict[str, Any]],
    ) -> dict[str, list[OptionContract]]:
        """Returns a structured dictionary of Calls and Puts clustered around the ATM strike."""
        atm_strike = self.get_atm_strike(spot_price, strike_gap)

        # Calculate strike ranges based on distance
        # e.g., if ATM is 20000, gap is 50, distance is 2 -> strikes: 19900, 19950, 20000, 20050, 20100
        min_strike = atm_strike - (strike_gap * distance)
        max_strike = atm_strike + (strike_gap * distance)

        # We need to deduce underlying symbol from scrip_data ideally, but here we scan all OPTIDX
        # or we can just filter all matching the strike range if they are OPTIDX.
        # Since underlying_symbol is not passed, let's assume the scrip_data passed is already filtered,
        # or we just grab matching strikes.

        # But wait, fetch_and_filter takes underlying_symbol. Let's just find matches.
        # Actually, let's just parse the scrip_data assuming it represents the target instrument.

        calls = []
        puts = []

        for item in scrip_data:
            if item.get("instrumenttype") == "OPTIDX":
                strike = float(item.get("strike", -1))
                if min_strike <= strike <= max_strike:
                    symbol = item.get("symbol", "")
                    opt_type = (
                        "CE"
                        if "CE" in symbol.upper()
                        else "PE"
                        if "PE" in symbol.upper()
                        else "UNKNOWN"
                    )
                    contract = OptionContract(
                        symbol=symbol,
                        token=str(item.get("token", "")),
                        strike=strike,
                        option_type=opt_type,
                        expiry=item.get("expiry", ""),
                    )

                    if opt_type == "CE":
                        calls.append(contract)
                    elif opt_type == "PE":
                        puts.append(contract)

        # Sort by strike
        calls.sort(key=lambda c: c.strike)
        puts.sort(key=lambda p: p.strike)

        return {"CE": calls, "PE": puts}
