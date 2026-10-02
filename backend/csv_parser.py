import io
from typing import List, Dict, Any, Tuple

def parse_portfolio_csv_content(content: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parses CSV content representing a portfolio of transactions or holdings.
    Handles:
    1. Yahoo Finance exported portfolio CSVs (with Symbol, Purchase Price, Quantity, Trade Date, Transaction Type)
    2. Generic CSVs with Symbol, Shares/Quantity, Price/Buy Price, Date
    3. Handles potential unescaped commas in comments/descriptions safely
    """
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return [], {"total_rows": 0, "parsed_transactions": 0, "unique_symbols": 0}

    header_line = lines[0]
    headers = [h.strip() for h in header_line.split(",")]

    sym_idx = 0
    price_idx = -1
    qty_idx = -1
    date_idx = -1
    type_idx = -1

    for i, h in enumerate(headers):
        h_lower = h.lower().strip()
        if "symbol" in h_lower or "ticker" in h_lower:
            sym_idx = i
        elif "purchase price" in h_lower or "buy price" in h_lower or "cost" in h_lower or (h_lower == "price" and price_idx == -1):
            price_idx = i
        elif "quantity" in h_lower or "shares" in h_lower or "qty" in h_lower:
            qty_idx = i
        elif "trade date" in h_lower or (h_lower == "date" and date_idx == -1):
            date_idx = i
        elif "transaction type" in h_lower or "type" in h_lower:
            type_idx = i

    # Fallbacks if columns weren't matched by name
    if price_idx == -1 and len(headers) >= 3:
        price_idx = 2
    if qty_idx == -1 and len(headers) >= 2:
        qty_idx = 1

    transactions = []

    for line in lines[1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue

        sym = parts[sym_idx].upper().strip() if len(parts) > sym_idx else ""
        if not sym or sym == "SYMBOL" or sym == "TICKER":
            continue

        # Transaction type detection (BUY vs SELL)
        trans_type = "BUY"
        # Check the last element first if standard Yahoo format
        if len(parts) > 0 and parts[-1].upper() in ["BUY", "SELL"]:
            trans_type = parts[-1].upper()
        elif type_idx != -1 and len(parts) > type_idx and parts[type_idx].upper() in ["BUY", "SELL"]:
            trans_type = parts[type_idx].upper()

        # Parse quantity and price safely
        qty = 0.0
        if qty_idx != -1 and len(parts) > qty_idx:
            val_str = parts[qty_idx].replace("$", "").replace(",", "").strip()
            try:
                qty = float(val_str)
            except ValueError:
                qty = 0.0

        price = 0.0
        if price_idx != -1 and len(parts) > price_idx:
            val_str = parts[price_idx].replace("$", "").replace(",", "").strip()
            try:
                price = float(val_str)
            except ValueError:
                price = 0.0

        trade_date = ""
        if date_idx != -1 and len(parts) > date_idx:
            trade_date = parts[date_idx].strip()

        if qty > 0 and price >= 0:
            transactions.append({
                "symbol": sym,
                "shares": qty,
                "buy_price": price,
                "transaction_type": trans_type,
                "buy_date": trade_date,
                "notes": f"{trans_type} transaction"
            })

    unique_syms = len(set(t["symbol"] for t in transactions))
    stats = {
        "total_rows": len(lines) - 1,
        "parsed_transactions": len(transactions),
        "unique_symbols": unique_syms
    }

    return transactions, stats
