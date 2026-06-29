"""
Position-management strategy (倉位管理策略).

Implements the technical-analysis position-management design doc as a *stateless
snapshot*: given a holding's aggregate entry (weighted-average buy price) and the
latest market data, classify the market state and recommend an action
(HOLD / ADD / SELL_PARTIAL / EXIT_ALL) with the key ATR-based risk levels.

This is advisory only — it does NOT track per-trade triggered flags or position
size over time. All numbers are computed from the stock's *aggregate* figures
(average price), never per individual purchase lot.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stock_data import get_ohlcv
from indicators import calculate_ma, calculate_bollinger_bands, calculate_rsi

# ── Tunable parameters (from the design doc §22) ──────────────────────────────
ATR_PERIOD = 14
ATR_STOP_MULTIPLIER = 2.5
MIN_BASE_STOP = 0.08
MAX_BASE_STOP = 0.18
LOSS_LEVEL_1_MULT = 0.6
LOSS_LEVEL_2_MULT = 1.0
LOSS_LEVEL_3_MULT = 1.5
VOLUME_MA_PERIOD = 20

STATE_LABELS = {
    "HEALTHY_TREND": "健康趨勢",
    "OVERHEATED": "過熱",
    "CLIMAX_TOP": "高潮頂",
    "WEAKENING": "轉弱",
    "NEUTRAL": "中性",
}


def _last(s) -> float | None:
    if s is None or len(s) == 0:
        return None
    v = s.iloc[-1]
    return float(v) if pd.notna(v) else None


def _atr_series(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    high, low, prev_close = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def _classify_state(ind: dict) -> str:
    """Replicates classify_market_state from the design doc (§16)."""
    close = ind["close"]
    ma5, ma10, ma20, ma60 = ind["ma5"], ind["ma10"], ind["ma20"], ind["ma60"]
    rsi = ind["rsi"]
    vr = ind["volume_ratio"]
    boll_upper, boll_mid = ind["boll_upper"], ind["boll_mid"]
    upper_shadow_ratio = ind["upper_shadow_ratio"]
    daily_return = ind["daily_return"]
    high = ind["high"]
    dd = ind["drawdown_from_peak"]

    # Guard: any missing core indicator → NEUTRAL
    if None in (ma5, ma10, ma20, ma60, rsi, vr, boll_upper, boll_mid):
        return "NEUTRAL"

    # 1) Climax top (≥3 hits)
    climax = 0
    if vr > 2.5: climax += 1
    if rsi > 75: climax += 1
    if close > boll_upper: climax += 1
    if upper_shadow_ratio is not None and upper_shadow_ratio > 0.35: climax += 1
    if daily_return is not None and daily_return > 0.06: climax += 1
    if high and close < high * 0.97: climax += 1
    if close / ma20 > 1.15: climax += 1
    if climax >= 3:
        return "CLIMAX_TOP"

    # 2) Major break → WEAKENING (highest among the weakening checks)
    if close < ma20 or (dd is not None and dd < -0.12) or ma10 < ma20:
        return "WEAKENING"
    weak = 0
    if close < ma10: weak += 1
    if ma5 < ma10: weak += 1
    if close < boll_mid: weak += 1
    if vr > 1.5 and ind["close"] < ind["open"]: weak += 1
    if dd is not None and dd < -0.08: weak += 1
    if weak >= 2:
        return "WEAKENING"

    # 3) Overheated (≥2 hits)
    over = 0
    if rsi > 70: over += 1
    if close > boll_upper: over += 1
    if close / ma20 > 1.12: over += 1
    if vr > 2.0: over += 1
    if over >= 2:
        return "OVERHEATED"

    # 4) Healthy trend
    if (close > ma5 > ma10 > ma20 > ma60
            and 55 <= rsi <= 68
            and 1.0 <= vr <= 2.0
            and close / ma20 <= 1.10
            and close > boll_mid):
        return "HEALTHY_TREND"

    return "NEUTRAL"


def _trend_break_action(profit_R: float, ind: dict) -> dict | None:
    """
    Graded handling of a major-trend break (instead of one abrupt EXIT_ALL).

    Severity ladder:
      - Confirmed breakdown → clear out:
          跌破 MA20 且 (MA10<MA20 或 自高點回撤≥8%)，或 回撤≥12%
      - 跌破 MA20 但未確認 → 分批保護利潤（盈利越高減越多）
      - 未破 MA20、但自高點回撤≥8% → 先減半保護利潤
      - 否則 → 不觸發（交給狀態處理）
    Returns a decision dict, or None when no break is detected.
    """
    close, ma10, ma20 = ind["close"], ind["ma10"], ind["ma20"]
    dd = ind["drawdown_from_peak"]
    if None in (ma10, ma20):
        return None

    below_ma20 = close < ma20
    deep_drawdown = dd is not None and dd <= -0.12
    confirmed = (below_ma20 and (ma10 < ma20 or (dd is not None and dd <= -0.08))) or deep_drawdown

    if confirmed:
        return {"action": "EXIT_ALL",
                "reason": "大趨勢破壞：跌破 MA20 且確認轉弱（MA10<MA20 或 回撤≥8%）或回撤≥12%",
                "ratio": 1.0, "ratio_type": "sell"}

    if below_ma20:
        if profit_R >= 3:
            return {"action": "SELL_PARTIAL", "reason": "跌破 MA20（尚未確認）：高利潤倉位先減半保護利潤", "ratio": 0.50, "ratio_type": "sell"}
        if profit_R >= 1:
            return {"action": "SELL_PARTIAL", "reason": "跌破 MA20（尚未確認）：獲利倉位先減倉觀察", "ratio": 0.40, "ratio_type": "sell"}
        return {"action": "SELL_PARTIAL", "reason": "跌破 MA20（尚未確認）：先減倉控制風險", "ratio": 0.30, "ratio_type": "sell"}

    if dd is not None and dd <= -0.08:
        return {"action": "SELL_PARTIAL", "reason": "自高點回撤逾 8%，先減半保護利潤", "ratio": 0.50, "ratio_type": "sell"}

    return None


def _decide(state: str, profit_R: float, pnl_pct: float, base_stop: float, ind: dict) -> dict:
    """Snapshot decision following evaluate_position priority (§15)."""
    # Priority 1 — loss control
    if pnl_pct <= -1.5 * base_stop:
        return {"action": "EXIT_ALL", "reason": "觸及第三層止損（-1.5R）", "ratio": 1.0, "ratio_type": "sell"}
    if pnl_pct <= -1.0 * base_stop:
        return {"action": "SELL_PARTIAL", "reason": "觸及第二層止損（-1.0R）", "ratio": 0.40, "ratio_type": "sell"}
    if pnl_pct <= -0.6 * base_stop:
        return {"action": "SELL_PARTIAL", "reason": "觸及第一層止損（-0.6R）", "ratio": 0.30, "ratio_type": "sell"}

    # Priority 2 — major trend break (graded, not a blanket exit)
    tb = _trend_break_action(profit_R, ind)
    if tb:
        return tb

    # Priority 3 — state handlers
    if state == "CLIMAX_TOP":
        if profit_R >= 3: return {"action": "SELL_PARTIAL", "reason": "高潮頂且盈利 ≥+3R，重倉止盈", "ratio": 0.80, "ratio_type": "sell"}
        if profit_R >= 2: return {"action": "SELL_PARTIAL", "reason": "高潮頂且盈利 ≥+2R，重倉止盈", "ratio": 0.70, "ratio_type": "sell"}
        if profit_R >= 1: return {"action": "SELL_PARTIAL", "reason": "高潮頂且盈利 ≥+1R，分批止盈", "ratio": 0.50, "ratio_type": "sell"}
        return {"action": "SELL_PARTIAL", "reason": "高潮頂，即使盈利不足也先減頭寸", "ratio": 0.30, "ratio_type": "sell"}

    if state == "OVERHEATED":
        if profit_R >= 3: return {"action": "SELL_PARTIAL", "reason": "過熱且 ≥+3R，大幅減倉留觀察倉", "ratio": 0.70, "ratio_type": "sell"}
        if profit_R >= 2: return {"action": "SELL_PARTIAL", "reason": "過熱且 ≥+2R，分批止盈", "ratio": 0.30, "ratio_type": "sell"}
        if profit_R >= 1.5: return {"action": "SELL_PARTIAL", "reason": "過熱且 ≥+1.5R，分批止盈", "ratio": 0.25, "ratio_type": "sell"}
        if profit_R >= 1: return {"action": "SELL_PARTIAL", "reason": "過熱且 ≥+1R，開始減倉", "ratio": 0.20, "ratio_type": "sell"}
        return {"action": "HOLD", "reason": "過熱但盈利不足，暫不操作", "ratio": 0.0, "ratio_type": "sell"}

    if state == "WEAKENING":
        if profit_R >= 2: return {"action": "SELL_PARTIAL", "reason": "盈利較多但趨勢轉弱，大幅減倉", "ratio": 0.70, "ratio_type": "sell"}
        if profit_R >= 1: return {"action": "SELL_PARTIAL", "reason": "盈利尚可但趨勢轉弱，減倉", "ratio": 0.50, "ratio_type": "sell"}
        return {"action": "EXIT_ALL", "reason": "盈利不足且趨勢轉弱，退出", "ratio": 1.0, "ratio_type": "sell"}

    if state == "HEALTHY_TREND":
        if 0.8 <= profit_R <= 1.8:
            return {"action": "ADD", "reason": "健康趨勢且 +0.8R~+1.8R，可考慮加倉", "ratio": 0.20, "ratio_type": "add"}
        if profit_R >= 3: return {"action": "SELL_PARTIAL", "reason": "健康趨勢達 +3R，部分止盈、其餘移動止盈", "ratio": 0.25, "ratio_type": "sell"}
        if profit_R >= 2: return {"action": "SELL_PARTIAL", "reason": "健康趨勢達 +2R，部分止盈", "ratio": 0.20, "ratio_type": "sell"}
        return {"action": "HOLD", "reason": "健康趨勢，續抱", "ratio": 0.0, "ratio_type": "sell"}

    return {"action": "HOLD", "reason": "中性、無明確訊號", "ratio": 0.0, "ratio_type": "sell"}


def _trailing_stop(profit_R: float, entry: float, peak: float, ma20: float | None) -> float | None:
    """Trailing stop price by profit_R band (§12.3)."""
    if profit_R < 1:
        return None
    if profit_R < 2:
        return entry
    if profit_R < 3:
        return max(entry, peak * 0.92)
    return max(ma20 or 0, peak * 0.90)


def analyze_position(symbol: str, entry_price: float | None = None, entry_date: str | None = None) -> dict:
    """
    Snapshot position analysis based on the holding's aggregate entry (avg price).

    entry_price : weighted-average buy price for the whole holding. If omitted
                  (None/0), the latest close is used as an assumed entry — useful
                  for analysing any watched stock "as if entering now".
    entry_date  : earliest purchase date (YYYY-MM-DD); used for peak/drawdown window
    """
    df = get_ohlcv(symbol)
    if df is None or df.empty or len(df) < 60:
        return {"error": "INSUFFICIENT_DATA"}

    assumed_entry = False
    if not entry_price or entry_price <= 0:
        entry_price = float(df["Close"].iloc[-1])
        assumed_entry = True

    ma = calculate_ma(df, [5, 10, 20, 60])
    bb = calculate_bollinger_bands(df)
    rsi_s = calculate_rsi(df)
    atr_s = _atr_series(df)
    vol_ma = df["Volume"].rolling(VOLUME_MA_PERIOD).mean()

    close = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else close
    o = float(df["Open"].iloc[-1]); h = float(df["High"].iloc[-1]); l = float(df["Low"].iloc[-1])

    atr14 = _last(atr_s)
    atr_pct = (atr14 / close) if (atr14 and close) else None
    vol_now = float(df["Volume"].iloc[-1]) if pd.notna(df["Volume"].iloc[-1]) else None
    vol_ma20 = _last(vol_ma)
    volume_ratio = (vol_now / vol_ma20) if (vol_now is not None and vol_ma20) else None

    total_range = h - l
    upper_shadow_ratio = ((h - max(o, close)) / total_range) if total_range > 0 else None
    daily_return = (close / prev_close - 1) if prev_close else None

    # Peak / drawdown since the earliest purchase date (fallback: last 120 bars)
    window = df
    if entry_date:
        try:
            window = df[df.index >= pd.to_datetime(entry_date)]
            if window.empty:
                window = df.tail(120)
        except Exception:
            window = df.tail(120)
    else:
        window = df.tail(120)
    peak_price = float(window["Close"].max())
    drawdown_from_peak = (close / peak_price - 1) if peak_price else None

    ind = {
        "close": close, "open": o, "high": h, "low": l,
        "ma5": _last(ma["MA5"]), "ma10": _last(ma["MA10"]),
        "ma20": _last(ma["MA20"]), "ma60": _last(ma["MA60"]),
        "rsi": _last(rsi_s),
        "boll_upper": _last(bb["BB_upper"]), "boll_mid": _last(bb["BB_middle"]),
        "volume_ratio": volume_ratio,
        "upper_shadow_ratio": upper_shadow_ratio,
        "daily_return": daily_return,
        "drawdown_from_peak": drawdown_from_peak,
    }

    if atr_pct is None:
        return {"error": "INSUFFICIENT_DATA"}

    base_stop = min(max(ATR_STOP_MULTIPLIER * atr_pct, MIN_BASE_STOP), MAX_BASE_STOP)
    pnl_pct = close / entry_price - 1
    profit_R = pnl_pct / base_stop if base_stop else 0.0

    state = _classify_state(ind)
    decision = _decide(state, profit_R, pnl_pct, base_stop, ind)
    trailing = _trailing_stop(profit_R, entry_price, peak_price, ind["ma20"])

    def r(x, n=2):
        return None if x is None else round(float(x), n)

    return {
        "symbol": symbol,
        "entry_price": r(entry_price),
        "assumed_entry": assumed_entry,
        "close": r(close),
        "pnl_pct": r(pnl_pct * 100),
        "atr_pct": r(atr_pct * 100),
        "base_stop_pct": r(base_stop * 100),
        "profit_R": r(profit_R),
        "state": state,
        "state_label": STATE_LABELS.get(state, state),
        "decision": decision,
        "high_volatility": bool(ATR_STOP_MULTIPLIER * atr_pct > MAX_BASE_STOP),
        "indicators": {
            "ma5": r(ind["ma5"]), "ma10": r(ind["ma10"]),
            "ma20": r(ind["ma20"]), "ma60": r(ind["ma60"]),
            "rsi": r(ind["rsi"]),
            "boll_upper": r(ind["boll_upper"]), "boll_mid": r(ind["boll_mid"]),
            "volume_ratio": r(volume_ratio),
            "upper_shadow_ratio": r(upper_shadow_ratio),
            "drawdown_from_peak_pct": r(drawdown_from_peak * 100 if drawdown_from_peak is not None else None),
            "peak_price": r(peak_price),
        },
        # Price levels for the chart (entry = aggregate average)
        "levels": {
            "stop_loss_1": r(entry_price * (1 - LOSS_LEVEL_1_MULT * base_stop)),
            "stop_loss_2": r(entry_price * (1 - LOSS_LEVEL_2_MULT * base_stop)),
            "stop_loss_3": r(entry_price * (1 - LOSS_LEVEL_3_MULT * base_stop)),
            "trailing_stop": r(trailing),
            "target_1R": r(entry_price * (1 + base_stop)),
            "target_2R": r(entry_price * (1 + 2 * base_stop)),
            "target_3R": r(entry_price * (1 + 3 * base_stop)),
        },
    }
