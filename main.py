from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from upstox_client import Configuration, ApiClient
from upstox_client.api.market_quote_api import MarketQuoteApi
from upstox_client.api.history_api import HistoryApi
from datetime import datetime, time
import pandas as pd

from backend.instruments import SECTORS


# =============================
# CONFIG
# =============================
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIyREFVWDkiLCJqdGkiOiI2OTU5MWI5Y2MzMjIxYTZiYWQxZjEwODciLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzY3NDQ3NDUyLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3Njc0Nzc2MDB9.pCz3Ub5E5E9F7EGkFcgWiDOwtQBFNt9JGus9puBTvc4"

config = Configuration()
config.access_token = ACCESS_TOKEN

api_client = ApiClient(config)
quote_api = MarketQuoteApi(api_client)
history_api = HistoryApi(api_client)

# =============================
# FASTAPI
# =============================
app = FastAPI(title="Sector Stock Screener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# DATA
# =============================


@app.get("/sectors")
def get_sectors():
    return SECTORS

# SECTORS = ["ALL", "BANKING", "IT", "PHARMA", "AUTO"]

# STOCKS = [
 #   {"symbol": "NSE_EQ|HDFCBANK", "name": "HDFCBANK", "sector": "BANKING"},
  #  {"symbol": "NSE_EQ|ICICIBANK", "name": "ICICIBANK", "sector": "BANKING"},
   # {"symbol": "NSE_EQ|INFY", "name": "INFY", "sector": "IT"},
   # {"symbol": "NSE_EQ|TCS", "name": "TCS", "sector": "IT"},
# ]

# =============================
# HELPERS
# =============================


def market_open():
    now = datetime.now().time()
    return time(9, 15) <= now <= time(15, 30)

# =============================
# ROUTES
# =============================


@app.get("/")
def health():
    return {"status": "running"}


@app.get("/sectors")
def sectors():
    return SECTORS


@app.get("/screener")
def screener():
    if not market_open():
        return []

    results = []

    for s in STOCKS:
        try:
            candles = history_api.get_historical_candle_data(
                instrument_key=s["symbol"],
                interval="5minute",
                to_date=datetime.now().strftime("%Y-%m-%d"),
                from_date=datetime.now().strftime("%Y-%m-%d"),
            )

            data = candles.data.candles
            if not data or len(data) < 15:
                continue

            df = pd.DataFrame(
                data,
                columns=["time", "open", "high", "low", "close", "volume"]
            )

            first_5_high = df.iloc[0]["high"]

            df["tp"] = (df["high"] + df["low"] + df["close"]) / 3
            vwap = (df["tp"] * df["volume"]).sum() / df["volume"].sum()

            delta = df["close"].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)

            avg_gain = gain.rolling(14).mean().iloc[-1]
            avg_loss = loss.rolling(14).mean().iloc[-1]

            rsi = 100 if avg_loss == 0 else 100 - \
                (100 / (1 + avg_gain / avg_loss))

            ltp = df.iloc[-1]["close"]

            if ltp > first_5_high and ltp > vwap and rsi > 60:
                results.append({
                    "symbol": s["name"],
                    "sector": s["sector"],
                    "ltp": round(ltp, 2),
                    "first_5min_high": round(first_5_high, 2),
                    "vwap": round(vwap, 2),
                    "rsi": round(rsi, 2),
                    "breakout": True
                })

        except Exception as e:
            print(f"{s['name']} error → {e}")

    return results
