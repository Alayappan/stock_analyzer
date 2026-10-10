from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional

from app.core.database import get_db
from app.models.transaction import Transaction
from app.models.portfolio import SubPortfolio
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.services.portfolio_engine import PortfolioEngine

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("", response_model=List[TransactionOut])
async def list_transactions(
    sub_portfolio_id: Optional[int] = Query(None, description="Filter by Sub-Portfolio ID"),
    ticker: Optional[str] = Query(None, description="Filter by Ticker Symbol"),
    type: Optional[str] = Query(None, description="Filter by transaction type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve transaction history with optional filters."""
    stmt = select(Transaction).order_by(desc(Transaction.executed_at), desc(Transaction.id))
    
    if sub_portfolio_id:
        stmt = stmt.where(Transaction.sub_portfolio_id == sub_portfolio_id)
    if ticker:
        stmt = stmt.where(Transaction.ticker == ticker.strip().upper())
    if type:
        stmt = stmt.where(Transaction.type == type.strip().upper())
        
    stmt = stmt.limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("", response_model=TransactionOut, status_code=201)
async def create_transaction(
    tx_in: TransactionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Record a transaction (BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAWAL, DIVIDEND) with cash wallet balance validation."""
    tx = await PortfolioEngine.execute_transaction(
        sub_portfolio_id=tx_in.sub_portfolio_id,
        tx_type=tx_in.type.value,
        ticker=tx_in.ticker,
        shares=tx_in.shares,
        price_per_share=tx_in.price_per_share,
        fees=tx_in.fees,
        total_amount=tx_in.total_amount,
        executed_at=tx_in.executed_at,
        notes=tx_in.notes,
        session=db
    )
    return tx

@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a transaction from the ledger."""
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    res = await db.execute(stmt)
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await db.delete(tx)
    await db.commit()
    return {"status": "success", "message": f"Transaction {transaction_id} deleted"}
