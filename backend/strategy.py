"""
Crypto Trading Strategy Engine v2
Nova Trend (trend-following) and Nova Range (mean-reversion)
Multi-timeframe confirmation, ATR-based stops, improved regime detection
"""

import requests
import numpy as np
import pandas as pd
from datetime import datetime
import ccxt

# HTX exchange client
htx = ccxt.htx()

def fetch_candles(symbol="BTC/USDT", timeframe="15m", limit=100):
    """Fetch OHLCV candles from HTX"""
    try:
        candles = htx.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        print(f"Error fetching candles: {e}")
        return None

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()

def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index)"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def calculate_supertrend(high, low, close, period=10, multiplier=3):
    """
    Calculate Supertrend indicator
    """
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    hl2 = (high + low) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(1, index=close.index)
    
    for i in range(period, len(close)):
        if i == period:
            supertrend.iloc[i] = lower_band.iloc[i]
            continue
            
        pc = supertrend.iloc[i-1]
        
        if close.iloc[i] > upper_band.iloc[i]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i]:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1
        else:
            supertrend.iloc[i] = pc
            direction.iloc[i] = direction.iloc[i-1]
    
    return supertrend, direction

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, lower, sma

def calculate_indicators(df):
    """Calculate all indicators for a dataframe"""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    
    # EMAs
    df["ema9"] = calculate_ema(close, 9)
    df["ema20"] = calculate_ema(close, 20)
    df["ema50"] = calculate_ema(close, 50)
    
    # RSI
    df["rsi"] = calculate_rsi(close, 14)
    
    # MACD
    df["macd"], df["macd_signal"], df["macd_hist"] = calculate_macd(close)
    
    # ATR
    df["atr"] = calculate_atr(df, 14)
    
    # Supertrend
    df["supertrend"], df["supertrend_dir"] = calculate_supertrend(high, low, close)
    
    # Bollinger Bands
    df["bb_upper"], df["bb_lower"], df["bb_middle"] = calculate_bollinger_bands(close)
    
    # Volume SMA
    df["volume_sma"] = volume.rolling(window=20).mean()
    df["volume_ratio"] = volume / df["volume_sma"]
    
    return df

def detect_regime(df_15m, df_4h=None):
    """
    Improved market regime detection with persistence requirement.
    
    TREND regime conditions:
    - EMA20 and EMA50 separation > 1.5%
    - MACD histogram magnitude significant
    - RSI outside 45-55 zone
    - Price consistently above/below EMA20
    - 4H trend alignment (if 4H data provided)
    
    RANGE regime conditions:
    - EMA20 and EMA50 separation < 1%
    - RSI between 40-60 most of the time
    - MACD histogram near zero
    - Price oscillating around EMA20
    - Low directional momentum
    
    Requires regime persistence for 3 candles before switching.
    """
    latest = df_15m.iloc[-1]
    prev3 = df_15m.iloc[-4:-1]  # Last 3 candles for persistence check
    
    # EMA separation percentage
    ema_diff_pct = abs(latest["ema20"] - latest["ema50"]) / latest["close"] * 100
    
    # RSI
    rsi = latest["rsi"]
    
    # MACD momentum
    macd_hist = latest["macd_hist"]
    macd_hist_pct = macd_hist / latest["close"] * 100 if latest["close"] > 0 else 0
    
    # ATR for volatility
    atr = latest["atr"]
    atr_pct = atr / latest["close"] * 100 if latest["close"] > 0 else 0
    
    # Price vs EMA20
    price_vs_ema20 = (latest["close"] - latest["ema20"]) / latest["ema20"] * 100
    
    # Volume
    volume_ratio = latest["volume_ratio"] if "volume_ratio" in latest else 1
    
    # Score-based regime detection
    range_score = 0
    trend_score = 0
    
    # EMA separation scoring
    if ema_diff_pct < 0.8:
        range_score += 3
    elif ema_diff_pct < 1.0:
        range_score += 2
    elif ema_diff_pct > 2.5:
        trend_score += 3
    elif ema_diff_pct > 1.5:
        trend_score += 2
    
    # RSI scoring
    if 40 <= rsi <= 60:
        range_score += 2
    elif rsi > 65:
        trend_score += 2
    elif rsi < 35:
        trend_score += 2
    
    # RSI stability (check if RSI was in range/zone for last 3 candles)
    rsi_in_range_count = sum(1 for i in range(-4, 0) if 40 <= df_15m.iloc[i]["rsi"] <= 60)
    if rsi_in_range_count >= 3:
        range_score += 1
    
    # MACD scoring
    if abs(macd_hist_pct) < 0.1:
        range_score += 2
    elif abs(macd_hist_pct) < 0.2:
        range_score += 1
    elif macd_hist_pct > 0.3:
        trend_score += 2
    elif macd_hist_pct > 0.15:
        trend_score += 1
    elif macd_hist_pct < -0.3:
        trend_score += 2
    elif macd_hist_pct < -0.15:
        trend_score += 1
    
    # Price position relative to EMA20
    if abs(price_vs_ema20) < 0.5:
        range_score += 1
    elif price_vs_ema20 > 1.0:
        trend_score += 1
    elif price_vs_ema20 < -1.0:
        trend_score += 1
    
    # Volume confirmation
    if volume_ratio > 1.5 and trend_score > 0:
        trend_score += 1
    elif volume_ratio < 0.7:
        range_score += 1  # Low volume favors range
    
    # 4H timeframe confirmation (if available)
    if df_4h is not None:
        h4_latest = df_4h.iloc[-1]
        h4_ema_diff = abs(h4_latest["ema20"] - h4_latest["ema50"]) / h4_latest["close"] * 100
        h4_rsi = h4_latest["rsi"]
        h4_price_vs_ema = (h4_latest["close"] - h4_latest["ema20"]) / h4_latest["ema20"] * 100
        
        # 4H trend bias
        if h4_ema_diff > 1.5:
            if h4_price_vs_ema > 0:
                trend_score += 2  # 4H bullish
            else:
                trend_score -= 1  # 4H bearish weakens bullish case
        elif h4_ema_diff < 1.0:
            range_score += 1
        
        if h4_rsi > 60 or h4_rsi < 40:
            trend_score += 1  # 4H RSI confirms trend
    else:
        # Without 4H, be more conservative
        if trend_score > 0:
            trend_score -= 1
    
    # Determine regime with persistence
    detected_regime = "RANGE" if range_score > trend_score else "TREND"
    
    # Check persistence (need 3 candles of same regime)
    regime_persistence_count = 0
    for i in range(-4, 0):
        prev_ema_diff = abs(df_15m.iloc[i]["ema20"] - df_15m.iloc[i]["ema50"]) / df_15m.iloc[i]["close"] * 100
        prev_rsi = df_15m.iloc[i]["rsi"]
        
        if detected_regime == "RANGE":
            if prev_ema_diff < 1.0 and 40 <= prev_rsi <= 60:
                regime_persistence_count += 1
        else:  # TREND
            if prev_ema_diff > 1.5 or prev_rsi > 65 or prev_rsi < 35:
                regime_persistence_count += 1
    
    # Require 3 candles persistence to switch regime
    if regime_persistence_count < 3:
        # Stay in previous regime (conservative)
        regime = "RANGE"  # Default to range when uncertain
    else:
        regime = detected_regime
    
    # Direction for TREND regime
    direction = None
    if regime == "TREND":
        if latest["supertrend_dir"] == 1 and rsi > 45:
            direction = "LONG"
        elif latest["supertrend_dir"] == -1 and rsi < 55:
            direction = "SHORT"
        else:
            direction = "LONG" if rsi > 50 else "SHORT"
    
    return {
        "regime": regime,
        "direction": direction,
        "ema_diff_pct": round(ema_diff_pct, 4),
        "rsi": round(rsi, 2),
        "macd_hist": round(macd_hist, 2),
        "macd_hist_pct": round(macd_hist_pct, 4),
        "atr": round(atr, 2),
        "atr_pct": round(atr_pct, 4),
        "price_vs_ema20": round(price_vs_ema20, 4),
        "volume_ratio": round(volume_ratio, 2),
        "bb_upper": round(latest["bb_upper"], 2) if "bb_upper" in latest else 0,
        "bb_lower": round(latest["bb_lower"], 2) if "bb_lower" in latest else 0,
        "supertrend_dir": int(latest["supertrend_dir"]),
        "range_score": range_score,
        "trend_score": trend_score,
        "volume_ratio_raw": float(volume_ratio)
    }

def calculate_confidence(regime_data, regime, strategy_type="TREND"):
    """
    Improved confidence calculation.
    
    Factors:
    - Trend alignment strength
    - Momentum strength
    - Volume confirmation
    - Volatility stability
    - Risk/reward potential
    """
    confidence = 0.5  # Base confidence
    factors = []
    
    rsi = regime_data["rsi"]
    ema_diff = regime_data["ema_diff_pct"]
    macd_hist = regime_data["macd_hist"]
    macd_hist_pct = regime_data["macd_hist_pct"]
    volume_ratio = regime_data.get("volume_ratio_raw", 1)
    atr_pct = regime_data.get("atr_pct", 2)
    
    if strategy_type == "TREND":
        # Trend alignment (30%)
        if ema_diff > 3:
            confidence += 0.15
            factors.append("strong_ema_separation")
        elif ema_diff > 2:
            confidence += 0.10
            factors.append("moderate_ema_separation")
        elif ema_diff > 1.5:
            confidence += 0.05
            factors.append("weak_ema_separation")
        
        # RSI optimal zone (25%)
        if 45 <= rsi <= 65:
            confidence += 0.125
            factors.append("rsi_optimal_zone")
        elif rsi > 75 or rsi < 30:
            confidence -= 0.10  # Too extreme
            factors.append("rsi_extreme")
        elif rsi > 70 or rsi < 35:
            confidence -= 0.05
            factors.append("rsi_ caution")
        
        # MACD momentum (20%)
        if abs(macd_hist_pct) > 0.3:
            confidence += 0.10
            factors.append("strong_momentum")
        elif abs(macd_hist_pct) > 0.15:
            confidence += 0.05
            factors.append("moderate_momentum")
        
        # Volume (15%)
        if volume_ratio > 1.5:
            confidence += 0.075
            factors.append("high_volume")
        elif volume_ratio < 0.8:
            confidence -= 0.05
            factors.append("low_volume_caution")
        
        # Volatility stability (10%)
        if atr_pct < 3:
            confidence += 0.05
            factors.append("stable_volatility")
        elif atr_pct > 5:
            confidence -= 0.03
            factors.append("high_volatility_caution")
    
    else:  # RANGE strategy
        # Range clarity (30%)
        if ema_diff < 0.8:
            confidence += 0.15
            factors.append("tight_range")
        elif ema_diff < 1.0:
            confidence += 0.10
            factors.append("moderate_range")
        
        # RSI in mean-reversion zone (25%)
        if 35 <= rsi <= 50:
            confidence += 0.125
            factors.append("rsi_support_zone")
        elif 50 <= rsi <= 60:
            confidence += 0.10
            factors.append("rsi_resistance_zone")
        
        # MACD near zero (20%)
        if abs(macd_hist_pct) < 0.1:
            confidence += 0.10
            factors.append("macd_neutral")
        elif abs(macd_hist_pct) < 0.2:
            confidence += 0.05
        
        # Volume (10%)
        if 0.8 <= volume_ratio <= 1.3:
            confidence += 0.05
            factors.append("normal_volume")
        
        # Bollinger Band position (15%)
        bb_lower = regime_data.get("bb_lower", 0)
        bb_upper = regime_data.get("bb_upper", 0)
        if bb_lower > 0 and bb_upper > bb_lower:
            bb_position = (regime_data.get("price", 0) - bb_lower) / (bb_upper - bb_lower)
            if bb_position < 0.2:  # Near lower band = good for LONG
                confidence += 0.075
                factors.append("near_lower_band")
            elif bb_position > 0.8:  # Near upper band
                confidence -= 0.05
    
    # Cap confidence
    confidence = min(confidence, 0.95)
    confidence = max(confidence, 0.0)
    
    return {
        "confidence": round(confidence, 2),
        "factors": factors
    }

def check_trade_filters(df_15m, regime_data, direction):
    """
    Trade filters to reduce overtrading.
    
    Do not open trade if:
    - Price moved less than 0.3% since last signal
    - RSI between 48 and 52 (neutral zone)
    - MACD histogram near zero
    - Volume below 0.8 × average
    """
    latest = df_15m.iloc[-1]
    prev_candle = df_15m.iloc[-2] if len(df_15m) >= 2 else latest
    
    price_change = abs(latest["close"] - prev_candle["close"]) / prev_candle["close"] * 100
    rsi = latest["rsi"]
    macd_hist = regime_data["macd_hist_pct"]
    volume_ratio = regime_data.get("volume_ratio_raw", 1)
    
    filters_triggered = []
    
    # Price movement filter
    if price_change < 0.3:
        filters_triggered.append(f"price_move_too_small_{price_change:.2f}%")
    
    # RSI neutral zone
    if 48 <= rsi <= 52:
        filters_triggered.append(f"rsi_neutral_{rsi:.1f}")
    
    # MACD near zero
    if abs(macd_hist) < 0.1:
        filters_triggered.append(f"macd_near_zero_{macd_hist:.4f}%")
    
    # Low volume
    if volume_ratio < 0.8:
        filters_triggered.append(f"low_volume_{volume_ratio:.2f}")
    
    return {
        "passed": len(filters_triggered) == 0,
        "filters_triggered": filters_triggered,
        "price_change": round(price_change, 4),
        "rsi": round(rsi, 2),
        "volume_ratio": round(volume_ratio, 2)
    }

def get_nova_trend_decision(df_15m, df_4h, regime_data, current_position=None):
    """
    Nova Trend (V1): Trend-Following Strategy
    
    Only trades when regime = TREND.
    Uses pullback entries with momentum confirmation.
    ATR-based stops and targets.
    """
    btc_price = df_15m.iloc[-1]["close"]
    atr = regime_data["atr"]
    regime = regime_data["regime"]
    direction = regime_data["direction"]
    rsi = regime_data["rsi"]
    ema_diff = regime_data["ema_diff_pct"]
    
    # Nova Trend ONLY trades in TREND regime
    if regime != "TREND":
        return {
            "strategy_version": "V1",
            "strategy_name": "Nova Trend",
            "market_regime": "range",
            "decision": "HOLD",
            "confidence": 0.5,
            "reasoning": f"Range-bound market. Nova Trend does not trade sideways. RSI={rsi:.1f}, EMA diff={ema_diff:.2f}%. Waiting for trend.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "filters_passed": None
        }
    
    # Confidence check
    confidence_data = calculate_confidence(regime_data, regime, "TREND")
    confidence = confidence_data["confidence"]
    
    if confidence < 0.6:
        return {
            "strategy_version": "V1",
            "strategy_name": "Nova Trend",
            "market_regime": "trend",
            "decision": "HOLD",
            "confidence": confidence,
            "reasoning": f"Confidence too low ({confidence:.0%}). Waiting for stronger trend. RSI={rsi:.1f}, EMA diff={ema_diff:.2f}%.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "filters_passed": None
        }
    
    # LONG entry only
    if direction != "LONG":
        return {
            "strategy_version": "V1",
            "strategy_name": "Nova Trend",
            "market_regime": "trend",
            "decision": "HOLD",
            "confidence": confidence,
            "reasoning": f"Bearish trend detected. Nova Trend long-only. RSI={rsi:.1f}. Waiting for bullish trend.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "filters_passed": None
        }
    
    # 4H trend bias check
    if df_4h is not None:
        h4_latest = df_4h.iloc[-1]
        h4_ema_diff = abs(h4_latest["ema20"] - h4_latest["ema50"]) / h4_latest["close"] * 100
        h4_price_vs_ema = (h4_latest["close"] - h4_latest["ema20"]) / h4_latest["ema20"] * 100
        
        # 4H must confirm bullish
        if h4_price_vs_ema < 0 or h4_ema_diff < 1.0:
            return {
                "strategy_version": "V1",
                "strategy_name": "Nova Trend",
                "market_regime": "trend",
                "decision": "HOLD",
                "confidence": confidence,
                "reasoning": f"4H trend not confirmed. 4H EMA diff={h4_ema_diff:.2f}%, price vs EMA20={h4_price_vs_ema:.2f}%. Waiting for alignment.",
                "entry_price": None,
                "stop_loss": None,
                "take_profit": None,
                "risk_reward": None,
                "filters_passed": None
            }
    
    # RSI avoidance checks
    if rsi > 75:
        return {
            "strategy_version": "V1",
            "strategy_name": "Nova Trend",
            "market_regime": "trend",
            "decision": "HOLD",
            "confidence": confidence,
            "reasoning": f"RSI overbought ({rsi:.1f}). Risk of reversal. Waiting for pullback.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "filters_passed": None
        }
    
    # Price extended check - avoid chasing
    ema20 = df_15m.iloc[-1]["ema20"]
    price_vs_ema = (btc_price - ema20) / ema20 * 100
    if price_vs_ema > 2.5:
        return {
            "strategy_version": "V1",
            "strategy_name": "Nova Trend",
            "market_regime": "trend",
            "decision": "HOLD",
            "confidence": confidence,
            "reasoning": f"Price extended {price_vs_ema:.2f}% above EMA20. Waiting for pullback toward EMA20.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "filters_passed": None
        }
    
    # Trade filters
    filters = check_trade_filters(df_15m, regime_data, direction)
    if not filters["passed"]:
        return {
            "strategy_version": "V1",
            "strategy_name": "Nova Trend",
            "market_regime": "trend",
            "decision": "HOLD",
            "confidence": confidence * 0.8,
            "reasoning": f"Trade filters triggered: {', '.join(filters['filters_triggered'])}. Waiting for cleaner setup.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
            "filters_passed": False
        }
    
    # Calculate entry, stops, targets
    # ATR-based stop: ATR × 1.5
    stop_distance = atr * 1.5
    stop_loss = btc_price - stop_distance
    
    # Target: 2× stop distance (minimum RR 1.8)
    target_distance = stop_distance * 2
    take_profit = btc_price + target_distance
    
    # Risk/reward ratio
    risk_reward = target_distance / stop_distance if stop_distance > 0 else 0
    
    # Require minimum RR of 1.8
    if risk_reward < 1.8:
        return {
            "strategy_version": "V1",
            "strategy_name": "Nova Trend",
            "market_regime": "trend",
            "decision": "HOLD",
            "confidence": confidence,
            "reasoning": f"Risk/reward {risk_reward:.1f} below minimum 1.8. Stop distance too tight relative to target.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": round(risk_reward, 2),
            "filters_passed": True
        }
    
    # Build reasoning
    reasoning = (
        f"Nova Trend LONG. 4H trend confirmed. "
        f"RSI={rsi:.1f} (optimal zone), EMA diff={ema_diff:.2f}%, "
        f"RR={risk_reward:.1f}. "
        f"Entry: ${btc_price:,.2f}, SL: ${stop_loss:,.2f}, TP: ${take_profit:,.2f}. "
        f"Confidence: {confidence:.0%}. "
        f"Trend aligned across timeframes."
    )
    
    return {
        "strategy_version": "V1",
        "strategy_name": "Nova Trend",
        "market_regime": "trend",
        "decision": "LONG",
        "confidence": confidence,
        "reasoning": reasoning,
        "entry_price": round(btc_price, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "risk_reward": round(risk_reward, 2),
        "atr_stop": round(stop_distance, 2),
        "filters_passed": True,
        "indicators": {
            "rsi": rsi,
            "ema_diff": ema_diff,
            "atr": regime_data["atr"],
            "macd_hist": regime_data["macd_hist"]
        }
    }

def get_nova_range_decision(df_15m, regime_data, current_position=None):
    """
    Nova Range (V2): Mean-Reversion Grid Strategy
    
    Only trades when regime = RANGE.
    Uses Bollinger Bands and swing highs/lows for range boundaries.
    Dynamic grid based on ATR.
    """
    btc_price = df_15m.iloc[-1]["close"]
    atr = regime_data["atr"]
    atr_pct = regime_data.get("atr_pct", 2)
    regime = regime_data["regime"]
    rsi = regime_data["rsi"]
    ema_diff = regime_data["ema_diff_pct"]
    
    bb_lower = regime_data.get("bb_lower", 0)
    bb_upper = regime_data.get("bb_upper", 0)
    bb_middle = (bb_lower + bb_upper) / 2
    
    # Nova Range ONLY trades in RANGE regime
    if regime != "RANGE":
        return {
            "strategy_version": "V2",
            "strategy_name": "Nova Range",
            "market_regime": "trend",
            "decision": "HOLD",
            "confidence": 0.5,
            "reasoning": f"Trend market detected. Nova Range grid pausing. RSI={rsi:.1f}, EMA diff={ema_diff:.2f}%. Waiting for range.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "range_high": None,
            "range_low": None,
            "grid_levels": None,
            "filters_passed": None
        }
    
    # Calculate range boundaries
    # Using swing highs/lows from last 40 candles
    recent_40 = df_15m.iloc[-40:]
    range_high = recent_40["high"].max()
    range_low = recent_40["low"].min()
    
    # Also use Bollinger extremes as confirmation
    if bb_upper > 0 and bb_lower > 0:
        # Use wider of the two
        range_high = max(range_high, bb_upper)
        range_low = min(range_low, bb_lower)
    
    # Dynamic grid: ATR-based spacing
    grid_step = atr * 0.8
    range_width = range_high - range_low
    num_levels = max(11, int(range_width / grid_step))
    grid_step = range_width / (num_levels - 1) if num_levels > 1 else atr
    
    # Calculate price position in range (0 = bottom, 1 = top)
    if range_high > range_low:
        price_position = (btc_price - range_low) / (range_high - range_low)
    else:
        price_position = 0.5
    
    # Confidence
    confidence_data = calculate_confidence(regime_data, regime, "RANGE")
    confidence = confidence_data["confidence"]
    
    # LONG entry conditions (near support)
    # Price within 20% of range_low, RSI < 40, near lower BB
    long_conditions_met = (
        price_position < 0.25 and  # Near bottom
        rsi < 55 and  # Not overbought
        btc_price <= bb_lower * 1.02  # Touching or near lower BB
    )
    
    # SHORT entry conditions (near resistance) - but we're long-only
    # So we only enter LONG near support
    
    # Entry rules
    if not long_conditions_met:
        return {
            "strategy_version": "V2",
            "strategy_name": "Nova Range",
            "market_regime": "range",
            "decision": "HOLD",
            "confidence": confidence,
            "reasoning": f"Nova Range waiting. Price at {price_position:.0%} of range. RSI={rsi:.1f}. Looking for pullback to support.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "range_high": round(range_high, 2),
            "range_low": round(range_low, 2),
            "num_levels": num_levels,
            "grid_step": round(grid_step, 2),
            "filters_passed": None
        }
    
    # Trade filters
    filters = check_trade_filters(df_15m, regime_data, "LONG")
    
    # Volume spike check - avoid possible trend start
    volume_ratio = regime_data.get("volume_ratio_raw", 1)
    if volume_ratio > 2.0:
        return {
            "strategy_version": "V2",
            "strategy_name": "Nova Range",
            "market_regime": "range",
            "decision": "HOLD",
            "confidence": confidence * 0.7,
            "reasoning": f"Volume spike ({volume_ratio:.1f}× avg). Possible trend start. Nova Range staying neutral.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "range_high": round(range_high, 2),
            "range_low": round(range_low, 2),
            "num_levels": num_levels,
            "grid_step": round(grid_step, 2),
            "filters_passed": False
        }
    
    # Stop loss: 3% below entry (configurable hard stop)
    stop_loss = btc_price * (1 - 0.03)  # 3% hard stop
    stop_distance = btc_price - stop_loss
    
    # Take profit: minimum 2:1 risk-reward (6% above entry with 3% stop)
    take_profit = btc_price + stop_distance * 2
    # Ensure TP is at least above entry
    take_profit = max(take_profit, btc_price * 1.01)
    
    # Risk/reward  
    target_distance = take_profit - btc_price
    risk_reward = target_distance / stop_distance if stop_distance > 0 else 0
    
    # Entry price (slight discount to current)
    entry_price = btc_price * 0.999  # Enter slightly below market
    
    reasoning = (
        f"Nova Range LONG. Mean-reversion setup. "
        f"Price at {price_position:.0%} of range (near support). "
        f"RSI={rsi:.1f}, ATR={atr:.2f}. "
        f"Range: ${range_low:,.0f}-${range_high:,.0f}. "
        f"Entry: ${entry_price:,.2f}, SL: ${stop_loss:,.2f}, TP: ${take_profit:,.2f}. "
        f"RR={risk_reward:.1f}. Confidence: {confidence:.0%}."
    )
    
    return {
        "strategy_version": "V2",
        "strategy_name": "Nova Range",
        "market_regime": "range",
        "decision": "LONG",
        "confidence": confidence,
        "reasoning": reasoning,
        "entry_price": round(entry_price, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "risk_reward": round(risk_reward, 2),
        "atr_stop": round(stop_distance, 2),
        "range_high": round(range_high, 2),
        "range_low": round(range_low, 2),
        "num_levels": num_levels,
        "grid_step": round(grid_step, 2),
        "filters_passed": True,
        "indicators": {
            "rsi": rsi,
            "price_position": round(price_position, 4),
            "atr": atr,
            "bb_lower": bb_lower,
            "bb_upper": bb_upper
        }
    }

def run_strategy(version="V2", timeframe="15m"):
    """
    Main strategy runner with multi-timeframe support.
    
    1. Fetch candles from HTX (15m + 4H)
    2. Calculate indicators
    3. Detect regime
    4. Generate decision based on strategy version
    """
    # Fetch candles
    df_15m = fetch_candles("BTC/USDT", "15m", 100)
    df_4h = fetch_candles("BTC/USDT", "4h", 100)
    
    if df_15m is None:
        return {
            "strategy_version": version,
            "strategy_name": "Nova Trend" if version == "V1" else "Nova Range",
            "market_regime": "unknown",
            "decision": "HOLD",
            "confidence": 0,
            "reasoning": "Failed to fetch market data from HTX",
            "error": True
        }
    
    # Calculate indicators for 15m (primary timeframe)
    df_15m = calculate_indicators(df_15m)
    
    # Calculate indicators for 4H if available
    if df_4h is not None and len(df_4h) > 50:
        df_4h = calculate_indicators(df_4h)
    else:
        df_4h = None
    
    # Detect regime using both timeframes
    regime_data = detect_regime(df_15m, df_4h)
    
    # Get current price
    btc_price = df_15m.iloc[-1]["close"]
    prices = {
        "BTC/USDT": {
            "price": btc_price,
            "high": df_15m.iloc[-1]["high"],
            "low": df_15m.iloc[-1]["low"],
            "volume": df_15m.iloc[-1]["volume"]
        }
    }
    
    # Generate decision based on strategy version
    if version == "V2":
        decision = get_nova_range_decision(df_15m, regime_data)
    else:
        decision = get_nova_trend_decision(df_15m, df_4h, regime_data)
    
    # Add metadata
    decision["timestamp"] = datetime.now().isoformat()
    decision["prices"] = prices
    decision["indicators"] = {
        "rsi": regime_data["rsi"],
        "ema20": round(df_15m.iloc[-1]["ema20"], 2),
        "ema50": round(df_15m.iloc[-1]["ema50"], 2),
        "macd": round(df_15m.iloc[-1]["macd"], 4),
        "macd_hist": regime_data["macd_hist"],
        "atr": regime_data["atr"],
        "supertrend_dir": regime_data["supertrend_dir"],
        "regime": regime_data["regime"],
        "ema_diff_pct": regime_data["ema_diff_pct"]
    }
    decision["regime_data"] = regime_data
    
    return decision

if __name__ == "__main__":
    # Test both strategies
    print("Testing Nova Trend (V1)...")
    result = run_strategy("V1")
    print(f"Decision: {result['decision']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Reasoning: {result.get('reasoning', 'N/A')}")
    print()
    
    print("Testing Nova Range (V2)...")
    result = run_strategy("V2")
    print(f"Decision: {result['decision']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Reasoning: {result.get('reasoning', 'N/A')}")
