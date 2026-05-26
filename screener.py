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
    if len(df) < 40: return False, None
    
    df['HMA_9'] = calculate_hma(df['Close'].dropna(), 9)
    highs = df['High'].dropna()
    lows = df['Low'].dropna()
    
    # Structural Pivot Highs (Breakout Level)
    df['PivotHigh'] = highs[(highs > highs.shift(1)) & (highs > highs.shift(2)) & 
                            (highs > highs.shift(-1)) & (highs > highs.shift(-2))]
    df['LastPivot'] = df['PivotHigh'].ffill()
    df['CHoCH_Trigger'] = (df['Close'] > df['LastPivot']) & (df['Close'].shift(1) <= df['LastPivot'].shift(1))
    
    # Stop Loss Level: Swing Low Pivot (Lookback 3 left, 3 right)
    df['PivotLow'] = lows[(lows < lows.shift(1)) & (lows < lows.shift(2)) & (lows < lows.shift(3)) & 
                          (lows < lows.shift(-1)) & (lows < lows.shift(-2)) & (lows < lows.shift(-3))]
    df['LastPivotLow'] = df['PivotLow'].ffill()
    
    above_hma = df['Close'].iloc[-1] > df['HMA_9'].iloc[-1]
    recent_triggers = df['CHoCH_Trigger'].iloc[-3:]
    has_recent_choch = recent_triggers.any()
    above_structure = df['Close'].iloc[-1] > df['LastPivot'].iloc[-1]
    
    if above_hma and has_recent_choch and above_structure:
        bars_ago = 3 - np.where(recent_triggers)[0][-1]
        
        # Setup Math
        entry_price = float(df['Close'].iloc[-1])
        sl_price = float(df['LastPivotLow'].iloc[-1])
        
        # Failsafe: If SL is somehow NA or above entry, fallback to recent 10-bar low
        if pd.isna(sl_price) or sl_price >= entry_price:
            sl_price = float(df['Low'].iloc[-10:].min())
            if sl_price >= entry_price: return False, None # Invalid setup
            
        risk = entry_price - sl_price
        target_price = entry_price + (risk * 2) # 1:2 Risk Reward
        
        return True, {
            "bars": int(bars_ago),
            "entry": round(entry_price, 2),
            "sl": round(sl_price, 2),
            "target": round(target_price, 2)
        }
    return False, None

def run_screener():
    # Top 200 Indian Equities
    india_tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "SBI.NS", "INFY.NS",
        "LICI.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS",
        "SUNPHARMA.NS", "ADANIENT.NS", "KOTAKBANK.NS", "TITAN.NS", "ONGC.NS", "TATAMOTORS.NS", "NTPC.NS",
        "AXISBANK.NS", "DMART.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS",
        "COALINDIA.NS", "BAJAJFINSV.NS", "BAJAJ-AUTO.NS", "POWERGRID.NS", "NESTLEIND.NS", "WIPRO.NS",
        "M&M.NS", "IOC.NS", "JIOFIN.NS", "HAL.NS", "DLF.NS", "ADANIPOWER.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
        "SIEMENS.NS", "IRFC.NS", "VBL.NS", "ZOMATO.NS", "PIDILITIND.NS", "GRASIM.NS", "SBILIFE.NS",
        "BEL.NS", "LTIM.NS", "TRENT.NS", "PNB.NS", "INDIGO.NS", "BANKBARODA.NS", "HDFCLIFE.NS", "ABB.NS",
        "BPCL.NS", "PFC.NS", "GODREJCP.NS", "TATAPOWER.NS", "HINDALCO.NS", "CHOLAFIN.NS", "BOSCHLTD.NS",
        "TVSMOTOR.NS", "RECLTD.NS", "BRITANNIA.NS", "INDUSINDBK.NS", "HAVELLS.NS", "CIPLA.NS", "SHREECEM.NS",
        "SRF.NS", "GAIL.NS", "TECHM.NS", "DIVISLAB.NS", "EICHERMOT.NS", "AMBUJACEM.NS", "APOLLOHOSP.NS",
        "MAXHEALTH.NS", "CGPOWER.NS", "TORNTPHARM.NS", "COLPAL.NS", "HEROMOTOCO.NS", "LODHA.NS",
        "CANBK.NS", "TIINDIA.NS", "AUBANK.NS", "ICICIGI.NS", "JINDALSTEL.NS", "CUMMINSIND.NS", "TATACOMM.NS",
        "IDEA.NS", "ZEC.NS", "POLYCAB.NS", "SHRIRAMFIN.NS", "UBL.NS", "MACROTECH.NS", "DIXON.NS",
        "PERSISTENT.NS", "MUTHOOTFIN.NS", "PETRONET.NS", "ASHOKLEY.NS", "SUNDARMFIN.NS", "MRF.NS",
        "FEDERALBNK.NS", "PIIND.NS", "PGHH.NS", "CONCOR.NS", "VOLTAS.NS", "IDFCFIRSTB.NS", "COROMANDEL.NS",
        "ASTRAL.NS", "BALKRISIND.NS", "M&MFIN.NS", "OBEROIRLTY.NS", "GMRINFRA.NS", "PRESTIGE.NS",
        "TATAELXSI.NS", "NMDC.NS", "ABCAPITAL.NS", "GUJGASLTD.NS", "LUPIN.NS", "PEL.NS", "BATAINDIA.NS",
        "MFSL.NS", "AUROPHARMA.NS", "BANDHANBNK.NS", "STARHEALTH.NS", "NHPC.NS", "SAIL.NS", "YESBANK.NS",
        "BIOCON.NS", "ICICIPRULI.NS", "BANKINDIA.NS", "UNIONBANK.NS", "MOTHERSON.NS", "TORNTPOWER.NS",
        "SKFINDIA.NS", "SYNGENE.NS", "FORTIS.NS", "ZEEL.NS", "GLAND.NS", "IPCALAB.NS", "IGL.NS", "LTTS.NS",
        "COFORGE.NS", "MINDTREE.NS", "MPHASIS.NS", "DALBHARAT.NS", "RAMCOCEM.NS", "LICHSGFIN.NS",
        "CRISIL.NS", "DELHIVERY.NS", "PAYTM.NS", "NYKAA.NS", "POLICYBZR.NS", "SONACOMS.NS", "KPITTECH.NS",
        "TATACHEM.NS", "DEVYANI.NS", "APTUS.NS", "POONAWALLA.NS", "AARTIIND.NS", "NAVINFLUOR.NS",
        "CLEAN.NS", "TRIDENT.NS", "WELSPUNIND.NS", "RELAXO.NS", "KPRMILL.NS", "INDIAMART.NS", "MCX.NS",
        "IEX.NS", "CAMS.NS", "CDSL.NS", "ANGELONE.NS", "UTIAMC.NS", "NAM-INDIA.NS", "BSOFT.NS", "AFFLE.NS",
        "HAPPSTMNDS.NS", "ROUTE.NS", "LATENTVIEW.NS", "MAPMYINDIA.NS", "MEDANTA.NS", "KIMS.NS", "RAINBOW.NS",
        "METROPOLIS.NS", "LALPATHLAB.NS", "MANAPPURAM.NS", "IIFL.NS", "CHAMBLFERT.NS", "DEEPAKNTR.NS",
        "TATAINVEST.NS", "JSWENERGY.NS", "SUZLON.NS", "INOXWIND.NS"
    ]

    # Top 200 US Equities
    usa_tickers = [
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "LLY", "JPM", "V", "UNH",
        "XOM", "MA", "JNJ", "PG", "HD", "MRK", "COST", "ABBV", "CVX", "CRM", "AMD", "PEP", "KO", "WMT",
        "BAC", "TMO", "LIN", "MCD", "ADBE", "DIS", "ACN", "CSCO", "ABT", "INTC", "INTU", "QCOM", "WFC",
        "DHR", "CMCSA", "IBM", "AMAT", "CAT", "GE", "TXN", "NOW", "PM", "NKE", "SPGI", "AMGN", "COP",
        "HON", "BA", "PFE", "UNP", "SYK", "ISRG", "RTX", "BKNG", "GS", "PLD", "ELV", "T", "NEE", "BLK",
        "TJX", "MDLZ", "PGR", "VRTX", "CB", "REGN", "ADP", "LMT", "MMC", "CI", "BSY", "ADI", "MU", "CVS",
        "GILD", "ETN", "C", "ZTS", "KLAC", "FI", "SLB", "BSX", "PANW", "CME", "SCHW", "MO", "SNPS", "CDNS",
        "DE", "CSX", "NOC", "ITW", "EQIX", "SHW", "SO", "AON", "ICE", "EOG", "WM", "TGT", "MCK", "APH",
        "PCAR", "ORLY", "HCA", "CL", "NXPI", "FCX", "MCO", "F", "USB", "MPC", "PXD", "EMR", "PSX", "TRV",
        "VLO", "MAR", "PH", "ROP", "MTD", "OXY", "AIG", "DHI", "TDG", "CARR", "DUK", "STZ", "PAYX", "TT",
        "AZO", "YUM", "ADSK", "IQV", "O", "WELL", "GPN", "EXC", "KMB", "SRE", "HLT", "AEP", "ROST", "CTAS",
        "CPRT", "MNST", "TEL", "KMI", "D", "CHTR", "KDP", "WMB", "FAST", "PRU", "GWW", "SYY", "PEG", "AFL",
        "SPG", "AWK", "LVS", "BIIB", "CTSH", "EA", "XEL", "VRSK", "WBA", "ILMN", "IDXX", "ALGN", "MTB",
        "TROW", "DFS", "ALL", "ROK", "OTIS", "AMP", "CBRE", "DLTR", "SBAC", "WDC", "GLW", "AME", "FITB",
        "YUMC", "NUE", "GPC", "VRSN", "KHC", "EPAM", "KEYS", "MTCH", "EXPD", "ODFL", "WST", "ANSS", "ZBH",
        "CDW", "DOV", "VMC", "MLM", "XYL", "IT", "CHD", "FMC", "TSCO", "BBY", "ULTA", "VFC", "HRL", "MKC",
        "SBUX", "SNA", "CINF", "L", "GL", "RJF", "PFG", "CMA", "ZION", "KEY", "CFG", "HBAN", "RF"
    ]
    
    results = {"india": [], "usa": [], "last_updated": ""}
    
    for ticker in india_tickers:
        df = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if not df.empty:
            is_valid, setup = check_setup(df)
            if is_valid: 
                results["india"].append({"ticker": ticker, **setup})
            
    for ticker in usa_tickers:
        df = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if not df.empty:
            is_valid, setup = check_setup(df)
            if is_valid: 
                results["usa"].append({"ticker": ticker, **setup})

    est = pytz.timezone('US/Eastern')
    results["last_updated"] = datetime.now(est).strftime("%Y-%m-%d %H:%M:%S EST")
    
    with open('data.json', 'w') as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    run_screener()
