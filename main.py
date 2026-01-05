from fastapi import FastAPI, Query
import requests
import os
from datetime import datetime, time, timedelta
from instruments import STOCKS, SECTORS


app = FastAPI()

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
    "Accept": "application/json"
}

# ================= MARKET TIME CHECK =================


def is_market_open():
    # Convert UTC → IST
    ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
    current_time = ist_now.time()

    market_open = time(9, 15)
    market_close = time(15, 30)

    return market_open <= current_time <= market_close


# ================= SECTORS =================
@app.get("/sectors")
def get_sectors():
    return SECTORS


# ================= BATCH LTP =================
def get_all_ltps(symbols):
    response = requests.get(
        "https://api.upstox.com/v2/market-quote/ltp",
        headers=HEADERS,
        params=[("instruments[]", s) for s in symbols],
        timeout=10
    )

    if response.status_code != 200:
        return {}

    return response.json().get("data", {})


# ================= PREVIOUS 5-MIN HIGH =================
def get_prev_5min_high(symbol):
    response = requests.get(
        "https://api.upstox.com/v2/historical-candle/intraday/5minute",
        headers=HEADERS,
        params={"instrument_key": symbol},
        timeout=10
    )

    if response.status_code != 200:
        return None

    candles = response.json().get("data", {}).get("candles", [])

    # Need at least 2 completed candles
    if len(candles) < 2:
        return None

    # 🔥 FIX: use MAX HIGH of completed candles (exclude current forming candle)
    prev_high = max(c[2] for c in candles[:-1])
    return prev_high


# ================= SCREENER =================
@app.get("/screener")
def screener(sector: str = Query("ALL")):
    if not is_market_open():
        return [{"message": "Market closed"}]

    results = []

    # Filter stocks by sector
    filtered_stocks = [
        s for s in STOCKS
        if sector == "ALL" or s["sector"] == sector
    ]

    if not filtered_stocks:
        return []

    symbols = [s["symbol"] for s in filtered_stocks]

    # 🔥 Batch LTP call
    ltp_map = get_all_ltps(symbols)

    for stock in filtered_stocks:
        symbol = stock["symbol"]

        ltp_data = ltp_map.get(symbol)
        if not ltp_data:
            continue

        ltp = ltp_data.get("last_price")
        if not ltp:
            continue

        prev_high = get_prev_5min_high(symbol)
        if not prev_high:
            continue

        # 🔥 Breakout condition
        # if ltp > prev_high:
        if ltp > prev_high * 0.995:
            results.append({
                "symbol": symbol,
                "name": stock["name"],
                "sector": stock["sector"],
                "ltp": round(ltp, 2),
                "prev_5min_high": round(prev_high, 2),
                "breakout": True
            })

    return results
