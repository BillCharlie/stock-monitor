"""
明日(T+1) 短線買賣時機訊號 — 對應「K 線影線、量價與隔日買賣決策框架」。

術語說明：文中「明日 / T+1」一律指「以今日收盤為基準的下一個交易日」，
即第二個交易日（今日為第一日），不是第三日。

與 position_strategy（倉位管理）互補：
  - position_strategy 回答「持有後該減/加/出」；
  - daily_signal 回答「明日(T+1)在什麼價位、什麼條件下進出最合適」。

輸出：今日 K 線分類、四項打分（趨勢/K線/量能/位置）、偏多偏空總分、
關鍵價位（今高/今低/MA5/MA10/前高/平台支撐）、以及隔日條件式觸發與建議買法。
本模組為技術分析輔助，不構成投資建議。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stock_data import get_ohlcv
from indicators import calculate_ma


def _last(s):
    if s is None or len(s) == 0:
        return None
    v = s.iloc[-1]
    return float(v) if pd.notna(v) else None


def _r(x, n=2):
    return None if x is None else round(float(x), n)


def analyze_daily_signal(symbol: str) -> dict:
    df = get_ohlcv(symbol)
    if df is None or df.empty or len(df) < 20:
        return {"error": "INSUFFICIENT_DATA"}

    o = float(df["Open"].iloc[-1]); h = float(df["High"].iloc[-1])
    l = float(df["Low"].iloc[-1]); c = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2])
    prev_low = float(df["Low"].iloc[-2])
    vol = float(df["Volume"].iloc[-1]) if pd.notna(df["Volume"].iloc[-1]) else 0.0

    ma = calculate_ma(df, [5, 10, 20, 60])
    ma5, ma10, ma20, ma60 = _last(ma["MA5"]), _last(ma["MA10"]), _last(ma["MA20"]), _last(ma["MA60"])
    ma5_prev = float(ma["MA5"].iloc[-2]) if len(df) > 5 else None
    ma10_prev = float(ma["MA10"].iloc[-2]) if len(df) > 10 else None

    vol_ma5 = float(df["Volume"].rolling(5).mean().iloc[-1])
    vol_ma10 = float(df["Volume"].rolling(10).mean().iloc[-1])
    vr5 = (vol / vol_ma5) if vol_ma5 else None
    vr10 = (vol / vol_ma10) if vol_ma10 else None

    # 前高（近 60 日、不含今日的最高）與平台支撐（近 20 日、不含今日的最低）
    look = df.iloc[-61:-1] if len(df) > 61 else df.iloc[:-1]
    prev_high = float(look["High"].max()) if not look.empty else None
    plat = df.iloc[-21:-1] if len(df) > 21 else df.iloc[:-1]
    platform_support = float(plat["Low"].min()) if not plat.empty else None

    rng = h - l
    body = c - o
    bullish = c >= o
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l
    upper_ratio = (upper_shadow / rng) if rng > 0 else 0.0
    lower_ratio = (lower_shadow / rng) if rng > 0 else 0.0
    body_ratio = (abs(body) / rng) if rng > 0 else 0.0
    daily_return = (c / prev_close - 1) if prev_close else 0.0
    big_volume = vr5 is not None and vr5 >= 1.2
    low_volume = vr5 is not None and vr5 < 0.8

    # ── 位置 ─────────────────────────────────────────────────────────────────
    near_prev_high = prev_high is not None and c >= prev_high * 0.98
    if ma20 and c / ma20 >= 1.15:
        position = "高位"
    elif near_prev_high and not (prev_high and c > prev_high):
        position = "前高附近"
    elif ma20 and ma60 and c <= ma20 * 0.98 and c <= ma60:
        position = "低位"
    elif (ma5 and abs(c / ma5 - 1) < 0.02) or (ma10 and abs(c / ma10 - 1) < 0.02):
        position = "均線附近"
    else:
        position = "平台/中段"

    broke_prev_high = prev_high is not None and c > prev_high

    # ── K 線分類（取第一個命中）────────────────────────────────────────────────
    if position in ("高位", "前高附近") and upper_ratio >= 0.30 and big_volume:
        candle = "高位衝高回落"
    elif bullish and body_ratio >= 0.5 and big_volume:
        candle = "放量大陽線帶下影" if lower_ratio >= 0.2 else "放量大陽線"
    elif broke_prev_high and big_volume:
        candle = "放量突破前高/平台"
    elif upper_ratio >= 0.35:
        candle = "紅K長上影" if bullish else "綠K長上影"
    elif lower_ratio >= 0.35 and body_ratio < 0.5:
        candle = "低位長下影" if position == "低位" else "長下影小實體"
    elif abs(upper_ratio - lower_ratio) < 0.12 and body_ratio < 0.4:
        candle = "上下影均衡收漲" if bullish else "上下影均衡收跌"
    else:
        candle = "小陽線" if bullish else "小陰線"

    # 短期均線倒掛（MA5 跌破 MA10，俗稱短均死叉）— 短線動能轉弱訊號
    ma_inverted = bool(ma5 and ma10 and ma5 < ma10)
    # 剛剛倒掛（前一日 MA5≥MA10、今日 MA5<MA10）= 死叉當天，訊號更強
    ma_cross_today = bool(ma_inverted and ma5_prev and ma10_prev and ma5_prev >= ma10_prev)

    # ── §13 打分 ───────────────────────────────────────────────────────────────
    trend = 0
    trend += 1 if (ma5 and c > ma5) else -2
    trend += 1 if (ma10 and c > ma10) else -3
    if ma5 and ma5_prev and ma5 > ma5_prev: trend += 1
    if ma10 and ma10_prev and ma10 > ma10_prev: trend += 1
    if ma5 and ma10 and ma20 and ma5 > ma10 > ma20: trend += 2
    if ma_inverted: trend -= 2          # MA5<MA10 短期均線倒掛
    if ma_cross_today: trend -= 1       # 今日剛形成死叉，額外扣分

    kline = 0
    if candle == "放量大陽線": kline += 3
    elif candle == "放量大陽線帶下影": kline += 2
    elif candle == "低位長下影": kline += 2
    elif candle == "紅K長上影": kline -= 2 if position in ("高位", "前高附近") else 0
    elif candle == "綠K長上影": kline -= 3
    elif candle == "高位衝高回落": kline -= 3
    elif candle == "上下影均衡收跌": kline -= 1
    if c < prev_low: kline -= 3

    volume_score = 0
    if vr5 is not None and vr5 > 1.0: volume_score += 1
    if vr10 is not None and vr10 > 1.0: volume_score += 1
    if broke_prev_high and big_volume: volume_score += 3
    if upper_ratio >= 0.35 and big_volume: volume_score -= 2
    if (not bullish) and big_volume: volume_score -= 3
    if low_volume and platform_support and c > platform_support: volume_score += 1

    pos_score = 0
    if position == "低位" and lower_ratio >= 0.3: pos_score += 2
    if candle == "放量突破前高/平台": pos_score += 3
    if position in ("平台/中段", "均線附近") and platform_support and c > platform_support and low_volume: pos_score += 2
    if near_prev_high and not broke_prev_high: pos_score -= 1
    if candle == "高位衝高回落": pos_score -= 3
    if broke_prev_high and bullish and upper_ratio < 0.2: pos_score += 3

    total = trend + kline + volume_score + pos_score
    if total >= 7:    bias = "偏多（可找買點）"
    elif total >= 4:  bias = "偏多觀察（等確認）"
    elif total >= 1:  bias = "中性（不急操作）"
    elif total >= -1: bias = "偏弱（降低期待）"
    else:             bias = "風險較高（不宜追高/應減倉）"

    # ── 明日(T+1) 條件式觸發（術語後括號為白話）─────────────────────────────────
    long_triggers = [f"站上今日高點 {_r(h)} 且不破回 → 偏多延續（漲勢可能續走）"]
    if ma5: long_triggers.append(f"回踩 MA5 {_r(ma5)} 不破再轉強 → 可低吸（回落到均線不破時逢低買進）")
    if prev_high and not broke_prev_high:
        long_triggers.append(f"放量站上前高 {_r(prev_high)} 並收穩 → 突破確認（過前高、可視為轉強）")

    short_triggers = [f"跌破今日低點 {_r(l)} → 承接失效（下方買盤頂不住）、偏空"]
    if ma5: short_triggers.append(f"跌破 MA5 {_r(ma5)} → 超短線轉弱（短線走弱、不宜追）")
    if ma10: short_triggers.append(f"跌破 MA10 {_r(ma10)} → 短線趨勢轉弱（該減倉或退出）")
    if ma_inverted and ma10:
        short_triggers.append(f"反彈不過 MA10 {_r(ma10)} → 短均倒掛壓制（MA5<MA10、追多需謹慎）")
    if prev_high and not broke_prev_high:
        short_triggers.append(f"反彈不過前高 {_r(prev_high)} → 上方壓力持續（衝不過、賣壓重）")

    # 短期均線倒掛結構提示
    note = None
    if ma_cross_today:
        note = f"MA5({_r(ma5)}) 今日剛跌破 MA10({_r(ma10)})，形成短均死叉（短線動能轉弱）；反彈不過 MA10 不宜追多，等站回 MA10 之上再轉強。"
    elif ma_inverted:
        note = f"MA5({_r(ma5)}) < MA10({_r(ma10)})，短期均線倒掛（短線偏弱）；除非放量重新站上 MA10，否則偏向回踩/觀望。"

    # ── 建議買法 ───────────────────────────────────────────────────────────────
    if candle in ("放量突破前高/平台",) or (broke_prev_high and big_volume):
        buy_method = f"突破買（突破壓力位時買進）：放量站上 {_r(prev_high or h)} 收穩、明日(T+1)不跌回突破位"
    elif (ma5 and c > ma5) and (ma10 and c > ma10) and total >= 1:
        buy_method = f"回踩買（拉回到均線不破再買，即低吸）：回踩 MA5 {_r(ma5)} / MA10 {_r(ma10)} 不破、出現承接再進"
    elif candle in ("紅K長上影", "綠K長上影", "高位衝高回落", "上下影均衡收跌", "上下影均衡收漲", "長下影小實體", "低位長下影"):
        buy_method = f"確認買（等明天走強確認再買）：明日(T+1)收紅站回今日高點 {_r(h)}、量能溫和放大再進"
    else:
        buy_method = "訊號分歧（多空不明），等明日(T+1)確認再決定"

    return {
        "candle_type": candle,
        "position": position,
        "bias": bias,
        "score": {"trend": trend, "kline": kline, "volume": volume_score, "position": pos_score, "total": total},
        "levels": {
            "today_high": _r(h), "today_low": _r(l), "close": _r(c),
            "ma5": _r(ma5), "ma10": _r(ma10),
            "prev_high": _r(prev_high), "platform_support": _r(platform_support),
        },
        "indicators": {
            "vol_ratio5": _r(vr5), "vol_ratio10": _r(vr10),
            "upper_shadow_ratio": _r(upper_ratio), "lower_shadow_ratio": _r(lower_ratio),
            "body_ratio": _r(body_ratio), "daily_return_pct": _r(daily_return * 100),
        },
        "long_triggers": long_triggers,
        "short_triggers": short_triggers,
        "buy_method": buy_method,
        "ma_inverted": ma_inverted,
        "ma_cross_today": ma_cross_today,
        "note": note,
    }
