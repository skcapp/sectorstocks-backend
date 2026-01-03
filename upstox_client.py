import requests

ACCESS_TOKEN = "493bb178-314d-476c-a83c-6c65fe530cd9"

HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def get_5min_candles(instrument_key):
    url = "https://api.upstox.com/v2/historical-candle/intraday"
    params = {
        "instrument_key": instrument_key,
        "interval": "5minute"
    }
    res = requests.get(url, headers=HEADERS, params=params)
    return res.json()["data"]["candles"]
