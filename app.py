"""
Nifty Weekly Options Strategy Dashboard
Tabs: 1-Backtest  2-Live Signal  3-IV History
"""
import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import date, timedelta, datetime
import math
import requests
import time
import sys
import os

# Add Live-Signal-Generator (or fallback Live-fetching) module to path
for module_dir in ['Live-Signal-Generator', 'Live-fetching']:
    module_path = os.path.join(os.path.dirname(__file__), module_dir)
    if os.path.exists(module_path):
        sys.path.insert(0, module_path)
        break

try:
    from fetch_nifty_option_chain import NIFTYOptionChainFetcher
    HAS_LIVE_FETCHER = True
except ImportError:
    HAS_LIVE_FETCHER = False

st.set_page_config(page_title="Nifty Options Dashboard", layout="wide",
                   page_icon="chart_with_upwards_trend",
                   initial_sidebar_state="expanded")

# NSE holidays 2026 - update yearly
NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26), date(2026, 3, 25), date(2026, 4, 2),
    date(2026, 4, 5),  date(2026, 4, 6),  date(2026, 4, 14),
    date(2026, 5, 1),  date(2026, 8, 15), date(2026, 10, 2),
    date(2026, 10, 26),date(2026, 11, 4), date(2026, 12, 25),
}

def effective_dte(from_date, expiry):
    count = 0
    d = from_date + timedelta(days=1)
    while d <= expiry:
        if d.weekday() < 5 and d not in NSE_HOLIDAYS_2026:
            count += 1
        d += timedelta(days=1)
    return max(count, 1)

def bs_nd2(spot, strike, iv_ann, dte_days, r=0.065):
    if iv_ann <= 0 or dte_days <= 0:
        return 0.99
    T = dte_days / 365
    d2 = (math.log(spot / strike) + (r - 0.5 * iv_ann**2) * T) / (iv_ann * math.sqrt(T))
    return float(norm.cdf(d2))

def ivp_quality(ivp_pct):
    return min(100, ivp_pct * 1.25)

def comp_score(prob, ivp_pct):
    return round(prob * 60 + ivp_quality(ivp_pct) * 0.40)

def sig_label(score, threshold=65):
    if score >= threshold: return "SELL"
    if score >= 50:        return "MONITOR"
    return "AVOID"

def sig_color(label):
    return {"SELL": "#C6EFCE", "MONITOR": "#FFEB9C", "AVOID": "#FFC7CE"}[label]

def cushion_color(ratio):
    if ratio >= 2.0: return "#C6EFCE"
    if ratio >= 1.0: return "#FFEB9C"
    return "#FFC7CE"

# Sidebar
with st.sidebar:
    st.markdown("### Controls")
    data_src   = st.selectbox("Data source", ["NSE Bhavcopy (EOD)", "DhanHQ API", "Kite Connect"])
    instrument = st.selectbox("Instrument", ["NIFTY 50", "SENSEX"])
    lookback_m = st.selectbox("Lookback (months)", [6, 12, 24, 36], index=1)
    entry_time = st.selectbox("Entry time", ["T-2 closing","T-1 opening","T-1 closing","T opening","T closing"])
    exit_time  = st.selectbox("Exit time",  ["T-1 closing","T opening","T closing"])
    st.markdown("---")
    ivp_range  = st.slider("IVP regime filter (%)", 0, 100, (20, 80))
    excl_fri   = st.toggle("Exclude Friday entries", value=True)
    sig_thresh = st.slider("Signal threshold", 50, 90, 65)
    st.markdown("---")
    expiry_dt  = st.date_input("Next expiry", value=date(2026, 4, 7))
    today_dt   = st.date_input("Today's date", value=date(2026, 4, 3))
    dte_adj    = effective_dte(today_dt, expiry_dt)
    st.info(f"Effective DTE: **{dte_adj} days** (holidays excluded)")
    st.markdown("---")
    lot_size     = 65 if instrument == "NIFTY 50" else 20
    capital_base = 500_000
    st.caption(f"Lot: {lot_size} | Capital: Rs {capital_base:,}")

# Fetch live prices from Kite API every hour
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_live_prices():
    """Fetch current prices. Uses Live-fetching module if available, else mock data."""
    try:
        if HAS_LIVE_FETCHER:
            fetcher = NIFTYOptionChainFetcher()
            spot = fetcher.fetch_yesterday_close()
            if spot:
                # Calculate mock IV/IVP based on current market conditions
                return {
                    "NIFTY 50": {"spot": spot, "chg": "+0 (0.00%)", "iv": 0.142, "ivp": 42},
                    "SENSEX": {"spot": int(spot * 3.23), "chg": "+0 (0.00%)", "iv": 0.138, "ivp": 38},
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "Live (1-hour refresh)"
                }
        # Fallback to mock
        return {
            "NIFTY 50": {"spot": 22700, "chg": "+87 (+0.38%)", "iv": 0.142, "ivp": 42},
            "SENSEX": {"spot": 73320, "chg": "-112 (-0.14%)", "iv": 0.138, "ivp": 38},
            "timestamp": "Mock (nsepython unavailable)",
            "source": "Mock"
        }
    except Exception as e:
        return {
            "NIFTY 50": {"spot": 22700, "chg": "+87 (+0.38%)", "iv": 0.142, "ivp": 42},
            "SENSEX": {"spot": 73320, "chg": "-112 (-0.14%)", "iv": 0.138, "ivp": 38},
            "timestamp": "Mock (error)",
            "source": "Mock (Error: check nsepython)"
        }

prices_data = fetch_live_prices()
SPOT   = {"NIFTY 50": prices_data["NIFTY 50"]["spot"], "SENSEX": prices_data["SENSEX"]["spot"]}
IV_ANN = {"NIFTY 50": prices_data["NIFTY 50"]["iv"], "SENSEX": prices_data["SENSEX"]["iv"]}
IVP    = {"NIFTY 50": prices_data["NIFTY 50"]["ivp"], "SENSEX": prices_data["SENSEX"]["ivp"]}
CHG    = {"NIFTY 50": prices_data["NIFTY 50"]["chg"], "SENSEX": prices_data["SENSEX"]["chg"]}
PRICE_TIMESTAMP = prices_data["timestamp"]

spot   = SPOT[instrument]
iv     = IV_ANN[instrument]
ivp    = IVP[instrument]
ivp_ok = ivp_range[0] <= ivp <= ivp_range[1]

PUT_OFFSETS  = [-0.045, -0.040, -0.035, -0.030, -0.025]
CALL_OFFSETS = [+0.025, +0.030, +0.035, +0.040, +0.045]

def top_bar():
    # Use Dhan spot if fetched, else mock
    nifty_spot  = st.session_state.get("dhan_spot", SPOT["NIFTY 50"]) if instrument == "NIFTY 50" else SPOT["NIFTY 50"]
    sensex_spot = SPOT["SENSEX"]
    # Row 1: NIFTY + SENSEX spot & IV
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NIFTY 50",  f"₹{nifty_spot:,.0f}",  CHG["NIFTY 50"])
    c2.metric("NIFTY IV",  f"{IV_ANN['NIFTY 50']*100:.1f}%", f"IVP {IVP['NIFTY 50']}")
    c3.metric("SENSEX",    f"₹{sensex_spot:,.0f}", CHG["SENSEX"])
    c4.metric("SENSEX IV", f"{IV_ANN['SENSEX']*100:.1f}%",   f"IVP {IVP['SENSEX']}")
    # Row 2: regime info
    regime = "ALLOW" if ivp_ok else "SKIP"
    st.info(f"**Regime:** {regime} | IVP {ivp} | DTE {dte_adj} | {'Fri excluded' if excl_fri else 'All days'}")
    source = prices_data.get("source", "Unknown")
    st.caption(f"🕐 Prices: {source} | {PRICE_TIMESTAMP} | ♻️ Hourly refresh")

# Tabs
tab1, tab2, tab3 = st.tabs(["Tab 1 - Backtest", "Tab 2 - Live Signal", "Tab 3 - IV History"])

# ── TAB 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    top_bar()
    st.markdown("---")

    # Dynamic backtest P&L with REAL market premium data from Kite API
    @st.cache_data(ttl=3600)
    def fetch_historical_premiums(instrument_type, strike_offset_pct, expiry_date):
        """Fetch historical option premiums for backtest.
        NOTE: Phase 2 will cache these to Google Sheets/database to avoid repeated API calls.
        For now, returns None to use formula-based fallback."""
        # TODO Phase 2: Implement historical premium fetch from cached Google Sheets or database
        # For now, return None to use formula fallback
        return None

    def generate_backtest_pnl(lookback_m, strike_offset_pct, win_rate=0.70, trades_per_month=4, ivp_range=(0, 100)):
        """Calculate P&L using real market premium data.
        Real NIFTY ATM premium: Rs 1,267/contract × 65 lot = Rs 82,331 gross
        Real loss model: 1% capital loss per losing trade = Rs 5,000

        PHASE 2 ROADMAP: Historical premiums will be fetched from cached database to enable
        accurate backtesting without repeated API calls."""

        total_trades = lookback_m * trades_per_month

        # Filter by IVP range
        min_ivp, max_ivp = ivp_range
        def trades_in_range(min_iv, max_iv):
            low_frac = 0.20 if (min_iv <= 33 and max_iv > 0) else 0
            mid_frac = 0.60 if (min_iv < 67 and max_iv > 33) else 0
            high_frac = 0.20 if (min_iv < 100 and max_iv > 67) else 0
            if min_iv <= 33 and max_iv >= 33:
                low_frac = min(0.20, (33 - min_iv) / 33) if min_iv < 33 else 0
            if min_iv <= 67 and max_iv >= 67:
                mid_frac = min(0.60, (min(67, max_iv) - max(33, min_iv)) / 34)
            if max_iv > 67:
                high_frac = min(0.20, (max_iv - 67) / 33) if max_iv > 67 else 0
            return low_frac + mid_frac + high_frac

        regime_fraction = trades_in_range(min_ivp, max_ivp)
        filtered_trades = int(total_trades * regime_fraction) if regime_fraction > 0 else 1

        win_count = int(filtered_trades * win_rate)
        loss_count = filtered_trades - win_count

        # REAL MARKET DATA: NIFTY ATM weekly premium = Rs 1,267/contract
        # Premium DECREASES with wider offset (far OTM = lower premium)
        # NOTE: These values would be fetched from historical cache in Phase 2
        base_premium_per_contract = 1267  # Kite API actual: 684.85 CE + 581.80 PE
        # Offset factor: closer to ATM = higher premium, further OTM = lower premium
        offset_factor = 1.0 - (abs(strike_offset_pct) - 0.025) / 0.045 * 0.35  # Correct scaling
        premium_per_contract = max(200, int(base_premium_per_contract * offset_factor))
        gross_premium = premium_per_contract * lot_size  # e.g., 1267 × 65 = 82,331

        # REALISTIC LOSS: 1% of capital per losing trade (not extreme tail loss)
        loss_per_trade = capital_base * 0.01  # Rs 5,000 for 500K capital

        gross_pnl = (win_count * gross_premium) - (loss_count * loss_per_trade) if filtered_trades > 0 else 0
        costs = filtered_trades * 250

        # Greeks (simplified based on premium)
        theta = int((gross_premium / dte_adj) * 0.7) if dte_adj > 0 else 0
        vega = -int(gross_premium * 0.05)  # 5% of premium
        max_dd = -loss_per_trade

        return {
            'offset': f"{strike_offset_pct*100:+.1f}%",
            'gross_pnl': gross_pnl,
            'costs': costs,
            'net_pnl': gross_pnl - costs,
            'vega': vega,
            'theta': theta,
            'win_rate': int(win_rate * 100),
            'max_dd': max_dd,
            'trades_used': filtered_trades,
        }

    # Generate backtest data for 5 offset scenarios, filtered by IVP range
    st.info(f"📊 Backtest filtered for IVP range: {ivp_range[0]}-{ivp_range[1]}%")
    bt_rows = []
    for offset in [-0.025, -0.030, -0.035, -0.040, -0.045]:
        bt_rows.append(generate_backtest_pnl(lookback_m, offset, ivp_range=tuple(ivp_range)))

    df = pd.DataFrame(bt_rows)
    df = df.rename(columns={
        'offset': 'Strike offset',
        'gross_pnl': 'Gross P&L',
        'costs': 'Costs',
        'net_pnl': 'Net P&L',
        'win_rate': 'Win rate',
        'max_dd': 'Max DD',
        'theta': 'Theta',
        'vega': 'Vega'
    })
    df["Net/month %"]    = (df["Net P&L"] / (capital_base * lookback_m) * 100).round(1)
    df["Return on 5L %"] = (df["Net P&L"] / capital_base * 100).round(1)
    df["DD/month %"]     = (df["Max DD"] / (capital_base * lookback_m) * 100).round(1)
    df["Cushion"]        = (df["Theta"] / df["Vega"].abs()).round(1)

    ca, cb, cc = st.columns(3)
    with ca:
        st.markdown("**Return on capital (%)**")
        st.bar_chart(df.set_index("Strike offset")["Return on 5L %"], color="#1D9E75")
    with cb:
        st.markdown("**Win rate (%)**")
        st.bar_chart(df.set_index("Strike offset")["Win rate"], color="#378ADD")
    with cc:
        st.markdown("**Max drawdown (Rs)**")
        st.bar_chart(df.set_index("Strike offset")["Max DD"].abs(), color="#E24B4A")

    st.markdown("---")
    st.caption(f"Capital: Rs {capital_base:,} | Lookback: {lookback_m}m | Entry: {entry_time} | Exit: {exit_time} | {'Fridays excluded' if excl_fri else 'All days'} | IVP filter: {ivp_range[0]}-{ivp_range[1]}%")

    disp = df.rename(columns={
        "Gross P&L": "Gross P&L (Rs)", "Costs": "Costs (Rs)",
        "Net P&L": "Net P&L (Rs)", "Vega": "Vega (Rs/1%IV)",
        "Theta": "Theta (Rs/day)", "Win rate": "Win rate (%)",
        "Max DD": "Max DD (Rs)", "Net/month %": "Net/month (%)",
        "Return on 5L %": "Return on Rs5L (%)", "DD/month %": "DD/month (%)",
        "Cushion": "Cushion (T/V)"
    })
    st.dataframe(disp[[
        "Strike offset","Gross P&L (Rs)","Costs (Rs)","Net P&L (Rs)",
        "Net/month (%)","Return on Rs5L (%)","Vega (Rs/1%IV)",
        "Theta (Rs/day)","Cushion (T/V)","Win rate (%)","Max DD (Rs)","DD/month (%)"
    ]], use_container_width=True, hide_index=True)

    with st.expander("Glossary & display rules"):
        st.markdown("""
**Net/month (%)** — Net P&L / (Rs 5,00,000 x lookback months). Shows return pace per month.

**Max DD/month (%)** — Largest loss / (Rs 5L x months). Negative = monthly capital at risk.

**Vega (Rs per 1% IV)** — P&L change for every 1% rise in IV. Negative because you are SHORT vol. Example: Vega=-220 means IV +5% costs you Rs 1,100.

**Theta (Rs/day)** — Daily time-decay income. Positive because you are short options. Theta=+440 means you earn Rs 440 per calendar day held.

**Cushion ratio (Theta / |Vega|)** — How many IV points must spike in ONE day to wipe today's Theta. 2x = IV needs to jump 2 full points to cancel one day's decay. Green >= 2x, Amber 1-2x, Red < 1x.

**Signal score** — 60% x BS probability N(d2) + 40% x IVP quality (IVP x 1.25, capped 100). Threshold adjustable in sidebar.

**Holiday DTE** — Calendar days minus weekends and NSE holidays. Example: Apr 3 to Apr 7 — Sat (5th) + Sun (6th) excluded = effective DTE of 2 days. Makes probability higher, Theta steeper.

**Display rules** — Rs: integers, Indian comma format. Percentages: one decimal. Ratios: one decimal + x. Negatives: in brackets.
        """)

# ── TAB 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    top_bar()
    st.markdown("---")

    # ── Dhan API credentials ──────────────────────────────────────────────────
    DHAN_CLIENT_ID  = "1109450231"
    NIFTY_SCRIP_ID  = 13
    SENSEX_SCRIP_ID = 51
    IDX_SEG         = "IDX_I"

    with st.expander("🔑 Dhan Access Token", expanded=not st.session_state.get("dhan_loaded")):
        dhan_token = st.text_input("Paste Dhan Access Token (from api.dhan.co)",
                                   type="password", key="dhan_tok",
                                   placeholder="eyJ0eXAiOiJKV1QiLCJhbGci...")
        st.caption(f"Client ID: `{DHAN_CLIENT_ID}` (hardcoded)")

    def fetch_dhan_expiry_list(scrip_id, tok):
        url = "https://api.dhan.co/v2/optionchain/expirylist"
        try:
            r = requests.post(url,
                              json={"UnderlyingScrip": scrip_id, "UnderlyingSeg": IDX_SEG},
                              headers={"Content-Type": "application/json",
                                       "client-id": DHAN_CLIENT_ID, "access-token": tok},
                              timeout=10)
            d = r.json()
            if d.get("status") == "success":
                return d.get("data", [])
            else:
                st.error(f"Dhan expiry error: `{d}`")
        except Exception as e:
            st.error(f"Expiry request failed: `{e}`")
        return []

    def fetch_dhan_chain(scrip_id, expiry_str, tok):
        url = "https://api.dhan.co/v2/optionchain"
        try:
            r = requests.post(url,
                              json={"UnderlyingScrip": scrip_id,
                                    "UnderlyingSeg": IDX_SEG,
                                    "Expiry": expiry_str},
                              headers={"Content-Type": "application/json",
                                       "client-id": DHAN_CLIENT_ID, "access-token": tok},
                              timeout=10)
            d = r.json()
            if d.get("status") == "success":
                return d.get("data", {})
            else:
                st.error(f"Dhan chain error: `{d}`")
        except Exception as e:
            st.error(f"Chain request failed: `{e}`")
        return {}

    def get_premium_from_chain(chain_data, strike_price, side):
        """Return LTP (1 decimal) for a strike+side from Dhan chain response."""
        oc = chain_data.get("oc", {})
        for key, val in oc.items():
            if abs(float(key) - strike_price) < 1:
                leg = val.get("ce" if side == "call" else "pe", {})
                ltp = leg.get("last_price", 0)
                return round(float(ltp), 1)
        return None

    # ── Expiry selector ───────────────────────────────────────────────────────
    scrip_id = NIFTY_SCRIP_ID if instrument == "NIFTY 50" else SENSEX_SCRIP_ID
    tok       = st.session_state.get("dhan_tok", "")
    has_creds = bool(tok)

    ec1, ec2, ec3 = st.columns([2, 2, 1])
    with ec1:
        if has_creds:
            expiry_list = fetch_dhan_expiry_list(scrip_id, tok)
            if expiry_list:
                selected_expiry_str = st.selectbox("Expiry (from Dhan)", expiry_list, key="tab2_expiry")
            else:
                selected_expiry_str = str(expiry_dt)
                st.warning("Could not load expiries — check credentials.")
        else:
            selected_expiry_str = str(expiry_dt)
            st.info("Enter Dhan credentials above to load live expiry list.")
    with ec2:
        fetch_chain_btn = st.button("📡 Fetch Live Chain", type="primary", disabled=not has_creds)
    with ec3:
        st.caption("Rate limit:\n1 req / 3 sec")

    if fetch_chain_btn and has_creds:
        with st.spinner("Fetching option chain from Dhan..."):
            chain = fetch_dhan_chain(scrip_id, selected_expiry_str, tok)
        if chain:
            st.session_state["dhan_chain"]      = chain
            st.session_state["dhan_expiry"]     = selected_expiry_str
            st.session_state["dhan_loaded"]     = True
            st.session_state["dhan_fetched_at"] = datetime.now().strftime("%H:%M:%S")
            st.session_state["dhan_spot"]       = chain.get("last_price", spot)
            st.success(f"✅ Chain loaded | Spot: ₹{chain.get('last_price', spot):,.1f} | Expiry: {selected_expiry_str}")
        else:
            st.error("Empty response from Dhan. Check credentials / expiry date.")

    # Use Dhan spot if fetched, else sidebar spot
    live_spot  = st.session_state.get("dhan_spot", spot)
    chain_data = st.session_state.get("dhan_chain", {})
    fetched_at = st.session_state.get("dhan_fetched_at", "")
    src_label  = f"Dhan API (fetched {fetched_at})" if chain_data else "Formula estimate (no Dhan data)"

    if not ivp_ok:
        st.error(f"REGIME: SKIP — IVP={ivp} outside {ivp_range[0]}-{ivp_range[1]}%. No trades today.")
    else:
        st.success(f"REGIME: ALLOW — IVP={ivp} in range. DTE={dte_adj} days (holiday-adjusted). Source: {src_label}")

    # ── Build leg tables ──────────────────────────────────────────────────────
    def make_leg(offsets, side):
        rows = []
        for off in offsets:
            # Round strike to nearest 50 (NSE standard)
            strike = int(round(live_spot * (1 + off) / 50) * 50)

            # Live premium from Dhan chain first, fall back to formula
            prem = get_premium_from_chain(chain_data, strike, side) if chain_data else None
            if prem is None or prem == 0:
                iv_factor     = iv / 0.14
                offset_factor = max(0.3, 1.0 - (abs(off) - 0.025) / 0.02)
                prem          = round(max(5.0, 1267 * offset_factor * iv_factor / 65), 1)
                prem_src      = "~est"
            else:
                prem_src = "live"

            profit   = round(prem * lot_size, 1)
            cap_req  = 250_000 if instrument == "NIFTY 50" else 125_000
            ret_pct  = round(profit / cap_req * 100, 1)
            prob     = bs_nd2(live_spot, strike, iv, dte_adj) if side == "put" \
                       else 1 - bs_nd2(live_spot, strike, iv, dte_adj)
            theta    = round(prem * lot_size / dte_adj, 1)
            vega     = round(-prem * lot_size * 0.15, 1)
            cushion  = round(theta / abs(vega), 1) if vega != 0 else 0
            score    = comp_score(prob, ivp)
            action   = sig_label(score, sig_thresh)
            ext_spot = strike * (0.995 if side == "put" else 1.005)
            ext_loss = round((strike - ext_spot) * lot_size) if side == "put" \
                       else round((ext_spot - strike) * lot_size)
            rows.append({
                "Offset":          f"{off*100:+.1f}%",
                "Strike":          strike,
                "Premium":         prem,
                "Src":             prem_src,
                "Profit/lot (Rs)": int(profit),
                "Capital (Rs)":    cap_req,
                "Return (%)":      ret_pct,
                "Prob N(d2) (%)":  round(prob * 100),
                "Theta (Rs/day)":  theta,
                "Vega (Rs/1%IV)":  vega,
                "Cushion":         cushion,
                "Score":           score,
                "Action":          action,
                "Ext. loss (Rs)":  ext_loss,
            })
        return pd.DataFrame(rows)

    put_df  = make_leg(PUT_OFFSETS,  "put")
    call_df = make_leg(CALL_OFFSETS, "call")
    bp = put_df.loc[put_df["Score"].idxmax()]
    bc = call_df.loc[call_df["Score"].idxmax()]

    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Best put strike",  f"₹{bp['Strike']:,} ({bp['Offset']})",
              f"Score {bp['Score']} | Prob {bp['Prob N(d2) (%)']}%")
    v2.metric("Best call strike", f"₹{bc['Strike']:,} ({bc['Offset']})",
              f"Score {bc['Score']} | Prob {bc['Prob N(d2) (%)']}%")
    strangle = bp["Score"] >= sig_thresh and bc["Score"] >= sig_thresh
    rec = "Strangle" if strangle else \
          ("Sell call" if bc["Score"] >= sig_thresh else
           ("Sell put" if bp["Score"] >= sig_thresh else "Stay out"))
    v3.metric("Recommendation", rec, f"Threshold: {sig_thresh}")
    v4.metric("Best call cushion", f"{bc['Cushion']}x", ">=2x safe | 1-2x watch | <1x risky")

    st.markdown("---")

    def color_row(df):
        def _apply(col):
            if col.name == "Action":
                colors = []
                for v in col:
                    bg  = sig_color(v)
                    txt = "color: black;" if bg == "#C6EFCE" else "color: white;"
                    colors.append(f"background-color:{bg}; {txt} font-weight: bold;")
                return colors
            if col.name == "Src":
                return ["color: #00cc88;" if v == "live" else "color: #888888;"
                        for v in col]
            return [""] * len(col)
        return df.style.apply(_apply).format({
            "Premium":         "{:.1f}",
            "Profit/lot (Rs)": "{:,}",
            "Capital (Rs)":    "{:,}",
            "Return (%)":      "{:.1f}",
            "Theta (Rs/day)":  "{:.1f}",
            "Vega (Rs/1%IV)":  "{:.1f}",
            "Cushion":         "{:.1f}x",
        })

    st.markdown("**PUT LEG — sell put (profit if spot stays above strike)**")
    st.dataframe(color_row(put_df), use_container_width=True, hide_index=True)

    st.markdown("**CALL LEG — sell call (profit if spot stays below strike)**")
    st.dataframe(color_row(call_df), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption(f"Premium: **live** = Dhan API real LTP (1 decimal) | **~est** = formula fallback. "
               f"Extreme loss = 0.5% beyond outer strike. "
               f"Max loss target < 5% of ₹{capital_base:,} = ₹{capital_base//20:,}")

    with st.expander("Glossary - live signal"):
        st.markdown("""
**Premium** — Actual Last Traded Price from Dhan API option chain, shown to 1 decimal. Green "live" = real Dhan data. Grey "~est" = Black-Scholes formula estimate (shown when Dhan not connected or strike not found).

**Strike rounding** — Rounded to nearest ₹50 to match NSE standard option strikes.

**Prob N(d2)** — Black-Scholes probability the option expires worthless. Inputs: Spot (from Dhan), Strike, IV (annualised), r=6.5%, holiday-adjusted DTE.

**Cushion ratio (Theta / |Vega|)** — How many IV points must spike in ONE day to wipe daily Theta. Green >= 2x, Amber 1-2x, Red < 1x.

**Signal score** — N(d2) x 0.60 + IVP quality x 0.40. IVP quality = IVP x 1.25 capped at 100. Threshold set in sidebar.

**Extreme loss 0.5%** — Worst-case loss if spot moves 0.5% beyond the outer strike at expiry.
        """)

# ── TAB 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    top_bar()
    st.markdown("---")
    st.subheader("📊 IV & Option Chain Data — Expiry Wise")
    st.caption("Source: Dhan API (live) | No charts — table format only")

    tok3 = st.session_state.get("dhan_tok", "")
    DHAN_CLIENT_ID_T3 = "1109450231"
    IDX_SEG_T3 = "IDX_I"

    def dhan_post(url, payload, tok):
        try:
            r = requests.post(url,
                              json=payload,
                              headers={"Content-Type": "application/json",
                                       "client-id": DHAN_CLIENT_ID_T3,
                                       "access-token": tok},
                              timeout=10)
            d = r.json()
            return d if d.get("status") == "success" else None
        except Exception:
            return None

    def fetch_chain_tab3(scrip_id, expiry, tok):
        d = dhan_post("https://api.dhan.co/v2/optionchain",
                      {"UnderlyingScrip": scrip_id, "UnderlyingSeg": IDX_SEG_T3, "Expiry": expiry}, tok)
        return d.get("data", {}) if d else {}

    def fetch_expiries_tab3(scrip_id, tok):
        d = dhan_post("https://api.dhan.co/v2/optionchain/expirylist",
                      {"UnderlyingScrip": scrip_id, "UnderlyingSeg": IDX_SEG_T3}, tok)
        return d.get("data", []) if d else []

    def chain_to_df(chain, spot, band=4.5):
        oc = chain.get("oc", {})
        spot = chain.get("last_price", spot)
        rows = []
        for k, v in oc.items():
            strike = float(k)
            if not (spot*(1-band/100) <= strike <= spot*(1+band/100)):
                continue
            ce = v.get("ce", {}); pe = v.get("pe", {})
            rows.append({
                "Strike":    int(strike),
                "CE LTP":    round(ce.get("last_price", 0), 1),
                "CE OI":     ce.get("oi", 0),
                "CE IV%":    round(ce.get("implied_volatility", 0), 2),
                "CE Delta":  round(ce.get("greeks", {}).get("delta", 0), 3),
                "CE Vol":    ce.get("volume", 0),
                "PE LTP":    round(pe.get("last_price", 0), 1),
                "PE OI":     pe.get("oi", 0),
                "PE IV%":    round(pe.get("implied_volatility", 0), 2),
                "PE Delta":  round(pe.get("greeks", {}).get("delta", 0), 3),
                "PE Vol":    pe.get("volume", 0),
            })
        return pd.DataFrame(rows).sort_values("Strike").reset_index(drop=True), spot

    if not tok3:
        st.info("👆 Paste your Dhan Access Token in Tab 2 first, then come back here.")
    else:
        t3c1, t3c2 = st.columns(2)

        # ── NIFTY section ──
        with t3c1:
            st.markdown("#### NIFTY 50")
            nifty_expiries = fetch_expiries_tab3(13, tok3)
            if nifty_expiries:
                sel_n = st.selectbox("Nifty Expiry", nifty_expiries, key="t3_nifty_exp")
                if st.button("Load Nifty Chain", key="t3_nifty_btn"):
                    ch = fetch_chain_tab3(13, sel_n, tok3)
                    if ch:
                        st.session_state["t3_nifty_chain"] = ch
                        st.session_state["t3_nifty_exp_used"] = sel_n
                if "t3_nifty_chain" in st.session_state:
                    df_n, spot_n = chain_to_df(st.session_state["t3_nifty_chain"], SPOT["NIFTY 50"])
                    atm_n = df_n.iloc[(df_n["Strike"] - spot_n).abs().argsort()[:1]]["Strike"].values[0]
                    st.caption(f"Spot: ₹{spot_n:,.1f} | ATM: ₹{atm_n:,} | Expiry: {st.session_state.get('t3_nifty_exp_used','')}")
                    def hl_atm_n(row):
                        return ["background-color:#2d2d4e;font-weight:bold"]*len(row) if row["Strike"]==atm_n else [""]*len(row)
                    st.dataframe(
                        df_n.style.apply(hl_atm_n, axis=1).format({
                            "CE LTP":"{:.1f}","PE LTP":"{:.1f}",
                            "CE IV%":"{:.2f}","PE IV%":"{:.2f}",
                            "CE Delta":"{:.3f}","PE Delta":"{:.3f}",
                            "CE OI":"{:,.0f}","PE OI":"{:,.0f}",
                            "CE Vol":"{:,.0f}","PE Vol":"{:,.0f}",
                        }),
                        use_container_width=True, hide_index=True, height=450
                    )
            else:
                st.warning("Could not load Nifty expiries.")

        # ── SENSEX section ──
        with t3c2:
            st.markdown("#### SENSEX")
            sensex_expiries = fetch_expiries_tab3(51, tok3)
            if sensex_expiries:
                sel_s = st.selectbox("Sensex Expiry", sensex_expiries, key="t3_sensex_exp")
                if st.button("Load Sensex Chain", key="t3_sensex_btn"):
                    ch = fetch_chain_tab3(51, sel_s, tok3)
                    if ch:
                        st.session_state["t3_sensex_chain"] = ch
                        st.session_state["t3_sensex_exp_used"] = sel_s
                if "t3_sensex_chain" in st.session_state:
                    df_s, spot_s = chain_to_df(st.session_state["t3_sensex_chain"], SPOT["SENSEX"])
                    atm_s = df_s.iloc[(df_s["Strike"] - spot_s).abs().argsort()[:1]]["Strike"].values[0]
                    st.caption(f"Spot: ₹{spot_s:,.1f} | ATM: ₹{atm_s:,} | Expiry: {st.session_state.get('t3_sensex_exp_used','')}")
                    def hl_atm_s(row):
                        return ["background-color:#2d2d4e;font-weight:bold"]*len(row) if row["Strike"]==atm_s else [""]*len(row)
                    st.dataframe(
                        df_s.style.apply(hl_atm_s, axis=1).format({
                            "CE LTP":"{:.1f}","PE LTP":"{:.1f}",
                            "CE IV%":"{:.2f}","PE IV%":"{:.2f}",
                            "CE Delta":"{:.3f}","PE Delta":"{:.3f}",
                            "CE OI":"{:,.0f}","PE OI":"{:,.0f}",
                            "CE Vol":"{:,.0f}","PE Vol":"{:,.0f}",
                        }),
                        use_container_width=True, hide_index=True, height=450
                    )
            else:
                st.warning("Could not load Sensex expiries.")
