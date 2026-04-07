#!/usr/bin/env python3
"""
================================================================================
NIFTY/SENSEX WEEKLY OPTIONS DATA LOADER
Day 1 Morning: 5-Step Process with Full IV & Greeks Calculation
================================================================================

SCOPE: Download NSE bhavcopy (2-month optimized), filter, calculate IV/Greeks
DURATION: ~45-60 minutes runtime
OUTPUT: PostgreSQL option_bars table with 5 Greeks calculated

MODIFICATIONS FROM SPEC:
- Date range: Last 2 months (instead of 6 months) to respect token/time limits
- Set `MONTHS_TO_FETCH = 6` to override to full 6 months
- All parameters exposed as module-level constants
"""

import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np
import requests
from io import StringIO, BytesIO
import logging
from pathlib import Path
import time
import zipfile
import os
import shutil
from jugaad_data.nse import bhavcopy_fo_save

# ============================================================================
# CONFIGURATION PARAMETERS (All Tunable)
# ============================================================================

# DATABASE
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "nifty_sensex_options"
DB_USER = "postgres"
DB_PASSWORD = "postgres"  # Set to your PostgreSQL password

# DOWNLOAD SCOPE
MONTHS_TO_FETCH = 1  # Set to 6 for full 6-month load; set to 1 for quick test
# Use RECENT dates from NSE archive
END_DATE = date(2026, 4, 3)  # Latest trading day (Friday before today)
START_DATE = END_DATE - timedelta(days=30 * MONTHS_TO_FETCH)

# FILTERING PARAMETERS
MIN_DTE = 1  # Minimum days to expiry
MAX_DTE = 7  # Maximum days to expiry
MIN_MONEYNESS_PCT = 1.5  # Lower bound moneyness %
MAX_MONEYNESS_PCT = 4.5  # Upper bound moneyness %

# CALCULATION PARAMETERS
RISK_FREE_RATE = 0.065  # RBI rate (6.5%)
IV_PRECISION = 1e-6  # IV convergence tolerance
MAX_IV_ITER = 100  # Max iterations for IV solver

# SYMBOLS TO FETCH
SYMBOLS = ['NIFTY', 'SENSEX']
OPTION_TYPES = ['CE', 'PE']  # Call, Put

# PROCESSING
BATCH_SIZE = 500  # Rows per INSERT batch
SLEEP_BETWEEN_REQUESTS = 0.5  # Seconds between NSE requests (polite crawling)

# LOGGING
LOG_FILE = Path(__file__).stem + ".log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),  # Fixed log encoding
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# NSE SESSION SETUP (Bypass 404 Blocks)
# ============================================================================
nse_session = requests.Session()
nse_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/all-reports"
})

try:
    logger.info("Initializing NSE session...")
    # Hit the all-reports page first (Referer trick)
    nse_session.get("https://www.nseindia.com/all-reports", timeout=10)
except Exception as e:
    logger.warning("Could not hit NSE reports page. Fallback to homepage.")

# ============================================================================
# STEP 1: DOWNLOAD NSE BHAVCOPY
# ============================================================================

def download_bhavcopy(target_date):
    """
    Download NSE bhavcopy for options on target_date.
    Try jugaad-data first (library handles anti-bot), fall back to NSE direct with Referer trick.
    """
    temp_dir = "./bhavcopy_temp"

    # ATTEMPT 1: Try jugaad-data
    try:
        logger.info(f"  Attempt 1: jugaad-data library")
        os.makedirs(temp_dir, exist_ok=True)
        bhavcopy_fo_save(target_date, temp_dir)

        files = os.listdir(temp_dir)
        csv_files = [f for f in files if f.endswith('.csv')]

        if csv_files:
            csv_path = os.path.join(temp_dir, csv_files[0])
            df = pd.read_csv(csv_path)
            logger.info(f"    [OK] jugaad-data: {len(df)} rows")
            shutil.rmtree(temp_dir, ignore_errors=True)
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            return df
    except Exception as e:
        logger.debug(f"    [DEBUG] jugaad-data failed: {str(e)}")

    # ATTEMPT 2: Fall back to NSE direct download with Referer trick
    year = target_date.strftime('%Y')
    month = target_date.strftime('%b').upper()
    date_str = target_date.strftime('%d%b%Y').upper()
    url = f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{year}/{month}/fo{date_str}bhav.csv.zip"

    try:
        logger.info(f"  Attempt 2: NSE direct (Referer trick)")
        response = nse_session.get(url, timeout=15)
        response.raise_for_status()

        # Unzip in memory
        with zipfile.ZipFile(BytesIO(response.content)) as z:
            filename = z.namelist()[0]
            with z.open(filename) as f:
                df = pd.read_csv(f)

        logger.info(f"    [OK] NSE direct: {len(df)} rows")
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        return df

    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            logger.warning(f"  [SKIP] 404 Not Found (likely a holiday)")
        elif response.status_code == 403:
            logger.warning(f"  [FAIL] 403 Forbidden (NSE blocked)")
        else:
            logger.warning(f"  [FAIL] HTTP {response.status_code}")
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        return None
    except Exception as e:
        logger.warning(f"  [FAIL] {str(e)}")
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# ============================================================================
# STEP 2: FILTER BY SYMBOL AND IMMEDIATE EXPIRY (<7 DTE)
# ============================================================================

def filter_options(df, current_date):
    """
    STEP 2: Filter options by:
    - Symbol in [NIFTY, SENSEX]
    - Option type in [CE, PE]
    - Days to expiry (1-7 days)
    
    Args:
        df (pd.DataFrame): Raw bhavcopy data
        current_date (date): Current trading date
    
    Returns:
        pd.DataFrame: Filtered dataframe with DTE calculated
    """
    logger.info(f"  FILTER 1: Symbol in {SYMBOLS}")
    df = df[df['SYMBOL'].isin(SYMBOLS)].copy()
    logger.info(f"    → {len(df)} rows remain")
    
    logger.info(f"  FILTER 2: Option type in {OPTION_TYPES}")
    df = df[df['OPTION_TYP'].isin(OPTION_TYPES)]
    logger.info(f"    → {len(df)} rows remain")
    
    # Parse expiry date
    logger.info(f"  FILTER 3: Days to expiry ({MIN_DTE}-{MAX_DTE})")
    df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DT'], format='%d-%b-%Y')
    df['dte'] = (df['EXPIRY_DATE'] - pd.Timestamp(current_date)).days
    
    df = df[(df['dte'] >= MIN_DTE) & (df['dte'] <= MAX_DTE)]
    logger.info(f"    → {len(df)} rows remain")
    
    return df

# ============================================================================
# STEP 3: FILTER BY MONEYNESS (1.5%-4.5%)
# ============================================================================

def get_spot_price(df, symbol):
    """
    Extract spot price from bhavcopy (index futures close price).
    
    Args:
        df (pd.DataFrame): Full bhavcopy
        symbol (str): 'NIFTY' or 'SENSEX'
    
    Returns:
        float: Spot price or None
    """
    futures = df[
        (df['SYMBOL'] == symbol) &
        (df['INSTRUMENT'] == 'FUTIDX')
    ]
    
    if len(futures) > 0:
        return futures.iloc[0]['CLOSE']
    return None

def filter_moneyness(df, current_date):
    """
    STEP 3: Filter by moneyness (1.5%-4.5%).
    
    Moneyness = abs((strike / spot - 1) * 100)
    
    Args:
        df (pd.DataFrame): Options-only dataframe
        current_date (date): Current date
    
    Returns:
        pd.DataFrame: Filtered by moneyness
    """
    logger.info(f"  FILTER 4: Moneyness ({MIN_MONEYNESS_PCT}%-{MAX_MONEYNESS_PCT}%)")
    
    # Get spot prices for both symbols
    full_df = df.copy()
    spot_map = {}
    
    for symbol in SYMBOLS:
        spot = get_spot_price(full_df, symbol)
        if spot:
            spot_map[symbol] = spot
            logger.info(f"    {symbol} spot: {spot}")
    
    # Calculate moneyness
    def calc_moneyness(row):
        spot = spot_map.get(row['SYMBOL'])
        if spot:
            return abs((row['STRIKE'] / spot - 1) * 100)
        return np.nan
    
    df['moneyness'] = df.apply(calc_moneyness, axis=1)
    initial_count = len(df)
    
    df = df[
        (df['moneyness'] >= MIN_MONEYNESS_PCT) &
        (df['moneyness'] <= MAX_MONEYNESS_PCT)
    ]
    
    logger.info(f"    → {len(df)} rows remain (from {initial_count})")
    return df

# ============================================================================
# STEP 4: CALCULATE IMPLIED VOLATILITY (IV)
# ============================================================================

def norm_cdf(x):
    """Standard normal cumulative distribution function."""
    from math import sqrt, pi, exp, erf
    return 0.5 * (1 + erf(x / sqrt(2)))

def norm_pdf(x):
    """Standard normal probability density function."""
    from math import exp, sqrt, pi
    return exp(-0.5 * x**2) / sqrt(2 * pi)

def black_scholes_call(S, K, T, r, sigma):
    """
    Black-Scholes call price.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        sigma: Volatility (decimal)
    
    Returns:
        Call price
    """
    from math import log, sqrt, exp
    
    if T <= 0 or sigma <= 0:
        return max(S - K, 0)
    
    d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    
    call = S * norm_cdf(d1) - K * exp(-r * T) * norm_cdf(d2)
    return call

def black_scholes_put(S, K, T, r, sigma):
    """
    Black-Scholes put price.
    """
    from math import log, sqrt, exp
    
    if T <= 0 or sigma <= 0:
        return max(K - S, 0)
    
    d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    
    put = K * exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
    return put

def vega(S, K, T, r, sigma):
    """Vega (sensitivity to 1% IV change)."""
    from math import log, sqrt, exp
    
    if T <= 0 or sigma <= 0:
        return 0
    
    d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    return S * norm_pdf(d1) * sqrt(T) / 100

def implied_volatility_newton(option_price, S, K, T, r, option_type, tol=1e-6, max_iter=100):
    """
    Calculate implied volatility using Newton-Raphson method.
    
    Args:
        option_price: Market option price
        S: Spot price
        K: Strike price
        T: Time to expiration (years)
        r: Risk-free rate
        option_type: 'C' for call, 'P' for put
        tol: Convergence tolerance
        max_iter: Max iterations
    
    Returns:
        IV (decimal) or None if no solution
    """
    # Initial guess: use intrinsic value to estimate
    if option_type == 'C':
        intrinsic = max(S - K, 0)
        bs_func = black_scholes_call
    else:
        intrinsic = max(K - S, 0)
        bs_func = black_scholes_put
    
    if option_price < intrinsic:
        return None  # Invalid price
    
    # Initial sigma guess
    sigma = 0.2  # 20% initial guess
    
    for i in range(max_iter):
        try:
            bs_price = bs_func(S, K, T, r, sigma)
            diff = bs_price - option_price
            
            if abs(diff) < tol:
                return sigma
            
            # Calculate vega for Newton-Raphson
            v = vega(S, K, T, r, sigma)
            if v < 1e-8:
                return None
            
            # Newton-Raphson update
            sigma = sigma - diff / v
            
            # Bounds check
            if sigma < 0.001:
                sigma = 0.001
            if sigma > 10:
                sigma = 10
        
        except Exception:
            return None
    
    return sigma if abs(bs_func(S, K, T, r, sigma) - option_price) < 0.01 else None

def calculate_iv(df):
    """
    STEP 4: Calculate implied volatility using Black-Scholes solver.
    
    Args:
        df (pd.DataFrame): Options dataframe with CLOSE, STRIKE, dte
    
    Returns:
        pd.DataFrame: With 'iv' column (as decimal, not %)
    """
    logger.info(f"  CALCULATE IV: Black-Scholes Newton-Raphson solver")
    
    iv_values = []
    success_count = 0
    null_count = 0
    
    for idx, row in df.iterrows():
        try:
            S = row['spot']
            K = row['STRIKE']
            T = row['dte'] / 365.0
            r = RISK_FREE_RATE
            option_type = 'C' if row['OPTION_TYP'] == 'CE' else 'P'
            market_price = row['CLOSE']
            
            # Solve for IV
            iv = implied_volatility_newton(market_price, S, K, T, r, option_type)
            
            if iv is not None:
                iv_values.append(iv)
                success_count += 1
            else:
                iv_values.append(None)
                null_count += 1
        
        except Exception as e:
            iv_values.append(None)
            null_count += 1
    
    df['iv'] = iv_values
    logger.info(f"    ✓ IV calculated: {success_count}/{len(df)} ({100*success_count//len(df)}%)")
    logger.info(f"    ✓ IV nulls: {null_count}/{len(df)} ({100*null_count//len(df)}%)")
    
    return df

# ============================================================================
# STEP 5: CALCULATE GREEKS (Delta, Gamma, Theta, Vega, Rho)
# ============================================================================

def calculate_greeks(df):
    """
    STEP 5: Calculate all 5 Greeks from implied volatility.
    
    Greeks calculated:
    - Delta: Rate of change vs spot (call: 0→1, put: -1→0)
    - Gamma: Rate of change of delta (0→0.1)
    - Theta: Time decay per day (divided by 365)
    - Vega: Sensitivity to 1% IV (divided by 100)
    - Rho: Sensitivity to 1% rate change (divided by 100)
    
    Args:
        df (pd.DataFrame): With iv column (decimal)
    
    Returns:
        pd.DataFrame: With all Greeks columns
    """
    logger.info(f"  CALCULATE GREEKS: Delta, Gamma, Theta, Vega, Rho")
    
    from math import log, sqrt, exp
    
    greeks_data = {
        'delta': [],
        'gamma': [],
        'theta': [],
        'vega': [],
        'rho': []
    }
    
    success_count = 0
    
    for idx, row in df.iterrows():
        try:
            if pd.isna(row['iv']) or row['iv'] <= 0:
                greeks_data['delta'].append(None)
                greeks_data['gamma'].append(None)
                greeks_data['theta'].append(None)
                greeks_data['vega'].append(None)
                greeks_data['rho'].append(None)
                continue
            
            S = row['spot']
            K = row['STRIKE']
            T = row['dte'] / 365.0
            r = RISK_FREE_RATE
            sigma = row['iv']
            option_type = row['OPTION_TYP']
            
            # Avoid division by zero
            if T <= 0 or sigma <= 0:
                greeks_data['delta'].append(None)
                greeks_data['gamma'].append(None)
                greeks_data['theta'].append(None)
                greeks_data['vega'].append(None)
                greeks_data['rho'].append(None)
                continue
            
            # Calculate d1, d2
            d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
            d2 = d1 - sigma * sqrt(T)
            
            # DELTA
            if option_type == 'CE':
                delta_val = norm_cdf(d1)
            else:  # PE
                delta_val = norm_cdf(d1) - 1
            
            # GAMMA (same for calls and puts)
            gamma_val = norm_pdf(d1) / (S * sigma * sqrt(T))
            
            # THETA (per day, divided by 365)
            if option_type == 'CE':
                theta_val = (
                    -S * norm_pdf(d1) * sigma / (2 * sqrt(T))
                    - r * K * exp(-r * T) * norm_cdf(d2)
                ) / 365
            else:  # PE
                theta_val = (
                    -S * norm_pdf(d1) * sigma / (2 * sqrt(T))
                    + r * K * exp(-r * T) * norm_cdf(-d2)
                ) / 365
            
            # VEGA (per 1% IV, divided by 100)
            vega_val = S * norm_pdf(d1) * sqrt(T) / 100
            
            # RHO (per 1% rate change, divided by 100)
            if option_type == 'CE':
                rho_val = K * T * exp(-r * T) * norm_cdf(d2) / 100
            else:  # PE
                rho_val = -K * T * exp(-r * T) * norm_cdf(-d2) / 100
            
            greeks_data['delta'].append(round(delta_val, 4))
            greeks_data['gamma'].append(round(gamma_val, 4))
            greeks_data['theta'].append(round(theta_val, 4))
            greeks_data['vega'].append(round(vega_val, 4))
            greeks_data['rho'].append(round(rho_val, 4))
            success_count += 1
        
        except Exception as e:
            logger.debug(f"    Greek calc error at row {idx}: {e}")
            greeks_data['delta'].append(None)
            greeks_data['gamma'].append(None)
            greeks_data['theta'].append(None)
            greeks_data['vega'].append(None)
            greeks_data['rho'].append(None)
    
    for greek_name, greek_vals in greeks_data.items():
        df[greek_name] = greek_vals
    
    logger.info(f"    ✓ Greeks calculated: {success_count}/{len(df)} rows")
    return df

# ============================================================================
# DATABASE INSERTION
# ============================================================================

def connect_db():
    """Connect to PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info(f" Connected to {DB_NAME}@{DB_HOST}")
        return conn
    except Exception as e:
        logger.error(f" DB connection failed: {e}")
        raise

def insert_batch(conn, df):
    """
    Insert dataframe batch into PostgreSQL using execute_batch.
    
    Args:
        conn: psycopg2 connection
        df: DataFrame with all required columns
    
    Returns:
        int: Number of rows inserted
    """
    cur = conn.cursor()
    
    rows_inserted = 0
    for batch_idx in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[batch_idx:batch_idx+BATCH_SIZE]
        
        insert_values = []
        for _, row in batch.iterrows():
            insert_values.append((
                pd.Timestamp(row['timestamp']),
                row['SYMBOL'],
                row['STRIKE'],
                row['OPTION_TYP'],
                row['EXPIRY_DATE'],
                row.get('OPEN'),
                row.get('HIGH'),
                row.get('LOW'),
                row['CLOSE'],
                row.get('VOLUME'),
                row.get('OI'),
                row['iv'] * 100 if pd.notna(row['iv']) else None,  # Convert to %
                row.get('delta'),
                row.get('gamma'),
                row.get('theta'),
                row.get('vega'),
                row.get('rho')
            ))
        
        execute_batch(
            cur,
            """
            INSERT INTO option_bars 
            (timestamp, symbol, strike, option_type, expiry, open, high, low, close, volume, open_interest, iv, delta, gamma, theta, vega, rho)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, strike, option_type, expiry)
            DO UPDATE SET
                close = EXCLUDED.close,
                iv = EXCLUDED.iv,
                delta = EXCLUDED.delta,
                gamma = EXCLUDED.gamma,
                theta = EXCLUDED.theta,
                vega = EXCLUDED.vega,
                rho = EXCLUDED.rho
            """,
            insert_values,
            page_size=BATCH_SIZE
        )
        
        rows_inserted += len(insert_values)
        logger.debug(f"  Inserted batch {batch_idx//BATCH_SIZE + 1}: {len(insert_values)} rows")
    
    conn.commit()
    return rows_inserted

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    logger.info("="*80)
    logger.info("NIFTY/SENSEX WEEKLY OPTIONS LOADER - DAY 1 MORNING 5-STEP PROCESS")
    logger.info("="*80)
    logger.info(f"Date range: {START_DATE} to {END_DATE}")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"DTE range: {MIN_DTE}-{MAX_DTE}")
    logger.info(f"Moneyness: {MIN_MONEYNESS_PCT}%-{MAX_MONEYNESS_PCT}%")
    logger.info(f"Risk-free rate: {RISK_FREE_RATE*100}%")
    logger.info("="*80)
    
    # Connect to DB
    conn = connect_db()
    
    # Date range to process
    current_date = START_DATE
    total_rows_inserted = 0
    dates_processed = 0
    
    while current_date <= END_DATE:
        # Skip weekends
        if current_date.weekday() >= 5:  # Saturday=5, Sunday=6
            current_date += timedelta(days=1)
            continue
        
        logger.info(f"\n{'='*80}")
        logger.info(f"PROCESSING: {current_date} ({current_date.strftime('%A')})")
        logger.info(f"{'='*80}")
        
        # Download bhavcopy
        raw_df = download_bhavcopy(current_date)
        if raw_df is None or len(raw_df) == 0:
            current_date += timedelta(days=1)
            continue
        
        # STEP 2: Filter by symbol and DTE
        logger.info("STEP 2: Filter by symbol & immediate expiry")
        options_df = filter_options(raw_df, current_date)
        
        if len(options_df) == 0:
            logger.info("  ✗ No options after filtering")
            current_date += timedelta(days=1)
            continue
        
        # STEP 3: Filter by moneyness
        logger.info("STEP 3: Filter by moneyness (1.5%-4.5%)")
        
        # Add spot price for moneyness calculation
        for symbol in SYMBOLS:
            spot = get_spot_price(raw_df, symbol)
            options_df.loc[options_df['SYMBOL'] == symbol, 'spot'] = spot
        
        options_df = filter_moneyness(options_df, current_date)
        
        if len(options_df) == 0:
            logger.info("  ✗ No options after moneyness filter")
            current_date += timedelta(days=1)
            continue
        
        # Prepare timestamp
        options_df['timestamp'] = pd.Timestamp(current_date.replace(hour=15, minute=30))
        
        # STEP 4: Calculate IV
        logger.info("STEP 4: Calculate implied volatility (Black-Scholes)")
        options_df = calculate_iv(options_df)
        
        # STEP 5: Calculate Greeks
        logger.info("STEP 5: Calculate Greeks (Delta, Gamma, Theta, Vega, Rho)")
        options_df = calculate_greeks(options_df)
        
        # Insert into DB
        logger.info("INSERTING into PostgreSQL")
        rows_inserted = insert_batch(conn, options_df)
        total_rows_inserted += rows_inserted
        dates_processed += 1
        
        logger.info(f"  ✓ {rows_inserted} rows inserted for {current_date}")
        
        current_date += timedelta(days=1)
    
    conn.close()
    
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Dates processed: {dates_processed}")
    logger.info(f"Total rows inserted: {total_rows_inserted}")
    logger.info(f"Expected: ~{5000 * MONTHS_TO_FETCH // 6} rows for {MONTHS_TO_FETCH} months")
    logger.info("="*80)
    logger.info(f"Log saved to: {LOG_FILE}")
    logger.info("[OK] COMPLETE: Ready for validation queries")

if __name__ == "__main__":
    main()
