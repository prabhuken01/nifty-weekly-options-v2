#!/usr/bin/env python3
"""
FALLBACK: Manual bhavcopy CSV files (Option 3 - Manual Override)

INSTRUCTIONS:
1. Download bhavcopy CSV files from NSE website manually
   https://www.nseindia.com/products/content/derivatives/equities/archivemonth.jsp
2. Place CSV files in ./bhavcopies/ folder
3. Run this script to process them

File naming: Copy NSE filename as-is (e.g., fo30OCT2024bhav.csv)
"""

import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from math import log, sqrt, pi, exp, erf

# DATABASE CONFIG
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "nifty_sensex_options"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

# PROCESSING CONFIG
SYMBOLS = ['NIFTY', 'SENSEX']
OPTION_TYPES = ['CE', 'PE']
MIN_DTE = 1
MAX_DTE = 7
MIN_MONEYNESS_PCT = 1.5
MAX_MONEYNESS_PCT = 4.5
RISK_FREE_RATE = 0.065
BATCH_SIZE = 500

LOG_FILE = "nifty_bhavcopy_manual.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# GREEK CALCULATIONS (same as main script)
# ============================================================================

def norm_cdf(x):
    """Standard normal cumulative distribution function."""
    return 0.5 * (1 + erf(x / sqrt(2)))

def norm_pdf(x):
    """Standard normal probability density function."""
    return exp(-0.5 * x**2) / sqrt(2 * pi)

def black_scholes_call(S, K, T, r, sigma):
    """Black-Scholes call price."""
    if T <= 0 or sigma <= 0:
        return max(S - K, 0)
    d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    return S * norm_cdf(d1) - K * exp(-r * T) * norm_cdf(d2)

def black_scholes_put(S, K, T, r, sigma):
    """Black-Scholes put price."""
    if T <= 0 or sigma <= 0:
        return max(K - S, 0)
    d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    return K * exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def vega(S, K, T, r, sigma):
    """Vega (sensitivity to 1% IV change)."""
    if T <= 0 or sigma <= 0:
        return 0
    d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    return S * norm_pdf(d1) * sqrt(T) / 100

def implied_volatility_newton(option_price, S, K, T, r, option_type, tol=1e-6, max_iter=100):
    """Calculate implied volatility using Newton-Raphson."""
    if option_type == 'C':
        intrinsic = max(S - K, 0)
        bs_func = black_scholes_call
    else:
        intrinsic = max(K - S, 0)
        bs_func = black_scholes_put

    if option_price < intrinsic:
        return None

    sigma = 0.2
    for i in range(max_iter):
        try:
            bs_price = bs_func(S, K, T, r, sigma)
            diff = bs_price - option_price
            if abs(diff) < tol:
                return sigma
            v = vega(S, K, T, r, sigma)
            if v < 1e-8:
                return None
            sigma = sigma - diff / v
            if sigma < 0.001:
                sigma = 0.001
            if sigma > 10:
                sigma = 10
        except:
            return None
    return sigma if abs(bs_func(S, K, T, r, sigma) - option_price) < 0.01 else None

def calculate_iv(df):
    """Calculate implied volatility for all rows."""
    iv_values = []
    for _, row in df.iterrows():
        try:
            S = row['spot']
            K = row['STRIKE']
            T = row['dte'] / 365.0
            option_type = 'C' if row['OPTION_TYP'] == 'CE' else 'P'
            market_price = row['CLOSE']
            iv = implied_volatility_newton(market_price, S, K, T, RISK_FREE_RATE, option_type)
            iv_values.append(iv)
        except:
            iv_values.append(None)
    df['iv'] = iv_values
    return df

def calculate_greeks(df):
    """Calculate delta, gamma, theta, vega, rho."""
    greeks = {'delta': [], 'gamma': [], 'theta': [], 'vega': [], 'rho': []}

    for _, row in df.iterrows():
        try:
            if pd.isna(row['iv']) or row['iv'] <= 0:
                for key in greeks:
                    greeks[key].append(None)
                continue

            S = row['spot']
            K = row['STRIKE']
            T = row['dte'] / 365.0
            r = RISK_FREE_RATE
            sigma = row['iv']
            opt_type = row['OPTION_TYP']

            if T <= 0 or sigma <= 0:
                for key in greeks:
                    greeks[key].append(None)
                continue

            d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
            d2 = d1 - sigma * sqrt(T)

            delta = norm_cdf(d1) if opt_type == 'CE' else norm_cdf(d1) - 1
            gamma = norm_pdf(d1) / (S * sigma * sqrt(T))
            theta = (-S * norm_pdf(d1) * sigma / (2 * sqrt(T)) - r * K * exp(-r * T) * norm_cdf(d2)) / 365 if opt_type == 'CE' else (-S * norm_pdf(d1) * sigma / (2 * sqrt(T)) + r * K * exp(-r * T) * norm_cdf(-d2)) / 365
            vega_val = S * norm_pdf(d1) * sqrt(T) / 100
            rho = K * T * exp(-r * T) * norm_cdf(d2) / 100 if opt_type == 'CE' else -K * T * exp(-r * T) * norm_cdf(-d2) / 100

            greeks['delta'].append(round(delta, 4))
            greeks['gamma'].append(round(gamma, 4))
            greeks['theta'].append(round(theta, 4))
            greeks['vega'].append(round(vega_val, 4))
            greeks['rho'].append(round(rho, 4))
        except:
            for key in greeks:
                greeks[key].append(None)

    for key, values in greeks.items():
        df[key] = values
    return df

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_bhavcopy_files():
    """Process all CSV files in bhavcopies/ folder."""
    logger.info("="*80)
    logger.info("MANUAL BHAVCOPY LOADER (Option 3)")
    logger.info("="*80)

    csv_dir = Path("./bhavcopies")
    if not csv_dir.exists():
        logger.error("[FAIL] ./bhavcopies/ directory not found!")
        logger.info("ACTION: Download CSV files from NSE and save to ./bhavcopies/")
        return

    csv_files = list(csv_dir.glob("*.csv"))
    if not csv_files:
        logger.warning("[SKIP] No CSV files found in ./bhavcopies/")
        return

    logger.info(f"[OK] Found {len(csv_files)} CSV files")

    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    total_rows = 0

    for csv_path in sorted(csv_files):
        logger.info(f"\n{'='*80}")
        logger.info(f"PROCESSING: {csv_path.name}")
        logger.info(f"{'='*80}")

        try:
            df = pd.read_csv(csv_path)
            logger.info(f"  Loaded {len(df)} raw rows")

            # Filter by symbol and option type
            df = df[df['SYMBOL'].isin(SYMBOLS)]
            df = df[df['OPTION_TYP'].isin(OPTION_TYPES)]
            logger.info(f"  After symbol/type filter: {len(df)} rows")

            if len(df) == 0:
                logger.warning("  [SKIP] No matching options")
                continue

            # Parse expiry and calculate DTE
            df['EXPIRY_DATE'] = pd.to_datetime(df['EXPIRY_DT'], format='%d-%b-%Y')
            # Use file date as current date (parse from filename like fo30OCT2024bhav.csv)
            try:
                # Extract date from filename: fo30OCT2024bhav.csv -> 2024-10-30
                import re
                match = re.search(r'fo(\d{2})([A-Z]{3})(\d{4})bhav', csv_path.name)
                if match:
                    day, month_str, year = match.groups()
                    month_map = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                                 'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12}
                    current_date = pd.Timestamp(int(year), month_map[month_str], int(day))
                else:
                    current_date = pd.Timestamp.now()
            except:
                current_date = pd.Timestamp.now()

            df['dte'] = (df['EXPIRY_DATE'] - current_date).dt.days
            df = df[(df['dte'] >= MIN_DTE) & (df['dte'] <= MAX_DTE)]
            logger.info(f"  After DTE filter: {len(df)} rows")

            if len(df) == 0:
                logger.warning("  [SKIP] No options in DTE range")
                continue

            # Add spot prices
            for symbol in SYMBOLS:
                futures = df[(df['SYMBOL'] == symbol) & (df['INSTRUMENT'] == 'FUTIDX')]
                if len(futures) > 0:
                    spot = futures.iloc[0]['CLOSE']
                    df.loc[df['SYMBOL'] == symbol, 'spot'] = spot

            # Filter by moneyness
            def calc_moneyness(row):
                spot = row['spot']
                if pd.notna(spot):
                    return abs((row['STRIKE'] / spot - 1) * 100)
                return np.nan

            df['moneyness'] = df.apply(calc_moneyness, axis=1)
            df = df[(df['moneyness'] >= MIN_MONEYNESS_PCT) & (df['moneyness'] <= MAX_MONEYNESS_PCT)]
            logger.info(f"  After moneyness filter: {len(df)} rows")

            if len(df) == 0:
                logger.warning("  [SKIP] No options after moneyness filter")
                continue

            # Add timestamp
            df['timestamp'] = current_date.replace(hour=15, minute=30)

            # Calculate IV and Greeks
            logger.info("  Calculating IV and Greeks...")
            df = calculate_iv(df)
            df = calculate_greeks(df)

            # Insert to DB
            cur = conn.cursor()
            rows_inserted = 0
            for i in range(0, len(df), BATCH_SIZE):
                batch = df.iloc[i:i+BATCH_SIZE]
                insert_vals = []
                for _, row in batch.iterrows():
                    insert_vals.append((
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
                        row['iv'] * 100 if pd.notna(row['iv']) else None,
                        row.get('delta'),
                        row.get('gamma'),
                        row.get('theta'),
                        row.get('vega'),
                        row.get('rho')
                    ))

                execute_batch(cur, """
                    INSERT INTO option_bars (timestamp, symbol, strike, option_type, expiry, open, high, low, close, volume, open_interest, iv, delta, gamma, theta, vega, rho)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, symbol, strike, option_type, expiry)
                    DO UPDATE SET close = EXCLUDED.close, iv = EXCLUDED.iv, delta = EXCLUDED.delta, gamma = EXCLUDED.gamma, theta = EXCLUDED.theta, vega = EXCLUDED.vega, rho = EXCLUDED.rho
                """, insert_vals, page_size=BATCH_SIZE)
                rows_inserted += len(insert_vals)

            conn.commit()
            cur.close()
            logger.info(f"  [OK] Inserted {rows_inserted} rows")
            total_rows += rows_inserted

        except Exception as e:
            logger.error(f"  [ERROR] {e}")

    conn.close()
    logger.info(f"\n{'='*80}")
    logger.info(f"SUMMARY: {total_rows} total rows inserted")
    logger.info(f"{'='*80}")

if __name__ == "__main__":
    process_bhavcopy_files()
