#!/usr/bin/env python3
"""
Standalone Kite Connect sample (not used by the main app).

Requires: pip install kiteconnect

Credentials (pick one):
  - Environment: KITE_API_KEY, KITE_ACCESS_TOKEN
  - File: --secrets path/to/secrets.toml with a [kite] table containing
    api_key and access_token

Get access_token: run ../kite_token_generator.py after login, or paste from Kite developer flow.

Examples:
  set KITE_API_KEY=xxx
  set KITE_ACCESS_TOKEN=yyy
  python reference/kite_connect_sample_fetch.py

  python reference/kite_connect_sample_fetch.py --secrets .streamlit/secrets.toml --interval day
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from kiteconnect import KiteConnect
    from kiteconnect.exceptions import KiteException
except ImportError:
    print("Install kiteconnect: pip install kiteconnect", file=sys.stderr)
    sys.exit(1)

try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore


def load_kite_credentials_from_toml(secrets_path: Path) -> dict:
    if not secrets_path.is_file():
        raise SystemExit(f"Secrets file not found: {secrets_path}")
    if tomllib is None:
        raise SystemExit("Python 3.11+ required for --secrets (tomllib).")
    data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
    kite = data.get("kite")
    if isinstance(kite, dict) and kite.get("api_key") and kite.get("access_token"):
        return kite
    # Minimal TOML without a [kite] header
    if data.get("api_key") and data.get("access_token"):
        return {"api_key": data["api_key"], "access_token": data["access_token"]}
    raise SystemExit(
        f"No Kite credentials in {secrets_path}: add [kite] with api_key and access_token, "
        "or top-level api_key and access_token."
    )


def resolve_credentials(secrets: Path | None) -> tuple[str, str]:
    api_key = os.environ.get("KITE_API_KEY", "").strip()
    access_token = os.environ.get("KITE_ACCESS_TOKEN", "").strip()
    if secrets:
        table = load_kite_credentials_from_toml(secrets)
        api_key = str(table.get("api_key", api_key)).strip()
        access_token = str(table.get("access_token", access_token)).strip()
    if not api_key or not access_token:
        raise SystemExit(
            "Set KITE_API_KEY and KITE_ACCESS_TOKEN, or pass --secrets with [kite] api_key and access_token."
        )
    return api_key, access_token


def find_instrument_token(kite: KiteConnect, exchange: str, tradingsymbol: str) -> int:
    for row in kite.instruments(exchange):
        if row.get("tradingsymbol") == tradingsymbol:
            return int(row["instrument_token"])
    raise SystemExit(f"Instrument not found: {exchange}:{tradingsymbol}")


def main() -> None:
    p = argparse.ArgumentParser(description="Sample Kite Connect REST calls (profile, quote, historical).")
    p.add_argument(
        "--secrets",
        type=Path,
        default=None,
        help="Optional path to TOML with [kite] api_key and access_token",
    )
    p.add_argument("--exchange", default="NSE", help="Exchange for --symbol lookup")
    p.add_argument("--symbol", default="NIFTY 50", help="tradingsymbol for historical/quote sample")
    p.add_argument(
        "--days",
        type=int,
        default=5,
        help="Calendar-day lookback window from today for historical from/to",
    )
    p.add_argument(
        "--interval",
        default="day",
        choices=[
            "minute",
            "3minute",
            "5minute",
            "10minute",
            "15minute",
            "30minute",
            "60minute",
            "day",
        ],
        help="Historical candle interval",
    )
    p.add_argument(
        "--full",
        action="store_true",
        help="Print full candle list (default: cap at 20 rows for readability)",
    )
    args = p.parse_args()

    api_key, access_token = resolve_credentials(args.secrets)
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    out: dict = {}

    # 1) Profile
    out["profile"] = kite.profile()

    # 2) Quote snapshot (single instrument)
    ikey = f"{args.exchange}:{args.symbol}"
    out["quote_keys_requested"] = [ikey]
    try:
        out["quote"] = kite.quote([ikey])
    except Exception as e:
        out["quote"] = {"error": str(e)}

    # 3) Historical candles
    token = find_instrument_token(kite, args.exchange, args.symbol)
    to_d = date.today()
    from_d = to_d - timedelta(days=max(args.days, 1))
    candles = kite.historical_data(
        instrument_token=token,
        from_date=from_d,
        to_date=to_d,
        interval=args.interval,
        continuous=False,
        oi=False,
    )
    out["historical_meta"] = {
        "instrument_token": token,
        "exchange": args.exchange,
        "tradingsymbol": args.symbol,
        "from_date": from_d.isoformat(),
        "to_date": to_d.isoformat(),
        "interval": args.interval,
        "candle_count": len(candles),
    }
    if args.full:
        out["historical_candles"] = candles
    else:
        out["historical_candles_preview"] = candles[:20]
        if len(candles) > 20:
            out["historical_candles_omitted"] = len(candles) - 20

    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    try:
        main()
    except KiteException as e:
        print(json.dumps({"error": str(e), "type": e.__class__.__name__}, indent=2), file=sys.stderr)
        sys.exit(1)
