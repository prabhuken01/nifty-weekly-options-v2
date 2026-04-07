# Google Sheets API Setup Guide
## For Historical Premium Caching (Phase 2)

---

## Prerequisites
- Google Account
- Python 3.8+
- pip (Python package manager)
- Terminal/Command Prompt access

---

## Step 1: Create Google Cloud Project

### 1.1 Go to Google Cloud Console
1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Click **"Select a Project"** (top-left dropdown)
4. Click **"NEW PROJECT"**

### 1.2 Create New Project
```
Project name: "Nifty-Trading-Bot" (or your preferred name)
Organization: Leave blank (or select if in organization)
Location: No organization
```
5. Click **CREATE**
6. Wait 1-2 minutes for project to be created
7. Click **SELECT PROJECT** to open your new project

---

## Step 2: Enable Google Sheets API

### 2.1 Search for API
1. In Cloud Console, go to **APIs & Services** → **Library**
2. Search for **"Google Sheets API"**
3. Click on **"Google Sheets API"** result
4. Click **ENABLE** button

### 2.2 Verify Activation
- You should see "API enabled" message
- Status shows **"Enabled"**

---

## Step 3: Create Service Account (For Server-to-Server Access)

### 3.1 Go to Credentials Page
1. In Cloud Console, go to **APIs & Services** → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** (top-left)
3. Select **"Service Account"**

### 3.2 Create Service Account
```
Service account name: "nifty-premium-cache"
Service account ID: auto-filled (e.g., nifty-premium-cache@project-id.iam.gserviceaccount.com)
Description: "Service account for fetching/storing option premiums"
```
4. Click **CREATE AND CONTINUE**

### 3.3 Grant Permissions (Optional - Skip for now)
- You can add roles if needed, but not required
- Click **CONTINUE**

### 3.4 Create Key
1. Click **CREATE KEY**
2. Select **JSON**
3. Click **CREATE**
4. **A JSON file will download** - Save it securely:
   ```
   Save as: E:\Personal\Trading_Champion\Projects\Nifty Weekly Options Strategy_v1\credentials.json
   ```
5. Click **DONE**

---

## Step 4: Enable Drive API (For File Access)

### 4.1 Go to APIs & Services Library
1. Click **APIs & Services** → **Library**
2. Search for **"Google Drive API"**
3. Click on result
4. Click **ENABLE**

---

## Step 5: Install Python Libraries

### 5.1 Open Command Prompt
```bash
cd E:\Personal\Trading_Champion\Projects\Nifty Weekly Options Strategy_v1
```

### 5.2 Install Required Packages
```bash
pip install gspread google-auth-oauthlib google-auth-httplib2 google-auth
```

**Package explanations:**
- `gspread` - Python wrapper for Google Sheets API
- `google-auth-*` - Authentication libraries

---

## Step 6: Create Google Sheets

### 6.1 Manual Creation (Quick Start)
1. Go to [Google Sheets](https://sheets.google.com/)
2. Click **"+ Blank"** to create new sheet
3. Rename sheet:
   - **Name:** "NIFTY_Premium_History"
   - Right-click sheet tab → Rename
4. Set up columns in Row 1:
   ```
   A1: Date        B1: Time      C1: Strike    D1: Expiry
   E1: IV          F1: IVP       G1: CE_Premium H1: PE_Premium
   I1: Notes
   ```

5. Create another sheet for SENSEX:
   - Click **"+"** button at bottom
   - Name it: "SENSEX_Premium_History"
   - Add same columns

### 6.2 Share Sheet with Service Account
1. In your Google Sheet, click **SHARE** (top-right)
2. In credentials.json, find the email in `"client_email"` field
   ```
   Example: nifty-premium-cache@PROJECT_ID.iam.gserviceaccount.com
   ```
3. Copy the email
4. Paste in Share dialog
5. Give **"Editor"** permission
6. Click **SHARE**
7. **Don't send notification** (it's a service account)

**Note the Sheet ID:** In the URL, you'll see something like:
```
https://docs.google.com/spreadsheets/d/[SHEET_ID_HERE]/edit
```
Save this Sheet ID - you'll need it in code.

---

## Step 7: Test Connection with Python Script

### 7.1 Create test script
Create file: `test_gsheet_connection.py`

```python
import gspread
from google.oauth2.service_account import Credentials

# Set up authentication
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']

creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
client = gspread.authorize(creds)

# Open the sheet
SHEET_ID = "PASTE_YOUR_SHEET_ID_HERE"  # Get from URL
sheet = client.open_by_key(SHEET_ID)

# Access worksheet
nifty_worksheet = sheet.worksheet('NIFTY_Premium_History')

# Test: Add a row
test_data = {
    'Date': '2026-04-04',
    'Time': '15:30:00',
    'Strike': '23250',
    'Expiry': '2026-04-07',
    'IV': '14.2',
    'IVP': '42',
    'CE_Premium': '284.65',
    'PE_Premium': '201.20',
    'Notes': 'Test entry'
}

# Add row
row_values = [
    test_data['Date'], test_data['Time'], test_data['Strike'],
    test_data['Expiry'], test_data['IV'], test_data['IVP'],
    test_data['CE_Premium'], test_data['PE_Premium'], test_data['Notes']
]

nifty_worksheet.append_row(row_values)
print("[OK] Test row added successfully!")

# Read back
all_values = nifty_worksheet.get_all_values()
print(f"[OK] Sheet now has {len(all_values)} rows")
```

### 7.2 Run test
```bash
python test_gsheet_connection.py
```

**Expected output:**
```
[OK] Test row added successfully!
[OK] Sheet now has 2 rows
```

If you get errors:
- **401 Unauthorized**: credentials.json path is wrong
- **404 Not found**: SHEET_ID is wrong
- **Permission denied**: Sheet wasn't shared with service account email

---

## Step 8: Environment Variables Setup (Optional but Recommended)

### 8.1 Create .env file
File: `E:\Personal\Trading_Champion\Projects\Nifty Weekly Options Strategy_v1\.env`

```
GOOGLE_SHEET_ID=PASTE_YOUR_SHEET_ID_HERE
GOOGLE_CREDENTIALS_PATH=./credentials.json
KITE_API_KEY=YOUR_KITE_API_KEY_HERE
```

### 8.2 Install python-dotenv
```bash
pip install python-dotenv
```

### 8.3 Use in code
```python
from dotenv import load_dotenv
import os

load_dotenv()
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
CREDS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')
```

---

## Step 9: Integration with Streamlit App

### 9.1 Create helper module
File: `gsheet_manager.py`

```python
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit as st

class GoogleSheetManager:
    def __init__(self, credentials_path='credentials.json', sheet_id=None):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
                      'https://www.googleapis.com/auth/drive']
        self.creds = Credentials.from_service_account_file(
            credentials_path, scopes=self.SCOPES
        )
        self.client = gspread.authorize(self.creds)
        self.sheet_id = sheet_id
        self.sheet = None

        if sheet_id:
            self.sheet = self.client.open_by_key(sheet_id)

    def append_premium_data(self, worksheet_name, date, time, strike, expiry,
                           iv, ivp, ce_premium, pe_premium, notes=''):
        """Add a row of premium data to the sheet."""
        worksheet = self.sheet.worksheet(worksheet_name)
        row = [date, time, strike, expiry, iv, ivp, ce_premium, pe_premium, notes]
        worksheet.append_row(row)
        return True

    def get_premiums_for_strike(self, worksheet_name, strike, expiry):
        """Fetch premium data for a specific strike and expiry."""
        worksheet = self.sheet.worksheet(worksheet_name)
        all_data = worksheet.get_all_records()

        matching = [
            row for row in all_data
            if row.get('Strike') == str(strike) and row.get('Expiry') == str(expiry)
        ]
        return matching

    def get_recent_premiums(self, worksheet_name, limit=10):
        """Get the last N rows of data."""
        worksheet = self.sheet.worksheet(worksheet_name)
        all_data = worksheet.get_all_records()
        return all_data[-limit:]

    def get_statistics(self, worksheet_name, strike=None):
        """Calculate average premium by strike."""
        worksheet = self.sheet.worksheet(worksheet_name)
        all_data = worksheet.get_all_records()

        stats = {}
        for row in all_data:
            strike_key = row.get('Strike')
            if strike and strike_key != str(strike):
                continue

            ce = float(row.get('CE_Premium', 0))
            pe = float(row.get('PE_Premium', 0))

            if strike_key not in stats:
                stats[strike_key] = {'ce': [], 'pe': []}

            stats[strike_key]['ce'].append(ce)
            stats[strike_key]['pe'].append(pe)

        # Calculate means
        for strike_key in stats:
            if stats[strike_key]['ce']:
                stats[strike_key]['ce_mean'] = sum(stats[strike_key]['ce']) / len(stats[strike_key]['ce'])
            if stats[strike_key]['pe']:
                stats[strike_key]['pe_mean'] = sum(stats[strike_key]['pe']) / len(stats[strike_key]['pe'])

        return stats

# Example usage in Streamlit
if __name__ == "__main__":
    manager = GoogleSheetManager(
        credentials_path='credentials.json',
        sheet_id='YOUR_SHEET_ID_HERE'
    )

    # Add data
    manager.append_premium_data(
        'NIFTY_Premium_History',
        date=datetime.now().strftime('%Y-%m-%d'),
        time=datetime.now().strftime('%H:%M:%S'),
        strike=23250,
        expiry='2026-04-07',
        iv=14.2,
        ivp=42,
        ce_premium=284.65,
        pe_premium=201.20
    )

    # Read data
    recent = manager.get_recent_premiums('NIFTY_Premium_History', limit=5)
    print(recent)
```

### 9.2 Update app.py to use helper
```python
from gsheet_manager import GoogleSheetManager

# Initialize manager (do this once in sidebar)
with st.sidebar:
    gsheet_manager = GoogleSheetManager(
        credentials_path='credentials.json',
        sheet_id=st.secrets.get('GOOGLE_SHEET_ID')  # or hardcode for now
    )

# In Tab 2, after fetching Kite API data:
def save_premium_to_sheet(instrument, strike, expiry, iv, ivp, ce_prem, pe_prem):
    worksheet_name = 'NIFTY_Premium_History' if instrument == 'NIFTY 50' else 'SENSEX_Premium_History'
    gsheet_manager.append_premium_data(
        worksheet_name,
        date=datetime.now().strftime('%Y-%m-%d'),
        time=datetime.now().strftime('%H:%M:%S'),
        strike=strike,
        expiry=expiry,
        iv=iv,
        ivp=ivp,
        ce_premium=ce_prem,
        pe_premium=pe_prem,
        notes=f'Auto-fetched from Kite API'
    )
```

---

## Step 10: Secure Credentials in Streamlit Cloud

### 10.1 If deploying to Streamlit Cloud
1. Do NOT commit `credentials.json` to GitHub
2. Add to `.gitignore`:
   ```
   credentials.json
   .env
   ```

3. In Streamlit Cloud dashboard:
   - App settings → Secrets
   - Add content of credentials.json as `google_credentials`
   - Add Sheet ID as `google_sheet_id`

4. Update code:
   ```python
   import streamlit as st
   import json
   import tempfile

   # Load from secrets
   creds_dict = st.secrets.get("google_credentials", {})

   # Write to temporary file
   with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
       json.dump(creds_dict, f)
       creds_path = f.name

   manager = GoogleSheetManager(
       credentials_path=creds_path,
       sheet_id=st.secrets.get('google_sheet_id')
   )
   ```

---

## Step 11: Create Scheduled Update Job

### 11.1 Daily Premium Fetch Script
File: `fetch_and_cache_premiums.py`

```python
"""
Scheduled job to fetch daily option premiums from Kite API and cache in Google Sheets
Run this daily after market close (e.g., 4:00 PM IST)
"""

from gsheet_manager import GoogleSheetManager
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

def fetch_and_cache_premiums(instrument='NIFTY 50', expiry_date=None):
    """Fetch premiums for all offsets and cache to Google Sheets."""

    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    manager = GoogleSheetManager(
        credentials_path='credentials.json',
        sheet_id=sheet_id
    )

    worksheet_name = 'NIFTY_Premium_History' if instrument == 'NIFTY 50' else 'SENSEX_Premium_History'

    # TODO: Fetch from Kite API using mcp__kite__get_quotes
    # For each offset (±2.5%, ±3.0%, ±3.5%, ±4.0%, ±4.5%):
    #   1. Calculate strike
    #   2. Fetch CE premium
    #   3. Fetch PE premium
    #   4. Call manager.append_premium_data()

    print(f"[OK] Cached {count} premium entries to Google Sheets")

if __name__ == "__main__":
    fetch_and_cache_premiums('NIFTY 50')
```

### 11.2 Schedule with Cron (Linux/Mac)
```bash
# Edit crontab
crontab -e

# Add line to run at 4 PM daily (16:00 IST = 10:30 UTC)
# Note: Adjust timezone as needed
30 10 * * 1-5 cd /path/to/project && python fetch_and_cache_premiums.py >> logs/cache.log 2>&1
```

### 11.3 Schedule with Windows Task Scheduler
1. Open **Task Scheduler**
2. Click **Create Task**
3. **General** tab:
   - Name: "Nifty-Premium-Cache"
   - Run with highest privileges: ✓

4. **Triggers** tab:
   - New Trigger
   - Begin task: On a schedule
   - Daily
   - Time: 16:00 (4:00 PM)
   - Repeat every 1 day
   - Enabled: ✓

5. **Actions** tab:
   - New Action
   - Program: `python.exe` (full path: `C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe`)
   - Arguments: `fetch_and_cache_premiums.py`
   - Start in: `E:\Personal\Trading_Champion\Projects\Nifty Weekly Options Strategy_v1`

6. Click **OK**

---

## Troubleshooting

### Issue: "403 Forbidden - Request had insufficient authentication scopes"
**Solution:**
```python
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
```

### Issue: "gspread.exceptions.SpreadsheetNotFound"
**Solution:**
- Check SHEET_ID in URL is correct
- Verify sheet is shared with service account email
- Try opening sheet link in browser while logged in as service account

### Issue: "ModuleNotFoundError: No module named 'gspread'"
**Solution:**
```bash
pip install gspread google-auth-oauthlib google-auth-httplib2
```

### Issue: "Could not automatically determine credentials"
**Solution:**
- Verify credentials.json exists in correct directory
- Check file path is correct (use absolute paths)
- Ensure JSON file is valid (open and check syntax)

### Issue: "Rate limit exceeded"
**Solution:**
- Add delays between API calls: `import time; time.sleep(1)`
- Cache data locally instead of querying repeatedly
- Use batch operations (append_rows instead of multiple append_row calls)

---

## Next Steps

1. ✅ Complete Steps 1-10 above
2. ✅ Test with `test_gsheet_connection.py`
3. ✅ Integrate `gsheet_manager.py` into app.py
4. ✅ Add scheduled job for daily premium caching (Step 11)
5. ⏭️ Update Tab 1 Backtest to query cached data instead of formula
6. ⏭️ Create Tab 4 "Historical Validation" showing actual vs. formula P&L

---

## Reference URLs

- [Google Cloud Console](https://console.cloud.google.com/)
- [Google Sheets API Docs](https://developers.google.com/sheets/api)
- [gspread Documentation](https://docs.gspread.org/)
- [Service Account Setup Guide](https://cloud.google.com/docs/authentication/getting-started)
- [Google Sheets Python Guide](https://docs.gspread.org/en/latest/auth.html)

---

## Security Checklist

- ✅ credentials.json in `.gitignore` (not committed)
- ✅ API keys in environment variables or `.env` (not in code)
- ✅ Google Sheet shared only with service account (not public)
- ✅ Service account has minimal required permissions (Editor on sheet only)
- ✅ Secrets managed in Streamlit Cloud (if deployed)
- ✅ Credentials file stored securely (restricted read access)

---

**Last Updated:** 2026-04-04
**Status:** Phase 2 Implementation Guide
