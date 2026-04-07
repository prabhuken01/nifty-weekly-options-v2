#!/usr/bin/env python3
"""
Process Real Kaggle Data - Already has Greeks!
CSV columns: strike_price, option_type, expiry, timestamp, ltp, volume, oi,
             underlying_spot_price, iv, delta, gamma, theta, vega, rho
"""

import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
import pandas as pd
from datetime import datetime
import logging

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "nifty_sensex_options"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

CHUNK_SIZE = 50000

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_real_data():
    """Process Kaggle CSV with existing Greeks"""
    logger.info("="*80)
    logger.info("PROCESS REAL KAGGLE DATA (WITH EXISTING GREEKS)")
    logger.info("="*80)

    csv_file = Path("final_merged_output.csv")

    if not csv_file.exists():
        logger.error("[ERROR] final_merged_output.csv not found")
        return False

    logger.info(f"\n[FILE] {csv_file.name}")
    logger.info(f"[SIZE] {csv_file.stat().st_size / (1024**3):.2f} GB")
    logger.info(f"[MODE] Reading in {CHUNK_SIZE:,}-row chunks")

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )

    # Clear old data
    cur = conn.cursor()
    cur.execute("DELETE FROM option_bars_daily")
    conn.commit()
    logger.info("[OK] Cleared old test data")

    total_rows = 0
    total_inserted = 0
    chunk_num = 0

    try:
        # Read CSV in chunks
        for chunk_df in pd.read_csv(csv_file, chunksize=CHUNK_SIZE, low_memory=False):
            chunk_num += 1
            total_rows += len(chunk_df)

            logger.info(f"\n[CHUNK {chunk_num}] {len(chunk_df):,} rows (Total: {total_rows:,})...")

            try:
                # Parse datetime columns
                chunk_df['timestamp'] = pd.to_datetime(chunk_df['timestamp'])
                chunk_df['expiry'] = pd.to_datetime(chunk_df['expiry'])
                chunk_df['date'] = chunk_df['timestamp'].dt.date

                # Group by date to get EOD (last price of day)
                group_cols = ['date', 'strike_price', 'option_type', 'expiry']

                eod_chunk = chunk_df.groupby(group_cols).agg({
                    'timestamp': 'last',
                    'ltp': 'last',  # Last traded price for EOD
                    'volume': 'sum',
                    'oi': 'last',
                    'underlying_spot_price': 'last',
                    'iv': 'last',
                    'delta': 'last',
                    'gamma': 'last',
                    'theta': 'last',
                    'vega': 'last',
                    'rho': 'last'
                }).reset_index()

                # Prepare for insertion
                insert_records = []
                for _, row in eod_chunk.iterrows():
                    try:
                        insert_records.append((
                            row['timestamp'],
                            'NIFTY',  # All NIFTY weeklies
                            row['strike_price'],
                            row['option_type'],
                            row['expiry'].date(),
                            None,  # open (not in CSV)
                            None,  # high (not in CSV)
                            None,  # low (not in CSV)
                            row['ltp'],  # close = last traded price
                            row['volume'],
                            row['oi'],
                            row['iv'] * 100 if pd.notna(row['iv']) else None,  # Convert to percentage
                            row['delta'],
                            row['gamma'],
                            row['theta'],
                            row['vega'],
                            row['rho']
                        ))
                    except Exception as e:
                        logger.debug(f"Row error: {e}")
                        continue

                # Insert chunk
                if insert_records:
                    cur = conn.cursor()
                    execute_batch(cur, """
                        INSERT INTO option_bars_daily (timestamp, symbol, strike, option_type, expiry,
                                                      open, high, low, close, volume, open_interest,
                                                      iv, delta, gamma, theta, vega, rho)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (timestamp, symbol, strike, option_type, expiry)
                        DO UPDATE SET close = EXCLUDED.close, iv = EXCLUDED.iv
                    """, insert_records, page_size=500)
                    conn.commit()
                    cur.close()

                    total_inserted += len(insert_records)
                    logger.info(f"  [OK] Inserted {len(insert_records):,} EOD records (Total: {total_inserted:,})")

            except Exception as e:
                logger.error(f"  [ERROR] Chunk {chunk_num} failed: {e}")
                continue

            # Process all chunks - full 13.7M rows
            # Progress update every 50 chunks
            if chunk_num % 50 == 0:
                logger.info(f"  [PROGRESS] {chunk_num} chunks processed, {total_inserted:,} EOD records so far")

        # Final stats
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM option_bars_daily")
        final_count = cur.fetchone()[0]

        if final_count > 0:
            cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM option_bars_daily")
            min_ts, max_ts = cur.fetchone()

            logger.info(f"\n" + "="*80)
            logger.info(f"[OK] REAL KAGGLE DATA LOADED!")
            logger.info(f"="*80)
            logger.info(f"Records: {final_count:,}")
            logger.info(f"Date range: {min_ts.date()} to {max_ts.date()}")
            logger.info(f"All Greeks included: IV, Delta, Gamma, Theta, Vega, Rho")
            return True
        else:
            logger.error("[ERROR] No records inserted")
            return False

        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = process_real_data()
    if not success:
        logger.error("\n[FAIL] Failed")
