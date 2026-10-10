from datetime import datetime
from decimal import Decimal
import logging
from typing import Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.market import FxRate
from app.services.yahoo_client import yahoo_client

logger = logging.getLogger(__name__)

# Fallback base rates against USD
FALLBACK_USD_RATES: Dict[str, Decimal] = {
    "USD": Decimal("1.000000"),
    "INR": Decimal("96.730000"),
    "JPY": Decimal("158.250000"),
    "EUR": Decimal("0.892400"), # 1 EUR = ~1.1206 USD
    "GBP": Decimal("0.755700"), # 1 GBP = ~1.3233 USD
    "CAD": Decimal("1.425400"),
    "AUD": Decimal("1.545000"),
    "HKD": Decimal("7.775000"),
}

class FxService:
    @staticmethod
    async def fetch_and_update_rates(session: AsyncSession) -> Dict[str, Decimal]:
        """Fetch live FX rates via Yahoo Finance REST client and persist cross-rates to database."""
        pairs_to_fetch = {
            "INR": "USDINR=X",
            "JPY": "JPY=X",
            "EUR": "EURUSD=X",
            "GBP": "GBPUSD=X",
            "CAD": "CAD=X",
            "AUD": "AUD=X",
            "HKD": "HKD=X"
        }
        
        rates_against_usd = {"USD": Decimal("1.000000")}

        try:
            live_quotes = yahoo_client.get_quotes(list(pairs_to_fetch.values()))
        except Exception as e:
            logger.warning(f"Error fetching live FX rates batch: {e}")
            live_quotes = {}
        
        for curr, pair_sym in pairs_to_fetch.items():
            rate_val: Optional[Decimal] = None
            if pair_sym in live_quotes:
                p = float(live_quotes[pair_sym]["current_price"])
                if p > 0:
                    if pair_sym in ["EURUSD=X", "GBPUSD=X"]:
                        rate_val = Decimal(str(round(1.0 / p, 6)))
                    else:
                        rate_val = Decimal(str(round(p, 6)))

            if not rate_val:
                rate_val = FALLBACK_USD_RATES.get(curr, Decimal("1.000000"))
                
            rates_against_usd[curr] = rate_val

        # Persist direct and inverse cross-currency rates to db
        currencies = list(rates_against_usd.keys())
        for c1 in currencies:
            for c2 in currencies:
                if c1 == c2:
                    calc_rate = Decimal("1.000000")
                else:
                    # c1 -> USD -> c2
                    usd_per_c1 = Decimal("1.0") / rates_against_usd[c1]
                    calc_rate = round(usd_per_c1 * rates_against_usd[c2], 6)
                
                # Upsert into database
                stmt = select(FxRate).where(FxRate.from_currency == c1, FxRate.to_currency == c2)
                res = await session.execute(stmt)
                fx_obj = res.scalar_one_or_none()
                if fx_obj:
                    fx_obj.rate = calc_rate
                    fx_obj.last_updated = datetime.utcnow()
                else:
                    fx_obj = FxRate(from_currency=c1, to_currency=c2, rate=calc_rate, last_updated=datetime.utcnow())
                    session.add(fx_obj)
                    
        await session.commit()
        return rates_against_usd

    @staticmethod
    async def get_exchange_rate(from_curr: str, to_curr: str, session: Optional[AsyncSession] = None) -> Decimal:
        """Get exchange rate from from_curr to to_curr with database lookup or fallback."""
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()
        
        if from_curr == to_curr:
            return Decimal("1.000000")
            
        if session:
            stmt = select(FxRate).where(FxRate.from_currency == from_curr, FxRate.to_currency == to_curr)
            res = await session.execute(stmt)
            fx_obj = res.scalar_one_or_none()
            if fx_obj and fx_obj.rate:
                return fx_obj.rate
                
        # Calculate from fallback USD rates table
        r1 = FALLBACK_USD_RATES.get(from_curr, Decimal("1.0"))
        r2 = FALLBACK_USD_RATES.get(to_curr, Decimal("1.0"))
        usd_per_from = Decimal("1.0") / r1
        return round(usd_per_from * r2, 6)
