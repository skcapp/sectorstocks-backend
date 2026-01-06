from fastapi import FastAPI, Query
import os

from upstox_client import ApiClient, Configuration
from upstox_client.api.market_quote_api import MarketQuoteApi

from instruments import STOCKS, SECTORS

app = FastAPI()

# -------- CONFIG --------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
if not UPSTOX_ACCESS_TOKEN:
    raise RuntimeError("UPSTOX_ACCESS_TOKEN not set")

config = Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN

client = ApiClient(config)
market_api = MarketQuoteApi(client)

# -------- ENDPOINTS --------


@app.get("/sectors")
def get_sectors():
    return SECTORS


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    print("=== SCREENER HIT ===", sector)

    if sector == "ALL":
        filtered = STOCKS
    else:
        filtered = [s for s in STOCKS if s["sector"] == sector]

    if not filtered:
        return []

    instrument_keys = [s["instrument_key"] for s in filtered]

    try:
        response = market_api.get_full_market_quote(
            api_version="2.0",
            instrument_key=",".join(instrument_keys)
        )
        quotes = response.data
    except Exception as e:
        print("Upstox API error:", e)
        return []

    results = []

    for stock in filtered:
        key = stock["instrument_key"]

        if key not in quotes:
            continue

        q = quotes[key]
        ltp = q.get("last_price")
        ohlc = q.get("ohlc")

        if not ltp or not ohlc:
            continue

        day_high = ohlc.get("high")
        if not day_high:
            continue

        print(stock["name"], ltp, day_high)

        # 🔥 Day High Breakout
        if ltp >= day_high * 0.998:
            results.append({
                "name": stock["name"],
                "sector": stock["sector"],
                "ltp": round(ltp, 2),
                "day_high": round(day_high, 2),
                "breakout": True
            })

    return results
