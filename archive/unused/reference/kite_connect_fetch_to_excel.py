#!/usr/bin/env python3
"""
Export Kite Connect sample data (profile, quote, historical) to an .xlsx file.

Auth (in order):
  1) KITE_API_KEY + KITE_ACCESS_TOKEN — ready to call APIs
  2) KITE_API_KEY + KITE_API_SECRET + KITE_REQUEST_TOKEN — exchanges token then calls APIs

The API secret alone cannot fetch data; you need a session access_token.

Do not commit the output workbook if it contains personal account fields.

Usage:
  set KITE_API_KEY=...
  set KITE_ACCESS_TOKEN=...
  python reference/kite_connect_fetch_to_excel.py --output reference/kite_connect_api_output.xlsx

  set KITE_API_KEY=...
  set KITE_API_SECRET=...
  set KITE_REQUEST_TOKEN=...   # from redirect URL after login; valid only minutes
  python reference/kite_connect_fetch_to_excel.py
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

try:
    from kiteconnect import KiteConnect
    from kiteconnect.exceptions import KiteException
except ImportError:
    print("pip install kiteconnect pandas openpyxl", file=sys.stderr)
    sys.exit(1)

try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore


def load_kite_credentials_from_toml(secrets_path: Path) -> dict:
    if tomllib is None:
        raise RuntimeError("Python 3.11+ required for --secrets (tomllib).")
    data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
    kite = data.get("kite")
    if isinstance(kite, dict) and kite.get("api_key") and kite.get("access_token"):
        return kite
    if data.get("api_key") and data.get("access_token"):
        return {"api_key": data["api_key"], "access_token": data["access_token"]}
    raise RuntimeError(
        "secrets.toml: add [kite] with api_key and access_token, or top-level api_key and access_token."
    )


def resolve_session(secrets: Path | None) -> tuple[KiteConnect, str]:
    """Return (kite, access_token). access_token may be newly generated."""
    api_key = os.environ.get("KITE_API_KEY", "").strip()
    access_token = os.environ.get("KITE_ACCESS_TOKEN", "").strip()
    api_secret = os.environ.get("KITE_API_SECRET", "").strip()
    request_token = os.environ.get("KITE_REQUEST_TOKEN", "").strip()

    if secrets:
        table = load_kite_credentials_from_toml(secrets)
        api_key = str(table.get("api_key", api_key)).strip()
        access_token = str(table.get("access_token", access_token)).strip()

    if not api_key:
        raise RuntimeError("Set KITE_API_KEY or use --secrets with api_key.")

    kite = KiteConnect(api_key=api_key)

    if access_token:
        kite.set_access_token(access_token)
        return kite, access_token

    if request_token and api_secret:
        sess = kite.generate_session(request_token=request_token, api_secret=api_secret)
        access_token = sess["access_token"]
        kite.set_access_token(access_token)
        return kite, access_token

    raise RuntimeError(
        "Missing session: set KITE_ACCESS_TOKEN, or set KITE_REQUEST_TOKEN + KITE_API_SECRET "
        "(request_token comes from the login redirect URL; it expires in minutes)."
    )


def find_instrument_token(kite: KiteConnect, exchange: str, tradingsymbol: str) -> int:
    for row in kite.instruments(exchange):
        if row.get("tradingsymbol") == tradingsymbol:
            return int(row["instrument_token"])
    raise RuntimeError(f"Instrument not found: {exchange}:{tradingsymbol}")


def write_auth_only_excel(path: Path, message: str, detail: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        pd.DataFrame({"field": ["status", "detail"], "value": [message, detail]}).to_excel(
            w, sheet_name="Auth", index=False
        )
        pd.DataFrame(
            {
                "step": [
                    "1. Open login URL (replace API_KEY):",
                    "2. After login, copy request_token from redirect URL",
                    "3. Set env: KITE_REQUEST_TOKEN, KITE_API_SECRET, KITE_API_KEY",
                    "4. Re-run this script (or set KITE_ACCESS_TOKEN from kite_token_generator.py)",
                ],
                "value": [
                    "https://kite.zerodha.com/connect/login?v=3&api_key=YOUR_API_KEY",
                    "?request_token=...&status=success",
                    "",
                    "",
                ],
            }
        ).to_excel(w, sheet_name="How_to_authenticate", index=False)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch Kite sample data and save to Excel.")
    p.add_argument(
        "--output",
        type=Path,
        default=Path("reference/kite_connect_api_output.xlsx"),
        help="Output .xlsx path",
    )
    p.add_argument("--secrets", type=Path, default=None, help="TOML with [kite] credentials")
    p.add_argument("--exchange", default="NSE")
    p.add_argument("--symbol", default="NIFTY 50")
    p.add_argument("--days", type=int, default=5)
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
    )
    return p.parse_args()


def run(args: argparse.Namespace) -> Path:
    out_path = args.output

    used_request_token = bool(os.environ.get("KITE_REQUEST_TOKEN", "").strip())

    try:
        kite, access_token = resolve_session(args.secrets)
    except RuntimeError as e:
        write_auth_only_excel(out_path, "AUTH_REQUIRED", str(e))
        print(f"Wrote {out_path} (auth instructions only): {e}", file=sys.stderr)
        raise SystemExit(2)

    if used_request_token:
        print(
            "Session OK. Save as KITE_ACCESS_TOKEN for later today (do not commit to git):",
            file=sys.stderr,
        )
        print(access_token, file=sys.stderr)

    profile = kite.profile()
    ikey = f"{args.exchange}:{args.symbol}"
    try:
        quote = kite.quote([ikey])
    except Exception as ex:
        quote = {"error": str(ex)}

    token = find_instrument_token(kite, args.exchange, args.symbol)
    to_d = date.today()
    from_d = to_d - timedelta(days=max(args.days, 1))

    hist_error: str | None = None
    try:
        candles = kite.historical_data(
            instrument_token=token,
            from_date=from_d,
            to_date=to_d,
            interval=args.interval,
            continuous=False,
            oi=False,
        )
    except KiteException as e:
        hist_error = f"{e.__class__.__name__}: {e}"
        candles = []

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prof_df = pd.json_normalize(profile)
    quote_df = pd.json_normalize(quote)
    if candles:
        hist_df = pd.DataFrame(candles)
    else:
        hist_df = pd.DataFrame(
            [
                {
                    "note": hist_error or "No historical rows",
                    "hint": (
                        "PermissionException usually means the Historical Data API add-on is not active "
                        "for this app. Subscribe under developers.kite.trade → your app → Historical data."
                    ),
                }
            ]
        )

    meta_rows = [
        ("exchange", args.exchange),
        ("tradingsymbol", args.symbol),
        ("instrument_token", token),
        ("from_date", from_d.isoformat()),
        ("to_date", to_d.isoformat()),
        ("interval", args.interval),
        ("candle_rows", len(candles)),
        ("historical_error", hist_error or ""),
        ("api_key_suffix", os.environ.get("KITE_API_KEY", "")[-4:] if os.environ.get("KITE_API_KEY") else ""),
    ]
    meta_df = pd.DataFrame(meta_rows, columns=["key", "value"])

    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        meta_df.to_excel(w, sheet_name="Run_meta", index=False)
        prof_df.to_excel(w, sheet_name="Profile", index=False)
        quote_df.to_excel(w, sheet_name="Quote", index=False)
        hist_df.to_excel(w, sheet_name="Historical", index=False)

    return out_path


if __name__ == "__main__":
    _args = parse_args()
    try:
        _path = run(_args)
        print(str(_path.resolve()))
    except SystemExit:
        raise
    except KiteException as e:
        write_auth_only_excel(_args.output, e.__class__.__name__, str(e))
        print(f"Wrote {_args.output}: API error — {e}", file=sys.stderr)
        sys.exit(1)
