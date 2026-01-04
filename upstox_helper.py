import requests

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIyREFVWDkiLCJqdGkiOiI2OTU5MWI5Y2MzMjIxYTZiYWQxZjEwODciLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzY3NDQ3NDUyLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3Njc0Nzc2MDB9.pCz3Ub5E5E9F7EGkFcgWiDOwtQBFNt9JGus9puBTvc4"


HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def get_5min_candles(instrument_key):
    url = "https://api.upstox.com/v2/historical-candle/intraday"
    params = {
        "instrument_key": instrument_key,
        "interval": "5minute"
    }
    res = requests.get(url, headers=HEADERS, params=params)
    return res.json()["data"]["candles"]
