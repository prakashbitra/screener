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
    
    wma_half = wma(series, half_length) * 2
    wma_full = wma(series, length)
    return wma(wma_half - wma_full, sqrt_length)

def check_setup(df):
    if len(df) < 40: return False, 0
    
    df['HMA_9'] = calculate_hma(df['Close'].dropna(), 9)
    highs = df['High'].dropna()
    df['PivotHigh'] = highs[(highs > highs.shift(1)) & (highs > highs.shift(2)) & 
                            (highs > highs.shift(-1)) & (highs > highs.shift(-2))]
    df['LastPivot'] = df['PivotHigh'].ffill()
    df['CHoCH_Trigger'] = (df['Close'] > df['LastPivot']) & (df['Close'].shift(1) <= df['LastPivot'].shift(1))
    
    above_hma = df['Close'].iloc[-1] > df['HMA_9'].iloc[-1]
    recent_triggers = df['CHoCH_Trigger'].iloc[-3:]
    has_recent_choch = recent_triggers.any()
    above_structure = df['Close'].iloc[-1] > df['LastPivot'].iloc[-1]
    
    if above_hma and has_recent_choch and above_structure:
        bars_ago = 3 - np.where(recent_triggers)[0][-1]
        return True, int(bars_ago) # Converted to native int for JSON
    return False, 0

def run_screener():
    india_tickers = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]
    usa_tickers = ["AAPL", "MSFT", "NVDA", "AMZN"]
    
    results = {"india": [], "usa": [], "last_updated": ""}
    
    # FIX: Switched from yf.download() to yf.Ticker().history() for flat data structures
    for ticker in india_tickers:
        df = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if not df.empty:
            is_valid, bars_ago = check_setup(df)
            if is_valid: results["india"].append({"ticker": ticker, "price": float(df['Close'].iloc[-1]), "bars": bars_ago})
            
    for ticker in usa_tickers:
        df = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if not df.empty:
            is_valid, bars_ago = check_setup(df)
            if is_valid: results["usa"].append({"ticker": ticker, "price": float(df['Close'].iloc[-1]), "bars": bars_ago})

    est = pytz.timezone('US/Eastern')
    results["last_updated"] = datetime.now(est).strftime("%Y-%m-%d %H:%M:%S EST")
    
    with open('data.json', 'w') as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    run_screener()
