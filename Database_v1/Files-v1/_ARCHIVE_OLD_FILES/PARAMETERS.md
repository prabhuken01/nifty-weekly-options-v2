#!/usr/bin/env python3
"""
================================================================================
PARAMETER REFERENCE & TUNING GUIDE
================================================================================

This document explains every tunable parameter in nifty_bhavcopy_loader.py
and recommended values for different use cases.

================================================================================
DATABASE PARAMETERS (Lines ~40-45)
================================================================================

DB_HOST = "localhost"
  - PostgreSQL server hostname or IP
  - Use "localhost" or "127.0.0.1" for local database
  - For remote: use actual IP or hostname
  - Example: "192.168.1.100" or "db.company.com"

DB_PORT = 5432
  - PostgreSQL server port
  - Default: 5432
  - Change if your PostgreSQL uses custom port
  - Check: psql -U postgres -c "SELECT inet_server_addr(), inet_server_port();"

DB_NAME = "nifty_sensex_options"
  - Name of database containing option_bars table
  - Must be created before running script
  - Create via: createdb nifty_sensex_options

DB_USER = "postgres"
  - PostgreSQL user account
  - Default: "postgres" (created during PostgreSQL install)
  - For custom user: create via createuser <username>

DB_PASSWORD = "postgres"
  - Password for DB_USER
  - CRITICAL: Change from default!
  - Will be exposed in script; consider using .env file for prod

================================================================================
DOWNLOAD SCOPE (Lines ~48-51)
================================================================================

MONTHS_TO_FETCH = 2
  - How many months of data to download
  - Options:
    • 2 = ~40 trading days, ~2000-3000 rows, ~30-45 min
    • 3 = ~60 trading days, ~3000-4500 rows, ~60-90 min
    • 6 = ~120 trading days, ~6000-7000 rows, ~120-180 min (full spec)
  
  - Recommendation for token constraints: START with 2, verify process, then 6

END_DATE = date.today()
  - Last date to download data for
  - Default: today's date
  - Change to specific date: date(2026, 4, 5) for April 5, 2026

START_DATE = END_DATE - timedelta(days=30 * MONTHS_TO_FETCH)
  - Auto-calculated from MONTHS_TO_FETCH
  - Manual override: date(2025, 10, 1) for Oct 1, 2025
  - Do NOT change unless you want custom date range

================================================================================
FILTERING PARAMETERS (Lines ~57-61)
================================================================================

MIN_DTE = 1
MAX_DTE = 7
  - Days to expiration range
  - Weekly options: 1-7 days to expiry
  - Monthly options: use 1-30 (but plan for fewer rows)
  - ATM only: set MAX_DTE = 1 or 3 (get tighter clustering)
  
  - IMPORTANT: NSE weekly expirations are every Wednesday/Thursday
  - Most liquid options 1-3 days before expiry
  
  Example configurations:
  - Min_DTE=1, Max_DTE=3: Only closest to expiry (highest gamma)
  - Min_DTE=1, Max_DTE=7: Full 1-week window (recommended)
  - Min_DTE=3, Max_DTE=7: Exclude ITM/deep OTM closing days

MIN_MONEYNESS_PCT = 1.5
MAX_MONEYNESS_PCT = 4.5
  - Strike selection as % distance from spot
  - Moneyness = ABS((Strike / Spot - 1) * 100)
  
  Example values:
  If NIFTY spot = 24000:
  - Strike 24000: moneyness = 0% (ATM)
  - Strike 24360: moneyness = 1.5% (0.5% OTM)
  - Strike 24480: moneyness = 2.0% (0.5% OTM)
  - Strike 25080: moneyness = 4.5% (2.25% OTM)
  - Strike 23040: moneyness = 4.0% (on put side, 2.0% OTM)
  
  Recommended ranges:
  - 0.0 - 1.5: Near ATM (highest gamma, most sensitive)
  - 1.5 - 3.0: ATM+OTM sweet spot (good Greeks, data rich)
  - 3.0 - 4.5: Further OTM (lower premium, less data)
  - 0.0 - 6.0: All strikes (for backtest robustness)
  
  Current setting (1.5-4.5): Good balance of liquidity & Greeks sensitivity

================================================================================
CALCULATION PARAMETERS (Lines ~67-70)
================================================================================

RISK_FREE_RATE = 0.065
  - Risk-free rate used in Black-Scholes (RBI repo rate)
  - Current: 6.5% (0.065 as decimal)
  - Update based on current RBI repo rate
  - Check: https://www.rbi.org.in/ or use current T-bill rate
  
  Historical examples:
  - 2024: 6.5%
  - 2023: 6.5%
  - 2022: 4.0-6.5%
  
  Impact:
  - Higher rate → Higher call value, lower put value (minor for 1-week options)
  - For weekly options: impact <5% on Greeks
  
  - ⚠️ IMPORTANT: RBI rate changes monthly; update if not current

IV_PRECISION = 1e-6
  - Convergence tolerance for Newton-Raphson IV solver
  - Options:
    • 1e-4: Fast but less accurate (~0.01% IV error)
    • 1e-6: Default (balanced)
    • 1e-8: Slower, very accurate
  - Tradeoff: accuracy vs. speed (tiny impact on overall runtime)

MAX_IV_ITER = 100
  - Maximum iterations for IV solver (Newton-Raphson)
  - Most options converge in 30-50 iterations
  - Rarely hits this limit; keeps bad data from infinite loops
  - Increase to 150 if IV_PRECISION very tight (1e-8)

================================================================================
SYMBOLS & OPTION TYPES (Lines ~75-78)
================================================================================

SYMBOLS = ['NIFTY', 'SENSEX']
  - Index symbols to fetch
  - Options (limit to reduce data):
    • ['NIFTY'] - NIFTY 50 only
    • ['SENSEX'] - SENSEX 30 only
    • ['NIFTY', 'SENSEX'] - Both (recommended)
  - Do NOT add BANKNIFTY here; requires separate handling (futures different)

OPTION_TYPES = ['CE', 'PE']
  - Call and Put options
  - Leave as-is; rarely need only one type
  - CE = Call option
  - PE = Put option

================================================================================
PROCESSING PARAMETERS (Lines ~83-85)
================================================================================

BATCH_SIZE = 500
  - Rows inserted per batch to PostgreSQL
  - Options:
    • 100: Slower, more frequent commits (safer for crash recovery)
    • 500: Default (good balance)
    • 1000: Faster, heavier memory usage
    • 2000: Very fast but requires 2+ GB RAM
  
  - Tune if you see:
    • Memory errors: Reduce to 250
    • Slow inserts: Increase to 1000
    • Network timeouts: Reduce to 100-200

SLEEP_BETWEEN_REQUESTS = 0.5
  - Seconds to pause between NSE HTTP requests
  - Politeness factor (don't hammer NSE servers)
  - Options:
    • 0.1: Fast (aggressive, not recommended)
    • 0.5: Default (respectful)
    • 1.0: Slow (if NSE is rate-limiting you)
  
  - Impact:
    • 2 months × 40 trading days = 40 downloads
    • 0.5s per download = 20 seconds overhead (minor)
    • Increase if seeing "429 Too Many Requests"

================================================================================
LOGGING (Lines ~91-95)
================================================================================

LOG_FILE = Path(__file__).stem + ".log"
  - Auto-generates filename from script name
  - Output: nifty_bhavcopy_loader.log
  - Contains all progress, errors, debug messages
  - Grows ~100-200 KB per run; safe to delete after review

logging.basicConfig(...) settings:
  - level=logging.INFO: Shows progress & warnings (recommended)
  - Change to DEBUG: Very verbose, includes each row processing
  - handlers: Write to both file and console (good for monitoring)

================================================================================
ADVANCED TUNING BY USE CASE
================================================================================

USE CASE 1: QUICK TEST (5-10 minutes)
  MONTHS_TO_FETCH = 1
  BATCH_SIZE = 500
  MAX_DTE = 3          # Only closest to expiry
  MIN_MONEYNESS_PCT = 1.5
  MAX_MONEYNESS_PCT = 3.0
  → Expect: ~1000-1500 rows, 5-10 min

USE CASE 2: BALANCED (30-45 minutes)
  MONTHS_TO_FETCH = 2  # Default (current)
  BATCH_SIZE = 500
  MAX_DTE = 7          # Full weekly range
  MIN_MONEYNESS_PCT = 1.5
  MAX_MONEYNESS_PCT = 4.5
  → Expect: ~2000-3000 rows, 30-45 min

USE CASE 3: FULL SPECIFICATION (120-180 minutes)
  MONTHS_TO_FETCH = 6
  BATCH_SIZE = 500
  MAX_DTE = 7
  MIN_MONEYNESS_PCT = 1.5
  MAX_MONEYNESS_PCT = 4.5
  → Expect: ~6000-7000 rows, 120-180 min

USE CASE 4: DEEP BACKTEST (180-300 minutes)
  MONTHS_TO_FETCH = 12
  BATCH_SIZE = 500
  MAX_DTE = 7
  MIN_MONEYNESS_PCT = 0.0    # All strikes
  MAX_MONEYNESS_PCT = 100.0
  → Expect: ~12000-15000 rows, 180+ min
  → WARNING: Very resource-intensive

================================================================================
PERFORMANCE MONITORING
================================================================================

Check script progress in terminal:

  - Each date: "PROCESSING: 2026-02-05 (Thursday)"
  - Each step: Progress through 5-step process
  - Each filter: "→ X rows remain" shows filtering effectiveness
  - IV calc: "✓ IV calculated: 45/45 (100%)"
  - Greeks: "✓ Greeks calculated: 45/45 rows"
  - Insert: "✓ 45 rows inserted for 2026-02-05"

If slow (>2 min per day):
  - Check network: NSE archives may be slow
  - Check CPU: IV solver is compute-intensive
  - Reduce BATCH_SIZE to reduce memory footprint
  - Increase SLEEP_BETWEEN_REQUESTS: it's not the issue

If memory errors:
  - Reduce BATCH_SIZE (e.g., 250)
  - Reduce MONTHS_TO_FETCH
  - Monitor RAM during run: top or Task Manager

================================================================================
PRODUCTION DEPLOYMENT
================================================================================

For production/scheduled runs:

1. Store password in environment variable:
   
   export DB_PASSWORD="your_password"
   
   Then in script:
   DB_PASSWORD = os.environ.get('DB_PASSWORD', 'default')

2. Add error notification (email/Slack on failure)

3. Schedule via cron (Linux/Mac) or Task Scheduler (Windows):
   
   # Daily 7 PM
   0 19 * * * cd /path && python nifty_bhavcopy_loader.py >> /var/log/loader.log 2>&1

4. Monitor log file for errors

5. Add validation queries to auto-check data quality post-load

================================================================================
"""

# Parameters as Python dictionary (for programmatic use)
PARAMETER_DEFAULTS = {
    'database': {
        'DB_HOST': 'localhost',
        'DB_PORT': 5432,
        'DB_NAME': 'nifty_sensex_options',
        'DB_USER': 'postgres',
    },
    'scope': {
        'MONTHS_TO_FETCH': 2,
        'END_DATE': 'date.today()',
    },
    'filtering': {
        'MIN_DTE': 1,
        'MAX_DTE': 7,
        'MIN_MONEYNESS_PCT': 1.5,
        'MAX_MONEYNESS_PCT': 4.5,
    },
    'calculation': {
        'RISK_FREE_RATE': 0.065,
        'IV_PRECISION': 1e-6,
        'MAX_IV_ITER': 100,
    },
    'processing': {
        'BATCH_SIZE': 500,
        'SLEEP_BETWEEN_REQUESTS': 0.5,
    }
}

if __name__ == "__main__":
    print(__doc__)
