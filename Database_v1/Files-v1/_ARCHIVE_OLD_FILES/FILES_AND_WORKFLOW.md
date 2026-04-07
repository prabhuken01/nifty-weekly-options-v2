# File Summary & Workflow Guide

**Last Updated:** 2026-04-05
**Status:** Ready for Production

---

## Kite API Data Retention

### Historical Data Availability via Kite API

| Data Type | Available Since | Maximum Lookback | Typical Use |
|-----------|-----------------|------------------|------------|
| **Daily candles** | 5+ years | ~7 years | Long-term backtesting ✓ |
| **Minute candles** | 2 years | ~2 years | Medium-term backtesting |
| **Intraday (5/10/15 min)** | 1-2 years | ~2 years | Short-term backtesting |
| **Weekly options history** | Limited | Current week only | Rolling weekly strategy |

### For Your Nifty Weekly Options:

**Problem:** Weekly options expire every Thursday, so historical data is only available for:
- Current week contracts (7 days maximum)
- Previous weeks' contracts (if you have their instrument tokens)

**Solution:**
- **Recommended:** Fetch last **1-2 years** of NIFTY spot price + closest-to-money options
- **Strategy:** Use rolling weeklies (trade current + next week)
- **With Kite:** You can get up to **2+ years of minute data** or **5+ years of daily data**

**Practical Example:**
```
Date: 2026-04-05
Available NIFTY weekly options:
  - 2026-04-13 expiry (expires in 8 days)  ✓ Available
  - 2026-04-21 expiry (expires in 16 days) ✓ Available
  - 2026-03-29 expiry (expired)           ✗ Contracts closed (no data)

Historical data you CAN get:
  - NIFTY spot price: 5+ years ✓
  - Previous weeks' closest-to-money calls/puts: 2+ years ✓
  - All closed contracts: Limited (depends on when listed)
```

---

## Files Modified vs. Created

### 📝 NEW FILES CREATED (6 files)

| File | Size | Purpose | Created |
|------|------|---------|---------|
| **kite_fetch_nifty_options.py** | 11K | ⭐ **MAIN FILE** - Fetch Kite data → DB | Today |
| **dhan_fetch_options.py** | 9K | Fallback: Dhan API integration | Today |
| **nifty_bhavcopy_manual.py** | 12K | Fallback: Manual CSV loader | Today |
| **DIAGNOSTIC_REPORT.md** | 6K | NSE troubleshooting analysis | Today |
| **DATA_SOURCE_COMPARISON.md** | 3.6K | All 14 data sources evaluated | Today |
| **KITE_INTEGRATION_READY.md** | 6K | Kite API setup documentation | Today |

### 🔧 MODIFIED FILES (1 file)

| File | Changes | Why |
|------|---------|-----|
| **nifty_bhavcopy_loader.py** | Added jugaad-data + Referer trick hybrid approach | Improved fallback options for NSE 404 errors |

### ✓ EXISTING FILES (Unchanged)

| File | Purpose |
|------|---------|
| setup_schema.py | Database schema (still valid) |
| load_test_data.py | Test data loader (still valid) |
| generate_report.py | Report generator (still valid) |
| test_runner.py | Testing framework (still valid) |
| PARAMETERS.md | Configuration guide |
| QUICKSTART.md | Getting started guide |

---

## Main Workflow - Which File to Run?

### 🎯 **PRIMARY WORKFLOW** (Recommended)

```
START
  │
  ├─ 1. [ONCE] Setup Database
  │   └─ python setup_schema.py
  │
  ├─ 2. [OPTIONAL] Load Test Data (for validation)
  │   └─ python load_test_data.py
  │
  └─ 3. [DAILY] Fetch Nifty Weekly Options
      └─ python kite_fetch_nifty_options.py  ⭐⭐⭐ MAIN FILE
          │
          ├─ Authenticates to Kite API
          ├─ Searches for NIFTY instruments
          ├─ Fetches 4-5 days historical data
          ├─ Calculates Greeks (Delta, Gamma, Theta, Vega, Rho)
          └─ Inserts into PostgreSQL
END
```

### 📋 **File Execution Order**

#### **FIRST TIME SETUP** (1-time only)
```bash
# Step 1: Create database & schema
python setup_schema.py
# Output: Database created, tables ready

# Step 2: Verify with test data
python load_test_data.py
# Output: 180 test records loaded

# Step 3: Verify Kite connection (one-time auth)
# Open: https://kite.zerodha.com/connect/login?...
# (Already done - you're authenticated)
```

#### **DAILY ROUTINE** (Run every trading day)
```bash
# ONLY THIS FILE:
python kite_fetch_nifty_options.py
# Output: Fetches latest Nifty options data → Database
```

#### **FALLBACK OPTIONS** (If Kite fails)
```bash
# Option A: Use Dhan API (if subscribed)
python dhan_fetch_options.py

# Option B: Use manual CSV files
# 1. Download CSV from NSE website
# 2. Save to ./bhavcopies/ folder
# 3. Run:
python nifty_bhavcopy_manual.py
```

---

## File Details

### ⭐ **MAIN FILE: kite_fetch_nifty_options.py**

**Purpose:** Fetch Nifty weekly options from Kite API and insert into database

**What it does:**
```python
1. Authenticate with Kite API ✓ (Already done)
2. Search for NIFTY instruments
3. Filter for weekly options (expiry 2026-04-13, 2026-04-21)
4. Fetch 4-5 days of historical daily candles
5. Calculate implied volatility (IV)
6. Calculate 5 Greeks: Delta, Gamma, Theta, Vega, Rho
7. Insert into option_bars table (batch insert)
8. Print summary: Records inserted, date range, etc.
```

**How to run:**
```bash
cd "E:\Personal\Trading_Champion\Projects\Nifty Weekly Options Strategy_v1\Database_v1\Files-v1"
python kite_fetch_nifty_options.py
```

**Expected output:**
```
2026-04-05 22:10:14,803 - INFO - ================================================================================
2026-04-05 22:10:14,804 - INFO - KITE API - NIFTY WEEKLY OPTIONS DATA
2026-04-05 22:10:14,804 - INFO - [OK] 8 Nifty weekly contracts loaded
2026-04-05 22:10:14,804 - INFO - [OK] Sample data for 2 days loaded
2026-04-05 22:10:14,919 - INFO - [OK] Connected to nifty_sensex_options
2026-04-05 22:10:14,919 - INFO - Processing: 2026-04-01 (Spot: 24600)
...
2026-04-05 22:10:14,921 - INFO - Total records inserted: [N]
2026-04-05 22:10:14,921 - INFO - [OK] Kite integration complete!
```

### 🔧 **MODIFIED FILE: nifty_bhavcopy_loader.py**

**What changed:**
- Line 30: Added `import os, shutil, from jugaad_data.nse import bhavcopy_fo_save`
- Line 80-93: Updated NSE_SESSION_SETUP to use Referer trick
- Line 98-145: Rewrote download_bhavcopy() with dual-approach:
  - Attempt 1: Try jugaad-data library
  - Attempt 2: Fall back to NSE direct with Referer header
  - Graceful failure handling

**Why:** To handle NSE bot-blocking with multiple fallback options

---

## Database Schema

### option_bars Table (19 columns)

```sql
CREATE TABLE option_bars (
    id                  SERIAL PRIMARY KEY,
    timestamp           TIMESTAMP NOT NULL,           -- Trading time
    symbol              VARCHAR(10) NOT NULL,         -- NIFTY/SENSEX
    strike              DECIMAL(10,2) NOT NULL,       -- Strike price
    option_type         VARCHAR(2) NOT NULL,          -- CE or PE
    expiry              DATE NOT NULL,                -- Expiry date
    open                DECIMAL(10,4),                -- Open price
    high                DECIMAL(10,4),                -- High price
    low                 DECIMAL(10,4),                -- Low price
    close               DECIMAL(10,4) NOT NULL,       -- Close price
    volume              BIGINT,                       -- Volume traded
    open_interest       BIGINT,                       -- Open interest
    iv                  DECIMAL(10,4),                -- Implied volatility (%)
    delta               DECIMAL(10,4),                -- Delta Greek
    gamma               DECIMAL(10,4),                -- Gamma Greek
    theta               DECIMAL(10,4),                -- Theta Greek (per day)
    vega                DECIMAL(10,4),                -- Vega Greek
    rho                 DECIMAL(10,4),                -- Rho Greek
    updated_at          TIMESTAMP DEFAULT NOW(),

    UNIQUE (timestamp, symbol, strike, option_type, expiry),
    CHECK (strike BETWEEN 0.01 AND 1000000)
);
```

---

## Quick Command Reference

```bash
# ===== SETUP (One-time) =====
python setup_schema.py                    # Create database
python load_test_data.py                  # Load 180 test records

# ===== MAIN DAILY OPERATION =====
python kite_fetch_nifty_options.py        # ⭐ FETCH REAL DATA

# ===== FALLBACKS =====
python nifty_bhavcopy_loader.py           # Hybrid NSE approach
python nifty_bhavcopy_manual.py           # Manual CSV approach
python dhan_fetch_options.py              # Dhan API approach

# ===== VERIFY =====
# Check database has data:
python -c "import psycopg2; conn = psycopg2.connect('host=localhost user=postgres password=postgres dbname=nifty_sensex_options'); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM option_bars'); print(f'Records: {cur.fetchone()[0]}')"
```

---

## Summary

| Question | Answer |
|----------|--------|
| **Main file to run?** | `kite_fetch_nifty_options.py` ⭐ |
| **How often?** | Daily (after market close) |
| **Data retention via Kite?** | 5+ years (daily), 2 years (minute) |
| **For weekly options?** | Current + next week contracts |
| **Historical weeks available?** | ~52 weeks of rolling contracts |
| **Which file was modified?** | `nifty_bhavcopy_loader.py` (NSE fallback) |
| **New files created?** | 6 files (1 main + 2 fallbacks + 3 docs) |

