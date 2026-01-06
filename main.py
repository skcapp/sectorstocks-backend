from fastapi import FastAPI, Query
from datetime import datetime, timedelta
import pytz
import os
import logging

from instruments import STOCKS, SECTORS

from upstox_client import Configuration, ApiClient
from upstox_client.apis import MarketQuoteApi, HistoryApi

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# ---------- UPSTOX SETUP ----------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

config = Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN
api_client = ApiClient(config)

quote_api = MarketQuoteApi(api_client)
history_api = HistoryApi(api_client)


# ---------- MARKET TIME CHECK ----------
def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_time <= now <= close_time


# ---------- SECTORS ----------
@app.get("/sectors")
def get_sectors():
    return SECTORS


# ---------- SCREENER ----------
@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logging.info(f"=== SCREENER HIT === {sector}")

    if not is_market_open():
        return [{"message": "Market closed"}]

    # Filter stocks by sector
    if sector == "ALL":
        filtered = STOCKS
    else:
        filtered = [s for s in STOCKS if s["sector"] == sector]

    if not filtered:
        return []

    symbols = [s["symbol"] for s in filtered]

    # ---------- FETCH LTP (BATCH) ----------
    try:
        quote_response = quote_api.get_full_market_quote(
            symbols=symbols,
            api_version="2.0"
        )
    except Exception as e:
        logging.error(f"Upstox quote error: {e}")
        return []

    results = []

    for stock in filtered:
        symbol = stock["symbol"]

        quote = quote_response.data.get(symbol)
        if not quote:
            continue

        ltp = quote["last_price"]

        # ---------- FETCH PREVIOUS 5-MIN HIGH ----------
        try:
            to_dt = datetime.now(pytz.UTC)
            from_dt = to_dt - timedelta(minutes=15)

            candles = history_api.get_historical_candle_data(
                instrument_key=symbol,
                interval="5minute",
                from_date=from_dt.isoformat(),
                to_date=to_dt.isoformat(),
                api_version="2.0"
            ).data.candles

            if len(candles) < 2:
                continue

            prev_5min_high = candles[-2][2]

        except Exception as e:
            logging.error(f"Candle error {symbol}: {e}")
            continue

        # ---------- BREAKOUT LOGIC ----------
        if ltp > prev_5min_high:
            results.append({
                "symbol": symbol,
                "name": stock["name"],
                "sector": stock["sector"],
                "ltp": round(ltp, 2),
                "prev_5min_high": round(prev_5min_high, 2),
                "breakout": True
            })

    return results
