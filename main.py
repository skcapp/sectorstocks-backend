from fastapi import FastAPI, Query
import os
import requests
from datetime import datetime, time
import pytz
from instruments import STOCKS, SECTORS

app = FastAPI()

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
    "Accept": "application/json"
}

UPSTOX_CANDLE_URL = "https://api.upstox.com/v2/historical-candle/intraday"

# -----------------------------
# Utility: Market hours check
# -----------------------------


def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    return time(9, 15) <= now <= time(15, 30)


# -----------------------------
# Fetch 5-min candles
# -----------------------------
def get_5min_candles(symbol):
    url = f"{UPSTOX_CANDLE_URL}/{symbol}/5minute"
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return []

    data = r.json().get("data", {})
    return data.get("candles", [])


# -----------------------------
# VWAP calculation
# -----------------------------
def calculate_vwap(candles):
    total_pv = 0
    total_vol = 0
    for c in candles:
        high = c[2]
        low = c[3]
        close = c[4]
        volume = c[5]
        typical_price = (high + low + close) / 3
        total_pv += typical_price * volume
        total_vol += volume

    if total_vol == 0:
        return 0
    return round(total_pv / total_vol, 2)


# -----------------------------
# RSI (simple 14-period)
# -----------------------------
def calculate_rsi(candles, period=14):
    if len(candles) < period + 1:
        return 0

    gains = []
    losses = []

    for i in range(1, period + 1):
        change = candles[-i][4] - candles[-i - 1][4]
        if change >= 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


# -----------------------------
# API: sectors
# -----------------------------
@app.get("/sectors")
def get_sectors():
    return SECTORS


# -----------------------------
# API: screener
# -----------------------------
@app.get("/screener")
def screener(sector: str = Query("ALL")):

    if not is_market_open():
        return [{"message": "Market closed"}]

    results = []

    for stock in STOCKS:

        # Sector filter
        if sector != "ALL" and stock["sector"] != sector:
            continue

        candles = get_5min_candles(stock["symbol"])

        # Need at least 2 candles
        if len(candles) < 2:
            continue

        # --- TRUE 5-MIN BREAKOUT LOGIC ---
        prev_candle = candles[-2]
        curr_candle = candles[-1]

        prev_high = prev_candle[2]
        curr_high = curr_candle[2]

        # Breakout condition
        if curr_high <= prev_high:
            continue

        # Indicators
        vwap = calculate_vwap(candles)
        rsi = calculate_rsi(candles)

        results.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "sector": stock["sector"],
            "price": curr_candle[4],
            "breakout": True,
            "prev_high": prev_high,
            "current_high": curr_high,
            "vwap": vwap,
            "rsi": rsi
        })

    return results
