-- ====================================================================
-- PostgreSQL 16 Schema for Multi-Currency Global Portfolio Management
-- High precision financial columns use NUMERIC(15, 4) or NUMERIC(15, 6)
-- ====================================================================

-- 1. Master Portfolios
CREATE TABLE IF NOT EXISTS portfolios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Regional Sub-Portfolios
CREATE TABLE IF NOT EXISTS sub_portfolios (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(10) NOT NULL DEFAULT 'US',
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    benchmark_ticker VARCHAR(50) NOT NULL DEFAULT '^GSPC',
    cash_balance NUMERIC(15, 4) NOT NULL DEFAULT 0.0000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Transaction Ledger
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    sub_portfolio_id INTEGER NOT NULL REFERENCES sub_portfolios(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL, -- BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAWAL, DIVIDEND
    ticker VARCHAR(50),
    shares NUMERIC(15, 4),
    price_per_share NUMERIC(15, 4),
    fees NUMERIC(15, 4) NOT NULL DEFAULT 0.0000,
    total_amount NUMERIC(15, 4) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Real-time Market Cache
CREATE TABLE IF NOT EXISTS market_cache (
    ticker VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    current_price NUMERIC(15, 4) NOT NULL,
    previous_close NUMERIC(15, 4) NOT NULL,
    day_change NUMERIC(15, 4) NOT NULL DEFAULT 0.0000,
    day_change_percent NUMERIC(15, 4) NOT NULL DEFAULT 0.0000,
    pe_ratio NUMERIC(15, 4),
    market_cap NUMERIC(20, 2),
    dividend_yield NUMERIC(15, 4),
    fifty_two_week_high NUMERIC(15, 4),
    fifty_two_week_low NUMERIC(15, 4),
    sector VARCHAR(100),
    industry VARCHAR(100),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Foreign Exchange Rates
CREATE TABLE IF NOT EXISTS fx_rates (
    from_currency VARCHAR(10) NOT NULL,
    to_currency VARCHAR(10) NOT NULL,
    rate NUMERIC(15, 6) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (from_currency, to_currency)
);

-- 6. Corporate Actions & Dividends Schedule
CREATE TABLE IF NOT EXISTS dividends (
    id SERIAL PRIMARY KEY,
    sub_portfolio_id INTEGER NOT NULL REFERENCES sub_portfolios(id) ON DELETE CASCADE,
    ticker VARCHAR(50) NOT NULL,
    ex_date DATE,
    record_date DATE,
    payment_date DATE,
    dividend_per_share NUMERIC(15, 4) NOT NULL,
    projected_payout NUMERIC(15, 4) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ANNOUNCED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for optimal query performance
CREATE INDEX IF NOT EXISTS idx_sub_portfolios_portfolio_id ON sub_portfolios(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_transactions_sub_portfolio_id ON transactions(sub_portfolio_id);
CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON transactions(ticker);
CREATE INDEX IF NOT EXISTS idx_transactions_executed_at ON transactions(executed_at);
CREATE INDEX IF NOT EXISTS idx_dividends_sub_portfolio_id ON dividends(sub_portfolio_id);
CREATE INDEX IF NOT EXISTS idx_dividends_ticker ON dividends(ticker);

-- Seed initial master portfolio and default sub-portfolios for quick-start demo
INSERT INTO portfolios (id, name, description, base_currency)
VALUES (1, 'Global Wealth Master', 'Global diversified holdings across US, India, Japan, and Europe', 'USD')
ON CONFLICT (id) DO NOTHING;

INSERT INTO sub_portfolios (id, portfolio_id, name, country, currency, benchmark_ticker, cash_balance)
VALUES 
    (1, 1, 'US Bluechips & Tech', 'US', 'USD', '^GSPC', 15000.0000),
    (2, 1, 'India Growth Equities', 'IN', 'INR', '^NSEI', 450000.0000),
    (3, 1, 'Japan High-Tech & Auto', 'JP', 'JPY', '^N225', 1200000.0000)
ON CONFLICT (id) DO NOTHING;

-- Reset sequence generator to match seeded IDs
SELECT setval('portfolios_id_seq', (SELECT MAX(id) FROM portfolios));
SELECT setval('sub_portfolios_id_seq', (SELECT MAX(id) FROM sub_portfolios));

-- Initial Demo Holdings
INSERT INTO transactions (id, sub_portfolio_id, type, ticker, shares, price_per_share, fees, total_amount, currency, notes)
VALUES
    (1, 1, 'BUY', 'AAPL', 40.0000, 185.5000, 0.0000, 7420.0000, 'USD', 'Core Apple Position'),
    (2, 1, 'BUY', 'MSFT', 25.0000, 402.1000, 0.0000, 10052.5000, 'USD', 'Microsoft AI & Cloud'),
    (3, 1, 'BUY', 'NVDA', 20.0000, 118.0000, 0.0000, 2360.0000, 'USD', 'NVIDIA GPU Acceleration'),
    (4, 2, 'BUY', 'RELIANCE.NS', 100.0000, 2850.0000, 50.0000, 285050.0000, 'INR', 'Reliance Industries Core'),
    (5, 2, 'BUY', 'TCS.NS', 60.0000, 4120.0000, 30.0000, 247230.0000, 'INR', 'Tata Consultancy Services'),
    (6, 3, 'BUY', '7203.T', 300.0000, 2850.0000, 500.0000, 855500.0000, 'JPY', 'Toyota Motor Japan'),
    (7, 3, 'BUY', '6758.T', 100.0000, 12600.0000, 500.0000, 1260500.0000, 'JPY', 'Sony Group Entertainment')
ON CONFLICT (id) DO NOTHING;

SELECT setval('transactions_id_seq', (SELECT MAX(id) FROM transactions));

