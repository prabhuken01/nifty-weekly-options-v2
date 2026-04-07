# NIFTY WEEKLY OPTIONS - DATA PIPELINE

## 🎯 What Was Just Set Up

Your database is now configured with **3 tables**:
1. **option_bars_daily** - 6 months of daily historical data (for backtesting)
2. **option_bars_minute** - Current + next week minute data (for live trading)
3. **data_metadata** - Tracks all updates automatically

**Status:** ✅ Ready to fetch data

---

## 📋 Quick Start - 3 Simple Steps

### **STEP 1: Setup Database** (Run ONCE - 2 minutes)
```bash
python setup_schema_enhanced.py
```
✅ Creates tables and indexes
✅ Ready for data insertion

### **STEP 2: Backfill 6 Months** (Run ONCE - 30 minutes)
```bash
python kite_fetch_nifty_daily_6months.py
```
✅ Downloads 6 months of historical daily data
✅ Stores in `option_bars_daily` table
✅ Ready for backtesting

### **STEP 3: Run Daily at 4 PM** (Run EVERY DAY)
```bash
python kite_fetch_nifty_minute_daily.py
```
✅ Fetches minute data for current + next week
✅ Stores in `option_bars_minute` table
✅ Ready for live trading

---

## 📁 File Structure

### 🟢 ACTIVE FILES (Use These)

| File | Purpose | Run When |
|------|---------|----------|
| **setup_schema_enhanced.py** | Create database tables | Once (Step 1) |
| **kite_fetch_nifty_daily_6months.py** | Backfill 6 months | Once (Step 2) |
| **kite_fetch_nifty_minute_daily.py** | Daily minute data | Daily @ 4 PM (Step 3) |
| **load_test_data.py** | Load synthetic test data | Optional (testing) |
| **nifty_bhavcopy_loader.py** | NSE backup (hybrid) | If Kite fails |
| **nifty_bhavcopy_manual.py** | Manual CSV import | If Kite fails |
| **NIFTY_Options_Data_Pipeline.xlsx** | Documentation | Read for setup |

### 🔵 ARCHIVED FILES (Reference Only)
See `_ARCHIVE_OLD_FILES/` folder for:
- Old schema files
- Diagnostic reports
- Earlier documentation
- Test files

---

## 📊 Database Schema

### Table: option_bars_daily
```
Columns: timestamp, symbol, strike, option_type, expiry,
         open, high, low, close, volume, open_interest,
         iv, delta, gamma, theta, vega, rho
Purpose: 6-month historical data for backtesting
Storage: ~1000+ records (daily)
```

### Table: option_bars_minute
```
Same columns as option_bars_daily
Purpose: Minute-level data for current + next week weeklies
Storage: ~1000+ records (minute candles)
```

### Table: data_metadata
```
Columns: table_name, last_update, data_type, source,
         records_count, date_range_from, date_range_to
Purpose: Track data updates automatically
```

---

## 🔄 Data Flow

```
Kite API (Authenticated)
    ↓
    ├─ [Step 2] Daily 6-month backfill
    │           └─ option_bars_daily table
    │               (Historical backtesting data)
    │
    └─ [Step 3] Daily minute fetch (4 PM)
                └─ option_bars_minute table
                    (Live trading data)
```

---

## 📖 Documentation

### **For Setup Instructions:**
→ Open: `NIFTY_Options_Data_Pipeline.xlsx`
  - Sheet 1: Instructions
  - Sheet 2: Database Schema
  - Sheet 3: Data Formats
  - Sheet 4: Workflow

### **For Reference (Archived):**
→ See `_ARCHIVE_OLD_FILES/` folder

---

## ✅ Execution Checklist

```
[ ] Step 1: Run setup_schema_enhanced.py
    └─ Output: "SCHEMA SETUP COMPLETE"

[ ] Step 2: Run kite_fetch_nifty_daily_6months.py
    └─ Output: "Ready to fetch 6 months of data"
    └─ Time: ~30 minutes

[ ] Step 3: Setup daily schedule for 4 PM
    ├─ Linux/Mac: Add to crontab
    │   0 16 * * 1-5 python /path/to/kite_fetch_nifty_minute_daily.py
    │
    └─ Windows: Task Scheduler
        Daily trigger at 16:00 (4 PM IST)

[ ] Verify data loaded:
    python -c "import psycopg2; conn = psycopg2.connect(
    'host=localhost user=postgres password=postgres
     dbname=nifty_sensex_options'); cur = conn.cursor();
    cur.execute('SELECT COUNT(*) FROM option_bars_daily');
    print(f'Daily records: {cur.fetchone()[0]}');
    cur.execute('SELECT COUNT(*) FROM option_bars_minute');
    print(f'Minute records: {cur.fetchone()[0]}')"
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Verify PostgreSQL is running |
| "Database does not exist" | Run setup_schema_enhanced.py first |
| "No records inserted" | Check Kite API authentication |
| "Greeks calculation failed" | Check spot price data availability |

---

## 📞 Next Steps

1. **NOW:** Open `NIFTY_Options_Data_Pipeline.xlsx` for detailed setup
2. **RUN:** Execute the 3 steps in order
3. **SCHEDULE:** Set up daily 4 PM cron/task
4. **MONITOR:** Check data_metadata table for updates

---

## 📊 Data Available

- **Daily:** 6 months of OHLCV + Greeks
- **Minute:** Current + next week (1-minute candles)
- **Greeks:** Delta, Gamma, Theta, Vega, Rho
- **Update:** Automatic tracking in metadata table

**Status: READY FOR BACKTESTING & LIVE TRADING** ✅

---

*Setup completed: 2026-04-05*
*Next: Read NIFTY_Options_Data_Pipeline.xlsx and run Step 1*
