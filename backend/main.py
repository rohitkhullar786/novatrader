from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import requests
import os
import json
import re
import asyncio
from datetime import datetime

def calculate_holding_time(timestamp):
    """Calculate holding time string from ISO timestamp"""
    if not timestamp:
        return None
    try:
        start = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        end = datetime.now()
        delta = end - start
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except:
        return None

from strategy import run_strategy, fetch_candles, calculate_indicators, detect_regime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "sk-cp-vEIFab8n5QijpfuWPnrWqpN18xbYczi4w_VlcagK0EtSZjJ3gRwrdYQdoq0KKQL9wXZdN0ctxuG01cD5nIuvLS9k7AaLl0JFP8LmOP9h1w816LAJhOWPULA")
MINIMAX_URL = "https://api.minimax.io/anthropic/v1/messages"

# OpenRouter config (primary) — using local proxy to opencode-go
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "") or open("/tmp/proxy-apikey.txt").read().strip()
OPENROUTER_URL = "https://opencode.ai/zen/go/v1/chat/completions"
PRIMARY_MODEL = "deepseek-v4-flash"
MODEL = PRIMARY_MODEL  # Use OpenRouter primary model by default

def call_ai_model(prompt, max_tokens=500, force_model=None):
    """Call AI model. Use force_model to specify model, or use default fallback chain."""
    
    # If a specific model is forced, use it directly
    if force_model:
        if "minimax" in force_model.lower():
            # Use MiniMax direct
            try:
                headers = {
                    "Authorization": f"Bearer {MINIMAX_API_KEY}",
                    "Content-Type": "application/json",
                    "x-api-key": MINIMAX_API_KEY
                }
                payload = {
                    "model": "MiniMax-M2.7",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens
                }
                response = requests.post(MINIMAX_URL, headers=headers, json=payload, timeout=30)
                data = response.json()
                content = data.get("content", [])
                for item in content:
                    if item.get("type") == "text":
                        return {
                            "content": item.get("text", "").strip(),
                            "model": "MiniMax-M2.7"
                        }
            except Exception as e:
                print(f"MiniMax call failed: {e}")
                return {"content": "Unable to generate reasoning", "model": "Unknown"}
        else:
            # Use OpenRouter with specified model
            try:
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5181",
                    "X-Title": "NovaTrader"
                }
                payload = {
                    "model": force_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens
                }
                response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
                data = response.json()
                if response.status_code == 200 and data.get("choices"):
                    return {
                        "content": (data["choices"][0]["message"].get("content") or data["choices"][0]["message"].get("reasoning_content") or "").strip(),
                        "model": force_model
                    }
                else:
                    print(f"OpenRouter error: {data}")
            except Exception as e:
                print(f"OpenRouter call failed: {e}")
            return {"content": "Unable to generate reasoning", "model": "Unknown"}
    
    # Default: Use PRIMARY_MODEL via OpenRouter ONLY (no fallback to MiniMax)
    if OPENROUTER_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5181",
                "X-Title": "NovaTrader"
            }
            payload = {
                "model": PRIMARY_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            data = response.json()
            if response.status_code == 200 and data.get("choices"):
                return {
                    "content": (data["choices"][0]["message"].get("content") or data["choices"][0]["message"].get("reasoning_content") or "").strip(),
                    "model": PRIMARY_MODEL
                }
            else:
                print(f"OpenRouter error: {data}")
        except Exception as e:
            print(f"OpenRouter call failed: {e}")
    
    return {"content": "Unable to generate reasoning", "model": "Unknown"}


# Cache for HTX data (5 second TTL)
import time as time_module
_htx_cache = {'prices': None, 'balance': None, 'open_orders': None, 'cache_time': 0}
CACHE_TTL = 5  # seconds

def get_cached_htx_data():
    global _htx_cache
    now = time_module.time()
    if now - _htx_cache['cache_time'] < CACHE_TTL and _htx_cache['prices'] is not None:
        return _htx_cache
    # Refresh cache
    try:
        tickers = htx_live.fetch_tickers(['BTC/USDT', 'BTC/USDD', 'TRX/USDT'])
        # Convert tickers to same format as fetch_ticker for compatibility
        prices = {}
        for symbol, ticker in tickers.items():
            if isinstance(ticker, dict):
                prices[symbol] = {
                    'price': ticker.get('last', 0),
                    'change': ticker.get('change', 0),
                    'changePercent': ticker.get('changePercent', 0),
                    'high': ticker.get('high', 0),
                    'low': ticker.get('low', 0),
                    'volume': ticker.get('volume', 0)
                }
            else:
                prices[symbol] = {'price': ticker, 'change': 0, 'changePercent': 0, 'high': 0, 'low': 0, 'volume': 0}
        balance = htx_live.fetch_balance()
        open_orders = htx_live.fetch_open_orders('BTC/USDD')
        _htx_cache = {
            'prices': prices,
            'balance': balance,
            'open_orders': open_orders,
            'cache_time': now
        }
    except Exception as e:
        print(f"HTX API error: {e}")
        if _htx_cache['prices'] is not None:
            return _htx_cache
    return _htx_cache

# HTX API credentials for live trading
HTX_API_KEY = "eefbb713-c797ccd2-fr2wer5t6y-2278b"
HTX_SECRET = "591dd418-b4f99777-2e1c848a-a7f65"

# HTX exchange client for live balance
import ccxt
htx_live = ccxt.htx({
    'apiKey': HTX_API_KEY,
    'secret': HTX_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'},
})

def get_live_balance():
    """Get live HTX balance"""
    try:
        balance = htx_live.fetch_balance()
        return {
            'BTC': balance.get('BTC', {}).get('free', 0),
            'USDD': balance.get('USDD', {}).get('free', 0),
            'TRX': balance.get('TRX', {}).get('free', 0),
        }
    except Exception as e:
        print(f"Error fetching live balance: {e}")
        return {'BTC': 0, 'USDD': 0, 'TRX': 0}

def place_live_buy(entry_price, amount):
    """Place a live BUY order on HTX
    Returns: (buy_order_id, fill_info) or (None, None) on failure
    Note: Stop loss is handled by the separate price_monitor_loop, NOT on HTX
    """
    try:
        # Place BUY limit order slightly BELOW current price for better fill price
        # This gives us a better entry if the price dips to our level
        buy_price = entry_price  # Place at signal price
        buy_order = htx_live.create_limit_buy_order('BTC/USDD', amount, buy_price)
        buy_order_id = buy_order['id']
        print(f"Live BUY order placed: ID={buy_order_id}, Price=${buy_price}, Amount={amount}")
        
        # Check if order was immediately filled (could happen with market orders or if limit price was hit)
        try:
            filled_order = htx_live.fetch_order(buy_order_id, 'BTC/USDD')
            if filled_order.get('status') in ['closed', 'filled']:
                print(f"Order {buy_order_id} was immediately filled!")
                return (buy_order_id, {
                    'filled': True,
                    'fill_price': filled_order.get('average', filled_order.get('price', buy_price)),
                    'fill_amount': filled_order.get('filled', amount),
                    'order': filled_order
                })
        except Exception as e:
            print(f"Could not check fill status for {buy_order_id}: {e}")
        
        return (buy_order_id, {'filled': False, 'fill_price': buy_price, 'fill_amount': 0, 'order': buy_order})
    except Exception as e:
        print(f"Error placing live buy: {e}")
        return (None, None)

def place_live_sell(market='market', amount=None, price=None):
    """Place a live SELL order to close position
    market: 'market' or 'limit'
    """
    try:
        if amount is None:
            bal = get_live_balance()
            amount = bal['BTC']
        
        if market == 'market':
            order = htx_live.create_market_sell_order('BTC/USDD', amount)
        else:
            order = htx_live.create_limit_sell_order('BTC/USDD', amount, price)
        print(f"Live SELL order placed: ID={order['id']}, Market={market}, Amount={amount}, Price={price}")
        return order['id']
    except Exception as e:
        print(f"Error placing live sell: {e}")
        return None

def cancel_live_stop_loss(sl_order_id):
    """Cancel a pending stop loss order"""
    try:
        htx_live.cancel_order(sl_order_id, 'BTC/USDD')
        print(f"Canceled stop loss order: ID={sl_order_id}")
        return True
    except Exception as e:
        print(f"Error canceling SL order {sl_order_id}: {e}")
        return False

def update_stop_loss(new_stop_price, amount):
    """Cancel existing SL and place new one at higher price (for trailing stop)"""
    try:
        # HTX doesn't support modifying orders directly, so we cancel and recreate
        order = htx_live.create_stop_loss_order('BTC/USDD', 'market', 'sell', amount, None, new_stop_price)
        print(f"Updated stop loss to: ${new_stop_price}, New ID={order['id']}")
        return order['id']
    except Exception as e:
        print(f"Error updating stop loss: {e}")
        return None

PAPER_BALANCE = 10000.0
LEVERAGE = 1  # No leverage for spot trading

# New dynamic position sizing
BASE_POSITION_SIZE_PCT = 0.30  # 30% of balance - confidence 0.7-0.8
HIGH_CONFIDENCE_SIZE_PCT = 0.50  # 50% if confidence >= 0.8
LOW_CONFIDENCE_SIZE_PCT = 0.20  # 20% if confidence 0.5-0.6

# Trailing stop (new: +2% activates)
TRAILING_STOP_ACTIVATION = 0.02  # +2% profit activates trailing stop
TRAILING_STOP_TRAIL_PCT = 0.012  # Trail 1.2% below high
STOP_LOSS_PCT = 0.03  # 3% stop loss
TAKE_PROFIT_PCT = 0.06  # 6% take profit (2:1 R:R with 3% stop)

# Live trading flag - set to True to enable real HTX trading
USE_LIVE_TRADING = True
AI_ONLY_MODE = False  # Live trading enabled

# Minimum trade amount in USDD
MIN_TRADE_VALUE_USDD = 10

# Minimum confidence to trade
MIN_CONFIDENCE_TO_TRADE = 0.6

# Risk/reward minimum
MIN_RISK_REWARD = 1.2

# Max decisions to store per strategy (keep memory in check)
MAX_DECISIONS = 100

STORAGE_FILE = os.path.join(os.path.dirname(__file__), 'storage.json')

def save_storage():
    """Persist storage to disk"""
    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump(storage, f)
    except Exception as e:
        print(f"Warning: Failed to save storage: {e}")

def load_storage():
    """Load storage from disk if exists"""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r') as f:
                loaded = json.load(f)
                for v in ['V1', 'V2']:
                    if v in loaded and isinstance(loaded[v], dict):
                        for key in ['balance', 'trades', 'positions', 'decisions', 'equity_curve']:
                            if key not in loaded[v]:
                                loaded[v][key] = [] if key in ['trades', 'decisions', 'equity_curve'] else ({} if key == 'positions' else PAPER_BALANCE)
                storage.update(loaded)
                print(f"Loaded storage from {STORAGE_FILE}")
        except Exception as e:
            print(f"Warning: Failed to load storage: {e}")

# In-memory storage
storage = {
    'V1': {'balance': PAPER_BALANCE, 'trades': [], 'positions': {}, 'decisions': [], 'equity_curve': []},
    'V2': {'balance': PAPER_BALANCE, 'trades': [], 'positions': {}, 'decisions': [], 'equity_curve': []}
}

# Load persisted storage on startup
load_storage()

def calculate_unrealized_pnl(positions, btc_price):
    """Calculate total unrealized P&L from open positions"""
    total_pnl = 0
    for pos in positions.values():
        if pos['side'] == 'LONG':
            pnl = pos['position_size'] * (btc_price - pos['entry_price']) / pos['entry_price']
        elif pos['side'] == 'SHORT':
            pnl = pos['position_size'] * (pos['entry_price'] - btc_price) / pos['entry_price']
        total_pnl += pnl
    return total_pnl

def calculate_equity(version, btc_price):
    """Calculate total equity using LIVE HTX balance"""
    live_bal = get_live_balance()
    usdd = live_bal.get('USDD', 0)
    btc_val = live_bal.get('BTC', 0) * btc_price
    total_live = usdd + btc_val
    
    # Also add any paper tracking if exists
    s = storage[version]
    unrealized_pnl = calculate_unrealized_pnl(s['positions'], btc_price)
    return total_live + unrealized_pnl

def get_used_margin(positions):
    """Calculate total used margin from open positions (excludes pending orders)"""
    return sum(pos.get('margin', 0) for pos in positions.values() if pos.get('status') != 'pending')

def get_free_balance(version):
    """Calculate free balance using LIVE HTX balance minus used margin"""
    live_bal = get_live_balance()
    usdd = live_bal.get('USDD', 0)
    s = storage[version]
    used_margin = get_used_margin(s['positions'])
    return usdd - used_margin

def get_position_size_pct(confidence):
    """Determine position size based on confidence - 4 tiers"""
    if confidence >= 0.80:
        return HIGH_CONFIDENCE_SIZE_PCT  # 50%
    elif confidence >= 0.70:
        return BASE_POSITION_SIZE_PCT  # 40% (was 30%)
    elif confidence >= 0.60:
        return 0.30  # 30% - new tier
    else:
        return LOW_CONFIDENCE_SIZE_PCT  # 20%

headers = {
    "Authorization": f"Bearer {MINIMAX_API_KEY}",
    "Content-Type": "application/json",
    "x-api-key": MINIMAX_API_KEY,
}

def fetch_htx_prices():
    """Fetch current prices from HTX"""
    from strategy import htx
    result = {}
    for symbol in ["BTC/USDT", "TRX/USDT", "BTC/USDD"]:
        try:
            ticker = htx.fetch_ticker(symbol)
            result[symbol] = {
                "price": ticker["last"],
                "change": ticker["change"],
                "changePercent": ticker["percentage"],
                "high": ticker["high"],
                "low": ticker["low"],
                "volume": ticker["baseVolume"]
            }
        except Exception as e:
            result[symbol] = {"error": str(e)}
    return result

def get_ai_reasoning(decision, prices, model=None):
    """Use AI to generate human-readable reasoning for the decision"""
    btc_price = prices.get('BTC/USDT', {}).get('price', 0)
    strategy = decision.get('strategy_version', 'V2')
    strategy_name = decision.get('strategy_name', 'Nova Range')
    regime = decision.get('market_regime', 'unknown')
    dec = decision.get('decision', 'HOLD')
    indicators = decision.get('indicators', {})
    rsi = indicators.get('rsi', 0)
    ema20 = indicators.get('ema20', 0)
    ema50 = indicators.get('ema50', 0)
    atr = indicators.get('atr', 0)
    confidence = decision.get('confidence', 0)
    rr = decision.get('risk_reward', 0)
    stop_loss = decision.get('stop_loss', 0)
    take_profit = decision.get('take_profit', 0)
    
    entry_price = decision.get('entry_price') or btc_price
    stop_loss_price = stop_loss if stop_loss else 0
    take_profit_price = take_profit if take_profit else 0
    rr_val = rr if rr else 0
    
    prompt = f"""You are a crypto trading analyst. Output ONLY the final analysis — do NOT include your thinking process, reasoning steps, or self-talk. Just the polished explanation.

Strategy: {strategy_name} | BTC: ${btc_price:,.2f} | Regime: {regime.upper()} | Decision: {dec} | Confidence: {confidence:.0%}
RSI: {rsi:.1f} | EMA20: ${ema20:,.2f} | EMA50: ${ema50:,.2f} | ATR: ${atr:.2f}
Entry: ${entry_price:,.2f} | SL: ${stop_loss_price:,.2f} | TP: ${take_profit_price:,.2f} | R:R: {rr_val:.1f}

Write exactly 1-2 sentences explaining the decision. Do not restate the data — explain the WHY.
"""
    
    return call_ai_model(prompt, max_tokens=500, force_model=model)

def check_pending_orders():
    """Check if any pending orders on HTX have been filled and update positions accordingly"""
    try:
        # Get all open orders from HTX
        open_orders = htx_live.fetch_open_orders('BTC/USDD')
        open_order_ids = {str(o['id']): o for o in open_orders}
        
        for version in ['V1', 'V2']:
            for symbol, pos in list(storage[version]['positions'].items()):
                pending_id = pos.get('pending_order_id')
                if pending_id and str(pending_id) in open_order_ids:
                    # Order is still pending
                    order = open_order_ids[str(pending_id)]
                    if order.get('filled', 0) > 0:
                        # Order was partially or fully filled!
                        fill_price = order.get('average', order.get('price'))
                        fill_amount = order.get('filled', 0)
                        print(f"PENDING ORDER FILLED: {pending_id} - filled {fill_amount} BTC at {fill_price}")
                        # Update position with fill info
                        pos['status'] = 'open'
                        pos['entry_price'] = fill_price
                        pos['quantity'] = fill_amount
                        pos['margin'] = fill_amount * fill_price
                        pos['position_size'] = fill_amount * fill_price
                        pos['on_htx'] = True
                        del pos['pending_order_id']
                        del pos['pending_entry_price']
                        del pos['limit_price']
                        # Record equity snapshot
                        prices = fetch_htx_prices()
                        record_equity_snapshot(version, prices)
                elif pending_id and str(pending_id) not in open_order_ids:
                    # Order is no longer in open orders - it was filled or cancelled
                    # Check the order status directly
                    try:
                        order = htx_live.fetch_order(str(pending_id), 'BTC/USDD')
                        if order.get('status') in ['closed', 'filled']:
                            fill_price = order.get('average', order.get('price', pos.get('limit_price', pos.get('entry_price'))))
                            fill_amount = order.get('filled', pos.get('quantity', 0))
                            if fill_amount > 0:
                                print(f"PENDING ORDER FILLED (via fetch): {pending_id} - filled {fill_amount} BTC at {fill_price}")
                                pos['status'] = 'open'
                                pos['entry_price'] = fill_price
                                pos['quantity'] = fill_amount
                                pos['margin'] = fill_amount * fill_price
                                pos['position_size'] = fill_amount * fill_price
                                pos['on_htx'] = True
                                if 'pending_order_id' in pos:
                                    del pos['pending_order_id']
                                if 'pending_entry_price' in pos:
                                    del pos['pending_entry_price']
                                if 'limit_price' in pos:
                                    del pos['limit_price']
                                prices = fetch_htx_prices()
                                record_equity_snapshot(version, prices)
                        else:
                            # Order was cancelled
                            print(f"PENDING ORDER CANCELLED: {pending_id} - removing position")
                            del storage[version]['positions'][symbol]
                    except Exception as e:
                        print(f"Error checking order {pending_id}: {e}")
    except Exception as e:
        print(f"Error checking pending orders: {e}")

def check_positions_for_stops(version, prices):
    """Check open positions for stop loss, take profit, or trailing stop hits"""
    s = storage[version]
    btc_price = prices.get('BTC/USDT', {}).get('price', 0)
    
    if btc_price == 0:
        return []
    
    closed_trades = []
    positions_to_close = []
    
    for symbol, pos in s['positions'].items():
        if pos['side'] not in ['LONG', 'SHORT']:
            continue
        
        entry_price = pos['entry_price']
        current_price = btc_price
        stop_loss = pos.get('stop_loss_price', 0)
        take_profit = pos.get('take_profit_price', 0)
        
        close_reason = None
        
        if pos['side'] == 'LONG':
            # Update highest price and trail the stop upward
            prev_highest = pos.get('highest_price')
            if prev_highest is None:
                prev_highest = entry_price
            if current_price > prev_highest:
                pos['highest_price'] = current_price
                
                # If trailing stop is already active, UPDATE it upward
                if pos.get('trailing_stop_active', False):
                    new_trail_price = current_price * (1 - TRAILING_STOP_TRAIL_PCT)
                    pos['trailing_stop_price'] = new_trail_price
                    if USE_LIVE_TRADING and pos.get('live_sl_order_id'):
                        cancel_live_stop_loss(pos['live_sl_order_id'])
                        new_sl_order_id = update_stop_loss(new_trail_price, pos['quantity'])
                        pos['live_sl_order_id'] = new_sl_order_id
                        print(f"LIVE TRADING: Trailing stop UPDATED to ${new_trail_price:,.2f}")
            
            # Check stop loss
            if stop_loss > 0 and current_price <= stop_loss:
                close_reason = 'STOP_LOSS'
            # Check take profit
            elif take_profit > 0 and current_price >= take_profit:
                close_reason = 'TAKE_PROFIT'
            # Check trailing stop activation
            elif not pos.get('trailing_stop_active', False):
                profit_pct = (pos['highest_price'] - entry_price) / entry_price
                if profit_pct >= TRAILING_STOP_ACTIVATION:
                    pos['trailing_stop_active'] = True
                    # Trail 1.2% below high
                    pos['trailing_stop_price'] = pos['highest_price'] * (1 - TRAILING_STOP_TRAIL_PCT)
                    
                    # If live trading, update the stop loss order
                    if USE_LIVE_TRADING and pos.get('live_sl_order_id'):
                        new_sl_price = pos['trailing_stop_price']
                        cancel_live_stop_loss(pos['live_sl_order_id'])
                        new_sl_order_id = update_stop_loss(new_sl_price, pos['quantity'])
                        pos['live_sl_order_id'] = new_sl_order_id
                        print(f"LIVE TRADING: Trailing stop ACTIVATED! New SL: ${new_sl_price}")
            
            # Check if price hit trailing stop
            if pos.get('trailing_stop_active', False):
                trail_price = pos.get('trailing_stop_price', 0)
                if trail_price > 0 and current_price <= trail_price:
                    close_reason = 'TRAILING_STOP'
        
        elif pos['side'] == 'SHORT':
            # Update lowest price and trail the stop downward
            prev_lowest = pos.get('lowest_price')
            if prev_lowest is None:
                prev_lowest = entry_price
            if current_price < prev_lowest:
                pos['lowest_price'] = current_price
                
                # If trailing stop is already active, UPDATE it downward
                if pos.get('trailing_stop_active', False):
                    new_trail_price = current_price * (1 + TRAILING_STOP_TRAIL_PCT)
                    pos['trailing_stop_price'] = new_trail_price
                    if USE_LIVE_TRADING and pos.get('live_sl_order_id'):
                        cancel_live_stop_loss(pos['live_sl_order_id'])
                        new_sl_order_id = update_stop_loss(new_trail_price, pos['quantity'])
                        pos['live_sl_order_id'] = new_sl_order_id
                        print(f"LIVE TRADING: Short Trailing stop UPDATED to ${new_trail_price:,.2f}")
            
            # Check stop loss
            if stop_loss > 0 and current_price >= stop_loss:
                close_reason = 'STOP_LOSS'
            # Check take profit
            elif take_profit > 0 and current_price <= take_profit:
                close_reason = 'TAKE_PROFIT'
            # Check trailing stop activation
            elif not pos.get('trailing_stop_active', False):
                profit_pct = (entry_price - pos['lowest_price']) / entry_price
                if profit_pct >= TRAILING_STOP_ACTIVATION:
                    pos['trailing_stop_active'] = True
                    pos['trailing_stop_price'] = pos['lowest_price'] * (1 + TRAILING_STOP_TRAIL_PCT)
            
            # Check if price hit trailing stop
            if pos.get('trailing_stop_active', False):
                trail_price = pos.get('trailing_stop_price', 0)
                if trail_price > 0 and current_price >= trail_price:
                    close_reason = 'TRAILING_STOP'
        
        if close_reason:
            positions_to_close.append((symbol, pos, close_reason))
    
    # Close positions that hit stops
    for symbol, pos, reason in positions_to_close:
        if pos['side'] == 'LONG':
            realized_pnl = pos['position_size'] * (btc_price - pos['entry_price']) / pos['entry_price']
        else:
            realized_pnl = pos['position_size'] * (pos['entry_price'] - btc_price) / pos['entry_price']
        
        reason_texts = {
            'STOP_LOSS': f"Stop loss hit",
            'TAKE_PROFIT': f"Take profit hit",
            'TRAILING_STOP': f"Trailing stop hit"
        }
        
        trade = {
            'strategy_version': version,
            'symbol': symbol,
            'side': pos['side'],
            'entry_price': pos['entry_price'],
            'exit_price': btc_price,
            'quantity': pos['quantity'],
            'margin': pos['margin'],
            'leverage': pos.get('leverage', LEVERAGE),
            'position_size': pos['position_size'],
            'pnl': realized_pnl,
            'net_pnl': realized_pnl,
            'holding_time': calculate_holding_time(pos['timestamp']),
            'timestamp': datetime.now().isoformat(),
            'datetime': datetime.now().strftime('%b %d, %H:%M'),
            'decision': 'CLOSE',
            'reasoning': f"{reason_texts.get(reason, reason)}. BTC @ ${btc_price:,.2f}.",
            'confidence': 1.0,
            'status': 'closed',
            'close_reason': reason
        }
        
        # If live trading enabled and there was a live SL order, cancel it
        if USE_LIVE_TRADING and pos.get('live_sl_order_id'):
            cancel_live_stop_loss(pos['live_sl_order_id'])
        
        # If live trading enabled and there was a live buy order, place sell to close
        if USE_LIVE_TRADING and pos.get('live_order_id'):
            sell_order_id = place_live_sell('market', pos['quantity'])
            if sell_order_id:
                trade['live_sell_order_id'] = sell_order_id
                print(f"LIVE TRADING: Closed position via {reason}, SELL order ID: {sell_order_id}")
        
        # Don't update paper balance for live trades - HTX handles the money
        del s['positions'][symbol]
        s['trades'].insert(0, trade)
        closed_trades.append(trade)
    
    if closed_trades:
        record_equity_snapshot(version, prices)
    
    return closed_trades

def execute_paper_trade(strategy_version, decision, prices):
    """Execute paper trade based on strategy decision with dynamic position sizing"""
    s = storage[strategy_version]
    btc_price = prices.get('BTC/USDT', {}).get('price', 0)
    
    if btc_price == 0:
        return None
    
    decision_upper = decision.get('decision', 'HOLD').upper()
    symbol = 'BTC/USDT'
    
    if decision_upper == 'HOLD':
        return None
    
    # CLOSE existing position
    if decision_upper == 'CLOSE':
        if symbol in s['positions']:
            pos = s['positions'][symbol]
            
            if pos['side'] == 'LONG':
                realized_pnl = pos['position_size'] * (btc_price - pos['entry_price']) / pos['entry_price']
            else:
                realized_pnl = pos['position_size'] * (pos['entry_price'] - btc_price) / pos['entry_price']
            
            trade = {
                'strategy_version': strategy_version,
                'symbol': symbol,
                'side': pos['side'],
                'entry_price': pos['entry_price'],
                'exit_price': btc_price,
                'quantity': pos['quantity'],
                'margin': pos['margin'],
                'leverage': pos.get('leverage', LEVERAGE),
                'position_size': pos['position_size'],
                'pnl': realized_pnl,
                'net_pnl': realized_pnl,
                'holding_time': calculate_holding_time(pos['timestamp']),
                'timestamp': datetime.now().isoformat(),
                'datetime': datetime.now().strftime('%b %d, %H:%M'),
                'decision': 'CLOSE',
                'reasoning': decision.get('reasoning', ''),
                'confidence': decision.get('confidence', 0.5),
                'status': 'closed'
            }
            
            s['balance'] += pos['margin'] + realized_pnl
            del s['positions'][symbol]
            s['trades'].insert(0, trade)
            record_equity_snapshot(strategy_version, prices)
            return trade
        return None
    
    # CHECK: If position exists and direction is OPPOSITE, close it only (no shorting)
    if symbol in s['positions']:
        existing = s['positions'][symbol]
        if existing['side'] == decision_upper:
            return None
        # Opposite direction - close existing position only
        if existing['side'] == 'LONG':
            realized_pnl = existing['position_size'] * (btc_price - existing['entry_price']) / existing['entry_price']
        else:
            realized_pnl = existing['position_size'] * (existing['entry_price'] - btc_price) / existing['entry_price']
        
        trade = {
            'strategy_version': strategy_version,
            'symbol': symbol,
            'side': existing['side'],
            'entry_price': existing['entry_price'],
            'exit_price': btc_price,
            'quantity': existing['quantity'],
            'margin': existing['margin'],
            'leverage': existing['leverage'],
            'position_size': existing['position_size'],
            'pnl': realized_pnl,
            'net_pnl': realized_pnl,
            'holding_time': calculate_holding_time(existing['timestamp']),
            'timestamp': datetime.now().isoformat(),
            'datetime': datetime.now().strftime('%b %d, %H:%M'),
            'decision': 'CLOSE',
            'reasoning': f"Closing position. Signal reversed. BTC @ ${btc_price:,.2f}. (Long only mode)",
            'confidence': decision.get('confidence', 0.5),
            'status': 'closed'
        }
        
        # Place real sell order on HTX for live trading
        if USE_LIVE_TRADING and existing.get('live_order_id'):
            if existing.get('live_sl_order_id'):
                cancel_live_stop_loss(existing['live_sl_order_id'])
            sell_order_id = place_live_sell('market', existing['quantity'])
            if sell_order_id:
                trade['live_sell_order_id'] = sell_order_id
                print(f"LIVE TRADING: Reversal close, SELL order ID: {sell_order_id}")
        
        # Don't update paper balance for live trades - HTX handles the money
        del s['positions'][symbol]
        s['trades'].insert(0, trade)
        record_equity_snapshot(strategy_version, prices)
        return trade
    
    # CHECK: Minimum time between trades (5 minutes)
    last_trade_time = None
    for t in s['trades']:
        if t.get('symbol') == symbol and t.get('status') == 'closed':
            last_trade_time = datetime.fromisoformat(t['timestamp'])
            break
    
    if last_trade_time:
        time_since_last = (datetime.now() - last_trade_time).total_seconds()
        if time_since_last < 300:
            return None
    
    # BLOCK SHORT POSITIONS - Long only
    if decision_upper == 'SHORT':
        return None
    
    # BLOCK if confidence too low
    confidence = decision.get('confidence', 0.5)
    if confidence < MIN_CONFIDENCE_TO_TRADE:
        return None
    
    # BLOCK if risk/reward below minimum
    rr = decision.get('risk_reward', 0)
    if rr > 0 and rr < MIN_RISK_REWARD:
        return None
    
    # BLOCK if no entry/stop/tp from strategy
    entry_price = decision.get('entry_price', 0)
    stop_loss = decision.get('stop_loss', 0)
    take_profit = decision.get('take_profit', 0)
    if not entry_price or not stop_loss:
        return None
    
    # Dynamic position sizing based on confidence - use LIVE HTX balance
    live_bal = get_live_balance()
    live_usdd = live_bal.get('USDD', 0)
    position_size_pct = get_position_size_pct(confidence)
    position_size = live_usdd * position_size_pct
    margin = position_size  # No leverage
    quantity = position_size / btc_price
    
    # If live balance too low, don't trade
    if live_usdd < MIN_TRADE_VALUE_USDD:
        print(f"LIVE TRADING: Insufficient USDD balance ${live_usdd:.2f} to open position")
        return None
    
    # SAFEGUARD: Cancel any stale/open HTX orders before placing new ones
    # Prevents duplicate accumulated orders when check_pending_orders() misses fills
    if USE_LIVE_TRADING:
        try:
            open_orders = htx_live.fetch_open_orders('BTC/USDD')
            if open_orders:
                print(f"[SAFEGUARD] Clearing {len(open_orders)} stale HTX orders before new trade")
                for order in open_orders:
                    try:
                        htx_live.cancel_order(str(order['id']), 'BTC/USDD')
                        print(f"[SAFEGUARD] Cancelled stale order {order['id']}")
                    except Exception as e:
                        print(f"[SAFEGUARD] Failed to cancel {order['id']}: {e}")
                # Refresh balance after cleanup
                live_bal = get_live_balance()
                live_usdd = live_bal.get('USDD', 0)
                live_btc = live_bal.get('BTC', 0)
                print(f"[SAFEGUARD] Balance now: ${live_usdd:.2f} USDD, {live_btc:.6f} BTC")
        except Exception as e:
            print(f"[SAFEGUARD] Error checking HTX orders: {e}")
    
    trade = {
        'strategy_version': strategy_version,
        'symbol': symbol,
        'side': decision_upper,
        'entry_price': entry_price,
        'exit_price': None,
        'quantity': quantity,
        'margin': margin,
        'leverage': LEVERAGE,
        'position_size': position_size,
        'pnl': 0,
        'net_pnl': 0,
        'holding_time': None,
        'timestamp': datetime.now().isoformat(),
        'datetime': datetime.now().strftime('%b %d, %H:%M'),
        'decision': decision_upper,
        'reasoning': decision.get('reasoning', ''),
        'confidence': confidence,
        'risk_reward': rr,
        'status': 'open',
        'stop_loss_price': stop_loss,
        'take_profit_price': take_profit,
        'atr_stop_distance': decision.get('atr_stop', 0),
        'highest_price': btc_price,
        'lowest_price': btc_price,
        'trailing_stop_active': False,
        'trailing_stop_price': None,
        'live_order_id': None,
        'live_sl_order_id': None,
        # Link to the AI decision that triggered this trade
        'signal_timestamp': decision.get('timestamp')
    }
    
    # If live trading enabled, place real order on HTX
    if USE_LIVE_TRADING and position_size >= MIN_TRADE_VALUE_USDD:
        try:
            # Get current live balance to determine actual available amount
            live_bal = get_live_balance()
            live_usdd = live_bal['USDD']
            
            # Use minimum of paper position size and available live balance
            live_amount = min(quantity, live_usdd / entry_price)
            
            if live_amount > 0:
                buy_order_id, fill_info = place_live_buy(entry_price, live_amount)
                if buy_order_id:
                    trade['live_order_id'] = buy_order_id
                    
                    # Only create position if order was filled
                    if fill_info and fill_info.get('filled'):
                        # Order was filled - create position with actual fill info
                        trade['quantity'] = fill_info.get('fill_amount', live_amount)
                        trade['entry_price'] = fill_info.get('fill_price', entry_price)
                        trade['margin'] = trade['quantity'] * trade['entry_price']
                        trade['status'] = 'open'
                        trade['on_htx'] = True
                        print(f"LIVE TRADING: Opened LONG {trade['quantity']} BTC at ${trade['entry_price']} (FILLED at {fill_info.get('fill_price')})")
                    else:
                        # Order not filled yet - create position as PENDING
                        # check_pending_orders() will find it and update when filled
                        trade['status'] = 'pending'
                        trade['on_htx'] = True
                        trade['pending_order_id'] = buy_order_id
                        trade['pending_entry_price'] = entry_price
                        trade['limit_price'] = fill_info.get('fill_price') if fill_info else entry_price
                        trade['quantity'] = live_amount
                        trade['margin'] = live_amount * entry_price
                        print(f"LIVE TRADING: Limit BUY order {buy_order_id} placed at ${fill_info.get('fill_price') if fill_info else entry_price} - PENDING FILL")
                        # Create position immediately so check_pending_orders can find it later
                        s['positions'][symbol] = trade
                        s['trades'].insert(0, trade)
                        record_equity_snapshot(strategy_version, prices)
                        return trade
        except Exception as e:
            print(f"LIVE TRADING ERROR: {e}")
    
    # Track position but don't update paper balance (live order is on HTX)
    s['positions'][symbol] = trade
    s['trades'].insert(0, trade)
    record_equity_snapshot(strategy_version, prices)
    
    return trade

def record_equity_snapshot(version, prices):
    """Record current equity for equity curve - uses LIVE HTX balance"""
    s = storage[version]
    btc_price = prices.get('BTC/USDT', {}).get('price', 0)
    
    unrealized_pnl = calculate_unrealized_pnl(s['positions'], btc_price)
    
    # Use live HTX balance
    live_bal = get_live_balance()
    live_usdd = live_bal.get('USDD', 0)
    live_btc = live_bal.get('BTC', 0)
    
    total_equity = live_usdd + (live_btc * btc_price) + unrealized_pnl
    used_margin = get_used_margin(s['positions'])
    free_balance = live_usdd - used_margin
    
    s['equity_curve'].append({
        'timestamp': datetime.now().isoformat(),
        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'equity': total_equity,
        'balance': live_usdd,  # Live HTX balance
        'used_margin': used_margin,
        'free_balance': free_balance,
        'unrealized_pnl': unrealized_pnl,
        'btc_price': btc_price
    })
    
    if len(s['equity_curve']) > 1000:
        s['equity_curve'] = s['equity_curve'][-1000:]

def calculate_metrics(version):
    """Calculate trading metrics for a strategy - uses LIVE HTX balance"""
    s = storage[version]
    trades = [t for t in s['trades'] if t.get('status') == 'closed']
    
    prices = fetch_htx_prices()
    btc_price = prices.get('BTC/USDT', {}).get('price', 0)
    unrealized_pnl = calculate_unrealized_pnl(s['positions'], btc_price)
    
    # Use live HTX balance for equity
    live_bal = get_live_balance()
    live_usdd = live_bal.get('USDD', 0)
    live_btc = live_bal.get('BTC', 0)
    total_equity = live_usdd + (live_btc * btc_price) + unrealized_pnl
    
    if not trades:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_pnl': 0,
            'total_pnl': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'equity': round(total_equity, 2)
        }
    
    winning = [t for t in trades if t.get('net_pnl', 0) > 0]
    losing = [t for t in trades if t.get('net_pnl', 0) < 0]
    
    total_pnl = sum(t.get('net_pnl', 0) for t in trades)
    win_rate = len(winning) / len(trades) * 100 if trades else 0
    
    if len(trades) >= 2:
        pnls = [t.get('net_pnl', 0) for t in trades]
        avg_pnl = sum(pnls) / len(pnls)
        variance = sum((p - avg_pnl) ** 2 for p in pnls) / len(pnls)
        std_dev = variance ** 0.5
        sharpe = (avg_pnl / std_dev * (252 ** 0.5)) if std_dev > 0 else 0
    else:
        sharpe = 0
    
    equity_curve = s['equity_curve']
    max_drawdown = 0
    if equity_curve:
        peak = equity_curve[0]['equity']
        for point in equity_curve:
            if point['equity'] > peak:
                peak = point['equity']
            drawdown = (peak - point['equity']) / peak * 100 if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    return {
        'total_trades': len(trades),
        'winning_trades': len(winning),
        'losing_trades': len(losing),
        'win_rate': round(win_rate, 1),
        'avg_pnl': round(total_pnl / len(trades), 2) if trades else 0,
        'total_pnl': round(total_pnl, 2),
        'sharpe_ratio': round(sharpe, 2),
        'max_drawdown': round(max_drawdown, 2),
        'equity': round(total_equity, 2)
    }

@app.get("/api/prices/stream")
async def price_stream():
    """SSE for real-time price updates"""
    async def event_generator():
        while True:
            prices = fetch_htx_prices()
            yield f"data: {json.dumps(prices)}\n\n"
            await asyncio.sleep(3)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/prices")
async def get_prices():
    """One-shot price fetch"""
    return fetch_htx_prices()

@app.get("/api/balance")
async def get_balance():
    """Get account info for both strategies - uses LIVE HTX balance"""
    prices = fetch_htx_prices()
    btc_price = prices.get('BTC/USDT', {}).get('price', 0)
    
    # Get live HTX balance for both strategies
    live_bal = get_live_balance()
    live_usdd = live_bal.get('USDD', 0)
    live_btc = live_bal.get('BTC', 0)
    
    result = {}
    for version in ['V1', 'V2']:
        s = storage[version]
        unrealized_pnl = calculate_unrealized_pnl(s['positions'], btc_price)
        used_margin = get_used_margin(s['positions'])
        
        # Use live HTX balance for equity calculation
        live_equity = live_usdd + (live_btc * btc_price)
        equity = live_equity + unrealized_pnl
        free_balance = live_usdd - used_margin
        
        result[version] = {
            'balance': round(live_usdd, 2),  # Live USDD balance
            'equity': round(equity, 2),
            'used_margin': round(used_margin, 2),
            'free_balance': round(free_balance, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'live_btc': live_btc
        }
    
    return result

@app.get("/api/htx-balance")
async def get_htx_balance():
    """Get real HTX account balances (ALL assets) fetched live from exchange"""
    try:
        balance = htx_live.fetch_balance()
        
        # Get BTC price for conversion
        prices = fetch_htx_prices()
        btc_price = prices.get('BTC/USDT', {}).get('price', 0)
        
        # Get all non-zero assets
        all_assets = {}
        total_value_usdd = 0
        
        for asset, data in balance.get('total', {}).items():
            if data and data > 0:
                # Get price in USDD (most assets priced against USDT or USDD)
                if asset in ['USDT', 'USDD', 'USD']:
                    price_in_usdd = 1.0
                elif asset == 'BTC':
                    price_in_usdd = btc_price
                else:
                    # Try to get price for this asset
                    price_key = f"{asset}/USDT"
                    asset_price = prices.get(price_key, {}).get('price', 0)
                    price_in_usdd = asset_price if asset_price > 0 else 0
                
                asset_value_usdd = data * price_in_usdd
                total_value_usdd += asset_value_usdd
                
                all_assets[asset] = {
                    'total': round(data, 8),
                    'free': round(balance.get(asset, {}).get('free', 0) or 0, 8),
                    'used': round(balance.get(asset, {}).get('used', 0) or 0, 8),
                    'value_usdd': round(asset_value_usdd, 2),
                    'price_usdd': round(price_in_usdd, 6) if price_in_usdd > 0 else None
                }
        
        return {
            'assets': all_assets,
            'total_value_usdd': round(total_value_usdd, 2),
            'btc_price': btc_price,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'error': str(e), 'timestamp': datetime.now().isoformat()}

@app.get("/api/trades")
async def get_trades():
    v1 = storage.get('V1', {}).get('trades', [])
    v2 = storage.get('V2', {}).get('trades', [])
    nova = storage.get('NOVA', {}).get('trades', [])
    all_trades = v1 + v2 + nova
    return sorted(all_trades, key=lambda x: x['timestamp'], reverse=True)

@app.get("/api/positions")
async def get_positions():
    """Get positions for all strategies with live P&L - uses cached HTX data"""
    # Use cached HTX data instead of multiple API calls
    cached = get_cached_htx_data()
    prices = cached['prices']
    btc_price = prices.get('BTC/USDT', {}).get('price', 0)
    
    # Get live HTX balance from cache
    live_bal = cached['balance']
    live_usdd = live_bal.get('USDD', {}).get('total', 0)
    live_btc = live_bal.get('BTC', {}).get('total', 0)
    
    # Get HTX open orders from cache
    htx_open_orders = []
    try:
        for o in cached['open_orders']:
            htx_open_orders.append({
                'id': o['id'],
                'side': o['side'],
                'type': o['type'],
                'price': o.get('price'),
                'amount': o['amount'],
                'filled': o.get('filled', 0),
                'remaining': o.get('remaining', o['amount']),
                'status': o['status'],
                'datetime': o.get('datetime')
            })
    except Exception as e:
        print(f"HTX open orders error: {e}")
    
    result = {
        'htx_balance': {
            'usdd': round(live_usdd, 2),
            'btc': live_btc,
            'btc_value_usdd': round(live_btc * btc_price, 2),
            'total_usdd': round(live_usdd + (live_btc * btc_price), 2)
        },
        'htx_open_orders': htx_open_orders,
        'strategies': {}
    }
    
    for version in ['V1', 'V2', 'NOVA']:
        s = storage.get(version, storage.get('V1'))
        if not s: continue
        used_margin = get_used_margin(s.get('positions', {}))
        free_balance = live_usdd - used_margin
        
        strategy_positions = [{
            'strategy_version': version,
            'coin': 'USDD',
            'balance': round(live_usdd, 2),
            'used_margin': round(used_margin, 2),
            'free_balance': round(free_balance, 2)
        }]
        
        for symbol, pos in s['positions'].items():
            # Skip pending orders - they are not filled positions yet
            if pos.get('status') == 'pending':
                continue
            
            # Verify position against HTX - check if we still have the BTC
            btc_held = live_btc if pos['side'] == 'LONG' else 0
            position_still_valid = btc_held >= pos['quantity'] * 0.99  # 1% tolerance
            
            if pos['side'] == 'LONG':
                pnl = pos['position_size'] * (btc_price - pos['entry_price']) / pos['entry_price']
            elif pos['side'] == 'SHORT':
                pnl = pos['position_size'] * (pos['entry_price'] - btc_price) / pos['entry_price']
            else:
                pnl = 0
            
            position_data = {
                'strategy_version': version,
                'coin': pos.get('coin', 'BTC'),
                'symbol': pos['symbol'],
                'side': pos['side'],
                'entry_price': pos['entry_price'],
                'current_price': btc_price,
                'quantity': pos['quantity'],
                'margin': pos['margin'],
                'leverage': pos.get('leverage', LEVERAGE),
                'position_size': pos['position_size'],
                'unrealized_pnl': round(pnl, 2),
                'stop_loss_price': round(pos.get('stop_loss_price', 0), 2),
                'take_profit_price': round(pos.get('take_profit_price', 0), 2),
                'trailing_stop_price': round(pos.get('trailing_stop_price', 0), 2) if pos.get('trailing_stop_active') else None,
                'trailing_stop_active': pos.get('trailing_stop_active', False),
                'confidence': pos.get('confidence', 0),
                'risk_reward': pos.get('risk_reward', 0),
                'reasoning': pos.get('reasoning', ''),
                'on_htx': position_still_valid,
                'live_order_id': pos.get('live_order_id'),
                'live_sl_order_id': pos.get('live_sl_order_id')
            }
            
            # If position not valid on HTX, mark it for review
            if not position_still_valid:
                position_data['warning'] = 'Position may have been closed on HTX'
            
            strategy_positions.append(position_data)
        
        result['strategies'][version] = strategy_positions
    
    return result

@app.get("/api/decisions")
async def get_decisions(limit: int = 400):
    v1 = storage.get('V1', {}).get('decisions', [])
    v2 = storage.get('V2', {}).get('decisions', [])
    nova = storage.get('NOVA', {}).get('decisions', [])
    all_decisions = v1 + v2 + nova
    sorted_decisions = sorted(all_decisions, key=lambda x: x['timestamp'], reverse=True)
    return sorted_decisions[:limit]

@app.get("/api/equity")
async def get_equity():
    """Get equity curve data for chart"""
    prices = fetch_htx_prices()
    btc_price = prices.get('BTC/USDT', {}).get('price', 0)
    
    result = {}
    for version in ['V1', 'V2']:
        s = storage.get(version, {'balance': 0, 'positions': {}, 'equity_curve': []})
        
        unrealized_pnl = calculate_unrealized_pnl(s.get('positions', {}), btc_price)
        current_equity = s.get('balance', 0) + unrealized_pnl
        used_margin = get_used_margin(s.get('positions', {}))
        free_balance = s.get('balance', 0) - used_margin
        
        equity_data = list(s.get('equity_curve', []))
        if not equity_data or equity_data[-1]['datetime'] != datetime.now().strftime('%Y-%m-%d %H:%M'):
            equity_data.append({
                'timestamp': datetime.now().isoformat(),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'equity': current_equity,
                'balance': s.get('balance', 0),
                'used_margin': used_margin,
                'free_balance': free_balance,
                'unrealized_pnl': unrealized_pnl,
                'btc_price': btc_price
            })
        
        result[version] = equity_data
    
    # Add REAL equity from live HTX balance
    try:
        live_bal = get_cached_htx_data()['balance']
        usdd = live_bal.get('USDD', {}).get('total', 0)
        btc = live_bal.get('BTC', {}).get('total', 0)
        btc_value = btc * btc_price
        real_equity = usdd + btc_value
    except:
        real_equity = 0
    
    result['REAL'] = [{
        'timestamp': datetime.now().isoformat(),
        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'equity': real_equity,
        'balance': real_equity,
        'used_margin': 0,
        'free_balance': real_equity,
        'unrealized_pnl': 0,
        'btc_price': btc_price
    }]
    
    return result

@app.get("/api/metrics")
async def get_metrics():
    """Get trading metrics for both strategies"""
    return {
        'V1': calculate_metrics('V1'),
        'V2': calculate_metrics('V2')
    }

@app.post("/api/decision/{version}")
async def get_decision(version: str):
    """Get trading decision using improved strategy + AI reasoning"""
    if version not in ['V1', 'V2']:
        return {"error": "Invalid version. Use V1 or V2."}
    
    decision = run_strategy(version=version)
    prices = fetch_htx_prices()
    
    ai_result = get_ai_reasoning(decision, prices)
    if ai_result:
        decision['reasoning'] = ai_result.get('content', '')
        decision['model'] = ai_result.get('model', 'Unknown')
    
    decision['timestamp'] = datetime.now().isoformat()
    storage[version]['decisions'].insert(0, decision)
    storage[version]['decisions'] = storage[version]['decisions'][:MAX_DECISIONS]
    
    trade = execute_paper_trade(version, decision, prices)
    if trade:
        decision['executed_trade'] = trade
    
    record_equity_snapshot(version, prices)
    save_storage()
    
    return decision

def run_combined_strategy():
    """Run the combined strategy (regime detection → pick trend or range). Returns decision dict."""
    trend_decision = run_strategy(version="V1")
    range_decision = run_strategy(version="V2")
    
    if trend_decision.get("error"):
        return trend_decision
    
    regime = trend_decision.get("market_regime", "unknown")
    decision = trend_decision if regime == "TREND" else range_decision
    decision["strategy_name"] = "Nova"
    decision["strategy_version"] = "NOVA"
    
    prices = fetch_htx_prices()
    ai_result = get_ai_reasoning(decision, prices)
    if ai_result:
        decision['reasoning'] = ai_result.get('content', '')
        decision['model'] = ai_result.get('model', 'Unknown')
    
    decision['timestamp'] = datetime.now().isoformat()
    
    if 'NOVA' not in storage:
        storage['NOVA'] = {'decisions': [], 'trades': [], 'positions': {}, 'balance': {'balance': 0}, 'equity_curve': []}
    storage['NOVA']['decisions'].insert(0, decision)
    storage['NOVA']['decisions'] = storage['NOVA']['decisions'][:MAX_DECISIONS]
    
    if not AI_ONLY_MODE:
        trade = execute_paper_trade("NOVA", decision, prices)
        if trade:
            decision['executed_trade'] = trade
    
    record_equity_snapshot("NOVA", prices)
    save_storage()
    return decision

@app.post("/api/decision")
async def get_combined_decision():
    return run_combined_strategy()

@app.post("/api/force-trade")
async def force_trade(request: Request):
    """Force a manual trade using the strategy with highest confidence"""
    data = await request.json()
    direction = data.get('direction', 'LONG').upper()
    
    if direction not in ['LONG', 'SHORT', 'CLOSE', 'BUY', 'SELL']:
        return {"error": "Invalid direction. Use BUY, SELL, or CLOSE."}
    
    # Normalize BUY/SELL to LONG/CLOSE
    if direction == 'BUY':
        direction = 'LONG'
    elif direction == 'SELL':
        direction = 'CLOSE'
    
    prices = fetch_htx_prices()
    btc_price = prices.get('BTC/USDT', {}).get('price', 0)
    
    if btc_price == 0:
        return {"error": "Failed to get BTC price"}
    
    # For CLOSE: check both V1 and V2 for open positions
    if direction == 'CLOSE':
        symbol = 'BTC/USDT'
        closed_version = None
        existing = None
        
        for v in ['V1', 'V2']:
            if symbol in storage[v]['positions']:
                existing = storage[v]['positions'][symbol]
                closed_version = v
                break
        
        if not existing:
            return {"success": False, "message": "No position to close"}
        
        version = closed_version
        if existing['side'] == 'LONG':
            realized_pnl = existing['position_size'] * (btc_price - existing['entry_price']) / existing['entry_price']
        else:
            realized_pnl = existing['position_size'] * (existing['entry_price'] - btc_price) / existing['entry_price']
        
        trade = {
            'strategy_version': version,
            'symbol': symbol,
            'side': existing['side'],
            'entry_price': existing['entry_price'],
            'exit_price': btc_price,
            'quantity': existing['quantity'],
            'margin': existing['margin'],
            'leverage': existing['leverage'],
            'position_size': existing['position_size'],
            'pnl': realized_pnl,
            'net_pnl': realized_pnl,
            'holding_time': calculate_holding_time(existing['timestamp']),
            'timestamp': datetime.now().isoformat(),
            'datetime': datetime.now().strftime('%b %d, %H:%M'),
            'decision': 'CLOSE',
            'reasoning': f'Manual CLOSE. BTC @ ${btc_price:,.2f}. P&L: ${realized_pnl:.2f}',
            'confidence': 1.0,
            'status': 'closed'
        }
        
        # Place real sell order on HTX for live trading
        if USE_LIVE_TRADING and existing.get('live_order_id'):
            if existing.get('live_sl_order_id'):
                cancel_live_stop_loss(existing['live_sl_order_id'])
            sell_order_id = place_live_sell('market', existing['quantity'])
            if sell_order_id:
                trade['live_sell_order_id'] = sell_order_id
                print(f"LIVE TRADING: Manual close, SELL order ID: {sell_order_id}")
        
        s = storage[version]
        del s['positions'][symbol]
        s['trades'].insert(0, trade)
        record_equity_snapshot(version, prices)
        save_storage()
        
        live_bal = get_live_balance()
        return {"success": True, "trade": trade, "live_balance": live_bal.get('USDD', 0)}
    
    # For LONG: auto-select strategy with highest confidence
    # Get latest decisions from both strategies
    v1_decisions = storage['V1']['decisions']
    v2_decisions = storage['V2']['decisions']
    
    v1_conf = v1_decisions[0].get('confidence', 0) if v1_decisions else 0
    v2_conf = v2_decisions[0].get('confidence', 0) if v2_decisions else 0
    
    # Use strategy with higher confidence
    if v1_conf >= v2_conf:
        version = 'V1'
        selected_conf = v1_conf
    else:
        version = 'V2'
        selected_conf = v2_conf
    
    # If confidence too low, use default
    if selected_conf < MIN_CONFIDENCE_TO_TRADE:
        selected_conf = MIN_CONFIDENCE_TO_TRADE
    
    # Use dynamic position sizing based on selected confidence
    position_size_pct = get_position_size_pct(selected_conf)
    live_bal = get_live_balance()
    live_usdd = live_bal.get('USDD', 0)
    position_size = live_usdd * position_size_pct
    
    if position_size < MIN_TRADE_VALUE_USDD:
        return {"success": False, "message": f"Insufficient balance. Need at least ${MIN_TRADE_VALUE_USDD:.2f} USDD."}
    
    decision = {
        'decision': direction,
        'reasoning': f'Manual {direction} using {version} (confidence: {selected_conf:.0%}) at ${btc_price:,.2f}. Position size: {position_size_pct*100:.0f}% of balance.',
        'confidence': selected_conf,
        'entry_price': btc_price,
        'stop_loss': btc_price * (1 - STOP_LOSS_PCT),
        'take_profit': btc_price * (1 + TAKE_PROFIT_PCT),
        'risk_reward': TAKE_PROFIT_PCT / STOP_LOSS_PCT
    }
    
    result = execute_paper_trade(version, decision, prices)
    save_storage()
    
    if result:
        live_bal = get_live_balance()
        return {"success": True, "trade": result, "strategy": version, "confidence": selected_conf, "position_size_pct": position_size_pct, "live_balance": live_bal.get('USDD', 0)}
    else:
        return {"success": False, "message": "Trade not executed"}
    
    if direction == 'CLOSE':
        symbol = 'BTC/USDT'
        s = storage[version]
        if symbol not in s['positions']:
            return {"success": False, "message": "No position to close"}
        
        existing = s['positions'][symbol]
        if existing['side'] == 'LONG':
            realized_pnl = existing['position_size'] * (btc_price - existing['entry_price']) / existing['entry_price']
        else:
            realized_pnl = existing['position_size'] * (existing['entry_price'] - btc_price) / existing['entry_price']
        
        trade = {
            'strategy_version': version,
            'symbol': symbol,
            'side': existing['side'],
            'entry_price': existing['entry_price'],
            'exit_price': btc_price,
            'quantity': existing['quantity'],
            'margin': existing['margin'],
            'leverage': existing['leverage'],
            'position_size': existing['position_size'],
            'pnl': realized_pnl,
            'net_pnl': realized_pnl,
            'holding_time': calculate_holding_time(existing['timestamp']),
            'timestamp': datetime.now().isoformat(),
            'datetime': datetime.now().strftime('%b %d, %H:%M'),
            'decision': 'CLOSE',
            'reasoning': f'Manual CLOSE. BTC @ ${btc_price:,.2f}. P&L: ${realized_pnl:.2f}',
            'confidence': 1.0,
            'status': 'closed'
        }
        
        # Place real sell order on HTX for live trading
        if USE_LIVE_TRADING and existing.get('live_order_id'):
            if existing.get('live_sl_order_id'):
                cancel_live_stop_loss(existing['live_sl_order_id'])
            sell_order_id = place_live_sell('market', existing['quantity'])
            if sell_order_id:
                trade['live_sell_order_id'] = sell_order_id
                print(f"LIVE TRADING: Manual close, SELL order ID: {sell_order_id}")
        
        # Don't update paper balance for live trades - HTX handles the money
        del s['positions'][symbol]
        s['trades'].insert(0, trade)
        record_equity_snapshot(version, prices)
        save_storage()
        
        live_bal = get_live_balance()
        return {"success": True, "trade": trade, "live_balance": live_bal.get('USDD', 0)}
    
    decision = {
        'decision': direction,
        'reasoning': f'Manual force trade: {direction} at ${btc_price}',
        'confidence': 0.8,
        'entry_price': btc_price,
        'stop_loss': btc_price * 0.97,
        'take_profit': btc_price * 1.06,
        'risk_reward': 2.0
    }
    
    result = execute_paper_trade(version, decision, prices)
    save_storage()
    
    if result:
        return {"success": True, "trade": result, "balance": storage[version]['balance']}
    else:
        return {"success": False, "message": "Trade not executed"}

@app.get("/")
def root():
    return {"status": "running", "strategies": ["V1", "V2"]}

@app.get("/api/indicators")
async def get_indicators():
    """Get current indicator values for BTC"""
    df = fetch_candles("BTC/USDT", "15m", 100)
    if df is None:
        return {"error": "Failed to fetch data"}
    
    from strategy import calculate_indicators, detect_regime, calculate_bollinger_bands, calculate_atr
    
    df = calculate_indicators(df)
    latest = df.iloc[-1]
    regime = detect_regime(df)
    
    atr = calculate_atr(df, 14)
    atr_val = atr.iloc[-1] if len(atr) > 0 else 0
    bb_upper, bb_lower, bb_middle = calculate_bollinger_bands(df["close"])
    
    return {
        "price": latest["close"],
        "rsi": round(latest["rsi"], 2),
        "ema9": round(latest["ema9"], 2),
        "ema20": round(latest["ema20"], 2),
        "ema50": round(latest["ema50"], 2),
        "macd": round(latest["macd"], 4),
        "macd_hist": round(latest["macd_hist"], 4),
        "atr": round(atr_val, 2),
        "supertrend_dir": int(latest["supertrend_dir"]),
        "bb_upper": round(bb_upper.iloc[-1], 2) if len(bb_upper) > 0 else 0,
        "bb_lower": round(bb_lower.iloc[-1], 2) if len(bb_lower) > 0 else 0,
        "bb_middle": round(bb_middle.iloc[-1], 2) if len(bb_middle) > 0 else 0,
        "regime": regime["regime"],
        "regime_scores": {"range": regime["range_score"], "trend": regime["trend_score"]},
        "volume_ratio": round(regime.get("volume_ratio_raw", 1), 2)
    }

# Auto-polling state
auto_run_enabled = False
auto_run_interval = 900  # 15 minutes for strategy
stop_check_interval = 30  # 30 seconds for stop monitoring
auto_run_task = None
stop_check_task = None

async def stop_monitor_loop():
    """Background loop that checks stops every 30 seconds (fast)"""
    global auto_run_enabled
    while True:
        if auto_run_enabled:
            try:
                prices = fetch_htx_prices()
                check_pending_orders()
                closed = check_positions_for_stops("NOVA", prices)
                if closed:
                    print(f"[STOP MONITOR] Closed {len(closed)} stopped position(s)")
                save_storage()
            except Exception as e:
                print(f"[STOP MONITOR] Error: {e}")
        await asyncio.sleep(stop_check_interval)

async def auto_run_loop():
    """Background loop that runs the unified Nova strategy every 15 min"""
    global auto_run_enabled
    while True:
        if auto_run_enabled:
            try:
                await asyncio.to_thread(run_combined_strategy)
            except Exception as e:
                print(f"[AUTO] Error in auto-run: {e}")
        await asyncio.sleep(auto_run_interval)

@app.post("/api/auto/start")
async def start_auto_run():
    """Start auto-polling — strategy every 15min, stop monitoring every 30s"""
    global auto_run_enabled, auto_run_task, stop_check_task
    auto_run_enabled = True
    if auto_run_task is None or auto_run_task.done():
        auto_run_task = asyncio.create_task(auto_run_loop())
    if stop_check_task is None or stop_check_task.done():
        stop_check_task = asyncio.create_task(stop_monitor_loop())
    return {"status": "auto-run started", "interval_seconds": auto_run_interval, "stop_check_seconds": stop_check_interval}

@app.post("/api/auto/stop")
async def stop_auto_run():
    """Stop auto-polling"""
    global auto_run_enabled
    auto_run_enabled = False
    return {"status": "auto-run stopped"}

@app.get("/api/auto/status")
async def get_auto_status():
    return {
        "enabled": auto_run_enabled,
        "interval_seconds": auto_run_interval
    }

@app.post("/api/run-both")
async def run_both_strategies():
    """Manually run both V1 and V2 strategies"""
    prices = fetch_htx_prices()
    
    v1_closed = check_positions_for_stops("V1", prices)
    v2_closed = check_positions_for_stops("V2", prices)
    
    # Run V1 (Nova Trend)
    v1_decision = run_strategy(version="V1")
    v1_trade = execute_paper_trade("V1", v1_decision, prices)
    
    if not v1_trade and v1_decision.get('decision') != 'HOLD':
        v1_decision['decision'] = 'HOLD'
        v1_decision['reasoning'] = f"No trade. Nova Trend waiting. BTC @ ${prices.get('BTC/USDT', {}).get('price', 0):,.2f}."
    
    if v1_trade or v1_decision.get('decision') == 'HOLD':
        v1_reasoning = get_ai_reasoning(v1_decision, prices)
        if v1_reasoning:
            v1_decision['reasoning'] = v1_reasoning.get('content', '')
            v1_decision['model'] = v1_reasoning.get('model', 'Unknown')
    
    v1_decision['timestamp'] = datetime.now().isoformat()
    storage['V1']['decisions'].insert(0, v1_decision)
    storage['V1']['decisions'] = storage['V1']['decisions'][:MAX_DECISIONS]
    if v1_trade:
        v1_decision['executed_trade'] = v1_trade
    record_equity_snapshot("V1", prices)
    
    # Run V2 (Nova Range)
    v2_decision = run_strategy(version="V2")
    v2_trade = execute_paper_trade("V2", v2_decision, prices)
    
    if not v2_trade and v2_decision.get('decision') != 'HOLD':
        v2_decision['decision'] = 'HOLD'
        v2_decision['reasoning'] = f"No trade. Nova Range waiting. BTC @ ${prices.get('BTC/USDT', {}).get('price', 0):,.2f}."
    
    if v2_trade or v2_decision.get('decision') == 'HOLD':
        v2_reasoning = get_ai_reasoning(v2_decision, prices)
        if v2_reasoning:
            v2_decision['reasoning'] = v2_reasoning.get('content', '')
            v2_decision['model'] = v2_reasoning.get('model', 'Unknown')
    
    v2_decision['timestamp'] = datetime.now().isoformat()
    storage['V2']['decisions'].insert(0, v2_decision)
    storage['V2']['decisions'] = storage['V2']['decisions'][:MAX_DECISIONS]
    if v2_trade:
        v2_decision['executed_trade'] = v2_trade
    record_equity_snapshot("V2", prices)
    
    save_storage()
    
    return {
        "V1": v1_decision,
        "V2": v2_decision,
        "closed_positions": {"V1": v1_closed, "V2": v2_closed},
        "timestamp": datetime.now().isoformat()
    }


# Price Monitor Loop - Fast monitoring for stop losses/take profits
PRICE_MONITOR_INTERVAL = 5  # seconds - runs every 5 seconds
price_monitor_enabled = False
price_monitor_task = None

async def price_monitor_loop():
    """Fast loop that ONLY checks stop losses and take profits
    Runs every 5 seconds, independent of the AI decision loop
    """
    global price_monitor_enabled
    print(f"[PRICE MONITOR] Started - checking every {PRICE_MONITOR_INTERVAL} seconds")
    while True:
        if price_monitor_enabled:
            try:
                prices = fetch_htx_prices()
                btc_price = prices.get('BTC/USDT', {}).get('price', 0)
                
                # Check V1 positions
                v1_closed = check_positions_for_stops("V1", prices)
                if v1_closed:
                    print(f"[PRICE MONITOR] V1 stopped out: {len(v1_closed)} positions closed")
                
                # Check V2 positions  
                v2_closed = check_positions_for_stops("V2", prices)
                if v2_closed:
                    print(f"[PRICE MONITOR] V2 stopped out: {len(v2_closed)} positions closed")
                
                if v1_closed or v2_closed:
                    save_storage()
                    
            except Exception as e:
                print(f"[PRICE MONITOR] Error: {e}")
        
        await asyncio.sleep(PRICE_MONITOR_INTERVAL)

@app.post("/api/price-monitor/start")
async def start_price_monitor():
    """Start fast price monitoring for stops"""
    global price_monitor_enabled, price_monitor_task
    price_monitor_enabled = True
    if price_monitor_task is None or price_monitor_task.done():
        price_monitor_task = asyncio.create_task(price_monitor_loop())
    return {"status": "price monitor started", "interval_seconds": PRICE_MONITOR_INTERVAL}

@app.post("/api/price-monitor/stop")
async def stop_price_monitor():
    """Stop price monitoring"""
    global price_monitor_enabled
    price_monitor_enabled = False
    return {"status": "price monitor stopped"}

@app.get("/api/price-monitor/status")
async def get_price_monitor_status():
    return {
        "enabled": price_monitor_enabled,
        "interval_seconds": PRICE_MONITOR_INTERVAL
    }

if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    # Start the price monitor loop automatically
    async def startup_tasks():
        global price_monitor_enabled, price_monitor_task
        price_monitor_enabled = True
        price_monitor_task = asyncio.create_task(price_monitor_loop())
        print("[STARTUP] Price monitor loop started")
    
    # Get the event loop and run startup
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(startup_tasks())
    
    # Run uvicorn with the app
    uvicorn.run(app, host="0.0.0.0", port=5181)
