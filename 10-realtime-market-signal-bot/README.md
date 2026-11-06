# ⚡ Institutional Real-Time Signal Bot & Market Depth HUD

> **Sub-Second WebSocket Quantitative Engine**  
> Tracks Order Book Depth (Level 2), Dynamic VWAP Bands, Sector Rotation, and India VIX to emit real-time BUY, SELL, and ACCUMULATION signals.

---

## 🚀 1-Click Launch

Double-click `run_bot.bat` or run in PowerShell:

```powershell
.\10-realtime-market-signal-bot\run_bot.ps1
```

Or start directly with Python:

```powershell
& "C:\Users\Sri\AppData\Local\Programs\Python\Python314\python.exe" 10-realtime-market-signal-bot/server.py
```

Then open your browser at: **`http://127.0.0.1:8000`**

---

## 🎯 The 4 Institutional Vectors Tracked in Sub-Second Speed

1. **Market Depth / Order Book Imbalance**:
   * Evaluates Top 5 Bid Qty vs Ask Qty ratio.
   * Ratio `< -0.30` $\rightarrow$ Extreme Selling Wall (Institutions offloading).
   * Ratio `> +0.30` $\rightarrow$ Heavy Buying Support (Institutions accumulating).
2. **Dynamic VWAP & Volatility Bands**:
   * Calculates cumulative intraday VWAP with $\pm 1.2\sigma$ volatility bands.
   * Crossing below VWAP triggers automatic de-risking alerts.
3. **Sector Rotation Momentum**:
   * Continuously measures `NIFTY IT` vs `BANK NIFTY` divergence to spot capital flight.
4. **India VIX Velocity**:
   * Detects sudden volatility spikes ($> +5\%$) indicating institutional derivative hedging.

---

## 🖥️ Live UI Features
* **Master Signal Banner**: Flashing `🟢 STRONG BUY`, `🔴 STRONG SELL`, or `⚖️ NEUTRAL`.
* **Exact Trade Parameters**: Real-time Entry, Target 1, Target 2, and Stop-Loss.
* **Audio Alerts**: Real-time synthesized chimes on signal shifts.
* **Live Streaming Chart**: Interactive Price vs VWAP and Volatility bands.
* **Order Book Depth Ladder**: Live 5-level bid/ask ladder with visual volume gauge.
* **Multi-Ticker Switcher**: Instantly switch between `PERSISTENT.NS`, `TCS.NS`, `INFY.NS`, `HDFCBANK.NS`, and `RELIANCE.NS`.
