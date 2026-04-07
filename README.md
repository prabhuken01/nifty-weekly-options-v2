# nifty-weekly-options-v2

Short strangle backtesting and live signal dashboard for NIFTY 50 and SENSEX weekly options.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## What's New (Phase 1 Complete)

✨ **Tab 2 - Live Signal Generator**
- Now fetches **REAL NIFTY spot prices** from NSE (via nsepython)
- **Actual option premiums** from NSE option chain (with 1-hour refresh)
- **Mobile responsive** UI (2-col on mobile, 5-col on desktop)
- Graceful fallback to formula-based estimation if API unavailable

## Project Structure

See `PROJECT_STRUCTURE.md` for detailed directory organization.

```
├── app.py                          # Main dashboard (3 tabs)
├── requirements.txt                # Dependencies (includes nsepython)
├── Live-Signal-Generator/          # Tab 2: Real-time option chain fetching
├── Backtest-Engine/                # Tab 1: Historical backtesting
├── Utilities/                      # Google Sheets, Excel, status tracking
├── Docs/                           # Setup guides & documentation
├── Database_v1/                    # Historical data storage (DO NOT MODIFY)
└── Archive/                        # Legacy code
```

---

## Architecture

```
app.py
├── Sidebar controls (instrument, lookback, IVP filter, expiry, DTE)
├── Tab 1 — Backtest Results
│   ├── Live spot + IV header (NIFTY & SENSEX)
│   ├── 3 bar charts (return%, win rate, max DD)
│   ├── Results table (12 columns, ₹5L normalised)
│   └── Glossary expander
├── Tab 2 — Live Signal
│   ├── Live spot + IV header
│   ├── Verdict banner (best put, best call, strangle?, cushion)
│   ├── Put leg grid (5 offsets × 13 rows)
│   ├── Call leg grid (5 offsets × 13 rows)
│   └── Glossary expander
└── Tab 3 — IV History
    ├── Period selector (1D / 1H / 5M)
    ├── Line chart — NIFTY + SENSEX IV (30 periods)
    ├── Bar chart — IVP rank
    ├── Data table
    └── Glossary expander
```

---

## Data sources

| Source | What | How | Cost |
|---|---|---|---|
| NSE Bhavcopy | EOD option chain, IV, OI | Download CSV from nseindia.com/market-data/live-equity-market | Free |
| DhanHQ Historical API | Intraday 1H / 5M candles | `GET /v2/charts/historical` with `instrument_token` | Free tier |
| Kite Connect | Live tick, option chain | `kite.ltp()` + `kite.instruments()` | ₹2000/month |

---

## Ground rules (match Excel spec)

- **₹ format:** integers only, Indian comma format — no decimals
- **% format:** one decimal place (e.g. 1.6%)
- **Ratios:** one decimal + x (e.g. 2.3x)
- **Signal scores:** integer out of 100
- **Negative P&L:** shown in brackets
- **Capital base:** ₹5,00,000 for all return% calculations
- **Lot sizes:** NIFTY=65, SENSEX=10
- **Brokerage:** ₹80 flat per trade
- **STT:** 0.05% on exit premium
- **IVP window:** 30 trading days rolling
- **Friday entries:** excluded by default (toggle in sidebar)
- **DTE:** holiday-adjusted — subtract weekends + NSE holidays from calendar days
- **Extreme loss scenario:** 0.5% beyond outer strike, last trading day

---

## Signal logic

### Composite score (0–100)
```
Score = (N(d2) probability × 0.60) + (IVP quality score × 0.40)
IVP quality score = min(100, IVP × 1.25)   # peaks at IVP=80
```

### Thresholds
| Score | Action |
|---|---|
| ≥ 65 (adjustable) | SELL |
| 50–64 | MONITOR |
| < 50 | AVOID |

### IV regime filter
| IVP | Action | Reason |
|---|---|---|
| < 20% | SKIP | IV too low — negative Vega convexity risk |
| 20–80% | ALLOW | Trade zone |
| > 80% | SKIP | Extreme Gamma risk |

### Holiday-adjusted DTE example
Trade date: Apr 3 (Thu) → Expiry: Apr 7 (Mon)  
Apr 5 (Sat) + Apr 6 (Sun) = non-trading  
Effective DTE = **2 days**  
Impact: N(d2) rises sharply (safer), Theta accelerates (more decay per day)

---

## Wiring live data (replace mock values in app.py)

### NSE Bhavcopy (1D, free)
```python
# Download from: https://www.nseindia.com/market-data/live-equity-market
# File: cm<DDMMMYYYY>bhav.csv — parse ATM strike premium
# ATM IV = Black-Scholes reverse on mid-price
```

### DhanHQ API (1H / 5M)
```python
import requests
headers = {"access-token": "YOUR_TOKEN", "client-id": "YOUR_CLIENT_ID"}
r = requests.get(
    "https://api.dhan.co/v2/charts/historical",
    params={"securityId": "13", "exchangeSegment": "NSE_FNO",
            "instrument": "OPTIDX", "expiryCode": 0,
            "oi": True, "fromDate": "2026-04-01", "toDate": "2026-04-07",
            "interval": "60"},  # 60=1H, 5=5M
    headers=headers)
data = r.json()
```

### Kite Connect (live tick)
```python
from kiteconnect import KiteConnect
kite = KiteConnect(api_key="YOUR_KEY")
kite.set_access_token("YOUR_TOKEN")
ltp = kite.ltp(["NSE:NIFTY 50", "BSE:SENSEX"])
```

---

## Next steps (Stage 2)

- [ ] Wire `SPOT`, `IV_ANN`, `IVP`, `CHG` dicts to live API calls
- [ ] Replace mock `prem` in `make_leg_df()` with actual option chain prices
- [ ] Add `capital_req` from broker margin API
- [ ] Populate Tab 3 from historical Bhavcopy files
- [ ] Deploy on Streamlit Cloud or local server
