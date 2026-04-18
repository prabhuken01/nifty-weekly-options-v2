"""
Daily IV & VIX tracker - runs after market hours to append new data
Reads Live_IV_Tracker.xlsx, extracts new rows, and appends to parquet + CSV
"""
import pandas as pd
import os
from datetime import date, datetime, timezone, timedelta

_IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(_IST).replace(tzinfo=None)

BT_DIR = os.path.dirname(__file__)
LIVE_IV_XLSX = os.path.join(BT_DIR, "Live_IV_Tracker.xlsx")
IV_HISTORY_CSV = os.path.join(BT_DIR, "iv_history_daily.csv")
VIX_HISTORY_CSV = os.path.join(BT_DIR, "nifty_vix_daily.csv")

def read_live_iv_tracker():
    """Read Live_IV_Tracker.xlsx and return clean dataframe."""
    try:
        df = pd.read_excel(LIVE_IV_XLSX, sheet_name=0, dtype={'Date': str})
        # Skip header rows and filter out NaN-only rows
        df = df[df['Date'].notna() & (df['Date'] != 'Fill daily after market hours using Dhan API c...')]
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        # Only keep rows with actual data
        df = df[df['NIFTY Spot'].notna() | df['SENSEX Spot'].notna()]
        return df
    except Exception as e:
        print(f"Error reading Live IV Tracker: {e}")
        return pd.DataFrame()

def append_to_iv_csv(new_rows):
    """Append new IV rows to iv_history_daily.csv."""
    if new_rows.empty:
        return

    # Read existing CSV if it exists
    if os.path.exists(IV_HISTORY_CSV):
        existing = pd.read_csv(IV_HISTORY_CSV)
        existing['Date'] = pd.to_datetime(existing['Date']).dt.date
        # Filter out duplicates
        new_rows = new_rows[~new_rows['Date'].isin(existing['Date'])]

    if new_rows.empty:
        return

    # Save combined data
    if os.path.exists(IV_HISTORY_CSV):
        combined = pd.concat([existing, new_rows], ignore_index=True)
    else:
        combined = new_rows

    combined = combined.sort_values('Date').reset_index(drop=True)
    combined.to_csv(IV_HISTORY_CSV, index=False)
    print(f"✓ Appended {len(new_rows)} new IV rows to {IV_HISTORY_CSV}")

def fetch_nifty_vix(dates):
    """
    Fetch Nifty VIX data for given dates.
    NOTE: This is a placeholder. Actual implementation should:
    - Call Dhan/Kite API to fetch NIFTYVIX data
    - Or read from a cached file
    - Or use yfinance if available (^NSEBANK or equivalent)
    """
    # For now, return empty - user should populate this with actual VIX fetch
    # Example: df['NIFTY VIX'] = vix_values
    return pd.DataFrame({
        'Date': dates,
        'NIFTY VIX': [None] * len(dates)  # Placeholder
    })

def sync_daily_data():
    """Main function: read Excel, append to CSVs."""
    print(f"[{now_ist().strftime('%H:%M:%S')}] Starting daily IV sync...")

    new_data = read_live_iv_tracker()
    if new_data.empty:
        print("No new data found in Live IV Tracker")
        return False

    # Prepare data for CSV
    iv_cols = ['Date', 'NIFTY Spot', 'NIFTY IV %', 'Expiry Used', 'DTE (Cal Days)',
               'ATM Strike', 'Straddle Price', 'SENSEX Spot', 'SENSEX IV %']
    iv_data = new_data[iv_cols].copy()

    # Append IV rows
    append_to_iv_csv(iv_data)

    # Fetch VIX for same dates
    vix_data = fetch_nifty_vix(new_data['Date'].tolist())
    if not vix_data.empty:
        if os.path.exists(VIX_HISTORY_CSV):
            existing_vix = pd.read_csv(VIX_HISTORY_CSV)
            vix_data = pd.concat([existing_vix, vix_data], ignore_index=True)
        vix_data = vix_data.drop_duplicates(subset=['Date']).sort_values('Date')
        vix_data.to_csv(VIX_HISTORY_CSV, index=False)
        print(f"✓ Updated {VIX_HISTORY_CSV}")

    print(f"[{now_ist().strftime('%H:%M:%S')}] Daily IV sync complete!")
    return True

if __name__ == "__main__":
    sync_daily_data()
