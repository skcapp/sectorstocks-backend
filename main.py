import os
import logging
from datetime import datetime, timedelta
import pytz

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from upstox_client import Configuration, ApiClient
from upstox_client.api.market_quote_api import MarketQuoteApi
from upstox_client.api.history_api import HistoryApi

from instruments import STOCKS, SECTORS

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Upstox setup
# --------------------------------------------------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
API_VERSION = "2.0"

config = Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN
api_client = ApiClient(config)

market_api = MarketQuoteApi(api_client)
history_api = HistoryApi(api_client)

IST = pytz.timezone("Asia/Kolkata")

# --------------------------------------------------
# Helpers
# --------------------------------------------------


def is_market_open():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False

    open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_time <= now <= close_time


def prev_5min_window():
    now = datetime.now(IST)
    end = now.replace(second=0, microsecond=0)
    start = end - timedelta(minutes=5)
    return start, end


# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.get("/sectors")
def sectors():
    return SECTORS


@app.get("/debug/instruments")
def debug_instruments():
    return {
        "total": len(STOCKS),
        "instrument_keys": [s.get("instrument_key") for s in STOCKS],
    }


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logger.info(f"=== SCREENER HIT === {sector}")

    if not is_market_open():
        return [{"message": "Market closed"}]

    # ------------------------------
    # Filter stocks
    # ------------------------------
    if sector == "ALL":
        filtered = STOCKS
    else:
        filtered = [s for s in STOCKS if s.get("sector") == sector]

    if not filtered:
        return []

    instrument_keys = []
    stock_map = {}

    for s in filtered:
        key = s.get("instrument_key")
        if not key:
            continue
        instrument_keys.append(key)
        stock_map[key] = s

    if not instrument_keys:
        return []

    # --------------------------------------------------
    # ✅ FIX: comma-separated string (Upstox requirement)
    # --------------------------------------------------
    instrument_key_str = ",".join(instrument_keys)

    logger.info(f"Requesting quotes for {len(instrument_keys)} instruments")

    try:
        quote_resp = market_api.get_full_market_quote(
            symbol=instrument_key_str,   # ← YES, symbol is instrument_key
            api_version=API_VERSION
        )
        quotes = quote_resp.data.data or {}
        logger.info(f"Quotes received: {len(quotes)}")
        logger.info(f"Quote keys sample: {list(quotes.keys())[:3]}")
    except Exception as e:
        logger.error(f"Upstox quote error: {e}")
        return []

    start, end = prev_5min_window()
    results = []

    # --------------------------------------------------
    # Breakout logic
    # --------------------------------------------------
    for inst_key, stock in stock_map.items():
        if inst_key not in quotes:
            continue

        try:
            ltp = quotes[inst_key]["last_price"]

            candle_resp = history_api.get_historical_candle_data(
                instrument_key=inst_key,
                interval="5minute",
                from_date=start.strftime("%Y-%m-%d %H:%M"),
                to_date=end.strftime("%Y-%m-%d %H:%M"),
                api_version=API_VERSION
            )

            candles = candle_resp.data or []
            if not candles:
                continue

            prev_high = max(c[2] for c in candles)

            logger.info(
                f"{stock['name']} | LTP={ltp} | PrevHigh={prev_high}"
            )

            # 🔥 breakout condition
            if ltp > prev_high:
                results.append({
                    "instrument_key": inst_key,
                    "name": stock["name"],
                    "sector": stock["sector"],
                    "ltp": round(ltp, 2),
                    "prev_5min_high": round(prev_high, 2),
                    "breakout": True
                })

        except Exception as e:
            logger.error(f"{inst_key} processing error: {e}")

    return results
