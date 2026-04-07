# Backtest Engine

Historical backtesting and strategy validation for NIFTY short strangle.

## Features
- Tab 1: Backtests strangle strategy with 6-36 month lookback
- Calculates P&L, Greeks (Theta, Vega), win rates, drawdown
- Filters by IV percentile regime
- Configurable entry/exit times and exclusions

## Components
- `validate_strategy.py` - Strategy validation and data fetching

## Integration
Used by `app.py` Tab 1 to display backtested performance metrics.

## Data Sources
- NSE Bhavcopy (free, T+1)
- Kite Connect API (if credentials available)
- yfinance (fallback)

## Status
- **Phase 1**: Formula-based premium estimation
- **Phase 2**: Real historical premiums from cached database
