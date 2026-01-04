from fastapi import FastAPI, Query
from typing import List, Dict
from instruments import STOCKS, SECTORS
import random
from datetime import datetime, time

app = FastAPI(
    title="Sector Stocks Live Screener",
    version="1.1.0"
)

# Dictionary to store last 5-minute high for breakout
last_5min_high = {}

# -----------------------------
# Root endpoint
# -----------------------------


@app.get("/")
def root():
    return {"status": "ok", "message": "Sector Stocks Backend Running"}

# -----------------------------
# Get sectors
# -----------------------------


@app.get("/sectors")
def get_sectors() -> List[str]:
    return SECTORS

# -----------------------------
# Helper: Check breakout & compute VWAP & RSI (placeholder logic)
# -----------------------------


def update_stock(stock):
    symbol = stock["symbol"]

    # Simulate current price for demo
    price = round(random.uniform(100, 500), 2)
    stock["current_price"] = price

    # 5-min breakout logic
    prev_high = last_5min_high.get(symbol, 0)
    if price > prev_high:
        stock["breakout"] = True
        last_5min_high[symbol] = price
    else:
        stock["breakout"] = False

    # VWAP & RSI placeholders (replace with real calculation from candles/live feed)
    stock["vwap"] = round(price * random.uniform(0.99, 1.01), 2)
    stock["rsi"] = round(random.uniform(30, 70), 2)

    return stock

# -----------------------------
# Screener endpoint
# -----------------------------


@app.get("/screener")
def screener(sector: str = Query("ALL", description="Sector filter")) -> List[Dict]:
    try:
        sector = sector.strip().upper()

        # Filter stocks by sector
        filtered = [
            s.copy() for s in STOCKS
            if sector == "ALL" or s.get("sector", "").upper() == sector
        ]

        # Update live fields: price, breakout, VWAP, RSI
        result = [update_stock(stock) for stock in filtered]

        return result

    except Exception as e:
        return [{"error": "Screener failed", "details": str(e)}]
