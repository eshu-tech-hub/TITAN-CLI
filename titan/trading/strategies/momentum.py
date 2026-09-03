from dataclasses import dataclass

from titan.market.series import MarketDataSeries
from titan.trading.strategies.base import SignalType, Strategy, TradeSignal


@dataclass
class MomentumStrategy(Strategy):
    """Momentum strategy using fast/slow EMAs and RSI."""
    
    fast_period: int = 9
    slow_period: int = 21
    rsi_period: int = 14
    stop_loss_pct: float = 0.015
    take_profit_pct: float = 0.03
    
    def _calculate_ema(self, prices: list[float], period: int) -> list[float]:
        if not prices:
            return []
        ema = [prices[0]]
        multiplier = 2 / (period + 1)
        for price in prices[1:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        return ema
        
    def _calculate_rsi(self, prices: list[float], period: int) -> list[float]:
        if len(prices) < period + 1:
            return [50.0] * len(prices)
            
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0.0 for d in deltas]
        losses = [-d if d < 0 else 0.0 for d in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi = [50.0] * period
        
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100.0 - (100.0 / (1.0 + rs)))
            
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100.0 - (100.0 / (1.0 + rs)))
                
        return rsi

    def generate_signal(self, data: MarketDataSeries) -> TradeSignal:
        closes = data.closes
        if len(closes) < self.slow_period + 1:
            return TradeSignal(SignalType.HOLD, "", closes[-1] if closes else 0.0)
            
        current_price = closes[-1]
        
        fast_ema = self._calculate_ema(closes, self.fast_period)
        slow_ema = self._calculate_ema(closes, self.slow_period)
        rsi = self._calculate_rsi(closes, self.rsi_period)
        
        if len(fast_ema) < 2 or len(slow_ema) < 2 or len(rsi) < 1:
            return TradeSignal(SignalType.HOLD, "", current_price)
            
        current_fast = fast_ema[-1]
        current_slow = slow_ema[-1]
        prev_fast = fast_ema[-2]
        prev_slow = slow_ema[-2]
        current_rsi = rsi[-1]
        
        symbol = ""
        
        # BUY Logic: Fast crosses above Slow AND RSI > 50
        if prev_fast <= prev_slow and current_fast > current_slow and current_rsi > 50:
            sl = current_price * (1.0 - self.stop_loss_pct)
            tp = current_price * (1.0 + self.take_profit_pct)
            return TradeSignal(
                signal=SignalType.BUY,
                symbol=symbol,
                price=current_price,
                stop_loss=sl,
                take_profit=tp,
                metadata={"rsi": current_rsi, "fast_ema": current_fast, "slow_ema": current_slow}
            )
            
        # SELL / EXIT Logic: Fast crosses below Slow OR RSI < 45
        if (prev_fast >= prev_slow and current_fast < current_slow) or current_rsi < 45:
            sl = current_price * (1.0 + self.stop_loss_pct)
            tp = current_price * (1.0 - self.take_profit_pct)
            return TradeSignal(
                signal=SignalType.SELL,
                symbol=symbol,
                price=current_price,
                stop_loss=sl,
                take_profit=tp,
                metadata={"rsi": current_rsi, "fast_ema": current_fast, "slow_ema": current_slow}
            )
            
        return TradeSignal(
            signal=SignalType.HOLD,
            symbol=symbol,
            price=current_price,
            metadata={"rsi": current_rsi, "fast_ema": current_fast, "slow_ema": current_slow}
        )
