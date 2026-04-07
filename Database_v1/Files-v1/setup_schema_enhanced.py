#!/usr/bin/env python3
"""
Enhanced PostgreSQL schema for both daily (6-month history) and minute (future weeklies) data
"""

import psycopg2

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "nifty_sensex_options"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

def setup_enhanced_schema():
    try:
        # Connect to postgres (default DB)
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database="postgres",
            user=DB_USER, password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("="*80)
        print("ENHANCED SCHEMA SETUP - DAILY + MINUTE DATA")
        print("="*80)

        print("\n[STEP 1] Creating database...")
        try:
            cur.execute("DROP DATABASE IF EXISTS nifty_sensex_options;")
        except:
            pass
        cur.execute("CREATE DATABASE nifty_sensex_options;")
        print("[OK] Database created")
        cur.close()
        conn.close()

        # Connect to new database
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        cur = conn.cursor()

        # ====================================================================
        # TABLE 1: DAILY DATA (6-month history for backtesting)
        # ====================================================================
        print("\n[STEP 2] Creating option_bars_daily table (6-month history)...")
        cur.execute("""
            DROP TABLE IF EXISTS option_bars_daily CASCADE;

            CREATE TABLE option_bars_daily (
                id                  SERIAL PRIMARY KEY,
                timestamp           TIMESTAMP NOT NULL,
                symbol              VARCHAR(10) NOT NULL,
                strike              DECIMAL(10, 2) NOT NULL,
                option_type         VARCHAR(2) NOT NULL,
                expiry              DATE NOT NULL,
                open                DECIMAL(10, 4),
                high                DECIMAL(10, 4),
                low                 DECIMAL(10, 4),
                close               DECIMAL(10, 4) NOT NULL,
                volume              BIGINT,
                open_interest       BIGINT,
                iv                  DECIMAL(10, 4),
                delta               DECIMAL(10, 4),
                gamma               DECIMAL(10, 4),
                theta               DECIMAL(10, 4),
                vega                DECIMAL(10, 4),
                rho                 DECIMAL(10, 4),
                updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT unique_daily UNIQUE (timestamp, symbol, strike, option_type, expiry),
                CONSTRAINT strike_range CHECK (strike BETWEEN 0.01 AND 1000000)
            );

            CREATE INDEX idx_daily_timestamp_symbol ON option_bars_daily(timestamp DESC, symbol);
            CREATE INDEX idx_daily_expiry_symbol ON option_bars_daily(expiry, symbol);
            CREATE INDEX idx_daily_strike ON option_bars_daily(strike);
        """)
        print("[OK] option_bars_daily table created (daily candles, 6-month history)")

        # ====================================================================
        # TABLE 2: MINUTE DATA (Real-time + future weekly options)
        # ====================================================================
        print("\n[STEP 3] Creating option_bars_minute table (minute data for future weeklies)...")
        cur.execute("""
            DROP TABLE IF EXISTS option_bars_minute CASCADE;

            CREATE TABLE option_bars_minute (
                id                  SERIAL PRIMARY KEY,
                timestamp           TIMESTAMP NOT NULL,
                symbol              VARCHAR(10) NOT NULL,
                strike              DECIMAL(10, 2) NOT NULL,
                option_type         VARCHAR(2) NOT NULL,
                expiry              DATE NOT NULL,
                open                DECIMAL(10, 4),
                high                DECIMAL(10, 4),
                low                 DECIMAL(10, 4),
                close               DECIMAL(10, 4) NOT NULL,
                volume              BIGINT,
                open_interest       BIGINT,
                iv                  DECIMAL(10, 4),
                delta               DECIMAL(10, 4),
                gamma               DECIMAL(10, 4),
                theta               DECIMAL(10, 4),
                vega                DECIMAL(10, 4),
                rho                 DECIMAL(10, 4),
                updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT unique_minute UNIQUE (timestamp, symbol, strike, option_type, expiry),
                CONSTRAINT strike_range_min CHECK (strike BETWEEN 0.01 AND 1000000)
            );

            CREATE INDEX idx_minute_timestamp_symbol ON option_bars_minute(timestamp DESC, symbol);
            CREATE INDEX idx_minute_expiry_symbol ON option_bars_minute(expiry, symbol);
            CREATE INDEX idx_minute_strike ON option_bars_minute(strike);
        """)
        print("[OK] option_bars_minute table created (minute candles, rolling future weeklies)")

        # ====================================================================
        # TABLE 3: METADATA (Track data sources & updates)
        # ====================================================================
        print("\n[STEP 4] Creating metadata table...")
        cur.execute("""
            DROP TABLE IF EXISTS data_metadata CASCADE;

            CREATE TABLE data_metadata (
                id                  SERIAL PRIMARY KEY,
                table_name          VARCHAR(50) NOT NULL,
                last_update         TIMESTAMP NOT NULL,
                data_type           VARCHAR(20) NOT NULL,
                source              VARCHAR(100) NOT NULL,
                records_count       BIGINT,
                date_range_from     DATE,
                date_range_to       DATE,
                status              VARCHAR(20) DEFAULT 'active'
            );

            CREATE INDEX idx_metadata_table ON data_metadata(table_name);
            CREATE INDEX idx_metadata_updated ON data_metadata(last_update DESC);
        """)
        print("[OK] data_metadata table created (tracking updates)")

        conn.commit()
        cur.close()
        conn.close()

        print("\n" + "="*80)
        print("SCHEMA SETUP COMPLETE")
        print("="*80)
        print(f"Database: {DB_NAME}")
        print(f"\nTables created:")
        print(f"  1. option_bars_daily   - Daily candles (6-month history, backtesting)")
        print(f"  2. option_bars_minute  - Minute candles (future weeklies, real-time)")
        print(f"  3. data_metadata       - Track sources & updates")
        print(f"\nIndexes:")
        print(f"  - Timestamp + Symbol optimization")
        print(f"  - Expiry + Symbol optimization")
        print(f"  - Strike price lookup")
        print(f"\nReady for:")
        print(f"  [1] Daily data: 6 months history (backtesting)")
        print(f"  [2] Minute data: Current + next 2 weeks (live trading)")
        print("="*80)

        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    setup_enhanced_schema()
