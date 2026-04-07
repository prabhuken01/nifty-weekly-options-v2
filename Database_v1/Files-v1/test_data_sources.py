#!/usr/bin/env python3
"""
Test both Breeze API and Kaggle for historical options data
"""

import os
import json

print("="*80)
print("TESTING DATA SOURCES: Breeze API vs Kaggle")
print("="*80)

# ============================================================================
# 1. TEST BREEZE API
# ============================================================================
print("\n[TEST 1] ICICI Direct Breeze API")
print("-" * 80)

breeze_status = False
try:
    from breeze_connect import BreezeConnect

    icici_creds_paths = [
        "icici_credentials.json",
        os.path.expanduser("~/.icici_credentials.json"),
        os.path.expanduser("~/.breeze/credentials.json"),
    ]

    cred_file = None
    for path in icici_creds_paths:
        if os.path.exists(path):
            cred_file = path
            break

    if cred_file:
        with open(cred_file) as f:
            creds = json.load(f)
        print(f"[OK] Found ICICI credentials: {cred_file}")
        breeze_status = True
    else:
        print("[FAIL] ICICI credentials not found")
        print("  Need: api_key, session_key, userid in icici_credentials.json")

except Exception as e:
    print(f"[FAIL] Breeze API error: {e}")

# ============================================================================
# 2. TEST KAGGLE API
# ============================================================================
print("\n[TEST 2] Kaggle Datasets")
print("-" * 80)

kaggle_status = False
try:
    from kaggle.api.kaggle_api_extended import KaggleApi

    kaggle_json = os.path.expanduser("~/.kaggle/kaggle.json")

    if os.path.exists(kaggle_json):
        print(f"[OK] Found Kaggle credentials: {kaggle_json}")
        api = KaggleApi()
        api.authenticate()
        print("[OK] Kaggle API authenticated")
        kaggle_status = True
    else:
        print(f"[FAIL] Kaggle credentials not found at {kaggle_json}")
        print("  Download from: https://www.kaggle.com/settings/account")

except Exception as e:
    print(f"[FAIL] Kaggle error: {e}")

# ============================================================================
# 3. RECOMMENDATION
# ============================================================================
print("\n" + "="*80)
if breeze_status and kaggle_status:
    print("BOTH AVAILABLE: Use Breeze (live) + Kaggle (backup)")
elif breeze_status:
    print("BREEZE AVAILABLE: 3 years minute data, real-time, free for ICICI")
elif kaggle_status:
    print("KAGGLE AVAILABLE: Easy setup, 2020-2024+ data, no account needed")
else:
    print("NEITHER AVAILABLE: Need to set up Breeze or Kaggle credentials")
print("="*80)
