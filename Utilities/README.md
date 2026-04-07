# Utilities

Helper modules for Google Sheets integration, Excel export, and status tracking.

## Components

### gsheet_manager.py
- Google Sheets API integration
- Reads/writes strategy data to Google Sheets
- Caches historical option premiums
- Phase 2 integration point

### create_status.py
- Generates status reports
- Tracks strategy execution status
- Logs trade metadata

### update_excel_phase2.py
- Exports strategy results to Excel
- Formats dashboards with charts
- Prepares reports for distribution

## Status
- Used by Phase 2 for persistent storage and caching
- Google Sheets API requires credentials setup
- See `Docs/GSHEET_SETUP_CHECKLIST.md` for setup
