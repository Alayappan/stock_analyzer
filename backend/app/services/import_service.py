import pandas as pd
import io
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException
import logging

from app.models.portfolio import Portfolio, SubPortfolio
from app.models.transaction import Transaction
from app.services.portfolio_engine import PortfolioEngine
from app.core.config import settings

logger = logging.getLogger(__name__)

# Regional detection from ticker suffix
REGION_MAP = {
    ".NS": {"country": "IN", "currency": "INR", "benchmark": "^NSEI", "name": "India Equities"},
    ".BO": {"country": "IN", "currency": "INR", "benchmark": "^NSEI", "name": "India Equities"},
    ".T": {"country": "JP", "currency": "JPY", "benchmark": "^N225", "name": "Japan Equities"},
    ".L": {"country": "GB", "currency": "GBP", "benchmark": "^FTSE", "name": "UK Equities"},
    ".DE": {"country": "EU", "currency": "EUR", "benchmark": "^STOXX50E", "name": "Europe Equities"},
    ".PA": {"country": "EU", "currency": "EUR", "benchmark": "^STOXX50E", "name": "Europe Equities"},
    ".AS": {"country": "EU", "currency": "EUR", "benchmark": "^STOXX50E", "name": "Europe Equities"},
    ".TO": {"country": "CA", "currency": "CAD", "benchmark": "^GSPTSE", "name": "Canada Equities"},
    ".HK": {"country": "HK", "currency": "HKD", "benchmark": "^HSI", "name": "Hong Kong Equities"},
}

def detect_region_for_ticker(ticker: str) -> Dict[str, str]:
    """Detect country, currency, benchmark, and name based on Yahoo Finance ticker suffix."""
    ticker_clean = ticker.strip().upper()
    for suffix, conf in REGION_MAP.items():
        if ticker_clean.endswith(suffix):
            return conf
    # Default to US
    return {"country": "US", "currency": "USD", "benchmark": "^GSPC", "name": "US Equities"}

class ImportService:
    @staticmethod
    def parse_file_to_dataframe(filename: str, content: bytes) -> pd.DataFrame:
        """Parse raw file content (CSV or Excel) into pandas DataFrame."""
        filename_lower = filename.lower()
        if filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
            return pd.read_excel(io.BytesIO(content))
        else:
            # Try UTF-8, then fallback to ISO-8859-1
            try:
                return pd.read_csv(io.BytesIO(content))
            except UnicodeDecodeError:
                return pd.read_csv(io.BytesIO(content), encoding="ISO-8859-1")

    @staticmethod
    def normalize_columns(df: pd.DataFrame) -> Dict[str, str]:
        """Map diverse Yahoo Finance CSV column variations to canonical fields."""
        column_mapping = {}
        for col in df.columns:
            clean = re.sub(r'[^a-zA-Z0-9]', '', str(col)).lower()
            if clean in ["symbol", "ticker", "tickersymbol", "code", "stock"]:
                column_mapping["ticker"] = col
            elif clean in ["tradedate", "date", "transactiondate", "purchasedate"]:
                column_mapping["date"] = col
            elif clean in ["quantity", "shares", "qty", "numshares"]:
                column_mapping["shares"] = col
            elif clean in ["purchaseprice", "price", "pricepaid", "costpershare", "currentprice"]:
                if "price" not in column_mapping or "purchase" in clean:
                    column_mapping["price"] = col
            elif clean in ["commission", "fee", "fees", "brokerage"]:
                column_mapping["fees"] = col
            elif clean in ["type", "transactiontype", "action"]:
                column_mapping["type"] = col
            elif clean in ["comment", "comments", "notes", "memo", "description"]:
                column_mapping["notes"] = col

        return column_mapping

    @staticmethod
    def parse_date(date_val: Any) -> datetime:
        """Safely parse various date formats into datetime object."""
        if pd.isna(date_val) or date_val is None:
            return datetime.utcnow()
        if isinstance(date_val, (datetime, pd.Timestamp)):
            return date_val.to_pydatetime()
        if isinstance(date_val, date):
            return datetime.combine(date_val, datetime.min.time())
        
        date_str = str(date_val).strip()
        # Handle formats: 20240115, 2024-01-15, 01/15/2024, etc.
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%m/%d/%Y", "%d/%m/%Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                pass
        return datetime.utcnow()

    @staticmethod
    async def import_portfolio_data(
        filename: str,
        content: bytes,
        portfolio_id: int,
        target_sub_portfolio_id: Optional[int],
        auto_fund_cash: bool,
        session: AsyncSession,
        skip_duplicates: bool = True,
        replace_existing: bool = False
    ) -> Dict[str, Any]:
        """Main ingestion engine for Yahoo Finance portfolio files with duplicate detection."""
        # 1. Verify Master Portfolio exists
        stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
        res = await session.execute(stmt)
        portfolio = res.scalar_one_or_none()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Master portfolio not found")

        # 2. Parse file to DataFrame
        try:
            df = ImportService.parse_file_to_dataframe(filename, content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

        if df.empty:
            raise HTTPException(status_code=400, detail="Uploaded file contains no data")

        # 3. Detect columns
        col_map = ImportService.normalize_columns(df)
        if "ticker" not in col_map:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required 'Symbol' or 'Ticker' column in file. Found columns: {list(df.columns)}"
            )

        # 4. Fetch existing sub-portfolios for auto-matching
        stmt_subs = select(SubPortfolio).where(SubPortfolio.portfolio_id == portfolio_id)
        res_subs = await session.execute(stmt_subs)
        sub_portfolios = list(res_subs.scalars().all())

        imported_count = 0
        duplicates_skipped = 0
        skipped_count = 0
        created_subportfolios = []
        rows_by_subportfolio: Dict[int, List[Dict[str, Any]]] = {}

        # 5. Process each row
        for idx, row in df.iterrows():
            raw_ticker = row[col_map["ticker"]]
            if pd.isna(raw_ticker) or not str(raw_ticker).strip():
                skipped_count += 1
                continue
            ticker = str(raw_ticker).strip().upper()

            # Parse shares and price
            shares_raw = row[col_map["shares"]] if "shares" in col_map and not pd.isna(row[col_map["shares"]]) else 1
            price_raw = row[col_map["price"]] if "price" in col_map and not pd.isna(row[col_map["price"]]) else 0
            fees_raw = row[col_map["fees"]] if "fees" in col_map and not pd.isna(row[col_map["fees"]]) else 0
            date_raw = row[col_map["date"]] if "date" in col_map and not pd.isna(row[col_map["date"]]) else None
            notes_raw = row[col_map["notes"]] if "notes" in col_map and not pd.isna(row[col_map["notes"]]) else "Yahoo Finance Import"
            type_raw = str(row[col_map["type"]]).strip().upper() if "type" in col_map and not pd.isna(row[col_map["type"]]) else "BUY"

            try:
                shares = Decimal(str(abs(float(shares_raw))))
                price = Decimal(str(abs(float(price_raw))))
                fees = Decimal(str(abs(float(fees_raw))))
            except (ValueError, TypeError):
                skipped_count += 1
                continue

            if shares <= 0:
                skipped_count += 1
                continue

            exec_date = ImportService.parse_date(date_raw)

            # Determine Target Sub-Portfolio
            target_sub_id = target_sub_portfolio_id
            if not target_sub_id:
                region_info = detect_region_for_ticker(ticker)
                # Find matching sub-portfolio by country or currency
                matched_sub = next(
                    (s for s in sub_portfolios if s.currency == region_info["currency"] or s.country == region_info["country"]),
                    None
                )
                if not matched_sub:
                    # Automatically create matching sub-portfolio
                    matched_sub = SubPortfolio(
                        portfolio_id=portfolio_id,
                        name=region_info["name"],
                        country=region_info["country"],
                        currency=region_info["currency"],
                        benchmark_ticker=region_info["benchmark"],
                        cash_balance=Decimal("0.0000")
                    )
                    session.add(matched_sub)
                    await session.commit()
                    await session.refresh(matched_sub)
                    sub_portfolios.append(matched_sub)
                    created_subportfolios.append(matched_sub.name)
                target_sub_id = matched_sub.id

            if target_sub_id not in rows_by_subportfolio:
                rows_by_subportfolio[target_sub_id] = []

            rows_by_subportfolio[target_sub_id].append({
                "ticker": ticker,
                "shares": shares,
                "price": price,
                "fees": fees,
                "date": exec_date,
                "notes": str(notes_raw),
                "type": "SELL" if "SELL" in type_raw else "BUY"
            })

        # Helper signature generator for deduplication
        def make_sig(t_type: str, t_ticker: Optional[str], t_shares: Any, t_price: Any, t_date: Any) -> Tuple:
            d_str = t_date.strftime("%Y-%m-%d") if hasattr(t_date, "strftime") else str(t_date)[:10]
            return (
                (t_type or "").upper(),
                (t_ticker or "").strip().upper(),
                round(Decimal(str(t_shares or 0)), 4),
                round(Decimal(str(t_price or 0)), 4),
                d_str
            )

        # 6. Fund cash wallet if requested and execute transactions
        for sub_id, tx_rows in rows_by_subportfolio.items():
            # Get sub-portfolio
            stmt_s = select(SubPortfolio).where(SubPortfolio.id == sub_id)
            res_s = await session.execute(stmt_s)
            sub_p = res_s.scalar_one()

            # Handle replace_existing if requested
            if replace_existing:
                logger.info(f"Replace existing enabled: wiping transactions for sub-portfolio {sub_id}")
                await session.execute(delete(Transaction).where(Transaction.sub_portfolio_id == sub_id))
                sub_p.cash_balance = Decimal("0.0000")
                await session.commit()
                await session.refresh(sub_p)

            # Sort transactions chronologically: BUY first then SELL on the same timestamp
            tx_rows.sort(key=lambda x: (x["date"], 0 if x["type"] == "BUY" else 1))

            # Deduplication: check against existing transactions in this sub-portfolio
            rows_to_execute = []
            if skip_duplicates and not replace_existing:
                stmt_existing = select(Transaction).where(Transaction.sub_portfolio_id == sub_id)
                res_existing = await session.execute(stmt_existing)
                existing_txs = res_existing.scalars().all()

                existing_counts = Counter(
                    make_sig(t.type, t.ticker, t.shares, t.price_per_share, t.executed_at)
                    for t in existing_txs
                    if t.type in ("BUY", "SELL")
                )
                incoming_counts = Counter()

                for r in tx_rows:
                    sig = make_sig(r["type"], r["ticker"], r["shares"], r["price"], r["date"])
                    incoming_counts[sig] += 1
                    if incoming_counts[sig] <= existing_counts[sig]:
                        duplicates_skipped += 1
                        continue
                    rows_to_execute.append(r)
            else:
                rows_to_execute = tx_rows

            # Calculate total cash required ONLY for new non-skipped BUY transactions
            total_buy_cash = Decimal("0.0000")
            for r in rows_to_execute:
                if r["type"] == "BUY":
                    total_buy_cash += (r["shares"] * r["price"]) + r["fees"]

            if auto_fund_cash and total_buy_cash > 0 and sub_p.cash_balance < total_buy_cash:
                needed_deposit = round(total_buy_cash - sub_p.cash_balance + Decimal("1000.00"), 4)
                # Auto deposit initial capital
                sub_p.cash_balance += needed_deposit
                deposit_tx = Transaction(
                    sub_portfolio_id=sub_id,
                    type="CASH_DEPOSIT",
                    ticker=None,
                    shares=None,
                    price_per_share=None,
                    fees=Decimal("0.0000"),
                    total_amount=needed_deposit,
                    currency=sub_p.currency,
                    executed_at=datetime.utcnow(),
                    notes=f"Auto-Fund Initial Capital for Yahoo Finance Import"
                )
                session.add(deposit_tx)
                await session.commit()
                await session.refresh(sub_p)

            # Execute individual transactions
            for r in rows_to_execute:
                try:
                    await PortfolioEngine.execute_transaction(
                        sub_portfolio_id=sub_id,
                        tx_type=r["type"],
                        ticker=r["ticker"],
                        shares=r["shares"],
                        price_per_share=r["price"],
                        fees=r["fees"],
                        total_amount=None,
                        executed_at=r["date"],
                        notes=r["notes"],
                        session=session
                    )
                    imported_count += 1
                except Exception as e:
                    logger.warning(f"Error executing imported row {r}: {e}")
                    skipped_count += 1

        return {
            "status": "success",
            "filename": filename,
            "total_rows_parsed": len(df),
            "transactions_imported": imported_count,
            "duplicates_skipped": duplicates_skipped,
            "rows_skipped": skipped_count,
            "created_subportfolios": list(set(created_subportfolios)),
            "sub_portfolios_affected": len(rows_by_subportfolio)
        }
