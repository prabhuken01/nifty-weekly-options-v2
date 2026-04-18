# Project Structure & Setup Guide

## 📁 File Organization

### Main Application Files
- **`main.py`** — Primary Streamlit dashboard (formerly `app.py`)
  - Tab 1: Live Signal (fetch live chains, view recommendations)
  - Tab 2: Backtest Engine (historical P&L analysis)
  - Tab 3: Validation Explorer (compare strategies)
  - Tab 4: **IV Analysis** (plot VIX + IV, download as Excel) ✨
  - Tab 5: IV History (option chain viewer)

### Data & Scripts
- **`data/`** — All data files (Excel, Parquet, CSV)
  - `Live_IV_Tracker.xlsx` — Daily IV manual entry (fill after market close)
  - `final_merged_output_30m_strike_within_6pct.parquet` — 30-min OHLC option data
  - `iv_impact_analysis_with_ivp.csv` — IV percentile (IVP) history
  - `*.xlsx` — Backtest results & strategy dashboards

- **`daily_iv_updater.py`** — Auto-update script (sync Excel → CSV daily)
  - Reads `Live_IV_Tracker.xlsx`
  - Appends new rows to `iv_history_daily.csv` and `nifty_vix_daily.csv`
  - **Run daily after market close** (or schedule as cron job)

- **`kite_token_generator.py`** — Generate Zerodha Kite API token

### Supporting Modules
- **`Live-Signal-Generator/`** — Fetch live option chains from Dhan API
- **`Utilities/`** — Helper utilities
- **`archive/`** — Old deployment docs, mockups

## 🚀 Quick Start

### 1. Run the Dashboard
```bash
streamlit run main.py
```
- Opens at `http://localhost:8501`
- Enter Dhan API token in sidebar → **Fetch Live Chain**

### 2. Auto-Update Daily IV Data
```bash
python3 daily_iv_updater.py
```
**Schedule daily after market close (15:30 IST):**
- **Linux/Mac:** Add to crontab: `30 15 * * 1-5 cd /path/to/project && python3 daily_iv_updater.py`
- **Windows:** Task Scheduler: Run `daily_iv_updater.py` at 15:30 IST

### 3. Manual IV Entry
1. Open `data/Live_IV_Tracker.xlsx`
2. Fill new row with today's market data:
   - Date, Spot, IV %, Expiry, DTE, ATM Strike, Straddle Price
3. Save → Run `daily_iv_updater.py` to sync to CSV

## 📊 New Features (v2.1)

### IV Analysis Tab (Tab 4) ✨
- **Dual Plot:** Nifty VIX vs ATM Straddle IV (side-by-side)
  - VIX shows realized volatility
  - IV shows implied volatility from straddle
- **Excel Download:** Export 30-day IV breakdown
- **Metrics:** Z-Score, percentile ranking, mean, range

### Daily Auto-Update
- Reads `Live_IV_Tracker.xlsx`
- Creates/appends to:
  - `data/iv_history_daily.csv` — Daily IV history
  - `data/nifty_vix_daily.csv` — Daily VIX (placeholder, needs API integration)

## 🔧 Configuration

### Dhan API Token
- Generate via Dhan broker portal
- Enter in sidebar → Triggers auto-fetch every 5 min
- Token cached for 15 min (configurable via `DHAN_LTP_TTL_SECONDS` env var)

### VIX Data Integration
Currently `daily_iv_updater.py` expects VIX data to be fetched from:
1. Dhan API (preferred)
2. NSE website
3. Kite API (fallback)

Modify `fetch_nifty_vix()` in `daily_iv_updater.py` to add your data source.

## 📝 Git Workflow

Changes are committed to `claude/modest-gauss-f13194` branch. To merge to main:
```bash
git checkout main
git pull
git merge claude/modest-gauss-f13194
git push
```

## 🐛 Troubleshooting

**Issue:** "No data for the selected date range"
- Check `data/final_merged_output_30m_strike_within_6pct.parquet` exists
- Last date in parquet: 2026-03-24 (update via API integration)

**Issue:** VIX not showing in chart
- `data/nifty_vix_daily.csv` needs to be populated
- Run `daily_iv_updater.py` with VIX data source configured

**Issue:** Excel download fails
- Ensure `openpyxl` is installed: `pip install openpyxl`
