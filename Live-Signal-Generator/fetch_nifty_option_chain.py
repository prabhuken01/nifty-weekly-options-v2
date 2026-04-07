#!/usr/bin/env python3
"""
NIFTY Option Chain Fetcher
Fetches option chain data within ±4.5% of yesterday's closing price
Author: Data Analyst
Date: April 2026
"""

import json
import csv
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple
import sys

# Try to import nsepython - if not available, show installation instructions
try:
    from nsepython import (
        nse_get_data,
        nse_optionchain,
        nse_optionchain_expirydict
    )
    HAS_NSEPYTHON = True
except ImportError:
    HAS_NSEPYTHON = False
    print("⚠️  nsepython not found. Install with:")
    print("   pip install nsepython --break-system-packages")
    print("\nContinuing with mock data for demonstration...")


class NIFTYOptionChainFetcher:
    """Fetch and filter NIFTY option chain data based on price bands"""
    
    def __init__(self, spot_price: float = None):
        """
        Initialize fetcher
        
        Args:
            spot_price: Optional manual spot price. If None, fetches from NSE
        """
        self.spot_price = spot_price
        self.yesterday_close = None
        self.upper_band = None
        self.lower_band = None
        self.option_chain_data = []
        self.filtered_data = []
        self.expiry_date = None
        
    def fetch_yesterday_close(self) -> float:
        """Fetch NIFTY's yesterday closing price from NSE"""
        if HAS_NSEPYTHON:
            try:
                data = nse_get_data("NIFTY")
                # NSE data contains 'prev_close' or 'close'
                self.yesterday_close = data.get('prev_close') or data.get('close')
                return self.yesterday_close
            except Exception as e:
                print(f"❌ Error fetching from NSE: {e}")
                return None
        else:
            # Mock data for testing
            print("ℹ️  Using mock data (nsepython not installed)")
            self.yesterday_close = 22713.10  # As of April 2, 2026
            return self.yesterday_close
    
    def calculate_bands(self, price_range_percent: float = 4.5) -> Tuple[float, float]:
        """
        Calculate upper and lower price bands
        
        Args:
            price_range_percent: Percentage range (default 4.5%)
            
        Returns:
            Tuple of (lower_band, upper_band)
        """
        if not self.yesterday_close:
            raise ValueError("Spot price not set. Call fetch_yesterday_close() first.")
        
        multiplier = price_range_percent / 100
        self.lower_band = self.yesterday_close * (1 - multiplier)
        self.upper_band = self.yesterday_close * (1 + multiplier)
        
        return self.lower_band, self.upper_band
    
    def fetch_option_chain(self) -> List[Dict]:
        """Fetch option chain from NSE"""
        if HAS_NSEPYTHON:
            try:
                # Get available expiries
                expiry_dates = nse_optionchain_expirydict("NIFTY")
                if not expiry_dates:
                    print("❌ No expiry dates available")
                    return []
                
                # Use first (nearest) weekly expiry
                self.expiry_date = expiry_dates[0]
                print(f"📅 Using expiry: {self.expiry_date}")
                
                # Fetch option chain
                self.option_chain_data = nse_optionchain(symbol="NIFTY", expiry_date=self.expiry_date)
                print(f"✓ Fetched {len(self.option_chain_data)} strikes from NSE")
                
                return self.option_chain_data
            except Exception as e:
                print(f"❌ Error fetching option chain: {e}")
                return []
        else:
            print("ℹ️  Using mock option chain data")
            # Return sample strikes
            self.option_chain_data = self._get_mock_option_chain()
            return self.option_chain_data
    
    def _get_mock_option_chain(self) -> List[Dict]:
        """Generate mock option chain data for testing"""
        # Generate strikes around spot price (every 50 points)
        base_strike = int(self.yesterday_close / 50) * 50
        
        strikes = []
        for i in range(base_strike - 500, base_strike + 600, 50):
            # Mock CE data
            ce_ltp = max(0.05, self.yesterday_close - i) if i < self.yesterday_close else 0.05
            # Mock PE data  
            pe_ltp = max(0.05, i - self.yesterday_close) if i > self.yesterday_close else 0.05
            
            strike_data = {
                'strikePrice': i,
                'expiryDate': self.expiry_date or '09-Apr-2026',
                'CE': {
                    'strikePrice': i,
                    'lastPrice': ce_ltp,
                    'bidprice': ce_ltp - 0.05,
                    'askPrice': ce_ltp + 0.05,
                    'openInterest': 125000 + (abs(i - self.yesterday_close) * 100),
                    'totalTradedVolume': 25000 + (abs(i - self.yesterday_close) * 50),
                    'impliedVolatility': 15.5 + (abs(i - self.yesterday_close) / 1000),
                },
                'PE': {
                    'strikePrice': i,
                    'lastPrice': pe_ltp,
                    'bidprice': pe_ltp - 0.05,
                    'askPrice': pe_ltp + 0.05,
                    'openInterest': 125000 + (abs(i - self.yesterday_close) * 100),
                    'totalTradedVolume': 25000 + (abs(i - self.yesterday_close) * 50),
                    'impliedVolatility': 15.5 + (abs(i - self.yesterday_close) / 1000),
                }
            }
            strikes.append(strike_data)
        
        return strikes
    
    def filter_by_band(self) -> List[Dict]:
        """Filter strikes within the price band"""
        if not self.option_chain_data:
            print("❌ No option chain data available. Call fetch_option_chain() first.")
            return []
        
        self.filtered_data = []
        
        for strike_data in self.option_chain_data:
            strike_price = strike_data['strikePrice']
            
            # Check if within band
            if self.lower_band <= strike_price <= self.upper_band:
                filtered_record = {
                    'strike': strike_price,
                    'call_ltp': strike_data['CE'].get('lastPrice', 0),
                    'call_oi': strike_data['CE'].get('openInterest', 0),
                    'call_volume': strike_data['CE'].get('totalTradedVolume', 0),
                    'call_iv': strike_data['CE'].get('impliedVolatility', 'N/A'),
                    'call_bid': strike_data['CE'].get('bidprice', 0),
                    'call_ask': strike_data['CE'].get('askPrice', 0),
                    'put_ltp': strike_data['PE'].get('lastPrice', 0),
                    'put_oi': strike_data['PE'].get('openInterest', 0),
                    'put_volume': strike_data['PE'].get('totalTradedVolume', 0),
                    'put_iv': strike_data['PE'].get('impliedVolatility', 'N/A'),
                    'put_bid': strike_data['PE'].get('bidprice', 0),
                    'put_ask': strike_data['PE'].get('askPrice', 0),
                }
                self.filtered_data.append(filtered_record)
        
        print(f"✓ Filtered {len(self.filtered_data)} strikes within band")
        return self.filtered_data
    
    def export_csv(self, filename: str = None) -> str:
        """Export filtered data to CSV"""
        if not self.filtered_data:
            print("❌ No data to export. Call filter_by_band() first.")
            return None
        
        if filename is None:
            filename = f"nifty_option_chain_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with open(filename, 'w', newline='') as f:
                fieldnames = [
                    'strike', 'call_ltp', 'call_bid', 'call_ask', 'call_oi',
                    'call_volume', 'call_iv', 'put_ltp', 'put_bid', 'put_ask',
                    'put_oi', 'put_volume', 'put_iv'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.filtered_data)
            
            print(f"✓ Data exported to {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error exporting CSV: {e}")
            return None
    
    def export_json(self, filename: str = None) -> str:
        """Export filtered data to JSON"""
        if not self.filtered_data:
            print("❌ No data to export. Call filter_by_band() first.")
            return None
        
        if filename is None:
            filename = f"nifty_option_chain_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            output = {
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'market_date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                    'spot_price': self.yesterday_close,
                    'upper_band': round(self.upper_band, 2),
                    'lower_band': round(self.lower_band, 2),
                    'band_percentage': 4.5,
                    'expiry_date': self.expiry_date,
                    'total_data_points': len(self.filtered_data),
                },
                'data': self.filtered_data
            }
            
            with open(filename, 'w') as f:
                json.dump(output, f, indent=2)
            
            print(f"✓ Data exported to {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error exporting JSON: {e}")
            return None
    
    def print_summary(self):
        """Print summary statistics"""
        print("\n" + "="*70)
        print("NIFTY OPTION CHAIN SUMMARY")
        print("="*70)
        print(f"Yesterday's Close: {self.yesterday_close:,.2f}")
        print(f"Upper Band (spot + 4.5%): {self.upper_band:,.2f}")
        print(f"Lower Band (spot - 4.5%): {self.lower_band:,.2f}")
        print(f"Expiry Date: {self.expiry_date}")
        print(f"Total Strikes in Band: {len(self.filtered_data)}")
        print("="*70)
    
    def print_data_table(self, num_rows: int = None):
        """Print data in table format"""
        if not self.filtered_data:
            print("❌ No data to display")
            return
        
        data_to_print = self.filtered_data[:num_rows] if num_rows else self.filtered_data
        
        print("\n" + "="*140)
        print("STRIKE | CALL_LTP | CALL_OI | CALL_VOL | PUT_LTP | PUT_OI | PUT_VOL | CALL_IV | PUT_IV")
        print("-"*140)
        
        for row in data_to_print:
            call_iv_str = str(row['call_iv'])[:6] if row['call_iv'] != 'N/A' else 'N/A'
            put_iv_str = str(row['put_iv'])[:6] if row['put_iv'] != 'N/A' else 'N/A'
            print(f"{row['strike']:>6.0f} | {row['call_ltp']:>8.2f} | {row['call_oi']:>7.0f} | "
                  f"{row['call_volume']:>8.0f} | {row['put_ltp']:>7.2f} | {row['put_oi']:>6.0f} | "
                  f"{row['put_volume']:>7.0f} | {call_iv_str:>6} | {put_iv_str:>6}")
        
        print("="*140 + "\n")


def main():
    """Main execution"""
    print("\n🔍 NIFTY Option Chain Fetcher")
    print("="*70)
    
    # Initialize fetcher
    fetcher = NIFTYOptionChainFetcher()
    
    # Step 1: Get yesterday's close
    print("\n📊 Step 1: Fetching yesterday's NIFTY closing price...")
    spot = fetcher.fetch_yesterday_close()
    
    if not spot:
        print("❌ Failed to fetch spot price")
        sys.exit(1)
    
    print(f"✓ NIFTY Close: {spot:,.2f}")
    
    # Step 2: Calculate bands
    print("\n📈 Step 2: Calculating price bands (±4.5%)...")
    lower, upper = fetcher.calculate_bands()
    print(f"✓ Band Range: {lower:,.2f} - {upper:,.2f}")
    
    # Step 3: Fetch option chain
    print("\n🔗 Step 3: Fetching option chain data...")
    fetcher.fetch_option_chain()
    
    # Step 4: Filter by band
    print("\n🎯 Step 4: Filtering strikes within band...")
    fetcher.filter_by_band()
    
    # Step 5: Print summary
    fetcher.print_summary()
    
    # Step 6: Display data
    print("\n📋 Step 6: Displaying filtered data (first 10 rows)...")
    fetcher.print_data_table(num_rows=10)
    
    # Step 7: Export data
    print("\n💾 Step 7: Exporting data...")
    csv_file = fetcher.export_csv()
    json_file = fetcher.export_json()
    
    if csv_file and json_file:
        print("\n✅ SUCCESS: Option chain data fetched and exported!")
        print(f"   CSV: {csv_file}")
        print(f"   JSON: {json_file}")
        print(f"   Data Points: {len(fetcher.filtered_data)}")
    else:
        print("\n⚠️  Export completed with warnings")


if __name__ == "__main__":
    main()
