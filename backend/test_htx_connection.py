#!/usr/bin/env python3
"""
HTX API Connection Test Script
Tests connectivity and fetches all required data for the trading bot
"""

import ccxt
import json
from datetime import datetime

# HTX API credentials
API_KEY = "ur2fg6h2gf-5f855d61-9dd69df9-604ab"
SECRET = "a3d590b1-142b98c9-de6809ae-c9def"

print("=" * 60)
print("HTX API Connection Test")
print("=" * 60)

# Initialize HTX exchange with API keys
try:
    htx = ccxt.htx({
        'apiKey': API_KEY,
        'secret': SECRET,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'},
    })
    print("✅ Exchange initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize exchange: {e}")
    exit(1)

# Test 1: Fetch Account Balance
print("\n" + "=" * 60)
print("TEST 1: Account Balance")
print("=" * 60)
try:
    balance = htx.fetch_balance()
    print(f"✅ Balance fetched successfully")
    print(f"\nUSDT Balance:")
    print(f"  Total: {balance.get('USDT', {}).get('total', 0)}")
    print(f"  Free:  {balance.get('USDT', {}).get('free', 0)}")
    print(f"  Used:  {balance.get('USDT', {}).get('used', 0)}")
    
    # Show all non-zero balances
    print(f"\nAll non-zero balances:")
    for currency, amount in balance.get('total', {}).items():
        if amount and amount > 0:
            print(f"  {currency}: {amount}")
except Exception as e:
    print(f"❌ Failed to fetch balance: {e}")

# Test 2: Fetch BTC/USDT Price
print("\n" + "=" * 60)
print("TEST 2: BTC/USDT Price")
print("=" * 60)
try:
    ticker = htx.fetch_ticker('BTC/USDT')
    print(f"✅ Ticker fetched successfully")
    print(f"\nBTC/USDT:")
    print(f"  Last Price:    ${ticker['last']:,.2f}")
    print(f"  24h High:     ${ticker['high']:,.2f}")
    print(f"  24h Low:      ${ticker['low']:,.2f}")
    print(f"  24h Change:   {ticker['percentage']:.2f}%")
    print(f"  24h Volume:   {ticker['volume']:,.2f} BTC")
except Exception as e:
    print(f"❌ Failed to fetch ticker: {e}")

# Test 3: Fetch Open Orders
print("\n" + "=" * 60)
print("TEST 3: Open Orders")
print("=" * 60)
try:
    open_orders = htx.fetch_open_orders('BTC/USDT')
    print(f"✅ Open orders fetched successfully")
    print(f"  Count: {len(open_orders)}")
    for order in open_orders:
        print(f"\n  Order ID: {order['id']}")
        print(f"  Type:     {order['type']} {order['side']}")
        print(f"  Price:    ${order['price']:,.2f}")
        print(f"  Amount:   {order['amount']}")
        print(f"  Filled:   {order['filled']}")
except Exception as e:
    print(f"❌ Failed to fetch open orders: {e}")

# Test 4: Fetch My Trades (Recent Trades)
print("\n" + "=" * 60)
print("TEST 4: My Recent Trades")
print("=" * 60)
try:
    # Fetch recent trades for BTC/USDT
    trades = htx.fetch_my_trades('BTC/USDT', limit=10)
    print(f"✅ My trades fetched successfully")
    print(f"  Count: {len(trades)}")
    for trade in trades[:5]:  # Show last 5
        dt = datetime.fromtimestamp(trade['timestamp']/1000)
        print(f"\n  Trade ID:     {trade['id']}")
        print(f"  Time:         {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Side:         {trade['side']}")
        print(f"  Price:        ${trade['price']:,.2f}")
        print(f"  Amount:       {trade['amount']}")
        print(f"  Cost:         ${trade['cost']:,.2f}")
        print(f"  Fee:          {trade['fee']}")
except Exception as e:
    print(f"❌ Failed to fetch trades: {e}")

# Test 5: Fetch OHLC (Candlestick) Data
print("\n" + "=" * 60)
print("TEST 5: Candlestick Data (for indicators)")
print("=" * 60)
try:
    candles = htx.fetch_ohlcv('BTC/USDT', timeframe='15m', limit=10)
    print(f"✅ Candles fetched successfully")
    print(f"  Count: {len(candles)}")
    print(f"\nLast 3 candles (15m timeframe):")
    for candle in candles[-3:]:
        dt = datetime.fromtimestamp(candle[0]/1000)
        print(f"  {dt.strftime('%Y-%m-%d %H:%M')}: O=${candle[1]:,.2f} H=${candle[2]:,.2f} L=${candle[3]:,.2f} C=${candle[4]:,.2f} V={candle[5]:,.2f}")
except Exception as e:
    print(f"❌ Failed to fetch candles: {e}")

# Test 6: Check if we can place orders (should fail without trading permission)
print("\n" + "=" * 60)
print("TEST 6: Order Placement Test (will fail gracefully)")
print("=" * 60)
try:
    # Try to create a small test order (won't actually execute if no funds or trading disabled)
    order = htx.create_order(
        symbol='BTC/USDT',
        type='limit',
        side='buy',
        price=htx.fetch_ticker('BTC/USDT')['last'] * 0.99,  # 1% below market
        amount=0.0001,  # Very small amount
    )
    print(f"⚠️ Order placed successfully (test order):")
    print(f"  Order ID: {order['id']}")
    print(f"  Status:   {order['status']}")
    # Cancel immediately
    htx.cancel_order(order['id'], 'BTC/USDT')
    print(f"  (Cancelled immediately after test)")
except Exception as e:
    print(f"ℹ️  Order placement result: {e}")
    print(f"   This is expected if trading permission is disabled")

print("\n" + "=" * 60)
print("Connection Test Complete")
print("=" * 60)
