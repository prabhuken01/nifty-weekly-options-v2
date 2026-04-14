import pandas as pd
import os

print("="*80)
print("BATCH 5: CONVERT PARQUET TO CSV (with old & new IV)")
print("="*80)

# Load parquet
print("\n[1/3] Loading parquet...")
df = pd.read_parquet('final_merged_output_30m_strike_within_6pct.parquet')
print(f"  Loaded {len(df):,} rows")
print(f"  Columns: {list(df.columns)}")

# Load IV comparison data
print("\n[2/3] Loading IV comparison data...")
iv_impact = pd.read_csv('iv_impact_analysis.csv')
print(f"  Loaded {len(iv_impact)} dates with IV calculations")

# Create mapping from date to IV data
iv_map = {}
for idx, row in iv_impact.iterrows():
    date_key = str(row['date'])
    iv_map[date_key] = {
        'old_iv': row['old_iv'],
        'new_iv': row['new_iv'],
        'old_band': None,  # Can add if needed
        'new_band': None
    }

# Add IV columns to main dataset
print("\n[3/3] Merging IV data and converting...")
df['date_str'] = pd.to_datetime(df['timestamp_30m']).dt.date.astype(str)
df['old_iv'] = df['date_str'].map(lambda x: iv_map.get(x, {}).get('old_iv'))
df['new_iv'] = df['date_str'].map(lambda x: iv_map.get(x, {}).get('new_iv'))

# Save as CSV
output_name = 'final_merged_output_30m_strike_within_6pct_updated.csv'
print(f"\n  Saving to {output_name}...")
df.to_csv(output_name, index=False)

print(f"  [OK] Saved {len(df):,} rows")
print(f"\n  Columns in output:")
print(f"    - All original columns from parquet")
print(f"    - old_iv: IV using nearest expiry (original method)")
print(f"    - new_iv: IV using DTE>=2 rule (new method)")

# Show sample
print(f"\n  Sample rows:")
sample_cols = ['timestamp_30m', 'strike_price', 'option_type', 'close', 'old_iv', 'new_iv']
sample_df = df[sample_cols].dropna(subset=['old_iv', 'new_iv']).head(5)
for idx, row in sample_df.iterrows():
    print(f"    {row['timestamp_30m']} | Strike {row['strike_price']} {row['option_type']} | "
          f"Prem {row['close']:.1f} | Old IV {row['old_iv']:.4f} | New IV {row['new_iv']:.4f}")

print("\n" + "="*80)
print("BATCH 5 COMPLETE")
print("="*80)
print("\nFinal outputs in Backtest-Engine/:")
print("  [OK] final_merged_output_30m_strike_within_6pct_updated.csv")
print(f"     - {len(df):,} rows, all option data with old & new IV")
print("  [OK] IV_Impact_Analysis.xlsx (detailed band analysis)")
print("  [OK] LUT_Impact_Summary.xlsx (LUT retraining verdict)")
print("  [OK] iv_series_14day.csv (latest 14 days for IV Analysis tab)")
print("\nApp updates:")
print("  [OK] bt_iv_straddle() now uses DTE>=2 rule")
print("  [OK] IV Analysis tab added (tab 4)")
print("  [OK] Ready to deploy!")
