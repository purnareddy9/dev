# 🌐 Autonomous Cloud & Market Intelligence Hub
> **Real-Time Financial & Cloud Infrastructure Analytics Engine**
> Autonomously updated on every market session via GitHub Actions and Google Gemini 3.8 Flash.

---

## 🌍 1. Global & Domestic Market Indices Pulse


| Index Benchmark | Live Level | 24h Change | Market Posture | Benchmark Sector Coverage |
| :--- | :--- | :--- | :--- | :--- |
| **NIFTY 50** (`^NSEI`) | **24,536.60 INR** | **+6.44%** (📈) | `🟢 BULLISH` | Indian Benchmark (Top 50 Blue-Chip Equities) |
| **SENSEX** (`^BSESN`) | **79,310.01 INR** | **+6.51%** (📈) | `🟢 BULLISH` | BSE Benchmark (Top 30 Established Companies) |
| **NIFTY IT** (`^CNXIT`) | **32,837.85 INR** | **+0.71%** (📈) | `🟢 BULLISH` | Indian Technology & Software Enterprise Sector |
| **NIFTY 500** (`^CRSLDX`) | **23,224.70 INR** | **+6.07%** (📈) | `🟢 BULLISH` | Indian Broad Market (Top 500 Across Large/Mid/Small-Cap) |
| **BANK NIFTY** (`^NSEBANK`) | **57,773.65 INR** | **+5.64%** (📈) | `🟢 BULLISH` | Indian Banking & Financial Services Sector |
| **S&P 500** (`^GSPC`) | **7,408.32 USD** | **-4.04%** (📉) | `🔴 BEARISH` | US Large-Cap Market Benchmark |
| **NASDAQ Composite** (`^IXIC`) | **24,485.80 USD** | **-6.49%** (📉) | `🔴 BEARISH` | Global Technology & Growth Benchmark |


---

## 🏛️ 2. Institutional Capital Flow Matrix (FII / DII Inflows & Outflows)
> *Official National Stock Exchange (NSE) Daily Institutional Cash Market Activity:*


| Institutional Segment | Gross Buy (₹ Cr) | Gross Sell (₹ Cr) | Net Inflow / Outflow (₹ Cr) | Institutional Posture | Session Date |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FII / FPI** (Foreign Institutions) | ₹31,797.86 Cr | ₹16,823.18 Cr | **+14,974.68 Cr** (🟢) | `🟢 AGGRESSIVE BUYING` | 05-Nov-2026 |
| **DII** (Domestic Mutual Funds / Banks) | ₹22,168.28 Cr | ₹32,612.82 Cr | **-10,444.54 Cr** (🔴) | `🔴 PROFIT BOOKING` | 05-Nov-2026 |
| **Combined Institutional Net** | **₹53,966.14 Cr** | **₹49,436.00 Cr** | **+4,530.14 Cr** (🟢) | `🟢 NET LIQUIDITY EXPANSION` | 05-Nov-2026 |


### FII vs DII Net Trading Flow
```mermaid
xychart-beta
    title "Institutional Net Cash Flow: FII vs DII (₹ Crores) - 05-Nov-2026"
    x-axis ["DII Net Flow", "FII/FPI Net Flow", "Combined Net"]
    y-axis "Net Value (₹ Cr)" -13055 --> 18718
    bar [-10444.54, 14974.68, 4530.14]
```

---

## 🧭 3. Daily Pre-Market & Post-Market Institutional Intelligence
- 📅 **[November 2, 2026: Institutional Order Flow & Macro Day-Trader Analysis](./daily-pulse/2026-11-02-day-trader-intelligence.md)**
  - *FII Net Buying Surge (+₹3,600 Cr)* | *US Election & Geopolitical Standoff (Iran / Qatar)*
  - *Gold/Silver Crash Breakdown (Binance $6.33B Hack Liquidation & Central Bank Sales)*
  - *Day Trader Pre/Post-Market Rules & Risk Management (Nithin Kamath Naked Option Warning)*
  - *Corporate Earnings Scorecards: Delhivery, Ramkrishna Forgings, Equitas SFB, Subex, Syrma SGS*

---

## 📈 4. Tracked Enterprise & Infrastructure Stocks

| Ticker | Company Name | Live Price | 24h Change | RSI (14) | Direct Reports |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **[NVDA](./stocks/NVDA/README.md)** | NVDA | View | +0.00% | N/A | [Latest](./stocks/NVDA/latest.md) • [News](./stocks/NVDA/news.md) • [History](./stocks/NVDA/history/) |
| **[PERSISTENT](./stocks/PERSISTENT/README.md)** | Persistent Systems Limited | 6109.5 INR | +4.28% | 66.41 | [Latest](./stocks/PERSISTENT/latest.md) • [News](./stocks/PERSISTENT/news.md) • [History](./stocks/PERSISTENT/history/) |

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
