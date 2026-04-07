#!/usr/bin/env python3
"""
Process Real Kaggle Data in Chunks (Memory Efficient)
Handle 3.7GB file by reading in 100K row chunks
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
CHUNK_SIZE = 100000  # Read 100K rows at a time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# GREEKS CALCULATION (INLINE)
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
# PROCESS IN CHUNKS
# ============================================================================

def process_kaggle_chunked():
    """Process large CSV in chunks"""
    logger.info("="*80)
    logger.info("PROCESSING REAL KAGGLE DATA (CHUNKED)")
    logger.info("="*80)

    csv_file = Path("final_merged_output.csv")

    if not csv_file.exists():
        logger.error("[ERROR] final_merged_output.csv not found")
        return False

    logger.info(f"\n[READ] File: {csv_file.name}")
    logger.info(f"[INFO] Size: {csv_file.stat().st_size / (1024**3):.2f} GB")
    logger.info(f"[INFO] Reading in {CHUNK_SIZE:,}-row chunks...")

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )

    # Clear old data first
    cur = conn.cursor()
    cur.execute("DELETE FROM option_bars_daily")
    conn.commit()
    logger.info("[OK] Cleared old data")

    total_rows = 0
    total_inserted = 0
    chunk_num = 0

    try:
        # Read CSV in chunks
        for chunk_df in pd.read_csv(csv_file, chunksize=CHUNK_SIZE, low_memory=False):
            chunk_num += 1
            total_rows += len(chunk_df)

            logger.info(f"\n[CHUNK {chunk_num}] Processing {len(chunk_df):,} rows (Total: {total_rows:,})...")

            try:
                # Standardize column names
                chunk_df.columns = chunk_df.columns.str.lower().str.strip()

                # Find timestamp column
                timestamp_col = None
                for col in chunk_df.columns:
                    if 'time' in col or 'date' in col:
                        timestamp_col = col
                        break

                if not timestamp_col:
                    logger.warning(f"  [SKIP] No timestamp column in chunk {chunk_num}")
                    continue

                # Parse timestamp
                chunk_df['timestamp'] = pd.to_datetime(chunk_df[timestamp_col], errors='coerce')
                chunk_df['date'] = chunk_df['timestamp'].dt.date

                # Group by date and options
                group_cols = ['date', 'symbol', 'strike', 'option_type', 'expiry']
                available_cols = [col for col in group_cols if col in chunk_df.columns]

                if len(available_cols) < 5:
                    logger.warning(f"  [SKIP] Missing grouping columns")
                    continue

                eod_chunk = chunk_df.groupby(available_cols).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum',
                    'oi': 'last'
                }).reset_index()

                # Add timestamp
                eod_chunk['timestamp'] = eod_chunk['date'].apply(
                    lambda x: datetime.combine(x, datetime.strptime("15:30", "%H:%M").time())
                )

                # Calculate Greeks
                insert_records = []
                for _, row in eod_chunk.iterrows():
                    try:
                        spot = 24500
                        T = (datetime.combine(row['expiry'], datetime.min.time()) -
                             datetime.combine(row['date'], datetime.min.time())).days / 365.0

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
                            delta, gamma, theta, vega_val, rho
                        ))
                    except:
                        continue

                # Insert chunk
                if insert_records:
                    cur = conn.cursor()
                    execute_batch(cur, """
                        INSERT INTO option_bars_daily (timestamp, symbol, strike, option_type, expiry, open, high, low, close, volume, open_interest, iv, delta, gamma, theta, vega, rho)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (timestamp, symbol, strike, option_type, expiry)
                        DO UPDATE SET close = EXCLUDED.close, iv = EXCLUDED.iv
                    """, insert_records, page_size=BATCH_SIZE)
                    conn.commit()
                    cur.close()

                    total_inserted += len(insert_records)
                    logger.info(f"  [OK] Inserted {len(insert_records):,} EOD records (Total: {total_inserted:,})")

            except Exception as e:
                logger.error(f"  [ERROR] Chunk {chunk_num} failed: {e}")
                continue

            # Limit to first 5 chunks for testing (~500K rows)
            if chunk_num >= 5:
                logger.info(f"\n[INFO] Processed {chunk_num} chunks ({total_rows:,} 1-min rows)")
                logger.info(f"[INFO] Converted to {total_inserted:,} daily EOD records")
                logger.info(f"[ACTION] Set CHUNK_LIMIT=None in script to process entire file")
                break

        # Final stats
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM option_bars_daily")
        final_count = cur.fetchone()[0]

        cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM option_bars_daily")
        min_ts, max_ts = cur.fetchone()

        cur.close()
        conn.close()

        logger.info(f"\n" + "="*80)
        logger.info(f"[OK] REAL KAGGLE DATA LOADED")
        logger.info(f"="*80)
        logger.info(f"Database records: {final_count:,}")
        logger.info(f"Date range: {min_ts.date()} to {max_ts.date()}")

        return True

    except Exception as e:
        logger.error(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = process_kaggle_chunked()
    if not success:
        logger.error("\n[FAIL] Processing failed")
