#!/usr/bin/env python3
"""
Step 2: Fetch 6 months of NIFTY daily options data
Supports: Breeze API > Kaggle > Kite API > Test Data (in priority order)
Insert into option_bars_daily table for backtesting
Run ONCE after database setup
"""

import logging
import sys
from pathlib import Path

LOG_FILE = "kite_fetch_daily_6months.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main - import and run unified fetcher"""
    logger.info("="*80)
    logger.info("STEP 2: 6-MONTH DAILY DATA BACKFILL")
    logger.info("="*80)
    logger.info("")
    logger.info("This script uses the best available data source:")
    logger.info("  1. Breeze API (if ICICI credentials found)")
    logger.info("  2. Kaggle (if kaggle.json found)")
    logger.info("  3. Kite API (if session active)")
    logger.info("  4. Test Data (fallback)")
    logger.info("")
    logger.info("See SETUP_BREEZE_OR_KAGGLE.md for setup instructions")
    logger.info("")

    try:
        # Import unified fetcher
        from kite_fetch_unified import fetch_historical_data

        # Run it
        success = fetch_historical_data()

        logger.info("")
        logger.info("="*80)
        if success:
            logger.info("[OK] Step 2 Complete: Historical data loaded")
            logger.info("[NEXT] Run Step 3 at 4 PM daily: python kite_fetch_nifty_minute_daily.py")
        else:
            logger.info("[WARN] Step 2 using fallback data")
            logger.info("[ACTION] Set up Breeze or Kaggle for real data")
        logger.info("="*80)

        return success

    except Exception as e:
        logger.error(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
