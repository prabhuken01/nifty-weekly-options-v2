"""
Sanity-check historical CSV vs Tab 2 logic (sample: 2024-10-14, 14:00 entry, T-1 exit).
Run from repo root:  python Backtest-Engine/validate_sample_trade.py
"""
import os
import sys
from datetime import timedelta

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CSV_PATH = os.path.join(os.path.dirname(__file__), "final_merged_output_30m_strike_within_6pct.csv")
LOT = 65


def load():
    if not os.path.isfile(CSV_PATH):
        print(f"Missing: {CSV_PATH}")
        sys.exit(1)
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp_30m", "expiry"])
    df["tdate"] = df["timestamp_30m"].dt.date
    df["edate"] = df["expiry"].dt.date
    df["hhmm"] = df["timestamp_30m"].dt.strftime("%H:%M")
    return df


def main():
    df = load()
    trade_date = pd.to_datetime("2024-10-14").date()
    use_time = "14:00"
    print(f"=== Sample trade check: {trade_date} @ {use_time} ===\n")

    times = sorted(df[df["tdate"] == trade_date]["hhmm"].unique())
    print("Bars on trade date:", times[:5], "...", times[-3:])

    expiries = sorted(df[df["edate"] > trade_date]["edate"].unique())
    expiry = expiries[0]
    spot_rows = df[(df["tdate"] == trade_date) & (df["hhmm"] == use_time)]
    if spot_rows.empty:
        print("No rows at", use_time)
        sys.exit(1)
    spot = float(spot_rows.iloc[0]["underlying_spot_close"])
    print(f"Spot @ {use_time}: Rs {spot:,.2f}  |  Expiry: {expiry}\n")

    put_strike = round(spot * 0.98 / 50) * 50
    call_strike = round(spot * 1.02 / 50) * 50
    print(f"Short strangle -2%/+2%: PE {put_strike}  CE {call_strike}\n")

    def prem(d, strike, ot):
        r = df[(df["tdate"] == d) & (df["edate"] == expiry) & (df["strike_price"] == float(strike))
               & (df["option_type"] == ot) & (df["hhmm"] == use_time)]
        return float(r["close"].iloc[0]) if len(r) else None

    t1 = expiry - timedelta(days=1)
    while t1.weekday() >= 5:
        t1 -= timedelta(days=1)
    exit_time = "15:00"  # matches Streamlit Tab 2 exit bar

    def prem_exit(d, strike, ot):
        r = df[(df["tdate"] == d) & (df["edate"] == expiry) & (df["strike_price"] == float(strike))
               & (df["option_type"] == ot) & (df["hhmm"] == exit_time)]
        return float(r["close"].iloc[0]) if len(r) else None

    total = 0
    for strike, ot, name in [(put_strike, "PE", "Short Put"), (call_strike, "CE", "Short Call")]:
        e = prem(trade_date, strike, ot)
        x = prem_exit(t1, strike, ot)
        if e is not None and x is not None:
            pnl = round((e - x) * LOT)
            total += pnl
            print(f"{name} {strike}: entry Rs {e:.2f}  exit Rs {x:.2f}  P&L Rs {pnl:+,}  (exit {t1})")
        else:
            print(f"{name} {strike}: entry={e} exit={x}  (missing row)")
    print(f"\nTotal (lot {LOT}): Rs {total:+,}")
    print(f"Capital (2 short legs x Rs 1,25,000): Rs 2,50,000  ->  return {total/250000*100:+.3f}%")


if __name__ == "__main__":
    main()
