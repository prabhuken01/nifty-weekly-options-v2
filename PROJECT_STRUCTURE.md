# NIFTY Weekly Options Strategy - Project Structure

## Overview
Modular short strangle strategy dashboard with live signal generation, historical backtesting, and volatility analysis.

## Directory Organization

### Root Level
```
app.py                    # Main Streamlit dashboard (3 tabs)
requirements.txt          # Python dependencies
README.md                 # Project overview
PROJECT_STRUCTURE.md      # This file
```

### Mini-Projects

#### 1. **Live-Signal-Generator/**
Real-time NIFTY option chain data fetching (Tab 2)
- Fetches live option premiums from NSE
- 1-hour caching to manage API usage
- Falls back to formula-based estimation if API unavailable
- Files: `fetch_nifty_option_chain.py`

#### 2. **Backtest-Engine/**
Historical strategy validation (Tab 1)
- 6-36 month backtests with configurable parameters
- Greeks calculation (Theta, Vega), P&L, drawdown
- IV percentile filtering
- Files: `validate_strategy.py`

#### 3. **Utilities/**
Integration helpers (Phase 2)
- Google Sheets API manager for caching
- Excel export and formatting
- Status tracking and reporting
- Files: `gsheet_manager.py`, `create_status.py`, `update_excel_phase2.py`

#### 4. **Docs/**
Documentation and setup guides
- Google Sheets API setup guide
- Phase 2 implementation roadmap
- Checklist for configuration

#### 5. **Database_v1/** ⚠️ KEEP UNTOUCHED
Historical data storage and retrieval
- NSE Bhavcopy loaders
- Option chain snapshots
- Test data infrastructure
- Managed independently

#### 6. **Archive/**
Deprecated/legacy code
- Old versions
- Experimental features

## Tab Structure

| Tab | Name | Source | Refresh | Purpose |
|-----|------|--------|---------|---------|
| 1 | Backtest | Formula-based | On-demand | Test strategy across historical periods |
| 2 | Live Signal | **NSE API** (new!) | ♻️ Hourly | Real-time strangle entry signals |
| 3 | IV History | Synthetic | On-demand | Volatility regime analysis |

## Key Updates (Phase 1)

### Tab 2 Improvements
✅ **Live Data Integration**
- Now fetches ACTUAL NIFTY spot price from NSE via nsepython
- Retrieves real option premiums from NSE option chain
- Falls back gracefully to formula-based estimation

✅ **Mobile Responsive**
- 2-column layout on mobile, 5-column on desktop
- Responsive metrics and dataframes
- Touch-friendly interface

✅ **1-Hour Refresh**
- `@st.cache_data(ttl=3600)` prevents excessive API calls
- Automatic refresh every hour
- Shows last update timestamp

### Dependencies
Added to `requirements.txt`:
- `nsepython>=0.3.0` - NSE data fetching

## Data Flow

```
NSE (Option Chain)
    ↓
Live-Signal-Generator/fetch_nifty_option_chain.py
    ↓
app.py (Tab 2)
    ↓
Live Signal Display (Real premiums + scores + recommendations)
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Optional: Install nsepython for live data**
   ```bash
   pip install nsepython --break-system-packages
   ```

3. **Run dashboard**
   ```bash
   streamlit run app.py
   ```

## Phase 2 Roadmap

- [ ] Cache real option premiums to Google Sheets
- [ ] Fetch historical premiums for Tab 1 backtests
- [ ] REST API wrapper for Tab 2 live signals
- [ ] Mobile app integration
- [ ] Automated trade execution logging

## Notes

- **Database_v1**: Managed separately - do NOT modify without explicit approval
- **Live-fetching**: Renamed to **Live-Signal-Generator** (backward compatible)
- **All tabs**: Maintain clean separation between feature modules
- **No breaking changes**: Existing backtest and IV history tabs unmodified
