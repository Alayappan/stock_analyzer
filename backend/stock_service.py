import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import concurrent.futures
from typing import Dict, Any, List, Optional

_CACHE: Dict[str, Dict[str, Any]] = {}

def get_from_cache(key: str, ttl_seconds: int = 60) -> Optional[Any]:
    item = _CACHE.get(key)
    if item and (time.time() - item["timestamp"] < ttl_seconds):
        return item["data"]
    return None

def set_to_cache(key: str, data: Any):
    _CACHE[key] = {"timestamp": time.time(), "data": data}

def clean_val(val, decimals: int = 2):
    if val is None or pd.isna(val) or (isinstance(val, (int, float)) and np.isnan(val)):
        return None
    if isinstance(val, (np.floating, float)):
        return round(float(val), decimals)
    if isinstance(val, (np.integer, int)):
        return int(val)
    return val

def fetch_single_stock_info(symbol: str) -> Dict[str, Any]:
    symbol = symbol.upper().strip()
    cache_key = f"yf_full_{symbol}"
    cached = get_from_cache(cache_key, ttl_seconds=120)
    if cached:
        return cached

    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    fast = ticker.fast_info

    # Price resolution
    current_price = (
        info.get("currentPrice") or
        info.get("regularMarketPrice") or
        getattr(fast, "last_price", None) or
        info.get("navPrice")
    )
    prev_close = (
        info.get("previousClose") or
        info.get("regularMarketPreviousClose") or
        getattr(fast, "previous_close", None)
    )

    if current_price and prev_close:
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100
    else:
        change = info.get("regularMarketChange", 0.0)
        change_pct = info.get("regularMarketChangePercent", 0.0)

    # 52w range position (0-100%)
    low52 = info.get("fiftyTwoWeekLow") or getattr(fast, "year_low", None)
    high52 = info.get("fiftyTwoWeekHigh") or getattr(fast, "year_high", None)
    range_pct = 50.0
    if low52 and high52 and current_price and high52 > low52:
        range_pct = round(((current_price - low52) / (high52 - low52)) * 100, 1)

    # Dividend yield calculation
    div_yield = info.get("dividendYield")
    div_rate = info.get("dividendRate")
    if div_yield is not None:
        div_yield_pct = div_yield * 100 if div_yield < 1 else div_yield
    else:
        div_yield_pct = None

    # Target price upside
    target_price = info.get("targetMeanPrice")
    upside_pct = None
    if target_price and current_price and current_price > 0:
        upside_pct = round(((target_price - current_price) / current_price) * 100, 2)

    # Market Cap Category
    mcap = info.get("marketCap") or getattr(fast, "market_cap", None)
    mcap_cat = "Unknown"
    if mcap:
        # Approximate classification
        if mcap >= 200_000_000_000:
            mcap_cat = "Mega Cap"
        elif mcap >= 10_000_000_000:
            mcap_cat = "Large Cap"
        elif mcap >= 2_000_000_000:
            mcap_cat = "Mid Cap"
        else:
            mcap_cat = "Small Cap"

    data = {
        "symbol": symbol,
        "shortName": info.get("shortName") or info.get("longName") or symbol,
        "longName": info.get("longName") or info.get("shortName") or symbol,
        "currency": info.get("currency", "INR" if symbol.endswith(".NS") or symbol.endswith(".BO") else "USD"),
        "exchange": info.get("exchange", "N/A"),
        "sector": info.get("sector") or "Other / ETFs",
        "industry": info.get("industry") or "Diversified",
        "currentPrice": clean_val(current_price),
        "previousClose": clean_val(prev_close),
        "dayChange": clean_val(change),
        "dayChangePercent": clean_val(change_pct),
        "dayLow": clean_val(info.get("dayLow") or getattr(fast, "day_low", None)),
        "dayHigh": clean_val(info.get("dayHigh") or getattr(fast, "day_high", None)),
        "fiftyTwoWeekLow": clean_val(low52),
        "fiftyTwoWeekHigh": clean_val(high52),
        "range52WeekPercent": clean_val(range_pct, 1),
        "marketCap": clean_val(mcap),
        "marketCapCategory": mcap_cat,
        "trailingPE": clean_val(info.get("trailingPE")),
        "forwardPE": clean_val(info.get("forwardPE")),
        "priceToBook": clean_val(info.get("priceToBook")),
        "priceToSales": clean_val(info.get("priceToSalesTrailing12Months")),
        "enterpriseToEbitda": clean_val(info.get("enterpriseToEbitda")),
        "pegRatio": clean_val(info.get("pegRatio")),
        "trailingEps": clean_val(info.get("trailingEps")),
        "forwardEps": clean_val(info.get("forwardEps")),
        "dividendYield": clean_val(div_yield_pct),
        "dividendRate": clean_val(div_rate),
        "beta": clean_val(info.get("beta")),
        "targetMeanPrice": clean_val(target_price),
        "targetUpsidePercent": clean_val(upside_pct),
        "recommendationKey": (info.get("recommendationKey") or "N/A").upper(),
        "numberOfAnalystOpinions": clean_val(info.get("numberOfAnalystOpinions")),
        "fiftyDayAverage": clean_val(info.get("fiftyDayAverage")),
        "twoHundredDayAverage": clean_val(info.get("twoHundredDayAverage")),
        # Financial Health
        "profitMargins": clean_val(info.get("profitMargins") * 100 if info.get("profitMargins") is not None else None),
        "operatingMargins": clean_val(info.get("operatingMargins") * 100 if info.get("operatingMargins") is not None else None),
        "returnOnEquity": clean_val(info.get("returnOnEquity") * 100 if info.get("returnOnEquity") is not None else None),
        "returnOnAssets": clean_val(info.get("returnOnAssets") * 100 if info.get("returnOnAssets") is not None else None),
        "debtToEquity": clean_val(info.get("debtToEquity")),
        "totalDebt": clean_val(info.get("totalDebt")),
        "totalCash": clean_val(info.get("totalCash")),
        "freeCashflow": clean_val(info.get("freeCashflow")),
        "operatingCashflow": clean_val(info.get("operatingCashflow")),
        # Profile
        "website": info.get("website", ""),
        "longBusinessSummary": info.get("longBusinessSummary", ""),
        "city": info.get("city", ""),
        "state": info.get("state", ""),
        "country": info.get("country", ""),
        "fullTimeEmployees": info.get("fullTimeEmployees")
    }

    set_to_cache(cache_key, data)
    return data

def analyze_full_portfolio(raw_holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Given raw holdings [{ symbol, shares, avg_buy_price, cost_basis }],
    fetches live Yahoo Finance metrics concurrently, computes portfolio allocation,
    risk factors, weighted beta, dividend yields, and sector breakdown.
    """
    if not raw_holdings:
        return {
            "summary": {
                "totalMarketValue": 0.0,
                "totalCostBasis": 0.0,
                "totalGainLoss": 0.0,
                "totalGainLossPercent": 0.0,
                "totalDayChange": 0.0,
                "totalDayChangePercent": 0.0,
                "totalAnnualDividends": 0.0,
                "portfolioDividendYield": 0.0,
                "portfolioBeta": 1.0,
                "portfolioPE": 0.0,
                "totalHoldings": 0,
                "profitableCount": 0,
                "lossCount": 0
            },
            "holdings": [],
            "sectorAllocation": [],
            "marketCapAllocation": [],
            "topWinners": [],
            "topLosers": []
        }

    symbols = [h["symbol"] for h in raw_holdings]

    # Concurrent fetch from Yahoo Finance
    yahoo_data_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        future_to_sym = {executor.submit(fetch_single_stock_info, sym): sym for sym in symbols}
        for future in concurrent.futures.as_completed(future_to_sym):
            sym = future_to_sym[future]
            try:
                yahoo_data_map[sym] = future.result()
            except Exception:
                yahoo_data_map[sym] = {
                    "symbol": sym,
                    "shortName": sym,
                    "currentPrice": None,
                    "sector": "Other",
                    "exchange": "N/A"
                }

    # Aggregate holdings with Yahoo Finance data
    total_market_value = 0.0
    total_cost_basis = 0.0
    total_day_change = 0.0
    total_annual_dividends = 0.0

    analyzed_holdings = []

    for h in raw_holdings:
        sym = h["symbol"]
        shares = float(h["shares"])
        avg_price = float(h["avg_buy_price"])
        cost_basis = float(h["cost_basis"])

        yf_info = yahoo_data_map.get(sym, {})
        current_price = yf_info.get("currentPrice") or avg_price
        day_chg = yf_info.get("dayChange") or 0.0
        day_chg_pct = yf_info.get("dayChangePercent") or 0.0

        market_val = shares * current_price
        gain_loss = market_val - cost_basis
        gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0.0
        pos_day_chg = shares * day_chg

        # Dividend calculation
        div_rate = yf_info.get("dividendRate")
        div_yield = yf_info.get("dividendYield")
        if div_rate and div_rate > 0:
            pos_annual_div = shares * div_rate
        elif div_yield and div_yield > 0:
            pos_annual_div = market_val * (div_yield / 100)
        else:
            pos_annual_div = 0.0

        total_market_value += market_val
        total_cost_basis += cost_basis
        total_day_change += pos_day_chg
        total_annual_dividends += pos_annual_div

        holding_record = {
            **yf_info,
            "shares": shares,
            "avgBuyPrice": avg_price,
            "costBasis": round(cost_basis, 2),
            "currentPrice": current_price,
            "marketValue": round(market_val, 2),
            "gainLoss": round(gain_loss, 2),
            "gainLossPercent": round(gain_loss_pct, 2),
            "positionDayChange": round(pos_day_chg, 2),
            "positionDayChangePercent": round(day_chg_pct, 2),
            "positionAnnualDividend": round(pos_annual_div, 2),
            "buyCount": h.get("buy_count", 1),
            "sellCount": h.get("sell_count", 0),
            "latestTradeDate": h.get("latest_date", "")
        }
        analyzed_holdings.append(holding_record)

    # Compute portfolio weights & portfolio weighted beta / PE
    weighted_beta_sum = 0.0
    beta_weight_total = 0.0
    weighted_pe_sum = 0.0
    pe_weight_total = 0.0

    profitable_count = 0
    loss_count = 0

    sector_totals: Dict[str, float] = {}
    mcap_totals: Dict[str, float] = {}

    for h in analyzed_holdings:
        m_val = h["marketValue"]
        weight_pct = (m_val / total_market_value * 100) if total_market_value > 0 else 0.0
        h["portfolioWeightPercent"] = round(weight_pct, 2)

        if h["gainLoss"] >= 0:
            profitable_count += 1
        else:
            loss_count += 1

        # Beta
        beta = h.get("beta")
        if beta and beta > 0:
            weighted_beta_sum += (beta * m_val)
            beta_weight_total += m_val

        # PE
        pe = h.get("trailingPE")
        if pe and 0 < pe < 300: # Exclude extreme outliers
            weighted_pe_sum += (pe * m_val)
            pe_weight_total += m_val

        # Sector
        sec = h.get("sector") or "Other"
        sector_totals[sec] = sector_totals.get(sec, 0.0) + m_val

        # Market Cap
        mcat = h.get("marketCapCategory") or "Other"
        mcap_totals[mcat] = mcap_totals.get(mcat, 0.0) + m_val

    # Summary metrics
    net_gain = total_market_value - total_cost_basis
    net_gain_pct = (net_gain / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
    prev_total_val = total_market_value - total_day_change
    day_gain_pct = (total_day_change / prev_total_val * 100) if prev_total_val > 0 else 0.0

    port_dividend_yield = (total_annual_dividends / total_market_value * 100) if total_market_value > 0 else 0.0
    port_beta = (weighted_beta_sum / beta_weight_total) if beta_weight_total > 0 else 1.0
    port_pe = (weighted_pe_sum / pe_weight_total) if pe_weight_total > 0 else None

    # Format sector allocation list
    sector_alloc = []
    for sec, val in sorted(sector_totals.items(), key=lambda x: x[1], reverse=True):
        sector_alloc.append({
            "sector": sec,
            "value": round(val, 2),
            "percentage": round((val / total_market_value * 100) if total_market_value > 0 else 0.0, 2)
        })

    # Format market cap allocation
    mcap_alloc = []
    for cat, val in sorted(mcap_totals.items(), key=lambda x: x[1], reverse=True):
        mcap_alloc.append({
            "category": cat,
            "value": round(val, 2),
            "percentage": round((val / total_market_value * 100) if total_market_value > 0 else 0.0, 2)
        })

    # Sort holdings by market value descending by default
    analyzed_holdings.sort(key=lambda x: x["marketValue"], reverse=True)

    # Top winners and losers by Gain/Loss %
    sorted_by_gain = sorted(analyzed_holdings, key=lambda x: x["gainLossPercent"], reverse=True)
    top_winners = sorted_by_gain[:4]
    top_losers = sorted(analyzed_holdings, key=lambda x: x["gainLossPercent"])[:4]

    return {
        "summary": {
            "totalMarketValue": round(total_market_value, 2),
            "totalCostBasis": round(total_cost_basis, 2),
            "totalGainLoss": round(net_gain, 2),
            "totalGainLossPercent": round(net_gain_pct, 2),
            "totalDayChange": round(total_day_change, 2),
            "totalDayChangePercent": round(day_gain_pct, 2),
            "totalAnnualDividends": round(total_annual_dividends, 2),
            "portfolioDividendYield": round(port_dividend_yield, 2),
            "portfolioBeta": round(port_beta, 2),
            "portfolioPE": round(port_pe, 2) if port_pe else None,
            "totalHoldings": len(analyzed_holdings),
            "profitableCount": profitable_count,
            "lossCount": loss_count
        },
        "holdings": analyzed_holdings,
        "sectorAllocation": sector_alloc,
        "marketCapAllocation": mcap_alloc,
        "topWinners": top_winners,
        "topLosers": top_losers
    }

def get_stock_deep_dive(symbol: str) -> Dict[str, Any]:
    """
    Returns full Yahoo Finance details for a holding modal/inspector.
    """
    base = fetch_single_stock_info(symbol)

    # Fetch news
    articles = []
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={symbol}&newsCount=6"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=4).json()
        for item in res.get("news", []):
            thumb_url = ""
            if "thumbnail" in item and "resolutions" in item["thumbnail"]:
                resolutions = item["thumbnail"]["resolutions"]
                if resolutions:
                    thumb_url = resolutions[-1].get("url", "")
            articles.append({
                "title": item.get("title"),
                "publisher": item.get("publisher"),
                "link": item.get("link"),
                "publishTime": item.get("providerPublishTime"),
                "thumbnail": thumb_url
            })
    except Exception:
        pass

    return {
        **base,
        "news": articles
    }

