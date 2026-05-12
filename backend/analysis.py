"""
Daily analysis engine using rule-based technical signals + linear regression prediction.
Each indicator returns a score in [-2, 2]; weighted sum determines overall rating.
"""
from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
import pandas as pd

from indicators import (
    calculate_bollinger_bands,
    calculate_kd,
    calculate_ma,
    calculate_obv,
    calculate_rsi,
)
from stock_data import get_ohlcv, get_investors_data

logger = logging.getLogger(__name__)

RATING_LABELS = {
    "strong_buy": "強力買進 ▲▲",
    "buy": "買進 ▲",
    "hold": "持有 ─",
    "sell": "賣出 ▼",
    "strong_sell": "強力賣出 ▼▼",
}


def _score_to_rating(score: float) -> str:
    if score >= 2.5:
        return "strong_buy"
    if score >= 1.0:
        return "buy"
    if score >= -1.0:
        return "hold"
    if score >= -2.5:
        return "sell"
    return "strong_sell"


def _linear_regression_forecast(closes: np.ndarray, forecast_days: int = 5) -> dict:
    n = len(closes)
    x = np.arange(n, dtype=float)
    coeffs = np.polyfit(x, closes, 1)
    slope = coeffs[0]
    fitted = np.polyval(coeffs, x)
    residuals = closes - fitted
    r_squared = 1 - np.var(residuals) / np.var(closes)

    pred_price = np.polyval(coeffs, n + forecast_days - 1)
    current = closes[-1]
    change_pct = (pred_price - current) / current * 100

    # Standard error of estimate
    std_err = np.std(residuals)
    upper = pred_price + 1.96 * std_err
    lower = pred_price - 1.96 * std_err

    return {
        "forecast_days": forecast_days,
        "pred_price": round(float(pred_price), 2),
        "pred_change_pct": round(float(change_pct), 2),
        "confidence_interval": [round(float(lower), 2), round(float(upper), 2)],
        "r_squared": round(float(r_squared), 4),
        "slope_per_day": round(float(slope), 4),
        "trend": "上升" if slope > 0 else "下降",
        "method": "OLS線性回歸 (20日)",
    }


def _analyze_institutional_investors(symbol: str) -> dict:
    """
    Analyze institutional investors and major holders.
    Returns institutional holdings, three forces data (for TW stocks), and signals.
    """
    try:
        investors_data = get_investors_data(symbol)
        
        # Taiwan stocks: 三大法人 data
        if investors_data.get("type") == "tw":
            if "error" in investors_data:
                return {
                    "type": "tw",
                    "symbol": symbol,
                    "status": "no_data",
                    "error": investors_data.get("error")
                }
            
            latest_date = investors_data.get("latest_date")
            foreign_net = investors_data.get("foreign_net", 0)  # 外資買賣超
            trust_net = investors_data.get("trust_net", 0)      # 投信買賣超
            dealer_net = investors_data.get("dealer_net", 0)    # 自營商買賣超
            total_net = investors_data.get("total_net", 0)      # 三大法人合計
            trend = investors_data.get("trend", [])
            
            # Analyze the trend
            signals = []
            score = 0.0
            
            # Overall 三大法人 signal
            if total_net > 0:
                signals.append({
                    "type": "bullish",
                    "signal": f"三大法人合計買超 {total_net:,} 股，機構看多"
                })
                score += 1.0
            elif total_net < 0:
                signals.append({
                    "type": "bearish",
                    "signal": f"三大法人合計賣超 {abs(total_net):,} 股，機構看空"
                })
                score -= 1.0
            
            # Individual investor breakdown
            if foreign_net > 0:
                signals.append({
                    "type": "bullish",
                    "signal": f"外資買超 {foreign_net:,} 股"
                })
                score += 0.5
            elif foreign_net < 0:
                signals.append({
                    "type": "bearish",
                    "signal": f"外資賣超 {abs(foreign_net):,} 股"
                })
                score -= 0.5
            
            if trust_net > 0:
                signals.append({
                    "type": "bullish",
                    "signal": f"投信買超 {trust_net:,} 股"
                })
                score += 0.3
            elif trust_net < 0:
                signals.append({
                    "type": "bearish",
                    "signal": f"投信賣超 {abs(trust_net):,} 股"
                })
                score -= 0.3
            
            if dealer_net > 0:
                signals.append({
                    "type": "bullish",
                    "signal": f"自營商買超 {dealer_net:,} 股"
                })
                score += 0.2
            elif dealer_net < 0:
                signals.append({
                    "type": "bearish",
                    "signal": f"自營商賣超 {abs(dealer_net):,} 股"
                })
                score -= 0.2
            
            # Trend analysis: if multiple days trending same direction
            if trend and len(trend) >= 3:
                recent_3 = trend[-3:]
                total_3_days = sum(t.get("total_net", 0) for t in recent_3)
                
                if total_3_days > 0:
                    signals.append({
                        "type": "bullish",
                        "signal": f"近3日三大法人累計買超 {total_3_days:,} 股，持續買進信號"
                    })
                    score += 1.0
                elif total_3_days < 0:
                    signals.append({
                        "type": "bearish",
                        "signal": f"近3日三大法人累計賣超 {abs(total_3_days):,} 股，持續賣出信號"
                    })
                    score -= 1.0
            
            return {
                "type": "tw",
                "symbol": symbol,
                "latest_date": latest_date,
                "components": {
                    "foreign_net": foreign_net,
                    "trust_net": trust_net,
                    "dealer_net": dealer_net,
                    "total_net": total_net,
                },
                "trend": trend[-5:] if trend else [],  # Last 5 days
                "signals": signals,
                "score": round(score, 2),
            }
        
        # US stocks: Institutional holdings
        elif investors_data.get("type") == "us":
            if "error" in investors_data:
                return {
                    "type": "us",
                    "symbol": symbol,
                    "status": "no_data",
                    "error": investors_data.get("error")
                }
            
            held_pct_insiders = investors_data.get("held_pct_insiders")
            held_pct_institutions = investors_data.get("held_pct_institutions")
            top_institutions = investors_data.get("top_institutions", [])
            
            signals = []
            score = 0.0
            
            # Institutional ownership signal
            if held_pct_institutions:
                if held_pct_institutions > 0.70:  # >70%
                    signals.append({
                        "type": "bullish",
                        "signal": f"機構持股高達 {held_pct_institutions*100:.1f}%，主力高度看好"
                    })
                    score += 1.0
                elif held_pct_institutions > 0.50:  # >50%
                    signals.append({
                        "type": "bullish",
                        "signal": f"機構持股 {held_pct_institutions*100:.1f}%，控制力強"
                    })
                    score += 0.5
                elif held_pct_institutions < 0.30:  # <30%
                    signals.append({
                        "type": "neutral",
                        "signal": f"機構持股僅 {held_pct_institutions*100:.1f}%，散戶居多"
                    })
            
            # Insider holdings
            if held_pct_insiders:
                if held_pct_insiders > 0.20:
                    signals.append({
                        "type": "bullish",
                        "signal": f"內部人士持股 {held_pct_insiders*100:.1f}%，高管看好公司"
                    })
                    score += 0.5
            
            return {
                "type": "us",
                "symbol": symbol,
                "held_pct_insiders": held_pct_insiders,
                "held_pct_institutions": held_pct_institutions,
                "top_institutions": top_institutions[:5] if top_institutions else [],
                "signals": signals,
                "score": round(score, 2),
            }
    
    except Exception as e:
        logger.error(f"Failed to analyze investors for {symbol}: {e}")
        return {
            "symbol": symbol,
            "status": "error",
            "error": str(e)
        }


def analyze_stock(symbol: str, name: str = "", interval: str = "1d") -> dict:
    df = get_ohlcv(symbol, interval=interval)
    if df.empty or len(df) < 20:
        return {"symbol": symbol, "name": name, "error": "資料不足，無法分析"}

    price = float(df["Close"].iloc[-1])
    prev_price = float(df["Close"].iloc[-2]) if len(df) >= 2 else price
    daily_change_pct = (price - prev_price) / prev_price * 100

    mas = calculate_ma(df, [5, 10, 20, 60, 120, 240])
    bb = calculate_bollinger_bands(df)
    rsi_s = calculate_rsi(df)
    kd = calculate_kd(df)
    obv_s = calculate_obv(df)

    signals: list[dict] = []
    score = 0.0

    # ── MA trend signals ──────────────────────────────────────────────────
    def last(s):
        v = s.iloc[-1] if len(s) > 0 else np.nan
        return float(v) if pd.notna(v) else None

    ma5  = last(mas["MA5"])
    ma10 = last(mas["MA10"])
    ma20 = last(mas["MA20"])
    ma60 = last(mas["MA60"])
    ma120 = last(mas["MA120"])
    ma240 = last(mas["MA240"])

    if ma5 and ma10:
        if ma5 > ma10:
            signals.append({"indicator": "MA", "signal": f"短期多頭：MA5({ma5:.2f}) > MA10({ma10:.2f})", "type": "bullish"})
            score += 1.0
        else:
            signals.append({"indicator": "MA", "signal": f"短期空頭：MA5({ma5:.2f}) < MA10({ma10:.2f})", "type": "bearish"})
            score -= 1.0

    if ma20 and ma60:
        if ma20 > ma60:
            signals.append({"indicator": "MA", "signal": f"中期多頭：MA20({ma20:.2f}) > MA60({ma60:.2f})", "type": "bullish"})
            score += 1.0
        else:
            signals.append({"indicator": "MA", "signal": f"中期空頭：MA20({ma20:.2f}) < MA60({ma60:.2f})", "type": "bearish"})
            score -= 1.0

    # Golden/dead cross (MA5 crosses MA20)
    if len(mas["MA5"]) >= 2 and len(mas["MA20"]) >= 2:
        ma5_prev = float(mas["MA5"].iloc[-2]) if pd.notna(mas["MA5"].iloc[-2]) else None
        ma20_prev = float(mas["MA20"].iloc[-2]) if pd.notna(mas["MA20"].iloc[-2]) else None
        if ma5 and ma20 and ma5_prev and ma20_prev:
            if ma5 > ma20 and ma5_prev <= ma20_prev:
                signals.append({"indicator": "MA", "signal": "MA5/MA20 黃金交叉！買入訊號", "type": "bullish"})
                score += 2.0
            elif ma5 < ma20 and ma5_prev >= ma20_prev:
                signals.append({"indicator": "MA", "signal": "MA5/MA20 死亡交叉！賣出訊號", "type": "bearish"})
                score -= 2.0

    # Price vs key MAs
    if ma60:
        if price > ma60:
            signals.append({"indicator": "MA60", "signal": f"股價在季線之上 (季線:{ma60:.2f})", "type": "bullish"})
            score += 0.5
        else:
            signals.append({"indicator": "MA60", "signal": f"股價跌破季線 (季線:{ma60:.2f})", "type": "bearish"})
            score -= 0.5

    if ma240:
        if price > ma240:
            signals.append({"indicator": "MA240", "signal": f"股價在年線之上 (年線:{ma240:.2f})", "type": "bullish"})
            score += 0.5
        else:
            signals.append({"indicator": "MA240", "signal": f"股價跌破年線 (年線:{ma240:.2f})", "type": "bearish"})
            score -= 0.5

    # ── RSI signals ───────────────────────────────────────────────────────
    rsi_val = last(rsi_s)
    if rsi_val:
        if rsi_val >= 80:
            signals.append({"indicator": "RSI", "signal": f"RSI={rsi_val:.1f} 嚴重超買，注意回調風險", "type": "bearish"})
            score -= 2.0
        elif rsi_val >= 70:
            signals.append({"indicator": "RSI", "signal": f"RSI={rsi_val:.1f} 超買區域", "type": "bearish"})
            score -= 1.0
        elif rsi_val <= 20:
            signals.append({"indicator": "RSI", "signal": f"RSI={rsi_val:.1f} 嚴重超賣，反彈機率高", "type": "bullish"})
            score += 2.0
        elif rsi_val <= 30:
            signals.append({"indicator": "RSI", "signal": f"RSI={rsi_val:.1f} 超賣區域，關注反彈", "type": "bullish"})
            score += 1.0
        elif 45 <= rsi_val <= 55:
            signals.append({"indicator": "RSI", "signal": f"RSI={rsi_val:.1f} 中性區間", "type": "neutral"})
        elif rsi_val > 55:
            signals.append({"indicator": "RSI", "signal": f"RSI={rsi_val:.1f} 偏多區間", "type": "bullish"})
            score += 0.3
        else:
            signals.append({"indicator": "RSI", "signal": f"RSI={rsi_val:.1f} 偏空區間", "type": "bearish"})
            score -= 0.3

    # RSI divergence (simplified)
    if len(rsi_s) >= 5 and len(df) >= 5:
        price_trend = df["Close"].iloc[-5:].values
        rsi_trend = rsi_s.iloc[-5:].values
        if not np.any(np.isnan(rsi_trend)):
            price_slope = np.polyfit(range(5), price_trend, 1)[0]
            rsi_slope = np.polyfit(range(5), rsi_trend, 1)[0]
            if price_slope > 0 and rsi_slope < 0:
                signals.append({"indicator": "RSI", "signal": "RSI頂背離：股價創高但RSI下降，注意反轉", "type": "bearish"})
                score -= 1.5
            elif price_slope < 0 and rsi_slope > 0:
                signals.append({"indicator": "RSI", "signal": "RSI底背離：股價創低但RSI上升，潛在反彈", "type": "bullish"})
                score += 1.5

    # ── KD signals ────────────────────────────────────────────────────────
    k_val = last(kd["K"])
    d_val = last(kd["D"])
    if k_val and d_val and len(kd["K"]) >= 2 and len(kd["D"]) >= 2:
        k_prev = float(kd["K"].iloc[-2]) if pd.notna(kd["K"].iloc[-2]) else None
        d_prev = float(kd["D"].iloc[-2]) if pd.notna(kd["D"].iloc[-2]) else None

        if k_prev and d_prev:
            if k_val > d_val and k_prev <= d_prev:
                signals.append({"indicator": "KD", "signal": f"KD黃金交叉！K={k_val:.1f} D={d_val:.1f} 買入訊號", "type": "bullish"})
                score += 2.0
            elif k_val < d_val and k_prev >= d_prev:
                signals.append({"indicator": "KD", "signal": f"KD死亡交叉！K={k_val:.1f} D={d_val:.1f} 賣出訊號", "type": "bearish"})
                score -= 2.0
            elif k_val > d_val:
                signals.append({"indicator": "KD", "signal": f"K線在D線之上 K={k_val:.1f} D={d_val:.1f}", "type": "bullish"})
                score += 0.5
            else:
                signals.append({"indicator": "KD", "signal": f"K線在D線之下 K={k_val:.1f} D={d_val:.1f}", "type": "bearish"})
                score -= 0.5

        if k_val <= 20 and d_val <= 20:
            signals.append({"indicator": "KD", "signal": f"KD超賣區域 (K={k_val:.1f})", "type": "bullish"})
            score += 1.0
        elif k_val >= 80 and d_val >= 80:
            signals.append({"indicator": "KD", "signal": f"KD超買區域 (K={k_val:.1f})", "type": "bearish"})
            score -= 1.0

    # ── Bollinger Band signals ────────────────────────────────────────────
    bb_upper = last(bb["BB_upper"])
    bb_lower = last(bb["BB_lower"])
    bb_middle = last(bb["BB_middle"])
    if bb_upper and bb_lower and bb_middle:
        bb_range = bb_upper - bb_lower
        if bb_range > 0:
            pct_b = (price - bb_lower) / bb_range
            bandwidth = bb_range / bb_middle * 100
            if pct_b > 1.0:
                signals.append({"indicator": "BB", "signal": f"突破布林上軌！%B={pct_b:.2f} 強勢突破", "type": "bullish"})
                score += 1.0
            elif pct_b > 0.85:
                signals.append({"indicator": "BB", "signal": f"接近布林上軌 (上軌:{bb_upper:.2f}) 注意回調", "type": "bearish"})
                score -= 0.5
            elif pct_b < 0.0:
                signals.append({"indicator": "BB", "signal": f"跌破布林下軌！%B={pct_b:.2f} 超賣反彈機會", "type": "bullish"})
                score += 1.0
            elif pct_b < 0.15:
                signals.append({"indicator": "BB", "signal": f"接近布林下軌 (下軌:{bb_lower:.2f}) 關注反彈", "type": "bullish"})
                score += 0.5
            else:
                signals.append({"indicator": "BB", "signal": f"布林通道中性區間 (中軌:{bb_middle:.2f})", "type": "neutral"})

            if bandwidth < 5:
                signals.append({"indicator": "BB", "signal": f"布林帶極窄 ({bandwidth:.1f}%) 醞釀突破行情", "type": "neutral"})

    # ── Volume signals ────────────────────────────────────────────────────
    if len(df) >= 20:
        avg_vol = float(df["Volume"].iloc[-20:].mean())
        cur_vol = float(df["Volume"].iloc[-1])
        vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 1.0
        is_up_day = df["Close"].iloc[-1] > df["Open"].iloc[-1]
        if vol_ratio > 2.0:
            vtype = "bullish" if is_up_day else "bearish"
            signals.append({"indicator": "Volume", "signal": f"爆量 (成交量={vol_ratio:.1f}倍均量) {'上漲放量強勢' if is_up_day else '下跌放量賣壓重'}", "type": vtype})
            score += 1.5 if is_up_day else -1.5
        elif vol_ratio > 1.5:
            signals.append({"indicator": "Volume", "signal": f"放量 ({vol_ratio:.1f}倍均量)", "type": "bullish" if is_up_day else "bearish"})
            score += 0.5 if is_up_day else -0.5
        elif vol_ratio < 0.5:
            signals.append({"indicator": "Volume", "signal": f"縮量 ({vol_ratio:.1f}倍均量) 市場觀望", "type": "neutral"})

    # ── OBV signals ───────────────────────────────────────────────────────
    window = min(10, len(obv_s))
    if window >= 5 and not obv_s.iloc[-window:].isna().any():
        obv_arr = obv_s.iloc[-window:].values.astype(float)
        price_arr = df["Close"].iloc[-window:].values.astype(float)
        obv_slope   = np.polyfit(range(window), obv_arr, 1)[0]
        price_slope = np.polyfit(range(window), price_arr, 1)[0]
        if price_slope > 0 and obv_slope < 0:
            signals.append({"indicator": "OBV", "signal": "OBV頂背離：股價上漲但OBV下降，量能背離警告", "type": "bearish"})
            score -= 1.5
        elif price_slope < 0 and obv_slope > 0:
            signals.append({"indicator": "OBV", "signal": "OBV底背離：股價下跌但OBV上升，潛在量能支撐", "type": "bullish"})
            score += 1.5
        elif obv_slope > 0 and price_slope > 0:
            signals.append({"indicator": "OBV", "signal": "OBV同步上揚，量能確認多頭趨勢", "type": "bullish"})
            score += 0.5
        elif obv_slope < 0 and price_slope < 0:
            signals.append({"indicator": "OBV", "signal": "OBV同步下降，量能確認空頭趨勢", "type": "bearish"})
            score -= 0.5

    # ── Linear regression prediction ──────────────────────────────────────
    prediction_5d = None
    prediction_20d = None
    if len(df) >= 20:
        closes_20 = df["Close"].tail(20).values.astype(float)
        prediction_5d = _linear_regression_forecast(closes_20, forecast_days=5)
    if len(df) >= 60:
        closes_60 = df["Close"].tail(60).values.astype(float)
        prediction_20d = _linear_regression_forecast(closes_60, forecast_days=20)

    # Support & resistance (recent swing highs/lows)
    support = None
    resistance = None
    if len(df) >= 30:
        recent = df.tail(30)
        support = float(recent["Low"].min())
        resistance = float(recent["High"].max())

    rating_key = _score_to_rating(score)

    return {
        "symbol": symbol,
        "name": name,
        "price": round(price, 4),
        "daily_change_pct": round(daily_change_pct, 2),
        "date": df.index[-1].strftime("%Y-%m-%d"),
        "signals": signals,
        "score": round(score, 2),
        "rating": RATING_LABELS[rating_key],
        "rating_key": rating_key,
        "indicators": {
            "MA5": round(ma5, 2) if ma5 else None,
            "MA10": round(ma10, 2) if ma10 else None,
            "MA20": round(ma20, 2) if ma20 else None,
            "MA60": round(ma60, 2) if ma60 else None,
            "MA120": round(ma120, 2) if ma120 else None,
            "MA240": round(ma240, 2) if ma240 else None,
            "RSI": round(rsi_val, 2) if rsi_val else None,
            "K": round(k_val, 2) if k_val else None,
            "D": round(d_val, 2) if d_val else None,
            "BB_upper": round(bb_upper, 2) if bb_upper else None,
            "BB_middle": round(bb_middle, 2) if bb_middle else None,
            "BB_lower": round(bb_lower, 2) if bb_lower else None,
        },
        "support": round(support, 2) if support else None,
        "resistance": round(resistance, 2) if resistance else None,
        "prediction_5d": prediction_5d,
        "prediction_20d": prediction_20d,
        "investors": _analyze_institutional_investors(symbol),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _flatten_watchlist(node, path: str = "") -> list[tuple[str, dict]]:
    """Recursively extract all (path_label, stock) pairs from nested watchlist."""
    items = []
    if isinstance(node, list):
        for s in node:
            items.append((path, s))
    elif isinstance(node, dict):
        for key, val in node.items():
            label = f"{path} > {key}" if path else key
            items.extend(_flatten_watchlist(val, label))
    return items


def generate_daily_report(watchlist: dict) -> dict:
    """Analyze all stocks and produce a structured daily report (works with nested watchlist)."""
    all_items = _flatten_watchlist(watchlist)

    all_results = {}
    top_buy: list[dict] = []
    top_sell: list[dict] = []
    sector_scores: dict[str, list[float]] = {}

    for path, s in all_items:
        symbol = s["symbol"]
        if symbol in all_results:
            continue  # skip duplicates (same stock in multiple sub-categories)
        result = analyze_stock(symbol, s.get("name", ""))
        if "error" in result:
            continue
        all_results[symbol] = result
        # accumulate per top-level sector (first component of path)
        top_sector = path.split(" > ")[0] if " > " in path else path
        sector_scores.setdefault(top_sector, []).append(result["score"])
        if result["rating_key"] in ("strong_buy", "buy"):
            top_buy.append({"symbol": symbol, "name": s.get("name", ""), "score": result["score"], "rating": result["rating"]})
        elif result["rating_key"] in ("strong_sell", "sell"):
            top_sell.append({"symbol": symbol, "name": s.get("name", ""), "score": result["score"], "rating": result["rating"]})

    sector_summary = {
        sec: {
            "avg_score": round(float(np.mean(scores)), 2),
            "sentiment": "多頭" if np.mean(scores) > 0.5 else ("空頭" if np.mean(scores) < -0.5 else "中性"),
            "count": len(scores),
        }
        for sec, scores in sector_scores.items()
    }

    top_buy.sort(key=lambda x: x["score"], reverse=True)
    top_sell.sort(key=lambda x: x["score"])

    overall_scores = [r["score"] for r in all_results.values()]
    market_sentiment = "多頭" if (overall_scores and np.mean(overall_scores) > 0.5) else ("空頭" if (overall_scores and np.mean(overall_scores) < -0.5) else "中性")

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_sentiment": market_sentiment,
        "top_opportunities": top_buy[:5],
        "top_risks": top_sell[:5],
        "sector_summary": sector_summary,
        "all_results": all_results,
    }
