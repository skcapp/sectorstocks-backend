import os
import logging
from datetime import datetime, timedelta, time
from typing import List

from fastapi import FastAPI, Query
import pytz

import upstox_client
from upstox_client import MarketQuoteApi, HistoryApi

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- FASTAPI ----------------
app = FastAPI()

# ---------------- UPSTOX SETUP ----------------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

config = upstox_client.Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN
api_client = upstox_client.ApiClient(config)

market_api = MarketQuoteApi(api_client)
history_api = HistoryApi(api_client)

API_VERSION = "2.0"
IST = pytz.timezone("Asia/Kolkata")

# ---------------- STOCK MASTER ----------------
STOCKS = [
    {"symbol": "HDFCBANK", "instrument_key": "NSE_EQ|HDFCBANK", "sector": "BANKING"},
    {"symbol": "ICICIBANK", "instrument_key": "NSE_EQ|ICICIBANK", "sector": "BANKING"},
    {"symbol": "INFY", "instrument_key": "NSE_EQ|INFY", "sector": "IT"},
    {"symbol": "TCS", "instrument_key": "NSE_EQ|TCS", "sector": "IT"},
    {"symbol": "SUNPHARMA", "instrument_key": "NSE_EQ|SUNPHARMA", "sector": "PHARMA"},
    {"symbol": "CIPLA", "instrument_key": "NSE_EQ|CIPLA", "sector": "PHARMA"},
    {"symbol": "MARUTI", "instrument_key": "NSE_EQ|MARUTI", "sector": "AUTO"},
    {"symbol": "HEROMOTOCO", "instrument_key": "NSE_EQ|HEROMOTOCO", "sector": "AUTO"},
]

SECTORS = sorted(set(s["sector"] for s in STOCKS))
SECTORS.insert(0, "ALL")

# ---------------- HELPERS ----------------


def market_is_open() -> bool:
    now = datetime.now(IST).time()
    return time(9, 15) <= now <= time(15, 30)

# ---------------- ROUTES ----------------


@app.get("/sectors")
def sectors():
    return SECTORS


@app.get("/screener")
def screener(sector: str = Query(...)):
    logger.info(f"=== SCREENER HIT === {sector}")

    if not market_is_open():
        return [{"message": "Market closed"}]

    # Filter stocks
    if sector == "ALL":
        filtered = STOCKS
    else:
        filtered = [s for s in STOCKS if s["sector"] == sector]

    if not filtered:
        return []

    instrument_keys = [s["instrument_key"] for s in filtered]

    # ---------- FETCH LTPs (BATCH) ----------
    try:
        quote_response = market_api.get_full_market_quote(
            symbol=",".join(instrument_keys),
            api_version=API_VERSION
        )
    except Exception as e:
        logger.error(f"LTP fetch failed: {e}")
        return []

    quotes = quote_response.data or {}
    results = []

    for stock in filtered:
        ikey = stock["instrument_key"]
        symbol = stock["symbol"]

        if ikey not in quotes:
            continue

        ltp = quotes[ikey]["last_price"]

        # ---------- FETCH 5-MIN CANDLES ----------
        try:
            to_dt = datetime.now(IST)
            from_dt = to_dt - timedelta(minutes=20)

            candles_resp = history_api.get_historical_candle_data(
                instrument_key=ikey,
                interval="5minute",
                from_date=from_dt.strftime("%Y-%m-%d %H:%M"),
                to_date=to_dt.strftime("%Y-%m-%d %H:%M"),
                api_version=API_VERSION
            )

            candles = candles_resp.data.candles if candles_resp.data else []

            # Need at least 2 candles → use PREVIOUS CLOSED candle
            if len(candles) < 2:
                continue

            prev_closed = candles[-2]
            prev_high = prev_closed[2]

            logger.info(
                f"{symbol} | LTP={ltp} | Prev5High={prev_high}"
            )

            # ----------Toggle breakout threshold here if needed ----------
            if ltp > prev_high:
                results.append({
                    "symbol": symbol,
                    "sector": stock["sector"],
                    "ltp": round(ltp, 2),
                    "prev_5min_high": round(prev_high, 2),
                    "breakout": True
                })

        except Exception as e:
            logger.error(f"{symbol} candle error: {e}")

    return results
