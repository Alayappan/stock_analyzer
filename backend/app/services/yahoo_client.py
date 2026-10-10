import requests
import re
import time
import logging
import urllib.parse
from typing import Dict, Any, List, Optional
from decimal import Decimal
import threading

logger = logging.getLogger(__name__)

# Known Indian market demergers / corporate renamings
SYMBOL_ALIASES: Dict[str, str] = {
    "TATAMOTORS.NS": "TMCV.NS",
    "TATAMOTORS.BO": "TMCV.BO",
}

class YahooFinanceClient:
    """
    Robust direct client for Yahoo Finance REST APIs.
    Maintains browser session cookies and dynamic query crumb to avoid 429 and rate-limiting.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(YahooFinanceClient, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.crumb: Optional[str] = None
        self._crumb_time: float = 0.0
        self._profile_cache: Dict[str, Dict[str, Any]] = {}
        self._init_lock = threading.Lock()
        self._initialized = True

    def _ensure_crumb(self, force: bool = False):
        """Acquire or renew session cookies and crumb."""
        now = time.time()
        # Refresh crumb every 60 minutes or on force
        if not force and self.crumb and (now - self._crumb_time < 3600):
            return

        with self._init_lock:
            if not force and self.crumb and (now - self._crumb_time < 3600):
                return

            # Strategy 1: Visit finance.yahoo.com/quote/AAPL to get session cookies + embedded crumb
            try:
                r = self.session.get("https://finance.yahoo.com/quote/AAPL", timeout=8)
                if r.status_code == 200:
                    m = re.search(r'"crumb":"([^"]+)"', r.text)
                    if m:
                        self.crumb = m.group(1).encode("utf-8").decode("unicode_escape")
                        self._crumb_time = time.time()
                        logger.info("Successfully acquired Yahoo Finance crumb from HTML session")
                        return
            except Exception as e:
                logger.debug(f"HTML crumb acquisition attempt: {e}")

            # Strategy 2: Direct getcrumb endpoint with fc.yahoo.com cookie
            try:
                self.session.get("https://fc.yahoo.com", timeout=6)
                res = self.session.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=6)
                if res.status_code == 200 and res.text and "Too Many Requests" not in res.text:
                    self.crumb = res.text.strip()
                    self._crumb_time = time.time()
                    logger.info("Acquired Yahoo Finance crumb from test/getcrumb endpoint")
                    return
            except Exception as e:
                logger.debug(f"Direct getcrumb endpoint attempt: {e}")

    def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch real-time quotes in batch for a list of tickers.
        Properly URL-encodes special characters (e.g. ARE&M.NS -> ARE%26M.NS)
        and handles corporate demergers/aliases (e.g. TATAMOTORS.NS -> TMCV.NS).
        """
        if not symbols:
            return {}

        clean_symbols = [s.strip().upper() for s in symbols if s and s.strip()]
        if not clean_symbols:
            return {}

        # Build symbol map for aliases
        symbol_map: Dict[str, List[str]] = {}
        query_symbols: List[str] = []
        for s in clean_symbols:
            actual = SYMBOL_ALIASES.get(s, s)
            if actual not in symbol_map:
                symbol_map[actual] = []
                query_symbols.append(actual)
            symbol_map[actual].append(s)

        self._ensure_crumb()
        sym_str = ",".join(urllib.parse.quote(s) for s in query_symbols)
        url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={sym_str}"
        if self.crumb:
            url += f"&crumb={self.crumb}"

        results: Dict[str, Dict[str, Any]] = {}
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code in [401, 403, 429]:
                # Invalidate crumb and retry once
                self._ensure_crumb(force=True)
                url = f"https://query2.finance.yahoo.com/v7/finance/quote?symbols={sym_str}"
                if self.crumb:
                    url += f"&crumb={self.crumb}"
                r = self.session.get(url, timeout=10)

            if r.status_code == 200:
                data = r.json()
                items = data.get("quoteResponse", {}).get("result", [])
                for item in items:
                    actual_sym = item.get("symbol", "").upper()
                    if not actual_sym:
                        continue

                    price = item.get("regularMarketPrice")
                    prev_close = item.get("regularMarketPreviousClose")
                    if price is None:
                        continue

                    diff = item.get("regularMarketChange")
                    if diff is None and prev_close is not None:
                        diff = price - prev_close
                    elif diff is None:
                        diff = 0.0

                    pct = item.get("regularMarketChangePercent")
                    if pct is None and prev_close:
                        pct = (diff / prev_close) * 100
                    elif pct is None:
                        pct = 0.0

                    name = item.get("shortName") or item.get("longName") or actual_sym
                    curr = item.get("currency") or ("INR" if actual_sym.endswith(".NS") else "JPY" if actual_sym.endswith(".T") else "USD")

                    quote_dict = {
                        "ticker": actual_sym,
                        "name": name,
                        "currency": curr,
                        "current_price": Decimal(str(round(price, 4))),
                        "previous_close": Decimal(str(round(prev_close if prev_close else price, 4))),
                        "day_change": Decimal(str(round(diff, 4))),
                        "day_change_percent": Decimal(str(round(pct, 4))),
                        "pe_ratio": Decimal(str(round(item.get("trailingPE") or item.get("forwardPE"), 2))) if (item.get("trailingPE") or item.get("forwardPE")) else None,
                        "market_cap": Decimal(str(round(item.get("marketCap"), 2))) if item.get("marketCap") else None,
                        "dividend_yield": Decimal(str(round(item.get("trailingAnnualDividendYield"), 4))) if item.get("trailingAnnualDividendYield") is not None else None,
                        "fifty_two_week_high": Decimal(str(round(item.get("fiftyTwoWeekHigh"), 4))) if item.get("fiftyTwoWeekHigh") else None,
                        "fifty_two_week_low": Decimal(str(round(item.get("fiftyTwoWeekLow"), 4))) if item.get("fiftyTwoWeekLow") else None,
                    }

                    results[actual_sym] = quote_dict
                    # Also populate original requested symbols (e.g. TATAMOTORS.NS)
                    for orig in symbol_map.get(actual_sym, []):
                        if orig != actual_sym:
                            results[orig] = {**quote_dict, "ticker": orig}
        except Exception as e:
            logger.warning(f"Error fetching batch quotes from Yahoo Finance: {e}")

        return results

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch a single ticker quote."""
        res = self.get_quotes([symbol])
        return res.get(symbol.strip().upper())

    def get_asset_profile(self, symbol: str) -> Dict[str, Any]:
        """Fetch sector, industry, and corporate profile."""
        sym = symbol.strip().upper()
        sym = SYMBOL_ALIASES.get(sym, sym)
        if sym in self._profile_cache:
            return self._profile_cache[sym]

        if sym.startswith("^"):
            profile = {"sector": "Index", "industry": "Benchmark"}
            self._profile_cache[sym] = profile
            return profile

        self._ensure_crumb()
        enc_sym = urllib.parse.quote(sym)
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{enc_sym}?modules=assetProfile"
        if self.crumb:
            url += f"&crumb={self.crumb}"

        try:
            r = self.session.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                res = data.get("quoteSummary", {}).get("result", [])
                if res and "assetProfile" in res[0]:
                    ap = res[0]["assetProfile"]
                    profile = {
                        "sector": ap.get("sector") or "Equities",
                        "industry": ap.get("industry") or "General",
                        "website": ap.get("website", ""),
                        "longBusinessSummary": ap.get("longBusinessSummary", "")
                    }
                    self._profile_cache[sym] = profile
                    return profile
        except Exception as e:
            logger.debug(f"Failed to fetch assetProfile for {sym}: {e}")

        fallback = {
            "sector": "Technology" if any(x in sym.lower() for x in ["aapl", "msft", "nvda", "infy", "tcs"]) else "Equities",
            "industry": "General"
        }
        self._profile_cache[sym] = fallback
        return fallback

    def get_chart_history(self, symbol: str, range_period: str = "6mo", interval: str = "1d") -> List[Dict[str, Any]]:
        """Fetch historical date + close points for performance graphs."""
        sym = symbol.strip().upper()
        sym = SYMBOL_ALIASES.get(sym, sym)
        self._ensure_crumb()
        enc_sym = urllib.parse.quote(sym)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{enc_sym}?interval={interval}&range={range_period}"
        if self.crumb:
            url += f"&crumb={self.crumb}"

        history_points: List[Dict[str, Any]] = []
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                res = data.get("chart", {}).get("result", [])
                if res:
                    timestamps = res[0].get("timestamp", [])
                    quote_data = res[0].get("indicators", {}).get("quote", [{}])[0]
                    closes = quote_data.get("close", [])
                    
                    for ts, val in zip(timestamps, closes):
                        if val is not None and not (isinstance(val, float) and (val != val)): # check NaN
                            d_str = time.strftime("%Y-%m-%d", time.gmtime(ts))
                            history_points.append({"date": d_str, "close": round(float(val), 2)})
        except Exception as e:
            logger.warning(f"Error fetching chart history for {sym}: {e}")

        return history_points

    def get_calendar_events(self, symbol: str) -> Dict[str, Any]:
        """Fetch dividend ex-dates and declared dividend rates."""
        sym = symbol.strip().upper()
        sym = SYMBOL_ALIASES.get(sym, sym)
        if sym.startswith("^"):
            return {}

        self._ensure_crumb()
        enc_sym = urllib.parse.quote(sym)
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{enc_sym}?modules=calendarEvents,summaryDetail"
        if self.crumb:
            url += f"&crumb={self.crumb}"

        try:
            r = self.session.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                res = data.get("quoteSummary", {}).get("result", [])
                if res:
                    item = res[0]
                    cal = item.get("calendarEvents", {})
                    summ = item.get("summaryDetail", {})
                    return {
                        "ex_dividend_date": cal.get("exDividendDate", {}).get("fmt"),
                        "dividend_date": cal.get("dividendDate", {}).get("fmt"),
                        "dividend_rate": summ.get("dividendRate", {}).get("raw"),
                        "dividend_yield": summ.get("dividendYield", {}).get("raw"),
                    }
        except Exception as e:
            logger.debug(f"Calendar events lookup for {sym}: {e}")

        return {}

    def get_news(self, symbol: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Fetch live ticker news via Yahoo search news endpoint."""
        sym = symbol.strip().upper()
        sym = SYMBOL_ALIASES.get(sym, sym)
        self._ensure_crumb()
        enc_sym = urllib.parse.quote(sym)
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={enc_sym}&newsCount={limit}"
        if self.crumb:
            url += f"&crumb={self.crumb}"

        news_items: List[Dict[str, Any]] = []
        try:
            r = self.session.get(url, timeout=8)
            if r.status_code == 200:
                data = r.json()
                items = data.get("news", [])
                for it in items[:limit]:
                    pub_ts = it.get("providerPublishTime")
                    pub_str = time.strftime("%Y-%m-%d %H:%M", time.gmtime(pub_ts)) if pub_ts else "Recent"
                    news_items.append({
                        "title": it.get("title", ""),
                        "publisher": it.get("publisher", "Yahoo Finance"),
                        "link": it.get("link", f"https://finance.yahoo.com/quote/{sym}/news"),
                        "published_time": pub_str,
                        "summary": it.get("summary") or it.get("title", "")
                    })
        except Exception as e:
            logger.debug(f"News fetch failed for {sym}: {e}")

        return news_items

yahoo_client = YahooFinanceClient()
