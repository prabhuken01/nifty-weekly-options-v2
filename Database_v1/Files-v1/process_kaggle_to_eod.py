#!/usr/bin/env python3
"""
Process Kaggle 1-minute data to daily EOD (End of Day)
Convert to database format with Greeks calculation
"""

import psycopg2
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from math import log, sqrt, pi, exp, erf

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "nifty_sensex_options"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

RISK_FREE_RATE = 0.065

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# GREEKS CALCULATION (same as before)
# ============================================================================

def norm_cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))

def norm_pdf(x):
    return exp(-0.5 * x**2) / sqrt(2 * pi)

def implied_volatility_newton(option_price, S, K, T, r, option_type, tol=1e-6, max_iter=100):
    if option_type == 'CE':
        intrinsic = max(S - K, 0)
    else:
        intrinsic = max(K - S, 0)

    if option_price < intrinsic:
        return None

    sigma = 0.2
    for i in range(max_iter):
        try:
            d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
            v = S * norm_pdf(d1) * sqrt(T) / 100

            if option_type == 'CE':
                d2 = d1 - sigma * sqrt(T)
                bs_price = S * norm_cdf(d1) - K * exp(-r * T) * norm_cdf(d2)
            else:
                d2 = d1 - sigma * sqrt(T)
                bs_price = K * exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

            diff = bs_price - option_price
            if abs(diff) < tol:
                return sigma
            if v < 1e-8:
                return None
            sigma = sigma - diff / v
            if sigma < 0.001:
                sigma = 0.001
            if sigma > 10:
                sigma = 10
        except:
            return None
    return sigma

def calculate_greeks(S, K, T, iv, option_type):
    if not iv or iv <= 0 or T <= 0:
        return None, None, None, None, None

    try:
        r = RISK_FREE_RATE
        sigma = iv
        d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)

        delta = norm_cdf(d1) if option_type == 'CE' else norm_cdf(d1) - 1
        gamma = norm_pdf(d1) / (S * sigma * sqrt(T))
        theta = (-S * norm_pdf(d1) * sigma / (2 * sqrt(T)) - r * K * exp(-r * T) * norm_cdf(d2)) / 365 if option_type == 'CE' else (-S * norm_pdf(d1) * sigma / (2 * sqrt(T)) + r * K * exp(-r * T) * norm_cdf(-d2)) / 365
        vega_val = S * norm_pdf(d1) * sqrt(T) / 100
        rho = K * T * exp(-r * T) * norm_cdf(d2) / 100 if option_type == 'CE' else -K * T * exp(-r * T) * norm_cdf(-d2) / 100

        return round(delta, 4), round(gamma, 4), round(theta, 4), round(vega_val, 4), round(rho, 4)
    except:
        return None, None, None, None, None

# ============================================================================
# PROCESS KAGGLE DATA
# ============================================================================

def process_kaggle_files():
    """Process CSV files from Kaggle and convert to EOD"""
    logger.info("="*80)
    logger.info("PROCESS KAGGLE DATA: 1-MIN TO DAILY EOD")
    logger.info("="*80)

    kaggle_path = Path("kaggle_data")

    if not kaggle_path.exists():
        logger.error("[ERROR] kaggle_data folder not found")
        return False

    # Find all CSV files
    csv_files = list(kaggle_path.glob("**/*.csv"))
    logger.info(f"\n[INFO] Found {len(csv_files)} CSV files")

    if not csv_files:
        logger.error("[ERROR] No CSV files found in kaggle_data")
        return False

    all_data = []

    # Read all CSV files
    for csv_file in csv_files:
        try:
            logger.info(f"[READ] {csv_file.name}...")
            df = pd.read_csv(csv_file)
            logger.info(f"  Loaded {len(df)} rows")

            all_data.append(df)
        except Exception as e:
            logger.warning(f"  Error reading {csv_file.name}: {e}")

    if not all_data:
        logger.error("[ERROR] Could not read any CSV files")
        return False

    # Combine all data
    logger.info(f"\n[COMBINE] Combining {len(all_data)} files...")
    df = pd.concat(all_data, ignore_index=True)
    logger.info(f"[OK] Combined: {len(df)} total rows")

    # Expected columns: timestamp, symbol, strike, option_type, expiry, open, high, low, close, volume, oi, iv, etc.
    logger.info(f"\n[INFO] Columns in dataset: {list(df.columns)}")

    # Convert to daily EOD
    logger.info(f"\n[CONVERT] Converting 1-minute data to daily EOD...")

    # Parse timestamp if needed
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    elif 'datetime' in df.columns:
        df['timestamp'] = pd.to_datetime(df['datetime'])
    else:
        logger.error("[ERROR] No timestamp column found")
        return False

    # Group by date and options
    df['date'] = df['timestamp'].dt.date
    df['symbol'] = df.get('symbol', 'NIFTY')
    df['strike'] = pd.to_numeric(df.get('strike', 24500), errors='coerce')
    df['option_type'] = df.get('option_type', 'CE')
    df['expiry'] = pd.to_datetime(df.get('expiry', '2026-04-13')).dt.date

    # Group by date, symbol, strike, option_type, expiry
    eod_data = df.groupby(['date', 'symbol', 'strike', 'option_type', 'expiry']).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'oi': 'last'
    }).reset_index()

    logger.info(f"[OK] Converted to {len(eod_data)} daily EOD records")

    # Add timestamp (3:30 PM EOD)
    eod_data['timestamp'] = eod_data['date'].apply(
        lambda x: datetime.combine(x, datetime.strptime("15:30", "%H:%M").time())
    )

    # Calculate Greeks
    logger.info(f"\n[GREEKS] Calculating Greeks...")

    greeks_data = []
    for _, row in eod_data.iterrows():
        try:
            # Get spot price (assume from NIFTY future or use close)
            spot = row.get('spot', 24500)  # Default to ~24500

            T = (datetime.combine(row['expiry'], datetime.min.time()) - datetime.combine(row['date'], datetime.min.time())).days / 365.0
            if T <= 0:
                continue

            close = row.get('close', 0)
            iv = implied_volatility_newton(close, spot, row['strike'], T, RISK_FREE_RATE, row['option_type'])

            if not iv:
                iv = 0.25

            delta, gamma, theta, vega_val, rho = calculate_greeks(spot, row['strike'], T, iv, row['option_type'])

            greeks_data.append({
                'timestamp': row['timestamp'],
                'symbol': row['symbol'],
                'strike': row['strike'],
                'option_type': row['option_type'],
                'expiry': row['expiry'],
                'open': row.get('open'),
                'high': row.get('high'),
                'low': row.get('low'),
                'close': close,
                'volume': row.get('volume'),
                'open_interest': row.get('oi'),
                'iv': iv * 100 if iv else None,
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega_val,
                'rho': rho
            })
        except Exception as e:
            logger.debug(f"Error processing row: {e}")

    logger.info(f"[OK] Calculated Greeks for {len(greeks_data)} records")

    # Insert into database
    logger.info(f"\n[INSERT] Loading into PostgreSQL...")
    return insert_to_database(greeks_data)

def insert_to_database(records):
    """Insert processed data into database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        cur = conn.cursor()

        from psycopg2.extras import execute_batch

        # Clear old data
        cur.execute("DELETE FROM option_bars_daily WHERE timestamp < NOW() - INTERVAL '6 months'")
        logger.info("[OK] Cleared old data")

        # Insert
        insert_data = [
            (
                r['timestamp'],
                r['symbol'],
                r['strike'],
                r['option_type'],
                r['expiry'],
                r.get('open'),
                r.get('high'),
                r.get('low'),
                r['close'],
                r.get('volume'),
                r.get('open_interest'),
                r.get('iv'),
                r.get('delta'),
                r.get('gamma'),
                r.get('theta'),
                r.get('vega'),
                r.get('rho')
            )
            for r in records
        ]

        execute_batch(cur, """
            INSERT INTO option_bars_daily (timestamp, symbol, strike, option_type, expiry, open, high, low, close, volume, open_interest, iv, delta, gamma, theta, vega, rho)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, strike, option_type, expiry)
            DO UPDATE SET close = EXCLUDED.close
        """, insert_data, page_size=500)

        conn.commit()

        # Verify
        cur.execute("SELECT COUNT(*) FROM option_bars_daily")
        count = cur.fetchone()[0]
        logger.info(f"[OK] Inserted {len(insert_data)} records (Total in DB: {count})")

        cur.close()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    success = process_kaggle_files()
    if success:
        logger.info("\n[OK] Processing complete - Data loaded into PostgreSQL")
    else:
        logger.error("\n[FAIL] Processing failed")
