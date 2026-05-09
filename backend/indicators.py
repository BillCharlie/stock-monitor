import pandas as pd
import numpy as np


def calculate_ma(df: pd.DataFrame, periods: list[int] = [5, 10, 20, 60, 120, 240]) -> dict:
    result = {}
    for p in periods:
        key = f"MA{p}"
        if len(df) >= p:
            result[key] = df["Close"].rolling(window=p).mean()
        else:
            result[key] = pd.Series([np.nan] * len(df), index=df.index)
    return result


def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> dict:
    if len(df) < period:
        empty = pd.Series([np.nan] * len(df), index=df.index)
        return {"BB_upper": empty, "BB_middle": empty, "BB_lower": empty}
    ma = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    return {
        "BB_upper": ma + num_std * std,
        "BB_middle": ma,
        "BB_lower": ma - num_std * std,
    }


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if len(df) < period + 1:
        return pd.Series([np.nan] * len(df), index=df.index)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_kd(df: pd.DataFrame, period: int = 9) -> dict:
    """Taiwan-standard KD (Slow Stochastic): K = 2/3 * prev_K + 1/3 * RSV, D = 2/3 * prev_D + 1/3 * K"""
    n = len(df)
    if n < period:
        empty = pd.Series([np.nan] * n, index=df.index)
        return {"K": empty, "D": empty}

    low_min = df["Low"].rolling(window=period, min_periods=period).min()
    high_max = df["High"].rolling(window=period, min_periods=period).max()
    h_l = (high_max - low_min).replace(0, np.nan)
    rsv = ((df["Close"] - low_min) / h_l * 100).fillna(50)

    k_vals = np.full(n, np.nan)
    d_vals = np.full(n, np.nan)

    # Find first valid RSV index
    first_valid = rsv.first_valid_index()
    if first_valid is None:
        return {"K": pd.Series(k_vals, index=df.index), "D": pd.Series(d_vals, index=df.index)}

    start_idx = df.index.get_loc(first_valid)
    k_vals[start_idx] = 50.0
    d_vals[start_idx] = 50.0

    rsv_arr = rsv.values
    for i in range(start_idx + 1, n):
        if np.isnan(rsv_arr[i]):
            k_vals[i] = k_vals[i - 1]
            d_vals[i] = d_vals[i - 1]
        else:
            k_vals[i] = k_vals[i - 1] * 2 / 3 + rsv_arr[i] * 1 / 3
            d_vals[i] = d_vals[i - 1] * 2 / 3 + k_vals[i] * 1 / 3

    return {
        "K": pd.Series(k_vals, index=df.index),
        "D": pd.Series(d_vals, index=df.index),
    }


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume for trend confirmation"""
    direction = np.sign(df["Close"].diff().fillna(0))
    obv = (direction * df["Volume"]).cumsum()
    return obv


def series_to_list(s: pd.Series, dates: pd.Index) -> list:
    """Convert pandas Series to [{time, value}] list, skipping NaN"""
    result = []
    for date, val in zip(dates, s):
        if pd.notna(val):
            result.append({"time": date.strftime("%Y-%m-%d"), "value": round(float(val), 4)})
    return result
