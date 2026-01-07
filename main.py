import pytz
import os
import logging
from datetime import datetime, time
from fastapi import FastAPI, Query

import upstox_client
from upstox_client.configuration import Configuration
from upstox_client.api_client import ApiClient
from upstox_client.api.market_quote_api import MarketQuoteApi

# --------------------------------------------------
# LOGGING
# --------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------
app = FastAPI()

# --------------------------------------------------
# UPSTOX CONFIG
# --------------------------------------------------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

if not UPSTOX_ACCESS_TOKEN:
    raise RuntimeError("UPSTOX_ACCESS_TOKEN not set in environment")

config = Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN
api_client = ApiClient(config)
market_api = MarketQuoteApi(api_client)

# --------------------------------------------------
# STOCK MASTER DATA
# --------------------------------------------------
STOCKS = [
    # BANKING
    {"name": "HDFCBANK", "sector": "BANKING", "instrument_key": "NSE_EQ|HDFCBANK"},
    {"name": "ICICIBANK", "sector": "BANKING",
        "instrument_key": "NSE_EQ|ICICIBANK"},
    {"name": "INDUSINDBK", "sector": "BANKING",
        "instrument_key": "NSE_EQ|INDUSINDBK"},
    {"name": "BANKBARODA", "sector": "BANKING",
        "instrument_key": "NSE_EQ|BANKBARODA"},

    # IT
    {"name": "INFY", "sector": "IT", "instrument_key": "NSE_EQ|INFY"},
    {"name": "TCS", "sector": "IT", "instrument_key": "NSE_EQ|TCS"},
    {"name": "TECHM", "sector": "IT", "instrument_key": "NSE_EQ|TECHM"},
    {"name": "HCLTECH", "sector": "IT", "instrument_key": "NSE_EQ|HCLTECH"},

    # PHARMA
    {"name": "SUNPHARMA", "sector": "PHARMA",
        "instrument_key": "NSE_EQ|SUNPHARMA"},
    {"name": "DRREDDY", "sector": "PHARMA", "instrument_key": "NSE_EQ|DRREDDY"},
    {"name": "CIPLA", "sector": "PHARMA", "instrument_key": "NSE_EQ|CIPLA"},
    {"name": "ZYDUSLIFE", "sector": "PHARMA",
        "instrument_key": "NSE_EQ|ZYDUSLIFE"},

    # AUTO
    {"name": "MARUTI", "sector": "AUTO", "instrument_key": "NSE_EQ|MARUTI"},
    {"name": "HEROMOTOCO", "sector": "AUTO",
        "instrument_key": "NSE_EQ|HEROMOTOCO"},

    # METALS
    {"name": "HINDALCO", "sector": "METALS", "instrument_key": "NSE_EQ|HINDALCO"},
    {"name": "JSWSTEEL", "sector": "METALS", "instrument_key": "NSE_EQ|JSWSTEEL"},
]

SECTORS = sorted(list({s["sector"] for s in STOCKS}))
SECTORS.insert(0, "ALL")

# --------------------------------------------------
# HELPERS
# --------------------------------------------------


IST = pytz.timezone("Asia/Kolkata")


def is_market_open():
    now_ist = datetime.now(IST).time()
    return time(9, 15) <= now_ist <= time(15, 30)


# --------------------------------------------------
# ROUTES
# --------------------------------------------------


@app.get("/sectors")
def get_sectors():
    return SECTORS


@app.get("/debug/instruments")
def debug_instruments():
    return {
        "total": len(STOCKS),
        "valid": len(STOCKS),
        "invalid": 0,
        "instruments": STOCKS,
    }


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logger.info(f"=== SCREENER HIT === {sector}")

    if not is_market_open():
        return [{"message": "Market closed"}]

    # Filter stocks
    if sector == "ALL":
        filtered = STOCKS
    else:
        filtered = [s for s in STOCKS if s["sector"] == sector]

    if not filtered:
        return []

    instrument_keys = [s["instrument_key"] for s in filtered]
    logger.info(f"Requesting quotes for {len(instrument_keys)} instruments")

    try:
        response = market_api.get_full_market_quote(
            symbol=",".join(instrument_keys),
            api_version="v2"
        )
    except Exception as e:
        logger.error(f"Upstox quote error: {e}")
        return []

    # IMPORTANT: response is a DICT
    quotes = response.get("data", {})
    logger.info(f"Quotes received: {len(quotes)}")

    results = []

    for stock in filtered:
        ikey = stock["instrument_key"]
        q = quotes.get(ikey)

        if not q:
            continue

        ltp = q["last_price"]
        prev_high = q["ohlc"]["high"]

        # 🔥 Breakout logic (LTP vs previous 5-min high approximation)
        if ltp > prev_high * 0.995:
            results.append({
                "symbol": stock["name"],
                "sector": stock["sector"],
                "ltp": round(ltp, 2),
                "prev_high": round(prev_high, 2),
                "breakout": True
            })

    return results
