#!/usr/bin/env python3
"""
==============================================================================
Autonomous Real-Time AI Market & Indices Intelligence Agent
Engineered for GitHub Actions, Autonomous Cloud CI/CD & Local Workstations
==============================================================================
- Provides real-time market summaries on major domestic & global indices:
  NIFTY 50, SENSEX, NIFTY IT, NIFTY 500, BANK NIFTY, S&P 500, NASDAQ.
- Features intelligent symbol resolution: auto-resolves Indian NSE/BSE tickers
  (e.g., 'PERSISTENT' -> 'PERSISTENT.NS', 'TCS' -> 'TCS.NS', 'INFY' -> 'INFY.NS')
  and global tickers without 404 errors.
- Calculates 20/50/200-day SMAs, Wilder's RSI (14), Golden/Death Crosses.
- Renders GitHub-native Mermaid price & moving average charts.
- Powered by Google Gemini 3.8 Flash (with resilient fallback).
- Autonomously generates date-wise historical archives and commits back to GitHub.
==============================================================================
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, List

# Ensure UTF-8 output on Windows & Linux runners
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def clean_markdown_fences(text: str) -> str:
    """Strips outer markdown code fences (```markdown ... ```) so GitHub renders rich native formatting."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    while cleaned.startswith("`"):
        cleaned = cleaned[1:]
    return cleaned.strip()


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
    """Renders a clean text progress bar for markdown displays."""
    if max_val <= min_val:
        return "[" + "░" * width + "]"
    ratio = max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
    filled = int(round(ratio * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


class MarketDataFetcher:
    """Fetches real-time market indices, stock quotes, historical technicals, and news."""

    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    @classmethod
    def resolve_symbol(cls, raw_symbol: str) -> Dict[str, str]:
        """
        Smart resolution for tickers:
        - Resolves index aliases (NIFTY 50, SENSEX, NIFTY IT, etc.)
        - Auto-discovers Indian NSE/BSE suffixes (e.g. 'PERSISTENT' -> 'PERSISTENT.NS')
        - Prevents 404 errors for non-US equities.
        """
        clean = raw_symbol.strip().upper()

        index_aliases = {
            "NIFTY": "^NSEI",
            "NIFTY 50": "^NSEI",
            "NIFTY50": "^NSEI",
            "SENSEX": "^BSESN",
            "BSE": "^BSESN",
            "NIFTY IT": "^CNXIT",
            "NIFTYIT": "^CNXIT",
            "NIFTY 500": "^CRSLDX",
            "NIFTY500": "^CRSLDX",
            "BANK NIFTY": "^NSEBANK",
            "BANKNIFTY": "^NSEBANK",
            "NIFTY BANK": "^NSEBANK",
            "SP500": "^GSPC",
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "DOW": "^DJI"
        }

        if clean in index_aliases:
            return {"query_symbol": index_aliases[clean], "clean_symbol": clean, "is_index": True}

        # If already has exchange extension (e.g., PERSISTENT.NS, NVDA) or index prefix (^)
        if "." in clean or clean.startswith("^"):
            return {"query_symbol": clean, "clean_symbol": clean.split(".")[0], "is_index": False}

        # Query Yahoo search API to find matching real symbol
        search_url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(clean)}&quotesCount=5"
        try:
            req = urllib.request.Request(search_url, headers=cls.HEADERS)
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                quotes = data.get("quotes", [])
                if quotes:
                    # Prefer NSE (.NS) for Indian tickers
                    for q in quotes:
                        q_sym = q.get("symbol", "")
                        if q_sym.endswith(".NS"):
                            print(f"🔍 Resolved '{clean}' to Indian NSE symbol '{q_sym}' via Yahoo Finance Search.", flush=True)
                            return {"query_symbol": q_sym, "clean_symbol": clean, "is_index": False}
                    # Else return the top matching equity symbol
                    top_sym = quotes[0].get("symbol", clean)
                    print(f"🔍 Resolved '{clean}' to '{top_sym}' via Yahoo Finance Search.", flush=True)
                    return {"query_symbol": top_sym, "clean_symbol": clean, "is_index": False}
        except Exception as e:
            print(f"⚠️ Yahoo search resolver error: {e}", flush=True)

        return {"query_symbol": clean, "clean_symbol": clean, "is_index": False}

    @classmethod
    def get_indices_pulse(cls) -> List[Dict[str, Any]]:
        """Queries live market metrics for major domestic and international indices."""
        indices_to_track = [
            ("NIFTY 50", "^NSEI", "Indian Benchmark (Top 50 Blue-Chip Equities)"),
            ("SENSEX", "^BSESN", "BSE Benchmark (Top 30 Established Companies)"),
            ("NIFTY IT", "^CNXIT", "Indian Technology & Software Enterprise Sector"),
            ("NIFTY 500", "^CRSLDX", "Indian Broad Market (Top 500 Across Large/Mid/Small-Cap)"),
            ("BANK NIFTY", "^NSEBANK", "Indian Banking & Financial Services Sector"),
            ("S&P 500", "^GSPC", "US Large-Cap Market Benchmark"),
            ("NASDAQ Composite", "^IXIC", "Global Technology & Growth Benchmark")
        ]

        results = []
        for name, symbol, description in indices_to_track:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
                req = urllib.request.Request(url, headers=cls.HEADERS)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    res = data["chart"]["result"][0]
                    meta = res["meta"]
                    price = meta.get("regularMarketPrice", 0.0)
                    prev_close = meta.get("chartPreviousClose", price)
                    change_pct = round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0.0
                    currency = meta.get("currency", "PTS")

                    results.append({
                        "name": name,
                        "symbol": symbol,
                        "description": description,
                        "price": price,
                        "previous_close": prev_close,
                        "change_percent": change_pct,
                        "currency": currency,
                        "status": "🟢 BULLISH" if change_pct >= 0 else "🔴 BEARISH"
                    })
            except Exception as e:
                print(f"⚠️ Index query skipped for {name} ({symbol}): {e}", flush=True)

        return results

    @classmethod
    def get_live_ticker_data(cls, symbol_info: Dict[str, str]) -> Dict[str, Any]:
        """Queries 1-year historical chart data and calculates technical indicators."""
        query_sym = symbol_info["query_symbol"]
        clean_sym = symbol_info["clean_symbol"]

        # If direct fetch fails with 404 and no extension, retry with .NS
        attempts = [query_sym]
        if "." not in query_sym and not query_sym.startswith("^"):
            attempts.append(f"{query_sym}.NS")
            attempts.append(f"{query_sym}.BO")

        last_err = None
        data = None

        for sym in attempts:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1y"
            try:
                req = urllib.request.Request(url, headers=cls.HEADERS)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    query_sym = sym
                    break
            except Exception as e:
                last_err = e

        if not data or not data.get("chart", {}).get("result"):
            raise ValueError(f"Unable to retrieve market chart data for '{clean_sym}' (tried: {attempts}): {last_err}")

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

        diff_sma20 = round(((current_price - sma_20) / sma_20) * 100, 2) if sma_20 else 0.0
        diff_sma50 = round(((current_price - sma_50) / sma_50) * 100, 2) if sma_50 else 0.0
        diff_sma200 = round(((current_price - sma_200) / sma_200) * 100, 2) if sma_200 else 0.0

        cross_status = "Golden Cross 🌟 (50 SMA > 200 SMA)" if sma_50 >= sma_200 else "Death Cross ⚠️ (50 SMA < 200 SMA)"

        high_52 = meta.get("fiftyTwoWeekHigh", max(closes) if closes else current_price)
        low_52 = meta.get("fiftyTwoWeekLow", min(closes) if closes else current_price)
        range_percentile = round(((current_price - low_52) / (high_52 - low_52)) * 100, 1) if (high_52 > low_52) else 50.0

        recent_10_closes = closes[-10:] if len(closes) >= 10 else closes
        recent_10_timestamps = timestamps[-len(recent_10_closes):]
        recent_10_dates = [time.strftime("%m-%d", time.gmtime(t)) for t in recent_10_timestamps]

        market_time = meta.get("regularMarketTime", time.time())
        date_str = time.strftime("%Y-%m-%d", time.gmtime(market_time))
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(market_time))

        return {
            "symbol": query_sym,
            "folder_symbol": clean_sym,
            "company_name": meta.get("longName") or meta.get("shortName") or clean_sym,
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

    @classmethod
    def get_live_news(cls, symbol: str) -> List[Dict[str, str]]:
        """Queries latest top breaking news articles for the stock ticker."""
        clean = symbol.split(".")[0].strip()
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(clean)}&quotesCount=1&newsCount=6"

        articles = []
        try:
            req = urllib.request.Request(url, headers=cls.HEADERS)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("news", [])[:6]:
                    pub_time = item.get("providerPublishTime", time.time())
                    articles.append({
                        "title": item.get("title", "Market Update"),
                        "publisher": item.get("publisher", "Financial News"),
                        "link": item.get("link", f"https://finance.yahoo.com/quote/{symbol}"),
                        "time_str": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(pub_time))
                    })
        except Exception as e:
            print(f"⚠️ News fetch warning: {e}", flush=True)

        return articles


class GeminiMarketAnalyst:
    """Invokes Google Gemini 3.8 Flash (with resilient fallback) to synthesize institutional reports."""

    def __init__(self):
        raw_key = os.getenv("GEMINI_API_KEY") or ""
        self.api_key = raw_key.strip().strip('"').strip("'")

    def analyze_market_snapshot(self, ticker_data: Dict[str, Any], indices: List[Dict[str, Any]], news: List[Dict[str, str]]) -> str:
        """Prompts Gemini with macro indices context, quantitative technicals, and news."""
        if not self.api_key:
            print("ℹ️ GEMINI_API_KEY secret not detected. Using algorithmic quantitative engine.", flush=True)
            return self._fallback_quantitative_analysis(ticker_data, indices)

        print(f"🔑 GEMINI_API_KEY detected (length: {len(self.api_key)} chars). Invoking Google Gemini AI...", flush=True)

        indices_summary = "\n".join([f"- {idx['name']} ({idx['symbol']}): {idx['price']} {idx['currency']} ({idx['change_percent']:+0.2f}%) [{idx['status']}]" for idx in indices])
        news_text = "\n".join([f"- [{a['publisher']}] {a['title']} ({a['time_str']})" for a in news]) if news else "No live headlines retrieved."

        prompt = (
            f"You are a Senior Quantitative Equity Strategist and Cloud Infrastructure SRE FinOps Agent.\n"
            f"Perform an institutional-grade research synthesis for {ticker_data['company_name']} ({ticker_data['symbol']}):\n\n"
            f"### 🌐 GLOBAL & DOMESTIC INDICES CONTEXT:\n{indices_summary}\n\n"
            f"### 📈 LIVE TECHNICAL & VALUATION DATA FOR {ticker_data['symbol']}:\n"
            f"- Current Price: ${ticker_data['current_price']} {ticker_data['currency']}\n"
            f"- 24h Change: {ticker_data['change_percent']:+0.2f}%\n"
            f"- 20-Day SMA: ${ticker_data['sma_20']} (Price diff: {ticker_data['diff_sma20']:+0.2f}%)\n"
            f"- 50-Day SMA: ${ticker_data['sma_50']} (Price diff: {ticker_data['diff_sma50']:+0.2f}%)\n"
            f"- 200-Day SMA: ${ticker_data['sma_200']} (Price diff: {ticker_data['diff_sma200']:+0.2f}%)\n"
            f"- Moving Average Alignment: {ticker_data['cross_status']}\n"
            f"- 14-Period RSI: {ticker_data['rsi_14']} / 100\n"
            f"- 52-Week Range: ${ticker_data['52_week_low']} to ${ticker_data['52_week_high']} (Current percentile: {ticker_data['range_percentile']}%)\n\n"
            f"### 📰 BREAKING NEWS HEADLINES:\n{news_text}\n\n"
            f"### INSTRUCTIONS FOR YOUR ANALYSIS:\n"
            f"Output professional, structured GitHub Markdown with the following exact sections:\n\n"
            f"### 1. 🎯 Executive Recommendation & Rating\n"
            f"- **Verdict**: **BUY**, **HOLD**, or **REDUCE / SELL** (Pick one with high conviction)\n"
            f"- **Conviction Score**: (1 to 10 Scale)\n"
            f"- **Target Price Range**: (Near-term 3-month and 12-month targets in {ticker_data['currency']})\n"
            f"- **Executive Thesis**: Concise paragraphs explaining fundamental, technical, and macroeconomic reasons.\n\n"
            f"### 2. 📊 Quantitative Valuation & Financial Fundamentals\n"
            f"- **Trailing & Forward P/E multiples**\n"
            f"- **Price-to-Sales (P/S) & Return on Equity (ROE)**\n"
            f"- **Operating & Profit Margins / Revenue Growth Trends**\n"
            f"- **Valuation Assessment**: (Undervalued / Fair Value / Overvalued)\n\n"
            f"### 3. 📈 Technical Trend & Moving Average Synthesis\n"
            f"- Detailed interaction with the 20, 50, and 200-day SMAs.\n"
            f"- Evaluation of RSI ({ticker_data['rsi_14']}) momentum.\n"
            f"- Identification of immediate support floor and major overhead resistance ceiling.\n\n"
            f"### 4. ☁️ Enterprise SRE & Cloud FinOps Impact\n"
            f"- Analyze infrastructure, digital transformation, and compute budget implications (whether this company is an IT service provider, hyperscaler, or silicon designer).\n"
            f"- Concrete FinOps recommendations for IT/engineering leadership (e.g. cloud optimization, software delivery velocity, workload scheduling).\n\n"
            f"### 5. ⚖️ Catalysts & Key Risks\n"
            f"- **Top 3 Bull Catalysts**\n"
            f"- **Top 3 Bear Risks**"
        )

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
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
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
        return self._fallback_quantitative_analysis(ticker_data, indices)

    def _fallback_quantitative_analysis(self, data: Dict[str, Any], indices: List[Dict[str, Any]]) -> str:
        """Deterministic quantitative and technical report if GEMINI_API_KEY is unavailable."""
        trend = "BULLISH 🟢" if data["change_percent"] > 0 else "BEARISH 🔴"
        rsi_zone = "Oversold (Accumulation Zone)" if data["rsi_14"] < 35 else ("Overbought (Take Profit Zone)" if data["rsi_14"] > 70 else "Neutral Momentum")
        verdict = "BUY / ACCUMULATE" if data["rsi_14"] < 38 and data["current_price"] >= data["sma_200"] else ("HOLD" if data["current_price"] >= data["sma_200"] else "REDUCE")

        return f"""
### 1. 🎯 Executive Recommendation & Rating
- **Verdict**: **{verdict}**
- **Trend Momentum**: **{trend}** ({data['change_percent']:+0.2f}% today)
- **Technical Posture**: Currently trading at `{data['current_price']} {data['currency']}` vs 200-SMA `{data['sma_200']}` ({data['diff_sma200']:+0.2f}%).
- **RSI Condition**: **{data['rsi_14']}** — {rsi_zone}.

### 2. 📊 Quantitative Valuation & Financial Fundamentals
- **52-Week Range**: `{data['52_week_low']}` – `{data['52_week_high']}` (Trading at {data['range_percentile']}% of annual bandwidth).
- **20-Day SMA**: `{data['sma_20']}` ({data['diff_sma20']:+0.2f}% relative distance).
- **50-Day SMA**: `{data['sma_50']}` ({data['diff_sma50']:+0.2f}% relative distance).
- **200-Day SMA**: `{data['sma_200']}` ({data['diff_sma200']:+0.2f}% relative distance).
- **Moving Average Cross**: {data['cross_status']}.

### 3. 📈 Technical Trend & Moving Average Synthesis
- Asset is testing key structural moving averages. Price relative to the 200-day simple moving average defines long-term institutional support.
- Short-term 20-day SMA tracking indicates ongoing momentum shift; a sustained close above the 50-day average is required to confirm trend reversal.

### 4. ☁️ Platform SRE & Cloud FinOps Impact
- For enterprise organizations leveraging this vendor or IT provider, market fluctuations warrant strict compute and IT budget right-sizing.
- Optimize application workloads and verify that operational service-level agreements (SLAs) are supported by cost-effective resource commitments.

### 5. ⚖️ Catalysts & Key Risks
- **Bull Catalysts**: Rebound from key moving average support; broadening digital transformation investments; stabilizing operating margins.
- **Bear Risks**: Prolonged tech sector consolidation; macro monetary shifts; changing enterprise IT spending priorities.
"""


class ReportGenerator:
    """Renders formatted GitHub Markdown reports, Mermaid charts, indices dashboards, and directory archives."""

    @staticmethod
    def render_indices_table(indices: List[Dict[str, Any]]) -> str:
        """Renders the executive market indices pulse table."""
        if not indices:
            return "_No live index data available._"

        rows = []
        for idx in indices:
            icon = "📈" if idx["change_percent"] >= 0 else "📉"
            rows.append(
                f"| **{idx['name']}** (`{idx['symbol']}`) | **{idx['price']:,.2f} {idx['currency']}** | "
                f"**{idx['change_percent']:+0.2f}%** ({icon}) | `{idx['status']}` | {idx['description']} |"
            )

        return f"""
| Index Benchmark | Live Level | 24h Change | Market Posture | Benchmark Sector Coverage |
| :--- | :--- | :--- | :--- | :--- |
{chr(10).join(rows)}
"""

    @staticmethod
    def render_mermaid_price_chart(data: Dict[str, Any]) -> str:
        """Renders GitHub-native Mermaid xychart-beta for 10-day price trend."""
        dates_json = json.dumps(data["recent_10_dates"])
        closes_json = json.dumps(data["recent_10_closes"])
        min_p = int(min(data["recent_10_closes"]) * 0.96)
        max_p = int(max(data["recent_10_closes"]) * 1.04)

        return f"""```mermaid
xychart-beta
    title "{data['folder_symbol']} 10-Day Closing Price Trajectory"
    x-axis {dates_json}
    y-axis "Close ({data['currency']})" {min_p} --> {max_p}
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
    title "{data['folder_symbol']} Price vs Key Moving Averages (20 / 50 / 200 SMA)"
    x-axis ["Current", "SMA 20", "SMA 50", "SMA 200"]
    y-axis "Price ({data['currency']})" {min_p} --> {max_p}
    bar {json.dumps(vals)}
```"""

    @classmethod
    def generate_full_report_markdown(cls, data: Dict[str, Any], indices: List[Dict[str, Any]], ai_analysis: str, news: List[Dict[str, str]]) -> str:
        """Compiles the complete detailed intelligence report."""
        change_emoji = "📈" if data["change_percent"] >= 0 else "📉"
        rsi_gauge = render_gauge_bar(data["rsi_14"], 0, 100, 20)
        range_gauge = render_gauge_bar(data["range_percentile"], 0, 100, 20)
        indices_table = cls.render_indices_table(indices)
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

        return f"""# {change_emoji} Real-Time Market & Cloud Infrastructure Intelligence: {data['folder_symbol']}
> **{data['company_name']}** (`{data['symbol']}`) | Analysis generated autonomously on `{data['timestamp']}`

---

## 🌐 1. Global & Domestic Market Indices Pulse
> *Real-time macro benchmark posture across Indian & global equity markets:*

{indices_table}

---

## 📌 2. Stock Executive Dashboard: {data['folder_symbol']}

| Metric | Live Value | 24h Context / Technical Status |
| :--- | :--- | :--- |
| **Current Live Price** | **{data['current_price']:,} {data['currency']}** | **{data['change_percent']:+0.2f}%** ({change_emoji}) |
| **Day High / Low** | {data['day_high']} / {data['day_low']} {data['currency']} | Intraday spread |
| **Previous Close** | {data['previous_close']} {data['currency']} | Reference baseline |
| **20-Day SMA** | **{data['sma_20']} {data['currency']}** | Price diff: `{data['diff_sma20']:+0.2f}%` |
| **50-Day SMA** | **{data['sma_50']} {data['currency']}** | Price diff: `{data['diff_sma50']:+0.2f}%` |
| **200-Day SMA** | **{data['sma_200']} {data['currency']}** | Price diff: `{data['diff_sma200']:+0.2f}%` |
| **Moving Average Cross** | `{data['cross_status']}` | Structural macro alignment |
| **RSI (14-Period)** | **{data['rsi_14']} / 100** | `{rsi_gauge}` |
| **52-Week Range** | {data['52_week_low']} – {data['52_week_high']} {data['currency']} | `{range_gauge}` ({data['range_percentile']}%) |
| **Trading Volume** | {data['volume']:,} | Regular session shares |

---

## 📊 3. Technical Trend Visualizations (GitHub Native Charts)

### 10-Day Closing Price Trajectory
{price_chart}

### Current Price vs 20 / 50 / 200 Simple Moving Averages
{ma_chart}

---

## 🤖 4. AI Deep Cognitive Research & FinOps Intelligence

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

        return f"""# 📰 Live News & Financial Catalyst Feed: {data['folder_symbol']} ({data['company_name']})
> *Last updated: `{data['timestamp']}`*

{items}

---
*Feed curated autonomously by **GitHub Actions DevOps AI Agent**.*
"""


def save_reports_and_sync_portfolio(ticker_data: Dict[str, Any], indices: List[Dict[str, Any]], full_report_md: str, news_md: str):
    """Saves stock reports into structured directories and updates portfolio index."""
    folder_sym = ticker_data["folder_symbol"]
    date_str = ticker_data["date"]

    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_dir = os.path.join(workspace_root, "market-intelligence")
    stock_dir = os.path.join(base_dir, "stocks", folder_sym)
    history_dir = os.path.join(stock_dir, "history")

    os.makedirs(history_dir, exist_ok=True)

    # 1. Save README.md in stock folder
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

    # 5. Save local market_report.md for workflow console cat
    local_report = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_report.md")
    with open(local_report, "w", encoding="utf-8") as f:
        f.write(full_report_md)

    # 6. Update master portfolio README.md with indices pulse
    portfolio_readme = os.path.join(base_dir, "README.md")
    update_portfolio_index(portfolio_readme, ticker_data, indices)

    print(f"📁 Reports saved successfully in:\n  - {readme_path}\n  - {history_path}\n  - {news_path}", flush=True)


def update_portfolio_index(portfolio_path: str, latest_data: Dict[str, Any], indices: List[Dict[str, Any]]):
    """Maintains master market-intelligence/README.md cataloging indices and all tracked stocks."""
    stocks_dir = os.path.join(os.path.dirname(portfolio_path), "stocks")
    os.makedirs(stocks_dir, exist_ok=True)

    tracked_symbols = sorted([d for d in os.listdir(stocks_dir) if os.path.isdir(os.path.join(stocks_dir, d))])
    if latest_data["folder_symbol"] not in tracked_symbols:
        tracked_symbols.append(latest_data["folder_symbol"])

    indices_table = ReportGenerator.render_indices_table(indices)

    rows = []
    for sym in tracked_symbols:
        if sym == latest_data["folder_symbol"]:
            d = latest_data
        else:
            d = {"folder_symbol": sym, "company_name": sym, "current_price": "View", "currency": "", "change_percent": 0.0, "rsi_14": "N/A"}

        change_badge = f"{d.get('change_percent', 0.0):+0.2f}%" if isinstance(d.get("change_percent"), (int, float)) else "N/A"
        price_str = f"{d.get('current_price')} {d.get('currency', '')}".strip()
        rows.append(
            f"| **[{sym}](./stocks/{sym}/README.md)** | {d.get('company_name', sym)} | "
            f"{price_str} | {change_badge} | {d.get('rsi_14')} | "
            f"[Latest](./stocks/{sym}/latest.md) • [News](./stocks/{sym}/news.md) • [History](./stocks/{sym}/history/) |"
        )

    portfolio_content = f"""# 🌐 Autonomous Cloud & Market Intelligence Hub
> **Real-Time Financial & Cloud Infrastructure Analytics Engine**
> Autonomously updated on every market session via GitHub Actions and Google Gemini 3.8 Flash.

---

## 🌍 1. Global & Domestic Market Indices Pulse

{indices_table}

---

## 📈 2. Tracked Enterprise & Infrastructure Stocks

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
    raw_ticker = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else "PERSISTENT"
    print(f"🚀 Initializing Autonomous AI Market Agent for input: '{raw_ticker}'...", flush=True)

    try:
        # Step 1: Query Domestic and Global Indices
        print("🌐 Step 1: Fetching Market Indices Pulse (Nifty 50, Sensex, Nifty IT, Nifty 500, Bank Nifty, S&P 500, Nasdaq)...", flush=True)
        indices = MarketDataFetcher.get_indices_pulse()
        for idx in indices:
            print(f"  📊 {idx['name']}: {idx['price']} {idx['currency']} ({idx['change_percent']:+0.2f}%)", flush=True)

        # Step 2: Resolve Ticker (smart NSE/BSE and global mapping)
        print(f"🔍 Step 2: Resolving symbol for '{raw_ticker}'...", flush=True)
        symbol_info = MarketDataFetcher.resolve_symbol(raw_ticker)
        print(f"✅ Symbol resolved: Query as '{symbol_info['query_symbol']}' (Folder: '{symbol_info['clean_symbol']}')", flush=True)

        # Step 3: Fetch 1-year historical chart data and technical indicators
        print(f"📡 Step 3: Fetching 1-year historical chart & indicators for '{symbol_info['query_symbol']}'...", flush=True)
        data = MarketDataFetcher.get_live_ticker_data(symbol_info)
        print(f"✅ Data fetched: {data['company_name']} ({data['current_price']} {data['currency']}) | SMA20: {data['sma_20']} | SMA50: {data['sma_50']} | SMA200: {data['sma_200']} | RSI: {data['rsi_14']}", flush=True)

        # Step 4: Fetch live breaking news
        print(f"📰 Step 4: Fetching live breaking news for '{data['folder_symbol']}'...", flush=True)
        news = MarketDataFetcher.get_live_news(data["symbol"])
        print(f"✅ Found {len(news)} live news headlines.", flush=True)

        # Step 5: Synthesize AI research report with Gemini 3.8 Flash
        print("🤖 Step 5: Invoking Google Gemini AI for cognitive synthesis...", flush=True)
        analyst = GeminiMarketAnalyst()
        ai_analysis = analyst.analyze_market_snapshot(data, indices, news)
        ai_analysis = clean_markdown_fences(ai_analysis)

        # Step 6: Generate reports & save
        print("📁 Step 6: Compiling Markdown dashboards and updating repository records...", flush=True)
        full_report_md = ReportGenerator.generate_full_report_markdown(data, indices, ai_analysis, news)
        news_md = ReportGenerator.generate_news_markdown(data, news)
        save_reports_and_sync_portfolio(data, indices, full_report_md, news_md)

        # Print output for runner console
        print(full_report_md, flush=True)

        # Step Summary for GitHub Actions Web UI
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
