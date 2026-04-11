# Changelog — Nifty Weekly Options Dashboard

## v3.0 — 2026-04-11

### Summary
Dashboard at time of changes: NIFTY spot ~₹24,050, Sensex ~₹79,200 (via Dhan LTP). 
IVP NIFTY=42, SENSEX=38. Regime: ALLOW. DTE=1 (expiry 2026-04-13).
Tab 1 shows 5 put legs (-1.5% to -3.5%) and 5 call legs (+1.5% to +3.5%), 
strangle recommended at Score 81. Best cushion 6.7x.

### Changes Made

#### 1. Auto-Fetch on Page Load (Tab 1)
- **Before**: User had to click "📡 Fetch Live Chain" button every time to get live data. Page showed `~est` (estimated) premiums by default.
- **After**: When Dhan token is available, chains are fetched automatically on first page load. The "Fetch Live Chain" button remains for manual refresh. Users now see live data immediately without extra clicks.

#### 2. Tab 3 — Auto-Load Option Chains
- **Before**: Nifty and Sensex chains only loaded when user clicked the "Load NIFTY 50 Chain" / "Load SENSEX Chain" buttons.
- **After**: Chains auto-load on first visit to Tab 3 when token is present. Buttons renamed to "🔄 Refresh" for manual re-fetch. Added empty-state handling if no strikes found near spot.

#### 3. Mobile Font Size & Readability
- **Before**: Small fonts on mobile, cramped metrics, hard-to-read dataframes.
- **After**: Added comprehensive mobile CSS: 
  - Metric labels 13px, values 20px, deltas 12px on mobile
  - Dataframe text 13px with 4px padding on mobile, 14px on desktop  
  - Tab labels 14px with 8px padding
  - Sidebar min-width 280px
  - Headers scaled (h1=22px, h2=18px, h3=16px)
  - Column min-width 140px to prevent crushing
  - Bold table headers with subtle background

#### 4. Tab 1 — Score & Delta Fixes
- **Before**: All put strikes showed nearly identical scores (80, 81, 81, 81, 81) because score formula was `60%×Prob + 40%×IVP`. Since IVP is constant and all far-OTM probs are ~99-100%, scores couldn't differentiate. Delta displayed as raw float with trailing zeros (e.g., `-0.000000`).
- **After**: 
  - Score formula now: `40%×Prob + 30%×IVP + 30%×Return attractiveness`. The Return% component rewards higher-premium (nearer) strikes, creating meaningful score differences across the 5 strikes.
  - Delta formatted to 4 decimal places (e.g., `-0.0230` instead of `-0.023000`).
  - Fixed `ext.loss` calculation: was `abs(off+0.005)` which gave wrong values for calls; now `abs(abs(off)+0.005)`.

#### 5. Tab 2 — Backtest Engine Overhaul
- **Before**: Synthetic backtest using formula-generated data with hardcoded win rates. No user interaction beyond sidebar filters.
- **After**: Complete redesign with 5-step workflow:
  1. **Date Selection** — Pick any historical date (from Oct 2024 onwards)
  2. **Market Snapshot** — Shows spot, IV, IVP, DTE for that date
  3. **Greeks Display** — Full Greeks (delta, gamma, theta, vega, prob OTM) at user-selected strike offset
  4. **Market Trend Indicators** — IV regime, trend signal, vega risk
  5. **Strategy Selection** — Short Put / Short Call / Short Strangle / Short Straddle / Iron Condor
  6. **Result** — Shows max profit, premium source, prob OTM for 1 contract
  - Includes implementation plan for Phase 2 (historical premium database lookup) in expander
  - Note: Live historical P&L requires backtest data files in `Backtest-Engine/` folder (see plan)

#### 6. No Other Changes
- All existing Tab 1 signal logic, Tab 3 chain display, sidebar controls, Dhan API integration, and glossary content preserved (except updated score formula references).

### Files Modified
- `app.py` — All changes above
- `CHANGELOG.md` — This file (new)

### Backup
Synced to: `E:\Personal\Trading_Champion\Projects\Nifty Weekly Options Strategy_v2_Claude`
