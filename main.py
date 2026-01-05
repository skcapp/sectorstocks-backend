from fastapi import FastAPI, Query
import os
import requests
from datetime import datetime, time
import pytz

from instruments import STOCKS, SECTORS

app = FastAPI()

# -----------------------------
# Upstox config
# -----------------------------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
    "Accept": "application/json"
}

CANDLE_URL = "https://api.upstox.com/v2/historical-candle/intraday"
LTP_URL = "https://api.upstox.com/v2/market-quote/ltp"


# -----------------------------
# Market hours (IST)
# -----------------------------
def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    return time(9, 15) <= now <= time(15, 30)


# -----------------------------
# Fetch 5-minute candles
# -----------------------------
def get_5min_candles(symbol):
    url = f"{CANDLE_URL}/{symbol}/5minute"
    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return []

    return r.json().get("data", {}).get("candles", [])


# -----------------------------
# Fetch LIVE LTP
# -----------------------------
def get_ltp(symbol):
    r = requests.get(
        "https://api.upstox.com/v2/market-quote/ltp",
        headers=HEADERS,
        params={"instruments[]": symbol},
        timeout=10
    )

    if r.status_code != 200:
        return None

    data = r.json().get("data", {})
    return data.get(symbol, {}).get("last_price")

# -----------------------------
# VWAP
# -----------------------------


def calculate_vwap(candles):
    total_pv = 0
    total_vol = 0

    for c in candles:
        high, low, close, vol = c[2], c[3], c[4], c[5]
        tp = (high + low + close) / 3
        total_pv += tp * vol
        total_vol += vol

    if total_vol == 0:
        return 0

    return round(total_pv / total_vol, 2)


# -----------------------------
# RSI (14)
# -----------------------------
def calculate_rsi(candles, period=14):
    if len(candles) < period + 1:
        return 0

    gains, losses = [], []

    for i in range(1, period + 1):
        diff = candles[-i][4] - candles[-i - 1][4]
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


# -----------------------------
# API: sectors
# -----------------------------
@app.get("/sectors")
def sectors():
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

        # Need at least 2 completed candles
        if len(candles) < 2:
            continue

        # 🔴 PREVIOUS COMPLETED 5-MIN HIGH
        prev_high = candles[-2][2]

        # 🔴 LIVE PRICE (LTP)
        ltp = get_ltp(stock["symbol"])
        if not ltp:
            continue

        # 🔥 TRUE BREAKOUT CONDITION
        if ltp <= prev_high:
            continue

        vwap = calculate_vwap(candles)
        rsi = calculate_rsi(candles)

        results.append({
            "symbol": stock["symbol"],
            "name": stock["name"],
            "sector": stock["sector"],
            "ltp": ltp,
            "prev_5min_high": prev_high,
            "breakout": True,
            "vwap": vwap,
            "rsi": rsi
        })

    return results
