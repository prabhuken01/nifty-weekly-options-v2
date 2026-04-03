# Phase 2: Historical Data Caching - Implementation Guide

## Overview

You now have **everything needed** to build the Phase 2 historical premium caching system that will enable accurate backtesting without repeated Kite API calls.

---

## What You Have

### 📚 Documentation (3 files)

| File | Purpose | Length | Status |
|------|---------|--------|--------|
| **GSHEET_SETUP_CHECKLIST.md** | Quick 15-minute setup procedure | 1-2 pages | 👈 **START HERE** |
| **GOOGLE_SHEETS_SETUP.md** | Detailed 11-step guide with all explanations | 40+ pages | Reference |
| **PHASE2_IMPLEMENTATION_GUIDE.md** | This file - roadmap overview | - | Status |

### 💻 Code (2 files)

| File | Purpose | Usage |
|------|---------|-------|
| **gsheet_manager.py** | Ready-to-use Python helper class | `from gsheet_manager import GoogleSheetManager` |
| **app.py** | Updated Streamlit app with Phase 1 placeholders | Already integrated |

### 📋 Excel Sheets

| Sheet | Purpose | Status |
|-------|---------|--------|
| **Phase2_Roadmap** | 5-step implementation plan (in Excel) | Reference |
| **Implementation_Status** | Track progress | Update as you complete |

---

## Getting Started (Choose Your Path)

### 🚀 **Path A: Quick Start (15 minutes)**

Follow this if you want to get running fast:

```
1. Open: GSHEET_SETUP_CHECKLIST.md
2. Go through Part A-D (15 min total)
3. Run: python quick_test.py
4. Done - you have Google Sheets API working
```

**Prerequisites:** Google account, Python 3.8+

### 📖 **Path B: Detailed Understanding (45 minutes)**

Follow this if you want to understand everything:

```
1. Read: GOOGLE_SHEETS_SETUP.md (Steps 1-5)
2. Read: GOOGLE_SHEETS_SETUP.md (Steps 6-9)
3. Run: test_gsheet_connection.py
4. Understand: gsheet_manager.py code
5. Done - you understand the full system
```

---

## 5-Step Implementation Roadmap

### **Step 1: Google Sheets + Python Setup (Week 1)**
```
Status: Required before continuing
Time: ~15-30 minutes
Files: GSHEET_SETUP_CHECKLIST.md

Tasks:
✓ Create Google Cloud project
✓ Enable Google Sheets & Drive APIs
✓ Create service account (JSON credentials)
✓ Create two Google Sheets (NIFTY + SENSEX)
✓ Install Python libraries (pip install gspread)
✓ Test connection (python quick_test.py)

Deliverable: Working connection to Google Sheets
Next: Step 2
```

### **Step 2: Historical Data Backfill (Week 2)**
```
Status: After Step 1 passes testing
Time: 2-4 hours
Files: None yet (will create backfill_script.py)

Tasks:
[ ] Fetch 12 weeks of NSE Bhavcopy data
[ ] Parse CSV to extract option premiums
[ ] Calculate statistics by strike/offset
[ ] Bulk load into Google Sheets
[ ] Validate data quality (missing rows, outliers)

Data needed:
- NIFTY weekly options: ±2.5%, ±3.0%, ±3.5%, ±4.0%, ±4.5% strikes
- SENSEX weekly options: same offsets
- IV and IVP for each period
- Call and Put premiums separately

Deliverable: 1,000+ rows in Google Sheets with historical premiums
Next: Step 3
```

### **Step 3: Scheduled Daily Update Job (Week 2-3)**
```
Status: After Step 1 passes + initial backfill complete
Time: 1-2 hours
Files: fetch_and_cache_premiums.py (to create)

Tasks:
[ ] Create schedule script that runs after NSE close
[ ] Fetch current premiums from Kite API
[ ] Calculate IV, IVP for the day
[ ] Append to Google Sheets
[ ] Maintain 52-week rolling window (delete old rows)
[ ] Add logging and error handling

Scheduling options:
- Windows: Task Scheduler (see Step 11 in GOOGLE_SHEETS_SETUP.md)
- Linux/Mac: cron job
- Cloud: Google Cloud Functions (free tier)

Deliverable: Automated daily premium capture
Next: Step 4
```

### **Step 4: Backtest Integration (Week 3)**
```
Status: After historical data + daily job running
Time: 2-3 hours
Files: Update app.py, modify generate_backtest_pnl()

Tasks:
[ ] Modify generate_backtest_pnl() to query Google Sheets
[ ] For each backtest run:
    - Fetch last lookback_m*4 weeks of data
    - Group by IV regime (LOW/MID/HIGH)
    - Calculate mean/median premium by offset
    - Use ACTUAL premiums instead of formula
[ ] Compare formula-based vs actual P&L
[ ] Document accuracy improvement

Code change (pseudocode):
```python
def generate_backtest_pnl(lookback_m, ...):
    # OLD: premium = formula_based()

    # NEW:
    historical_data = gsheet_mgr.get_statistics(
        'NIFTY_Premium_History',
        lookback_days=lookback_m*30
    )
    premium = historical_data[strike]['strangle_mean']

    # Rest of calculation same
```

Deliverable: Backtest with actual historical premiums
Next: Step 5
```

### **Step 5: Validation Tab + Dashboard (Week 4)**
```
Status: After all backtest changes working
Time: 2-3 hours
Files: Add Tab 4 to app.py

New Tab 4: "Historical Validation"

Features:
[ ] Show formula-based P&L vs actual historical P&L
[ ] Win rate by IV regime (LOW/MID/HIGH)
[ ] Best performing offset + IV combination
[ ] Confidence level ("High: 12+ weeks" vs "Low: <4 weeks")
[ ] Scatter plot: Offset vs Return
[ ] Heatmap: IV Regime vs Strike Offset Performance

Example output:
```
╔════════════════════════════════════════════════════════╗
║          BACKTEST VALIDATION RESULTS                   ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║ Model: Formula-based (current)                         ║
║ Return on 5L (12m): 525.99% ← Optimistic              ║
║                                                        ║
║ Reality: Actual historical premiums (Phase 2)          ║
║ Return on 5L (12m): 387.45% ← Realistic               ║
║                                                        ║
║ Variance: -138.54% (formula overestimated)            ║
║ Confidence: HIGH (14 weeks of data)                   ║
║                                                        ║
║ Best Regime: HIGH IVP (50-80%)                        ║
║ Best Offset: -3.5% PUT, +3.5% CALL                    ║
║ Win Rate: 76% (vs 70% model)                          ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
```

Deliverable: Production-ready dashboard with validation
Final: Review, document, celebrate 🎉
```

---

## Implementation Checklist

### Phase 2a: Setup (Week 1)
```
Week 1:
□ Follow GSHEET_SETUP_CHECKLIST.md (15 min)
□ Get credentials.json downloaded
□ Create two Google Sheets with headers
□ Share sheets with service account email
□ Run quick_test.py - passes? → Continue
□ Test with multiple rows added? → Continue
□ Read statistics back from sheet? → Continue
□ Verify .env file configured correctly? → Continue

Status: ___________
Next: Week 2
```

### Phase 2b: Historical Backfill (Week 2)
```
Week 2:
□ Research NSE Bhavcopy format (CSV structure)
□ Get 12 weeks of historical data (Feb-Apr 2026)
□ Write backfill_script.py
□ Test on small subset (2-3 days)
□ Run full backfill
□ Verify row counts:
  - NIFTY: ~1,000+ rows
  - SENSEX: ~1,000+ rows
□ Spot-check a few rows (realistic premiums?)

Status: ___________
Next: Week 3
```

### Phase 2c: Daily Job (Week 3)
```
Week 3:
□ Create fetch_and_cache_premiums.py
□ Test with mock data first
□ Test with actual Kite API call
□ Set up scheduler (Windows/Linux/Cloud)
□ Verify job runs at 4:00 PM IST daily
□ Manually run once to verify append works
□ Check logs for errors
□ Set rolling window deletion (older than 52 weeks)

Status: ___________
Next: Week 4
```

### Phase 2d: Backtest Integration (Week 4)
```
Week 4:
□ Update generate_backtest_pnl() function
□ Replace formula calculation with Google Sheets query
□ Compare output: formula vs actual
□ Update cells to show new P&L values
□ Run backtest with different lookback periods
□ Verify results are stable (not too noisy)
□ Document accuracy improvements in Excel

Status: ___________
Next: Week 5
```

### Phase 2e: Validation Tab + Polish (Week 5)
```
Week 5:
□ Add Tab 4 "Historical Validation"
□ Implement formula vs actual P&L comparison
□ Add confidence scoring (weeks of data)
□ Create visualization (scatter, heatmap)
□ Write glossary for new metrics
□ Final testing on live app
□ Update Implementation_Status sheet to COMPLETE
□ Create GitHub release notes

Status: ___________
Final: ✓ COMPLETE
```

---

## Files You'll Create

During implementation, you'll create these new files:

```
Phase 2 Files to Create:

1. backfill_script.py
   - Fetch historical NSE data
   - Parse and transform
   - Bulk load to Google Sheets

2. fetch_and_cache_premiums.py
   - Daily scheduled job
   - Call Kite API
   - Append to Google Sheets
   - Cleanup old rows

3. test_phase2_integration.py
   - Test end-to-end flow
   - Validate data quality
   - Performance benchmarks

4. Phase2_README.md
   - Implementation summary
   - Lessons learned
   - Future improvements (Phase 3+)

Total new code: ~600 lines (manageable!)
```

---

## Expected Outcomes

### Before Phase 2 (Current)
```
✗ Premiums: Formula-based (not realistic)
✗ Backtest: Uses estimated premiums
✗ Validation: Can't compare to actual trades
✗ API calls: Every time user opens app
✗ Offline: Not possible (no cache)

Result: Strategy looks too good to be true (525.99% annual return)
```

### After Phase 2 (Target)
```
✓ Premiums: Real market data (historical cache)
✓ Backtest: Uses actual premiums from past
✓ Validation: Compare formula P&L to reality
✓ API calls: Cached - only 1 daily fetch
✓ Offline: Works without API (cache lookup)

Result: Realistic P&L discovery (probably 300-400% range)
Strategy confidence: HIGH
```

---

## Success Criteria

| Criterion | Pass/Fail |
|-----------|-----------|
| Google Sheets connection works | [ ] |
| 12+ weeks of historical data loaded | [ ] |
| Daily job runs and appends data | [ ] |
| Backtest uses actual (not formula) premiums | [ ] |
| Tab 4 shows formula vs actual comparison | [ ] |
| Performance: Backtest runs < 5 seconds | [ ] |
| Data quality: < 1% missing values | [ ] |
| All metrics documented in Excel | [ ] |

---

## Quick Reference Commands

```bash
# Test Google Sheets connection
python quick_test.py

# Run backfill (after creating script)
python backfill_script.py --weeks 12 --instrument NIFTY

# Manually fetch and cache today's premiums
python fetch_and_cache_premiums.py --dry-run    # Preview
python fetch_and_cache_premiums.py --execute    # Do it

# Run Streamlit app
streamlit run app.py

# Check git status
git status

# Commit Phase 2 work
git add .
git commit -m "Phase 2: Implement historical premium caching"
git push origin main
```

---

## Troubleshooting Path

**Problem:** Can't connect to Google Sheets

**Solution Tree:**
1. Is credentials.json in the right folder?
   - Check: `ls credentials.json` should exist
   - Fix: Download from Google Cloud Console again

2. Is SHEET_ID correct?
   - Check: URL should be `...spreadsheets/d/[SHEET_ID]/edit`
   - Fix: Copy exact ID from address bar

3. Is sheet shared with service account?
   - Check: credentials.json has `"client_email": "...@iam..."`
   - Fix: Share sheet with that email (Editor permission)

4. Are Python libraries installed?
   - Check: `pip list | grep gspread`
   - Fix: `pip install gspread google-auth-oauthlib`

**Still stuck?**
- Run: `python test_complete_setup.py` (see GSHEET_SETUP_CHECKLIST.md)
- Post error output in `#trading-bot` Slack

---

## Timeline

| Phase | Duration | Start | End | Status |
|-------|----------|-------|-----|--------|
| Phase 1 | 1 week | Mar 28 | Apr 4 | ✓ DONE |
| Phase 2 | 4 weeks | Apr 5 | May 2 | ⏳ IN PROGRESS |
| Phase 3 | 2 weeks | May 3 | May 16 | ⏹️ PENDING |
| Phase 4 | 1 week | May 17 | May 23 | ⏹️ PENDING |

**Current Date:** 2026-04-04
**Phase 2 Start:** Whenever you're ready (expected this week)

---

## Resources

### Documentation
- **GSHEET_SETUP_CHECKLIST.md** — Start here (15 min)
- **GOOGLE_SHEETS_SETUP.md** — Detailed reference (all 11 steps)
- **gsheet_manager.py** — Code examples and API

### External Links
- [Google Cloud Console](https://console.cloud.google.com/) - Create project
- [Google Sheets API Docs](https://developers.google.com/sheets/api) - Reference
- [gspread Documentation](https://docs.gspread.org/) - Python library docs
- [NSE Bhavcopy](https://www.nseindia.com/) - Historical data source

### Code Examples
- See examples in gsheet_manager.py (bottom of file)
- See integration in app.py (Tab 2 has fetch_option_premiums function)

---

## Next Steps

### **Immediate (Today)**
1. Read this file (you're reading it now ✓)
2. Skim GSHEET_SETUP_CHECKLIST.md (2 min)
3. Decide: Ready to start Phase 2 now?

### **Decision Point**
```
Ready to implement Phase 2 now?
│
├─ YES → Go to GSHEET_SETUP_CHECKLIST.md, Part A
│        Follow the 15-minute setup
│        Come back here when quick_test.py passes
│
└─ NO  → Save these files for later
         Continue with other work
         Note: Phase 2 unlocks accurate backtesting
```

### **After Phase 2 Completion**
1. Review actual P&L results (should be 300-400% range)
2. Identify best performing offset + IV regime
3. Decide: Deploy live or refine further?
4. Update Excel with validation results
5. Plan Phase 3 (advanced features)

---

## Questions Checklist

Before you start, confirm you have:

```
□ Google account (personal or workspace)
□ Python 3.8+ installed
□ pip package manager working
□ Access to this project directory
□ ~15-30 minutes for setup
□ Understanding of what Phase 2 does (read above)
□ Backup of current app.py (already in git ✓)
```

---

## Support & Questions

If you get stuck:

1. Check **GOOGLE_SHEETS_SETUP.md** troubleshooting section
2. Run **test_complete_setup.py** to diagnose
3. Review error messages - they usually explain the issue
4. Common issues:
   - 401 Unauthorized → credentials.json path wrong
   - 404 Not Found → SHEET_ID wrong
   - Permission Denied → sheet not shared with service account

---

**You've got this! Phase 2 is well-documented and achievable. Start with the checklist.** 🚀

---

Last Updated: 2026-04-04
Next Review: 2026-04-11 (after setup completion)
