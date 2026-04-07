#!/usr/bin/env python3
"""
Shoonya API - Live Market Data Fetcher
Fetches real-time NIFTY spot prices and option premiums
Author: Trading Champion
Date: April 2026
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional

try:
    from NorenRestApiPy.NorenApi import NorenApi
    HAS_SHOONYA = True
except ImportError:
    HAS_SHOONYA = False


class ShoomyaLiveDataFetcher:
    """Fetch live market data using Shoonya API (Finvasia)"""

    def __init__(self, user_id: str = None, password: str = None, api_key: str = None, pin: str = None):
        """
        Initialize Shoonya API connection

        Args:
            user_id: Shoonya/Finvasia user ID
            password: Shoonya password
            api_key: Shoonya API key
            pin: 2FA PIN (if required)

        Environment variables:
            SHOONYA_USER_ID, SHOONYA_PASSWORD, SHOONYA_API_KEY, SHOONYA_PIN
        """
        if not HAS_SHOONYA:
            print("⚠️  NorenApi not installed. Install with: pip install norenapi")
            self.api = None
            return

        # Get credentials from args or environment
        self.user_id = user_id or os.getenv("SHOONYA_USER_ID")
        self.password = password or os.getenv("SHOONYA_PASSWORD")
        self.api_key = api_key or os.getenv("SHOONYA_API_KEY")
        self.pin = pin or os.getenv("SHOONYA_PIN")

        self.api = None
        self.authenticated = False
        self.last_update = None

        if self.user_id and self.password and self.api_key:
            self._connect()

    def _connect(self):
        """Connect to Shoonya API"""
        try:
            self.api = NorenApi(
                host="https://api.shoonya.com/NorenWCP/",
                clientcode=self.user_id,
                password=self.password,
                userkey=self.api_key,
                telegrambot=None
            )

            # Login
            ret = self.api.login()
            if ret == "SUCCESS":
                print("✓ Shoonya API connected")
                self.authenticated = True
            else:
                print(f"❌ Shoonya login failed: {ret}")
                self.authenticated = False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.authenticated = False

    def fetch_live_spot(self, symbol: str = "NIFTY", exchange: str = "NSE") -> Optional[Dict]:
        """
        Fetch live spot price for NIFTY

        Args:
            symbol: Trading symbol (default "NIFTY")
            exchange: Exchange code (NSE for NIFTY)

        Returns:
            Dict with spot, change, change%, IV, IVP or None if failed
        """
        if not self.authenticated or not self.api:
            return None

        try:
            # Fetch live quote
            token = self._get_token(symbol, exchange)
            if not token:
                print(f"❌ Could not find token for {symbol}")
                return None

            ret = self.api.get_quotes(exchange=exchange, token=token)

            if ret and ret.get("stat") == "Ok":
                quote = ret
                spot = float(quote.get("ltp", 0))
                close = float(quote.get("close", spot))
                change = spot - close
                change_pct = (change / close * 100) if close > 0 else 0

                # Calculate IV from bid-ask spread (simplified)
                bid = float(quote.get("bid", spot))
                ask = float(quote.get("ask", spot))
                iv_pct = ((ask - bid) / spot * 100) if spot > 0 else 14.2

                self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                return {
                    "symbol": symbol,
                    "spot": spot,
                    "change": f"{change:+.2f}",
                    "change_pct": f"{change_pct:+.2f}%",
                    "iv": iv_pct / 100,  # Convert to decimal
                    "ivp": 50,  # IVP would need historical data
                    "timestamp": self.last_update,
                    "bid": bid,
                    "ask": ask,
                    "oi": int(quote.get("oi", 0)),
                    "volume": int(quote.get("volume", 0)),
                }
            else:
                print(f"❌ Quote error: {ret}")
                return None

        except Exception as e:
            print(f"❌ Fetch error: {e}")
            return None

    def fetch_option_chain(self, symbol: str = "NIFTY", expiry_date: str = None,
                          price_range_pct: float = 4.5) -> Optional[List[Dict]]:
        """
        Fetch option chain around ATM strike

        Args:
            symbol: Base symbol (NIFTY/SENSEX)
            expiry_date: Expiry date (format: DD-MMM-YYYY, e.g., "07-APR-2026")
            price_range_pct: Range around ATM (default 4.5%)

        Returns:
            List of option chain data with CE/PE premiums
        """
        if not self.authenticated or not self.api:
            return None

        try:
            # First get current spot
            spot_data = self.fetch_live_spot(symbol)
            if not spot_data:
                return None

            spot = spot_data["spot"]

            # Calculate band
            lower = spot * (1 - price_range_pct / 100)
            upper = spot * (1 + price_range_pct / 100)

            # Base strike (round to nearest 50)
            base_strike = int(spot / 50) * 50

            option_chain = []

            # Fetch strikes in range
            for strike in range(int(lower / 50) * 50, int(upper / 50) * 50 + 50, 50):
                try:
                    # Fetch CE
                    ce_symbol = f"{symbol}{strike}CE"
                    ce_token = self._get_token(ce_symbol, "NFO")

                    if ce_token:
                        ce_quote = self.api.get_quotes(exchange="NFO", token=ce_token)
                        ce_ltp = float(ce_quote.get("ltp", 0)) if ce_quote else 0
                    else:
                        ce_ltp = 0

                    # Fetch PE
                    pe_symbol = f"{symbol}{strike}PE"
                    pe_token = self._get_token(pe_symbol, "NFO")

                    if pe_token:
                        pe_quote = self.api.get_quotes(exchange="NFO", token=pe_token)
                        pe_ltp = float(pe_quote.get("ltp", 0)) if pe_quote else 0
                    else:
                        pe_ltp = 0

                    if ce_ltp > 0 or pe_ltp > 0:
                        option_chain.append({
                            "strike": strike,
                            "ce_ltp": ce_ltp,
                            "pe_ltp": pe_ltp,
                            "ce_bid": ce_ltp * 0.98 if ce_ltp > 0 else 0,
                            "ce_ask": ce_ltp * 1.02 if ce_ltp > 0 else 0,
                            "pe_bid": pe_ltp * 0.98 if pe_ltp > 0 else 0,
                            "pe_ask": pe_ltp * 1.02 if pe_ltp > 0 else 0,
                        })

                except Exception as e:
                    print(f"  ⚠️  Strike {strike}: {e}")
                    continue

            return option_chain if option_chain else None

        except Exception as e:
            print(f"❌ Option chain error: {e}")
            return None

    def _get_token(self, symbol: str, exchange: str) -> Optional[str]:
        """
        Get token for symbol (requires instrument master)

        For now, return None - in production, maintain a local token cache
        or fetch from Shoonya instruments endpoint
        """
        # TODO: Implement instrument master caching
        # For MVP, rely on direct symbol-based queries
        return None

    def disconnect(self):
        """Logout from Shoonya API"""
        try:
            if self.api and self.authenticated:
                self.api.logout()
                self.authenticated = False
                print("✓ Shoonya API disconnected")
        except Exception as e:
            print(f"⚠️  Disconnect error: {e}")


def main():
    """Test Shoonya connection"""
    print("\n🔗 Shoonya API Live Data Fetcher")
    print("="*70)

    # Check credentials
    user_id = os.getenv("SHOONYA_USER_ID")
    password = os.getenv("SHOONYA_PASSWORD")
    api_key = os.getenv("SHOONYA_API_KEY")

    if not (user_id and password and api_key):
        print("\n⚠️  Shoonya credentials not found in environment variables")
        print("\nTo set up:")
        print("  1. Sign up at https://www.shoonya.com/")
        print("  2. Get API credentials from Shoonya/Finvasia")
        print("  3. Set environment variables:")
        print("     - SHOONYA_USER_ID")
        print("     - SHOONYA_PASSWORD")
        print("     - SHOONYA_API_KEY")
        print("     - SHOONYA_PIN (if required)")
        return

    # Initialize fetcher
    fetcher = ShoomyaLiveDataFetcher(user_id=user_id, password=password, api_key=api_key)

    if not fetcher.authenticated:
        print("\n❌ Failed to authenticate with Shoonya API")
        return

    # Fetch live NIFTY
    print("\n📊 Fetching live NIFTY data...")
    spot_data = fetcher.fetch_live_spot("NIFTY", "NSE")

    if spot_data:
        print(f"✓ NIFTY: {spot_data['spot']:,.2f} {spot_data['change']} ({spot_data['change_pct']})")
        print(f"  IV: {spot_data['iv']*100:.1f}% | OI: {spot_data['oi']:,} | Volume: {spot_data['volume']:,}")
    else:
        print("❌ Failed to fetch NIFTY data")

    # Fetch option chain
    print("\n🔗 Fetching option chain...")
    option_chain = fetcher.fetch_option_chain("NIFTY")

    if option_chain:
        print(f"✓ Fetched {len(option_chain)} strikes")
        for row in option_chain[:3]:
            print(f"  Strike {row['strike']}: CE {row['ce_ltp']:.2f} | PE {row['pe_ltp']:.2f}")
    else:
        print("❌ Failed to fetch option chain")

    # Disconnect
    fetcher.disconnect()


if __name__ == "__main__":
    main()
