# 💼 PortfolioPulse - Yahoo Finance Portfolio & Holding Analyzer

A dedicated, executive-grade portfolio and holding analysis application powered by **FastAPI** and **Yahoo Finance**. Designed specifically for deep portfolio analytics, risk profiling, fundamental holding analysis, and bulk transaction processing.

---

## 🚀 Key Highlights & What Was Built

### 1. 📁 Bulk Portfolio Upload & 1-Click Import
- **Instant 1-Click Import**: Directly loads and analyzes the workspace's `portfolio.csv` (**1,552 historical transactions**).
- **Drag-and-Drop CSV Uploader**: Supports Yahoo Finance exported CSVs as well as standard broker trade logs.
- **Smart Transaction Aggregator**:
  - Automatically nets **BUY** and **SELL** orders per stock.
  - Accurately computes net share quantity and weighted average purchase price.
  - Automatically filters closed positions and shows only active holdings (34 unique active stocks).
  - Mode choice: **Replace** or **Append** transactions.

### 2. 🏛️ Executive Portfolio KPI Dashboard
- **Total Portfolio Market Value**: Live valuation across all active holdings.
- **Total Invested Capital (Cost Basis)**: Exact capital deployed.
- **Unrealized Profit & Loss**: Net gain/loss in dollars/rupees and total percentage return (`+XX.XX%`).
- **Today's Intraday P&L**: Today's dollar movement and intraday portfolio change percentage.
- **Annual Dividend Income**: Projected annual dividend payout across all positions and overall **Portfolio Dividend Yield %**.
- **Portfolio Weighted Beta (Risk Index)**: Aggregate portfolio volatility relative to the market index (indicates Conservative / Moderate / High Growth).
- **Weighted Average P/E Ratio**: Aggregate portfolio valuation multiple.

### 3. 📊 Diversification & Risk Analytics
- **Sector & Asset Class Allocation**:
  - Interactive multi-segment colored allocation bar.
  - Detailed breakdown of capital deployed across Financial Services, Technology, Industrials, Energy, Healthcare, Commodities/Gold, etc.
- **Market Cap Distribution**: Breakdown across Large Cap, Mid Cap, and Small Cap.
- **Performance Highlights**: Instant view of your Top Gainers and Top Laggards.

### 4. 📑 Comprehensive Holdings Table (Yahoo Finance Analytics)
Every holding is enriched with real-time Yahoo Finance metrics:
- **Stock / Asset**: Symbol, Full Company Name, Sector tag.
- **Holding Stats**: Net shares held, volume-weighted average buy price.
- **Live Price & Day Change**: Current price and today's dollar / percentage delta.
- **Position Values**: Current Market Value and Total Invested Cost Basis.
- **Total Return**: Unrealized P&L ($ and %) with color-coded badges.
- **Portfolio Weight %**: Visual progress bar showing allocation weight.
- **Valuation Multiples**: Trailing P/E (TTM).
- **Dividends**: Dividend Yield % and projected annual dividend cashflow per position.
- **Risk Indicators**: Beta (5Y) and 52-Week Range indicator bar.
- **Analyst Consensus**: Wall Street / Street recommendation badge (Buy / Hold / Sell) and target price upside potential.
- **Interactive Controls**:
  - Click any table header to sort ascending / descending.
  - Filter tabs: `All Holdings`, `Profitable Only`, `Losses Only`, `Dividend Payers`.
  - Search filter: find any symbol, name, or sector in milliseconds.

### 5. 🔍 Deep-Dive Holding Modal
Clicking **"Analyze"** on any holding opens a deep fundamental inspector:
- **Valuation Multiples**: Trailing P/E, Forward P/E, Price-to-Book (P/B), Price-to-Sales (P/S), EV/EBITDA, PEG ratio, EPS.
- **Profitability & Margins**: Operating Margin %, Profit Margin %, Return on Equity (ROE) %, Return on Assets (ROA) %.
- **Solvency & Health**: Total Cash, Total Debt, Debt-to-Equity, Operating Cash Flow, Levered Free Cash Flow.
- **Analyst Forecasts**: Consensus Rating, Target Mean Price, Upside Potential %, Analyst Count.
- **Company Profile**: Business summary, sector, industry, website, full-time employees.
- **Recent News**: Latest Yahoo Finance headlines and articles.

### 6. 📥 Export Analyzed Portfolio
- One-click export of the entire analyzed portfolio to CSV with all computed Yahoo Finance metrics.

---

## ⚡ How to Run

1. Open your terminal in the project directory:
   ```bash
   cd "/Users/kamalesh/Downloads/Stock analyzer"
   ```

2. Start the server (and automatically open the browser):
   ```bash
   ./venv/bin/python3 run.py
   ```
   Or:
   ```bash
   ./venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```

3. Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

