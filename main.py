import os
import logging
from datetime import datetime, timedelta
import pytz

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from upstox_client import Configuration, ApiClient
from upstox_client.api.market_quote_api import MarketQuoteApi
from upstox_client.api.history_api import HistoryApi

from instruments import STOCKS, SECTORS

# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# --------------------------------------------------
# FastAPI app
# --------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Upstox config
# --------------------------------------------------
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
API_VERSION = "2.0"

config = Configuration()
config.access_token = UPSTOX_ACCESS_TOKEN
api_client = ApiClient(config)

market_api = MarketQuoteApi(api_client)
history_api = HistoryApi(api_client)

# --------------------------------------------------
# Helpers
# --------------------------------------------------
IST = pytz.timezone("Asia/Kolkata")


def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:  # Sat/Sun
        return False

    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def previous_5min_window():
    now = datetime.now(IST)
    end = now.replace(second=0, microsecond=0)
    start = end - timedelta(minutes=5)
    return start, end


# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.get("/sectors")
def get_sectors():
    return SECTORS


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logger.info(f"=== SCREENER HIT === {sector}")

    if not is_market_open():
        return [{"message": "Market closed"}]

    # -----------------------------
    # Filter stocks by sector
    # -----------------------------
    if sector == "ALL":
        filtered = STOCKS
    else:
        filtered = [s for s in STOCKS if s["sector"] == sector]

    if not filtered:
        return []

    instrument_keys = [s["symbol"] for s in filtered]

    # -----------------------------
    # Fetch LTP (BATCH – FIXED)
    # -----------------------------
    try:
        quote_response = market_api.get_full_market_quote(
            symbol=instrument_keys,   # ✅ MUST BE LIST
            api_version=API_VERSION
        )
        quotes = quote_response.data or {}
        logger.info(f"Quote keys returned: {list(quotes.keys())}")
    except Exception as e:
        logger.error(f"Upstox quote error: {e}")
        return []

    # -----------------------------
    # Time window
    # -----------------------------
    start, end = previous_5min_window()

    results = []

    # -----------------------------
    # Per-stock logic
    # -----------------------------
    for stock in filtered:
        symbol = stock["symbol"]

        if symbol not in quotes:
            logger.info(f"Skipping {symbol} – no quote")
            continue

        try:
            ltp = quotes[symbol]["last_price"]

            candle_resp = history_api.get_historical_candle_data(
                instrument_key=symbol,
                interval="5minute",
                from_date=start.strftime("%Y-%m-%d %H:%M"),
                to_date=end.strftime("%Y-%m-%d %H:%M"),
                api_version=API_VERSION
            )

            candles = candle_resp.data or []
            if not candles:
                continue

            prev_high = max(c[2] for c in candles)  # HIGH column

            logger.info(
                f"{symbol} | LTP={ltp} | Prev5High={prev_high}"
            )

            # 🔥 BREAKOUT LOGIC (slightly relaxed)
            if ltp > prev_high * 0.995:
                results.append({
                    "symbol": symbol,
                    "name": stock["name"],
                    "sector": stock["sector"],
                    "ltp": round(ltp, 2),
                    "prev_5min_high": round(prev_high, 2),
                    "breakout": True
                })

        except Exception as e:
            logger.error(f"{symbol} processing error: {e}")

    return results


# --------------------------------------------------
# Debug helper
# --------------------------------------------------
@app.get("/debug/instruments")
def debug_instruments():
    return {
        "total": len(STOCKS),
        "symbols": [s["symbol"] for s in STOCKS]
    }
