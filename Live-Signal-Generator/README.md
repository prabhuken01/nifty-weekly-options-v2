# Live Signal Generator

Real-time NIFTY option chain data fetcher for Tab 2 (Live Signal).

## Features
- Fetches live option chain data from NSE
- Filters strikes within ±4.5% of yesterday's closing price
- Supports 1-hour caching to manage API usage
- Provides fallback to mock data if API unavailable

## Components
- `fetch_nifty_option_chain.py` - Main fetcher class

## Integration
Used by `app.py` Tab 2 to fetch live option premiums for strangle signal generation.

## Dependencies
- nsepython (auto-fetches from NSE)
- See main `requirements.txt`

## Usage
```python
from fetch_nifty_option_chain import NIFTYOptionChainFetcher

fetcher = NIFTYOptionChainFetcher()
spot = fetcher.fetch_yesterday_close()
fetcher.calculate_bands()
fetcher.fetch_option_chain()
fetcher.filter_by_band()
```

## Status
- **Phase 1**: Working with NSE data via nsepython
- **Phase 2**: Will cache to Google Sheets/database for faster retrieval
