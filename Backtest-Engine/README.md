# Backtest Engine

Historical backtesting and strategy validation for NIFTY short strangle.

## Features
- Tab 1: Backtests strangle strategy with 6-36 month lookback
- Calculates P&L, Greeks (Theta, Vega), win rates, drawdown
- Filters by IV percentile regime
- Configurable entry/exit times and exclusions

## Components
- `validate_strategy.py` — Strategy validation and data fetching
- `validate_sample_trade.py` — Quick CSV sanity check (sample date; mirrors Tab 2 entry/exit bars)
- `nifty_options_framework_v2.html` / `nifty_options_framework_v3.html` — UI / spec reference for Tab 2
- `mockups/` — static HTML prototypes (`tab2_mockup.html`, `tab2_corrected_mockup.html`, `tab2_v3.html`); see `mockups/README.md`

## Integration
- `app.py` **Tab 1** — live signal grids
- `app.py` **Tab 2** — historical simulator reads `final_merged_output_30m_strike_within_6pct.csv`

## Data Sources
- NSE Bhavcopy (free, T+1)
- Kite Connect API (if credentials available)
- yfinance (fallback)

## Status
- **Phase 1**: Formula-based premium estimation
- **Phase 2**: Real historical premiums from cached database
