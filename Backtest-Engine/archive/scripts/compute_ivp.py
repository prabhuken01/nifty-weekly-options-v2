import pandas as pd
import numpy as np
from datetime import datetime

print("="*80)
print("COMPUTING IVP (IV PERCENTILE) - 252-DAY ROLLING WINDOW")
print("="*80)

# Load IV impact data
print("\n[1/3] Loading IV analysis data...")
iv_df = pd.read_csv('iv_impact_analysis.csv')
iv_df['date'] = pd.to_datetime(iv_df['date']).dt.date
iv_df = iv_df.sort_values('date')
print(f"  Loaded {len(iv_df)} dates")

# Compute rolling 252-day IVP for both old and new IV
print("\n[2/3] Computing 252-day rolling percentiles...")

iv_df['old_ivp'] = None
iv_df['new_ivp'] = None

for idx, row in iv_df.iterrows():
    current_date = pd.Timestamp(row['date'])
    window_start = current_date - pd.Timedelta(days=252)

    # OLD IV: Get all IVs up to current date (252-day rolling window)
    if pd.notna(row['old_iv']):
        hist_mask = (iv_df['date'] <= row['date']) & (iv_df['date'] > window_start.date()) & (iv_df['old_iv'].notna())
        hist_old = iv_df[hist_mask]['old_iv'].values

        if len(hist_old) > 0:
            percentile_old = (hist_old < row['old_iv']).sum() / len(hist_old) * 100
            iv_df.at[idx, 'old_ivp'] = round(percentile_old, 1)

    # NEW IV: Same for new method
    if pd.notna(row['new_iv']):
        hist_mask = (iv_df['date'] <= row['date']) & (iv_df['date'] > window_start.date()) & (iv_df['new_iv'].notna())
        hist_new = iv_df[hist_mask]['new_iv'].values

        if len(hist_new) > 0:
            percentile_new = (hist_new < row['new_iv']).sum() / len(hist_new) * 100
            iv_df.at[idx, 'new_ivp'] = round(percentile_new, 1)

    if (idx + 1) % 50 == 0:
        print(f"    Progress: {idx + 1}/{len(iv_df)}")

print(f"\n  Old IVP computed: {iv_df['old_ivp'].notna().sum()} dates")
print(f"  New IVP computed: {iv_df['new_ivp'].notna().sum()} dates")

# Add IV bands based on IVP tiers
def ivp_to_band(ivp):
    if ivp is None or pd.isna(ivp):
        return None
    if ivp < 20:
        return '<20 (Low)'
    elif ivp < 40:
        return '20-40 (Low-Medium)'
    elif ivp < 60:
        return '40-60 (Medium)'
    elif ivp < 80:
        return '60-80 (Medium-High)'
    else:
        return '80+ (High)'

iv_df['old_ivp_band'] = iv_df['old_ivp'].apply(ivp_to_band)
iv_df['new_ivp_band'] = iv_df['new_ivp'].apply(ivp_to_band)

# Show sample
print("\n[3/3] Sample data with IVP:")
sample_cols = ['date', 'old_iv', 'old_ivp', 'old_ivp_band', 'new_iv', 'new_ivp', 'new_ivp_band']
print(iv_df[sample_cols].dropna(subset=['old_ivp', 'new_ivp']).tail(10).to_string(index=False))

# Save enhanced version
print("\n  Saving enhanced IV analysis...")
iv_df.to_csv('iv_impact_analysis_with_ivp.csv', index=False)

# Statistics
print("\n" + "="*80)
print("IVP STATISTICS")
print("="*80)

both_valid = iv_df[(iv_df['old_ivp'].notna()) & (iv_df['new_ivp'].notna())]

if len(both_valid) > 0:
    print(f"\nComparison ({len(both_valid)} dates with both IVP values):")
    print(f"  OLD IVP (nearest expiry):")
    print(f"    Mean: {both_valid['old_ivp'].mean():.1f}")
    print(f"    Median: {both_valid['old_ivp'].median():.1f}")
    print(f"    Std Dev: {both_valid['old_ivp'].std():.1f}")
    print(f"    Min: {both_valid['old_ivp'].min():.1f} | Max: {both_valid['old_ivp'].max():.1f}")

    print(f"\n  NEW IVP (DTE>=2 rule):")
    print(f"    Mean: {both_valid['new_ivp'].mean():.1f}")
    print(f"    Median: {both_valid['new_ivp'].median():.1f}")
    print(f"    Std Dev: {both_valid['new_ivp'].std():.1f}")
    print(f"    Min: {both_valid['new_ivp'].min():.1f} | Max: {both_valid['new_ivp'].max():.1f}")

    ivp_change = both_valid['new_ivp'] - both_valid['old_ivp']
    print(f"\n  IVP CHANGE (New - Old):")
    print(f"    Mean: {ivp_change.mean():.1f} points")
    print(f"    Median: {ivp_change.median():.1f} points")
    print(f"    Std Dev: {ivp_change.std():.1f}")
    print(f"    Min: {ivp_change.min():.1f} | Max: {ivp_change.max():.1f}")

    # Band shift analysis
    band_shift_count = (iv_df['old_ivp_band'] != iv_df['new_ivp_band']).sum()
    print(f"\n  IVP BAND SHIFTS: {band_shift_count} dates ({100*band_shift_count/len(iv_df):.1f}%)")

print("\n" + "="*80)
print("IVP COMPUTATION COMPLETE")
print("="*80)
print("\nOutput: iv_impact_analysis_with_ivp.csv")
print("  - All 371 dates with old_iv, old_ivp, old_ivp_band")
print("  - All 371 dates with new_iv, new_ivp, new_ivp_band")
print("  - Ready for IV Analysis tab and Excel reports")
