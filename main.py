from fastapi import FastAPI, Query
from typing import List, Dict
from instruments import STOCKS, SECTORS
from indicators import calculate_vwap, calculate_rsi
import requests
import os
from datetime import datetime, time
import pytz

# =====================
# CONFIG
# =====================
BASE_URL = "https://api.upstox.com/v2"
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
IST = pytz.timezone("Asia/Kolkata")

app = FastAPI(title="Professional Intraday Screener", version="3.0")

# =====================
# HELPERS
# =====================


def market_open():
    now = datetime.now(IST).time()
    return time(9, 15) <= now <= time(15, 30)


def headers():
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json"
    }


def get_ltp(symbol):
    url = f"{BASE_URL}/market-quote/ltp"
    r = requests.get(url, headers=headers(), params={
                     "symbol": symbol}, timeout=5)
    return r.json()["data"][symbol]["last_price"]


def get_5min_candles(symbol, count=20):
    url = f"{BASE_URL}/historical-candle/intraday/{symbol}/5minute"
    r = requests.get(url, headers=headers(), timeout=5)
    candles = r.json()["data"]["candles"]
    return candles[-count:]

# =====================
# ROUTES
# =====================


@app.get("/")
def root():
    return {"status": "ok", "market_open": market_open()}


@app.get("/sectors")
def sectors():
    return SECTORS


@app.get("/screener")
def screener(sector: str = Query("ALL")) -> List[Dict]:

    if not market_open():
        return [{"message": "Market closed"}]

    sector = sector.upper()
    filtered = [
        s for s in STOCKS
        if sector == "ALL" or s["sector"].upper() == sector
    ]

    output = []

    for stock in filtered:
        symbol = stock["symbol"]

        try:
            candles = get_5min_candles(symbol)
            ltp = get_ltp(symbol)

            prev_5min_high = candles[-2][2]  # previous candle HIGH
            breakout = ltp > prev_5min_high

            vwap = calculate_vwap(candles)
            rsi = calculate_rsi(candles)

            output.append({
                "symbol": symbol,
                "name": stock["name"],
                "sector": stock["sector"],
                "price": ltp,
                "prev_5min_high": prev_5min_high,
                "breakout": breakout,
                "vwap": vwap,
                "rsi": rsi
            })

        except Exception:
            continue

    return output
