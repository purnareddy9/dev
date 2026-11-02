#!/usr/bin/env python3
"""
==============================================================================
Serverless Real-Time AI Stock & Provider Market Analyst Agent
Designed to run on GitHub Actions & Local Workstations
==============================================================================
Pulls REAL live financial market data, calculates quantitative technical metrics,
and invokes Google Gemini to perform autonomous investment thesis reasoning.
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


class MarketDataFetcher:
    """Fetches real live stock market prices and historical trends."""

    @staticmethod
    def get_live_ticker_data(symbol: str) -> Dict[str, Any]:
        """Queries real-time live stock price and 5-day market data."""
        clean_symbol = symbol.strip().upper()
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_symbol}?interval=1d&range=5d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        result = data["chart"]["result"][0]
        meta = result["meta"]
        indicators = result["indicators"]["quote"][0]
        closes = [round(c, 2) for c in indicators.get("close", []) if c is not None]

        current_price = meta.get("regularMarketPrice", closes[-1] if closes else 0.0)
        previous_close = meta.get("chartPreviousClose", closes[-2] if len(closes) > 1 else current_price)
        change_pct = round(((current_price - previous_close) / previous_close) * 100, 2) if previous_close else 0.0

        return {
            "symbol": clean_symbol,
            "currency": meta.get("currency", "USD"),
            "current_price": current_price,
            "previous_close": previous_close,
            "change_percent": change_pct,
            "52_week_high": meta.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": meta.get("fiftyTwoWeekLow", "N/A"),
            "recent_closes": closes,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(meta.get("regularMarketTime", time.time())))
        }


class GeminiMarketAnalyst:
    """Connects to Google Gemini API to analyze market trends and generate investment thesis."""

    def __init__(self):
        raw_key = os.getenv("GEMINI_API_KEY") or ""
        self.api_key = raw_key.strip().strip('"').strip("'")

    def analyze_market_snapshot(self, ticker_data: Dict[str, Any]) -> str:
        """Prompts Gemini with live market metrics for quantitative and fundamental analysis."""
        if not self.api_key:
            print("ℹ️ GEMINI_API_KEY secret not detected. Using algorithmic quantitative engine.", flush=True)
            return self._fallback_quantitative_analysis(ticker_data)

        print(f"🔑 GEMINI_API_KEY detected (length: {len(self.api_key)} chars). Invoking Google Gemini AI...", flush=True)

        prompt = (
            f"You are a Senior Quantitative Equity Analyst and SRE FinOps Agent.\n"
            f"Analyze this real-time stock market data for ticker {ticker_data['symbol']}:\n"
            f"- Current Price: ${ticker_data['current_price']} {ticker_data['currency']}\n"
            f"- 24h Change: {ticker_data['change_percent']}%\n"
            f"- 52-Week Range: ${ticker_data['52_week_low']} - ${ticker_data['52_week_high']}\n"
            f"- Recent 5-Day Close Prices: {ticker_data['recent_closes']}\n\n"
            f"Provide a concise, professional analysis in GitHub Markdown:\n"
            f"1. **Market Sentiment & Technical Trend** (Bullish/Bearish/Neutral based on 5-day trajectory)\n"
            f"2. **Key Valuation & Risk Factors** (Cloud/Tech sector exposure, volatility)\n"
            f"3. **Actionable SRE & Platform Strategy** (FinOps hedging, infrastructure budget impact if this is a cloud provider like GOOGL, MSFT, AMZN, or NVDA)\n"
            f"4. **Executive Verdict** (Buy / Hold / Reduce rating with clear rationale)"
        )

        # Primary: Official Native Google Gemini REST Endpoint
        # Priority order updated for latest Gemini generation API models
        models_to_try = [
            "gemini-3.5-flash-lite",
            "gemini-3.8-flash",
            "gemini-flash-latest",
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
                with urllib.request.urlopen(req, timeout=25) as resp:
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
        # Fallback to algorithmic quantitative analysis if all endpoints fail
        return self._fallback_quantitative_analysis(ticker_data)

    def _fallback_quantitative_analysis(self, data: Dict[str, Any]) -> str:
        """Deterministic quantitative analysis if GEMINI_API_KEY is not set."""
        trend = "BULLISH 🟢" if data["change_percent"] > 0 else "BEARISH 🔴"
        return f"""
### 📊 Quantitative Market Analysis (Algorithmic Engine)

- **Sentiment**: **{trend}** ({data['change_percent']:+0.2f}% change today)
- **Technical Position**: Current price `${data['current_price']}` is trading within the 52-week range (`${data['52_week_low']}` – `${data['52_week_high']}`).
- **5-Day Momentum**: Trajectory closes: `{data['recent_closes']}`.
- **FinOps Cloud Provider Note**: If this ticker represents an infrastructure provider (e.g. AWS/Azure/GCP/NVIDIA), current price momentum indicates steady enterprise compute and AI infrastructure demand.

> *Note: Set `GEMINI_API_KEY` in GitHub Repository Secrets to unlock Deep Cognitive LLM Reasoning.*
"""


def generate_github_step_summary(ticker_data: Dict[str, Any], ai_analysis: str):
    """Outputs a rich Markdown dashboard into GitHub Actions $GITHUB_STEP_SUMMARY and local file."""
    change_emoji = "📈" if ticker_data["change_percent"] >= 0 else "📉"
    
    summary_md = f"""
# {change_emoji} Real-Time AI Stock & Provider Market Analysis: {ticker_data['symbol']}

| Metric | Live Market Value |
| :--- | :--- |
| **Ticker Symbol** | `{ticker_data['symbol']}` |
| **Current Live Price** | **${ticker_data['current_price']} {ticker_data['currency']}** |
| **24h Price Change** | **{ticker_data['change_percent']:+0.2f}%** |
| **Previous Close** | ${ticker_data['previous_close']} |
| **52-Week Range** | ${ticker_data['52_week_low']} – ${ticker_data['52_week_high']} |
| **Data Timestamp** | {ticker_data['timestamp']} |

---

## 🤖 AI Investment & Cloud Provider Intelligence Report

{ai_analysis}

---
*Report generated autonomously by **GitHub Actions Real-Time AI Agent**.*
"""

    # Force immediate unbuffered flush to stdout
    print(summary_md, flush=True)

    # Save to local file so shell steps can read it directly
    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_report.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(summary_md)

    # If running inside GitHub Actions, write directly to GITHUB_STEP_SUMMARY
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(summary_md)


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else "NVDA"
    print(f"📡 Querying live real-time market data for '{ticker}'...", flush=True)
    
    try:
        data = MarketDataFetcher.get_live_ticker_data(ticker)
        print(f"✅ Data fetched: ${data['current_price']} ({data['change_percent']:+0.2f}%)", flush=True)
        analyst = GeminiMarketAnalyst()
        analysis = analyst.analyze_market_snapshot(data)
        generate_github_step_summary(data, analysis)
        print("🎉 Agent execution finished successfully!", flush=True)
    except Exception as e:
        print(f"❌ Error during market agent execution: {e}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
