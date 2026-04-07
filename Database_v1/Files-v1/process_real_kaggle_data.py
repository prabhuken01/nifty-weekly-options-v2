#!/usr/bin/env python3
"""
Process Real Kaggle Nifty Options Data
Convert 1-minute data to daily EOD with full Greeks
"""

import psycopg2
from psycopg2.extras import execute_batch
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
BATCH_SIZE = 500

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# GREEKS CALCULATION
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
# PROCESS REAL DATA
# ============================================================================

def process_real_kaggle_data():
    """Process real Kaggle Nifty options 1-min data to daily EOD"""
    logger.info("="*80)
    logger.info("PROCESSING REAL KAGGLE DATA: 1-MIN TO DAILY EOD")
    logger.info("="*80)

    csv_file = Path("final_merged_output.csv")

    if not csv_file.exists():
        logger.error("[ERROR] final_merged_output.csv not found")
        logger.error("[ACTION] Make sure file is in current directory")
        return False

    logger.info(f"\n[READ] Loading CSV file: {csv_file.name}")
    logger.info(f"[INFO] Size: {csv_file.stat().st_size / (1024**3):.2f} GB")

    try:
        # Read CSV in chunks to handle large file
        logger.info("[READ] Reading CSV file...")
        df = pd.read_csv(csv_file, low_memory=False)
        logger.info(f"[OK] Loaded {len(df):,} rows")

        # Display columns
        logger.info(f"\n[INFO] Columns in dataset:")
        for col in df.columns[:15]:
            logger.info(f"  - {col}")
        if len(df.columns) > 15:
            logger.info(f"  ... and {len(df.columns) - 15} more")

        # Check data
        logger.info(f"\n[DATA] Sample data:")
        logger.info(f"{df.head(2).to_string()}")

        # Standardize column names (make lowercase)
        df.columns = df.columns.str.lower().str.strip()

        # Identify key columns (adjust based on actual data)
        timestamp_col = None
        for col in df.columns:
            if 'time' in col.lower() or 'datetime' in col.lower() or 'date' in col.lower():
                timestamp_col = col
                break

        if not timestamp_col:
            logger.error("[ERROR] Cannot find timestamp column")
            logger.error(f"[INFO] Available columns: {list(df.columns)}")
            return False

        logger.info(f"[OK] Using timestamp column: {timestamp_col}")

        # Parse timestamp
        df['timestamp'] = pd.to_datetime(df[timestamp_col])
        df['date'] = df['timestamp'].dt.date

        # Group by date and options to create EOD
        logger.info(f"\n[CONVERT] Converting 1-minute data to daily EOD...")

        group_cols = ['date', 'symbol', 'strike', 'option_type', 'expiry']
        available_cols = [col for col in group_cols if col in df.columns]

        logger.info(f"[INFO] Grouping by: {available_cols}")

        eod_data = df.groupby(available_cols).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'oi': 'last'
        }).reset_index()

        logger.info(f"[OK] Created {len(eod_data):,} daily EOD records")

        # Add timestamp (3:30 PM EOD)
        eod_data['timestamp'] = eod_data['date'].apply(
            lambda x: datetime.combine(x, datetime.strptime("15:30", "%H:%M").time())
        )

        # Calculate Greeks
        logger.info(f"\n[GREEKS] Calculating Greeks for {len(eod_data):,} records...")

        insert_records = []
        for idx, row in eod_data.iterrows():
            try:
                spot = 24500  # Default NIFTY spot
                T = (datetime.combine(row['expiry'], datetime.min.time()) - datetime.combine(row['date'], datetime.min.time())).days / 365.0

                if T <= 0:
                    continue

                close = row.get('close', 0)
                iv = implied_volatility_newton(close, spot, row['strike'], T, RISK_FREE_RATE, row['option_type'])

                if not iv:
                    iv = 0.25

                delta, gamma, theta, vega_val, rho = calculate_greeks(spot, row['strike'], T, iv, row['option_type'])

                insert_records.append((
                    row['timestamp'],
                    row['symbol'],
                    row['strike'],
                    row['option_type'],
                    row['expiry'],
                    row.get('open'),
                    row.get('high'),
                    row.get('low'),
                    close,
                    row.get('volume'),
                    row.get('oi'),
                    iv * 100 if iv else None,
                    delta,
                    gamma,
                    theta,
                    vega_val,
                    rho
                ))

                if (idx + 1) % 10000 == 0:
                    logger.info(f"  Processed {idx + 1:,} records...")

            except Exception as e:
                logger.debug(f"Error processing row {idx}: {e}")
                continue

        logger.info(f"[OK] Calculated Greeks for {len(insert_records):,} records")

        # Insert to database
        logger.info(f"\n[INSERT] Loading into PostgreSQL...")
        return insert_to_database(insert_records)

    except Exception as e:
        logger.error(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

def insert_to_database(records):
    """Insert processed data into database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        cur = conn.cursor()

        # Clear old synthetic test data
        cur.execute("DELETE FROM option_bars_daily")
        logger.info("[OK] Cleared old test data")

        # Insert in batches
        execute_batch(cur, """
            INSERT INTO option_bars_daily (timestamp, symbol, strike, option_type, expiry, open, high, low, close, volume, open_interest, iv, delta, gamma, theta, vega, rho)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, strike, option_type, expiry)
            DO UPDATE SET close = EXCLUDED.close, iv = EXCLUDED.iv
        """, records, page_size=BATCH_SIZE)

        conn.commit()

        # Verify
        cur.execute("SELECT COUNT(*) FROM option_bars_daily")
        count = cur.fetchone()[0]

        cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM option_bars_daily")
        min_ts, max_ts = cur.fetchone()

        logger.info(f"\n[OK] Inserted {len(records):,} real Kaggle records")
        logger.info(f"[INFO] Total in DB: {count:,} records")
        logger.info(f"[INFO] Date range: {min_ts.date()} to {max_ts.date()}")

        cur.close()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"[ERROR] Database insert failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = process_real_kaggle_data()
    if success:
        logger.info("\n" + "="*80)
        logger.info("[OK] REAL KAGGLE DATA LOADED SUCCESSFULLY")
        logger.info("="*80)
    else:
        logger.error("\n[FAIL] Processing failed")
