import os
import logging
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from upstox_client import Configuration, ApiClient
from upstox_client.api.market_quote_api import MarketQuoteApi

from instruments import STOCKS, SECTORS

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# -----------------------------
# Upstox Client Setup
# -----------------------------
config = Configuration()
config.access_token = os.getenv("UPSTOX_ACCESS_TOKEN")

api_client = ApiClient(config)
quote_api = MarketQuoteApi(api_client)

# -----------------------------
# Helper: Safe Quote Fetch
# -----------------------------


def get_quote_safe(instrument_key: str):
    try:
        response = quote_api.get_full_market_quote(
            symbol=instrument_key,
            api_version="2.0"
        )
        return response
    except Exception as e:
        logging.error(f"Quote failed for {instrument_key}: {e}")
        return None

# -----------------------------
# Screener API
# -----------------------------


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logging.info(f"=== SCREENER HIT === {sector}")

    if sector not in SECTORS:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid sector"}
        )

    filtered = [
        s for s in STOCKS
        if sector == "ALL" or s.get("sector") == sector
    ]

    results = []

    for stock in filtered:
        instrument_key = stock.get("instrument_key")
        if not instrument_key:
            logging.error(f"Missing instrument_key: {stock}")
            continue

        quote = get_quote_safe(instrument_key)
        if not quote:
            continue

        try:
            data = quote["data"][instrument_key]
            results.append({
                "instrument_key": instrument_key,
                "name": stock.get("name"),
                "sector": stock.get("sector"),
                "ltp": data.get("last_price"),
                "open": data.get("ohlc", {}).get("open"),
                "high": data.get("ohlc", {}).get("high"),
                "low": data.get("ohlc", {}).get("low"),
                "volume": data.get("volume")
            })
        except Exception as e:
            logging.error(f"Parse error {instrument_key}: {e}")

    return results

# -----------------------------
# 🔍 DEBUG ENDPOINT (IMPORTANT)
# -----------------------------


@app.get("/debug/instruments")
def debug_instruments():
    """
    Tests every instrument_key and returns:
    ✔ VALID keys
    ❌ INVALID keys with exact error
    """

    report = []

    for stock in STOCKS:
        key = stock.get("instrument_key")

        if not key:
            report.append({
                "name": stock.get("name"),
                "status": "INVALID",
                "reason": "Missing instrument_key"
            })
            continue

        try:
            quote = quote_api.get_full_market_quote(
                symbol=key,
                api_version="2.0"
            )
            report.append({
                "name": stock.get("name"),
                "instrument_key": key,
                "status": "VALID"
            })
        except Exception as e:
            report.append({
                "name": stock.get("name"),
                "instrument_key": key,
                "status": "INVALID",
                "error": str(e)
            })

    return {
        "total": len(STOCKS),
        "valid": len([r for r in report if r["status"] == "VALID"]),
        "invalid": len([r for r in report if r["status"] == "INVALID"]),
        "report": report
    }
