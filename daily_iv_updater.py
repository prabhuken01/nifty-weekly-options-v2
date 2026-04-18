"""
Daily IV updater — run at 15:30 IST after market close.
Fetches live option chain from Dhan, computes ATM straddle IV via Black-Scholes,
appends to data/iv_history_daily.csv.

Usage:
    python daily_iv_updater.py --token <dhan_access_token>
    python daily_iv_updater.py              # reads token from env DHAN_TOKEN

Schedule (Linux/Mac crontab - 10:00 UTC = 15:30 IST):
    0 10 * * 1-5  cd /path/to/project && python daily_iv_updater.py --token $DHAN_TOKEN

Schedule (Windows Task Scheduler):
    Program: python  |  Arguments: daily_iv_updater.py --token <TOKEN>
    Trigger: Daily weekdays at 15:30 IST
"""
import requests
import pandas as pd
import numpy as np
import math
import os
import sys
import argparse
from datetime import date, datetime, timedelta, timezone
from scipy.stats import norm
from scipy.optimize import brentq

_IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.now(_IST).replace(tzinfo=None)

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATA_DIR       = os.path.join(BASE_DIR, "data")
IV_CSV         = os.path.join(DATA_DIR, "iv_history_daily.csv")

NIFTY_SCRIP_ID = 13
UNDERLYING_SEG = "IDX_I"
BASE_URL       = "https://api.dhan.co/v2"
RND            = 50
R, Q           = 0.06, 0.015    # risk-free rate, dividend yield

def _headers(tok):
    return {
        "access-token": tok,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _bs_iv_straddle(S, K, T, r, q, market_price):
    """Implied vol from ATM straddle via Black-Scholes Brentq solver."""
    def price(sigma):
        if T <= 0 or sigma <= 0:
            return 0
        d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        call = S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        put  = K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)
        return call + put
    try:
        return brentq(lambda s: price(s) - market_price, 0.01, 2.0)
    except Exception:
        return None

def fetch_expiry_list(tok):
    r = requests.post(f"{BASE_URL}/optionchain/expirylist",
                      json={"UnderlyingScrip": NIFTY_SCRIP_ID, "UnderlyingSeg": UNDERLYING_SEG},
                      headers=_headers(tok), timeout=15)
    d = r.json()
    if d.get("status") == "success":
        return d.get("data", [])
    raise RuntimeError(f"expirylist failed: {r.status_code} {r.text[:200]}")

def fetch_chain(expiry_str, tok):
    r = requests.post(f"{BASE_URL}/optionchain",
                      json={"UnderlyingScrip": NIFTY_SCRIP_ID, "UnderlyingSeg": UNDERLYING_SEG,
                            "Expiry": expiry_str},
                      headers=_headers(tok), timeout=20)
    d = r.json()
    if d.get("status") == "success":
        return d.get("data", {})
    raise RuntimeError(f"optionchain failed: {r.status_code} {r.text[:200]}")

def capture_today_iv(tok):
    """Capture today's ATM straddle IV using live Dhan option chain (BSM)."""
    today_str = date.today().strftime("%Y-%m-%d")
    exps  = fetch_expiry_list(tok)
    valid = [e for e in exps if e >= today_str]
    if not valid:
        raise RuntimeError("No valid future expiry found")
    expiry_str = valid[0]

    chain = fetch_chain(expiry_str, tok)
    spot  = float(chain.get("last_price") or 0)
    if spot <= 0:
        raise RuntimeError("Spot price missing from chain response")

    atm = int(round(spot / RND) * RND)
    oc  = chain.get("oc", {})

    strike_row = None
    for k, v in oc.items():
        try:
            if abs(float(k) - atm) < 1:
                strike_row = v
                break
        except Exception:
            pass
    if not strike_row:
        raise RuntimeError(f"ATM strike {atm} not found in option chain")

    ce_prem = float(strike_row.get("ce", {}).get("last_price", 0) or 0)
    pe_prem = float(strike_row.get("pe", {}).get("last_price", 0) or 0)
    if ce_prem <= 0 or pe_prem <= 0:
        raise RuntimeError(f"CE={ce_prem} PE={pe_prem} — zero premium, market may be closed")
    straddle = ce_prem + pe_prem

    expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d")
    T         = max((expiry_dt - datetime.now()).total_seconds(), 0) / (365.0 * 24 * 3600)
    dte_cal   = max((expiry_dt.date() - date.today()).days, 1)

    iv = _bs_iv_straddle(spot, float(atm), T, R, Q, straddle)
    if iv is None or not (0.02 <= iv <= 2.0):
        iv = straddle / (0.8 * spot * math.sqrt(max(T, 1/365)))

    return {
        "Date":           date.today(),
        "NIFTY Spot":     round(spot, 2),
        "NIFTY IV %":     round(iv * 100, 2),
        "Expiry Used":    expiry_str,
        "DTE (Cal Days)": dte_cal,
        "ATM Strike":     atm,
        "Straddle Price": round(straddle, 1),
        "CE LTP":         round(ce_prem, 1),
        "PE LTP":         round(pe_prem, 1),
        "Source":         "Dhan Live Chain",
    }

def append_to_csv(row):
    os.makedirs(DATA_DIR, exist_ok=True)
    new_df = pd.DataFrame([row])
    new_df["Date"] = pd.to_datetime(new_df["Date"]).dt.date

    if os.path.exists(IV_CSV):
        existing = pd.read_csv(IV_CSV)
        existing["Date"] = pd.to_datetime(existing["Date"]).dt.date
        if row["Date"] in existing["Date"].values:
            print(f"[SKIP] {row['Date']} already in {IV_CSV}")
            return False
        combined = pd.concat([existing, new_df], ignore_index=True).sort_values("Date")
    else:
        combined = new_df
    combined.to_csv(IV_CSV, index=False)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", default="", help="Dhan access token")
    args, _ = parser.parse_known_args()
    tok = args.token or os.environ.get("DHAN_TOKEN", "")

    if not tok:
        print("ERROR: No Dhan token. Pass --token <token> or set DHAN_TOKEN env var.")
        sys.exit(1)

    print(f"[{now_ist().strftime('%H:%M:%S')} IST] Capturing today's IV…")
    try:
        row  = capture_today_iv(tok)
        saved = append_to_csv(row)
        if saved:
            print(f"✅ {row['Date']} | Spot {row['NIFTY Spot']} | "
                  f"IV {row['NIFTY IV %']:.1f}% | Straddle {row['Straddle Price']} | "
                  f"Expiry {row['Expiry Used']}")
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)
