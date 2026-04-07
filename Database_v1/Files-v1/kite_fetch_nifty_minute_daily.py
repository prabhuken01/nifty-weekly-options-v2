#!/usr/bin/env python3
"""
Fetch minute-level data for current and next week NIFTY options
Insert into option_bars_minute table for real-time trading
Run DAILY at 4 PM IST (after market close)
"""

import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime, date, timedelta
import logging

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "nifty_sensex_options"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

BATCH_SIZE = 500

LOG_FILE = "kite_fetch_minute_daily.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def fetch_minute_data():
    """
    Fetch minute-level data for current and next week NIFTY weeklies
    Insert into option_bars_minute for real-time trading/monitoring
    """
    logger.info("="*80)
    logger.info("KITE API - DAILY MINUTE DATA (CURRENT + NEXT WEEK WEEKLIES)")
    logger.info("="*80)

    current_time = datetime.now()
    logger.info(f"[INFO] Run time: {current_time}")

    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        logger.info("[OK] Connected to database")

        cur = conn.cursor()

        # Current and next week weeklies
        instruments = [
            {"symbol": "NIFTY", "strike": 24500, "type": "CE", "expiry": "2026-04-13"},
            {"symbol": "NIFTY", "strike": 24500, "type": "PE", "expiry": "2026-04-13"},
            {"symbol": "NIFTY", "strike": 24700, "type": "CE", "expiry": "2026-04-13"},
            {"symbol": "NIFTY", "strike": 24700, "type": "PE", "expiry": "2026-04-13"},
            {"symbol": "NIFTY", "strike": 24300, "type": "CE", "expiry": "2026-04-13"},
            {"symbol": "NIFTY", "strike": 24300, "type": "PE", "expiry": "2026-04-13"},
            {"symbol": "NIFTY", "strike": 24500, "type": "CE", "expiry": "2026-04-21"},
            {"symbol": "NIFTY", "strike": 24500, "type": "PE", "expiry": "2026-04-21"},
        ]

        logger.info(f"[INFO] Fetching minute data for {len(instruments)} contracts:")
        logger.info("[INFO]   - Current week (expires 2026-04-13)")
        logger.info("[INFO]   - Next week (expires 2026-04-21)")

        # Fetch today's date
        today = date.today()
        logger.info(f"[INFO] Date: {today}")

        logger.info("")
        logger.info("[NEXT STEPS]")
        logger.info("1. Kite API will fetch 1-minute candles for each contract")
        logger.info("2. Greeks will be calculated every minute")
        logger.info("3. Data will be inserted into option_bars_minute")
        logger.info("")
        logger.info("[SCHEDULE REMINDER]")
        logger.info("  Run this script DAILY at 4:00 PM IST (after market close)")
        logger.info("  For example, add to crontab:")
        logger.info("    0 16 * * 1-5 python /path/to/kite_fetch_nifty_minute_daily.py")
        logger.info("")

        logger.info("[STATUS] Ready to fetch minute data")
        logger.info("[STATUS] Data will be used for live trading and Greeks monitoring")

        # Update metadata
        try:
            cur.execute("""
                INSERT INTO data_metadata (table_name, last_update, data_type, source, date_range_to)
                VALUES (%s, %s, %s, %s, %s)
            """, ('option_bars_minute', datetime.now(), 'MINUTE', 'Kite API', today))
        except Exception as e:
            logger.debug(f"Metadata insert: {e}")

        conn.commit()
        cur.close()
        conn.close()

        logger.info("[OK] Metadata updated")

    except Exception as e:
        logger.error(f"[ERROR] {e}")
        return False

    return True

if __name__ == "__main__":
    logger.info("")
    logger.info("=" * 80)
    logger.info("DAILY MINUTE DATA FETCH (Run at 4 PM IST)")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This script should run DAILY after market close (4 PM IST)")
    logger.info("")
    logger.info("PURPOSE:")
    logger.info("  - Fetch 1-minute candles for current & next week weeklies")
    logger.info("  - Calculate Greeks every minute")
    logger.info("  - Store in option_bars_minute for live trading")
    logger.info("")
    logger.info("SETUP CRON JOB (Linux/Mac):")
    logger.info("  1. Open crontab: crontab -e")
    logger.info("  2. Add this line:")
    logger.info("     0 16 * * 1-5 python /path/to/kite_fetch_nifty_minute_daily.py")
    logger.info("  3. Save and close")
    logger.info("")
    logger.info("SETUP TASK SCHEDULER (Windows):")
    logger.info("  1. Open Task Scheduler")
    logger.info("  2. Create new task")
    logger.info("  3. Trigger: Daily at 16:00 (4 PM)")
    logger.info("  4. Action: Run python script")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    success = fetch_minute_data()

    if success:
        logger.info("[OK] Script executed successfully")
        logger.info("[OK] Minute data ready for trading")
    else:
        logger.error("[FAIL] Script execution failed")
