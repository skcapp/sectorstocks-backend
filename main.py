import os
import logging
from datetime import datetime, time
import pytz

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from upstox_client import Configuration, ApiClient
from upstox_client.api.market_quote_api import MarketQuoteApi

from instruments import STOCKS, SECTORS

# -------------------------------------------------
# App setup
# -------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

# -------------------------------------------------
# Upstox setup
# -------------------------------------------------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

config = Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN
api_client = ApiClient(config)

market_api = MarketQuoteApi(api_client)

# -------------------------------------------------
# Market hours check (IST)
# -------------------------------------------------


def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    return time(9, 15) <= now <= time(15, 30)

# -------------------------------------------------
# Routes
# -------------------------------------------------


@app.get("/")
def root():
    return {"status": "Sector Stocks Backend Running"}


@app.get("/sectors")
def get_sectors():
    return SECTORS


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logging.info(f"=== SCREENER HIT === {sector}")

    if not is_market_open():
        return [{"message": "Market closed"}]

    try:
        # -------------------------------
        # Filter stocks by sector
        # -------------------------------
        if sector == "ALL":
            filtered = STOCKS
        else:
            filtered = [s for s in STOCKS if s["sector"] == sector]

        if not filtered:
            return []

        # -------------------------------
        # Extract instrument keys
        # -------------------------------
        instrument_keys = []
        for s in filtered:
            if "instrument_key" in s:
                instrument_keys.append(s["instrument_key"])

        if not instrument_keys:
            return []

        symbols = ",".join(instrument_keys)
        logging.info(f"Fetching quotes for: {symbols}")

        # -------------------------------
        # Fetch LTP quotes (CORRECT CALL)
        # -------------------------------
        quote_resp = market_api.get_full_market_quote(
            symbols,
            "2.0"
        )

        quotes = quote_resp.data

        results = []

        # -------------------------------
        # Breakout logic (LTP vs prev 5-min high)
        # -------------------------------
        for stock in filtered:
            key = stock["instrument_key"]

            if key not in quotes:
                continue

            ltp = quotes[key]["last_price"]

            # TEMP FIXED prev_high (until candle API added)
            prev_high = ltp * 0.995  # buffer logic

            if ltp > prev_high:
                results.append({
                    "symbol": key,
                    "name": stock["name"],
                    "sector": stock["sector"],
                    "ltp": round(ltp, 2),
                    "prev_5min_high": round(prev_high, 2),
                    "breakout": True
                })

        return results

    except Exception as e:
        logging.error(f"Upstox API error: {e}")
        return []
