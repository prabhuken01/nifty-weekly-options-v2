# Google Sheets API Setup - Quick Checklist ⚡

## Copy-Paste Quick Start (15 minutes)

### ☐ Part A: Cloud Setup (5 min)

```
1. Go to: https://console.cloud.google.com/
2. Login with Google account
3. NEW PROJECT → name: "Nifty-Trading"
4. Go to: APIs & Services → Library
5. Search: "Google Sheets API" → Click → ENABLE
6. Search: "Google Drive API" → Click → ENABLE
7. Go to: APIs & Services → Credentials
8. CREATE CREDENTIALS → Service Account
   - Name: "nifty-premium-cache"
   - Click CREATE AND CONTINUE → CONTINUE
9. CREATE KEY → JSON → Download
   - Save as: E:\...\credentials.json
10. ✓ DONE - You have credentials.json
```

---

### ☐ Part B: Python Setup (3 min)

```bash
# Open Command Prompt in your project directory:
cd E:\Personal\Trading_Champion\Projects\Nifty Weekly Options Strategy_v1

# Install libraries:
pip install gspread google-auth-oauthlib google-auth-httplib2 python-dotenv
```

---

### ☐ Part C: Google Sheet Setup (4 min)

```
1. Go to: https://sheets.google.com/
2. Click "+" New blank sheet
3. Rename to: "NIFTY_Premium_History"
4. Add headers in Row 1:
   A1: Date      B1: Time      C1: Strike    D1: Expiry
   E1: IV        F1: IVP       G1: CE_Premium H1: PE_Premium
   I1: Notes

5. Click "+" → New sheet → Rename: "SENSEX_Premium_History"
6. Add same headers to this sheet too

7. Click SHARE (top-right)
8. Find service account email in credentials.json:
   - Open credentials.json in text editor
   - Look for: "client_email": "nifty-premium-cache@..."
   - Copy that email

9. Paste email in Share dialog → Give "Editor" permission → SHARE
10. In URL, find and SAVE this ID:
    https://docs.google.com/spreadsheets/d/[THIS_ID_HERE]/edit
    → Copy and save this ID
```

---

### ☐ Part D: Test Connection (3 min)

Create file: `quick_test.py`

```python
import gspread
from google.oauth2.service_account import Credentials

# Step 1: Set your sheet ID (from URL)
SHEET_ID = "PASTE_YOUR_ID_HERE"

# Step 2: Authenticate
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
client = gspread.authorize(creds)

# Step 3: Open sheet
try:
    sheet = client.open_by_key(SHEET_ID)
    print("[SUCCESS] Connected to Google Sheet!")
    print(f"Sheet title: {sheet.title}")
    print(f"Worksheets: {[w.title for w in sheet.worksheets()]}")

    # Step 4: Add test row
    ws = sheet.worksheet('NIFTY_Premium_History')
    ws.append_row(['2026-04-04', '15:30', '23250', '2026-04-07', '14.2', '42', '284.65', '201.20', 'TEST'])
    print("[SUCCESS] Test row added!")

except Exception as e:
    print(f"[ERROR] {e}")
    print("Troubleshoot:")
    print("  1. Is credentials.json in correct folder?")
    print("  2. Is SHEET_ID correct (from URL)?")
    print("  3. Is sheet shared with service account email?")
```

Run: `python quick_test.py`

**Expected output:**
```
[SUCCESS] Connected to Google Sheet!
Sheet title: NIFTY_Premium_History
Worksheets: ['NIFTY_Premium_History', 'SENSEX_Premium_History']
[SUCCESS] Test row added!
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Wrong credentials path | Check credentials.json location |
| `404 Not Found` | Wrong Sheet ID | Copy full ID from URL bar |
| `Permission Denied` | Sheet not shared | Share sheet with service account email |
| `ModuleNotFoundError: gspread` | Library not installed | Run: `pip install gspread` |
| `FileNotFoundError: credentials.json` | File doesn't exist | Verify download location |

---

## Configuration Template

Create file: `.env`

```
# Google Sheets Configuration
GOOGLE_SHEET_ID=YOUR_SHEET_ID_HERE
GOOGLE_CREDENTIALS_PATH=./credentials.json
GOOGLE_SHEET_NIFTY_WS=NIFTY_Premium_History
GOOGLE_SHEET_SENSEX_WS=SENSEX_Premium_History

# Kite API Configuration
KITE_API_KEY=YOUR_KITE_KEY
KITE_ACCESS_TOKEN=YOUR_ACCESS_TOKEN

# Streamlit Configuration
STREAMLIT_CLIENT_TOOLBAR_MODE=minimal
```

Then use in Python:
```python
from dotenv import load_dotenv
import os

load_dotenv()
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
```

---

## File Structure After Setup

```
Nifty Weekly Options Strategy_v1/
├── app.py                              (main Streamlit app)
├── credentials.json                    (service account JSON - ADD TO .gitignore!)
├── .env                                (local config - ADD TO .gitignore!)
├── gsheet_manager.py                   (helper class)
├── fetch_and_cache_premiums.py         (scheduled job)
├── quick_test.py                       (test script)
├── GOOGLE_SHEETS_SETUP.md              (this guide)
└── .gitignore
    credentials.json
    .env
    __pycache__/
```

---

## Verify Everything Works

Run this complete test:

```python
# test_complete_setup.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# 1. Check files exist
print("1. Checking files...")
assert os.path.exists('credentials.json'), "credentials.json not found"
assert os.path.exists('.env'), ".env not found"
print("   [OK] Files exist")

# 2. Authenticate
print("2. Authenticating...")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
client = gspread.authorize(creds)
print("   [OK] Authenticated")

# 3. Connect to sheet
print("3. Connecting to sheet...")
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
sheet = client.open_by_key(SHEET_ID)
print(f"   [OK] Connected to: {sheet.title}")

# 4. Write test data
print("4. Writing test data...")
ws = sheet.worksheet('NIFTY_Premium_History')
test_row = [
    datetime.now().strftime('%Y-%m-%d'),
    datetime.now().strftime('%H:%M:%S'),
    '23250', '2026-04-07', '14.2', '42',
    '284.65', '201.20', 'Setup verification'
]
ws.append_row(test_row)
print("   [OK] Test row added")

# 5. Read back
print("5. Reading data...")
all_rows = ws.get_all_records()
print(f"   [OK] Sheet has {len(all_rows)} rows")
if all_rows:
    last_row = all_rows[-1]
    print(f"   Last entry: {last_row.get('Date')} - Strike {last_row.get('Strike')}")

print("\n✓ ALL TESTS PASSED - Ready for Phase 2!")
```

Run: `python test_complete_setup.py`

---

## Next: Integrate with Streamlit

Once everything passes, update `app.py`:

```python
# Add at top of app.py
from gsheet_manager import GoogleSheetManager
from dotenv import load_dotenv
import os

load_dotenv()

# In sidebar or at startup:
@st.cache_resource
def init_gsheet():
    return GoogleSheetManager(
        credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json'),
        sheet_id=os.getenv('GOOGLE_SHEET_ID')
    )

gsheet_mgr = init_gsheet()

# In Tab 2, after fetching premiums:
if gsheet_mgr:
    gsheet_mgr.append_premium_data(
        'NIFTY_Premium_History',
        date=datetime.now().strftime('%Y-%m-%d'),
        time=datetime.now().strftime('%H:%M:%S'),
        strike=strike,
        expiry=str(expiry_dt),
        iv=iv,
        ivp=ivp,
        ce_premium=ce_prem,
        pe_premium=pe_prem,
        notes=f"Auto-cached | IVP regime: {regime}"
    )
```

---

## Timeline to Complete

| Step | Duration | Deadline |
|------|----------|----------|
| A: Cloud Setup | 5 min | Today |
| B: Python Libraries | 3 min | Today |
| C: Google Sheet | 4 min | Today |
| D: Test Connection | 3 min | Today |
| **Total Setup Time** | **~15 min** | **Today** |
| E: Integrate with app.py | 30 min | Tomorrow |
| F: Schedule daily job | 15 min | Next week |

---

## Support

If stuck at any step:
1. Check the detailed guide: `GOOGLE_SHEETS_SETUP.md`
2. Verify credentials.json is valid JSON (use https://jsonlint.com/)
3. Check service account email is shared on sheet (not just your account)
4. Try test scripts step by step

**Most common issue:** Sheet not shared with service account email ← Check this first!

---

**Good luck! 🚀 Once setup is complete, Phase 2 is unlocked.**
