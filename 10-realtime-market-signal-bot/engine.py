"""
==============================================================================
Institutional Real-Time Signal & Pressure Engine
==============================================================================
Analyzes 4 institutional vectors in sub-second velocity:
1. Market Depth / Order Book Imbalance (Bid vs Ask Queue)
2. Dynamic VWAP & Multi-Sigma Volatility Bands
3. Sector Relative Divergence (IT vs Banking Rotation)
4. India VIX Volatility & Hedging Velocity
==============================================================================
"""

import math
import time
from typing import Dict, Any, List, Optional


class OrderBookDepth:
    """Calculates order book imbalance, buy/sell walls, and institutional absorption."""

    def __init__(self, bids: Optional[List[Dict[str, float]]] = None, asks: Optional[List[Dict[str, float]]] = None):
        self.bids = bids or []  # [{"price": float, "qty": int}]
        self.asks = asks or []

    @property
    def total_bid_qty(self) -> int:
        return sum(int(b.get("qty", 0)) for b in self.bids)

    @property
    def total_ask_qty(self) -> int:
        return sum(int(a.get("qty", 0)) for a in self.asks)

    @property
    def imbalance_ratio(self) -> float:
        """
        Returns ratio from -1.0 (100% Sell Pressure) to +1.0 (100% Buy Pressure).
        > +0.25 : Strong Institutional Accumulation
        < -0.25 : Strong Institutional Selling / Dumping
        """
        tot = self.total_bid_qty + self.total_ask_qty
        if tot == 0:
            return 0.0
        return round((self.total_bid_qty - self.total_ask_qty) / tot, 4)

    @property
    def pressure_status(self) -> str:
        r = self.imbalance_ratio
        if r > 0.35:
            return "🟢 HEAVY BUYING PRESSURE"
        elif r > 0.10:
            return "🟢 MILD BUY BIAS"
        elif r < -0.35:
            return "🔴 HEAVY SELLING PRESSURE"
        elif r < -0.10:
            return "🔴 MILD SELL BIAS"
        return "⚖️ BALANCED ORDER BOOK"


class VWAPCalculator:
    """Maintains running Volume-Weighted Average Price with Standard Deviation Bands."""

    def __init__(self):
        self.cum_vol = 0.0
        self.cum_price_vol = 0.0
        self.price_history: List[float] = []
        self.current_vwap = 0.0
        self.upper_band_1 = 0.0
        self.lower_band_1 = 0.0
        self.upper_band_2 = 0.0
        self.lower_band_2 = 0.0

    def update(self, price: float, volume: float) -> float:
        if volume <= 0:
            volume = 1.0

        self.cum_vol += volume
        self.cum_price_vol += price * volume
        self.current_vwap = round(self.cum_price_vol / self.cum_vol, 2)
        self.price_history.append(price)

        if len(self.price_history) > 1200:
            self.price_history.pop(0)

        # Dynamic Standard Deviation calculation for volatility bands
        if len(self.price_history) > 5:
            mean = sum(self.price_history[-100:]) / len(self.price_history[-100:])
            variance = sum((p - mean) ** 2 for p in self.price_history[-100:]) / len(self.price_history[-100:])
            std_dev = math.sqrt(variance)
            self.upper_band_1 = round(self.current_vwap + (1.2 * std_dev), 2)
            self.lower_band_1 = round(self.current_vwap - (1.2 * std_dev), 2)
            self.upper_band_2 = round(self.current_vwap + (2.0 * std_dev), 2)
            self.lower_band_2 = round(self.current_vwap - (2.0 * std_dev), 2)
        else:
            self.upper_band_1 = round(self.current_vwap * 1.005, 2)
            self.lower_band_1 = round(self.current_vwap * 0.995, 2)
            self.upper_band_2 = round(self.current_vwap * 1.010, 2)
            self.lower_band_2 = round(self.current_vwap * 0.990, 2)

        return self.current_vwap


class SectorDivergenceTracker:
    """Tracks Relative Rotation between Nifty IT, Bank Nifty, and Broad Market."""

    def __init__(self):
        self.it_change = 0.0
        self.bank_change = 0.0
        self.nifty_change = 0.0

    def update(self, it_pct: float, bank_pct: float, nifty_pct: float):
        self.it_change = it_pct
        self.bank_change = bank_pct
        self.nifty_change = nifty_pct

    @property
    def it_relative_strength(self) -> float:
        """Difference between Nifty IT and Bank Nifty."""
        return round(self.it_change - self.bank_change, 2)

    @property
    def rotation_status(self) -> str:
        diff = self.it_relative_strength
        if diff > 1.0:
            return "🟢 CAPITAL ROTATING INTO IT"
        elif diff < -1.0:
            return "🔴 CAPITAL ROTATING OUT OF IT (TO BANKS)"
        return "⚖️ BALANCED SECTOR COUPLING"


class HighFrequencySignalEngine:
    """
    Synthesizes the 4 institutional pillars into live millisecond-speed BUY / SELL signals.
    """

    def __init__(self, ticker: str = "PERSISTENT"):
        self.ticker = ticker
        self.vwap_calc = VWAPCalculator()
        self.sector_tracker = SectorDivergenceTracker()
        self.last_signal_time = 0.0
        self.last_action = "NEUTRAL"

    def evaluate_tick(
        self,
        price: float,
        volume: float,
        depth: OrderBookDepth,
        vix: float = 16.5,
        vix_change_pct: float = 0.0,
        it_pct: float = 0.0,
        bank_pct: float = 0.0,
        nifty_pct: float = 0.0
    ) -> Dict[str, Any]:
        """
        Executes millisecond scoring across all 4 institutional vectors.
        """
        vwap = self.vwap_calc.update(price, volume)
        self.sector_tracker.update(it_pct, bank_pct, nifty_pct)

        vwap_diff_pct = round(((price - vwap) / vwap) * 100, 2)
        imbalance = depth.imbalance_ratio
        it_rel = self.sector_tracker.it_relative_strength

        # Quantitative Score: -100 (Extreme Sell) to +100 (Extreme Buy)
        score = 0
        reasons = []

        # Vector 1: VWAP Position & Bands (Weight: 35%)
        if price > vwap:
            score += 25
            reasons.append(f"Price above VWAP (₹{vwap})")
            if price > self.vwap_calc.upper_band_1:
                score += 10
                reasons.append("Breaking above Upper Volatility Band")
        else:
            score -= 25
            reasons.append(f"Price below VWAP (₹{vwap})")
            if price < self.vwap_calc.lower_band_1:
                score -= 10
                reasons.append("Sinking below Lower Volatility Band")

        # Vector 2: Order Book Imbalance (Weight: 35%)
        if imbalance > 0.25:
            score += 35
            reasons.append(f"Heavy Buy Queue (+{int(imbalance * 100)}% Bid Imbalance)")
        elif imbalance > 0.10:
            score += 15
        elif imbalance < -0.25:
            score -= 35
            reasons.append(f"Massive Sell Wall ({int(imbalance * 100)}% Ask Imbalance)")
        elif imbalance < -0.10:
            score -= 15

        # Vector 3: Sector Rotation (Weight: 15%)
        if it_rel > 0.5:
            score += 15
            reasons.append(f"IT Outperforming Banks by {it_rel:+0.2f}%")
        elif it_rel < -0.5:
            score -= 15
            reasons.append(f"Capital Draining into Banks ({it_rel:+0.2f}% lag)")

        # Vector 4: India VIX Velocity (Weight: 15%)
        if vix_change_pct > 5.0:
            score -= 15
            reasons.append(f"VIX Spiking ({vix_change_pct:+0.1f}% spike - Hedging active)")
        elif vix_change_pct < -2.0:
            score += 15
            reasons.append(f"VIX Cooling ({vix_change_pct:+0.1f}% drop - Risk-On)")

        # Action & Confidence determination
        if score >= 60:
            action = "STRONG BUY"
            color = "#00e676"
            badge = "🟢 STRONG BUY"
            confidence = min(98, 50 + int(score * 0.48))
        elif score >= 25:
            action = "BUY"
            color = "#22c55e"
            badge = "🟢 BUY"
            confidence = min(85, 45 + int(score * 0.4))
        elif score <= -60:
            action = "STRONG SELL"
            color = "#ff1744"
            badge = "🔴 STRONG SELL"
            confidence = min(98, 50 + int(abs(score) * 0.48))
        elif score <= -25:
            action = "SELL"
            color = "#ef4444"
            badge = "🔴 SELL"
            confidence = min(85, 45 + int(abs(score) * 0.4))
        else:
            action = "NEUTRAL"
            color = "#f59e0b"
            badge = "⚖️ NEUTRAL / HOLD"
            confidence = 50

        # Exact Risk-Managed Trade Parameters
        atr_approx = round(price * 0.006, 2)  # ~0.6% standard intraday noise buffer
        if "BUY" in action:
            target_1 = round(price + (atr_approx * 1.5), 2)
            target_2 = round(price + (atr_approx * 3.0), 2)
            stop_loss = round(min(vwap * 0.997, price - atr_approx), 2)
        elif "SELL" in action:
            target_1 = round(price - (atr_approx * 1.5), 2)
            target_2 = round(price - (atr_approx * 3.0), 2)
            stop_loss = round(max(vwap * 1.003, price + atr_approx), 2)
        else:
            target_1 = round(vwap * 1.008, 2)
            target_2 = round(vwap * 1.015, 2)
            stop_loss = round(vwap * 0.992, 2)

        return {
            "timestamp": time.strftime("%H:%M:%S"),
            "ticker": self.ticker,
            "price": price,
            "vwap": vwap,
            "vwap_diff_pct": vwap_diff_pct,
            "upper_band_1": self.vwap_calc.upper_band_1,
            "lower_band_1": self.vwap_calc.lower_band_1,
            "total_bid_qty": depth.total_bid_qty,
            "total_ask_qty": depth.total_ask_qty,
            "imbalance_ratio": imbalance,
            "pressure_status": depth.pressure_status,
            "it_relative_strength": it_rel,
            "sector_rotation_status": self.sector_tracker.rotation_status,
            "vix": vix,
            "vix_change_pct": vix_change_pct,
            "score": score,
            "action": action,
            "badge": badge,
            "color": color,
            "confidence": confidence,
            "entry_price": price,
            "target_1": target_1,
            "target_2": target_2,
            "stop_loss": stop_loss,
            "rationale": " • ".join(reasons) if reasons else "Market consolidating in narrow bandwidth."
        }
