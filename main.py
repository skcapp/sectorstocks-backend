from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel
from instruments import SECTOR_STOCKS
import random  # Simulated price for demo
import datetime

app = FastAPI()

# Allow Flutter mobile requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model


class StockOut(BaseModel):
    symbol: str
    sector: str
    price: float
    vwap: float
    rsi: float
    breakout: bool

# Demo: simulate first 5-min high + VWAP+RSI


def simulate_stock(symbol, sector):
    price = round(random.uniform(100, 5000), 2)
    vwap = price * random.uniform(0.98, 1.02)
    rsi = random.uniform(20, 80)
    breakout = price > (price * 0.995) and 50 < rsi < 70
    return {
        "symbol": symbol,
        "sector": sector,
        "price": price,
        "vwap": round(vwap, 2),
        "rsi": round(rsi, 2),
        "breakout": breakout
    }


@app.get("/sectors", response_model=List[str])
def get_sectors():
    return ["ALL"] + list(SECTOR_STOCKS.keys())


@app.get("/screener", response_model=List[StockOut])
def get_screener():
    results = []
    for sector, stocks in SECTOR_STOCKS.items():
        for sym, name in stocks:
            results.append(simulate_stock(name, sector))
    return results


@app.get("/")
def root():
    return {"status": "running"}
