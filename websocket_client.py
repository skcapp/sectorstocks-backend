import websocket
import json
from live_price_cache import update_price

ACCESS_TOKEN = "493bb178-314d-476c-a83c-6c65fe530cd9"


def on_message(ws, msg):
    data = json.loads(msg)
    for tick in data.get("data", []):
        update_price(tick["instrument_key"], tick["last_price"])


def on_open(ws):
    sub = {
        "guid": "live",
        "method": "sub",
        "data": {
            "mode": "ltp",
            "instrumentKeys": [
                "NSE_EQ|HDFCBANK",
                "NSE_EQ|ICICIBANK",
                "NSE_EQ|TCS",
                "NSE_EQ|INFY"
            ]
        }
    }
    ws.send(json.dumps(sub))


def start_socket():
    ws = websocket.WebSocketApp(
        "wss://api.upstox.com/v3/feed/market-data-feed",
        header={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        on_open=on_open,
        on_message=on_message
    )
    ws.run_forever()


start_socket()
