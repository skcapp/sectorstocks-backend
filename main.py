import os
import logging
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from upstox_python_sdk.api import Upstox

# ==========================
# CONFIG
# ==========================
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

API_VERSION = "v2"

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MIN = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MIN = 30

# ==========================
# LOGGING
# ==========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# ==========================
# APP
# ==========================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# UPSTOX CLIENT
# ==========================
u = Upstox(UPSTOX_API_KEY, UPSTOX_ACCESS_TOKEN)
market_api = u.market_api()

# ==========================
# STOCK MASTER
# ==========================
STOCKS = [
    {"name": "HDFCBANK", "symbol": "NSE_EQ|HDFCBANK", "sector": "BANKING"},
    {"name": "ICICIBANK", "symbol": "NSE_EQ|ICICIBANK", "sector": "BANKING"},
    {"name": "INFY", "symbol": "NSE_EQ|INFY", "sector": "IT"},
    {"name": "TCS", "symbol": "NSE_EQ|TCS", "sector": "IT"},
    {"name": "RELIANCE", "symbol": "NSE_EQ|RELIANCE", "sector": "ENERGY"},
    # add remaining stocks
]

# ==========================
# HELPERS
# ==========================


def is_market_open():
    now = datetime.now()
    return (
        (now.hour > MARKET_OPEN_HOUR or
         (now.hour == MARKET_OPEN_HOUR and now.minute >= MARKET_OPEN_MIN))
        and
        (now.hour < MARKET_CLOSE_HOUR or
         (now.hour == MARKET_CLOSE_HOUR and now.minute <= MARKET_CLOSE_MIN))
    )


def filter_stocks(sector):
    if sector == "ALL":
        return STOCKS
    return [s for s in STOCKS if s["sector"] == sector]

# ==========================
# SCREENER
# ==========================


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logger.info(f"=== SCREENER HIT === {sector}")

    if not is_market_open():
        return [{"message": "Market closed"}]

    filtered = filter_stocks(sector)
    symbols = [s["symbol"] for s in filtered]

    logger.info(f"Requesting quotes for {len(symbols)} instruments")

    try:
        quote_resp = market_api.get_full_market_quote(
            symbol=",".join(symbols),
            api_version=API_VERSION
        )

        # ✅ CORRECT FIX
        quotes = quote_resp.get("data", {})
        logger.info(f"Quotes received: {len(quotes)}")

    except Exception as e:
        logger.error(f"Upstox quote error: {e}")
        return []

    results = []

    for stock in filtered:
        q = quotes.get(stock["symbol"])
        if not q:
            continue

        ltp = q.get("last_price", 0)
        high = q.get("ohlc", {}).get("high", 0)

        if ltp > high:
            results.append({
                "symbol": stock["symbol"],
                "name": stock["name"],
                "sector": stock["sector"],
                "ltp": ltp,
                "high": high
            })

    return results

# ==========================
# DEBUG
# ==========================


@app.get("/debug/instruments")
def debug_instruments():
    return {
        "total": len(STOCKS),
        "valid": len(STOCKS),
        "invalid": 0,
        "symbols": [s["symbol"] for s in STOCKS]
    }
