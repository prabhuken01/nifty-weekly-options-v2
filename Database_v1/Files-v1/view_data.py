import psycopg2

conn = psycopg2.connect(host="localhost", port=5432, database="nifty_sensex_options", user="postgres", password="postgres")
cur = conn.cursor()

print("="*100)
print("VIEWING option_bars_daily TABLE")
print("="*100)

# Show first 20 rows
cur.execute("SELECT timestamp, symbol, strike, option_type, close, iv, delta FROM option_bars_daily ORDER BY timestamp DESC LIMIT 20")
print("\nFirst 20 records:")
print(f"{'Timestamp':<25} {'Symbol':<10} {'Strike':<10} {'Type':<6} {'Close':<12} {'IV':<10} {'Delta':<10}")
print("-"*100)
for row in cur.fetchall():
    print(f"{str(row[0]):<25} {row[1]:<10} {row[2]:<10.0f} {row[3]:<6} {row[4]:<12.2f} {row[5]:<10.2f} {row[6]:<10.4f}")

# Statistics
print("\n" + "="*100)
print("SUMMARY")
print("="*100)
cur.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM option_bars_daily")
count, min_date, max_date = cur.fetchone()
print(f"Total records: {count}")
print(f"Date range: {min_date} to {max_date}")

cur.execute("SELECT symbol, COUNT(*) FROM option_bars_daily GROUP BY symbol")
print("\nRecords by symbol:")
for sym, cnt in cur.fetchall():
    print(f"  {sym}: {cnt}")

cur.close()
conn.close()
print("\n[OK] Done")
