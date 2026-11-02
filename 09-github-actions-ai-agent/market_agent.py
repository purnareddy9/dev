#!/usr/bin/env python3
"""
==============================================================================
Autonomous Real-Time AI Stock & Cloud Infrastructure Market Intelligence Agent
Engineered for GitHub Actions, Autonomous Cloud CI/CD & Local Workstations
==============================================================================
Pulls real-time 1-year historical market quotes, calculates quantitative
technical indicators (20/50/200 SMA, RSI 14, Golden/Death Cross), fetches live
breaking news, and synthesizes institutional-grade investment & FinOps reports
using Google Gemini 3.8 Flash (with intelligent multi-tier fallback).
Autonomously generates date-wise historical archives and commits back to GitHub.
==============================================================================
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List

# Ensure UTF-8 output on Windows & Linux runners
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculates Wilder's 14-period Relative Strength Index (RSI)."""
    if len(prices) < period + 1:
        return 50.0

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def render_gauge_bar(value: float, min_val: float, max_val: float, width: int = 20) -> str:
    """Renders a clean text-based progress bar for markdown displays."""
    if max_val <= min_val:
        return "[" + "░" * width + "]"
    ratio = max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
    filled = int(round(ratio * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


class MarketDataFetcher:
    """Fetches live market metrics, 1-year historical price series, and news."""

    @staticmethod
    def get_live_ticker_data(symbol: str) -> Dict[str, Any]:
        """Queries 1-year daily chart data and calculates SMAs, RSI, and momentum."""
        clean_symbol = symbol.strip().upper()
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_symbol}?interval=1d&range=1y"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        result = data["chart"]["result"][0]
        meta = result["meta"]
        timestamps = result.get("timestamp", [])
        quote = result["indicators"]["quote"][0]
        closes = [round(c, 2) for c in quote.get("close", []) if c is not None]

        current_price = meta.get("regularMarketPrice", closes[-1] if closes else 0.0)
        previous_close = meta.get("chartPreviousClose", closes[-2] if len(closes) > 1 else current_price)
        change_pct = round(((current_price - previous_close) / previous_close) * 100, 2) if previous_close else 0.0

        # Technical Indicators
        sma_20 = round(sum(closes[-20:]) / min(20, len(closes)), 2) if closes else current_price
        sma_50 = round(sum(closes[-50:]) / min(50, len(closes)), 2) if closes else current_price
        sma_200 = round(sum(closes[-200:]) / min(200, len(closes)), 2) if closes else current_price
        rsi_14 = calculate_rsi(closes)

        # Distances from Moving Averages
        diff_sma20 = round(((current_price - sma_20) / sma_20) * 100, 2) if sma_20 else 0.0
        diff_sma50 = round(((current_price - sma_50) / sma_50) * 100, 2) if sma_50 else 0.0
        diff_sma200 = round(((current_price - sma_200) / sma_200) * 100, 2) if sma_200 else 0.0

        cross_status = "Golden Cross 🌟 (50 SMA > 200 SMA)" if sma_50 >= sma_200 else "Death Cross ⚠️ (50 SMA < 200 SMA)"

        # 52-Week Range Percentile
        high_52 = meta.get("fiftyTwoWeekHigh", max(closes) if closes else current_price)
        low_52 = meta.get("fiftyTwoWeekLow", min(closes) if closes else current_price)
        range_percentile = round(((current_price - low_52) / (high_52 - low_52)) * 100, 1) if (high_52 > low_52) else 50.0

        # Recent 10-day series for chart rendering
        recent_10_closes = closes[-10:] if len(closes) >= 10 else closes
        recent_10_timestamps = timestamps[-len(recent_10_closes):]
        recent_10_dates = [time.strftime("%m-%d", time.gmtime(t)) for t in recent_10_timestamps]

        market_time = meta.get("regularMarketTime", time.time())
        date_str = time.strftime("%Y-%m-%d", time.gmtime(market_time))
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(market_time))

        return {
            "symbol": clean_symbol,
            "company_name": meta.get("longName") or meta.get("shortName") or clean_symbol,
            "currency": meta.get("currency", "USD"),
            "current_price": current_price,
            "previous_close": previous_close,
            "change_percent": change_pct,
            "day_high": meta.get("regularMarketDayHigh", current_price),
            "day_low": meta.get("regularMarketDayLow", current_price),
            "volume": meta.get("regularMarketVolume", 0),
            "52_week_high": high_52,
            "52_week_low": low_52,
            "range_percentile": range_percentile,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "diff_sma20": diff_sma20,
            "diff_sma50": diff_sma50,
            "diff_sma200": diff_sma200,
            "cross_status": cross_status,
            "rsi_14": rsi_14,
            "recent_10_closes": recent_10_closes,
            "recent_10_dates": recent_10_dates,
            "date": date_str,
            "timestamp": timestamp_str
        }

    @staticmethod
    def get_live_news(symbol: str) -> List[Dict[str, str]]:
        """Queries latest top breaking news articles for the stock ticker."""
        clean_symbol = symbol.strip().upper()
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={clean_symbol}&quotesCount=1&newsCount=6"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        req = urllib.request.Request(url, headers=headers)
        articles = []
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("news", [])[:6]:
                    pub_time = item.get("providerPublishTime", time.time())
                    articles.append({
                        "title": item.get("title", "Market Update"),
                        "publisher": item.get("publisher", "Financial News"),
                        "link": item.get("link", f"https://finance.yahoo.com/quote/{clean_symbol}"),
                        "time_str": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(pub_time))
                    })
        except Exception as e:
            print(f"⚠️ News fetch warning: {e}", flush=True)

        return articles


class GeminiMarketAnalyst:
    """Connects to Google Gemini API (prioritizing Gemini 3.8 Flash) with resilient multi-tier fallback."""

    def __init__(self):
        raw_key = os.getenv("GEMINI_API_KEY") or ""
        self.api_key = raw_key.strip().strip('"').strip("'")

    def analyze_market_snapshot(self, ticker_data: Dict[str, Any], news: List[Dict[str, str]]) -> str:
        """Prompts Gemini with quantitative indicators and breaking news for deep institutional analysis."""
        if not self.api_key:
            print("ℹ️ GEMINI_API_KEY secret not detected. Using algorithmic quantitative engine.", flush=True)
            return self._fallback_quantitative_analysis(ticker_data, news)

        print(f"🔑 GEMINI_API_KEY detected (length: {len(self.api_key)} chars). Invoking Google Gemini AI...", flush=True)

        news_text = "\n".join([f"- [{a['publisher']}] {a['title']} ({a['time_str']})" for a in news]) if news else "No live headlines retrieved."

        prompt = (
            f"You are a Senior Quantitative Equity Analyst and Cloud Infrastructure SRE FinOps Agent.\n"
            f"Perform an institutional-grade research synthesis for {ticker_data['company_name']} ({ticker_data['symbol']}):\n\n"
            f"### LIVE TECHNICAL & QUANTITATIVE DATA:\n"
            f"- Current Price: ${ticker_data['current_price']} {ticker_data['currency']}\n"
            f"- 24h Change: {ticker_data['change_percent']:+0.2f}%\n"
            f"- 20-Day SMA: ${ticker_data['sma_20']} (Price diff: {ticker_data['diff_sma20']:+0.2f}%)\n"
            f"- 50-Day SMA: ${ticker_data['sma_50']} (Price diff: {ticker_data['diff_sma50']:+0.2f}%)\n"
            f"- 200-Day SMA: ${ticker_data['sma_200']} (Price diff: {ticker_data['diff_sma200']:+0.2f}%)\n"
            f"- Moving Average Alignment: {ticker_data['cross_status']}\n"
            f"- 14-Period RSI: {ticker_data['rsi_14']} / 100\n"
            f"- 52-Week Range: ${ticker_data['52_week_low']} to ${ticker_data['52_week_high']} (Current percentile: {ticker_data['range_percentile']}%)\n\n"
            f"### RECENT NEWS HEADLINES:\n{news_text}\n\n"
            f"### INSTRUCTIONS FOR YOUR ANALYSIS:\n"
            f"Output professional, structured GitHub Markdown with the following exact sections:\n\n"
            f"### 1. 🎯 Executive Recommendation & Rating\n"
            f"- **Verdict**: **BUY**, **HOLD**, or **REDUCE / SELL** (Pick one with strong conviction)\n"
            f"- **Conviction Score**: (1 to 10 Scale)\n"
            f"- **Target Price Range**: (Near-term 3-month and 12-month targets)\n"
            f"- **Executive Thesis**: 2 concise paragraphs summarizing fundamental and technical rationale.\n\n"
            f"### 2. 📊 Quantitative Valuation & Financial Fundamentals\n"
            f"Synthesize estimated valuation metrics:\n"
            f"- **Trailing & Forward P/E**\n"
            f"- **Price-to-Sales (P/S) & Return on Equity (ROE)**\n"
            f"- **Profit Margins & Revenue Trajectory**\n"
            f"- **Valuation Assessment**: (Overvalued / Fair Value / Undervalued)\n\n"
            f"### 3. 📈 Technical Trend & Moving Average Synthesis\n"
            f"- Detail the interaction between the current price and the 20, 50, and 200-day SMAs.\n"
            f"- Analyze the RSI ({ticker_data['rsi_14']}) level (Oversold, Bullish Divergence, or Distribution).\n"
            f"- Highlight key support and resistance floors.\n\n"
            f"### 4. ☁️ Platform SRE & Cloud FinOps Impact\n"
            f"- Analyze the infrastructure and cloud budget implications (especially if this is an AI, compute, or hyperscaler provider like NVDA, MSFT, GOOGL, AMZN, ORCL).\n"
            f"- Provide concrete FinOps recommendations for engineering teams (e.g. spot instances, GPU reservation strategies, CUD hedging, cluster right-sizing).\n\n"
            f"### 5. ⚖️ Catalysts & Key Risks\n"
            f"- **Top 3 Bull Catalysts**\n"
            f"- **Top 3 Bear Risks**"
        )

        # Multi-tier resilient fallback prioritizing Gemini 3.8 Flash
        models_to_try = [
            "gemini-3.8-flash",
            "gemini-flash-latest",
            "gemini-3.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-2.5-pro"
        ]
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }

        for model in models_to_try:
            print(f"🤖 Querying Google Gemini ({model})...", flush=True)
            native_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            native_payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2
                }
            }

            try:
                req = urllib.request.Request(
                    native_url,
                    data=json.dumps(native_payload).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        texts = [p.get("text", "") for p in parts if "text" in p and p.get("text")]
                        if texts:
                            print(f"✨ Successfully generated AI analysis with model '{model}'!", flush=True)
                            return "\n\n".join(texts)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                print(f"⚠️ Gemini model {model} returned HTTP {e.code}: {err_body[:200]}", flush=True)
            except Exception as e:
                print(f"⚠️ Gemini model {model} request failed: {e}", flush=True)

        print("⚠️ All Gemini model queries exhausted. Falling back to algorithmic quantitative engine.", flush=True)
        return self._fallback_quantitative_analysis(ticker_data, news)

    def _fallback_quantitative_analysis(self, data: Dict[str, Any], news: List[Dict[str, str]]) -> str:
        """Deterministic quantitative and technical report if GEMINI_API_KEY is unavailable."""
        trend = "BULLISH 🟢" if data["change_percent"] > 0 else "BEARISH 🔴"
        rsi_zone = "Oversold (Accumulation Zone)" if data["rsi_14"] < 35 else ("Overbought (Take Profit Zone)" if data["rsi_14"] > 70 else "Neutral Momentum")
        verdict = "BUY / ACCUMULATE" if data["rsi_14"] < 38 and data["current_price"] >= data["sma_200"] else ("HOLD" if data["current_price"] >= data["sma_200"] else "REDUCE")

        return f"""
### 1. 🎯 Executive Recommendation & Rating
- **Verdict**: **{verdict}**
- **Trend Momentum**: **{trend}** ({data['change_percent']:+0.2f}% today)
- **Technical Posture**: Currently trading at `${data['current_price']}` vs 200-SMA `${data['sma_200']}` ({data['diff_sma200']:+0.2f}%).
- **RSI Condition**: **{data['rsi_14']}** — {rsi_zone}.

### 2. 📊 Quantitative Valuation & Financial Fundamentals
- **52-Week Range**: `${data['52_week_low']}` – `${data['52_week_high']}` (Trading at {data['range_percentile']}% of annual bandwidth).
- **20-Day SMA**: `${data['sma_20']}` ({data['diff_sma20']:+0.2f}% relative distance).
- **50-Day SMA**: `${data['sma_50']}` ({data['diff_sma50']:+0.2f}% relative distance).
- **200-Day SMA**: `${data['sma_200']}` ({data['diff_sma200']:+0.2f}% relative distance).
- **Moving Average Cross**: {data['cross_status']}.

### 3. 📈 Technical Trend & Moving Average Synthesis
- Asset is testing key structural moving averages. Price relative to the 200-day simple moving average defines long-term institutional support.
- Short-term 20-day SMA tracking indicates ongoing momentum shift; a sustained close above the 50-day average is required to confirm trend reversal.

### 4. ☁️ Platform SRE & Cloud FinOps Impact
- For engineering organizations leveraging this vendor's infrastructure, current market fluctuations warrant strict compute right-sizing.
- Review commitments for GPU instances (e.g. H100/B200 clusters) and prioritize Spot or savings-plan capacity over on-demand rates.

### 5. ⚖️ Catalysts & Key Risks
- **Bull Catalysts**: Rebound from 200-day SMA support; enterprise AI capital expenditure expansion; stabilizing cloud margins.
- **Bear Risks**: Prolonged tech sector rotation; macro monetary headwinds; supply chain lead time variations.
"""


class ReportGenerator:
    """Renders formatted GitHub Markdown reports, Mermaid charts, and directory archives."""

    @staticmethod
    def render_mermaid_price_chart(data: Dict[str, Any]) -> str:
        """Renders GitHub-native Mermaid xychart-beta for 10-day price trend."""
        dates_json = json.dumps(data["recent_10_dates"])
        closes_json = json.dumps(data["recent_10_closes"])
        min_p = int(min(data["recent_10_closes"]) * 0.96)
        max_p = int(max(data["recent_10_closes"]) * 1.04)

        return f"""```mermaid
xychart-beta
    title "{data['symbol']} 10-Day Closing Price Trajectory"
    x-axis {dates_json}
    y-axis "Close Price ($USD)" {min_p} --> {max_p}
    line {closes_json}
```"""

    @staticmethod
    def render_mermaid_ma_chart(data: Dict[str, Any]) -> str:
        """Renders GitHub-native Mermaid xychart-beta comparing Price vs 20/50/200 SMAs."""
        vals = [data["current_price"], data["sma_20"], data["sma_50"], data["sma_200"]]
        min_p = int(min(vals) * 0.95)
        max_p = int(max(vals) * 1.05)

        return f"""```mermaid
xychart-beta
    title "{data['symbol']} Price vs Key Moving Averages (20 / 50 / 200 SMA)"
    x-axis ["Current", "SMA 20", "SMA 50", "SMA 200"]
    y-axis "Price ($USD)" {min_p} --> {max_p}
    bar {json.dumps(vals)}
```"""

    @classmethod
    def generate_full_report_markdown(cls, data: Dict[str, Any], ai_analysis: str, news: List[Dict[str, str]]) -> str:
        """Compiles the complete detailed intelligence report."""
        change_emoji = "📈" if data["change_percent"] >= 0 else "📉"
        rsi_gauge = render_gauge_bar(data["rsi_14"], 0, 100, 20)
        range_gauge = render_gauge_bar(data["range_percentile"], 0, 100, 20)
        price_chart = cls.render_mermaid_price_chart(data)
        ma_chart = cls.render_mermaid_ma_chart(data)

        news_section = ""
        if news:
            news_rows = "\n".join([f"| {a['time_str']} | **{a['publisher']}** | [{a['title']}]({a['link']}) |" for a in news])
            news_section = f"""
## 📰 Breaking News & Real-Time Market Sentiment

| Timestamp | Source | Headline |
| :--- | :--- | :--- |
{news_rows}
"""

        return f"""# {change_emoji} Real-Time AI Stock & Cloud Infrastructure Intelligence: {data['symbol']}
> **{data['company_name']}** | Analysis generated autonomously on `{data['timestamp']}`

---

## 📌 Executive Market Dashboard

| Metric | Live Value | 24h Context / Technical Status |
| :--- | :--- | :--- |
| **Current Live Price** | **${data['current_price']} {data['currency']}** | **{data['change_percent']:+0.2f}%** ({change_emoji}) |
| **Day High / Low** | ${data['day_high']} / ${data['day_low']} | Intraday spread |
| **Previous Close** | ${data['previous_close']} | Reference baseline |
| **20-Day SMA** | **${data['sma_20']}** | Price diff: `{data['diff_sma20']:+0.2f}%` |
| **50-Day SMA** | **${data['sma_50']}** | Price diff: `{data['diff_sma50']:+0.2f}%` |
| **200-Day SMA** | **${data['sma_200']}** | Price diff: `{data['diff_sma200']:+0.2f}%` |
| **Moving Average Cross** | `{data['cross_status']}` | Structural macro alignment |
| **RSI (14-Period)** | **{data['rsi_14']} / 100** | `{rsi_gauge}` |
| **52-Week Range** | ${data['52_week_low']} – ${data['52_week_high']} | `{range_gauge}` ({data['range_percentile']}%) |
| **Trading Volume** | {data['volume']:,} | Regular session shares |

---

## 📊 Technical Trend Visualizations (GitHub Native Charts)

### 10-Day Closing Price Trajectory
{price_chart}

### Current Price vs 20 / 50 / 200 Simple Moving Averages
{ma_chart}

---

## 🤖 AI Deep Cognitive Research & FinOps Intelligence

{ai_analysis}

---
{news_section}

---
*Autonomous Report generated by **DevOps AI Market Intelligence Agent** running on GitHub Actions & Gemini 3.8 Flash.*
"""

    @staticmethod
    def generate_news_markdown(data: Dict[str, Any], news: List[Dict[str, str]]) -> str:
        """Compiles dedicated news.md file for the stock."""
        items = "\n\n".join([
            f"### [{a['title']}]({a['link']})\n"
            f"- **Publisher**: {a['publisher']}\n"
            f"- **Published Date**: {a['time_str']}\n"
            f"- **Direct Link**: [{a['link']}]({a['link']})"
            for a in news
        ]) if news else "_No recent breaking news found for this ticker._"

        return f"""# 📰 Live News & Financial Catalyst Feed: {data['symbol']} ({data['company_name']})
> *Last updated: `{data['timestamp']}`*

{items}

---
*Feed curated autonomously by **GitHub Actions DevOps AI Agent**.*
"""


def save_reports_and_sync_portfolio(ticker_data: Dict[str, Any], full_report_md: str, news_md: str):
    """Saves stock reports into structured directories and updates portfolio index."""
    symbol = ticker_data["symbol"]
    date_str = ticker_data["date"]

    # Base directory for market intelligence
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_dir = os.path.join(workspace_root, "market-intelligence")
    stock_dir = os.path.join(base_dir, "stocks", symbol)
    history_dir = os.path.join(stock_dir, "history")

    os.makedirs(history_dir, exist_ok=True)

    # 1. Save README.md in stock folder (browsable on GitHub)
    readme_path = os.path.join(stock_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(full_report_md)

    # 2. Save latest.md
    latest_path = os.path.join(stock_dir, "latest.md")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(full_report_md)

    # 3. Save date-wise historical archive
    history_path = os.path.join(history_dir, f"{date_str}.md")
    with open(history_path, "w", encoding="utf-8") as f:
        f.write(full_report_md)

    # 4. Save news.md
    news_path = os.path.join(stock_dir, "news.md")
    with open(news_path, "w", encoding="utf-8") as f:
        f.write(news_md)

    # 5. Save local market_report.md for console cat
    local_report = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_report.md")
    with open(local_report, "w", encoding="utf-8") as f:
        f.write(full_report_md)

    # 6. Update master portfolio README.md
    portfolio_readme = os.path.join(base_dir, "README.md")
    update_portfolio_index(portfolio_readme, ticker_data)

    print(f"📁 Reports saved successfully in:\n  - {readme_path}\n  - {history_path}\n  - {news_path}", flush=True)


def update_portfolio_index(portfolio_path: str, latest_data: Dict[str, Any]):
    """Maintains master market-intelligence/README.md cataloging all tracked stocks."""
    stocks_dir = os.path.join(os.path.dirname(portfolio_path), "stocks")
    os.makedirs(stocks_dir, exist_ok=True)

    tracked_symbols = sorted([d for d in os.listdir(stocks_dir) if os.path.isdir(os.path.join(stocks_dir, d))])
    if latest_data["symbol"] not in tracked_symbols:
        tracked_symbols.append(latest_data["symbol"])

    rows = []
    for sym in tracked_symbols:
        sym_readme = os.path.join(stocks_dir, sym, "README.md")
        if sym == latest_data["symbol"]:
            d = latest_data
        else:
            d = {"symbol": sym, "company_name": sym, "current_price": "View", "change_percent": 0.0, "rsi_14": "N/A", "date": "Tracked"}

        change_badge = f"{d.get('change_percent', 0.0):+0.2f}%" if isinstance(d.get("change_percent"), (int, float)) else "N/A"
        rows.append(
            f"| **[{sym}](./stocks/{sym}/README.md)** | {d.get('company_name', sym)} | "
            f"${d.get('current_price')} | {change_badge} | {d.get('rsi_14')} | "
            f"[Latest](./stocks/{sym}/latest.md) • [News](./stocks/{sym}/news.md) • [History](./stocks/{sym}/history/) |"
        )

    portfolio_content = f"""# 🌐 Autonomous Cloud & SRE Market Intelligence Hub
> **Real-Time Financial & Cloud Infrastructure Analytics Engine**
> Autonomously updated on every market session via GitHub Actions and Google Gemini 3.8 Flash.

---

## 📈 Tracked Enterprise & Infrastructure Stocks

| Ticker | Company Name | Live Price | 24h Change | RSI (14) | Direct Reports |
| :--- | :--- | :--- | :--- | :--- | :--- |
{chr(10).join(rows)}

---

### 📂 Directory Architecture
```text
market-intelligence/
├── README.md                      # Master Portfolio Index (This File)
└── stocks/
    └── <TICKER>/                  # Dedicated Stock Directory
        ├── README.md              # Live Interactive Dashboard & Visual Charts
        ├── latest.md              # Latest Complete Research Analysis
        ├── news.md                # Breaking News & Sentiment Feed
        └── history/
            └── YYYY-MM-DD.md      # Immutable Date-Wise Session Archives
```

---
*Built with Python, GitHub Actions, and Google Gemini 3.8 Flash.*
"""

    with open(portfolio_path, "w", encoding="utf-8") as f:
        f.write(portfolio_content)


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else "NVDA"
    print(f"📡 Querying 1-year historical data & technicals for '{ticker}'...", flush=True)

    try:
        data = MarketDataFetcher.get_live_ticker_data(ticker)
        print(f"✅ Data fetched: {data['company_name']} (${data['current_price']}) | SMA20: ${data['sma_20']} | SMA50: ${data['sma_50']} | SMA200: ${data['sma_200']} | RSI: {data['rsi_14']}", flush=True)

        print(f"📰 Querying live breaking news for '{ticker}'...", flush=True)
        news = MarketDataFetcher.get_live_news(ticker)
        print(f"✅ Found {len(news)} live news headlines.", flush=True)

        analyst = GeminiMarketAnalyst()
        ai_analysis = analyst.analyze_market_snapshot(data, news)

        # Generate reports
        full_report_md = ReportGenerator.generate_full_report_markdown(data, ai_analysis, news)
        news_md = ReportGenerator.generate_news_markdown(data, news)

        # Save date-wise, latest, news, and update portfolio
        save_reports_and_sync_portfolio(data, full_report_md, news_md)

        # Output to console
        print(full_report_md, flush=True)

        # Write to GitHub Step Summary if running in GitHub Actions
        step_summary_path = os.getenv("GITHUB_STEP_SUMMARY")
        if step_summary_path:
            with open(step_summary_path, "a", encoding="utf-8") as f:
                f.write(full_report_md)

        print("🎉 Autonomous Market Intelligence Agent execution completed successfully!", flush=True)
    except Exception as e:
        print(f"❌ Error during agent execution: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
