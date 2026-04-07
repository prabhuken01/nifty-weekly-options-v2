#!/usr/bin/env python3
"""
================================================================================
QUICK START GUIDE: NIFTY/SENSEX OPTIONS LOADER
================================================================================

This guide walks you through setup, installation, and execution.
Time estimate: 45-60 minutes runtime + 10 minutes setup
Token usage: ~6% of session (optimized for constraints)

STEP 0: PRE-REQUISITES
================================================================================

You must have:
1. PostgreSQL running locally (default: localhost:5432)
2. Database 'nifty_sensex_options' created with 'option_bars' table
3. Python 3.8+ installed
4. ~500 MB free disk space for NSE downloads

If database doesn't exist, create it first:

    psql -U postgres -c "CREATE DATABASE nifty_sensex_options;"
    psql -U postgres -d nifty_sensex_options < schema.sql

(See schema.sql below)

================================================================================

STEP 1: CREATE DATABASE SCHEMA
================================================================================

Run this in DBeaver or psql:

------- BEGIN SQL -------

CREATE DATABASE IF NOT EXISTS nifty_sensex_options;

CREATE TABLE option_bars (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    strike DECIMAL(10, 2) NOT NULL,
    option_type VARCHAR(2) NOT NULL,
    expiry DATE NOT NULL,
    open DECIMAL(10, 4),
    high DECIMAL(10, 4),
    low DECIMAL(10, 4),
    close DECIMAL(10, 4) NOT NULL,
    volume BIGINT,
    open_interest BIGINT,
    iv DECIMAL(10, 4),
    delta DECIMAL(10, 4),
    gamma DECIMAL(10, 4),
    theta DECIMAL(10, 4),
    vega DECIMAL(10, 4),
    rho DECIMAL(10, 4),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_option_bar UNIQUE (timestamp, symbol, strike, option_type, expiry),
    CONSTRAINT strike_range CHECK (strike BETWEEN 0.01 AND 1000000)
);

CREATE INDEX idx_timestamp_symbol_strike ON option_bars(timestamp DESC, symbol, strike);
CREATE INDEX idx_expiry_symbol ON option_bars(expiry, symbol);

------- END SQL -------

Expected output: "CREATE TABLE", "CREATE INDEX" messages

================================================================================

STEP 2: INSTALL PYTHON DEPENDENCIES
================================================================================

Open terminal and run:

    pip install psycopg2-binary pandas requests numpy

That's it! (py_vollib used, but Black-Scholes implemented natively)

Verify installation:

    python -c "import psycopg2; import pandas; import requests; print('✓ All deps OK')"

================================================================================

STEP 3: CONFIGURE SCRIPT PARAMETERS
================================================================================

Open nifty_bhavcopy_loader.py in your editor.

CRITICAL: Update these parameters:

    # DATABASE SECTION (Line ~40)
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_NAME = "nifty_sensex_options"
    DB_USER = "postgres"
    DB_PASSWORD = "postgres"  # ← CHANGE THIS to your password

    # SCOPE SECTION (Line ~48)
    MONTHS_TO_FETCH = 2  # Set to 6 for full 6-month load
                         # Set to 2 for quick test (~2000-3000 rows)

OPTIONAL: Adjust filtering parameters:

    # FILTERING PARAMETERS (Line ~57)
    MIN_DTE = 1              # Keep options 1-7 days from expiry
    MAX_DTE = 7
    MIN_MONEYNESS_PCT = 1.5  # Keep strikes 1.5%-4.5% OTM
    MAX_MONEYNESS_PCT = 4.5

All other parameters have reasonable defaults.

================================================================================

STEP 4: RUN THE SCRIPT
================================================================================

Terminal command:

    python nifty_bhavcopy_loader.py

Expected output (sample):

    ================================================================================
    NIFTY/SENSEX WEEKLY OPTIONS LOADER - DAY 1 MORNING 5-STEP PROCESS
    ================================================================================
    Date range: 2026-02-05 to 2026-04-05
    Symbols: ['NIFTY', 'SENSEX']
    DTE range: 1-7
    Moneyness: 1.5%-4.5%
    Risk-free rate: 6.5%
    ================================================================================
    ✓ Connected to nifty_sensex_options@localhost

    ================================================================================
    PROCESSING: 2026-02-05 (Thursday)
    ================================================================================
    Downloading: 2026-02-05 (https://archives.nseindia.com/...)
      ✓ Downloaded 1234 rows for 2026-02-05
    STEP 2: Filter by symbol & immediate expiry
      FILTER 1: Symbol in ['NIFTY', 'SENSEX']
        → 847 rows remain
      FILTER 2: Option type in ['CE', 'PE']
        → 847 rows remain
      FILTER 3: Days to expiry (1-7)
        → 123 rows remain
    STEP 3: Filter by moneyness (1.5%-4.5%)
      FILTER 4: Moneyness (1.5%-4.5%)
        NIFTY spot: 24500.00
        SENSEX spot: 78500.00
        → 45 rows remain
    STEP 4: Calculate implied volatility (Black-Scholes)
      CALCULATE IV: Black-Scholes Newton-Raphson solver
        ✓ IV calculated: 45/45 (100%)
        ✓ IV nulls: 0/45 (0%)
    STEP 5: Calculate Greeks (Delta, Gamma, Theta, Vega, Rho)
      CALCULATE GREEKS: Delta, Gamma, Theta, Vega, Rho
        ✓ Greeks calculated: 45/45 rows
    INSERTING into PostgreSQL
      ✓ 45 rows inserted for 2026-02-05

    ================================================================================
    PROCESSING: 2026-02-06 (Friday)
    ================================================================================
    ...
    (Continues for all dates in range)

RUNTIME EXPECTATIONS:

- 2-month load: 45-60 minutes (40-50 trading days, ~2000-3000 rows)
- 6-month load: 120-180 minutes (~120 trading days, ~6000-7000 rows)

Monitor progress in terminal. Log also saved to:

    nifty_bhavcopy_loader.log

================================================================================

STEP 5: VALIDATE DATA IN DATABASE
================================================================================

After script completes, verify data in DBeaver:

Run Query #1: Row count by symbol

    SELECT symbol, COUNT(*) as cnt, COUNT(DISTINCT DATE(timestamp)) as days
    FROM option_bars
    GROUP BY symbol
    ORDER BY symbol;

Expected result:

    | symbol | cnt  | days |
    |--------|------|------|
    | NIFTY  | 1000 | 40   |
    | SENSEX | 1000 | 40   |

Run Query #2: Date range check

    SELECT 
      MIN(DATE(timestamp)) as start_date, 
      MAX(DATE(timestamp)) as end_date,
      COUNT(DISTINCT DATE(timestamp)) as trading_days
    FROM option_bars;

Expected: Continuous date range from START_DATE to END_DATE (weekdays only)

Run Query #3: IV statistics

    SELECT 
      symbol,
      COUNT(*) as cnt,
      ROUND(AVG(iv), 2) as avg_iv,
      ROUND(MIN(iv), 2) as min_iv,
      ROUND(MAX(iv), 2) as max_iv,
      ROUND(100.0 * SUM(CASE WHEN iv IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as null_pct
    FROM option_bars
    WHERE iv IS NOT NULL
    GROUP BY symbol
    ORDER BY symbol;

Expected: IV between 10%-35%, <5% nulls

Run Query #4: Greeks statistics

    SELECT 
      COUNT(*) as total_rows,
      ROUND(100.0 * SUM(CASE WHEN delta IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as delta_pct,
      ROUND(100.0 * SUM(CASE WHEN gamma IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as gamma_pct,
      ROUND(100.0 * SUM(CASE WHEN theta IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as theta_pct,
      ROUND(100.0 * SUM(CASE WHEN vega IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as vega_pct,
      ROUND(100.0 * SUM(CASE WHEN rho IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as rho_pct
    FROM option_bars;

Expected: 95%+ coverage for all Greeks

Run Query #5: Sample records (visual inspection)

    SELECT 
      timestamp, symbol, strike, option_type, close, iv, delta, gamma, theta, vega
    FROM option_bars
    WHERE DATE(timestamp) = (SELECT MAX(DATE(timestamp)) FROM option_bars)
    ORDER BY symbol, strike, option_type
    LIMIT 10;

Expected: Realistic option prices, IV 10-35%, Greeks within ranges

================================================================================

TROUBLESHOOTING
================================================================================

ISSUE: "psycopg2.OperationalError: connection failed"

  Solution:
  1. Check PostgreSQL is running: `psql -U postgres`
  2. Verify DB exists: `psql -U postgres -l | grep nifty_sensex`
  3. Check password in script matches actual password
  4. Check DB_HOST and DB_PORT are correct

---

ISSUE: "RequestException: HTTPError 404" or "No such file or directory"

  Solution:
  1. NSE archives may have downtime or missing dates
  2. Script logs warnings but continues to next date
  3. Check nifty_bhavcopy_loader.log for exact failed dates
  4. Weekend dates automatically skipped

---

ISSUE: "ValueError: No solution found for IV" or many NULL IVs

  Solution:
  1. Option price may be outside market bounds
  2. Script handles gracefully, NULL < 5% expected
  3. Check CLOSE prices are realistic (not 0 or infinity)

---

ISSUE: "UNIQUE constraint violated"

  Solution:
  1. Duplicate dates/symbols/strikes in raw data (rare)
  2. Script handles via ON CONFLICT DO UPDATE
  3. Re-run script safely; duplicates updated, not inserted twice

---

ISSUE: Script takes longer than expected

  Solution:
  1. Network speed: NSE archives may be slow
  2. DB speed: Check disk space, PostgreSQL load
  3. CPU: IV calculation is iterative (30-50 iterations per option)
  4. Reduce BATCH_SIZE (line ~77) from 500 to 100 if memory constrained

================================================================================

ADVANCED: PARAMETER TUNING
================================================================================

To optimize for your use case:

1. FASTER PROCESSING (fewer rows):
   - Reduce MONTHS_TO_FETCH (1-2 months)
   - Increase MIN_MONEYNESS_PCT / decrease MAX_MONEYNESS_PCT
   - Reduce BATCH_SIZE for faster commits

2. MORE DATA (longer history):
   - Increase MONTHS_TO_FETCH (up to 12)
   - Expect 180-240 minute runtime
   - Ensure 1+ GB disk space

3. DIFFERENT MONEYNESS RANGE:
   - ATM only: MIN=0, MAX=1.5
   - Deep OTM: MIN=3.5, MAX=6.0
   - All strikes: MIN=0, MAX=100 (warning: very slow)

4. TIGHTER IV TOLERANCE:
   - Decrease IV_PRECISION (e.g., 1e-8)
   - More accurate IV, slower processing

================================================================================

NEXT STEPS (After validation)
================================================================================

1. ✓ Data loaded and validated
2. → Use option_bars for backtesting
3. → Join with index data (NIFTY/SENSEX spot prices)
4. → Calculate daily P&L for option strategies

Ready for Week 1 Day 2 backtest module!

================================================================================
"""

if __name__ == "__main__":
    print(__doc__)
