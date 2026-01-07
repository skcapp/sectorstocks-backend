from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, time
import pytz
import os
import requests
import logging

# ================= CONFIG =================

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

UPSTOX_QUOTE_URL = "https://api.upstox.com/v2/market-quote/quotes"

IST = pytz.timezone("Asia/Kolkata")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# ================= APP =================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DATA =================

INSTRUMENTS = [
    {"name": "RELIANCE", "instrument_key": "NSE_EQ|INE002A01018", "sector": "ALL"},
    {"name": "TCS", "instrument_key": "NSE_EQ|INE467B01029", "sector": "ALL"},
    {"name": "INFY", "instrument_key": "NSE_EQ|INE009A01021", "sector": "ALL"},
    {"name": "ICICIBANK", "instrument_key": "NSE_EQ|INE090A01021", "sector": "ALL"},
    {"name": "HDFCBANK", "instrument_key": "NSE_EQ|INE040A01034", "sector": "ALL"},
    # keep adding…
]

# ================= HELPERS =================


def is_market_open():
    now = datetime.now(IST).time()
    return time(9, 15) <= now <= time(15, 30)


def fetch_quotes(instrument_keys):
    """
    Calls Upstox REST API directly
    """
    headers = {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Accept": "application/json",
    }

    params = {
        "instrument_key": ",".join(instrument_keys)
    }

    try:
        r = requests.get(
            UPSTOX_QUOTE_URL,
            headers=headers,
            params=params,
            timeout=10
        )
        r.raise_for_status()
        return r.json().get("data", {})
    except Exception as e:
        logger.error(f"Quote fetch failed: {e}")
        return {}

# ================= ROUTES =================


@app.get("/debug/instruments")
def debug_instruments():
    return {
        "total": len(INSTRUMENTS),
        "instruments": INSTRUMENTS
    }


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logger.info(f"=== SCREENER HIT === {sector}")

    if not is_market_open():
        return [{"message": "Market closed"}]

    filtered = [
        i for i in INSTRUMENTS
        if sector == "ALL" or i["sector"] == sector
    ]

    if not filtered:
        return []

    instrument_keys = [i["instrument_key"] for i in filtered]

    logger.info(f"Requesting quotes for {len(instrument_keys)} instruments")

    quotes = fetch_quotes(instrument_keys)

    logger.info(f"Quotes received: {len(quotes)}")

    results = []

    for stock in filtered:
        key = stock["instrument_key"]
        q = quotes.get(key)

        if not q:
            continue

        ltp = q.get("last_price")
        ohlc = q.get("ohlc", {})
        open_price = ohlc.get("open")

        if ltp is None or open_price is None:
            continue

        results.append({
            "symbol": stock["name"],
            "open": open_price,
            "ltp": ltp
        })

    return results
