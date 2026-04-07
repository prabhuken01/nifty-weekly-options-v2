#!/usr/bin/env python3
"""
Standalone script to create PostgreSQL schema for option_bars table.
Run this ONCE before running nifty_bhavcopy_loader.py
"""

import psycopg2

# Database connection parameters
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "nifty_sensex_options"
DB_USER = "postgres"
DB_PASSWORD = "postgres"  # Set to your PostgreSQL password

SQL_SCHEMA = """
CREATE DATABASE IF NOT EXISTS nifty_sensex_options;

CREATE TABLE option_bars (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    strike DECIMAL(10, 2) NOT NULL,
    option_type VARCHAR(2) NOT NULL,
    expiry DATE NOT NULL,
    open DECIMAL(10, 4),
    high DECIMAL(10, 4),
    low DECIMAL(10, 4),
    close DECIMAL(10, 4) NOT NULL,
    volume BIGINT,
    open_interest BIGINT,
    iv DECIMAL(10, 4),
    delta DECIMAL(10, 4),
    gamma DECIMAL(10, 4),
    theta DECIMAL(10, 4),
    vega DECIMAL(10, 4),
    rho DECIMAL(10, 4),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_option_bar UNIQUE (timestamp, symbol, strike, option_type, expiry),
    CONSTRAINT strike_range CHECK (strike BETWEEN 0.01 AND 1000000)
);

CREATE INDEX idx_timestamp_symbol_strike ON option_bars(timestamp DESC, symbol, strike);
CREATE INDEX idx_expiry_symbol ON option_bars(expiry, symbol);
"""

def setup_schema():
    try:
        # Connect to postgres (default DB)
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database="postgres",
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Creating database...")
        try:
            cur.execute("DROP DATABASE IF EXISTS nifty_sensex_options;")
        except:
            pass
        cur.execute("CREATE DATABASE nifty_sensex_options;")
        print("✓ Database created")
        cur.close()
        conn.close()
        
        # Connect to new database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        print("Creating table...")
        
        # Drop existing table if exists (optional)
        cur.execute("DROP TABLE IF EXISTS option_bars CASCADE;")
        
        # Create table
        cur.execute("""
            CREATE TABLE option_bars (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                strike DECIMAL(10, 2) NOT NULL,
                option_type VARCHAR(2) NOT NULL,
                expiry DATE NOT NULL,
                open DECIMAL(10, 4),
                high DECIMAL(10, 4),
                low DECIMAL(10, 4),
                close DECIMAL(10, 4) NOT NULL,
                volume BIGINT,
                open_interest BIGINT,
                iv DECIMAL(10, 4),
                delta DECIMAL(10, 4),
                gamma DECIMAL(10, 4),
                theta DECIMAL(10, 4),
                vega DECIMAL(10, 4),
                rho DECIMAL(10, 4),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_option_bar UNIQUE (timestamp, symbol, strike, option_type, expiry),
                CONSTRAINT strike_range CHECK (strike BETWEEN 0.01 AND 1000000)
            );
        """)
        print("✓ Table created")
        
        print("Creating indexes...")
        cur.execute("CREATE INDEX idx_timestamp_symbol_strike ON option_bars(timestamp DESC, symbol, strike);")
        cur.execute("CREATE INDEX idx_expiry_symbol ON option_bars(expiry, symbol);")
        print("✓ Indexes created")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("\n✓ SCHEMA SETUP COMPLETE")
        print(f"Database: {DB_NAME}")
        print(f"Table: option_bars (19 columns, 2 indexes)")
        print("Ready for nifty_bhavcopy_loader.py")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify PostgreSQL is running")
        print("2. Check DB_PASSWORD is correct")
        print("3. Check DB_HOST and DB_PORT")

if __name__ == "__main__":
    setup_schema()
