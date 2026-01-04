import numpy as np


def calculate_vwap(candles):
    # candles: [timestamp, open, high, low, close, volume]
    prices = np.array([c[4] for c in candles])
    volumes = np.array([c[5] for c in candles])
    return round((prices * volumes).sum() / volumes.sum(), 2)


def calculate_rsi(candles, period=14):
    closes = np.array([c[4] for c in candles])
    deltas = np.diff(closes)

    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)
