import os
import logging
from fastapi import FastAPI, Query
from kiteconnect import KiteConnect
from datetime import datetime, timedelta
from typing import List

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# ---------------- APP ----------------
app = FastAPI(title="Sector Breakout Screener")

# ---------------- KITE INIT ----------------
KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")

if not KITE_API_KEY or not KITE_ACCESS_TOKEN:
    raise RuntimeError("KITE_API_KEY or KITE_ACCESS_TOKEN missing")

kite = KiteConnect(api_key=KITE_API_KEY)
kite.set_access_token(KITE_ACCESS_TOKEN)

# ---------------- SECTORS ----------------
SECTORS = {
    "IT": ["NSE:INFY", "NSE:TCS", "NSE:TECHM", "NSE:HCLTECH", "NSE:WIPRO"],
    "BANK": ["NSE:HDFCBANK", "NSE:ICICIBANK", "NSE:AXISBANK", "NSE:SBIN"],
    "AUTO": ["NSE:MARUTI", "NSE:TATAMOTORS", "NSE:M&M", "NSE:HEROMOTOCO"],
}

# ---------------- UTIL ----------------


def get_symbols(sector: str) -> List[str]:
    if sector == "ALL":
        symbols = []
        for s in SECTORS.values():
            symbols.extend(s)
        return list(set(symbols))
    return SECTORS.get(sector, [])


def get_previous_5min_candle(symbol: str):
    try:
        to_dt = datetime.now()
        from_dt = to_dt - timedelta(minutes=15)

        instrument_token = kite.ltp([symbol])[symbol]["instrument_token"]

        candles = kite.historical_data(
            instrument_token,
            from_dt,
            to_dt,
            interval="5minute"
        )

        if len(candles) < 2:
            return None

        return candles[-2]  # previous completed candle

    except Exception as e:
        logger.error(f"Candle fetch error {symbol}: {e}")
        return None

# ---------------- API ----------------


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    sector = sector.upper()
    logger.info(f"=== SCREENER HIT === {sector}")

    symbols = get_symbols(sector)
    if not symbols:
        return []

    logger.info(f"Requesting quotes for {len(symbols)} instruments")

    try:
        quotes = kite.ltp(symbols)
    except Exception as e:
        logger.error(f"LTP error: {e}")
        return []

    results = []

    for symbol in symbols:
        try:
            quote = quotes.get(symbol)
            if not quote:
                continue

            ltp = quote["last_price"]
            volume = quote.get("volume", 0)

            prev_candle = get_previous_5min_candle(symbol)
            if not prev_candle:
                continue

            prev_high = prev_candle["high"]
            prev_volume = prev_candle["volume"]

            # ---- BREAKOUT + VOLUME CONDITION ----
            if ltp > prev_high and volume > prev_volume:
                results.append({
                    "symbol": symbol,
                    "ltp": round(ltp, 2),
                    "breakout_level": prev_high,
                    "volume": volume,
                    "prev_volume": prev_volume,
                    "sector": sector
                })

        except Exception as e:
            logger.error(f"Processing error {symbol}: {e}")

    return results

# ---------------- HEALTH ----------------


@app.get("/")
def health():
    return {"status": "running"}
