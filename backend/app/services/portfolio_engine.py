from decimal import Decimal
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException

from app.models.portfolio import Portfolio, SubPortfolio
from app.models.transaction import Transaction, TransactionType
from app.models.market import MarketCache, DividendSchedule
from app.schemas.portfolio import (
    HoldingOut, SubPortfolioDetailOut, MasterRollupOut, SubPortfolioSummaryConverted
)
from app.services.market_data import MarketDataService
from app.services.fx_service import FxService
import logging

logger = logging.getLogger(__name__)

class PortfolioEngine:
    @staticmethod
    async def get_or_update_market_cache(ticker: str, session: AsyncSession, force_refresh: bool = False) -> MarketCache:
        """Get cached quote or fetch and persist to market_cache table."""
        stmt = select(MarketCache).where(MarketCache.ticker == ticker)
        res = await session.execute(stmt)
        cached = res.scalar_one_or_none()
        
        # If cache exists and is fresh (less than 5 mins old) and not force_refresh, reuse
        if not force_refresh and cached and cached.last_updated and (datetime.utcnow() - cached.last_updated.replace(tzinfo=None)).total_seconds() < 300:
            return cached
            
        # Fetch fresh quote
        q = MarketDataService.get_ticker_quote(ticker)
        if not cached:
            cached = MarketCache(
                ticker=ticker,
                name=q["name"],
                currency=q["currency"],
                current_price=q["current_price"],
                previous_close=q["previous_close"],
                day_change=q["day_change"],
                day_change_percent=q["day_change_percent"],
                pe_ratio=q["pe_ratio"],
                market_cap=q["market_cap"],
                dividend_yield=q["dividend_yield"],
                fifty_two_week_high=q["fifty_two_week_high"],
                fifty_two_week_low=q["fifty_two_week_low"],
                sector=q["sector"],
                industry=q["industry"],
                last_updated=datetime.utcnow()
            )
            session.add(cached)
        else:
            cached.name = q["name"]
            cached.currency = q["currency"]
            cached.current_price = q["current_price"]
            cached.previous_close = q["previous_close"]
            cached.day_change = q["day_change"]
            cached.day_change_percent = q["day_change_percent"]
            cached.pe_ratio = q["pe_ratio"]
            cached.market_cap = q["market_cap"]
            cached.dividend_yield = q["dividend_yield"]
            cached.fifty_two_week_high = q["fifty_two_week_high"]
            cached.fifty_two_week_low = q["fifty_two_week_low"]
            cached.sector = q["sector"]
            cached.industry = q["industry"]
            cached.last_updated = datetime.utcnow()
            
        await session.commit()
        await session.refresh(cached)
        return cached

    @staticmethod
    async def calculate_sub_portfolio_holdings(sub_portfolio_id: int, session: AsyncSession) -> SubPortfolioDetailOut:
        """Calculate live holdings, cost basis, realized/unrealized P&L, and daily P&L for a sub-portfolio."""
        # 1. Fetch sub-portfolio
        stmt = select(SubPortfolio).where(SubPortfolio.id == sub_portfolio_id)
        res = await session.execute(stmt)
        sub_p = res.scalar_one_or_none()
        if not sub_p:
            raise HTTPException(status_code=404, detail="Sub-portfolio not found")

        # 2. Fetch all transactions ordered by execution time
        stmt_tx = select(Transaction).where(Transaction.sub_portfolio_id == sub_portfolio_id).order_by(Transaction.executed_at.asc())
        res_tx = await session.execute(stmt_tx)
        transactions = res_tx.scalars().all()

        # 3. Aggregate position by ticker
        holdings_map: Dict[str, Dict[str, Any]] = {}
        for tx in transactions:
            if not tx.ticker:
                continue
            ticker = tx.ticker.strip().upper()
            if ticker not in holdings_map:
                holdings_map[ticker] = {
                    "shares": Decimal("0.0000"),
                    "total_cost": Decimal("0.0000"),
                    "avg_cost": Decimal("0.0000"),
                    "realized_pnl": Decimal("0.0000")
                }
            
            pos = holdings_map[ticker]
            if tx.type == "BUY":
                shares_bought = tx.shares or Decimal("0")
                price = tx.price_per_share or Decimal("0")
                fees = tx.fees or Decimal("0")
                new_shares = pos["shares"] + shares_bought
                new_cost = pos["total_cost"] + (shares_bought * price) + fees
                pos["shares"] = new_shares
                pos["total_cost"] = new_cost
                pos["avg_cost"] = (new_cost / new_shares) if new_shares > 0 else Decimal("0")
            elif tx.type == "SELL":
                shares_sold = tx.shares or Decimal("0")
                sell_price = tx.price_per_share or Decimal("0")
                fees = tx.fees or Decimal("0")
                if shares_sold > 0:
                    cost_portion = pos["avg_cost"] * shares_sold
                    proceeds = (shares_sold * sell_price) - fees
                    pos["realized_pnl"] += (proceeds - cost_portion)
                    pos["shares"] = max(Decimal("0"), pos["shares"] - shares_sold)
                    pos["total_cost"] = pos["shares"] * pos["avg_cost"]

        # 4. Build HoldingsOut list and calculate market valuation
        holdings_list: List[HoldingOut] = []
        total_invested = Decimal("0.0000")
        total_market_value = Decimal("0.0000")
        total_daily_pnl = Decimal("0.0000")

        for ticker, pos in holdings_map.items():
            if pos["shares"] <= Decimal("0"):
                continue

            # Get quote
            quote = await PortfolioEngine.get_or_update_market_cache(ticker, session)
            current_price = quote.current_price
            prev_close = quote.previous_close
            day_change = quote.day_change

            shares = pos["shares"]
            avg_cost = pos["avg_cost"]
            invested_val = round(shares * avg_cost, 4)
            current_val = round(shares * current_price, 4)
            unrealized_pnl = current_val - invested_val
            unrealized_pnl_pct = round((unrealized_pnl / invested_val * 100), 2) if invested_val > 0 else Decimal("0.00")
            
            day_pnl = round(shares * day_change, 4)
            day_pnl_pct = round((day_change / prev_close * 100), 2) if prev_close > 0 else Decimal("0.00")

            total_invested += invested_val
            total_market_value += current_val
            total_daily_pnl += day_pnl

            holdings_list.append(HoldingOut(
                ticker=ticker,
                name=quote.name,
                shares=round(shares, 4),
                cost_basis=round(avg_cost, 4),
                current_price=round(current_price, 4),
                current_value=round(current_val, 4),
                unrealized_pnl=round(unrealized_pnl, 4),
                unrealized_pnl_percent=unrealized_pnl_pct,
                daily_pnl=round(day_pnl, 4),
                daily_pnl_percent=day_pnl_pct,
                sector=quote.sector or "Other",
                currency=quote.currency or sub_p.currency
            ))

        # 5. Calculate Sub-portfolio level totals
        cash_balance = sub_p.cash_balance
        total_portfolio_value = round(total_market_value + cash_balance, 4)
        total_unrealized_pnl = round(total_market_value - total_invested, 4)
        total_unrealized_pnl_pct = round((total_unrealized_pnl / total_invested * 100), 2) if total_invested > 0 else Decimal("0.00")
        
        prev_market_val = total_market_value - total_daily_pnl
        total_daily_pnl_pct = round((total_daily_pnl / prev_market_val * 100), 2) if prev_market_val > 0 else Decimal("0.00")

        return SubPortfolioDetailOut(
            id=sub_p.id,
            portfolio_id=sub_p.portfolio_id,
            name=sub_p.name,
            country=sub_p.country,
            currency=sub_p.currency,
            benchmark_ticker=sub_p.benchmark_ticker,
            cash_balance=round(cash_balance, 4),
            total_invested_value=round(total_invested, 4),
            total_market_value=round(total_market_value, 4),
            total_portfolio_value=total_portfolio_value,
            total_unrealized_pnl=total_unrealized_pnl,
            total_unrealized_pnl_percent=total_unrealized_pnl_pct,
            total_daily_pnl=round(total_daily_pnl, 4),
            total_daily_pnl_percent=total_daily_pnl_pct,
            created_at=sub_p.created_at,
            updated_at=sub_p.updated_at,
            holdings=holdings_list
        )

    @staticmethod
    async def execute_transaction(
        sub_portfolio_id: int,
        tx_type: str,
        ticker: Optional[str],
        shares: Optional[Decimal],
        price_per_share: Optional[Decimal],
        fees: Decimal,
        total_amount: Optional[Decimal],
        executed_at: Optional[datetime],
        notes: Optional[str],
        session: AsyncSession
    ) -> Transaction:
        """Execute and validate a transaction against the regional cash wallet."""
        stmt = select(SubPortfolio).where(SubPortfolio.id == sub_portfolio_id)
        res = await session.execute(stmt)
        sub_p = res.scalar_one_or_none()
        if not sub_p:
            raise HTTPException(status_code=404, detail="Sub-portfolio not found")

        tx_type = tx_type.upper()
        fees = fees or Decimal("0.0000")
        calc_total = total_amount

        # Validate by transaction type
        if tx_type == "BUY":
            if not ticker or not shares or not price_per_share or shares <= 0 or price_per_share <= 0:
                raise HTTPException(status_code=400, detail="BUY requires valid ticker, shares > 0, and price > 0")
            calc_total = round((shares * price_per_share) + fees, 4)
            
            # Cash Wallet Balance validation
            if sub_p.cash_balance < calc_total:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient cash wallet balance. Available: {sub_p.currency} {sub_p.cash_balance:,.2f}, Required: {sub_p.currency} {calc_total:,.2f}. Please deposit cash first."
                )
            # Deduct from cash wallet
            sub_p.cash_balance -= calc_total

        elif tx_type == "SELL":
            if not ticker or not shares or not price_per_share or shares <= 0 or price_per_share <= 0:
                raise HTTPException(status_code=400, detail="SELL requires valid ticker, shares > 0, and price > 0")
            calc_total = round((shares * price_per_share) - fees, 4)
            
            # Check currently owned shares
            detail = await PortfolioEngine.calculate_sub_portfolio_holdings(sub_portfolio_id, session)
            owned_shares = Decimal("0")
            for h in detail.holdings:
                if h.ticker.upper() == ticker.upper():
                    owned_shares = h.shares
                    break
            if shares > owned_shares:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot sell {shares} shares of {ticker}. Currently owned: {owned_shares} shares."
                )
            # Add proceeds to cash wallet
            sub_p.cash_balance += calc_total

        elif tx_type == "CASH_DEPOSIT":
            if not calc_total or calc_total <= 0:
                raise HTTPException(status_code=400, detail="CASH_DEPOSIT requires positive amount")
            sub_p.cash_balance += calc_total

        elif tx_type == "CASH_WITHDRAWAL":
            if not calc_total or calc_total <= 0:
                raise HTTPException(status_code=400, detail="CASH_WITHDRAWAL requires positive amount")
            if sub_p.cash_balance < calc_total:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient cash wallet balance. Available: {sub_p.currency} {sub_p.cash_balance:,.2f}, Requested: {sub_p.currency} {calc_total:,.2f}."
                )
            sub_p.cash_balance -= calc_total

        elif tx_type == "DIVIDEND":
            if not calc_total or calc_total <= 0:
                raise HTTPException(status_code=400, detail="DIVIDEND requires positive amount")
            sub_p.cash_balance += calc_total

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported transaction type: {tx_type}")

        # Record transaction
        tx = Transaction(
            sub_portfolio_id=sub_portfolio_id,
            type=tx_type,
            ticker=ticker.strip().upper() if ticker else None,
            shares=shares,
            price_per_share=price_per_share,
            fees=fees,
            total_amount=calc_total,
            currency=sub_p.currency,
            executed_at=executed_at or datetime.utcnow(),
            notes=notes
        )
        session.add(tx)
        await session.commit()
        await session.refresh(tx)

        # Trigger background quote cache update if stock transaction
        if ticker:
            try:
                await PortfolioEngine.get_or_update_market_cache(ticker, session)
            except Exception as e:
                logger.warning(f"Could not auto-cache quote for {ticker}: {e}")

        return tx

    @staticmethod
    async def calculate_master_rollup(portfolio_id: int, base_currency: str, session: AsyncSession) -> MasterRollupOut:
        """Roll up all sub-portfolios into a unified master portfolio net worth in base_currency."""
        stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
        res = await session.execute(stmt)
        portfolio = res.scalar_one_or_none()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Master portfolio not found")

        base_curr = (base_currency or portfolio.base_currency).upper()

        stmt_subs = select(SubPortfolio).where(SubPortfolio.portfolio_id == portfolio_id)
        res_subs = await session.execute(stmt_subs)
        sub_portfolios = res_subs.scalars().all()

        converted_summaries: List[SubPortfolioSummaryConverted] = []
        master_net_worth = Decimal("0.0000")
        master_cash = Decimal("0.0000")
        master_market_val = Decimal("0.0000")
        master_invested = Decimal("0.0000")
        master_unrealized_pnl = Decimal("0.0000")
        master_daily_pnl = Decimal("0.0000")

        for sp in sub_portfolios:
            detail = await PortfolioEngine.calculate_sub_portfolio_holdings(sp.id, session)
            fx_rate = await FxService.get_exchange_rate(sp.currency, base_curr, session)

            # Convert to master currency
            conv_cash = round(detail.cash_balance * fx_rate, 4)
            conv_market = round(detail.total_market_value * fx_rate, 4)
            conv_total = round(detail.total_portfolio_value * fx_rate, 4)
            conv_invested = round(detail.total_invested_value * fx_rate, 4)
            conv_unrealized = round(detail.total_unrealized_pnl * fx_rate, 4)
            conv_daily = round(detail.total_daily_pnl * fx_rate, 4)

            master_cash += conv_cash
            master_market_val += conv_market
            master_net_worth += conv_total
            master_invested += conv_invested
            master_unrealized_pnl += conv_unrealized
            master_daily_pnl += conv_daily

            converted_summaries.append(SubPortfolioSummaryConverted(
                id=sp.id,
                name=sp.name,
                country=sp.country,
                local_currency=sp.currency,
                benchmark_ticker=sp.benchmark_ticker,
                local_cash_balance=detail.cash_balance,
                local_market_value=detail.total_market_value,
                local_total_value=detail.total_portfolio_value,
                local_daily_pnl=detail.total_daily_pnl,
                local_unrealized_pnl=detail.total_unrealized_pnl,
                base_fx_rate=fx_rate,
                converted_cash_balance=conv_cash,
                converted_market_value=conv_market,
                converted_total_value=conv_total,
                converted_daily_pnl=conv_daily,
                converted_unrealized_pnl=conv_unrealized
            ))

        unrealized_pct = round((master_unrealized_pnl / master_invested * 100), 2) if master_invested > 0 else Decimal("0.00")
        prev_net = master_net_worth - master_daily_pnl
        daily_pct = round((master_daily_pnl / prev_net * 100), 2) if prev_net > 0 else Decimal("0.00")

        return MasterRollupOut(
            portfolio_id=portfolio.id,
            portfolio_name=portfolio.name,
            base_currency=base_curr,
            total_net_worth=round(master_net_worth, 2),
            total_cash=round(master_cash, 2),
            total_market_value=round(master_market_val, 2),
            total_invested=round(master_invested, 2),
            total_unrealized_pnl=round(master_unrealized_pnl, 2),
            total_unrealized_pnl_percent=unrealized_pct,
            total_daily_pnl=round(master_daily_pnl, 2),
            total_daily_pnl_percent=daily_pct,
            sub_portfolios=converted_summaries
        )
