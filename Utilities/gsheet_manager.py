"""
Google Sheets Manager - Helper class for managing premium history cache
Simplifies reading/writing to Google Sheets for Phase 2 historical data caching
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleSheetManager:
    """
    Manages Google Sheets for storing historical option premium data.

    Usage:
        manager = GoogleSheetManager(
            credentials_path='credentials.json',
            sheet_id='YOUR_SHEET_ID'
        )

        # Add premium data
        manager.append_premium_data(
            'NIFTY_Premium_History',
            date='2026-04-04',
            time='15:30:00',
            strike=23250,
            expiry='2026-04-07',
            iv=14.2,
            ivp=42,
            ce_premium=284.65,
            pe_premium=201.20
        )

        # Query data
        stats = manager.get_statistics('NIFTY_Premium_History', strike=23250)
    """

    def __init__(self, credentials_path='credentials.json', sheet_id=None):
        """
        Initialize Google Sheets manager.

        Args:
            credentials_path: Path to service account JSON credentials
            sheet_id: Google Sheets ID (from URL)
        """
        self.SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        try:
            self.creds = Credentials.from_service_account_file(
                credentials_path, scopes=self.SCOPES
            )
            self.client = gspread.authorize(self.creds)
            logger.info("✓ Google Sheets authentication successful")
        except FileNotFoundError:
            logger.error(f"Credentials file not found: {credentials_path}")
            self.creds = None
            self.client = None
            return
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.creds = None
            self.client = None
            return

        self.sheet_id = sheet_id
        self.sheet = None

        if sheet_id:
            try:
                self.sheet = self.client.open_by_key(sheet_id)
                logger.info(f"✓ Connected to sheet: {self.sheet.title}")
            except Exception as e:
                logger.error(f"Failed to open sheet {sheet_id}: {e}")
                logger.info("  Troubleshoot:")
                logger.info("  1. Verify SHEET_ID is correct")
                logger.info("  2. Confirm sheet is shared with service account email")
                logger.info("  3. Check credentials.json is valid")

    def is_connected(self) -> bool:
        """Check if successfully connected to Google Sheets."""
        return self.sheet is not None

    def append_premium_data(self,
                          worksheet_name: str,
                          date: str,
                          time: str,
                          strike: int,
                          expiry: str,
                          iv: float,
                          ivp: int,
                          ce_premium: float,
                          pe_premium: float,
                          notes: str = '') -> bool:
        """
        Add a row of premium data to the sheet.

        Args:
            worksheet_name: Name of worksheet ('NIFTY_Premium_History' or 'SENSEX_Premium_History')
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM:SS format
            strike: Strike price (int)
            expiry: Expiry date in YYYY-MM-DD format
            iv: Implied volatility as decimal (e.g., 0.142 for 14.2%)
            ivp: IV percentile (0-100)
            ce_premium: Call option premium in rupees
            pe_premium: Put option premium in rupees
            notes: Optional notes about the entry

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.warning("Not connected to Google Sheets")
            return False

        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            row = [
                date,
                time,
                str(strike),
                expiry,
                str(round(iv, 3)) if isinstance(iv, float) else str(iv),
                str(ivp),
                str(round(ce_premium, 2)) if isinstance(ce_premium, float) else str(ce_premium),
                str(round(pe_premium, 2)) if isinstance(pe_premium, float) else str(pe_premium),
                notes
            ]
            worksheet.append_row(row)
            logger.info(f"✓ Added row to {worksheet_name}: {strike} {expiry}")
            return True
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet not found: {worksheet_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to append data: {e}")
            return False

    def append_premium_rows(self,
                          worksheet_name: str,
                          rows: List[Dict]) -> int:
        """
        Add multiple rows of premium data at once (more efficient).

        Args:
            worksheet_name: Name of worksheet
            rows: List of dicts with keys: date, time, strike, expiry, iv, ivp, ce_premium, pe_premium, notes

        Returns:
            Number of rows added
        """
        if not self.is_connected():
            logger.warning("Not connected to Google Sheets")
            return 0

        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            formatted_rows = []

            for row_dict in rows:
                formatted_row = [
                    row_dict.get('date', ''),
                    row_dict.get('time', ''),
                    str(row_dict.get('strike', '')),
                    row_dict.get('expiry', ''),
                    str(round(float(row_dict.get('iv', 0)), 3)),
                    str(row_dict.get('ivp', '')),
                    str(round(float(row_dict.get('ce_premium', 0)), 2)),
                    str(round(float(row_dict.get('pe_premium', 0)), 2)),
                    row_dict.get('notes', '')
                ]
                formatted_rows.append(formatted_row)

            worksheet.append_rows(formatted_rows)
            logger.info(f"✓ Added {len(formatted_rows)} rows to {worksheet_name}")
            return len(formatted_rows)
        except Exception as e:
            logger.error(f"Failed to append multiple rows: {e}")
            return 0

    def get_premiums_for_strike(self,
                               worksheet_name: str,
                               strike: int,
                               expiry: Optional[str] = None) -> List[Dict]:
        """
        Fetch all premium data for a specific strike.

        Args:
            worksheet_name: Name of worksheet
            strike: Strike price to search for
            expiry: Optional expiry date filter

        Returns:
            List of matching rows as dicts
        """
        if not self.is_connected():
            logger.warning("Not connected to Google Sheets")
            return []

        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            all_data = worksheet.get_all_records()

            matching = [
                row for row in all_data
                if row.get('Strike') == str(strike) and
                (expiry is None or row.get('Expiry') == str(expiry))
            ]
            return matching
        except Exception as e:
            logger.error(f"Failed to fetch premiums: {e}")
            return []

    def get_recent_premiums(self,
                           worksheet_name: str,
                           limit: int = 10) -> List[Dict]:
        """
        Get the last N rows of data.

        Args:
            worksheet_name: Name of worksheet
            limit: Number of rows to return

        Returns:
            List of last N rows as dicts
        """
        if not self.is_connected():
            logger.warning("Not connected to Google Sheets")
            return []

        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            all_data = worksheet.get_all_records()
            return all_data[-limit:] if all_data else []
        except Exception as e:
            logger.error(f"Failed to fetch recent data: {e}")
            return []

    def get_statistics(self,
                      worksheet_name: str,
                      strike: Optional[int] = None) -> Dict:
        """
        Calculate average premiums by strike.

        Args:
            worksheet_name: Name of worksheet
            strike: Optional specific strike to analyze

        Returns:
            Dict with structure:
            {
                'strike_price': {
                    'ce_mean': average_call_premium,
                    'pe_mean': average_put_premium,
                    'ce_samples': count,
                    'pe_samples': count,
                    'strangle_mean': average_strangle
                }
            }
        """
        if not self.is_connected():
            logger.warning("Not connected to Google Sheets")
            return {}

        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            all_data = worksheet.get_all_records()

            stats = {}
            for row in all_data:
                strike_key = row.get('Strike')

                if strike and strike_key != str(strike):
                    continue

                try:
                    ce = float(row.get('CE_Premium', 0)) if row.get('CE_Premium') else 0
                    pe = float(row.get('PE_Premium', 0)) if row.get('PE_Premium') else 0
                except ValueError:
                    continue

                if strike_key not in stats:
                    stats[strike_key] = {
                        'ce': [],
                        'pe': [],
                        'ce_mean': 0,
                        'pe_mean': 0,
                        'ce_samples': 0,
                        'pe_samples': 0,
                        'strangle_mean': 0
                    }

                if ce > 0:
                    stats[strike_key]['ce'].append(ce)
                if pe > 0:
                    stats[strike_key]['pe'].append(pe)

            # Calculate means
            for strike_key in stats:
                ce_data = stats[strike_key]['ce']
                pe_data = stats[strike_key]['pe']

                if ce_data:
                    stats[strike_key]['ce_mean'] = round(sum(ce_data) / len(ce_data), 2)
                    stats[strike_key]['ce_samples'] = len(ce_data)

                if pe_data:
                    stats[strike_key]['pe_mean'] = round(sum(pe_data) / len(pe_data), 2)
                    stats[strike_key]['pe_samples'] = len(pe_data)

                if ce_data and pe_data:
                    stats[strike_key]['strangle_mean'] = round(
                        stats[strike_key]['ce_mean'] + stats[strike_key]['pe_mean'], 2
                    )

                # Remove raw lists to keep output clean
                del stats[strike_key]['ce']
                del stats[strike_key]['pe']

            logger.info(f"✓ Calculated statistics for {len(stats)} strikes")
            return stats
        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            return {}

    def get_row_count(self, worksheet_name: str) -> int:
        """Get total number of data rows in worksheet."""
        if not self.is_connected():
            return 0

        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            return len(worksheet.get_all_records())
        except Exception as e:
            logger.error(f"Failed to get row count: {e}")
            return 0

    def clear_worksheet(self, worksheet_name: str) -> bool:
        """Clear all data from worksheet (keep headers in Row 1)."""
        if not self.is_connected():
            return False

        try:
            worksheet = self.sheet.worksheet(worksheet_name)
            # Get all rows
            all_rows = worksheet.get_all_values()

            if len(all_rows) > 1:
                # Delete all rows except header (Row 1)
                worksheet.delete_rows(2, len(all_rows))
                logger.info(f"✓ Cleared {worksheet_name} (kept headers)")
                return True
            return True
        except Exception as e:
            logger.error(f"Failed to clear worksheet: {e}")
            return False


# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLE USAGE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Initialize manager
    manager = GoogleSheetManager(
        credentials_path='credentials.json',
        sheet_id='YOUR_SHEET_ID_HERE'  # Replace with actual ID
    )

    # Check connection
    if not manager.is_connected():
        print("[ERROR] Failed to connect to Google Sheets")
        print("Make sure:")
        print("  1. credentials.json exists in current directory")
        print("  2. Sheet ID is correct")
        print("  3. Sheet is shared with service account email")
        exit(1)

    # Example 1: Add single row
    print("\n--- Example 1: Add Single Row ---")
    manager.append_premium_data(
        'NIFTY_Premium_History',
        date=datetime.now().strftime('%Y-%m-%d'),
        time=datetime.now().strftime('%H:%M:%S'),
        strike=23250,
        expiry='2026-04-07',
        iv=0.142,
        ivp=42,
        ce_premium=284.65,
        pe_premium=201.20,
        notes='Example entry'
    )

    # Example 2: Add multiple rows at once
    print("\n--- Example 2: Add Multiple Rows ---")
    sample_data = [
        {
            'date': '2026-04-03',
            'time': '15:30:00',
            'strike': 23250,
            'expiry': '2026-04-07',
            'iv': 0.140,
            'ivp': 38,
            'ce_premium': 280.00,
            'pe_premium': 198.00,
            'notes': 'Sample 1'
        },
        {
            'date': '2026-04-02',
            'time': '15:30:00',
            'strike': 23250,
            'expiry': '2026-04-07',
            'iv': 0.145,
            'ivp': 45,
            'ce_premium': 290.00,
            'pe_premium': 205.00,
            'notes': 'Sample 2'
        }
    ]
    count = manager.append_premium_rows('NIFTY_Premium_History', sample_data)
    print(f"Added {count} rows")

    # Example 3: Get statistics
    print("\n--- Example 3: Statistics ---")
    stats = manager.get_statistics('NIFTY_Premium_History', strike=23250)
    for strike, data in stats.items():
        print(f"Strike {strike}:")
        print(f"  Call avg: Rs {data['ce_mean']} (n={data['ce_samples']})")
        print(f"  Put avg: Rs {data['pe_mean']} (n={data['pe_samples']})")
        print(f"  Strangle avg: Rs {data['strangle_mean']}")

    # Example 4: Get recent data
    print("\n--- Example 4: Recent Data ---")
    recent = manager.get_recent_premiums('NIFTY_Premium_History', limit=5)
    for row in recent:
        print(f"{row['Date']} {row['Time']} - Strike {row['Strike']}: "
              f"CE={row['CE_Premium']}, PE={row['PE_Premium']}")

    # Example 5: Get specific strike data
    print("\n--- Example 5: Data for Specific Strike ---")
    strike_data = manager.get_premiums_for_strike('NIFTY_Premium_History', 23250)
    print(f"Found {len(strike_data)} entries for strike 23250")

    print("\n✓ All examples completed successfully!")
