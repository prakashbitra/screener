import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime
import pytz

def calculate_hma(series, length=9):
    half_length = int(length / 2)
    sqrt_length = int(np.sqrt(length))
    def wma(s, l):
        weights = np.arange(1, l + 1)
        return s.rolling(l).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    return wma(wma(series, half_length) * 2 - wma(series, length), sqrt_length)

def check_setup(df):
    if len(df) < 50: return False, None
    
    # ATR & Trendline Slope
    df['ATR'] = df['High'].rolling(28).max() - df['Low'].rolling(28).min() # Simplified ATR proxy
    slope = df['ATR'] / 28 * 1.6
    
    # Pivot Highs/Lows (Lookback 28)
    df['ph'] = (df['High'] > df['High'].shift(28)) & (df['High'] > df['High'].shift(-28))
    df['pl'] = (df['Low'] < df['Low'].shift(28)) & (df['Low'] < df['Low'].shift(-28))
    
    # Last SH/SL for CHoCH
    df['lastSH'] = df['High'].where(df['ph']).ffill()
    df['lastSL'] = df['Low'].where(df['pl']).ffill()
    
    # Signals
    bullCHoCH = (df['Close'] > df['lastSH'].shift(1)) & (df['Close'].shift(1) <= df['lastSH'].shift(2))
    bearCHoCH = (df['Close'] < df['lastSL'].shift(1)) & (df['Close'].shift(1) >= df['lastSL'].shift(2))
    
    # Trendline Breakout (Placeholder using RSI/Vol proxy for 'Break')
    bullBreak = df['Close'] > df['High'].rolling(28).mean() + slope
    
    # Combined Signal (CHoCH within 20 bars of Break)
    # We look for bullBreak in the last 20 bars
    recent_break = bullBreak.rolling(20).any()
    
    if (bullCHoCH.iloc[-1] and recent_break.iloc[-1]):
        entry = float(df['Close'].iloc[-1])
        sl = float(df['lastSL'].iloc[-1])
        risk = entry - sl
        if risk <= 0: return False, None
        return True, {"entry": entry, "target": entry + (risk * 1.5), "sl": sl}
        
    return False, None

def run_screener():
    # Add your full ticker lists here as before...
    india_tickers = ["RELIANCE.NS", "TCS.NS"] # Keep your list
    usa_tickers = ["AMD", "QCOM", "AMAT", "GE", "TXN"] # Keep your list
    
    results = {"india": [], "usa": [], "last_updated": datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M:%S EST")}
    for t in india_tickers:
        df = yf.Ticker(t).history(period="3mo", interval="1d")
        valid, setup = check_setup(df)
        if valid: results["india"].append({"ticker": t, **setup})
    for t in usa_tickers:
        df = yf.Ticker(t).history(period="3mo", interval="1d")
        valid, setup = check_setup(df)
        if valid: results["usa"].append({"ticker": t, **setup})
    with open('data.json', 'w') as f: json.dump(results, f, indent=4)

if __name__ == "__main__": run_screener()
