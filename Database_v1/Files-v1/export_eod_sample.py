#!/usr/bin/env python3
"""
Export sample EOD options data to Excel (last 30 days)
"""
import psycopg2
import pandas as pd
from datetime import datetime, timedelta

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="nifty_sensex_options",
    user="postgres",
    password="postgres"
)

# Get last 30 days of EOD data
query = """
SELECT
    timestamp::date as Date,
    symbol,
    strike,
    option_type,
    expiry::date as Expiry,
    open,
    high,
    low,
    close as LTP,
    volume,
    open_interest as OI,
    iv,
    delta,
    gamma,
    theta,
    vega,
    rho
FROM option_bars_daily
WHERE timestamp >= NOW() - INTERVAL '30 days'
ORDER BY timestamp DESC, symbol, strike
LIMIT 5000
"""

df = pd.read_sql(query, conn)
conn.close()

# Export to Excel
output_file = "EOD_Options_Sample_Last30Days.xlsx"
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='EOD Data', index=False)

    # Format sheet
    ws = writer.sheets['EOD Data']
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 10

print(f"[OK] Date range: {df.iloc[:, 0].min()} to {df.iloc[:, 0].max()}")
print(f"[OK] Unique dates: {df.iloc[:, 0].nunique()}")
