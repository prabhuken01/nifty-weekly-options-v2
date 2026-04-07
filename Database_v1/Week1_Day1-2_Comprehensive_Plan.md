# WEEK 1: DAY 1-2 COMPREHENSIVE EXECUTION PLAN
## Data Load: Oct 2025 - Apr 2026 (NIFTY & SENSEX Weekly Options)

---

## PART 1: EXECUTION PLAN & TASKS

| Task # | Action | Tool/Method | Input | Processing | Output/Check | Duration | Status |
|--------|--------|-------------|-------|-----------|--------------|----------|--------|
| 1 | Create PostgreSQL Schema | DBeaver SQL Editor | None | CREATE TABLE option_bars with indexes | Schema visible in DB nifty_sensex_options | 10 min | Ready |
| 2 | Fetch 6-month Bhavcopy | Python script (Claude Haiku) | NSE CSV daily files (Oct 2025-Apr 2026) | Download & parse ~180 files | ~180 days × 2 symbols loaded | 30 min | Pending |
| 3 | Filter Data (Immediate Expiry) | Python logic | Raw bhavcopy data | Keep only <7 days to expiry | Filtered DF (~5K-7K rows) | 10 min | Pending |
| 4 | Filter Strikes (1.5%-4.5% moneyness) | Python logic | Filtered data | Calculate (strike/spot - 1)*100, filter | Target strike prices only | 10 min | Pending |
| 5 | Calculate Implied Volatility (IV) | py_vollib Black-Scholes solver | Option price, spot, strike, DTE | Newton-Raphson IV solver (~50 iter) | IV % column populated (<5% NULL) | 45 min | Pending |
| 6 | Calculate Greeks (5 metrics) | py_vollib derivatives | IV % + market params (r=0.065) | Delta, Gamma, Theta/365, Vega/100, Rho/100 | 5 Greeks columns populated | 30 min | Pending |
| 7 | Batch Insert to PostgreSQL | psycopg2.execute_batch() | Processed Pandas DataFrame | INSERT INTO option_bars (...) ON CONFLICT UPDATE | Rows indexed, ready for query | 15 min | Pending |
| 8 | Validation & Checksum | DBeaver SQL queries | PostgreSQL option_bars table | COUNT rows, check NULL%, date range, IV stats | Validation report (10 queries) | 10 min | Pending |

**Total Estimated Time: 2.5 - 3 hours (mostly script runtime)**

---

## PART 2: DATABASE SCHEMA - COLUMN DETAILS

### CREATE TABLE Statement (Run in DBeaver)

```sql
CREATE DATABASE nifty_sensex_options;

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
```

### Column Definitions

| Column | Type | Constraints | Source | Description | Example | NULL% | Index |
|--------|------|-------------|--------|-------------|---------|-------|-------|
| id | SERIAL | PRIMARY KEY | Auto | Unique row identifier | 1, 2, 3... | 0% | YES (PK) |
| **timestamp** | TIMESTAMP | NOT NULL, INDEX | NSE Bhavcopy | Market close date-time (YYYY-MM-DD HH:MM:SS) | 2026-01-15 15:30:00 | 0% | YES (DESC) |
| **symbol** | VARCHAR(10) | NOT NULL, INDEX | Filename | Index symbol (NIFTY or SENSEX only) | NIFTY, SENSEX | 0% | YES |
| **strike** | DECIMAL(10,2) | NOT NULL, CHECK | Bhavcopy | Strike price (multiple of 0.5) | 23500.00, 23500.50, 24000.00 | 0% | YES |
| **option_type** | VARCHAR(2) | NOT NULL | Bhavcopy | Call or Put (CE, PE) | CE, PE | 0% | NO |
| **expiry** | DATE | NOT NULL, INDEX | Contract spec | Expiration date (YYYY-MM-DD) | 2026-01-16, 2026-01-23 | 0% | YES |
| open | DECIMAL(10,4) | NULLABLE | OHLC | Opening price of the day | 125.5000, 125.2500 | <1% | NO |
| high | DECIMAL(10,4) | NULLABLE | OHLC | Highest price of the day | 128.7500 | <1% | NO |
| low | DECIMAL(10,4) | NULLABLE | OHLC | Lowest price of the day | 124.5000 | <1% | NO |
| **close** | DECIMAL(10,4) | NOT NULL | LTP | Closing/Last Traded Price | 126.2500 | 0% | NO |
| volume | BIGINT | NULLABLE | Bhavcopy | Total contracts traded | 150000, 250000 | 2-3% | NO |
| open_interest | BIGINT | NULLABLE | Bhavcopy | Open contracts held (OI) | 500000, 750000 | 2-3% | NO |
| **iv** | DECIMAL(10,4) | NULLABLE | **CALCULATED** | Implied Volatility (%) | 18.5000, 22.3500, 16.2500 | <5% | NO |
| **delta** | DECIMAL(10,4) | NULLABLE | FROM IV | Sensitivity to spot price (-1 to +1) | 0.6500 (CE), -0.3400 (PE) | <5% | NO |
| **gamma** | DECIMAL(10,4) | NULLABLE | FROM IV | Rate of change of delta (0 to 1) | 0.0125, 0.0250 | <5% | NO |
| **theta** | DECIMAL(10,4) | NULLABLE | FROM IV | Time decay per day (365-normalized) | -0.1500, 0.2000 | <5% | NO |
| **vega** | DECIMAL(10,4) | NULLABLE | FROM IV | Sensitivity to 1% IV change | 0.4500, 0.8000 | <5% | NO |
| **rho** | DECIMAL(10,4) | NULLABLE | FROM IV | Sensitivity to 1% interest rate change | 0.0150, 0.0300 | <5% | NO |
| updated_at | TIMESTAMP | DEFAULT NOW() | Auto | Last record update timestamp | 2026-01-20 10:30:15 | 0% | NO |

---

## PART 3: EXPECTED DATA SAMPLE

### Sample Rows (Oct 2025 - Apr 2026)

| timestamp | symbol | strike | option_type | expiry | close | iv(%) | delta | gamma | theta | vega | DTE | moneyness% |
|-----------|--------|--------|-------------|--------|-------|-------|-------|-------|-------|------|-----|------------|
| 2025-10-01 15:30 | NIFTY | 23500.00 | CE | 2025-10-08 | 126.25 | 18.50 | 0.6500 | 0.0125 | -0.1500 | 0.4500 | 7 | 2.15 |
| 2025-10-01 15:30 | NIFTY | 23500.00 | PE | 2025-10-08 | 125.50 | 17.80 | -0.3400 | 0.0128 | -0.1600 | 0.4200 | 7 | 2.15 |
| 2025-10-01 15:30 | NIFTY | 24000.00 | CE | 2025-10-08 | 76.50 | 20.10 | 0.4200 | 0.0145 | -0.1200 | 0.5100 | 7 | -1.06 |
| 2025-10-01 15:30 | SENSEX | 78500.00 | CE | 2025-10-08 | 187.25 | 19.20 | 0.6700 | 0.0110 | -0.1450 | 0.4800 | 7 | 1.95 |
| 2026-04-30 15:30 | NIFTY | 25000.00 | CE | 2026-05-07 | 97.25 | 16.50 | 0.7100 | 0.0115 | -0.1350 | 0.4200 | 7 | 3.22 |
| 2026-04-30 15:30 | NIFTY | 25000.00 | PE | 2026-05-07 | 93.75 | 16.20 | -0.2900 | 0.0118 | -0.1420 | 0.4000 | 7 | 3.22 |
| 2026-04-30 15:30 | SENSEX | 78500.00 | PE | 2026-05-07 | 185.50 | 18.90 | -0.3200 | 0.0112 | -0.1380 | 0.4600 | 7 | -0.32 |

**Expected row count: 5,000 - 7,000 rows (180 days × 2 symbols × 15-20 strikes × 2 option types)**

---

## PART 4: IV & GREEKS CALCULATION FORMULAS

### INPUT PARAMETERS

| Symbol | Definition | Source | Example |
|--------|-----------|--------|---------|
| **S** | Spot Price (Underlying) | NSE index close | 24500.00 |
| **K** | Strike Price | Bhavcopy | 23500.00 |
| **T** | Time to Expiration (years) | (DTE / 365) | 7 days = 0.0192 years |
| **r** | Risk-free rate | Fixed (RBI rate) | 0.065 (6.5%) |
| **σ** | Volatility (decimal) | **CALCULATED (IV)** | 0.18 for 18% |
| **C** | Option Price (market) | Bhavcopy close (LTP) | 126.25 |

### STEP 1: CALCULATE IMPLIED VOLATILITY (IV)

**Method:** Black-Scholes IV Solver (Newton-Raphson iteration)

**Input:** Option price C, spot S, strike K, days to expiry DTE, risk-free rate r

**Process:**
1. Initialize guess for σ
2. Iteratively solve: **BS_Call(S, K, T, r, σ) = C**
3. Use Newton-Raphson to find σ where BS output matches market price
4. Converge to tolerance: 1e-6 (typically 30-50 iterations)
5. If no solution: NULL (rare for liquid options)

**Output:** σ as decimal, multiply by 100 for percentage display

**Example:**
- Market option price: 126.25
- After solver: σ = 0.1850 (18.50%)

---

### STEP 2: CALCULATE GREEKS (from IV)

Once IV is obtained, calculate all Greeks using Black-Scholes partial derivatives:

| Greek | Formula | Meaning | Range | Notes |
|-------|---------|---------|-------|-------|
| **δ (Delta)** | ∂C/∂S = N(d1) | Rate of change vs underlying spot | CE: 0→1<br>PE: -1→0 | How much option price changes per ₹1 move in spot |
| **γ (Gamma)** | ∂δ/∂S = φ(d1)/(S·σ·√T) | Rate of change of delta | 0 → 0.1 (peaks ATM) | Always positive; how much delta changes |
| **θ (Theta)** | ∂C/∂T ÷ 365 **(per day)** | Time decay per day | CE: negative<br>PE: depends | Loss of value due to 1 day passage |
| **ν (Vega)** | ∂C/∂σ ÷ 100 **(per 1% IV)** | IV sensitivity | Positive for all | Price change per 1% increase in IV |
| **ρ (Rho)** | ∂C/∂r ÷ 100 **(per 1% rate)** | Interest rate sensitivity | Small for short DTE | Usually negligible for weekly options |

### MATHEMATICAL FOUNDATION

**d1 and d2:**
```
d1 = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
d2 = d1 - σ·√T
```

**Where:**
- N(x) = Cumulative normal distribution (standard normal CDF)
- φ(x) = Probability density function at x
- All Greeks derived from these

**Example Calculation (NIFTY 23500 CE, 7 DTE):**
- S = 24000, K = 23500, T = 0.0192, r = 0.065, σ = 0.1850
- d1 = 1.234, d2 = 0.895
- δ = N(d1) = 0.6500
- γ = φ(d1)/(24000·0.1850·0.1385) = 0.0125
- θ = -0.1500 (per day)
- ν = 0.4500 (per 1% IV)
- ρ = 0.0150 (per 1% rate)

---

## PART 5: POSTGRESQL VALIDATION QUERIES (Run in DBeaver)

### Query 1: Table Structure
```sql
\d option_bars;
```
**Expected:** Shows all 19 columns with types and indexes

### Query 2: Row Count by Symbol
```sql
SELECT symbol, COUNT(*) as cnt, COUNT(DISTINCT DATE(timestamp)) as days
FROM option_bars
GROUP BY symbol
ORDER BY symbol;
```
**Expected:** NIFTY: ~2500-3500 rows, SENSEX: ~2500-3500 rows

### Query 3: Date Range
```sql
SELECT MIN(DATE(timestamp)) as start_date, MAX(DATE(timestamp)) as end_date
FROM option_bars;
```
**Expected:** 2025-10-01 to 2026-04-30 (182 days, minus weekends)

### Query 4: NULL Count by Column
```sql
SELECT 
  COUNT(*) as total,
  COUNT(*) - COUNT(iv) as null_iv,
  COUNT(*) - COUNT(delta) as null_delta,
  COUNT(*) - COUNT(gamma) as null_gamma,
  COUNT(*) - COUNT(theta) as null_theta,
  COUNT(*) - COUNT(vega) as null_vega
FROM option_bars;
```
**Expected:** <5% NULL for all Greeks columns (due to failed IV solver on illiquid options)

### Query 5: IV Statistics (Sanity Check)
```sql
SELECT 
  COUNT(*) as total_with_iv,
  MIN(iv) as min_iv,
  MAX(iv) as max_iv,
  AVG(iv) as avg_iv,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY iv) as median_iv
FROM option_bars
WHERE iv IS NOT NULL;
```
**Expected:** min_iv ~10%, max_iv ~35%, avg_iv ~18%, median ~17%

### Query 6: Greeks Completeness
```sql
SELECT 
  COUNT(*) as total,
  COUNT(iv) as has_iv,
  COUNT(delta) as has_delta,
  ROUND(100.0 * COUNT(iv) / COUNT(*), 2) as pct_complete
FROM option_bars;
```
**Expected:** >95% rows have all Greeks

### Query 7: Immediate Expiry Check (<7 DTE)
```sql
SELECT DISTINCT expiry, expiry - CURRENT_DATE as dte
FROM option_bars
ORDER BY expiry;
```
**Expected:** All DTEs between 0 and 7 days

### Query 8: Strike Filter (1.5%-4.5% moneyness)
```sql
SELECT symbol, COUNT(DISTINCT strike) as unique_strikes, MIN(strike) as min_strike, MAX(strike) as max_strike
FROM option_bars
GROUP BY symbol;
```
**Expected:** NIFTY: 12-16 strikes per expiry, SENSEX: similar range

### Query 9: Sample Records (Visual Inspection)
```sql
SELECT timestamp, symbol, strike, option_type, close, iv, delta, gamma, theta, vega
FROM option_bars
WHERE DATE(timestamp) = '2025-10-01'
ORDER BY symbol, strike, option_type
LIMIT 20;
```
**Expected:** See realistic option prices and Greeks values

### Query 10: Export to CSV (Optional)
```sql
\COPY (SELECT * FROM option_bars ORDER BY timestamp, symbol, strike) 
  TO '/tmp/nifty_sensex_export.csv' WITH CSV HEADER;
```
**Result:** CSV file with all rows for external analysis

---

## PART 6: DBEAVER STEP-BY-STEP GUIDE

### Step 1: Connect to PostgreSQL
1. Open DBeaver
2. Left panel → right-click "Connections" → **New Database Connection**
3. Select **PostgreSQL** → Next
4. Fill in:
   - Host: `localhost`
   - Port: `5432`
   - Database: `postgres` (test)
   - Username: `postgres`
   - Password: [your password]
   - ✓ Save password
5. **Test Connection** → Success message
6. **Finish**

### Step 2: Create Schema
1. Right-click connection → **New SQL Editor**
2. Copy-paste entire CREATE TABLE statement (from Part 2)
3. **Ctrl+A** → **Ctrl+Enter** (Execute)
4. Expected: "Command executed successfully"

### Step 3: Verify Table Created
1. Expand **Databases** → **nifty_sensex_options** → **Tables**
2. Right-click **option_bars** → **View Data**
3. Should show empty table (0 rows initially)

### Step 4: Run Python Data Load Script
1. Save Claude's script to `load_options_data.py`
2. Terminal: `pip install psycopg2 py_vollib pandas requests`
3. Terminal: `python load_options_data.py`
4. Watch for progress messages (date-by-date)
5. Expected finish: "✓ Loaded 180 days, X rows inserted"

### Step 5: Validate Data in DBeaver
1. In DBeaver, press **F5** (Refresh)
2. Right-click option_bars → **View Data** again
3. Should now see 5000+ rows
4. New SQL Editor → Run Query #1, #2, #3 (from Part 5)
5. Check results match expectations

---

## PART 7: PYTHON SCRIPT OUTLINE (For Claude Haiku)

### High-Level Structure

```python
# 1. IMPORTS
import psycopg2
from datetime import datetime, timedelta
from py_vollib.black_scholes.implied_volatility import implied_volatility
from py_vollib.greeks.black_scholes import delta, gamma, theta, vega, rho
import pandas as pd
import requests

# 2. CONNECT TO PostgreSQL
conn = psycopg2.connect('dbname=nifty_sensex_options user=postgres password=...')
cur = conn.cursor()

# 3. LOOP: Oct 2025 - Apr 2026
for current_date in date_range(2025-10-01, 2026-04-30):
    if is_weekday(current_date):  # Mon-Fri only
        
        # 4. FETCH BHAVCOPY
        df = fetch_nse_bhavcopy(current_date)  # CSV download
        
        # 5. FILTER SYMBOL
        df = df[df['SYMBOL'].isin(['NIFTY', 'SENSEX'])]
        
        # 6. FILTER EXPIRY (<7 DTE)
        df['dte'] = (df['EXPIRY_DATE'] - current_date).days
        df = df[(df['dte'] > 0) & (df['dte'] <= 7)]
        
        # 7. FILTER STRIKES (1.5%-4.5%)
        spot = get_spot_price(current_date)
        df['moneyness'] = abs((df['STRIKE'] / spot - 1) * 100)
        df = df[df['moneyness'].between(1.5, 4.5)]
        
        # 8. CALCULATE IV
        for idx, row in df.iterrows():
            try:
                iv = implied_volatility(
                    option_price=row['CLOSE'],
                    underlying_price=spot,
                    strike=row['STRIKE'],
                    days_to_expiration=row['dte'],
                    risk_free_rate=0.065,
                    option_type='c' if row['OPTION_TYPE']=='CE' else 'p'
                )
                df.loc[idx, 'iv'] = iv * 100
            except:
                df.loc[idx, 'iv'] = None
        
        # 9. CALCULATE GREEKS (from IV)
        for idx, row in df.iterrows():
            if pd.notna(row['iv']):
                sigma = row['iv'] / 100
                df.loc[idx, 'delta'] = delta(...)
                df.loc[idx, 'gamma'] = gamma(...)
                df.loc[idx, 'theta'] = theta(...) / 365
                df.loc[idx, 'vega'] = vega(...) / 100
                df.loc[idx, 'rho'] = rho(...) / 100
        
        # 10. INSERT TO PostgreSQL
        for idx, row in df.iterrows():
            cur.execute("""
                INSERT INTO option_bars (...) VALUES (...)
                ON CONFLICT (timestamp, symbol, strike, option_type, expiry)
                DO UPDATE SET close = EXCLUDED.close, iv = EXCLUDED.iv
            """, (row_tuple))
        
        conn.commit()
        print(f"✓ {current_date}: {len(df)} rows inserted")

# 11. VALIDATION
cur.execute("SELECT COUNT(*) FROM option_bars")
print(f"✓ Total rows: {cur.fetchone()[0]}")
conn.close()
```

---

## PART 8: CHECKLIST (Week 1: Day 1-2)

- [ ] **DAY 1 MORNING** (1 hour)
  - [ ] Test PostgreSQL in DBeaver (5 min)
  - [ ] Create schema from Part 2 (5 min)
  - [ ] Request Claude Haiku script for Oct 2025 - Apr 2026 (5 min)
  - [ ] pip install psycopg2 py_vollib pandas requests (10 min)
  - [ ] Review script + understand IV/Greeks (15 min)

- [ ] **DAY 1 AFTERNOON** (1.5 hours)
  - [ ] Run Python script (60-120 min)
  - [ ] Monitor progress in terminal
  - [ ] Expected: "Loaded 180 days, X rows"

- [ ] **DAY 2 MORNING** (30-45 minutes)
  - [ ] Verify script complete (5 min)
  - [ ] Run validation queries (Part 5) in DBeaver (20 min)
    - [ ] Query #2: Row count by symbol
    - [ ] Query #3: Date range (Oct 1, 2025 - Apr 30, 2026)
    - [ ] Query #4: NULL check (<5%)
    - [ ] Query #6: IV statistics (10%-35% range)
    - [ ] Query #9: Sample records (visual inspection)
  - [ ] Export to CSV (optional) (5 min)
  - [ ] **SIGN-OFF:** Data ready for backtest (5 min)

---

## TOKEN USAGE ESTIMATE

| Task | Tool | Tokens Used | % of Budget |
|------|------|-------------|------------|
| Write this comprehensive plan | Claude | ~2,500 | 3.1% |
| Write historical loader script (later) | Claude Haiku | ~1,500 | 1.9% |
| **Total** | | **~4,000** | **~5%** |

**Remaining for debugging, edge cases, live integration: ~76,000 tokens (95%)**

---

## NEXT STEPS

1. **Save this file locally** for reference during execution
2. **Request Claude:** "Write the Python script for loading Oct 2025 - Apr 2026 Nifty/Sensex bhavcopy data with IV and Greeks calculation"
3. **Execute in DBeaver:** Create schema (Part 2)
4. **Run Python script** (takes 1-2 hours)
5. **Validate** using queries (Part 5)
6. **Confirm:** Data ready for backtest in Week 2

---

**TOTAL SETUP TIME: 2.5 - 3 hours | TOKEN USAGE: ~5% | COMPLEXITY: Low-Medium**
