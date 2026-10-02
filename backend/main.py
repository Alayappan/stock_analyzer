from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import io
import csv

from .database import (
    init_db, bulk_insert_transactions, get_aggregated_portfolio,
    clear_portfolio, get_transaction_count, add_single_holding,
    delete_holding_by_symbol
)
from .csv_parser import parse_portfolio_csv_content
from .stock_service import analyze_full_portfolio, get_stock_deep_dive

app = FastAPI(title="PortfolioPulse - Yahoo Finance Portfolio Analyzer", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

class ManualHoldingRequest(BaseModel):
    symbol: str
    shares: float
    buy_price: float
    buy_date: Optional[str] = None
    notes: Optional[str] = None

# --- API Endpoints ---

@app.get("/api/portfolio/analysis")
def get_portfolio_analysis():
    """
    Returns complete Yahoo Finance analysis of all portfolio holdings,
    including aggregated metrics, sector allocation, weighted beta/PE, and dividend yield.
    """
    try:
        raw_holdings = get_aggregated_portfolio()
        analysis = analyze_full_portfolio(raw_holdings)
        analysis["rawTransactionCount"] = get_transaction_count()
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/upload")
async def upload_portfolio_csv(
    file: UploadFile = File(...),
    mode: str = Form("replace") # "replace" or "append"
):
    """
    Accepts bulk CSV file upload (Yahoo Finance export or standard format),
    parses transactions, and saves to database.
    """
    try:
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8-sig", errors="replace")

        transactions, stats = parse_portfolio_csv_content(content_str)
        if not transactions:
            raise HTTPException(status_code=400, detail="No valid transactions found in uploaded CSV file.")

        replace_all = (mode == "replace")
        inserted = bulk_insert_transactions(transactions, replace_all=replace_all)

        raw_holdings = get_aggregated_portfolio()

        return {
            "success": True,
            "filename": file.filename,
            "mode": mode,
            "parsedTransactions": len(transactions),
            "insertedRecords": inserted,
            "activeHoldingsCount": len(raw_holdings),
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/portfolio/clear")
def clear_all_portfolio():
    deleted = clear_portfolio()
    return {"success": True, "deletedCount": deleted}

@app.delete("/api/portfolio/holding/{symbol}")
def delete_holding(symbol: str):
    success = delete_holding_by_symbol(symbol)
    return {"success": success, "symbol": symbol}

@app.post("/api/portfolio/add-manual")
def add_manual(req: ManualHoldingRequest):
    if req.shares <= 0 or req.buy_price <= 0:
        raise HTTPException(status_code=400, detail="Shares and purchase price must be greater than zero")
    new_id = add_single_holding(
        symbol=req.symbol,
        shares=req.shares,
        buy_price=req.buy_price,
        buy_date=req.buy_date,
        notes=req.notes
    )
    return {"success": True, "id": new_id}

@app.get("/api/holding/deep-dive/{symbol}")
def deep_dive(symbol: str):
    """
    Returns deep-dive valuation multiples, margins, solvency, and news for a specific holding.
    """
    try:
        data = get_stock_deep_dive(symbol)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/export")
def export_portfolio_analysis():
    """
    Exports the current portfolio analysis with all Yahoo Finance fields into CSV.
    """
    raw_holdings = get_aggregated_portfolio()
    analysis = analyze_full_portfolio(raw_holdings)
    holdings = analysis.get("holdings", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Symbol", "Company Name", "Sector", "Industry", "Shares",
        "Avg Buy Price", "Current Price", "Market Value", "Cost Basis",
        "Unrealized P&L ($)", "Return (%)", "Day Change ($)", "Day Change (%)",
        "Portfolio Weight (%)", "P/E (TTM)", "Forward P/E", "P/B Ratio",
        "EPS", "Dividend Yield (%)", "Annual Dividend ($)", "Beta",
        "Analyst Target", "Analyst Rating"
    ])

    for h in holdings:
        writer.writerow([
            h.get("symbol"),
            h.get("shortName"),
            h.get("sector"),
            h.get("industry"),
            h.get("shares"),
            h.get("avgBuyPrice"),
            h.get("currentPrice"),
            h.get("marketValue"),
            h.get("costBasis"),
            h.get("gainLoss"),
            h.get("gainLossPercent"),
            h.get("positionDayChange"),
            h.get("positionDayChangePercent"),
            h.get("portfolioWeightPercent"),
            h.get("trailingPE"),
            h.get("forwardPE"),
            h.get("priceToBook"),
            h.get("trailingEps"),
            h.get("dividendYield"),
            h.get("positionAnnualDividend"),
            h.get("beta"),
            h.get("targetMeanPrice"),
            h.get("recommendationKey")
        ])

    output.seek(0)
    return PlainTextResponse(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio_yahoo_analysis.csv"}
    )

# Static files setup
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
