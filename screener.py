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
    if len(df) < 40: return False, None
    df = df.copy()
    df['HMA_9'] = calculate_hma(df['Close'].dropna(), 9)
    # Pivot Highs
    df['PivotHigh'] = df['High'][(df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(2)) & (df['High'] > df['High'].shift(-1)) & (df['High'] > df['High'].shift(-2))]
    df['LastPivot'] = df['PivotHigh'].ffill()
    # Pivot Lows (SL)
    df['PivotLow'] = df['Low'][(df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(2)) & (df['Low'] < df['Low'].shift(3)) & (df['Low'] < df['Low'].shift(-1)) & (df['Low'] < df['Low'].shift(-2)) & (df['Low'] < df['Low'].shift(-3))]
    df['LastPivotLow'] = df['PivotLow'].ffill()
    
    df['CHoCH_Trigger'] = (df['Close'] > df['LastPivot']) & (df['Close'].shift(1) <= df['LastPivot'].shift(1))
    
    if (df['Close'].iloc[-1] > df['HMA_9'].iloc[-1]) and df['CHoCH_Trigger'].iloc[-3:].any() and (df['Close'].iloc[-1] > df['LastPivot'].iloc[-1]):
        entry = float(df['Close'].iloc[-1])
        sl = float(df['LastPivotLow'].iloc[-1]) if not pd.isna(df['LastPivotLow'].iloc[-1]) else float(df['Low'].iloc[-10:].min())
        target = entry + ((entry - sl) * 2)
        return True, {"entry": entry, "target": target, "sl": sl, "bars": int(np.where(df['CHoCH_Trigger'].iloc[-3:])[0][-1] + 1)}
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
