from fastapi import FastAPI, Query
import os

from upstox_client import ApiClient, Configuration
from upstox_client.api.market_quote_api import MarketQuoteApi

from instruments import STOCKS, SECTORS


app = FastAPI()

# ---------------- CONFIG ----------------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

config = Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN
client = ApiClient(config)
market_api = MarketQuoteApi(client)

# ---------------- SCREENER ----------------


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    print("=== SCREENER HIT ===", sector)

    # ✅ FIX 1: sector filter
    if sector == "ALL":
        filtered_stocks = STOCKS
    else:
        filtered_stocks = [s for s in STOCKS if s["sector"] == sector]

    if not filtered_stocks:
        print("No stocks after sector filter")
        return []

    symbols = [s["symbol"] for s in filtered_stocks]

    # Fetch quotes in ONE batch
    quotes = market_api.get_full_market_quote(symbols)

    results = []

    for stock in filtered_stocks:
        symbol = stock["symbol"]

        if symbol not in quotes:
            continue

        quote = quotes[symbol]
        ltp = quote["last_price"]
        day_high = quote["ohlc"]["high"]

        print(symbol, "LTP:", ltp, "HIGH:", day_high)

        # 🔥 Breakout logic (reliable)
        if ltp >= day_high * 0.998:
            results.append({
                "symbol": symbol,
                "name": stock["name"],
                "sector": stock["sector"],
                "ltp": round(ltp, 2),
                "day_high": round(day_high, 2),
                "breakout": True
            })

    return results


@app.get("/sectors")
def sectors():
    return SECTORS
