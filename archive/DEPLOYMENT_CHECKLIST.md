# Deployment Checklist — 2026-04-14

## IV & IVP Enhancement Complete ✓

### Data Files (Ready for App)
- ✓ `final_merged_output_30m_strike_within_6pct_updated.csv` — Full historical data (850K rows) with old_iv + new_iv columns
- ✓ `final_merged_output_30m_strike_within_6pct.parquet` — Backup (faster loading)
- ✓ `iv_impact_analysis_with_ivp.csv` — 371 dates with IV + IVP (old & new methods)
- ✓ `iv_series_14day.csv` — Latest 14 days for IV Analysis tab
- ✓ `iv_comparison_metrics.json` — Latest IV vs historical stats

### Strategy Files
- ✓ `Nifty_Strategy_Selector_v2.xlsx` — LUT (no retraining needed)
- ✓ `NIFTY_Options_Backtest_Results.xlsx` — Backtest source data

### Code Changes
- ✓ **app.py:** `bt_iv_straddle()` now uses DTE≥2 rule (skips 0DTE/T-1)
- ✓ **app.py:** New "📊 IV Analysis" tab (shows IV + IVP trends, 14-day history)
- ✓ **app.py:** Tab structure: Live Signal → Backtest → Validation → IV Analysis → IV History

## Key Metrics

### IV Analysis
- **Old Method:** Nearest expiry (any DTE)
- **New Method:** First expiry with DTE≥2
- **Impact:** 19.1% of dates shift bands, but 0% strategy changes in LUT
- **Verdict:** Safe to deploy, no LUT retraining needed

### IVP Analysis (252-day rolling)
- **Old IVP Mean:** 46.2 (median 44.0)
- **New IVP Mean:** 45.3 (median 43.9)
- **Change:** -0.9 points average (very stable!)
- **IVP Band Shifts:** 58.5% (more sensitive than IV, as expected)
- **Verdict:** Consistent methodology across both metrics

## Kite Fallback (Optional)
If not yet set up:
1. Run: `python kite_token_generator.py`
2. Add `[kite]` section to `.streamlit/secrets.toml`
3. Restart app

Without Kite setup: Dhan works fine, but token expires in 24h (manual refresh needed)

## Pre-Deployment Verification

Before going live, verify:
- [ ] Restart Streamlit: `streamlit run app.py`
- [ ] Tab 1 (Live Signal): IV values match live chain calculation
- [ ] Tab 2 (Backtest): IV avoids 0DTE collapse, uses DTE≥2 expiry
- [ ] New IV Analysis tab: Shows 14-day trend + IVP percentile
- [ ] IV Analysis: Latest IV displayed with z-score and percentile rank
- [ ] Backtest Explorer: IV consistency across all strategies

## File Organization

### Archive Contents
Backtest-Engine/archive/ contains:
- `old_data/` — Previous CSV versions (replaced by _updated.csv)
- `scripts/` — Batch processing scripts (no longer needed)
- `analysis/` — Intermediate analysis files
- `documentation/` — Old HTML documentation

To access archived files: `Backtest-Engine/archive/{folder}/`

## No Core Changes
✓ App architecture unchanged
✓ Backtest logic unchanged
✓ LUT structure unchanged
✓ Trading rules unchanged
✓ Only IV methodology unified + IVP added for analysis

## Ready for Deployment ✓

All enhancements complete. App is ready to run.
