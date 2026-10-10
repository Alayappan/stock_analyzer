from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.models.portfolio import Portfolio, SubPortfolio
from app.models.transaction import Transaction
from app.models.market import DividendSchedule
from app.schemas.portfolio import (
    PortfolioCreate, PortfolioOut, SubPortfolioBase, SubPortfolioCreate, SubPortfolioUpdate, SubPortfolioOut,
    SubPortfolioDetailOut, MasterRollupOut, CashWalletUpdate, CashPoolEdit
)
from app.schemas.market import DividendScheduleOut
from app.services.portfolio_engine import PortfolioEngine

router = APIRouter(prefix="", tags=["Portfolios"])

@router.get("/portfolios", response_model=List[PortfolioOut])
async def list_portfolios(db: AsyncSession = Depends(get_db)):
    """List all master portfolios with their sub-portfolios."""
    stmt = select(Portfolio).order_by(Portfolio.id.asc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/portfolios", response_model=PortfolioOut, status_code=201)
async def create_portfolio(portfolio_in: PortfolioCreate, db: AsyncSession = Depends(get_db)):
    """Create a new master portfolio."""
    p = Portfolio(
        name=portfolio_in.name,
        description=portfolio_in.description,
        base_currency=portfolio_in.base_currency.upper()
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p

@router.get("/portfolios/{portfolio_id}", response_model=PortfolioOut)
async def get_portfolio(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    """Get single master portfolio details."""
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    res = await db.execute(stmt)
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return p

@router.get("/portfolios/{portfolio_id}/rollup", response_model=MasterRollupOut)
async def get_master_portfolio_rollup(
    portfolio_id: int,
    base_currency: Optional[str] = Query(None, description="Override display base currency (e.g. USD, INR, EUR, GBP, JPY)"),
    db: AsyncSession = Depends(get_db)
):
    """Calculate multi-currency rollup for master portfolio converted to base currency with live FX rates."""
    return await PortfolioEngine.calculate_master_rollup(portfolio_id, base_currency, db)

@router.post("/portfolios/{portfolio_id}/sub-portfolios", response_model=SubPortfolioOut, status_code=201)
async def create_sub_portfolio(
    portfolio_id: int,
    sub_in: SubPortfolioBase,
    db: AsyncSession = Depends(get_db)
):
    """Add a new regional sub-portfolio with dedicated currency and benchmark index."""
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Master portfolio not found")

    sp = SubPortfolio(
        portfolio_id=portfolio_id,
        name=sub_in.name,
        country=sub_in.country.upper(),
        currency=sub_in.currency.upper(),
        benchmark_ticker=sub_in.benchmark_ticker.upper(),
        cash_balance=sub_in.cash_balance
    )
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return sp

@router.get("/sub-portfolios/{sub_portfolio_id}", response_model=SubPortfolioDetailOut)
async def get_sub_portfolio_detail(sub_portfolio_id: int, db: AsyncSession = Depends(get_db)):
    """Get comprehensive sub-portfolio details with real-time calculated holdings, P&L, and cash wallet."""
    return await PortfolioEngine.calculate_sub_portfolio_holdings(sub_portfolio_id, db)

@router.post("/sub-portfolios/{sub_portfolio_id}/cash")
async def update_cash_wallet(
    sub_portfolio_id: int,
    cash_in: CashWalletUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Deposit or withdraw cash from the regional sub-portfolio cash wallet."""
    tx_type = cash_in.type.upper()
    if tx_type not in ["CASH_DEPOSIT", "CASH_WITHDRAWAL"]:
        raise HTTPException(status_code=400, detail="Type must be CASH_DEPOSIT or CASH_WITHDRAWAL")

    tx = await PortfolioEngine.execute_transaction(
        sub_portfolio_id=sub_portfolio_id,
        tx_type=tx_type,
        ticker=None,
        shares=None,
        price_per_share=None,
        fees=Decimal("0.0000"),
        total_amount=cash_in.amount,
        executed_at=datetime.utcnow(),
        notes=cash_in.notes or f"Manual {tx_type}",
        session=db
    )
    
    # Return updated sub-portfolio
    stmt = select(SubPortfolio).where(SubPortfolio.id == sub_portfolio_id)
    res = await db.execute(stmt)
    sub_p = res.scalar_one()
    return {
        "status": "success",
        "action": tx_type,
        "amount": cash_in.amount,
        "new_cash_balance": sub_p.cash_balance,
        "currency": sub_p.currency,
        "transaction_id": tx.id
    }

@router.get("/sub-portfolios/{sub_portfolio_id}/dividends", response_model=List[DividendScheduleOut])
async def get_sub_portfolio_dividends(sub_portfolio_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch projected dividends and corporate actions for held tickers in this sub-portfolio."""
    stmt = select(DividendSchedule).where(DividendSchedule.sub_portfolio_id == sub_portfolio_id).order_by(DividendSchedule.payment_date.asc().nulls_last())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.put("/sub-portfolios/{sub_portfolio_id}", response_model=SubPortfolioOut)
async def update_sub_portfolio(
    sub_portfolio_id: int,
    update_in: SubPortfolioUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Edit sub-portfolio metadata (name, country, currency, benchmark index, and cash balance)."""
    stmt = select(SubPortfolio).where(SubPortfolio.id == sub_portfolio_id)
    res = await db.execute(stmt)
    sub_p = res.scalar_one_or_none()
    if not sub_p:
        raise HTTPException(status_code=404, detail="Sub-portfolio not found")

    if update_in.name is not None and update_in.name.strip():
        sub_p.name = update_in.name.strip()
    if update_in.country is not None and update_in.country.strip():
        sub_p.country = update_in.country.strip().upper()
    if update_in.currency is not None and update_in.currency.strip():
        sub_p.currency = update_in.currency.strip().upper()
    if update_in.benchmark_ticker is not None and update_in.benchmark_ticker.strip():
        sub_p.benchmark_ticker = update_in.benchmark_ticker.strip().upper()
    if update_in.cash_balance is not None:
        diff = update_in.cash_balance - sub_p.cash_balance
        if diff != Decimal("0.0000"):
            adj_type = "CASH_DEPOSIT" if diff > 0 else "CASH_WITHDRAWAL"
            adj_tx = Transaction(
                sub_portfolio_id=sub_portfolio_id,
                type=adj_type,
                total_amount=abs(diff),
                currency=sub_p.currency,
                executed_at=datetime.utcnow(),
                notes="Manual cash pool balance adjustment"
            )
            db.add(adj_tx)
            sub_p.cash_balance = update_in.cash_balance

    await db.commit()
    await db.refresh(sub_p)
    return sub_p

@router.delete("/sub-portfolios/{sub_portfolio_id}")
async def delete_sub_portfolio(sub_portfolio_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a sub-portfolio along with its transaction ledger, cash wallet, and dividends."""
    stmt = select(SubPortfolio).where(SubPortfolio.id == sub_portfolio_id)
    res = await db.execute(stmt)
    sub_p = res.scalar_one_or_none()
    if not sub_p:
        raise HTTPException(status_code=404, detail="Sub-portfolio not found")

    sub_name = sub_p.name
    await db.delete(sub_p)
    await db.commit()
    return {
        "status": "success",
        "message": f"Sub-portfolio '{sub_name}' (ID: {sub_portfolio_id}) successfully deleted.",
        "deleted_id": sub_portfolio_id
    }

@router.put("/sub-portfolios/{sub_portfolio_id}/cash-pool")
async def edit_cash_pool_balance(
    sub_portfolio_id: int,
    pool_in: CashPoolEdit,
    db: AsyncSession = Depends(get_db)
):
    """Directly edit/set the sub-portfolio cash pool balance and automatically balance the transaction ledger."""
    stmt = select(SubPortfolio).where(SubPortfolio.id == sub_portfolio_id)
    res = await db.execute(stmt)
    sub_p = res.scalar_one_or_none()
    if not sub_p:
        raise HTTPException(status_code=404, detail="Sub-portfolio not found")

    old_balance = sub_p.cash_balance
    new_balance = pool_in.new_cash_balance
    diff = new_balance - old_balance

    tx_id = None
    if diff != Decimal("0.0000"):
        tx_type = "CASH_DEPOSIT" if diff > 0 else "CASH_WITHDRAWAL"
        tx = Transaction(
            sub_portfolio_id=sub_portfolio_id,
            type=tx_type,
            ticker=None,
            shares=None,
            price_per_share=None,
            fees=Decimal("0.0000"),
            total_amount=abs(diff),
            currency=sub_p.currency,
            executed_at=datetime.utcnow(),
            notes=pool_in.notes or f"Manual cash pool adjustment from {old_balance:,.2f} to {new_balance:,.2f}"
        )
        db.add(tx)
        sub_p.cash_balance = new_balance
        await db.commit()
        await db.refresh(sub_p)
        tx_id = tx.id

    return {
        "status": "success",
        "sub_portfolio_id": sub_portfolio_id,
        "previous_cash_balance": old_balance,
        "new_cash_balance": sub_p.cash_balance,
        "currency": sub_p.currency,
        "difference": diff,
        "audit_transaction_id": tx_id
    }

@router.post("/sub-portfolios/{sub_portfolio_id}/deduplicate")
async def deduplicate_sub_portfolio(
    sub_portfolio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Scan and remove duplicate transactions from a sub-portfolio ledger.
    Keeps the earliest occurrence for each (ticker, type, shares, price, date) tuple.
    """
    stmt_sub = select(SubPortfolio).where(SubPortfolio.id == sub_portfolio_id)
    res_sub = await db.execute(stmt_sub)
    sub_p = res_sub.scalar_one_or_none()
    if not sub_p:
        raise HTTPException(status_code=404, detail="Sub-portfolio not found")

    stmt_tx = select(Transaction).where(
        Transaction.sub_portfolio_id == sub_portfolio_id,
        Transaction.type.in_(["BUY", "SELL"])
    ).order_by(Transaction.id.asc())
    res_tx = await db.execute(stmt_tx)
    all_stock_txs = res_tx.scalars().all()

    seen_sigs = set()
    to_delete_ids = []
    for tx in all_stock_txs:
        d_str = tx.executed_at.strftime("%Y-%m-%d") if tx.executed_at else ""
        sig = (
            tx.type,
            (tx.ticker or "").strip().upper(),
            round(Decimal(str(tx.shares or 0)), 4),
            round(Decimal(str(tx.price_per_share or 0)), 4),
            d_str
        )
        if sig in seen_sigs:
            to_delete_ids.append(tx.id)
        else:
            seen_sigs.add(sig)

    if to_delete_ids:
        await db.execute(delete(Transaction).where(Transaction.id.in_(to_delete_ids)))
        await db.commit()

    return {
        "status": "success",
        "sub_portfolio_id": sub_portfolio_id,
        "duplicates_removed": len(to_delete_ids),
        "unique_stock_transactions": len(seen_sigs)
    }

