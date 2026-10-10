from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.services.import_service import ImportService

router = APIRouter(prefix="/portfolios", tags=["Import"])

@router.post("/import")
async def import_portfolio_file(
    file: UploadFile = File(..., description="Yahoo Finance portfolio export CSV or Excel file"),
    portfolio_id: int = Form(1, description="Target master portfolio ID"),
    target_sub_portfolio_id: Optional[int] = Form(None, description="Optional specific sub-portfolio ID, or auto-detect by region if null"),
    auto_fund_cash: bool = Form(True, description="Automatically deposit initial cash if wallet balance is below buy cost"),
    skip_duplicates: bool = Form(True, description="Skip duplicate transactions already present in the ledger"),
    replace_existing: bool = Form(False, description="Wipe existing transactions in target sub-portfolio before importing"),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest Yahoo Finance portfolio export file (CSV/XLSX).
    Automatically maps tickers to sub-portfolios via regional suffixes (.NS -> India, .T -> Japan, blank -> US).
    Initializes transaction ledger and regional cash wallets with idempotent deduplication.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    result = await ImportService.import_portfolio_data(
        filename=file.filename,
        content=content,
        portfolio_id=portfolio_id,
        target_sub_portfolio_id=target_sub_portfolio_id,
        auto_fund_cash=auto_fund_cash,
        session=db,
        skip_duplicates=skip_duplicates,
        replace_existing=replace_existing
    )
    return result
