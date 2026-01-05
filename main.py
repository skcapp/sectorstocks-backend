import upstox_client
from upstox_client.configuration import Configuration
from upstox_client.api_client import ApiClient
from upstox_client.api.market_quote_api import MarketQuoteApi
from upstox_client.api.history_api import HistoryApi

from fastapi import FastAPI, Query
from datetime import datetime, timedelta, time
import os
import requests
import pytz
from instruments import STOCKS, SECTORS

app = FastAPI()

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

config = Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN

api_client = ApiClient(config)


quote_api = MarketQuoteApi(api_client)
history_api = HistoryApi(api_client)


IST = pytz.timezone("Asia/Kolkata")


def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()

    market_open = time(9, 15)
    market_close = time(15, 30)

    return market_open <= now <= market_close

# ---------- SECTORS ----------


@app.get("/sectors")
def get_sectors():
    return SECTORS


# ---------- SCREENER ----------
@app.get("/screener")
def screener(sector: str = Query("ALL")):
    print("=== SCREENER HIT ===")
    print("Sector:", sector)

    now = datetime.now(IST)

    # ---- Market hours check ----

    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

    if not (market_open <= now <= market_close):
        return [{"message": "Market closed"}]

    # ---- Symbols to scan ----
    scan_stocks = [
        s for s in STOCKS
        if sector == "ALL" or s["sector"] == sector
    ]

    if not scan_stocks:
        return []

    symbols = [s["symbol"] for s in scan_stocks]

    # ---- Batch LTP ----
    try:
        ltp_resp = quote_api.get_ltp(symbols=",".join(symbols))
        ltp_map = {
            k: v.last_price
            for k, v in ltp_resp.data.items()
            if v.last_price
        }
    except Exception as e:
        print("LTP ERROR:", e)
        return []

    print("LTP COUNT:", len(ltp_map))

    # ---- Candle time window ----
    to_date = now.strftime("%Y-%m-%d %H:%M")
    from_date = (now - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M")

    results = []

    for stock in scan_stocks:
        symbol = stock["symbol"]
        ltp = ltp_map.get(symbol)

        if not ltp:
            continue

        try:
            history_response = history_api.get_historical_candle_data(
                instrument_key=symbol,
                interval="5minute",
                from_date=from_date,
                to_date=to_date
            )

            candles = history_response.data.candles

            if not candles or len(candles) < 2:
                continue

            # PREVIOUS COMPLETED 5-MIN CANDLE
            prev_high = float(candles[-2][2])

            print(
                stock["name"],
                "LTP:", ltp,
                "PREV_HIGH:", prev_high
            )

            # ---- BREAKOUT LOGIC ----
            if ltp >= prev_high * 0.995:
                results.append({
                    "symbol": symbol,
                    "name": stock["name"],
                    "sector": stock["sector"],
                    "ltp": round(ltp, 2),
                    "prev_5min_high": round(prev_high, 2),
                    "breakout": True
                })

        except Exception as e:
            print("CANDLE ERROR:", stock["name"], e)
            continue

    return results
