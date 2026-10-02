import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "stock_analyzer.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Portfolio transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        shares REAL NOT NULL,
        buy_price REAL NOT NULL,
        buy_date TEXT,
        transaction_type TEXT DEFAULT 'BUY',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Check if transaction_type column exists (migration check)
    cursor.execute("PRAGMA table_info(portfolio)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "transaction_type" not in columns:
        cursor.execute("ALTER TABLE portfolio ADD COLUMN transaction_type TEXT DEFAULT 'BUY'")

    conn.commit()
    conn.close()

def bulk_insert_transactions(transactions: List[Dict[str, Any]], replace_all: bool = True) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    if replace_all:
        cursor.execute("DELETE FROM portfolio")

    inserted = 0
    batch = []
    for tx in transactions:
        sym = tx.get("symbol", "").upper().strip()
        shares = float(tx.get("shares", 0.0))
        price = float(tx.get("buy_price", 0.0))
        tx_type = tx.get("transaction_type", "BUY").upper().strip()
        date = tx.get("buy_date", "")
        notes = tx.get("notes", "")

        if sym and shares > 0:
            batch.append((sym, shares, price, date, tx_type, notes))
            inserted += 1

    cursor.executemany("""
        INSERT INTO portfolio (symbol, shares, buy_price, buy_date, transaction_type, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, batch)

    conn.commit()
    conn.close()
    return inserted

def get_aggregated_portfolio() -> List[Dict[str, Any]]:
    """
    Consolidates raw transactions into net active holdings per symbol.
    Nets BUY and SELL orders, calculating weighted average cost basis.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, symbol, shares, buy_price, transaction_type, buy_date FROM portfolio ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    holdings_dict: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        sym = row["symbol"].upper().strip()
        shares = float(row["shares"])
        price = float(row["buy_price"])
        tx_type = (row["transaction_type"] or "BUY").upper().strip()

        if sym not in holdings_dict:
            holdings_dict[sym] = {
                "symbol": sym,
                "net_shares": 0.0,
                "total_invested": 0.0,
                "buy_count": 0,
                "sell_count": 0,
                "earliest_date": row["buy_date"] or "",
                "latest_date": row["buy_date"] or ""
            }

        h = holdings_dict[sym]
        if tx_type == "SELL":
            h["net_shares"] -= shares
            # Reduce cost basis proportionally
            h["total_invested"] -= (shares * price)
            h["sell_count"] += 1
        else: # BUY
            h["net_shares"] += shares
            h["total_invested"] += (shares * price)
            h["buy_count"] += 1

        if row["buy_date"]:
            h["latest_date"] = row["buy_date"]

    active_holdings = []
    for sym, h in holdings_dict.items():
        net_shares = round(h["net_shares"], 4)
        if net_shares > 0.0001:
            # Weighted average price
            total_cost = max(0.0, h["total_invested"])
            avg_price = round(total_cost / net_shares, 2) if net_shares > 0 else 0.0
            active_holdings.append({
                "symbol": sym,
                "shares": net_shares,
                "avg_buy_price": avg_price,
                "cost_basis": round(total_cost, 2),
                "buy_count": h["buy_count"],
                "sell_count": h["sell_count"],
                "latest_date": h["latest_date"]
            })

    # Sort descending by cost basis by default
    active_holdings.sort(key=lambda x: x["cost_basis"], reverse=True)
    return active_holdings

def clear_portfolio() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted

def get_transaction_count() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM portfolio")
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0

def add_single_holding(symbol: str, shares: float, buy_price: float, buy_date: Optional[str] = None, notes: Optional[str] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO portfolio (symbol, shares, buy_price, buy_date, transaction_type, notes)
        VALUES (?, ?, ?, ?, 'BUY', ?)
    """, (symbol.upper().strip(), shares, buy_price, buy_date or "", notes or ""))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def delete_holding_by_symbol(symbol: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol.upper().strip(),))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

