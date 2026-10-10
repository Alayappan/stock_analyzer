from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, time, date
import pytz
import logging
from sqlalchemy import select, distinct
from typing import Dict, Any, List

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.transaction import Transaction
from app.models.portfolio import SubPortfolio
from app.models.market import DividendSchedule
from app.services.market_data import MarketDataService
from app.services.fx_service import FxService
from app.services.portfolio_engine import PortfolioEngine

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def is_market_open(exchange_key: str) -> Dict[str, Any]:
    """Check whether a specific regional stock exchange is currently trading."""
    conf = settings.MARKET_SCHEDULES.get(exchange_key)
    if not conf:
        return {"is_open": False, "local_time": "", "open_time": "", "close_time": ""}

    tz = pytz.timezone(conf["timezone"])
    local_now = datetime.now(tz)
    weekday = local_now.weekday() # 0 = Monday, 6 = Sunday

    # Closed on weekends
    if weekday >= 5:
        return {
            "is_open": False,
            "local_time": local_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "open_time": conf["open"],
            "close_time": conf["close"],
            "status_reason": "Weekend Closed"
        }

    open_parts = [int(p) for p in conf["open"].split(":")]
    close_parts = [int(p) for p in conf["close"].split(":")]
    open_time = time(open_parts[0], open_parts[1])
    close_time = time(close_parts[0], close_parts[1])
    current_time = local_now.time()

    is_open = open_time <= current_time <= close_time
    return {
        "is_open": is_open,
        "local_time": local_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "open_time": conf["open"],
        "close_time": conf["close"],
        "status_reason": "Market Open" if is_open else "Closed Outside Trading Hours"
    }

def get_all_market_statuses() -> List[Dict[str, Any]]:
    """Return status across all major monitored regional stock exchanges."""
    results = []
    for ex_key, conf in settings.MARKET_SCHEDULES.items():
        st = is_market_open(ex_key)
        results.append({
            "exchange_id": ex_key,
            "name": conf["name"],
            "country": conf["country"],
            "currency": conf["currency"],
            "timezone": conf["timezone"],
            "is_open": st["is_open"],
            "local_time": st["local_time"],
            "open_time": conf["open"],
            "close_time": conf["close"],
        })
    return results

async def sync_all_markets(force: bool = False) -> Dict[str, Any]:
    """Fetch live stock quotes, benchmark indices, dividend declarations, and FX rates."""
    logger.info("Executing market synchronization job...")
    updated_tickers = []
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Update FX rates first
            await FxService.fetch_and_update_rates(session)

            # 2. Gather all held tickers from transactions
            stmt_tx = select(distinct(Transaction.ticker)).where(Transaction.ticker.isnot(None))
            res_tx = await session.execute(stmt_tx)
            tickers = [t[0].strip().upper() for t in res_tx.fetchall() if t[0]]

            # 3. Add default benchmark indices
            for bm in settings.DEFAULT_BENCHMARKS.values():
                b_ticker = bm["ticker"].strip().upper()
                if b_ticker not in tickers:
                    tickers.append(b_ticker)

            # 4. Fetch quotes & update market cache
            for ticker in tickers:
                try:
                    await PortfolioEngine.get_or_update_market_cache(ticker, session, force_refresh=force)
                    updated_tickers.append(ticker)
                except Exception as e:
                    logger.warning(f"Error syncing ticker {ticker}: {e}")

            # 5. Check and record dividend declarations for held stocks
            stmt_subs = select(SubPortfolio)
            res_subs = await session.execute(stmt_subs)
            sub_portfolios = res_subs.scalars().all()

            for sp in sub_portfolios:
                detail = await PortfolioEngine.calculate_sub_portfolio_holdings(sp.id, session)
                for h in detail.holdings:
                    if h.shares > 0:
                        div_declarations = MarketDataService.get_dividend_declarations(h.ticker)
                        for d in div_declarations:
                            def to_date_obj(val):
                                if isinstance(val, datetime):
                                    return val.date()
                                if isinstance(val, date):
                                    return val
                                if isinstance(val, str) and val.strip():
                                    try:
                                        return datetime.strptime(val.strip(), "%Y-%m-%d").date()
                                    except Exception:
                                        return None
                                return None

                            payout = round(h.shares * d["dividend_per_share"], 4)
                            div_obj = DividendSchedule(
                                sub_portfolio_id=sp.id,
                                ticker=h.ticker,
                                ex_date=to_date_obj(d.get("ex_date")),
                                record_date=to_date_obj(d.get("record_date")),
                                payment_date=to_date_obj(d.get("payment_date")),
                                dividend_per_share=d["dividend_per_share"],
                                projected_payout=payout,
                                currency=d.get("currency", sp.currency),
                                status=d.get("status", "ANNOUNCED")
                            )
                            session.add(div_obj)
            await session.commit()
            
            logger.info(f"Market synchronization completed. Synced {len(updated_tickers)} tickers.")
            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "synced_tickers": updated_tickers,
                "count": len(updated_tickers)
            }
        except Exception as e:
            logger.error(f"Error during market sync: {e}")
            await session.rollback()
            return {"status": "error", "message": str(e)}

def start_scheduler():
    """Start APScheduler background job running every 5 minutes."""
    if not scheduler.running:
        scheduler.add_job(
            sync_all_markets,
            trigger=IntervalTrigger(minutes=settings.MARKET_POLL_INTERVAL_MINUTES),
            id="market_sync_worker",
            name="Periodic Market and FX Sync",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"APScheduler started. Polling markets every {settings.MARKET_POLL_INTERVAL_MINUTES} minutes.")

def stop_scheduler():
    """Gracefully shutdown scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
