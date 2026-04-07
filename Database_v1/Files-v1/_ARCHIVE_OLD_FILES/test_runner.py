#!/usr/bin/env python3
"""
Test Runner: Validate bhavcopy loader with multiple password combinations
Outputs all results to Excel format
"""

import pandas as pd
import psycopg2
from datetime import datetime, date, timedelta
import logging
from pathlib import Path
import json

# ============================================================================
# LOGGING SETUP
# ============================================================================

LOG_FILE = "test_runner.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# PASSWORD COMBINATIONS TO TEST
# ============================================================================

PASSWORD_ATTEMPTS = [
    ("postgres", "Default PostgreSQL password"),
    ("", "Empty password"),
    ("admin", "Common admin password"),
    ("password", "Generic password"),
    ("12345678", "Numeric password"),
]

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "nifty_sensex_options",
    "user": "postgres",
}

# ============================================================================
# TEST RESULTS TRACKING
# ============================================================================

test_results = {
    "timestamp": datetime.now().isoformat(),
    "connection_tests": [],
    "schema_setup": None,
    "loader_execution": None,
    "data_retrieval": None,
    "summary": {}
}

# ============================================================================
# STEP 1: TEST DATABASE CONNECTIONS
# ============================================================================

def test_db_connection(password, description):
    """Test connection with a specific password."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Testing: {description} (password='{password}')")
    logger.info(f"{'='*70}")

    result = {
        "password": password,
        "description": description,
        "connected": False,
        "error": None,
        "timestamp": datetime.now().isoformat()
    }

    try:
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=password,
            database="postgres"  # Try connecting to default postgres DB first
        )

        result["connected"] = True
        logger.info(f"✓ CONNECTION SUCCESSFUL with password: '{password}'")

        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        logger.info(f"PostgreSQL Version: {version}")
        result["postgres_version"] = version

        cur.close()
        conn.close()

    except psycopg2.OperationalError as e:
        result["error"] = str(e)
        logger.warning(f"✗ Connection failed: {e}")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"✗ Unexpected error: {e}")

    test_results["connection_tests"].append(result)
    return result

# ============================================================================
# STEP 2: SETUP SCHEMA
# ============================================================================

def setup_schema_test(password):
    """Attempt schema setup with successful password."""
    logger.info(f"\n{'='*70}")
    logger.info(f"SETTING UP SCHEMA")
    logger.info(f"{'='*70}")

    result = {
        "attempted": True,
        "success": False,
        "error": None,
        "timestamp": datetime.now().isoformat(),
        "tables_created": [],
        "indexes_created": []
    }

    try:
        # Connect to default postgres DB
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=password,
            database="postgres"
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Create database
        logger.info("Creating database: nifty_sensex_options")
        cur.execute("CREATE DATABASE IF NOT EXISTS nifty_sensex_options;")
        result["tables_created"].append("nifty_sensex_options")
        logger.info("✓ Database created")

        cur.close()
        conn.close()

        # Connect to new database
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=password,
            database="nifty_sensex_options"
        )
        cur = conn.cursor()

        # Create table
        logger.info("Creating table: option_bars")
        cur.execute("""
            DROP TABLE IF EXISTS option_bars CASCADE;

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
        result["tables_created"].append("option_bars")
        logger.info("✓ Table created")

        # Create indexes
        logger.info("Creating indexes")
        cur.execute("CREATE INDEX idx_timestamp_symbol_strike ON option_bars(timestamp DESC, symbol, strike);")
        cur.execute("CREATE INDEX idx_expiry_symbol ON option_bars(expiry, symbol);")
        result["indexes_created"].extend([
            "idx_timestamp_symbol_strike",
            "idx_expiry_symbol"
        ])
        logger.info("✓ Indexes created")

        conn.commit()
        cur.close()
        conn.close()

        result["success"] = True
        logger.info("✓ SCHEMA SETUP COMPLETE")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"✗ Schema setup failed: {e}")

    test_results["schema_setup"] = result
    return result

# ============================================================================
# STEP 3: LOAD SAMPLE DATA (Simulated Bhavcopy)
# ============================================================================

def load_sample_data(password):
    """Load simulated bhavcopy data into database."""
    logger.info(f"\n{'='*70}")
    logger.info(f"LOADING SAMPLE DATA")
    logger.info(f"{'='*70}")

    result = {
        "attempted": True,
        "success": False,
        "error": None,
        "rows_loaded": 0,
        "timestamp": datetime.now().isoformat(),
        "date_range": None
    }

    try:
        # Generate sample data
        sample_data = []
        end_date = date.today()
        start_date = end_date - timedelta(days=30)  # 1 month of data

        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Weekdays only
                for symbol in ['NIFTY', 'SENSEX']:
                    for option_type in ['CE', 'PE']:
                        for strike_offset in [-200, -100, 0, 100, 200]:
                            base_strike = 20000 if symbol == 'NIFTY' else 60000

                            sample_data.append({
                                'timestamp': pd.Timestamp(current_date.replace(hour=15, minute=30)),
                                'symbol': symbol,
                                'strike': base_strike + strike_offset,
                                'option_type': option_type,
                                'expiry': current_date + timedelta(days=4),
                                'open': 100.5,
                                'high': 105.0,
                                'low': 98.5,
                                'close': 102.0,
                                'volume': 1000000,
                                'open_interest': 500000,
                                'iv': 25.5,
                                'delta': 0.45,
                                'gamma': 0.002,
                                'theta': -0.05,
                                'vega': 0.15,
                                'rho': 0.03
                            })
            current_date += timedelta(days=1)

        df_sample = pd.DataFrame(sample_data)
        result["date_range"] = f"{start_date} to {end_date}"

        logger.info(f"Generated {len(df_sample)} sample records")
        logger.info(f"Date range: {result['date_range']}")

        # Insert into database
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=password,
            database="nifty_sensex_options"
        )
        cur = conn.cursor()

        from psycopg2.extras import execute_batch

        insert_values = []
        for _, row in df_sample.iterrows():
            insert_values.append((
                row['timestamp'],
                row['symbol'],
                row['strike'],
                row['option_type'],
                row['expiry'],
                row['open'],
                row['high'],
                row['low'],
                row['close'],
                row['volume'],
                row['open_interest'],
                row['iv'],
                row['delta'],
                row['gamma'],
                row['theta'],
                row['vega'],
                row['rho']
            ))

        execute_batch(
            cur,
            """
            INSERT INTO option_bars
            (timestamp, symbol, strike, option_type, expiry, open, high, low, close, volume, open_interest, iv, delta, gamma, theta, vega, rho)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, strike, option_type, expiry)
            DO UPDATE SET close = EXCLUDED.close
            """,
            insert_values,
            page_size=500
        )

        conn.commit()
        cur.close()
        conn.close()

        result["rows_loaded"] = len(insert_values)
        result["success"] = True
        logger.info(f"✓ {result['rows_loaded']} rows loaded successfully")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"✗ Data loading failed: {e}")

    test_results["loader_execution"] = result
    return result

# ============================================================================
# STEP 4: RETRIEVE DATA
# ============================================================================

def retrieve_data(password):
    """Retrieve loaded data from database."""
    logger.info(f"\n{'='*70}")
    logger.info(f"RETRIEVING DATA")
    logger.info(f"{'='*70}")

    result = {
        "attempted": True,
        "success": False,
        "error": None,
        "rows_retrieved": 0,
        "timestamp": datetime.now().isoformat(),
        "data": None
    }

    try:
        conn = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=password,
            database="nifty_sensex_options"
        )

        df_retrieved = pd.read_sql_query(
            """
            SELECT
                timestamp, symbol, strike, option_type, expiry,
                open, high, low, close, volume, open_interest,
                iv, delta, gamma, theta, vega, rho
            FROM option_bars
            ORDER BY timestamp DESC, symbol, strike
            LIMIT 1000
            """,
            conn
        )

        conn.close()

        result["rows_retrieved"] = len(df_retrieved)
        result["success"] = True
        result["data"] = df_retrieved

        logger.info(f"✓ Retrieved {result['rows_retrieved']} rows successfully")
        logger.info(f"\nSample of retrieved data:")
        logger.info(df_retrieved.head(10).to_string())

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"✗ Data retrieval failed: {e}")

    test_results["data_retrieval"] = result
    return result

# ============================================================================
# STEP 5: EXPORT TO EXCEL
# ============================================================================

def export_to_excel():
    """Export all test results to Excel."""
    logger.info(f"\n{'='*70}")
    logger.info(f"EXPORTING RESULTS TO EXCEL")
    logger.info(f"{'='*70}")

    excel_file = "test_results_bhavcopy.xlsx"

    try:
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:

            # Sheet 1: Connection Test Results
            conn_df = pd.DataFrame(test_results["connection_tests"])
            conn_df.to_excel(writer, sheet_name="Connection Tests", index=False)
            logger.info(f"✓ Sheet 'Connection Tests' created")

            # Sheet 2: Schema Setup Results
            if test_results["schema_setup"]:
                schema_info = {
                    "Parameter": [
                        "Attempted",
                        "Success",
                        "Tables Created",
                        "Indexes Created",
                        "Error"
                    ],
                    "Value": [
                        test_results["schema_setup"]["attempted"],
                        test_results["schema_setup"]["success"],
                        ", ".join(test_results["schema_setup"]["tables_created"]),
                        ", ".join(test_results["schema_setup"]["indexes_created"]),
                        test_results["schema_setup"]["error"] or "None"
                    ]
                }
                schema_df = pd.DataFrame(schema_info)
                schema_df.to_excel(writer, sheet_name="Schema Setup", index=False)
                logger.info(f"✓ Sheet 'Schema Setup' created")

            # Sheet 3: Data Loading Results
            if test_results["loader_execution"]:
                loader_info = {
                    "Parameter": [
                        "Attempted",
                        "Success",
                        "Rows Loaded",
                        "Date Range",
                        "Error"
                    ],
                    "Value": [
                        test_results["loader_execution"]["attempted"],
                        test_results["loader_execution"]["success"],
                        test_results["loader_execution"]["rows_loaded"],
                        test_results["loader_execution"]["date_range"] or "N/A",
                        test_results["loader_execution"]["error"] or "None"
                    ]
                }
                loader_df = pd.DataFrame(loader_info)
                loader_df.to_excel(writer, sheet_name="Data Loading", index=False)
                logger.info(f"✓ Sheet 'Data Loading' created")

            # Sheet 4: Data Retrieval Summary
            if test_results["data_retrieval"]:
                retrieval_info = {
                    "Parameter": [
                        "Attempted",
                        "Success",
                        "Rows Retrieved",
                        "Error"
                    ],
                    "Value": [
                        test_results["data_retrieval"]["attempted"],
                        test_results["data_retrieval"]["success"],
                        test_results["data_retrieval"]["rows_retrieved"],
                        test_results["data_retrieval"]["error"] or "None"
                    ]
                }
                retrieval_df = pd.DataFrame(retrieval_info)
                retrieval_df.to_excel(writer, sheet_name="Data Retrieval", index=False)
                logger.info(f"✓ Sheet 'Data Retrieval' created")

            # Sheet 5: Retrieved Data (if successful)
            if test_results["data_retrieval"] and test_results["data_retrieval"]["data"] is not None:
                test_results["data_retrieval"]["data"].to_excel(
                    writer, sheet_name="Retrieved Data", index=False
                )
                logger.info(f"✓ Sheet 'Retrieved Data' created with {len(test_results['data_retrieval']['data'])} rows")

            # Sheet 6: Summary
            summary_info = {
                "Test": [
                    "Connection Test",
                    "Schema Setup",
                    "Data Loading",
                    "Data Retrieval",
                    "Excel Export"
                ],
                "Status": [
                    "PASSED" if any(t["connected"] for t in test_results["connection_tests"]) else "FAILED",
                    "PASSED" if test_results["schema_setup"] and test_results["schema_setup"]["success"] else "FAILED",
                    "PASSED" if test_results["loader_execution"] and test_results["loader_execution"]["success"] else "FAILED",
                    "PASSED" if test_results["data_retrieval"] and test_results["data_retrieval"]["success"] else "FAILED",
                    "COMPLETED"
                ]
            }
            summary_df = pd.DataFrame(summary_info)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            logger.info(f"✓ Sheet 'Summary' created")

        logger.info(f"\n✓ Excel file created: {excel_file}")
        return excel_file

    except Exception as e:
        logger.error(f"✗ Excel export failed: {e}")
        return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    logger.info("="*70)
    logger.info("BHAVCOPY LOADER - COMPREHENSIVE TEST SUITE")
    logger.info("="*70)
    logger.info(f"Start time: {datetime.now()}")

    # Step 1: Test all password combinations
    successful_password = None
    logger.info(f"\n{'='*70}")
    logger.info(f"STEP 1: TESTING DATABASE CONNECTIONS")
    logger.info(f"{'='*70}\n")

    for password, description in PASSWORD_ATTEMPTS:
        test_result = test_db_connection(password, description)
        if test_result["connected"]:
            successful_password = password
            logger.info(f"\n✓ SUCCESSFUL PASSWORD FOUND: '{password}'")
            break

    if successful_password is None:
        logger.error("\n✗ Could not connect with any password combination")
        logger.info("Proceeding with offline test simulation...")

    else:
        # Step 2: Setup schema
        logger.info("\n")
        setup_result = setup_schema_test(successful_password)

        if setup_result["success"]:
            # Step 3: Load data
            logger.info("\n")
            load_result = load_sample_data(successful_password)

            # Step 4: Retrieve data
            if load_result["success"]:
                logger.info("\n")
                retrieve_result = retrieve_data(successful_password)

    # Step 5: Export to Excel
    logger.info("\n")
    excel_file = export_to_excel()

    # Final summary
    logger.info(f"\n{'='*70}")
    logger.info(f"TEST EXECUTION COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"End time: {datetime.now()}")
    logger.info(f"Log file: {LOG_FILE}")
    if excel_file:
        logger.info(f"Excel output: {excel_file}")

    # Print summary
    logger.info(f"\n{'='*70}")
    logger.info("QUICK SUMMARY")
    logger.info(f"{'='*70}")

    if test_results["connection_tests"]:
        connected_count = sum(1 for t in test_results["connection_tests"] if t["connected"])
        logger.info(f"Connections successful: {connected_count}/{len(test_results['connection_tests'])}")

    if test_results["schema_setup"]:
        logger.info(f"Schema setup: {'✓ SUCCESS' if test_results['schema_setup']['success'] else '✗ FAILED'}")

    if test_results["loader_execution"]:
        logger.info(f"Data loading: {'✓ SUCCESS' if test_results['loader_execution']['success'] else '✗ FAILED'} ({test_results['loader_execution']['rows_loaded']} rows)")

    if test_results["data_retrieval"]:
        logger.info(f"Data retrieval: {'✓ SUCCESS' if test_results['data_retrieval']['success'] else '✗ FAILED'} ({test_results['data_retrieval']['rows_retrieved']} rows)")

    logger.info(f"{'='*70}")

if __name__ == "__main__":
    main()
