from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, time
import pytz
import os
import requests
import logging

# ================= CONFIG =================

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

UPSTOX_QUOTE_URL = "https://api.upstox.com/v2/market-quote/quotes"

IST = pytz.timezone("Asia/Kolkata")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# ================= APP =================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DATA =================

INSTRUMENTS = [
    #  {"name": "RELIANCE", "instrument_key": "NSE_EQ|INE002A01018", "sector": "ALL"},
    #  {"name": "TCS", "instrument_key": "NSE_EQ|INE467B01029", "sector": "ALL"},
    #  {"name": "INFY", "instrument_key": "NSE_EQ|INE009A01021", "sector": "ALL"},
    #   {"name": "ICICIBANK", "instrument_key": "NSE_EQ|INE090A01021", "sector": "ALL"},
    # {"name": "HDFCBANK", "instrument_key": "NSE_EQ|INE040A01034", "sector": "ALL"},
    # keep adding…
    {"name": "HDFCBANK", "instrument_key": "NSE_EQ|INE040A01034", "sector": "BANKING"},
    {"name": "ICICIBANK", "instrument_key":  "NSE_EQ|INE090A01021", "sector": "BANKING"},
    {"name": "INDUSINDBK", "instrument_key":  "NSE_EQ|INE095A01012", "sector": "BANKING"},
    {"name": "BANKBARODA", "instrument_key": "NSE_EQ|INE028A01039", "sector": "BANKING"},

    {"name": "INFY", 		 "instrument_key": "NSE_EQ|INE009A01021", 	"sector": "IT"},
    {"name": "TCS",	 	 	 "instrument_key": "NSE_EQ|INE467B01029", 		"sector": "IT"},
    {"name": "TECHM", 		 "instrument_key": "NSE_EQ|INE669C01036", 	"sector": "IT"},
    {"name": "HCLTECH", 	 "instrument_key": "NSE_EQ|INE860A01027", 		"sector": "IT"},
    {"name": "SUNPHARMA",	 "instrument_key": "NSE_EQ|INE044A01036", "sector": "PHARMA"},
    {"name": "DRREDDY", 	 "instrument_key": "NSE_EQ|INE089A01031", 		"sector": "PHARMA"},
    {"name": "CIPLA", 		 "instrument_key": "NSE_EQ|INE059A01026", 	"sector": "PHARMA"},
    {"name": "ZYDUSLIFE",	 "instrument_key": "NSE_EQ|INE010B01027",		"sector": "PHARMA"},
    {"name": "MARUTI",		 "instrument_key": "NSE_EQ|INE585B01010",  	"sector": "AUTO"},
    {"name": "M&M", 		 "instrument_key": "NSE_EQ|INE101A01026", 	"sector": "AUTO"},
    {"name": "HEROMOTOCO",  "instrument_key": "NSE_EQ|INE158A01026", 	"sector": "AUTO"},
    {"name": "BHEL",		 "instrument_key": "NSE_EQ|INE257A01026",  	"sector": "ENERGY"},
    {"name": "HINDPETRO", 	 "instrument_key": "NSE_EQ|INE094A01015", 		"sector": "ENERGY"},
    {"name": "SIEMENS", 	 "instrument_key": "NSE_EQ|INE003A01024", 		"sector": "ENERGY"},
    {"name": "RELIANCE", 	 "instrument_key": "NSE_EQ|INE002A01018",  		"sector": "ENERGY"},
    {"name": "ADANIENT", 	 "instrument_key": "NSE_EQ|INE423A01024",  		"sector": "METALS"},
    {"name": "HINDALCO", 	 "instrument_key": "NSE_EQ|INE038A01020",  		"sector": "METALS"},
    {"name": "HINDCOPPER",  "instrument_key": "NSE_EQ|INE531E01026",  	"sector": "METALS"},
    {"name": "NATIONALUM",	 "instrument_key": "NSE_EQ|INE139A01034",		"sector": "METALS"},
    {"name": "JSWSTEEL", 	 "instrument_key": "NSE_EQ|INE019A01038",  		"sector": "METALS"},
    {"name": "DABUR", 		 "instrument_key": "NSE_EQ|INE016A01026", "sector": "FMCG"},
    {"name": "GODREJCP", 	 "instrument_key": "NSE_EQ|INE102D01028",  		"sector": "FMCG"},
    {"name": "TATACONSUM",  "instrument_key": "NSE_EQ|INE192A01025", 	"sector": "FMCG"},
    {"name": "MARICO", 	 "instrument_key": "NSE_EQ|INE196A01026", "sector": "FMCG"},
    {"name": "AEGISLOG", 	 "instrument_key": "NSE_EQ|INE208C01025",  		"sector": "OILGAS"},
    {"name": "BPCL", 		 "instrument_key": "NSE_EQ|INE029A01011", 	"sector": "OILGAS"},
    {"name": "GUJGASLTD", 	 "instrument_key": "NSE_EQ|INE844O01030", 		"sector": "OILGAS"},
    {"name": "PETRONET", 	 "instrument_key": "NSE_EQ|INE347G01014",  		"sector": "OILGAS"},
    {"name": "LT", 	 "instrument_key": "NSE_EQ|INE018A01030", "sector": "INFRA"},
    {"name": "RVNL", 		 "instrument_key": "NSE_EQ|INE415G01027", 	"sector": "INFRA"},
    {"name": "IRCON", 		 "instrument_key": "NSE_EQ|INE962Y01021", 	"sector": "INFRA"},

]

# ================= HELPERS =================


def is_market_open():
    now = datetime.now(IST).time()
    return time(9, 15) <= now <= time(15, 30)


def fetch_quotes(instrument_keys):
    """
    Calls Upstox REST API directly
    """
    headers = {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Accept": "application/json",
    }

    params = {
        "instrument_key": ",".join(instrument_keys)
    }

    try:
        r = requests.get(
            UPSTOX_QUOTE_URL,
            headers=headers,
            params=params,
            timeout=10
        )
        r.raise_for_status()
        return r.json().get("data", {})
    except Exception as e:
        logger.error(f"Quote fetch failed: {e}")
        return {}

# ================= ROUTES =================


@app.get("/debug/instruments")
def debug_instruments():
    return {
        "total": len(INSTRUMENTS),
        "instruments": INSTRUMENTS
    }


@app.get("/screener")
def screener(sector: str = Query("ALL")):
    logger.info(f"=== SCREENER HIT === {sector}")

    if not is_market_open():
        return [{"message": "Market closed"}]

    filtered = [
        i for i in INSTRUMENTS
        if sector == "ALL" or i["sector"] == sector
    ]

    if not filtered:
        return []

    instrument_keys = [i["instrument_key"] for i in filtered]

    logger.info(f"Requesting quotes for {len(instrument_keys)} instruments")

    quotes = fetch_quotes(instrument_keys)

    logger.info(f"Quotes received: {len(quotes)}")

    results = []

    for stock in filtered:
        key = stock["instrument_key"]
        q = quotes.get(key)

        if not q:
            continue

        ltp = q.get("last_price")
        ohlc = q.get("ohlc", {})
        open_price = ohlc.get("open")

        if ltp is None or open_price is None:
            continue

        results.append({
            "symbol": stock["name"],
            "open": open_price,
            "ltp": ltp
        })

    return results
