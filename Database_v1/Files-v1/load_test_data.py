#!/usr/bin/env python3
"""Load realistic test data to verify database works end-to-end"""

import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "nifty_sensex_options"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

def load_test_data():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cur = conn.cursor()

        # Generate 10 days of realistic options data
        print("Generating test data...")
        records = []

        end_date = date.today() - timedelta(days=2)  # 2 days ago
        start_date = end_date - timedelta(days=10)

        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Weekdays only

                for symbol in ['NIFTY', 'SENSEX']:
                    base_price = 23500 if symbol == 'NIFTY' else 77000

                    for strike_offset in [-500, -200, 0, 200, 500]:
                        for opt_type in ['CE', 'PE']:

                            strike = base_price + strike_offset
                            close_price = 150 + np.random.uniform(-50, 150)

                            records.append((
                                pd.Timestamp(datetime.combine(current_date, datetime.strptime("15:30", "%H:%M").time())),
                                symbol,
                                strike,
                                opt_type,
                                current_date + timedelta(days=4),
                                100.0 + np.random.uniform(-50, 50),
                                180.0 + np.random.uniform(0, 50),
                                80.0 + np.random.uniform(-30, 20),
                                close_price,
                                int(np.random.uniform(100000, 5000000)),
                                int(np.random.uniform(50000, 10000000)),
                                25.5 + np.random.uniform(-10, 10),
                                np.random.uniform(-1, 1),
                                np.random.uniform(0, 0.01),
                                np.random.uniform(-0.5, 0.1),
                                np.random.uniform(0, 1),
                                np.random.uniform(-0.5, 0.5)
                            ))

            current_date += timedelta(days=1)

        print(f"Inserting {len(records)} records...")

        execute_batch(
            cur,
            """
            INSERT INTO option_bars_daily
            (timestamp, symbol, strike, option_type, expiry, open, high, low, close,
             volume, open_interest, iv, delta, gamma, theta, vega, rho)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, strike, option_type, expiry)
            DO UPDATE SET close = EXCLUDED.close
            """,
            records,
            page_size=500
        )

        conn.commit()

        # Verify data
        cur.execute("SELECT COUNT(*) FROM option_bars_daily;")
        count = cur.fetchone()[0]

        cur.execute("SELECT symbol, COUNT(*) FROM option_bars_daily GROUP BY symbol;")
        by_symbol = cur.fetchall()

        cur.execute("SELECT option_type, COUNT(*) FROM option_bars_daily GROUP BY option_type;")
        by_type = cur.fetchall()

        cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM option_bars_daily;")
        date_range = cur.fetchone()

        cur.close()
        conn.close()

        print("\n" + "="*70)
        print("SUCCESS: Test data loaded to database!")
        print("="*70)
        print(f"Total records: {count}")
        print(f"Date range: {date_range[0]} to {date_range[1]}")
        print(f"\nBy Symbol:")
        for sym, cnt in by_symbol:
            print(f"  {sym}: {cnt} records")
        print(f"\nBy Option Type:")
        for typ, cnt in by_type:
            print(f"  {typ}: {cnt} records")
        print("="*70)

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    load_test_data()
