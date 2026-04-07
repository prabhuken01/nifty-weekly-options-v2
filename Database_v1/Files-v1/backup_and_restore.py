#!/usr/bin/env python3
"""
One-click Backup & Restore to AWS RDS
"""

import subprocess
import os
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_local_database():
    """Backup local PostgreSQL database"""
    logger.info("="*80)
    logger.info("STEP 1: BACKUP LOCAL DATABASE")
    logger.info("="*80)

    backup_file = "nifty_kaggle_backup.sql"

    logger.info(f"\n[BACKUP] Creating {backup_file}...")

    try:
        result = subprocess.run([
            "pg_dump",
            "-h", "localhost",
            "-U", "postgres",
            "-d", "nifty_sensex_options"
        ], capture_output=True, text=True, check=True)

        with open(backup_file, 'w') as f:
            f.write(result.stdout)

        size_mb = Path(backup_file).stat().st_size / (1024**2)
        logger.info(f"[OK] Backup created: {backup_file} ({size_mb:.2f} MB)")
        return True

    except FileNotFoundError:
        logger.error("[ERROR] pg_dump not found - PostgreSQL tools not in PATH")
        logger.error("[ACTION] Install PostgreSQL and add to PATH, or:")
        logger.error("        Use full path: 'C:\\Program Files\\PostgreSQL\\15\\bin\\pg_dump'")
        return False
    except Exception as e:
        logger.error(f"[ERROR] Backup failed: {e}")
        return False

def restore_to_aws(endpoint, password):
    """Restore to AWS RDS"""
    logger.info("\n" + "="*80)
    logger.info("STEP 2: RESTORE TO AWS RDS")
    logger.info("="*80)

    backup_file = "nifty_kaggle_backup.sql"

    if not Path(backup_file).exists():
        logger.error(f"[ERROR] {backup_file} not found")
        logger.error("[ACTION] Run backup_local_database() first")
        return False

    logger.info(f"\n[RESTORE] Restoring to AWS RDS...")
    logger.info(f"  Endpoint: {endpoint}")
    logger.info(f"  Database: nifty_sensex_options")

    try:
        with open(backup_file, 'r') as f:
            backup_data = f.read()

        result = subprocess.run([
            "psql",
            "-h", endpoint,
            "-U", "postgres",
            "-d", "nifty_sensex_options"
        ], input=backup_data, text=True, capture_output=True, check=True,
           env={**os.environ, 'PGPASSWORD': password})

        logger.info("[OK] Restoration started")
        logger.info("[INFO] This may take 1-2 minutes...")

        if result.stderr:
            logger.info(f"[RESULT] {result.stderr}")

        return True

    except FileNotFoundError:
        logger.error("[ERROR] psql not found - PostgreSQL tools not in PATH")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"[ERROR] Restore failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"[ERROR] {e}")
        return False

def verify_aws_connection(endpoint, password):
    """Verify cloud database connection"""
    logger.info("\n" + "="*80)
    logger.info("STEP 3: VERIFY CLOUD CONNECTION")
    logger.info("="*80)

    try:
        import psycopg2

        logger.info(f"\n[CONNECT] Connecting to AWS RDS...")

        conn = psycopg2.connect(
            host=endpoint,
            port=5432,
            database="nifty_sensex_options",
            user="postgres",
            password=password
        )

        cur = conn.cursor()

        # Get stats
        cur.execute("SELECT COUNT(*) FROM option_bars_daily")
        count = cur.fetchone()[0]

        cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM option_bars_daily")
        min_ts, max_ts = cur.fetchone()

        cur.execute("SELECT AVG(iv) FROM option_bars_daily WHERE iv IS NOT NULL")
        avg_iv = cur.fetchone()[0]

        cur.close()
        conn.close()

        logger.info("\n" + "="*80)
        logger.info("SUCCESS! Cloud Database Ready!")
        logger.info("="*80)
        logger.info(f"Records: {count:,}")
        logger.info(f"Date range: {min_ts.date()} to {max_ts.date()}")
        logger.info(f"Greeks: IV avg = {avg_iv:.2f}%")
        logger.info("="*80)
        logger.info("\nYour database is now accessible from ANYWHERE!")
        logger.info(f"Connect: postgres://postgres@{endpoint}:5432/nifty_sensex_options")

        return True

    except ImportError:
        logger.error("[ERROR] psycopg2 not installed")
        logger.error("[ACTION] Run: pip install psycopg2-binary")
        return False
    except Exception as e:
        logger.error(f"[ERROR] Connection failed: {e}")
        logger.error("[ACTION] Check AWS RDS instance status, endpoint, and password")
        return False

def main():
    """Main workflow"""
    logger.info("\n")
    logger.info("#" * 80)
    logger.info("# BACKUP & RESTORE NIFTY DATABASE TO AWS RDS")
    logger.info("#" * 80)

    # Get AWS details
    endpoint = input("\nEnter AWS RDS endpoint (e.g., nifty-options-db.xxxxx.rds.amazonaws.com): ").strip()
    password = input("Enter AWS RDS password: ").strip()

    if not endpoint or not password:
        logger.error("[ERROR] Endpoint and password required")
        return False

    # Step 1: Backup
    if not backup_local_database():
        return False

    # Step 2: Restore
    input("\n[WAIT] Press ENTER once AWS RDS instance is AVAILABLE (green status)...")
    if not restore_to_aws(endpoint, password):
        return False

    # Step 3: Verify
    input("\n[WAIT] Press ENTER after restore completes (usually 1-2 minutes)...")
    if not verify_aws_connection(endpoint, password):
        return False

    logger.info("\n[DONE] All steps completed successfully!")
    logger.info("[NEXT] Update your connection strings to use the AWS endpoint")

if __name__ == "__main__":
    main()
