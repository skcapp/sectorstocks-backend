import os
import logging
import threading
import time
from datetime import datetime, time as dtime, timedelta

import pytz
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from upstox_client import Configuration, ApiClient
from upstox_client.api.market_quote_api import MarketQuoteApi
from upstox_client.api.history_api import HistoryApi

from instruments import STOCKS, SECTORS

# -------------------------------------------------
# App setup
# -------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

# -------------------------------------------------
# Upstox setup
# -------------------------------------------------
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

config = Configuration()
config.access_token = ACCESS_TOKEN
client = ApiClient(config)

quote_api = MarketQuoteApi(client)
history_api = HistoryApi(client)

# -------------------------------------------------
# Market hours (IST)
# -------------------------------------------------


def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    return dtime(9, 20) <= now <= dtime(15, 30)


# -------------------------------------------------
# Cache
# -------------------------------------------------
CACHE = []

# -------------------------------------------------
# Routes
# -------------------------------------------------


@app.get("/sectors")
def get_sectors():
    return SECTORS


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logging.info(f"=== SCREENER HIT === {sector}")

    if not is_market_open():
        return [{"message": "Market closed"}]

    if sector == "ALL":
        return CACHE

    return [s for s in CACHE if s["sector"] == sector]


# -------------------------------------------------
# Breakout engine (runs every 5 minutes)
# -------------------------------------------------
def refresh_cache():
    global CACHE

    ist = pytz.timezone("Asia/Kolkata")

    while True:
        results = []

        if not is_market_open():
            CACHE = []
            time.sleep(300)
            continue

        for stock in STOCKS:
            try:
                instrument_key = stock["instrument_key"]

                # -------------------------
                # 1️⃣ LTP
                # -------------------------
                quote = quote_api.get_full_market_quote(
                    instrument_key,
                    "2.0"
                )

                ltp = quote.data[instrument_key]["last_price"]

                # -------------------------
                # 2️⃣ 5-minute candles
                # -------------------------
                to_dt = datetime.now(ist)
                from_dt = to_dt - timedelta(minutes=20)

                candles = history_api.get_historical_candle_data(
                    instrument_key,
                    "5minute",
                    from_dt.strftime("%Y-%m-%d"),
                    to_dt.strftime("%Y-%m-%d"),
                    "2.0"
                )

                candle_data = candles.data.candles

                if len(candle_data) < 2:
                    continue

                prev_candle = candle_data[-2]
                curr_candle = candle_data[-1]

                prev_high = prev_candle[2]
                prev_vol = prev_candle[5]
                curr_vol = curr_candle[5]

                # -------------------------
                # 3️⃣ Breakout logic
                # -------------------------
                if ltp > prev_high and curr_vol > prev_vol:
                    results.append({
                        "symbol": instrument_key,
                        "name": stock["name"],
                        "sector": stock["sector"],
                        "ltp": round(ltp, 2),
                        "prev_5min_high": round(prev_high, 2),
                        "volume": curr_vol,
                        "breakout": True
                    })

            except Exception as e:
                logging.error(f"{stock['name']} error: {e}")

        CACHE = results
        logging.info(f"Cache refreshed: {len(CACHE)} breakouts")

        time.sleep(300)  # 5 minutes


# -------------------------------------------------
# Startup
# -------------------------------------------------
@app.on_event("startup")
def startup():
    threading.Thread(target=refresh_cache, daemon=True).start()
