import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date

print("="*80)
print("BATCH 4: IV ANALYSIS TAB DATA PREPARATION")
print("="*80)

# Load parquet
print("\n[1/3] Loading parquet and computing 14-day IV series...")
df = pd.read_parquet('final_merged_output_30m_strike_within_6pct.parquet')
df['timestamp_30m'] = pd.to_datetime(df['timestamp_30m'])
df['expiry'] = pd.to_datetime(df['expiry'])
df['tdate'] = df['timestamp_30m'].dt.date
df['edate'] = df['expiry'].dt.date
df['hhmm'] = df['timestamp_30m'].dt.strftime('%H:%M')

# Get unique trade dates (sorted, most recent first)
unique_dates = sorted(df['tdate'].unique(), reverse=True)

# Keep last 14 days
recent_dates = unique_dates[:14] if len(unique_dates) >= 14 else unique_dates
recent_dates = sorted(recent_dates)  # Sort ascending for chart

print(f"  Computing IV for {len(recent_dates)} recent dates")
print(f"  Date range: {recent_dates[0]} to {recent_dates[-1]}")

# NSE holidays (from app.py)
NSE_HOLIDAYS = {
    date(2026,1,26), date(2026,3,25), date(2026,4,2), date(2026,4,5),
    date(2026,4,6),  date(2026,4,14), date(2026,5,1), date(2026,8,15),
    date(2026,10,2), date(2026,10,26),date(2026,11,4),date(2026,12,25),
}

def effective_dte(from_date, expiry):
    count, d = 0, from_date + timedelta(days=1)
    while d <= expiry:
        if d.weekday() < 5 and d not in NSE_HOLIDAYS:
            count += 1
        d += timedelta(days=1)
    return max(count, 1)

# Compute IV series
import math

iv_series = []

for trade_d in recent_dates:
    # Get spot at 15:00
    spot_rows = df[(df['tdate'] == trade_d) & (df['hhmm'] == '15:00')]
    if spot_rows.empty:
        continue

    spot = float(spot_rows['underlying_spot_close'].iloc[0])

    # Get first expiry with DTE >= 2
    exp_rows = df[(df['edate'] >= trade_d)].sort_values('edate')
    if exp_rows.empty:
        continue

    rnd = 50
    atm = int(round(spot / rnd) * rnd)

    new_iv = None
    new_exp = None
    new_dte = None

    for exp_date in exp_rows['edate'].unique():
        dte = effective_dte(trade_d, exp_date)
        if dte >= 2:
            new_exp = exp_date
            new_dte = dte
            break

    if new_exp:
        rows_new = df[(df['tdate']==trade_d) & (df['edate']==new_exp) & (df['hhmm']=='15:00')]
        ce_new = rows_new[(rows_new['strike_price']==atm) & (rows_new['option_type']=='CE')]['close']
        pe_new = rows_new[(rows_new['strike_price']==atm) & (rows_new['option_type']=='PE')]['close']

        if len(ce_new) and len(pe_new):
            stv_new = float(ce_new.iloc[0]) + float(pe_new.iloc[0])
            if new_dte > 0:
                T_new = new_dte / 365
                new_iv = round(stv_new / (0.8 * spot * math.sqrt(T_new)), 4) if stv_new > 1 else None

    if new_iv:
        iv_series.append({
            'date': trade_d,
            'iv': new_iv * 100,  # Convert to percentage for display
            'spot': round(spot, 2),
            'atm_strike': atm,
            'expiry': new_exp,
            'dte': new_dte,
            'method': 'DTE>=2'
        })

series_df = pd.DataFrame(iv_series)

print(f"  Computed {len(series_df)} IV values")

# Compute statistics
if len(series_df) > 0:
    print(f"\n  Statistics (last {len(series_df)} days):")
    print(f"    Mean IV: {series_df['iv'].mean():.2f}%")
    print(f"    Min IV:  {series_df['iv'].min():.2f}%")
    print(f"    Max IV:  {series_df['iv'].max():.2f}%")
    print(f"    Latest:  {series_df.iloc[-1]['iv']:.2f}% ({series_df.iloc[-1]['date']})")

# Save for tab display
print("\n[2/3] Creating display data...")
series_df.to_csv('iv_series_14day.csv', index=False)

# Also save as JSON for web display
import json
series_json = series_df.to_dict(orient='records')
with open('iv_series_14day.json', 'w') as f:
    json.dump(series_json, f, default=str, indent=2)

print(f"  Saved: iv_series_14day.csv and iv_series_14day.json")

# Create comparison table (current vs historical average)
print("\n[3/3] Generating comparison metrics...")

if len(series_df) > 0:
    latest_row = series_df.iloc[-1]
    hist_mean = series_df['iv'].mean()
    hist_median = series_df['iv'].median()
    hist_std = series_df['iv'].std()

    latest_iv = latest_row['iv']
    z_score = (latest_iv - hist_mean) / hist_std if hist_std > 0 else 0

    comparison = {
        'latest_date': str(latest_row['date']),
        'latest_iv': float(round(latest_iv, 2)),
        'latest_spot': float(latest_row['spot']),
        'latest_atm': int(latest_row['atm_strike']),
        'latest_expiry': str(latest_row['expiry']),
        'latest_dte': int(latest_row['dte']),
        'historical_mean': float(round(hist_mean, 2)),
        'historical_median': float(round(hist_median, 2)),
        'historical_std': float(round(hist_std, 2)),
        'z_score': float(round(z_score, 2)),
        'percentile_rank': float(round(100 * len(series_df[series_df['iv'] <= latest_iv]) / len(series_df), 1)),
        'days_analyzed': int(len(series_df)),
        'iv_percentile_band': (
            'Low (<20th percentile)' if z_score < -1 else
            'Low-Medium (-1 to 0 sigma)' if z_score < 0 else
            'Medium-High (0 to 1 sigma)' if z_score < 1 else
            'High (>1 sigma)'
        )
    }

    print(f"\n  Latest IV ({latest_row['date']}): {comparison['latest_iv']}%")
    print(f"  14-day Mean: {comparison['historical_mean']}%")
    print(f"  Z-score: {comparison['z_score']} ({comparison['iv_percentile_band']})")
    print(f"  Percentile: {comparison['percentile_rank']:.1f}%")

    # Save comparison
    with open('iv_comparison_metrics.json', 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"\n  Saved: iv_comparison_metrics.json")

print("\n" + "="*80)
print("BATCH 4 COMPLETE")
print("="*80)
print("\nOutputs for IV Analysis tab:")
print("  - iv_series_14day.csv (14-day IV history)")
print("  - iv_series_14day.json (for chart display)")
print("  - iv_comparison_metrics.json (latest vs historical)")
print("\nNext: BATCH 5 will update app.py and deploy")
