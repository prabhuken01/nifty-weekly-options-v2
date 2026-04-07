# Setup Guide: Breeze API vs Kaggle

## Quick Comparison

| Feature | Breeze API | Kaggle |
|---------|-----------|--------|
| **Setup Time** | 30 min | 5 min |
| **Data Coverage** | 3 years minute-level | 2020-2024+ daily |
| **Cost** | Free (ICICI account) | Free |
| **Real-time Data** | Yes | No (historical only) |
| **Greeks Included** | Manual calculation | Manual calculation |
| **Account Required** | ICICI Direct account | Kaggle account (free) |

---

## Option 1: ICICI Direct Breeze API (Recommended for Live Trading)

### Step 1: Get ICICI Credentials
1. Log into your ICICI Direct trading account
2. Go to **Settings → API → Breeze API**
3. Note down:
   - `api_key`
   - `session_key`
   - `userid`

### Step 2: Create Credentials File
Create file: `icici_credentials.json`

```json
{
  "api_key": "your_api_key_here",
  "session_key": "your_session_key_here",
  "userid": "your_user_id_here"
}
```

Save in one of these locations:
- Current directory: `./icici_credentials.json`
- Home directory: `~/.icici_credentials.json`

### Step 3: Run
```bash
python kite_fetch_unified.py
```

**Pros:**
- 3 years of historical minute-level data
- Real-time + historical
- Free for ICICI users
- Per-minute OHLCV + Open Interest
- Best for backtesting + live trading

**Cons:**
- Requires ICICI Direct account setup
- Slightly longer setup time

---

## Option 2: Kaggle Datasets (Easiest Setup)

### Step 1: Get Kaggle API Key
1. Go to https://www.kaggle.com/settings/account
2. Scroll to "API" section
3. Click "Create New API Token"
4. This downloads `kaggle.json`

### Step 2: Place Credentials File
Move the downloaded `kaggle.json` to:
```
~/.kaggle/kaggle.json
```

On Windows: `C:\Users\<YourUsername>\.kaggle\kaggle.json`

### Step 3: Fix Permissions (Linux/Mac only)
```bash
chmod 600 ~/.kaggle/kaggle.json
```

### Step 4: Run
```bash
python kite_fetch_unified.py
```

**Pros:**
- Fastest setup (5 minutes)
- No trading account needed
- Multiple datasets available
- 2020-2024+ data
- Very easy for beginners

**Cons:**
- Historical data only (no live updates)
- May have gaps or delays
- Requires manual periodic updates

---

## Available Kaggle Datasets

1. **[Indian Nifty and Banknifty Options Data 2020-2024](https://www.kaggle.com/datasets/ayushsacri/indian-nifty-and-banknifty-options-data-2020-2024)**
   - 4+ years of daily options data
   - Includes Nifty + BankNifty
   - RECOMMENDED for this setup

2. **[Historical Nifty Options 2024 All Expiries](https://www.kaggle.com/datasets/senthilkumarvaithi/historical-nifty-options-2024-all-expiries)**
   - Comprehensive 2024 data
   - All expiry dates

3. **[NSE - Nifty 50 Minute data 2015 to 2026](https://www.kaggle.com/datasets/debashis74017/nifty-50-minute-data)**
   - Minute-level spot prices
   - Good for spot price reference

---

## Automatic Selection

The `kite_fetch_unified.py` script **automatically**:
1. Detects available sources
2. Tries Breeze first (if credentials found)
3. Falls back to Kaggle
4. Uses test data if neither available
5. Inserts everything into database with full Greeks calculation

---

## Verify Setup

After setting up, run:
```bash
python kite_fetch_unified.py
```

You should see one of:
- `[SUCCESS] Breeze API`
- `[SUCCESS] Kaggle`
- `[FALLBACK] Using test data`

Check the log file:
```bash
tail -20 kite_fetch_unified.log
```

---

## Integration with Step 2

The Step 2 script now uses the unified fetcher:
```bash
python kite_fetch_nifty_daily_6months.py
```

This will:
1. Auto-detect available sources
2. Fetch 6 months of historical data
3. Calculate Greeks for all options
4. Insert into `option_bars_daily` table
5. Update metadata

---

## Recommendation

- **Best for Backtesting**: Kaggle (quick setup, 4+ years data)
- **Best for Live Trading**: Breeze (real-time + 3 years historical)
- **Best for Both**: Set up both (Breeze primary, Kaggle fallback)

Choose **Kaggle** if you just want to get started quickly (5 min setup).
Choose **Breeze** if you have ICICI account and want real-time data (30 min setup).
