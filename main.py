from fastapi import FastAPI, Query
from kiteconnect import KiteConnect
from datetime import datetime, timedelta
import pandas as pd
import os
import logging

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI()

# --------------------------------------------------
# Kite Setup
# --------------------------------------------------
kite = KiteConnect(api_key=os.getenv("KITE_API_KEY"))
kite.set_access_token(os.getenv("KITE_ACCESS_TOKEN"))

# --------------------------------------------------
# Sector → Stocks Mapping
# (instrument tokens MUST be correct)
# --------------------------------------------------
SECTORS = {
    "IT": {
        "INFY": 408065,
        "TCS": 2953217,
        "WIPRO": 969473,
        "TECHM": 3465729
    },
    "BANK": {
        "HDFCBANK": 341249,
        "ICICIBANK": 1270529,
        "SBIN": 779521
    }
}

# --------------------------------------------------
# Utils
# --------------------------------------------------


def market_open():
    now = datetime.now()
    return now.weekday() < 5 and now.hour >= 9 and (now.hour < 15 or (now.hour == 15 and now.minute <= 30))


def get_prev_5min_high(token):
    """Get previous completed 5-min candle high"""
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(minutes=30)

        candles = kite.historical_data(
            token,
            from_date,
            to_date,
            interval="5minute"
        )

        if len(candles) < 2:
            return None

        prev_candle = candles[-2]
        return prev_candle["high"]

    except Exception as e:
        logger.error(f"Candle error {token}: {e}")
        return None


# --------------------------------------------------
# Screener API
# --------------------------------------------------
@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logger.info(f"=== SCREENER HIT === {sector}")

    if not market_open():
        return [{"message": "Market closed"}]

    selected = {}

    if sector == "ALL":
        for sec in SECTORS.values():
            selected.update(sec)
    else:
        selected = SECTORS.get(sector.upper(), {})

    if not selected:
        return []

    tokens = list(selected.values())

    # ------------------ LTP ------------------
    try:
        ltp_data = kite.ltp(tokens)
    except Exception as e:
        logger.error(f"LTP error: {e}")
        return [{"error": "Market data permission missing"}]

    results = []
    sector_strength = {}

    for symbol, token in selected.items():
        ltp = ltp_data.get(str(token), {}).get("last_price")
        if not ltp:
            continue

        prev_high = get_prev_5min_high(token)
        if not prev_high:
            continue

        # ------------------ Breakout Logic ------------------
        if ltp > prev_high:
            momentum = round(((ltp - prev_high) / prev_high) * 100, 2)

            sec = next(s for s, v in SECTORS.items() if symbol in v)
            sector_strength.setdefault(sec, 0)
            sector_strength[sec] += momentum

            results.append({
                "symbol": symbol,
                "sector": sec,
                "ltp": ltp,
                "prev_5min_high": prev_high,
                "breakout_pct": momentum
            })

    # ------------------ Sector Ranking ------------------
    ranked_sectors = sorted(
        sector_strength.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return {
        "breakouts": results,
        "sector_ranking": ranked_sectors
    }


# --------------------------------------------------
# Health
# --------------------------------------------------
@app.get("/")
def root():
    return {"status": "Sector Screener Live"}
