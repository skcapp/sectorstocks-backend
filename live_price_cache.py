LIVE_PRICES = {}


def update_price(key, price):
    LIVE_PRICES[key] = price


def get_price(key):
    return LIVE_PRICES.get(key)
