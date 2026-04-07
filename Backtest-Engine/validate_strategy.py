#!/usr/bin/env python3
"""
Strategy Validation: Fetch actual historical data to validate P&L model
"""
import os
import sys
from datetime import datetime, timedelta
import json

print("[INFO] Strategy Validation - Data Fetching")
print("[INFO] ================================================")

# Check Kite credentials
print("\n[CHECK] Kite Connect Credentials")
kite_creds_paths = [
    os.path.expanduser("~/.kite_credentials.json"),
    os.path.expanduser("~/.zerodha/kite.json"),
    "kite_credentials.json",
]

cred_found = None
for path in kite_creds_paths:
    if os.path.exists(path):
        print(f"[FOUND] {path}")
        cred_found = path
        break

if not cred_found:
    print("[MISSING] No Kite credentials file found")
    print("[ACTION] Need one of:")
    print("  1) API Key + Access Token")
    print("  2) Save JSON at ~/.kite_credentials.json")

# Check data requirements
print("\n[PLAN] Data Collection Strategy")
print("  1) Fetch NIFTY weekly option data (NSE Bhavcopy)")
print("  2) Fetch SENSEX weekly option data (BSE Bhavcopy)")
print("  3) Calculate actual premiums collected")
print("  4) Calculate actual win rates from historical data")
print("  5) Recalculate strategy P&L with real data")

print("\n[STATUS] Ready to fetch data")
print("  - yfinance: Available (no auth needed)")
print("  - NSE Bhavcopy: Need to fetch from NSE website")
print("  - BSE Bhavcopy: Need to fetch from BSE website")
print(f"  - Kite Connect: {'Available' if cred_found else 'Need credentials'}")

# Next steps
print("\n[NEXT] Provide Kite credentials or confirm to proceed with yfinance + Bhavcopy fetch")
