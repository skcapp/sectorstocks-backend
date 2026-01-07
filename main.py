import os
import logging
from datetime import datetime, time

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

import upstox_client
from upstox_client.api.market_quote_api import MarketQuoteApi


# -------------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# -------------------------------------------------------------------
# FASTAPI APP
# -------------------------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# UPSTOX CONFIG
# -------------------------------------------------------------------
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

configuration = upstox_client.Configuration()
configuration.access_token = ACCESS_TOKEN

api_client = upstox_client.ApiClient(configuration)
quote_api = MarketQuoteApi(api_client)

# -------------------------------------------------------------------
# SECTORS & INSTRUMENT KEYS
# -------------------------------------------------------------------
SECTORS = {
    "IT": [
        "NSE_EQ|INFY",
        "NSE_EQ|TCS",
        "NSE_EQ|TECHM",
        "NSE_EQ|HCLTECH",
    ],
    "BANK": [
        "NSE_EQ|HDFCBANK",
        "NSE_EQ|ICICIBANK",
        "NSE_EQ|INDUSINDBK",
        "NSE_EQ|BANKBARODA",
    ],
    "ALL": [
        "NSE_EQ|INFY",
        "NSE_EQ|TCS",
        "NSE_EQ|TECHM",
        "NSE_EQ|HCLTECH",
        "NSE_EQ|HDFCBANK",
        "NSE_EQ|ICICIBANK",
        "NSE_EQ|INDUSINDBK",
        "NSE_EQ|BANKBARODA",
        "NSE_EQ|RELIANCE",
        "NSE_EQ|LT",
        "NSE_EQ|ITC",
        "NSE_EQ|SBIN",
        "NSE_EQ|AXISBANK",
        "NSE_EQ|MARUTI",
        "NSE_EQ|TATAMOTORS",
        "NSE_EQ|SUNPHARMA",
        "NSE_EQ|DRREDDY",
        "NSE_EQ|CIPLA",
        "NSE_EQ|JSWSTEEL",
        "NSE_EQ|TATASTEEL",
        "NSE_EQ|ADANIENT",
        "NSE_EQ|HINDALCO",
        "NSE_EQ|BPCL",
        "NSE_EQ|ONGC",
        "NSE_EQ|NTPC",
        "NSE_EQ|POWERGRID",
        "NSE_EQ|ULTRACEMCO",
        "NSE_EQ|GRASIM",
        "NSE_EQ|BAJFINANCE",
        "NSE_EQ|BAJAJFINSV",
        "NSE_EQ|KOTAKBANK",
        "NSE_EQ|ASIANPAINT",
        "NSE_EQ|NESTLEIND",
        "NSE_EQ|BRITANNIA",
        "NSE_EQ|WIPRO",
        "NSE_EQ|COALINDIA",
        "NSE_EQ|TITAN",
        "NSE_EQ|HINDUNILVR",
        "NSE_EQ|SBILIFE",
    ],
}

# -------------------------------------------------------------------
# MARKET TIME CHECK (OPTIONAL)
# -------------------------------------------------------------------


def is_market_open():
    now = datetime.now().time()
    return time(9, 15) <= now <= time(15, 30)

# -------------------------------------------------------------------
# DEBUG ENDPOINT
# -------------------------------------------------------------------


@app.get("/debug/instruments")
def debug_instruments():
    all_keys = sorted(set(k for v in SECTORS.values() for k in v))
    return {
        "total": len(all_keys),
        "instrument_keys": all_keys,
    }

# -------------------------------------------------------------------
# SCREENER ENDPOINT
# -------------------------------------------------------------------


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    sector = sector.upper()
    logger.info(f"=== SCREENER HIT === {sector}")

    if sector not in SECTORS:
        return {"error": "Invalid sector"}

    instrument_keys = SECTORS[sector]
    logger.info(f"Requesting quotes for {len(instrument_keys)} instruments")

    # Optional market time check
    if not is_market_open():
        return [{"message": "Market closed"}]

    try:
        quotes = quote_api.get_full_market_quote(
            instrument_key=instrument_keys
        )

        logger.info(f"Quotes received: {len(quotes)}")

    except Exception as e:
        logger.error(f"Upstox quote error: {e}")
        return []

    results = []

    # ----------------------------------------------------------------
    # CRITICAL FIX — CORRECT QUOTE PARSING
    # ----------------------------------------------------------------
    for instrument_key, q in quotes.items():
        try:
            results.append({
                "instrument_key": instrument_key,
                "ltp": q.get("last_price"),
                "open": q.get("ohlc", {}).get("open"),
                "high": q.get("ohlc", {}).get("high"),
                "low": q.get("ohlc", {}).get("low"),
                "close": q.get("ohlc", {}).get("close"),
            })
        except Exception as e:
            logger.error(f"Parse error for {instrument_key}: {e}")

    return results
