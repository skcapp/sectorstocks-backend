from fastapi import FastAPI, Query
from typing import List, Dict
from instruments import SECTORS, STOCKS

app = FastAPI(
    title="Sector Stocks API",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Sector Stocks Backend Running"
    }


# -----------------------------
# GET SECTORS
# -----------------------------
@app.get("/sectors")
def get_sectors() -> List[str]:
    return SECTORS


# -----------------------------
# GET STOCK SCREENER
# -----------------------------
@app.get("/screener")
def get_screener(
    sector: str = Query("ALL", description="Sector name")
) -> List[Dict]:

    try:
        # Normalize input
        sector = sector.strip().upper()

        # Return all stocks
        if sector == "ALL":
            return STOCKS

        # Filter by sector
        filtered_stocks = [
            stock for stock in STOCKS
            if stock.get("sector", "").upper() == sector
        ]

        return filtered_stocks

    except Exception as e:
        # Never crash Railway
        return [{
            "error": "Screener failed",
            "details": str(e)
        }]
