from live_price_cache import get_price


def is_5min_breakout(df, instrument_key):
    first_high = df.iloc[0]["high"]
    live_price = get_price(instrument_key)
    return live_price and live_price > first_high
