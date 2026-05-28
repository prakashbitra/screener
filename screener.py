import yfinance as yf
import pandas as pd
import concurrent.futures
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

def process_ticker(ticker):
    try:
        # Fetch 1H data (most reliable free data)
        df = yf.Ticker(ticker).history(period="1mo", interval="1h")
        if len(df) < 100: return None
        
        # Resample 1H data to 4H
        df_4h = df.resample('4H').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        # Add your Logic here (e.g., HMA9 + CHoCH)
        # Using 4H-based pivot calculations
        lookback = 3
        df_4h['HMA9'] = df_4h['Close'].rolling(9).mean() # Simplified HMA
        df_4h['PivotHigh'] = df_4h['High'][(df_4h['High'] > df_4h['High'].shift(1)) & (df_4h['High'] > df_4h['High'].shift(-1))]
        
        last_close = df_4h['Close'].iloc[-1]
        if last_close > df_4h['HMA9'].iloc[-1] and last_close > df_4h['PivotHigh'].ffill().iloc[-1]:
            return {"ticker": ticker, "entry": last_close, "sl": df_4h['Low'].iloc[-lookback:].min(), "target": last_close * 1.02}
    except:
        return None
    return None
    
def run_screener():
    all_tickers = ["AAPL", "RELIANCE.NS", ...] # Your list of 400
    results = {"india": [], "usa": []}
    
    # Run in parallel to handle 400 stocks in seconds
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {executor.submit(process_ticker, t): t for t in all_tickers}
        for future in concurrent.futures.as_completed(future_to_ticker):
            res = future.result()
            if res:
                # categorize into india/usa based on suffix
                if ".NS" in res['ticker']: results["india"].append(res)
                else: results["usa"].append(res)
    
    with open('data.json', 'w') as f: json.dump(results, f, indent=4)

if __name__ == "__main__": run_screener()
