from fastapi import FastAPI, Query
import os

from upstox_client import ApiClient, Configuration
from upstox_client.api.market_quote_api import MarketQuoteApi

from instruments import STOCKS, SECTORS

app = FastAPI()

# ---------- CONFIG ----------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

if not UPSTOX_ACCESS_TOKEN:
    raise RuntimeError("UPSTOX_ACCESS_TOKEN not set")

config = Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN

client = ApiClient(config)
market_api = MarketQuoteApi(client)

# ---------- ENDPOINTS ----------


@app.get("/sectors")
def get_sectors():
    return SECTORS


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    print("=== SCREENER HIT ===", sector)

    # Sector filter
    if sector == "ALL":
        filtered_stocks = STOCKS
    else:
        filtered_stocks = [s for s in STOCKS if s["sector"] == sector]

    if not filtered_stocks:
        return []

    symbols = [s["symbol"] for s in filtered_stocks]

    try:
        response = market_api.get_full_market_quote(
            api_version="2.0",
            symbol=",".join(symbols)
        )
        quotes = response.data
    except Exception as e:
        print("Upstox API error:", str(e))
        return []

    results = []

    for stock in filtered_stocks:
        symbol = stock["symbol"]

        if symbol not in quotes:
            continue

        quote = quotes[symbol]

        ltp = quote.get("last_price")
        ohlc = quote.get("ohlc")

        if not ltp or not ohlc:
            continue

        day_high = ohlc.get("high")
        if not day_high:
            continue

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
