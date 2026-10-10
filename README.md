# Multi-Currency Global Portfolio Management System

A production-grade, containerized global portfolio tracker (similar to Yahoo Finance) built with **FastAPI**, **Angular 18+**, **PostgreSQL 16**, and **Docker**.

---

## 🌟 Key Features

1. **Yahoo Finance Bulk Import Engine:**
   - Drag-and-drop ingestion of Yahoo Finance portfolio exports (CSV & Excel).
   - Auto-detection of local currencies and regions based on ticker suffixes (e.g. `.NS` for India/INR, `.T` for Tokyo/JPY, blank for US/USD).
   - Automatic sub-portfolio grouping and ledger creation with auto-cash funding.

2. **Master & Sub-Portfolio Structure:**
   - **Master Portfolio Rollup:** Real-time multi-currency valuation converted into your chosen Base Currency (`USD`, `INR`, `EUR`, `GBP`, `JPY`) using live foreign exchange rates.
   - **Regional Sub-Portfolios:** Country-specific portfolios (e.g., US Equities, India Growth, Japan Tech) with dedicated regional benchmark indices (S&P 500 `^GSPC`, NIFTY 50 `^NSEI`, Nikkei 225 `^N225`).
   - **Cash Wallets:** Dedicated cash pool balance per sub-portfolio. `BUY` transactions automatically deduct from available cash, while `SELL` and `DIVIDEND` credit funds back with real-time validation.

3. **Transaction Engine & Ledger:**
   - Transaction types: `BUY`, `SELL`, `CASH_DEPOSIT`, `CASH_WITHDRAWAL`, `DIVIDEND`.
   - Weighted average cost basis tracking, realized and unrealized P&L, and daily P&L.

4. **Automated Market Synchronization (`APScheduler`):**
   - Background polling worker running every 5 minutes.
   - Regional market trading hours awareness (NYSE, NSE, TSE, LSE, EURONEXT).
   - Live quotes, historical price bars, and FX rates fetched via `yfinance`.
   - Global **Refresh Now** button in the UI for instant on-demand sync.

5. **Corporate Actions & Dividends:**
   - Scrapes declared dividends and ex-dates from Yahoo Finance for owned tickers.
   - Automatically projects payouts: `Shares Owned * Declared Dividend per Share`.

6. **Analytics & Visualizations:**
   - Company-wise and Sector-wise interactive Donut charts powered by Chart.js.
   - Historical Portfolio Valuation Growth chart compared side-by-side with regional benchmark index normalized from inception (% return).
   - Live RSS news feed with financial sentiment analysis (Bullish / Bearish / Neutral) and key stats (P/E, Market Cap, 52W range).

---

## 🏗️ Architecture & Technology Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | Angular 18+ | Standalone Components, Reactive Forms, Tailwind CSS, Chart.js |
| **Backend** | Python 3.11 / FastAPI | Async endpoints, SQLAlchemy 2.0 ORM, Pydantic v2, APScheduler, yfinance |
| **Database** | PostgreSQL 16 | Relational schema, `NUMERIC(15, 4)` for financial precision |
| **Web Server** | Nginx Alpine | Reverse proxy for API and SPA routing |
| **Containers** | Docker & Compose | Multi-stage Dockerfiles for optimized production images |

---

## 🚀 Quick Start (Docker Compose)

### 1. Clone & Enter Project Directory
```bash
cd "stock portfolio tracker"
```

### 2. Start the Stack
```bash
docker compose up --build
```

### 3. Access Services
- **Web Application:** [http://localhost](http://localhost) (or [http://localhost:4200](http://localhost:4200))
- **FastAPI Interactive Docs (Swagger):** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **FastAPI OpenAPI Schema:** [http://localhost:8000/api/openapi.json](http://localhost:8000/api/openapi.json)
- **PostgreSQL Database:** `localhost:5432` (User: `portfolio_user`, DB: `portfolio_db`)

---

## 📁 Project Structure

```
├── docker-compose.yml          # Container orchestration (db, backend, frontend)
├── .env.example                # Environment variables template
├── init-db/
│   └── 01-init.sql             # PostgreSQL 16 schema & demo seeds
├── sample-data/
│   ├── yahoo_portfolio_sample.csv       # Sample Yahoo export (US, India, Japan)
│   └── yahoo_multi_currency_sample.csv  # Extended Yahoo export
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI entry point & lifespan
│       ├── core/               # Database and configuration
│       ├── models/             # SQLAlchemy models (NUMERIC 15,4)
│       ├── schemas/            # Pydantic v2 schemas
│       ├── services/           # yfinance, FX service, portfolio engine, scheduler
│       └── routers/            # REST API endpoints
└── frontend/
    ├── Dockerfile              # Multi-stage Angular build
    ├── nginx.conf              # Reverse proxy & SPA routing
    ├── package.json
    ├── angular.json
    └── src/
        ├── index.html
        ├── main.ts
        ├── styles.css          # Tailwind dark financial terminal theme
        └── app/
            ├── models/         # TypeScript interfaces
            ├── services/       # Portfolio, market, and toast services
            └── components/     # Navbar, Dashboard, Sub-portfolio, Modals, Charts
```

---

## 📊 Yahoo Finance CSV Import Guide

You can import any standard Yahoo Finance export file:
1. Navigate to the top navbar and click **"Import File"**.
2. Drag and drop `sample-data/yahoo_portfolio_sample.csv` or your own export file.
3. Select **"Auto-Detect & Group by Region"** to let the system automatically detect:
   - `AAPL`, `MSFT`, `NVDA` ➔ Assigned to **US Equities** (`USD`, Benchmark: `^GSPC`)
   - `RELIANCE.NS`, `TCS.NS` ➔ Assigned to **India Equities** (`INR`, Benchmark: `^NSEI`)
   - `7203.T`, `6758.T` ➔ Assigned to **Japan Equities** (`JPY`, Benchmark: `^N225`)
4. Check **"Auto-Fund Regional Cash Wallets"** to automatically initialize the cash pool for imported purchases.
5. Click **"Import & Sync Ledger"**.

---

## 💱 Multi-Currency & FX Engine

Exchange rates are fetched in real-time against `USD` and converted on-demand:
$$\text{Rate}(C_1 \to C_2) = \frac{\text{Rate}(\text{USD} \to C_2)}{\text{Rate}(\text{USD} \to C_1)}$$

When viewing the Master Dashboard in Base Currency $B$ (e.g. `INR`), each sub-portfolio $S$ in currency $C_s$ is converted as:
$$\text{Net Worth}_B = \sum_{S} \left( \text{Market Value}(S) + \text{Cash}(S) \right) \times \text{Rate}(C_s \to B)$$

---

## 📈 Benchmark Comparison Normalization

Portfolio growth and regional benchmark index are normalized from inception ($t_0$) to base 100% / % return:
$$\text{Return}_{\text{benchmark}}(t) = \frac{\text{Close}_{\text{benchmark}}(t) - \text{Close}_{\text{benchmark}}(t_0)}{\text{Close}_{\text{benchmark}}(t_0)} \times 100\%$$
Plotted side-by-side with historical portfolio return progression for fair visual comparison.
