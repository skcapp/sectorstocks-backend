import pandas as pd
import ta


def calculate_indicators(candles):
    df = pd.DataFrame(
        candles,
        columns=["time", "open", "high", "low", "close", "volume"]
    )

    df["vwap"] = ta.volume.VolumeWeightedAveragePrice(
        df["high"], df["low"], df["close"], df["volume"]
    ).vwap()

    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    return df
