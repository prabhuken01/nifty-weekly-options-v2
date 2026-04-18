"""
Nifty Weekly Options Strategy Dashboard
Tabs: 1-Live Signal  2-Backtest  3-IV History
"""
import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import date, timedelta, datetime, timezone
import math, requests, sys, os, re, json
import io

# ── IST helper ────────────────────────────────────────────────────────────────
_IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    """Return current datetime in IST (UTC+5:30)."""
    return datetime.now(_IST).replace(tzinfo=None)

for d in ['Live-Signal-Generator', 'Live-fetching']:
    p = os.path.join(os.path.dirname(__file__), d)
    if os.path.exists(p):
        sys.path.insert(0, p); break

st.set_page_config(page_title="Nifty Options Dashboard", layout="wide",
                   page_icon="📈", initial_sidebar_state="expanded")


def _is_mobile_client():
    """Best-effort mobile detection (Streamlit Cloud forwards User-Agent)."""
    try:
        ctx = getattr(st, "context", None)
        if ctx is None or not getattr(ctx, "headers", None):
            return False
        ua = (ctx.headers.get("User-Agent") or "").lower()
        return "mobi" in ua or "iphone" in ua or "ipod" in ua or "android" in ua
    except Exception:
        return False


_IS_MOBILE = _is_mobile_client()

# ── Mobile-friendly CSS (desktop vs phone font scale) ────────────────────────
_desktop_fs = 18
_mobile_fs = 18
_df_fs = 17 if not _IS_MOBILE else 16
_sub = 22 if not _IS_MOBILE else 22
_h1 = 28 if not _IS_MOBILE else 24
_h2 = 22 if not _IS_MOBILE else 20

st.markdown(f"""
<style>
/* Desktop: larger readable base; mobile: slightly larger again */
.stApp {{ font-size: {_desktop_fs if not _IS_MOBILE else _mobile_fs}px !important; }}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {{
    font-size: {0.98 * (_desktop_fs if not _IS_MOBILE else _mobile_fs):.0f}px !important;
    line-height: 1.5 !important;
}}
.stDataFrame, [data-testid="stDataFrame"] {{
    font-size: {_df_fs}px !important;
}}
.stDataFrame td, .stDataFrame th {{
    padding: {"10px 12px" if not _IS_MOBILE else "8px 10px"} !important;
}}
[data-testid="stMetricLabel"] {{ font-size: {15 if not _IS_MOBILE else 15}px !important; }}
[data-testid="stMetricValue"] {{ font-size: {26 if not _IS_MOBILE else 24}px !important; font-weight: 700 !important; }}
div[data-testid="stDataFrame"] div[data-testid="stMarkdownContainer"] p {{
    font-size: {_df_fs}px !important;
}}
[data-testid="stVerticalBlock"] > div .stMarkdown p {{
    font-size: {0.95 * (_desktop_fs if not _IS_MOBILE else _mobile_fs):.0f}px !important;
}}
h1 {{ font-size: {_h1}px !important; }}
h2, .stSubheader {{ font-size: {_sub}px !important; }}
h3 {{ font-size: {20 if not _IS_MOBILE else 17}px !important; }}
.stCaption {{ font-size: {13 if not _IS_MOBILE else 14}px !important; }}

@media (max-width: 768px) {{
    .stApp {{ font-size: {_mobile_fs}px !important; }}
    [data-testid="stMetric"] {{ padding: 8px 10px !important; }}
    [data-testid="stMetricValue"] {{ font-size: 23px !important; }}
    .stTabs [data-baseweb="tab"] {{ font-size: 15px !important; padding: 10px 14px !important; }}
    [data-testid="stSidebar"] {{ min-width: 280px !important; }}
    [data-testid="column"] {{ min-width: 140px !important; }}
}}
:root {{
    --bg-main: #0D0D0D; --bg-card: #1A1A1A; --bg-border: #2A2A2A;
    --text-pri: #F0F0F0; --text-sec: #A0A0A0;
    --accent-pos: #00C896; --accent-neg: #FF4D4D; --accent-neu: #7B8CDE;
}}
.stApp {{ background-color: var(--bg-main) !important; color: var(--text-pri) !important; }}
.stApp > header {{ background-color: var(--bg-main) !important; }}
section[data-testid="stSidebar"] {{
    background-color: var(--bg-card) !important;
    border-right: 1px solid var(--bg-border) !important;
}}
section[data-testid="stSidebar"] * {{ color: var(--text-pri) !important; }}
[data-testid="stMetric"] {{
    background-color: var(--bg-card) !important;
    border: 1px solid var(--bg-border) !important;
    border-radius: 8px !important; padding: 10px 14px !important;
}}
[data-testid="stMetricLabel"] {{ color: var(--text-sec) !important; }}
[data-testid="stMetricValue"] {{ color: var(--text-pri) !important; }}
[data-testid="stMetricDelta"] {{ color: var(--accent-pos) !important; }}
.stTabs [data-baseweb="tab-list"] {{
    background-color: var(--bg-card) !important;
    border-bottom: 2px solid var(--bg-border) !important;
}}
.stTabs [data-baseweb="tab"] {{ color: var(--text-sec) !important; background: transparent !important; }}
.stTabs [aria-selected="true"] {{
    color: var(--accent-neu) !important;
    border-bottom: 2px solid var(--accent-neu) !important;
}}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{
    background-color: var(--bg-card) !important;
    border-color: var(--bg-border) !important; color: var(--text-pri) !important;
}}
.stDataFrame {{ border: 1px solid var(--bg-border) !important; border-radius: 6px; }}
.stDataFrame th {{
    font-weight: 700 !important; background-color: #1E1E2E !important;
    color: var(--text-pri) !important; border-bottom: 2px solid var(--bg-border) !important;
}}
.stDataFrame td {{ color: var(--text-pri) !important; border-bottom: 1px solid var(--bg-border) !important; }}
div[data-testid="stAlert"] {{ background-color: var(--bg-card) !important; border-left-width: 4px !important; }}
div[data-testid="stAlert"] p {{ color: var(--text-pri) !important; }}
.stButton > button {{
    background-color: var(--bg-card) !important;
    color: var(--text-pri) !important; border: 1px solid var(--bg-border) !important;
}}
.stButton > button:hover {{ border-color: var(--accent-neu) !important; color: var(--accent-neu) !important; }}
.stButton > button[kind="primary"] {{
    background-color: #1A2A4A !important; border-color: var(--accent-neu) !important;
    color: var(--accent-neu) !important;
}}
details {{ background-color: var(--bg-card) !important; border: 1px solid var(--bg-border) !important; border-radius: 8px !important; }}
summary {{ color: var(--text-pri) !important; }}
.stCaption {{ color: var(--text-sec) !important; }}
hr {{ border-color: var(--bg-border) !important; }}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
# DhanHQ: lengthen cache vs default 60s — override with env (seconds). Token refresh is separate from TTL.
DHAN_LTP_TTL   = max(60, int(os.environ.get("DHAN_LTP_TTL_SECONDS", "900")))      # default 15 min
DHAN_MISC_TTL  = max(120, int(os.environ.get("DHAN_MISC_TTL_SECONDS", "1800")))   # funds / expiry list
DHAN_CLIENT_ID  = "1109450231"

# Tab 2 ↔ Validation Explorer: same five cores, same ranking order (first wins ties)
BT_CORE_STYPES = ("ss", "ws", "ic", "bp", "bc")
BT_STYPE_LABELS = {
    "ss": "Short Strangle", "ws": "Wide Strangle", "ic": "Iron Condor",
    "bp": "Bull Put Spread", "bc": "Bear Call Spread",
}


def _detail_popover(title: str, body_md: str):
    """Mobile: short on-screen text + ℹ️ popover. Desktop: caption (full width)."""
    if _IS_MOBILE:
        pop = getattr(st, "popover", None)
        if pop:
            with st.popover(f"ℹ️ {title}"):
                st.markdown(body_md)
        else:
            with st.expander(f"ℹ️ {title}", expanded=False):
                st.markdown(body_md)
    else:
        st.caption(body_md)
NIFTY_SCRIP_ID  = 13
SENSEX_SCRIP_ID = 51
IDX_SEG         = "IDX_I"

NSE_HOLIDAYS = {
    date(2026,1,26), date(2026,3,25), date(2026,4,2), date(2026,4,5),
    date(2026,4,6),  date(2026,4,14), date(2026,5,1), date(2026,8,15),
    date(2026,10,2), date(2026,10,26),date(2026,11,4),date(2026,12,25),
}

LOT   = {"NIFTY 50": 65,      "SENSEX": 20}
CAP   = {"NIFTY 50": 125_000, "SENSEX": 125_000}   # both default 1.25L
ROUND = {"NIFTY 50": 50,      "SENSEX": 100}
# Fallback IV values used when live option chain data is unavailable
# In normal operation, IV is calculated dynamically from ATM straddle (DTE≥2 rule)
IV_ANN= {"NIFTY 50": 0.142,   "SENSEX": 0.138}

# ── Helper functions ──────────────────────────────────────────────────────────
def effective_dte(from_date, expiry):
    count, d = 0, from_date + timedelta(days=1)
    while d <= expiry:
        if d.weekday() < 5 and d not in NSE_HOLIDAYS:
            count += 1
        d += timedelta(days=1)
    return max(count, 1)

def parse_exp(s):
    try:    return datetime.strptime(s, "%Y-%m-%d").date()
    except: return date.today() + timedelta(days=7)

def bs_d1d2(spot, strike, iv, T, r=0.065):
    if iv <= 0 or T <= 0: return 0, 0
    d1 = (math.log(spot/strike) + (r + 0.5*iv**2)*T) / (iv*math.sqrt(T))
    return d1, d1 - iv*math.sqrt(T)

def prob_nd2(spot, strike, iv, dte_days, side):
    T = dte_days/365
    _, d2 = bs_d1d2(spot, strike, iv, T)
    p = float(norm.cdf(d2))
    return p if side == "put" else 1-p

def delta_bs(spot, strike, iv, dte_days, side):
    T = dte_days/365
    d1, _ = bs_d1d2(spot, strike, iv, T)
    nd1 = float(norm.cdf(d1))
    return round(nd1 - 1, 3) if side == "put" else round(nd1, 3)

def comp_score(prob, ret_pct=0):
    """Score = 60% × Prob(OTM) + 40% × Return attractiveness"""
    prob_component = prob * 100 * 0.60
    ret_component  = min(100, ret_pct * 25) * 0.40   # 4% ret = 100 score
    return round(prob_component + ret_component)
def sig_label(sc, thr=65): return "SELL" if sc>=thr else ("MONITOR" if sc>=50 else "AVOID")
def sig_color(lbl): return {"SELL":"#00AA55","MONITOR":"#FF9500","AVOID":"#DD3333"}[lbl]

# ── Strategy name normalisation (BUG 1 + BUG 2) ──────────────────────────
def norm_strategy_name(s):
    """Strip S# - prefix and (ONLY) suffix for comparisons (BUG 1+2)."""
    s = re.sub(r'^S\d+\s*[-–]\s*', '', str(s).strip())
    s = re.sub(r'\s*\(ONLY\)\s*$', '', s)
    return s.strip()

def lut_strategy_display(lut_entry):
    """UI display label — strips (ONLY) and S#- prefix (same as comparisons)."""
    return norm_strategy_name(lut_entry.get("s", "")) if lut_entry else ""

def lut_strategy_base(lut_entry):
    """Base name stripped of (ONLY) for comparisons (BUG 2)."""
    return norm_strategy_name(lut_entry.get("s", ""))

# ── Dhan API ──────────────────────────────────────────────────────────────────
def _hdr(tok): return {"Content-Type":"application/json","client-id":DHAN_CLIENT_ID,"access-token":tok}

@st.cache_data(ttl=DHAN_LTP_TTL, show_spinner=False)
@st.cache_data(ttl=DHAN_LTP_TTL, show_spinner=False)
def fetch_ltp_cached(tok):
    """Cached LTP fetch (respects DHAN_LTP_TTL, default 15 min)."""
    try:
        r = requests.post("https://api.dhan.co/v2/marketfeed/ltp",
                          json={"IDX_I":[13,51]}, headers=_hdr(tok), timeout=8)
        idx = r.json().get("data",{}).get("IDX_I",{})
        n = idx.get("13",{}).get("last_price",0)
        s = idx.get("51",{}).get("last_price",0)
        if n and s:
            return {"nifty":float(n),"sensex":float(s),"ts":now_ist().strftime("%H:%M:%S")}
    except: pass
    return None

def fetch_ltp_kite(kite_api_key, kite_access_token):
    """Fetch LTP from Kite Connect (fallback when Dhan fails)."""
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=kite_api_key)
        kite.access_token = kite_access_token

        # Fetch quotes for NIFTY (256265) and SENSEX (265)
        quotes = kite.quote(["NSE:NIFTY50", "BSE:SENSEX"])

        n = quotes.get("NSE:NIFTY50", {}).get("last_price", 0)
        s = quotes.get("BSE:SENSEX", {}).get("last_price", 0)

        if n and s:
            return {"nifty":float(n),"sensex":float(s),"ts":now_ist().strftime("%H:%M:%S"), "source":"Kite"}
    except ImportError:
        pass  # KiteConnect not installed
    except Exception:
        pass  # Kite fetch failed
    return None

def fetch_ltp(tok):
    """Non-cached LTP for session state updates (Dhan → Kite fallback → None)."""
    # Try Dhan first
    try:
        r = requests.post("https://api.dhan.co/v2/marketfeed/ltp",
                          json={"IDX_I":[13,51]}, headers=_hdr(tok), timeout=8)
        resp_json = r.json()

        if resp_json.get("status") == "failure":
            dhan_msg = resp_json.get('message','Unknown error')
            if "401" in str(resp_json) or "Unauthorized" in dhan_msg:
                # Token expired
                st.warning(f"🔴 **Dhan token expired** — Paste new token below")
            else:
                st.warning(f"⚠️ Dhan LTP failed: {dhan_msg[:40]}")
            dhan_success = False
        else:
            idx = resp_json.get("data",{}).get("IDX_I",{})
            n = idx.get("13",{}).get("last_price")
            s = idx.get("51",{}).get("last_price")
            if n and s:
                return {"nifty":float(n),"sensex":float(s),"ts":now_ist().strftime("%H:%M:%S"), "source":"Dhan"}
            dhan_success = False

    except requests.Timeout:
        st.warning("⚠️ Dhan LTP timeout — trying Kite fallback")
        dhan_success = False
    except Exception as e:
        st.warning(f"⚠️ Dhan LTP error ({type(e).__name__}): {str(e)[:80]} — trying Kite fallback")
        dhan_success = False

    # Try Kite fallback if Dhan failed
    try:
        kite_key = st.secrets.get("kite", {}).get("api_key")
        kite_token = st.secrets.get("kite", {}).get("access_token")
        if kite_key and kite_token:
            kite_ltp = fetch_ltp_kite(kite_key, kite_token)
            if kite_ltp:
                st.info(f"✓ Using Kite LTP (Dhan unavailable)")
                return kite_ltp
    except:
        pass

    return None

@st.cache_data(ttl=DHAN_MISC_TTL, show_spinner=False)
def fetch_funds(tok):
    try:
        r = requests.get("https://api.dhan.co/v2/fundlimit", headers=_hdr(tok), timeout=8)
        d = r.json()
        return {"available":d.get("availabelBalance",0),"used":d.get("utilizedAmount",0),"total":d.get("sodLimit",0)}
    except: return None

@st.cache_data(ttl=DHAN_MISC_TTL, show_spinner=False)
def fetch_expiry_list(scrip_id, tok):
    try:
        r = requests.post("https://api.dhan.co/v2/optionchain/expirylist",
                          json={"UnderlyingScrip":scrip_id,"UnderlyingSeg":IDX_SEG},
                          headers=_hdr(tok), timeout=10)
        d = r.json()
        if d.get("status") == "success": return d.get("data",[])
    except: pass
    return []

def fetch_chain(scrip_id, expiry_str, tok):
    try:
        r = requests.post("https://api.dhan.co/v2/optionchain",
                          json={"UnderlyingScrip":scrip_id,"UnderlyingSeg":IDX_SEG,"Expiry":expiry_str},
                          headers=_hdr(tok), timeout=10)
        d = r.json()
        if d.get("status") == "success": return d.get("data",{})
    except: pass
    return {}

def ltp_from_chain(chain, strike, side):
    for k, v in chain.get("oc",{}).items():
        if abs(float(k)-strike) < 1:
            ltp = v.get("ce" if side=="call" else "pe",{}).get("last_price",0)
            return round(float(ltp),1) if ltp else None
    return None

# ── Dhan Partner OAuth constants ──────────────────────────────────────────────
DHAN_PARTNER_KEY  = "12c0fd3e"
DHAN_APP_URL      = "https://nifty-weekly-options-v2.streamlit.app/"
DHAN_LOGIN_URL    = (f"https://web.dhan.co/login?"
                     f"partnerId={DHAN_PARTNER_KEY}"
                     f"&redirectUri={DHAN_APP_URL}")

# ── Shared token cache (persists across sessions on same server instance) ──────
_TOKEN_CACHE = os.path.join(os.path.dirname(__file__), ".streamlit", "_tok_cache.json")

def _save_token_cache(tok: str):
    """Write token to server-side cache so all sessions (incl. mobile) can load it."""
    try:
        os.makedirs(os.path.dirname(_TOKEN_CACHE), exist_ok=True)
        with open(_TOKEN_CACHE, "w") as _f:
            json.dump({"token": tok, "saved_at": now_ist().isoformat()}, _f)
    except Exception:
        pass

def _load_token_cache() -> str:
    """Read token from server-side cache. Returns '' if missing/expired."""
    try:
        with open(_TOKEN_CACHE) as _f:
            data = json.load(_f)
        tok = data.get("token", "")
        if not tok:
            return ""
        # Validate JWT expiry before returning
        import base64 as _b64
        payload = json.loads(_b64.urlsafe_b64decode(tok.split('.')[1] + '=='))
        if payload.get('exp', 0) > now_ist().timestamp():
            return tok
        return ""   # expired — don't use
    except Exception:
        return ""

# ── Token: OAuth redirect → secrets → cache file → session ───────────────────
# 1. Check if Dhan redirected back with tokenId in URL (Partner OAuth flow)
_qp = st.query_params
_tok_from_url = _qp.get("tokenId", "")
if _tok_from_url and _tok_from_url.strip():
    _clean_tok = _tok_from_url.strip()
    st.session_state["dhan_tok"] = _clean_tok
    st.session_state["_tok_manually_set"] = True
    st.session_state["_tok_from_oauth"] = True
    _save_token_cache(_clean_tok)          # ← persist so mobile sessions pick it up
    try:
        st.query_params.clear()
    except Exception:
        pass

# 2. Secrets (Streamlit Cloud configured token)
if not st.session_state.get("dhan_tok"):
    try:
        t = st.secrets["dhan"]["access_token"]
        if t and t.strip(): st.session_state["dhan_tok"] = t.strip()
    except: pass

# 3. Server-side cache file (written when any session completes OAuth)
if not st.session_state.get("dhan_tok"):
    _cached = _load_token_cache()
    if _cached:
        st.session_state["dhan_tok"] = _cached

if not st.session_state.get("kite_loaded"):
    try:
        kite_cfg = st.secrets.get("kite", {})
        if kite_cfg.get("api_key") and kite_cfg.get("access_token"):
            st.session_state["kite_loaded"] = True
    except: pass

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── SECTION 1: Data Source ────────────────────────────────────────────────
    st.markdown("### 1️⃣ Data Source")
    st.selectbox("Source", ["DhanHQ API","NSE Bhavcopy (EOD)","Kite Connect"], key="data_src")

    # Token — only show input if NOT already loaded from secrets
    _tok_from_secret = bool(
        not st.session_state.get("_tok_manually_set") and
        st.session_state.get("dhan_tok") and
        not st.session_state.get("dhan_token")
    )
    st.markdown("**📊 Live Data Source**")
    _tab_dhan, _tab_kite = st.tabs(["Dhan (Primary)", "Kite (Fallback)"])

    with _tab_dhan:
        # ── Decode token expiry from JWT ──────────────────────────────────────
        def _tok_expiry_info(tok_str):
            """Return (expires_dt, hours_left) from JWT payload, or (None, None)."""
            try:
                import base64, json as _json
                payload = _json.loads(base64.urlsafe_b64decode(tok_str.split('.')[1] + '=='))
                exp_dt  = datetime.fromtimestamp(payload['exp'])
                hrs     = (exp_dt - now_ist()).total_seconds() / 3600
                return exp_dt, hrs
            except Exception:
                return None, None

        _cur_tok = st.session_state.get("dhan_tok", "")
        _exp_dt, _hrs_left = _tok_expiry_info(_cur_tok) if _cur_tok else (None, None)

        if _cur_tok:
            if st.session_state.get("_tok_from_oauth"):
                st.success("✅ Dhan connected via Partner login")
                st.session_state.pop("_tok_from_oauth", None)
            else:
                st.success("✅ Dhan token active")

            if _hrs_left is not None:
                if _hrs_left < 1:
                    st.error(f"🔴 Token expires in {_hrs_left*60:.0f} min — reconnect now!")
                elif _hrs_left < 4:
                    st.warning(f"⚠️ Token expires in {_hrs_left:.1f}h")
                else:
                    st.caption(f"⏰ Expires: {_exp_dt.strftime('%d %b %H:%M')} ({_hrs_left:.0f}h left)")

        # ── One-click reconnect via Partner OAuth ─────────────────────────────
        st.markdown(f"""
<a href="{DHAN_LOGIN_URL}" target="_blank">
  <button style="width:100%;padding:8px;background:#1f77b4;color:white;
                 border:none;border-radius:6px;cursor:pointer;font-size:14px;">
    🔗 {'Reconnect' if _cur_tok else 'Connect'} Dhan (1-click)
  </button>
</a>
""", unsafe_allow_html=True)
        st.caption("Clicking opens Dhan login → after login you're redirected back with token auto-loaded.")

        # ── Manual fallback ───────────────────────────────────────────────────
        with st.expander("Or paste token manually"):
            _inp_key = "dhan_token_override" if _cur_tok else "dhan_token"
            _inp = st.text_input("Dhan access token", type="password", key=_inp_key)
            if _inp:
                _inp_clean = _inp.strip()
                st.session_state["dhan_tok"] = _inp_clean
                st.session_state["_tok_manually_set"] = True
                _save_token_cache(_inp_clean)   # persist for other sessions
                st.success("✓ Token loaded & shared with all sessions")

    with _tab_kite:
        if st.session_state.get("kite_loaded"):
            st.success("✅ Kite token configured")
            st.caption("Kite is ready as fallback when Dhan unavailable")
        else:
            st.info("Kite provides fallback LTP when Dhan fails")
            st.caption("Setup: Run `python kite_token_generator.py` then add to secrets.toml [kite] section")

    tok = st.session_state.get("dhan_tok","")
    has_tok = bool(tok)

    # Expiry selectors
    if has_tok:
        n_exps = fetch_expiry_list(NIFTY_SCRIP_ID, tok)
        s_exps = fetch_expiry_list(SENSEX_SCRIP_ID, tok)
        _ec1, _ec2 = st.columns(2)
        with _ec1:
            sel_n_exp = st.selectbox("Nifty Exp", n_exps if n_exps else ["—"], key="nifty_exp")
        with _ec2:
            sel_s_exp = st.selectbox("Sensex Exp", s_exps if s_exps else ["—"], key="sensex_exp")
    else:
        sel_n_exp = str(date.today() + timedelta(days=3))
        sel_s_exp = str(date.today() + timedelta(days=4))

    # DTE derived from Nifty expiry
    dte_adj = effective_dte(date.today(), parse_exp(sel_n_exp))
    st.caption(f"DTE: **{dte_adj}** trading days to {sel_n_exp} (weekends + holidays excluded)")

    st.caption(
        f"⏱️ **Dhan cache:** LTP **{DHAN_LTP_TTL // 60}m** · funds/expiry list **{DHAN_MISC_TTL // 60}m** "
        f"(env `DHAN_LTP_TTL_SECONDS`, `DHAN_MISC_TTL_SECONDS`). **Chains** refresh each **Fetch** click.")
    fetch_btn = st.button("📡 Fetch Live Chain", type="primary", disabled=not has_tok,
                          use_container_width=True, key="fetch_live_btn")
    if fetch_btn:
        # Clear cached chain so auto-fetch runs fresh
        for k in ["nifty_chain","sensex_chain","chain_ts","chain_ts_epoch",
                  "nifty_spot_live","sensex_spot_live"]:
            st.session_state.pop(k, None)

    # Strike parameters (below Fetch)
    _sc1, _sc2 = st.columns(2)
    with _sc1:
        if not _IS_MOBILE:
            st.write(f"**Dist from spot (%)** — Enter value below")
        dist_pct = st.number_input("Distance from spot (%)", 0.1, 5.0, 0.5, 0.1,
                                   key="dist_pct", help="Closest strike distance from spot",
                                   label_visibility="collapsed" if not _IS_MOBILE else "visible")
    with _sc2:
        if not _IS_MOBILE:
            st.write(f"**Offset step (%)** — Enter value below")
        step_pct = st.number_input("Offset step (%)", 0.1, 2.0, 0.5, 0.1,
                                   key="step_pct", help="Gap between each of the 5 strikes",
                                   label_visibility="collapsed" if not _IS_MOBILE else "visible")
    st.caption(f"Put strikes: −{dist_pct:.1f}% to −{dist_pct+4*step_pct:.1f}% | "
               f"Call: +{dist_pct:.1f}% to +{dist_pct+4*step_pct:.1f}%")
    st.markdown("---")

# ── Tab 1 live-signal filter defaults (widgets live inside Tab 1; tabs 2–3 reuse state)
sig_thresh = int(st.session_state.get("sig_thresh", 65))

# ── Live data ─────────────────────────────────────────────────────────────────
_ltp   = fetch_ltp(tok)   if tok else None
_funds = fetch_funds(tok) if tok else None

# Use session state spot as primary source (from chain fetch), fallback to session LTP, then _ltp, then defaults
SPOT = {
    "NIFTY 50": st.session_state.get(
        "nifty_spot_live",
        st.session_state.get("nifty_ltp_live", _ltp["nifty"] if _ltp else 22700)
    ),
    "SENSEX": st.session_state.get(
        "sensex_spot_live",
        st.session_state.get("sensex_ltp_live", _ltp["sensex"] if _ltp else 73320)
    )
}
PRICE_TS  = _ltp["ts"] if _ltp else "—"
PRICE_SRC = "Dhan LTP" if _ltp else "Mock"

# Capital: from Dhan if available, else 1.25L for both
if _funds and _funds["total"] > 0:
    capital_base = int(_funds["total"])
    cap_src = "live"
else:
    capital_base = 125_000
    cap_src = "mock"

# Dynamic strike offsets
PUT_OFFSETS  = [-(dist_pct/100 + i*(step_pct/100)) for i in range(5)]
CALL_OFFSETS = [+(dist_pct/100 + i*(step_pct/100)) for i in range(5)]

# ── Handle fetch button + auto-refresh logic ─────────────────────────────────
_chain_age_mins = (now_ist().timestamp() - st.session_state.get("chain_ts_epoch", 0)) / 60
_expiry_changed = (st.session_state.get("nifty_exp_used") != sel_n_exp or
                   st.session_state.get("sensex_exp_used") != sel_s_exp)

# Auto-fetch conditions:
# 1. First load (no chain in session)
# 2. Chain is older than 5 minutes
# 3. Selected expiry changed since last fetch
_auto_fetch = has_tok and (
    "nifty_chain" not in st.session_state or
    _chain_age_mins > 5 or
    _expiry_changed
)

if (fetch_btn or _auto_fetch) and has_tok:
    with st.spinner("Fetching Nifty & Sensex option chains…"):
        nc = fetch_chain(NIFTY_SCRIP_ID,  sel_n_exp, tok)
        sc = fetch_chain(SENSEX_SCRIP_ID, sel_s_exp, tok)
    ts = now_ist().strftime("%H:%M:%S")
    if nc:
        st.session_state.update({"nifty_chain":nc,"nifty_exp_used":sel_n_exp,
                                  "nifty_spot_live":nc.get("last_price",SPOT["NIFTY 50"])})
    if sc:
        st.session_state.update({"sensex_chain":sc,"sensex_exp_used":sel_s_exp,
                                  "sensex_spot_live":sc.get("last_price",SPOT["SENSEX"])})
    if nc or sc:
        st.session_state["chain_ts"] = ts
        st.session_state["chain_ts_epoch"] = now_ist().timestamp()

# ── Build leg table ───────────────────────────────────────────────────────────
def make_leg(offsets, side, idx):
    spot       = st.session_state.get("nifty_spot_live" if idx=="NIFTY 50" else "sensex_spot_live", SPOT[idx])
    chain      = st.session_state.get("nifty_chain"     if idx=="NIFTY 50" else "sensex_chain",     {})
    _exp_key = "nifty_exp_used" if idx=="NIFTY 50" else "sensex_exp_used"
    _cal_dte = max((parse_exp(st.session_state.get(_exp_key, sel_n_exp if idx=="NIFTY 50" else sel_s_exp)) - date.today()).days, 1)
    iv         = live_iv_from_chain(chain, spot, idx, _cal_dte)  # Calendar DTE for Black-Scholes
    lot        = LOT[idx];    rnd = ROUND[idx]
    cap        = capital_base  # same for both (1.25L default or Dhan total)
    rows = []
    for off in offsets:
        strike = int(round(spot*(1+off)/rnd)*rnd)
        prem = ltp_from_chain(chain, strike, side) if chain else None
        if not prem:
            base = 1267 if idx=="NIFTY 50" else 450
            prem = round(max(5.0, base*max(0.3,1-(abs(off)-0.005)/0.02)*(iv/0.14)/lot), 1)
            src = "~est"
        else:
            src = "live"
        profit  = round(prem*lot, 1)
        ret     = round(profit/cap*100, 1)
        prob    = prob_nd2(spot, strike, iv, dte_adj, side)
        dlt     = delta_bs(spot, strike, iv, dte_adj, side)
        theta   = round(prem*lot/dte_adj, 1)
        vega    = round(-prem*lot*0.15, 1)
        cushion = round(theta/abs(vega), 1) if vega else 0
        score   = comp_score(prob, ret)
        action  = sig_label(score, sig_thresh)
        # Ext.loss: loss if spot moves 0.5% beyond strike
        ext     = round(abs(abs(off)+0.005)*lot*strike, 0)
        rows.append({"Offset":f"{off*100:+.1f}%","Strike":strike,"Premium":prem,"Src":src,
                     "Profit/lot":int(profit),"Capital":cap,"Return%":ret,
                     "Delta":f"{dlt:.4f}","Theta":theta,"Vega":vega,
                     "Prob%":round(prob*100),"Cushion":cushion,
                     "Score":score,"Action":action,"Ext.loss":int(ext)})
    return pd.DataFrame(rows)

def style_leg(df):
    def _apply(col):
        if col.name == "Action":
            return [f"background-color:{sig_color(v)};color:white;font-weight:bold"
                    for v in col]
        if col.name == "Src":
            return ["color:#00cc88" if v=="live" else "color:#888" for v in col]
        return [""]*len(col)
    return df.style.apply(_apply).format(
        {"Premium":"{:.1f}","Profit/lot":"{:,}","Capital":"{:,}",
         "Return%":"{:.1f}","Theta":"{:.1f}","Vega":"{:.1f}","Cushion":"{:.1f}x"},
        subset=["Premium","Profit/lot","Capital","Return%","Theta","Vega","Cushion"])

def render_index(idx):
    chain     = st.session_state.get("nifty_chain" if idx=="NIFTY 50" else "sensex_chain",{})
    exp_used  = st.session_state.get("nifty_exp_used" if idx=="NIFTY 50" else "sensex_exp_used","—")
    spot      = st.session_state.get("nifty_spot_live" if idx=="NIFTY 50" else "sensex_spot_live",SPOT[idx])
    ts        = st.session_state.get("chain_ts","")
    src_lbl   = f"Dhan (fetched {ts})" if chain else "Formula estimate"

    if _IS_MOBILE:
        st.success("✅ **Ready to trade**")
        _detail_popover(
            "Trade details",
            f"**DTE** = **{dte_adj}** trading days to selected expiry. **Data:** {src_lbl}.")
    else:
        st.success(f"Ready to trade | DTE={dte_adj}d | {src_lbl}")
    if chain:
        st.caption(f"Spot: ₹{spot:,.1f} | Expiry: {exp_used} | Rounding: ₹{ROUND[idx]}")

    put_df  = make_leg(PUT_OFFSETS,  "put",  idx)
    call_df = make_leg(CALL_OFFSETS, "call", idx)
    bp = put_df.loc[put_df["Score"].idxmax()]
    bc = call_df.loc[call_df["Score"].idxmax()]

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Best Put",  f"₹{bp['Strike']:,} ({bp['Offset']})", f"Score {bp['Score']} | Prob {bp['Prob%']}%")
    m2.metric("Best Call", f"₹{bc['Strike']:,} ({bc['Offset']})", f"Score {bc['Score']} | Prob {bc['Prob%']}%")
    rec = "Strangle" if bp["Score"]>=sig_thresh and bc["Score"]>=sig_thresh else \
          ("Sell call" if bc["Score"]>=sig_thresh else ("Sell put" if bp["Score"]>=sig_thresh else "Stay out"))
    m3.metric("Recommendation", rec, f"Threshold: {sig_thresh}")
    m4.metric("Best Cushion", f"{bc['Cushion']}x", "≥2x safe | 1-2x watch | <1x risky")

    col_order = ["Offset","Strike","Premium","Src","Profit/lot","Capital","Return%",
                 "Delta","Theta","Vega","Prob%","Cushion","Score","Action","Ext.loss"]
    st.markdown("**PUT LEG**")
    st.dataframe(style_leg(put_df[col_order]), use_container_width=True, hide_index=True)
    st.markdown("**CALL LEG**")
    st.dataframe(style_leg(call_df[col_order]), use_container_width=True, hide_index=True)
    st.caption(
        f"Lot: {LOT[idx]} | Capital: ₹{capital_base:,} ({cap_src}) | Strike rnd: ₹{ROUND[idx]} | "
        f"**Score** = 40%×Prob + 30%×IVP + 30%×Return. Threshold={sig_thresh}"
    )

def top_bar(tab_id=""):
    # Get freshest spot prices: chain (T-0 from fetch) > session LTP > SPOT
    nifty_chain = st.session_state.get("nifty_chain", {})
    sensex_chain = st.session_state.get("sensex_chain", {})

    nifty_spot = (
        st.session_state.get("nifty_spot_live") or  # From chain fetch (most recent)
        st.session_state.get("nifty_ltp_live") or   # From manual/auto LTP refresh
        SPOT["NIFTY 50"]  # Last known good value
    )
    sensex_spot = (
        st.session_state.get("sensex_spot_live") or
        st.session_state.get("sensex_ltp_live") or
        SPOT["SENSEX"]
    )

    # Use calendar days for IV formula (Black-Scholes convention), not trading days
    nifty_cal_dte = max((parse_exp(st.session_state.get("nifty_exp_used", sel_n_exp)) - date.today()).days, 1)
    sensex_cal_dte = max((parse_exp(st.session_state.get("sensex_exp_used", sel_s_exp)) - date.today()).days, 1)
    nifty_iv = live_iv_from_chain(nifty_chain, nifty_spot, "NIFTY 50", nifty_cal_dte)
    sensex_iv = live_iv_from_chain(sensex_chain, sensex_spot, "SENSEX", sensex_cal_dte)

    # Data freshness
    chain_age_mins = (now_ist().timestamp() - st.session_state.get("chain_ts_epoch", 0)) / 60
    chain_ts_str   = st.session_state.get("chain_ts", "—")
    freshness_indicator = "🔴" if chain_age_mins > 5 else "🟢"

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("NIFTY 50",  f"₹{nifty_spot:,.0f}")
    c2.metric("NIFTY IV",  f"{nifty_iv*100:.1f}%")
    c3.metric("SENSEX",    f"₹{sensex_spot:,.0f}")
    c4.metric("SENSEX IV", f"{sensex_iv*100:.1f}%")
    st.info(f"**Markets ready** | DTE {dte_adj} trading days")

    # Chain freshness + inline refresh button (visible on all devices including mobile)
    _cb1, _cb2 = st.columns([5, 1])
    with _cb1:
        if chain_ts_str != "—":
            _age_lbl = f"{chain_age_mins:.0f} min ago" if chain_age_mins >= 1 else "just now"
            st.caption(f"{freshness_indicator} Chain @ {chain_ts_str} ({_age_lbl}) | Auto-refreshes every 5 min or on expiry change")
        else:
            st.caption("⏳ Fetching chain…")
    with _cb2:
        if st.button("🔄 Refresh", key=f"top_bar_refresh_btn_{tab_id}", help="Force refresh chain + IV", type="primary"):
            for k in ["nifty_chain","sensex_chain","nifty_spot_live","sensex_spot_live",
                      "chain_ts","chain_ts_epoch","nifty_ltp_live","sensex_ltp_live"]:
                st.session_state.pop(k, None)
            st.rerun()

# ── Backtest Engine helpers ────────────────────────────────────────────────────
BT_CSV_END = date(2026, 3, 24)

@st.cache_data(show_spinner=False)
def load_bt_df():
    bt_dir = os.path.join(os.path.dirname(__file__), "data")
    p_parquet = os.path.join(bt_dir, "final_merged_output_30m_strike_within_6pct.parquet")

    if os.path.exists(p_parquet):
        df = pd.read_parquet(p_parquet)
        df["timestamp_30m"] = pd.to_datetime(df["timestamp_30m"])
        df["expiry"] = pd.to_datetime(df["expiry"])
    else:
        return pd.DataFrame()

    df["tdate"] = df["timestamp_30m"].dt.date
    df["edate"] = df["expiry"].dt.date
    df["hhmm"]  = df["timestamp_30m"].dt.strftime("%H:%M")
    return df

def bt_expiry_dates_as_date(df):
    """All unique expiry dates as Python `date` (avoids dtype mismatches vs `date_input`)."""
    if df is None or df.empty:
        return set()
    return set(pd.to_datetime(df["edate"]).dt.date)


def bt_expiries_on_or_after(df, trade_d):
    return sorted(e for e in bt_expiry_dates_as_date(df) if e >= trade_d)


def bt_find_expiry(df, d):
    """Nearest expiry on or after trade date (includes same-day expiry sessions)."""
    fut = bt_expiries_on_or_after(df, d)
    return fut[0] if fut else None

def bt_find_expiry_dte2(df, d):
    """First expiry with DTE>=2 from trade date. Falls back to nearest if none found.
    This enforces the DTE>=2 rule for trade entry expiry selection."""
    fut = bt_expiries_on_or_after(df, d)
    for e in fut:
        if effective_dte(d, e) >= 2:
            return e
    return fut[0] if fut else None

def bt_get_spot_at(df, d, hhmm):
    r = df[(df["tdate"]==d) & (df["hhmm"]==hhmm)]
    return float(r["underlying_spot_close"].iloc[0]) if len(r) else None

def bt_get_spot(df, d):
    """Prefer 15:00, then 14:00, then first available."""
    for h in ("15:00", "14:00", "10:00"):
        v = bt_get_spot_at(df, d, h)
        if v is not None: return v
    return None

def live_iv_from_chain(chain, spot, idx, dte_days):
    """Calculate IV from live option chain ATM straddle (DTE≥2 rule).
    Falls back to IV_ANN if chain unavailable or insufficient data."""
    if not chain: return IV_ANN[idx]

    rnd = ROUND[idx]
    atm = int(round(spot/rnd)*rnd)

    # Find prices from chain for ATM calls and puts
    # Use fuzzy key matching (Dhan returns float keys like "23900.0", not "23900")
    oc = chain.get("oc", {})
    atm_data = None
    for k, v in oc.items():
        try:
            if abs(float(k) - atm) < 1:
                atm_data = v
                break
        except (ValueError, TypeError):
            continue

    if atm_data is None: return IV_ANN[idx]

    ce_ltp = atm_data.get("ce", {}).get("last_price")
    pe_ltp = atm_data.get("pe", {}).get("last_price")

    if not ce_ltp or not pe_ltp: return IV_ANN[idx]

    stv = float(ce_ltp) + float(pe_ltp)
    T = dte_days / 365

    if T > 0:
        iv = round(stv / (0.8 * spot * math.sqrt(T)), 4)
        return min(iv, 0.50)  # Cap at 50% for safety
    return IV_ANN[idx]

def bt_iv_straddle(df, d, ed, spot, hhmm="15:00"):
    """
    Calculate IV from ATM straddle using DTE>=2 rule for stability.
    Falls back to nearest expiry if no valid DTE>=2 expiry found.
    """
    rnd = ROUND["NIFTY 50"]
    atm = int(round(spot/rnd)*rnd)

    # NEW: Find first expiry with DTE >= 2 (instead of using provided ed)
    # Get all available expiries from this date
    available_expiries = sorted(df[df["tdate"]==d]["edate"].unique())

    best_ed = None
    for candidate_ed in available_expiries:
        dte = effective_dte(d, candidate_ed)
        if dte >= 2:
            best_ed = candidate_ed
            break

    # Fallback to provided expiry if DTE < 2
    if best_ed is None:
        best_ed = ed

    rows = df[(df["tdate"]==d) & (df["edate"]==best_ed) & (df["hhmm"]==hhmm)]
    ce = rows[(rows["strike_price"]==atm) & (rows["option_type"]=="CE")]["close"]
    pe = rows[(rows["strike_price"]==atm) & (rows["option_type"]=="PE")]["close"]
    if len(ce) and len(pe):
        stv = float(ce.iloc[0]) + float(pe.iloc[0])
        T   = effective_dte(d, best_ed) / 365
        iv  = round(stv / (0.8 * spot * math.sqrt(T)), 4) if T > 0 else IV_ANN["NIFTY 50"]
        return iv, round(stv, 1), atm
    return IV_ANN["NIFTY 50"], None, atm

def bt_prem_at(df, d, ed, strike, otype, hhmm):
    r = df[(df["tdate"]==d) & (df["edate"]==ed) &
           (df["strike_price"]==float(strike)) & (df["option_type"]==otype) &
           (df["hhmm"]==hhmm)]
    return float(r["close"].iloc[0]) if len(r) else None

def bt_get_prem(df, entry_d, exit_d, ed, strike, otype, entry_hhmm="15:00", exit_hhmm="15:00"):
    return bt_prem_at(df, entry_d, ed, strike, otype, entry_hhmm), bt_prem_at(df, exit_d, ed, strike, otype, exit_hhmm)

@st.cache_data(show_spinner=False)
def load_iv_history_csv():
    """Load daily IV history from CSV."""
    bt_dir = os.path.join(os.path.dirname(__file__), "data")
    csv_path = os.path.join(bt_dir, "iv_history_daily.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_vix_history_csv():
    """Load Nifty VIX daily history from CSV."""
    bt_dir = os.path.join(os.path.dirname(__file__), "data")
    csv_path = os.path.join(bt_dir, "nifty_vix_daily.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def bt_gross_pnl_for_legs(bt_df, is_historical, bt_date, exit_date, bt_expiry,
                          bt_entry_hhmm, bt_exit_hhmm, legs_spec, lot,
                          bt_spot_val, chain2, bt_iv_val):
    """Sum of leg P&Ls × lot (gross, before brokerage). Same rules as Tab 2 leg loop."""
    total = 0
    ok = True
    for label, strike, otype, side in legs_spec:
        if is_historical:
            e_p, x_p = bt_get_prem(bt_df, bt_date, exit_date, bt_expiry,
                                   strike, otype, bt_entry_hhmm, bt_exit_hhmm)
            if x_p is None and side == "long" and exit_date == bt_expiry:
                _esp = (bt_get_spot_at(bt_df, exit_date, bt_exit_hhmm)
                        or bt_get_spot(bt_df, exit_date))
                if _esp is not None:
                    x_p = max(0.0, (_esp - strike) if otype == "CE" else (strike - _esp))
        else:
            e_p = ltp_from_chain(chain2, strike,
                                 "call" if otype == "CE" else "put") if chain2 else None
            if not e_p:
                off = abs(strike / bt_spot_val - 1)
                e_p = round(max(5.0, 1267 * max(0.3, 1 - (off - 0.005) / 0.02)
                                * (bt_iv_val / 0.14) / lot), 1)
            x_p = None
        if e_p is not None and x_p is not None:
            if side == "short":
                total += round((e_p - x_p) * lot)
            else:
                total += round((x_p - e_p) * lot)
        else:
            ok = False
    return total, ok


def bt_pick_best_stype_net(bt_df, is_historical, bt_date, exit_date, bt_expiry,
                           bt_entry_hhmm, bt_exit_hhmm, spot, dist_pct, lot, rnd,
                           chain2, iv_val):
    """Pick core strategy with highest net P&L (after ₹40×legs), same exit rules as Tab 2."""
    best_st, best_net = None, None
    for stp in BT_CORE_STYPES:
        legs = bt_build_legs(spot, dist_pct, stp, rnd)
        g, ok = bt_gross_pnl_for_legs(
            bt_df, is_historical, bt_date, exit_date, bt_expiry,
            bt_entry_hhmm, bt_exit_hhmm, legs, lot, spot, chain2, iv_val)
        if not ok:
            continue
        net = g - round(40 * len(legs), 0)
        if best_net is None or net > best_net:
            best_net = net
            best_st = stp
    return best_st, best_net


def bt_default_dist_pct(dte_sel):
    return {"T": 2.0, "T-1": 2.0, "T-2": 3.5, "T-3": 5.0, "T-4": 6.0, "T-5": 6.0}.get(dte_sel, 5.0)


def bt_lut_dte_key(dte_sel):
    """LUT only defines T-4…T-1; T and T-5 map to nearest bucket."""
    if dte_sel == "T":
        return "T-1"
    if dte_sel == "T-5":
        return "T-4"
    return dte_sel


def bt_gamma_dte_key(dte_sel):
    if dte_sel in ("T", "T-1"):
        return "T-1"
    if dte_sel == "T-5":
        return "T-4"
    return dte_sel

def bt_build_legs(spot, dist_pct, stype, rnd):
    """dist_pct as percent (e.g. 5.0 for 5%). 1% buffer between short/long for spreads & IC."""
    X   = dist_pct / 100.0
    buf = 0.01
    pe_s = int(round(spot*(1-X)/rnd)*rnd)
    ce_s = int(round(spot*(1+X)/rnd)*rnd)
    pe_l = int(round(spot*(1-X-buf)/rnd)*rnd)
    ce_l = int(round(spot*(1+X+buf)/rnd)*rnd)
    if stype == "ss":
        return [("Short Put", pe_s, "PE", "short"), ("Short Call", ce_s, "CE", "short")]
    if stype == "ws":
        return [("Long Put", pe_s, "PE", "long"), ("Long Call", ce_s, "CE", "long")]
    if stype == "ic":
        # BUG 3 fix: enforce 200 pt minimum wing width so IC loss is always capped.
        # Long put strike LOWER than short put (further OTM for puts).
        # Long call strike HIGHER than short call (further OTM for calls).
        min_wing_pts = max(200, int(round(spot * buf / rnd)) * rnd)
        pe_l_ic = int(round((pe_s - min_wing_pts) / rnd) * rnd)
        ce_l_ic = int(round((ce_s + min_wing_pts) / rnd) * rnd)
        return [
            ("Short Put (inner)", pe_s,    "PE", "short"),
            ("Short Call (inner)", ce_s,   "CE", "short"),
            ("Long Put (wing)",   pe_l_ic, "PE", "long"),
            ("Long Call (wing)",  ce_l_ic, "CE", "long"),
        ]
    if stype == "bp":
        return [("Short Put", pe_s, "PE", "short"), ("Long Put", pe_l, "PE", "long")]
    if stype == "bc":
        return [("Short Call", ce_s, "CE", "short"), ("Long Call", ce_l, "CE", "long")]
    return [("Short Put", pe_s, "PE", "short"), ("Short Call", ce_s, "CE", "short")]


def val_leg_otm_pct(spot, strike, otype):
    if not spot or spot <= 0:
        return None
    if otype == "PE":
        return round((spot - strike) / spot * 100.0, 2)
    return round((strike - spot) / spot * 100.0, 2)


def val_kite_legs_dataframe(val_spot, dist_pct, strat_name, stype_v, rnd_v, val_exp, lot_v):
    """Per-leg rows: geometry names match bt_build_legs (inner / wing for IC)."""
    legs = bt_build_legs(val_spot, dist_pct, stype_v, rnd_v)
    rows = []
    for lbl, stk, otype, side in legs:
        otm = val_leg_otm_pct(val_spot, float(stk), otype)
        sym = f"NIFTY {val_exp.strftime('%d%b%y').upper()} {int(stk)} {otype}"
        rows.append({
            "Strategy": strat_name,
            "Geometry": lbl,
            "Strike": int(stk),
            "CE/PE": otype,
            "Action": "SELL" if side == "short" else "BUY",
            "% OTM vs spot": otm,
            "Qty / lot": lot_v,
            "NFO hint": sym,
        })
    return pd.DataFrame(rows)


def _kite_secret_str(v):
    """Strip Streamlit/TOML paste noise; empty after strip means missing."""
    if v is None:
        return ""
    return str(v).strip()


def val_kite_live_status():
    """
    Returns (ready, user_hint). user_hint is empty when ready; otherwise explains the fix
    (missing [kite], wrong nesting, enable_live off, empty keys).
    """
    try:
        _ = st.secrets
    except Exception as e:
        return False, (
            f"Secrets are not available (`{e}`). "
            "**Streamlit Cloud:** App → Settings → Secrets. "
            "**Local run:** create `.streamlit/secrets.toml` in the project folder (gitignored)."
        )

    if "kite" not in st.secrets:
        misplaced = ""
        try:
            if _kite_secret_str(st.secrets.get("api_key")) or _kite_secret_str(
                st.secrets.get("access_token")
            ):
                misplaced = (
                    " You have **`api_key` / `access_token` at the top level of Secrets**, "
                    "but this app only reads them **inside `[kite]`** — move them under that header."
                )
        except Exception:
            pass
        return False, (
            "No **`[kite]`** section in Secrets." + misplaced
            + " Use the template below (exact header + three keys)."
        )

    try:
        k = st.secrets["kite"]
    except Exception as e:
        return False, f"Cannot read `st.secrets['kite']`: `{e}`"

    en = k.get("enable_live")
    if isinstance(en, str):
        en_on = en.strip().lower() in ("1", "true", "yes", "on")
    else:
        en_on = bool(en)
    ak = _kite_secret_str(k.get("api_key"))
    at = _kite_secret_str(k.get("access_token"))

    missing = []
    if not en_on:
        missing.append(
            "**`enable_live`** is missing or not true — add `enable_live = true` under `[kite]` "
            "(this flag is required so orders never fire by accident)."
        )
    if not ak:
        missing.append("**`api_key`** is missing or blank under `[kite]`.")
    if not at:
        missing.append("**`access_token`** is missing or blank under `[kite]`.")

    if missing:
        return False, " ".join(missing)

    return True, ""


def val_kite_live_configured():
    ok, _ = val_kite_live_status()
    return ok


def _kite_inst_expiry_date(exp):
    """Normalize Zerodha `instruments()` expiry to datetime.date."""
    if exp is None:
        return None
    if isinstance(exp, date) and not isinstance(exp, datetime):
        return exp
    if isinstance(exp, datetime):
        return exp.date()
    try:
        return pd.to_datetime(exp).date()
    except Exception:
        return None


def _kite_match_nfo_symbol(nfo_list, exp_date, strike, inst_type):
    """
    Find NIFTY index option on NFO matching expiry (date), strike, CE/PE.
    Returns (tradingsymbol, instrument_token, lot_size) or (None, None, 0).
    """
    strike = float(strike)
    inst_type = str(inst_type).upper()
    candidates = []
    for inst in nfo_list:
        ex = inst.get("exchange")
        seg = str(inst.get("segment") or "")
        if ex != "NFO" and not seg.upper().startswith("NFO"):
            continue
        if inst.get("name") != "NIFTY":
            continue
        if str(inst.get("instrument_type", "")).upper() != inst_type:
            continue
        try:
            sk = float(inst.get("strike") or 0)
        except (TypeError, ValueError):
            continue
        if abs(sk - strike) > 0.01:
            continue
        exd = _kite_inst_expiry_date(inst.get("expiry"))
        if exd != exp_date:
            continue
        candidates.append(inst)
    if not candidates:
        return None, None, 0
    candidates.sort(key=lambda x: int(x.get("lot_size") or 999999))
    best = candidates[0]
    return (
        best.get("tradingsymbol"),
        best.get("instrument_token"),
        int(best.get("lot_size") or 0),
    )


def val_kite_try_place_orders(order_records, val_exp_date):
    """
    Place NRML MARKET orders on NFO. Requires `kiteconnect`, Secrets `[kite]`:
    enable_live, api_key, access_token. Resolves `tradingsymbol` via Kite instrument master.
    """
    _k_ok, _k_hint = val_kite_live_status()
    if not _k_ok:
        return False, (
            _k_hint
            + " After editing Secrets, **Save** and **Reboot** the app. "
            "`kiteconnect` must be in **requirements.txt** on Cloud (already in repo — redeploy if needed)."
        )
    try:
        from kiteconnect import KiteConnect
    except ImportError:
        return False, (
            "Python package `kiteconnect` is missing on the server. "
            "Add `kiteconnect>=4.2.0` to **requirements.txt**, commit, and **reboot** the Streamlit Cloud app."
        )
    try:
        ksec = st.secrets["kite"]
        api_key = _kite_secret_str(ksec.get("api_key"))
        access_token = _kite_secret_str(ksec.get("access_token"))
    except Exception as e:
        return False, f"Secrets `[kite]` read error: {e}"

    if not api_key or not access_token:
        return False, (
            "Secrets `[kite]` has empty **api_key** or **access_token** after trimming spaces. "
            "Paste the full values (no leading/trailing blank lines)."
        )

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    try:
        kite.profile()
    except Exception as e:
        return False, (
            "Kite rejected the session (**profile** failed). Usually: **access_token** expired (daily), "
            "or it was generated with a **different** Connect app **api_key** than the one in Secrets, "
            "or a copy-paste error. Regenerate token from the login URL for this api_key and update Secrets. "
            f"Detail: `{e}`"
        )

    try:
        nfo = kite.instruments("NFO")
    except Exception as e:
        return False, f"Could not download NFO instruments (check token / network): {e}"

    placed_ids = []
    for row in order_records:
        strike = int(row["strike"])
        itype = row["instrument_type"]
        tsym, _tok, lot_sz = _kite_match_nfo_symbol(nfo, val_exp_date, strike, itype)
        if not tsym:
            return (
                False,
                f"No NFO contract for **NIFTY** {strike} **{itype}** expiry **{val_exp_date}**. "
                f"Pick the expiry that exists on Kite (weekly series). Partial order IDs: {placed_ids}",
            )
        qty = int(row["quantity"])
        if lot_sz > 0 and qty % lot_sz != 0:
            return (
                False,
                f"Quantity **{qty}** must be a multiple of exchange lot **{lot_sz}** for `{tsym}`. "
                f"Adjust qty in app (NIFTY lot is usually **{lot_sz}**). Placed so far: {placed_ids or 'none'}",
            )
        try:
            oid = kite.place_order(
                variety=KiteConnect.VARIETY_REGULAR,
                exchange="NFO",
                tradingsymbol=tsym,
                transaction_type=(
                    KiteConnect.TRANSACTION_TYPE_SELL
                    if row.get("transaction_type") == "SELL"
                    else KiteConnect.TRANSACTION_TYPE_BUY
                ),
                quantity=int(row["quantity"]),
                order_type=KiteConnect.ORDER_TYPE_MARKET,
                product=KiteConnect.PRODUCT_NRML,
            )
            placed_ids.append(f"{tsym}→{oid}")
        except Exception as e:
            es = str(e).lower()
            hint = ""
            if "api_key" in es or "access_token" in es or "incorrect" in es:
                hint = (
                    " If this mentions api_key/access_token, fix Secrets: same **api_key** + fresh **access_token** "
                    "from today’s login flow; no extra spaces."
                )
            return False, f"Kite rejected order **{tsym}**: `{e}`. Placed so far: {placed_ids or 'none'}{hint}"

    return True, f"Submitted **{len(placed_ids)}** market NRML leg(s): {'; '.join(placed_ids)}"


def bt_next_expiry_live(d):
    """For live dates: Tuesday expiry (current NSE rule)."""
    days = (1 - d.weekday()) % 7 or 7
    exp  = d + timedelta(days=days)
    while exp in NSE_HOLIDAYS or exp.weekday() >= 5:
        exp -= timedelta(days=1)
    return exp

def iv_band(pct):
    if pct < 13: return "<13%"
    if pct < 15: return "13-15%"
    if pct < 18: return "15-18%"
    if pct < 22: return "18-22%"
    return ">22%"

def dte_label(trade_d, expiry_d, dte_days):
    """STEP 01 default from calendar + trading days to Nearest Expiry."""
    if trade_d == expiry_d:
        return "T"
    if dte_days >= 5:
        return "T-5"
    if dte_days >= 4:
        return "T-4"
    if dte_days == 3:
        return "T-3"
    if dte_days == 2:
        return "T-2"
    return "T-1"

BT_LUT = {
  "T-4|<13%|NEUTRAL":  {"s":"Iron Condor",      "st":"ic","win":97.6,"pnl":507,  "dc":0.07,"dp":-0.07,"th":12, "tc":0.76,"ml":-5468},
  "T-4|<13%|BULLISH":  {"s":"Bear Call Spread",  "st":"bc","win":88.4,"pnl":1125, "dc":0.30,"dp":None, "th":20, "tc":1.47,"ml":-7387},
  "T-4|<13%|BEARISH":  {"s":"Bull Put Spread",   "st":"bp","win":88.4,"pnl":1125, "dc":None,"dp":-0.30,"th":20, "tc":1.35,"ml":-7387},
  "T-4|13-15%|NEUTRAL":{"s":"Wide Strangle",     "st":"ws","win":81.3,"pnl":698,  "dc":0.13,"dp":-0.13,"th":20, "tc":1.06,"ml":-33072},
  "T-4|13-15%|BULLISH":{"s":"Bull Put Spread",   "st":"bp","win":72.7,"pnl":-522, "dc":None,"dp":-0.30,"th":30, "tc":1.35,"ml":-10680,"warn":"Marginal edge — half lot only"},
  "T-4|13-15%|BEARISH":{"s":"Bear Call Spread",  "st":"bc","win":54.5,"pnl":-1465,"dc":0.29,"dp":None, "th":30, "tc":1.47,"ml":-7667, "skip":"Win 54%, avg P&L negative. Skip."},
  "T-4|15-18%|NEUTRAL":{"s":"Short Strangle",    "st":"ss","win":83.3,"pnl":1107, "dc":0.17,"dp":-0.17,"th":31, "tc":1.27,"ml":-18093},
  "T-4|15-18%|BULLISH":{"s":"Wide Strangle",     "st":"ws","win":83.3,"pnl":969,  "dc":0.13,"dp":-0.13,"th":26, "tc":1.06,"ml":-13030},
  "T-4|15-18%|BEARISH":{"s":"Wide Strangle",     "st":"ws","win":66.7,"pnl":-500, "dc":0.13,"dp":-0.13,"th":26, "tc":1.06,"ml":-10000,"warn":"Negative avg P&L — size down"},
  "T-4|18-22%|NEUTRAL":{"s":"Wide Strangle",     "st":"ws","win":75.0,"pnl":500,  "dc":0.13,"dp":-0.13,"th":22, "tc":1.06,"ml":-10000},
  "T-4|18-22%|BULLISH":{"s":"Bull Put Spread",   "st":"bp","win":80.0,"pnl":1000, "dc":None,"dp":-0.30,"th":30, "tc":1.35,"ml":-8000},
  "T-4|18-22%|BEARISH":{"s":"Bear Call Spread",  "st":"bc","win":75.0,"pnl":800,  "dc":0.30,"dp":None, "th":28, "tc":1.47,"ml":-9000},
  "T-4|>22%|NEUTRAL":  {"s":"Short Strangle",    "st":"ss","win":100, "pnl":6710, "dc":0.17,"dp":-0.17,"th":41, "tc":1.27,"ml":0},
  "T-4|>22%|BULLISH":  {"s":"Bull Put Spread",   "st":"bp","win":100, "pnl":4048, "dc":None,"dp":-0.30,"th":46, "tc":1.35,"ml":0},
  "T-4|>22%|BEARISH":  {"s":"Bear Call Spread",  "st":"bc","win":100, "pnl":3699, "dc":0.30,"dp":None, "th":45, "tc":1.47,"ml":0},
  "T-3|<13%|NEUTRAL":  {"s":"Wide Strangle",     "st":"ws","win":88.6,"pnl":468,  "dc":0.12,"dp":-0.12,"th":17, "tc":1.29,"ml":-14590},
  "T-3|<13%|BULLISH":  {"s":"Bear Call Spread",  "st":"bc","win":84.1,"pnl":752,  "dc":0.30,"dp":None, "th":24, "tc":1.47,"ml":-5248},
  "T-3|<13%|BEARISH":  {"s":"Bull Put Spread",   "st":"bp","win":84.1,"pnl":752,  "dc":None,"dp":-0.30,"th":24, "tc":1.35,"ml":-5248},
  "T-3|13-15%|NEUTRAL":{"s":"Bull Put Spread",   "st":"bp","win":85.7,"pnl":510,  "dc":None,"dp":-0.30,"th":38, "tc":1.35,"ml":-7332},
  "T-3|13-15%|BULLISH":{"s":"Bull Put Spread",   "st":"bp","win":85.7,"pnl":510,  "dc":None,"dp":-0.30,"th":38, "tc":1.35,"ml":-7332},
  "T-3|13-15%|BEARISH":{"s":"Short Strangle",    "st":"ss","win":57.1,"pnl":-2189,"dc":0.17,"dp":-0.18,"th":34, "tc":1.63,"ml":-12942,"skip":"Win 57%, avg P&L negative. Skip."},
  "T-3|15-18%|NEUTRAL":{"s":"Iron Condor",       "st":"ic","win":92.9,"pnl":246,  "dc":0.07,"dp":-0.07,"th":22, "tc":0.93,"ml":-5491},
  "T-3|15-18%|BULLISH":{"s":"Bear Call Spread",  "st":"bc","win":92.9,"pnl":1111, "dc":0.29,"dp":None, "th":44, "tc":1.47,"ml":-7855},
  "T-3|15-18%|BEARISH":{"s":"Wide Strangle",     "st":"ws","win":85.7,"pnl":1214, "dc":0.13,"dp":-0.13,"th":31, "tc":1.29,"ml":-10617},
  "T-3|18-22%|NEUTRAL":{"s":"Iron Condor",       "st":"ic","win":83.3,"pnl":486,  "dc":0.07,"dp":-0.08,"th":25, "tc":0.93,"ml":-1917},
  "T-3|18-22%|BULLISH":{"s":"Bull Put Spread",   "st":"bp","win":100, "pnl":2564, "dc":None,"dp":-0.29,"th":48, "tc":1.35,"ml":0},
  "T-3|18-22%|BEARISH":{"s":"Wide Strangle",     "st":"ws","win":83.3,"pnl":1409, "dc":0.12,"dp":-0.12,"th":35, "tc":1.29,"ml":-6347},
  "T-3|>22%|NEUTRAL":  {"s":"Short Strangle",    "st":"ss","win":83.3,"pnl":528,  "dc":0.17,"dp":-0.18,"th":58, "tc":1.63,"ml":-31978},
  "T-3|>22%|BULLISH":  {"s":"Bull Put Spread",   "st":"bp","win":100, "pnl":3974, "dc":None,"dp":-0.30,"th":71, "tc":1.35,"ml":0},
  "T-3|>22%|BEARISH":  {"s":"Short Strangle",    "st":"ss","win":83.3,"pnl":528,  "dc":0.17,"dp":-0.18,"th":58, "tc":1.63,"ml":-31978},
  "T-2|<13%|NEUTRAL":  {"s":"Iron Condor",       "st":"ic","win":95.2,"pnl":80,   "dc":0.07,"dp":-0.07,"th":25, "tc":0.93,"ml":-6071},
  "T-2|<13%|BULLISH":  {"s":"Bear Call Spread",  "st":"bc","win":86.5,"pnl":634,  "dc":0.30,"dp":None, "th":45, "tc":1.47,"ml":-5670},
  "T-2|<13%|BEARISH":  {"s":"Wide Strangle",     "st":"ws","win":92.1,"pnl":419,  "dc":0.12,"dp":-0.12,"th":33, "tc":1.29,"ml":-21213},
  "T-2|13-15%|NEUTRAL":{"s":"Wide Strangle",     "st":"ws","win":91.7,"pnl":859,  "dc":0.13,"dp":-0.12,"th":44, "tc":1.29,"ml":-7368},
  "T-2|13-15%|BULLISH":{"s":"Bear Call Spread",  "st":"bc","win":100, "pnl":1106, "dc":0.28,"dp":None, "th":58, "tc":1.47,"ml":0},
  "T-2|13-15%|BEARISH":{"s":"Wide Strangle",     "st":"ws","win":91.7,"pnl":859,  "dc":0.13,"dp":-0.12,"th":44, "tc":1.29,"ml":-7368},
  "T-2|15-18%|NEUTRAL":{"s":"Bull Put Spread",   "st":"bp","win":85.7,"pnl":168,  "dc":None,"dp":-0.30,"th":61, "tc":1.35,"ml":-8263},
  "T-2|15-18%|BULLISH":{"s":"Bull Put Spread",   "st":"bp","win":85.7,"pnl":168,  "dc":None,"dp":-0.30,"th":61, "tc":1.35,"ml":-8263},
  "T-2|15-18%|BEARISH":{"s":"Iron Condor",       "st":"ic","win":78.6,"pnl":-486, "dc":0.07,"dp":-0.08,"th":33, "tc":0.93,"ml":-9296, "warn":"Negative avg. Cautious."},
  "T-2|18-22%|NEUTRAL":{"s":"Short Strangle",    "st":"ss","win":85.7,"pnl":3453, "dc":0.17,"dp":-0.17,"th":101,"tc":1.27,"ml":-5892},
  "T-2|18-22%|BULLISH":{"s":"Short Strangle",    "st":"ss","win":85.7,"pnl":3453, "dc":0.17,"dp":-0.17,"th":101,"tc":1.27,"ml":-5892},
  "T-2|18-22%|BEARISH":{"s":"Wide Strangle",     "st":"ws","win":85.7,"pnl":2362, "dc":0.12,"dp":-0.12,"th":82, "tc":1.29,"ml":-3690},
  "T-2|>22%|NEUTRAL":  {"s":"Short Strangle",    "st":"ss","win":85.7,"pnl":3453, "dc":0.17,"dp":-0.17,"th":101,"tc":1.27,"ml":-5892},
  "T-2|>22%|BULLISH":  {"s":"Bull Put Spread",   "st":"bp","win":100, "pnl":2706, "dc":None,"dp":-0.29,"th":119,"tc":1.35,"ml":0},
  "T-2|>22%|BEARISH":  {"s":"Bear Call Spread",  "st":"bc","win":42.9,"pnl":-1253,"dc":0.30,"dp":None, "th":105,"tc":1.47,"ml":-7118,"skip":"Win 43%, negative P&L. Skip."},
  "T-1|<13%|NEUTRAL":  {"s":"Iron Condor (ONLY)","st":"ic","win":80.0,"pnl":150,  "dc":0.07,"dp":-0.07,"th":30, "tc":1.61,"ml":-3500},
  "T-1|<13%|BULLISH":  {"s":"Iron Condor (ONLY)","st":"ic","win":75.0,"pnl":120,  "dc":0.07,"dp":-0.07,"th":28, "tc":1.61,"ml":-3500},
  "T-1|<13%|BEARISH":  {"s":"Iron Condor (ONLY)","st":"ic","win":75.0,"pnl":120,  "dc":0.07,"dp":-0.07,"th":28, "tc":1.61,"ml":-3500},
  "T-1|13-15%|NEUTRAL":{"s":"Iron Condor (ONLY)","st":"ic","win":78.0,"pnl":100,  "dc":0.07,"dp":-0.07,"th":35, "tc":1.61,"ml":-4000},
  "T-1|13-15%|BULLISH":{"s":"Iron Condor (ONLY)","st":"ic","win":75.0,"pnl":90,   "dc":0.07,"dp":-0.07,"th":33, "tc":1.61,"ml":-4000},
  "T-1|13-15%|BEARISH":{"s":"Iron Condor (ONLY)","st":"ic","win":75.0,"pnl":90,   "dc":0.07,"dp":-0.07,"th":33, "tc":1.61,"ml":-4000},
  "T-1|15-18%|NEUTRAL":{"s":"Iron Condor (ONLY)","st":"ic","win":76.0,"pnl":80,   "dc":0.07,"dp":-0.07,"th":40, "tc":1.61,"ml":-5000},
  "T-1|15-18%|BULLISH":{"s":"Iron Condor (ONLY)","st":"ic","win":72.0,"pnl":70,   "dc":0.07,"dp":-0.07,"th":38, "tc":1.61,"ml":-5000},
  "T-1|15-18%|BEARISH":{"s":"Iron Condor (ONLY)","st":"ic","win":72.0,"pnl":70,   "dc":0.07,"dp":-0.07,"th":38, "tc":1.61,"ml":-5000},
  "T-1|18-22%|NEUTRAL":{"s":"Iron Condor (ONLY)","st":"ic","win":74.0,"pnl":60,   "dc":0.07,"dp":-0.07,"th":45, "tc":1.61,"ml":-6000},
  "T-1|18-22%|BULLISH":{"s":"Iron Condor (ONLY)","st":"ic","win":70.0,"pnl":50,   "dc":0.07,"dp":-0.07,"th":43, "tc":1.61,"ml":-6000},
  "T-1|18-22%|BEARISH":{"s":"Iron Condor (ONLY)","st":"ic","win":70.0,"pnl":50,   "dc":0.07,"dp":-0.07,"th":43, "tc":1.61,"ml":-6000},
  "T-1|>22%|NEUTRAL":  {"s":"Iron Condor (ONLY)","st":"ic","win":72.0,"pnl":40,   "dc":0.07,"dp":-0.07,"th":55, "tc":1.61,"ml":-7000},
  "T-1|>22%|BULLISH":  {"s":"Iron Condor (ONLY)","st":"ic","win":68.0,"pnl":30,   "dc":0.07,"dp":-0.07,"th":53, "tc":1.61,"ml":-7000},
  "T-1|>22%|BEARISH":  {"s":"Iron Condor (ONLY)","st":"ic","win":68.0,"pnl":30,   "dc":0.07,"dp":-0.07,"th":53, "tc":1.61,"ml":-7000},
}

BT_GAMMA = {
  "T-4":{"max":0.0015,"exit":0.0018,"rule":"Roll if gamma exceeds 0.0018"},
  "T-3":{"max":0.0022,"exit":0.0028,"rule":"Roll if gamma exceeds 0.0028 intraday"},
  "T-2":{"max":0.0035,"exit":0.0040,"rule":"Exit if gamma exceeds 0.0040 — no exceptions"},
  "T-1":{"max":0.0055,"exit":0.0060,"rule":"Exit immediately if >0.0060 or spot within 0.5% of short strike"},
}

BT_GP = {  # greek profile per strategy type
  "ss":{"delta":("important","~0.00. Drift >±0.12 = hedge or exit tested side."),
        "gamma":("critical","PRIMARY risk. Unlimited loss both sides. Never exceed DTE max."),
        "theta":("critical","The P&L engine. Must meet min from LUT before entry."),
        "vega": ("important","Short vega. Rising VIX = MTM headwind even if you expire OTM.")},
  "ws":{"delta":("monitor","~0.00. ±0.15 = one side getting tested."),
        "gamma":("critical","Critical at T-2/T-1. Wide strikes buffer but gamma bites near expiry."),
        "theta":("critical","Thin premium — min theta non-negotiable for this width."),
        "vega": ("important","2pt VIX rise = ₹800–1200 cost before any delta move.")},
  "ic":{"delta":("important","Near 0.00. Drift >±0.05 = wing under threat — rebalance."),
        "gamma":("critical","Explodes on BOTH wings near expiry simultaneously. T-1 max 0.0055."),
        "theta":("critical","Only income source. Theta/cap% must meet 0.93% minimum."),
        "vega": ("monitor","Both wings offset vega. Watch only if IV spikes mid-trade.")},
  "bp":{"delta":("critical","Net long delta. Drops below -0.10 = short strike threatened — exit."),
        "gamma":("monitor","Bounded by long put hedge. Watch if spot approaches short strike."),
        "theta":("critical","Your income. Min 20–119 pts/day depending on DTE/IV."),
        "vega": ("low","Spread hedges vega. Not primary concern unless extreme VIX spike.")},
  "bc":{"delta":("critical","Net short delta. Turns positive >+0.05 = short call threatened — exit."),
        "gamma":("monitor","Bounded by long call. Watch at T-2/T-1 on sharp rally."),
        "theta":("critical","Must meet minimum. T-4 >22% IV needs ≥45 pts/day."),
        "vega": ("low","Net vega low. IV crush slightly benefits — short deflates faster.")},
}
_LV = {"critical":"#ff4b4b","important":"#ffa421","monitor":"#1c83e1","low":"#808495"}
_LBG = {"critical":"rgba(255,75,75,0.08)","important":"rgba(255,164,33,0.08)",
        "monitor":"rgba(28,131,225,0.08)","low":"rgba(128,132,149,0.05)"}
_LICO = {"critical":"🔴","important":"🟡","monitor":"🔵","low":"⚪"}

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab_val, tab_iv_analysis, tab3 = st.tabs([
    "📡 Tab 1 — Live Signal",
    "📈 Tab 2 — Backtest Engine",
    "🔬 Tab 3 — Validation Explorer",
    "📊 Tab 4 — IV Analysis",
    "📜 Tab 5 — IV History",
])

# ── TAB 1: Live Signal ────────────────────────────────────────────────────────
with tab1:
    st.markdown("##### Live signal filters")
    sig_thresh = st.number_input(
        "Score threshold", 50, 90, 65, key="sig_thresh",
        help="Composite score SELL / MONITOR / AVOID")

    # ── Auto-refresh LTP + manual refresh button ───────────────────────────────
    if has_tok:
        _refresh_col1, _refresh_col2 = st.columns([3, 1])
        with _refresh_col2:
            if st.button("🔄 Refresh LTP", use_container_width=True, key="refresh_ltp_btn"):
                fresh_ltp = fetch_ltp(tok)
                if fresh_ltp:
                    st.session_state["nifty_ltp_live"] = fresh_ltp["nifty"]
                    st.session_state["sensex_ltp_live"] = fresh_ltp["sensex"]
                    st.session_state["ltp_refresh_ts"] = now_ist().timestamp()
                    st.success(f"✓ LTP updated at {fresh_ltp['ts']}")
                    st.rerun()
                else:
                    st.error("✗ Failed to refresh LTP")

        # Auto-refresh on first load or if data is older than 2 minutes
        _ltp_age = (now_ist().timestamp() - st.session_state.get("ltp_refresh_ts", 0)) / 60
        if st.session_state.get("nifty_ltp_live") is None or _ltp_age > 2:
            fresh_ltp = fetch_ltp(tok)
            if fresh_ltp:
                st.session_state["nifty_ltp_live"] = fresh_ltp["nifty"]
                st.session_state["sensex_ltp_live"] = fresh_ltp["sensex"]
                st.session_state["ltp_refresh_ts"] = now_ist().timestamp()

    top_bar(tab_id="t1")
    st.markdown("---")
    st.subheader("NIFTY 50 — Weekly Options Signal")
    render_index("NIFTY 50")
    st.markdown("---")
    st.subheader("SENSEX — Weekly Options Signal")
    render_index("SENSEX")
    st.markdown("---")

    # Footer: Capital Status
    st.markdown("#### 💰 Capital Status")
    if _funds:
        fa,fb,fc = st.columns(3)
        fa.metric("Available", f"₹{_funds['available']:,.0f}", "from Dhan")
        fb.metric("Used Margin",f"₹{_funds['used']:,.0f}")
        fc.metric("Total",     f"₹{_funds['total']:,.0f}")
    else:
        st.info(f"Capital: ₹{capital_base:,} (mock — enter Dhan token to auto-fill from account)")

    with st.expander("Glossary"):
        st.markdown("""
**Score** = 60% × Prob N(d2) + 40% × min(Return%×25, 100). SELL ≥ threshold, MONITOR ≥50, else AVOID.

**Prob N(d2)** — BS probability option expires worthless. Inputs: spot, strike, IV, r=6.5%, DTE (holidays excluded).

**Delta** — Put: N(d1)−1, Call: N(d1). Magnitude = sensitivity to ₹1 spot move.

**Cushion (Theta/|Vega|)** — IV points needed to wipe one day's Theta. ≥2x safe, 1-2x watch, <1x risky.

**Strike rounding** — Nifty: ₹50, Sensex: ₹100 (BSE standard).

**Ext. loss** — Estimated loss if spot moves 0.5% beyond the strike at expiry.

**DTE** — Trading days to expiry (weekends + NSE holidays excluded).
        """)

# ── TAB 2: Historical Strategy Simulator ─────────────────────────────────────
with tab2:
    top_bar(tab_id="t2")
    st.markdown("---")
    st.subheader("📊 Historical Strategy Simulator (v3)")
    st.caption("Entry bar + strike % slider · ₹1.25L per short leg · IC/spreads +1% long buffer · P&L first, details in expanders")

    bt_df = load_bt_df()

    # Data source footnote
    data_src_note = "**Data source:** 30-min OHLC for NIFTY options (Oct 2024–Mar 2026) | Strikes within 6% of spot | Contains: timestamp, strike, option type (CE/PE), OHLC prices, volume, OI, underlying spot"
    with st.expander("ℹ️ About this backtest data", expanded=False):
        st.caption(data_src_note)

    # ── Section 1: Date & Mode ────────────────────────────────────────────────
    st.markdown("#### 1️⃣ Select Date, Entry & Exit Timing")
    def _sync_val_date_from_bt2():
        st.session_state["val_date"] = st.session_state["bt_date2"]
        st.session_state["iv_analysis_end_date"] = st.session_state["bt_date2"]

    def _sync_val_entry_from_bt2():
        st.session_state["val_entry_hhmm"] = st.session_state["bt_entry_hhmm"]

    def _sync_val_dist_from_bt2():
        st.session_state["val_dist_slider"] = float(st.session_state["bt_dist_slider"])

    _bt_bar_opts = ["14:00", "10:00", "15:00"]
    _bt_bar0 = st.session_state.get("bt_entry_hhmm", "14:00")
    if _bt_bar0 not in _bt_bar_opts:
        _bt_bar0 = "14:00"

    s1c1, s1c2, s1c3 = st.columns(3)
    with s1c1:
        _bt_default = st.session_state.get("bt_date2", date.today())
        bt_date = st.date_input(
            "Trade Date", value=_bt_default,
            min_value=date(2024, 9, 23), max_value=date.today(),
            key="bt_date2", on_change=_sync_val_date_from_bt2)
    with s1c2:
        bt_entry_hhmm = st.selectbox(
            "Entry bar (CSV 30m)",
            _bt_bar_opts,
            index=_bt_bar_opts.index(_bt_bar0),
            format_func=lambda x: {"14:00": "Closing — 14:00",
                                   "10:00": "Opening — 10:00",
                                   "15:00": "EOD — 15:00"}[x],
            key="bt_entry_hhmm",
            on_change=_sync_val_entry_from_bt2,
            help="Premiums at this timestamp on trade date. Exit always uses 15:00 on exit date.")
    with s1c3:
        _exit_opts = [
            "T Close (expiry day close)",
            "T-1 Close (day before expiry)",
        ]
        if "bt2_exit_sel" not in st.session_state:
            st.session_state["bt2_exit_sel"] = _exit_opts[0]
        bt_exit_mode = st.selectbox(
            "Exit Timing",
            _exit_opts,
            key="bt2_exit_sel",
            help="Default: hold through expiry-day 15:00 close.",
        )
    exit_is_T1   = "T-1" in bt_exit_mode
    bt_exit_hhmm = "15:00"
    is_historical = (not bt_df.empty) and (bt_date <= BT_CSV_END)

    bt_expiry_from_picker = None
    _csv_expiry_dates = bt_expiry_dates_as_date(bt_df)
    _on_expiry_session = is_historical and bt_date in _csv_expiry_dates
    if _on_expiry_session:
        _pick = bt_expiries_on_or_after(bt_df, bt_date)[:2]
        if _pick:
            st.info(
                "📅 **Expiry session** — this trade date is a listed expiry in the CSV. "
                "Pick **same day (0DTE)** or **next weekly expiry**; metrics and P&L use your choice."
            )

            def _fmt_expiry_choice(ed):
                if ed == bt_date:
                    return f"{ed} — same day (0DTE)"
                return f"{ed} — next expiry ({ed.strftime('%A')})"

            bt_expiry_from_picker = st.selectbox(
                "Nearest expiry (choose series)",
                _pick,
                format_func=_fmt_expiry_choice,
                key=f"bt_expiry_pick_{bt_date}",
                help="Same day = options expiring that session. Next = following week’s expiry in the file.",
            )

    if is_historical:
        st.success("📁 **Historical — real P&L** (CSV)")
        _detail_popover(
            "Historical mode",
            "Premiums from the backtest CSV at your **entry bar** (10:00 / 14:00 / 15:00) and **exit at 15:00** "
            "on the chosen exit date (T close or T-1). **Brokerage** in Tab 2 / Validation = **₹40 × leg count**.")
    else:
        st.warning("📡 **Live — estimated P&L**")
        _detail_popover(
            "Live mode",
            "Trade date is **after** the CSV window. Entry from **Dhan chain** (or model estimate); exit is not fully "
            "priced from history — treat numbers as indicative.")

    # Snapshot
    bt_valid = True
    bt_expiry = None
    if is_historical:
        _sp = bt_get_spot_at(bt_df, bt_date, bt_entry_hhmm)
        if _sp is None:
            _sp = bt_get_spot(bt_df, bt_date)
        if _sp is None:
            st.error("No data for this date — market may have been closed. Try a nearby trading day.")
            bt_valid = False
        else:
            bt_spot_val = _sp
            if bt_expiry_from_picker is not None:
                bt_expiry = bt_expiry_from_picker
            else:
                bt_expiry = bt_find_expiry_dte2(bt_df, bt_date)  # DTE>=2 enforced
            if bt_expiry is None:
                st.error("Could not find a future expiry in data for this date.")
                bt_valid = False
            else:
                bt_iv_val, bt_straddle_val, bt_atm = bt_iv_straddle(
                    bt_df, bt_date, bt_expiry, bt_spot_val, bt_entry_hhmm)
    else:
        # Live mode: use Dhan chain for real IV, not hardcoded fallback
        _live_chain = st.session_state.get("nifty_chain", {})
        bt_spot_val = (st.session_state.get("nifty_spot_live") or
                       st.session_state.get("nifty_ltp_live") or SPOT["NIFTY 50"])
        bt_expiry       = bt_next_expiry_live(bt_date)
        _exp_used = st.session_state.get("nifty_exp_used", sel_n_exp)
        _cal_dte  = max((parse_exp(_exp_used) - date.today()).days, 1)
        bt_iv_val       = live_iv_from_chain(_live_chain, bt_spot_val, "NIFTY 50", _cal_dte)
        bt_straddle_val = None
        bt_atm          = int(round(bt_spot_val / ROUND["NIFTY 50"]) * ROUND["NIFTY 50"])

    if bt_valid:
        bt_iv_pct  = round(bt_iv_val * 100, 1)
        bt_dte_val = effective_dte(bt_date, bt_expiry)
        t1_exit    = bt_expiry - timedelta(days=1)
        while t1_exit.weekday() >= 5 or t1_exit in NSE_HOLIDAYS:
            t1_exit -= timedelta(days=1)
        exit_date = t1_exit if exit_is_T1 else bt_expiry

        sm1, sm2, sm3, sm4, sm5 = st.columns(5)
        sm1.metric("Nifty Spot", f"₹{bt_spot_val:,.0f}",
                   f"● {bt_entry_hhmm}" if is_historical else "~ live")
        sm2.metric("Nearest Expiry", bt_expiry.strftime("%Y-%m-%d"),
                   bt_expiry.strftime("%A"))
        _dte_caption = (
            "same calendar day as expiry (0DTE session)" if bt_date == bt_expiry
            else f"{bt_dte_val} trading days to expiry")
        sm3.metric("DTE", _dte_caption)
        sm4.metric("ATM IV%", f"{bt_iv_pct}%",
                   "from ATM straddle" if is_historical else "~ live")
        sm5.metric("ATM Straddle",
                   f"₹{bt_straddle_val:.0f}" if bt_straddle_val else "~ live",
                   "actual CE+PE" if is_historical else "est.")

        st.markdown("---")

        # ── Section 2: 3-Step Selection ───────────────────────────────────────
        st.markdown("#### 2️⃣ 3-Step Strategy Selection")
        auto_dte = dte_label(bt_date, bt_expiry, bt_dte_val)
        auto_iv  = iv_band(bt_iv_pct)
        _sync_sig = (str(bt_date), str(bt_expiry), auto_dte, auto_iv)
        if st.session_state.get("bt_step_sync_sig") != _sync_sig:
            st.session_state["bt_step_sync_sig"] = _sync_sig
            st.session_state["bt_dte_sel"] = auto_dte
            st.session_state["bt_iv_sel"] = auto_iv

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.caption("STEP 01 — DTE · auto from **Nearest Expiry** + calendar")
            dte_opts = ["T-5", "T-4", "T-3", "T-2", "T-1", "T"]
            st.caption(
                "**T** = trade date **is** expiry · **T-5** = 5+ trading days out · "
                "**T-1**…**T-4** = buckets toward expiry")
            _dte_cur = st.session_state.get("bt_dte_sel", auto_dte)
            if _dte_cur not in dte_opts:
                _dte_cur = auto_dte
            bt_dte_sel = st.radio(
                "DTE", dte_opts, index=dte_opts.index(_dte_cur),
                horizontal=True, key="bt_dte_sel", label_visibility="collapsed")
            if bt_dte_sel != auto_dte:
                st.caption(f"⚡ Overriding auto ({auto_dte})")
        with sc2:
            st.caption("STEP 02 — IV Band · auto-set from **ATM IV %** above")
            iv_opts  = ["<13%","13-15%","15-18%","18-22%",">22%"]
            _iv_cur = st.session_state.get("bt_iv_sel", auto_iv)
            if _iv_cur not in iv_opts:
                _iv_cur = auto_iv
            bt_iv_sel = st.radio(
                "IV Band", iv_opts, index=iv_opts.index(_iv_cur),
                horizontal=True, key="bt_iv_sel", label_visibility="collapsed")
            if bt_iv_sel != auto_iv:
                st.caption(f"⚡ Overriding auto ({auto_iv})")
        with sc3:
            st.caption("STEP 03 — Market Trend · your read on that date")
            bt_trend = st.radio("Trend", ["NEUTRAL","BULLISH","BEARISH"],
                                horizontal=True, key="bt_trend",
                                label_visibility="collapsed")
            with st.expander("ℹ How is this used in live trading?"):
                st.markdown("""
**Check before entry:** India VIX direction · prev close vs 20-DMA · FII futures positioning

**How it tilts the strategy:**
- Neutral → symmetric premium (Strangle / IC)
- Bullish → favour Put side (Bull Put Spread)
- Bearish → favour Call side (Bear Call Spread)

**In this simulator:** your trend choice reflects what you _believed_ the market would do on that date — use it to compare your read vs what actually happened in the P&L result tab.""")

        st.markdown("---")

        # ── Section 3: Strategy + dynamic strikes + P&L (v3) ───────────────────
        st.markdown("#### 3️⃣ Strategy Recommendation & P&L")
        lut_key = f"{bt_lut_dte_key(bt_dte_sel)}|{bt_iv_sel}|{bt_trend}"
        lut = BT_LUT.get(lut_key)
        gam = BT_GAMMA.get(bt_gamma_dte_key(bt_dte_sel), BT_GAMMA["T-4"])
        rnd = ROUND["NIFTY 50"]
        lot = LOT["NIFTY 50"]
        cap_leg = CAP["NIFTY 50"]  # ₹1,25,000 per short leg

        if not lut:
            st.error(f"No LUT entry for `{lut_key}`")
        else:
            skip_flag = lut.get("skip")
            warn_flag = lut.get("warn")
            if bt_iv_sel == "<13%":
                st.caption(
                    "📉 **<13% IV** — the **LUT** usually prefers spreads/condors (thinner premiums). "
                    "**Short Strangle is still calculated below** when the LUT pick isn’t SS, "
                    "so you can compare side-by-side.")
            if skip_flag:
                st.error(f"⊘ **No Trade — Skip This Setup**\n\n{skip_flag}\n\n"
                         f"Win rate: {lut['win']}% · Avg P&L: ₹{lut['pnl']:+,}")
            else:
                if warn_flag:
                    st.warning(f"⚠️ {warn_flag}")

                _strat_display = lut_strategy_display(lut)
                _strat_base    = lut_strategy_base(lut)
                lut_st = lut["st"]

                ddef = bt_default_dist_pct(bt_dte_sel)
                if "bt_dist_slider" not in st.session_state:
                    st.session_state["bt_dist_slider"] = float(ddef)
                _ps = float(st.session_state["bt_dist_slider"])
                if not (1.0 <= _ps <= 7.0):
                    st.session_state["bt_dist_slider"] = float(ddef)

                st.markdown(
                    """
<style>
/* Prominent strike-% slider (Tab 2) */
div[data-testid="stSlider"] { padding: 14px 8px 22px !important; }
div[data-testid="stSlider"] label p {
  font-size: 1.05rem !important; font-weight: 600 !important; line-height: 1.35 !important;
}
div[data-testid="stSlider"] [data-baseweb="slider"] { height: 10px !important; }
div[data-testid="stSlider"] [role="slider"] {
  width: 22px !important; height: 22px !important; box-shadow: 0 0 0 3px rgba(255,75,75,0.35);
}
</style>
""",
                    unsafe_allow_html=True)
                dist_pct = st.slider(
                    "Strike distance from spot (% OTM) — shorts symmetric; "
                    "spreads / IC add **+1%** buffer between short & long",
                    min_value=1.0, max_value=7.0, step=0.5, key="bt_dist_slider",
                    on_change=_sync_val_dist_from_bt2,
                    help="Synced with Validation Explorer. Same session key `bt_dist_slider`. "
                         "Defaults: T / T-1 → 2% · T-2 → 3.5% · T-3 → 5% · T-4 / T-5 → 6% (first visit only).")
                # Do not assign st.session_state["bt_dist_slider"] after the widget (Streamlit rule).

                chain2_bt = st.session_state.get("nifty_chain", {})
                if is_historical:
                    best_st, _best_net = bt_pick_best_stype_net(
                        bt_df, True, bt_date, exit_date, bt_expiry,
                        bt_entry_hhmm, bt_exit_hhmm, bt_spot_val, dist_pct, lot, rnd,
                        chain2_bt, bt_iv_val)
                    stype = best_st if best_st else lut_st
                else:
                    stype = lut_st

                _sim_lbl = BT_STYPE_LABELS.get(stype, stype.upper())
                kc1, kc2, kc3, kc4 = st.columns(4)
                kc1.metric(
                    "P&L simulates",
                    _sim_lbl,
                    "↔ Validation best-net" if stype == lut_st else f"LUT: {_strat_display}",
                )
                kc2.metric("LUT win rate", f"{lut['win']}%", "for this bucket")
                kc3.metric("LUT avg P&L", f"₹{lut['pnl']:+,}", "historical table")
                kc4.metric("LUT max loss",
                           f"₹{lut['ml']:,}" if lut["ml"] else "None in dataset")
                if is_historical and stype != lut_st:
                    if _IS_MOBILE:
                        st.success("🎯 **Simulator = Validation best-net** at this % OTM")
                    else:
                        st.success(
                            f"🎯 **Aligned with Validation Explorer:** highest **net** P&L at **{dist_pct:.1f}%** OTM "
                            f"is **{_sim_lbl}** (Tab 2 exit rules). LUT still suggests **{_strat_display}**.")
                    _detail_popover(
                        "LUT vs simulator vs Validation",
                        f"**This run:** best **net** P&L at **{dist_pct:.1f}%** OTM → **{_sim_lbl}**; LUT row → **{_strat_display}**.\n\n"
                        "**LUT** = map from DTE × IV band × trend (sample stats).\n\n"
                        "**Tab 2 rank** = same CSV + **your exit timing** (T or T-1 close).\n\n"
                        "**Validation table** = exit **15:00 on expiry** for every leg — can differ slightly from Tab 2 "
                        "if you use **T-1 exit** here.")
                st.caption(
                    f"Theta/Capital: **{lut['tc']}%/day** (per ₹1,25,000 short leg) · "
                    f"Min theta: **{lut['th']} pts/day** · Gamma max: **{gam['max']}** · LUT key `{lut_key}` "
                    f"(step DTE **{bt_dte_sel}** → bucket `{bt_lut_dte_key(bt_dte_sel)}`)")
                legs_spec = bt_build_legs(bt_spot_val, dist_pct, stype, rnd)
                dc, dp = lut.get("dc"), lut.get("dp")
                if stype == "ss":
                    strike_note = (f"Short Strangle: short PUT −{dist_pct:.1f}% / short CALL +{dist_pct:.1f}% "
                                   f"(LUT ref Δ PE {dp} / CE {dc})")
                elif stype == "ws":
                    strike_note = (f"Long Strangle (wide): long PUT −{dist_pct:.1f}% / long CALL +{dist_pct:.1f}% "
                                   f"(LUT ref short-Δ targets PE {dp} / CE {dc} — debit strategy)")
                elif stype == "ic":
                    _ic_pe_s = next((s for _, s, o, d in legs_spec if o == "PE" and d == "short"), None)
                    _ic_ce_s = next((s for _, s, o, d in legs_spec if o == "CE" and d == "short"), None)
                    _ic_lp = next((s for _, s, o, d in legs_spec if o == "PE" and d == "long"), None)
                    _ic_lc = next((s for _, s, o, d in legs_spec if o == "CE" and d == "long"), None)
                    def _ru(x):
                        return f"₹{x:,}" if x is not None else "—"
                    strike_note = (
                        f"Iron Condor: shorts ±{dist_pct:.1f}% (PE {_ru(_ic_pe_s)}/CE {_ru(_ic_ce_s)}), "
                        f"wings PE {_ru(_ic_lp)}/CE {_ru(_ic_lc)} (+1% buffer vs shorts) · LUT ref Δ PE {dp} / CE {dc}")
                elif stype == "bp":
                    strike_note = (f"Bull Put Spread: short PUT −{dist_pct:.1f}%, long PUT −{dist_pct+1:.1f}% "
                                   f"(1% buffer) · LUT ref Δ {dp}")
                elif stype == "bc":
                    strike_note = (f"Bear Call Spread: short CALL +{dist_pct:.1f}%, long CALL +{dist_pct+1:.1f}% "
                                   f"(1% buffer) · LUT ref Δ {dc}")
                else:
                    strike_note = ""
                st.info(strike_note)

                # ── Actual P&L first ───────────────────────────────────────────
                st.markdown("##### 💰 Actual P&L Result")
                st.caption(
                    f"Entry **{bt_date}** `{bt_entry_hhmm}` · Exit **{exit_date}** `{bt_exit_hhmm}` · "
                    f"{bt_exit_mode}")
                rows_data = []
                _s = {"pnl": 0, "has_exit": True, "entry_debit": 0.0}
                n_short = sum(1 for t in legs_spec if t[3] == "short")

                for label, strike, otype, side in legs_spec:
                    if is_historical:
                        e_p, x_p = bt_get_prem(bt_df, bt_date, exit_date, bt_expiry,
                                               strike, otype, bt_entry_hhmm, bt_exit_hhmm)
                        src = "● real"
                        # BUG 3 fix: long wing missing in CSV at expiry → use intrinsic value.
                        # Prevents IC loss exceeding SS loss (IC has defined/capped max loss).
                        if x_p is None and side == "long" and exit_date == bt_expiry:
                            _esp = (bt_get_spot_at(bt_df, exit_date, bt_exit_hhmm)
                                    or bt_get_spot(bt_df, exit_date))
                            if _esp is not None:
                                x_p = max(0.0, (_esp - strike) if otype == "CE" else (strike - _esp))
                                src = "● intrinsic"
                    else:
                        chain2 = st.session_state.get("nifty_chain", {})
                        e_p = ltp_from_chain(chain2, strike,
                                             "call" if otype == "CE" else "put") if chain2 else None
                        if not e_p:
                            off = abs(strike / bt_spot_val - 1)
                            e_p = round(max(5.0, 1267 * max(0.3, 1 - (off - 0.005) / 0.02)
                                            * (bt_iv_val / 0.14) / lot), 1)
                        x_p = None
                        src = "~ est"
                    if e_p is not None and x_p is not None:
                        if side == "short":
                            leg_pnl = round((e_p - x_p) * lot)
                        else:
                            leg_pnl = round((x_p - e_p) * lot)
                        _s["pnl"] += leg_pnl
                    else:
                        leg_pnl = None
                        _s["has_exit"] = False
                    if e_p is not None and side == "long":
                        _s["entry_debit"] += e_p * lot
                    rows_data.append({
                        "Leg": label,
                        "Strike": int(strike),
                        "Type": otype,
                        "Side": side[:1].upper(),
                        "Entry Prem": float(e_p) if e_p is not None else np.nan,
                        "Exit Prem": float(x_p) if x_p is not None else np.nan,
                        "P&L / Lot": float(leg_pnl) if leg_pnl is not None else np.nan,
                        "Cap / leg": float(cap_leg) if side == "short" else np.nan,
                        "Src": src,
                    })

                total_pnl = _s["pnl"]
                has_exit = _s["has_exit"]
                entry_debit = _s["entry_debit"]
                total_cap = cap_leg * n_short if n_short else entry_debit
                cap_basis_lbl = "Total short margin (1.25L × shorts)" if n_short else "Premium paid (long legs × lot)"
                ret_pct = (total_pnl / total_cap * 100) if total_cap and has_exit else None

                if rows_data:
                    df_legs = pd.DataFrame(rows_data)
                    _leg_cols = [
                        "Leg", "Strike", "Type", "Side",
                        "Entry Prem", "Exit Prem", "P&L / Lot", "Cap / leg", "Src",
                    ]
                    df_legs = df_legs[_leg_cols]

                    if stype == "ic":
                        st.caption(
                            "**Iron condor geometry:** inner **shorts** sit closer to spot than outer **long** wings. "
                            "Calls: inner strike **below** wing strike — inner call is less OTM so entry premium is "
                            "typically **higher** than the wing. Puts: inner strike **above** wing strike — same idea. "
                            "Premiums are from the CSV at your entry/exit timestamps."
                        )

                    def _style_bt_legs(df):
                        """Dark table + accent colors (matches earlier Tab 2 look)."""
                        tbl = [
                            dict(selector="", props=[
                                ("background-color", "#0d1117"),
                                ("color", "#e6edf3"),
                            ]),
                            dict(selector="thead th", props=[
                                ("background-color", "#1e2a3d"),
                                ("color", "#f0f6fc"),
                                ("font-weight", "600"),
                                ("padding", "10px 12px"),
                                ("border-bottom", "2px solid #30363d"),
                            ]),
                            dict(selector="tbody td", props=[
                                ("color", "#e6edf3"),
                                ("padding", "8px 12px"),
                                ("border-bottom", "1px solid #21262d"),
                            ]),
                            dict(selector="tbody tr:nth-child(even) td", props=[
                                ("background-color", "#121922"),
                            ]),
                            dict(selector="tbody tr:nth-child(odd) td", props=[
                                ("background-color", "#0d1117"),
                            ]),
                        ]

                        def _cell_colors(col):
                            if col.name == "P&L / Lot":
                                out = []
                                for v in col:
                                    if pd.isna(v):
                                        out.append("")
                                    elif v > 0:
                                        out.append("color: #21c55d; font-weight: 600")
                                    elif v < 0:
                                        out.append("color: #ef4444; font-weight: 600")
                                    else:
                                        out.append("color: #e6edf3")
                                return out
                            if col.name == "Type":
                                return [
                                    "color: #3b82f6; font-weight: 600" if v == "CE" else
                                    "color: #ef4444; font-weight: 600" if v == "PE" else ""
                                    for v in col
                                ]
                            if col.name == "Src":
                                return [
                                    "color: #21c55d" if "real" in str(v) else "color: #6b7280"
                                    for v in col
                                ]
                            return [""] * len(col)

                        fmt = {
                            "Strike": lambda v: f"₹{int(v):,}" if pd.notna(v) else "—",
                            "Entry Prem": lambda v: f"₹{v:.1f}" if pd.notna(v) else "—",
                            "Exit Prem": lambda v: f"₹{v:.1f}" if pd.notna(v) else "—",
                            "P&L / Lot": lambda v: f"₹{v:+,.0f}" if pd.notna(v) else "—",
                            "Cap / leg": lambda v: f"₹{v:,.0f}" if pd.notna(v) else "—",
                        }
                        return (
                            df.style
                            .set_table_styles(tbl)
                            .apply(_cell_colors, axis=0)
                            .format(fmt, na_rep="—")
                        )

                    with st.container(border=True):
                        st.caption(
                            f"Leg breakdown · entry `{bt_entry_hhmm}` · exit `{bt_exit_hhmm}` · × {lot} qty/lot"
                        )
                        st.dataframe(
                            _style_bt_legs(df_legs),
                            hide_index=True,
                            use_container_width=True,
                            height=min(420, 72 + len(df_legs) * 36),
                            column_order=_leg_cols,
                        )

                    brokerage_bt = round(40 * len(legs_spec), 0)
                    net_bt = (total_pnl - brokerage_bt) if has_exit else None
                    ret_pct_net = (
                        (net_bt / total_cap * 100) if total_cap and net_bt is not None else None)
                    r1, r2, r3, r4, r5 = st.columns(5)
                    if is_historical and has_exit:
                        outcome = (
                            "✅ net profit" if net_bt is not None and net_bt > 0 else
                            "❌ net loss" if net_bt is not None and net_bt < 0 else "—")
                        r1.metric("📊 Gross P&L", f"₹{total_pnl:+,.0f}", "before brokerage")
                        r2.metric("🏦 Brokerage", f"₹{brokerage_bt:,.0f}",
                                  f"{len(legs_spec)} legs × ₹40")
                        r3.metric("💰 Net P&L", f"₹{net_bt:+,.0f}" if net_bt is not None else "—", outcome)
                        r4.metric("Return on capital", f"{ret_pct_net:+.2f}%" if ret_pct_net is not None else "—",
                                  cap_basis_lbl if n_short else "vs premium basis")
                        diff = round((net_bt - lut["pnl"]) / max(abs(lut["pnl"]), 1) * 100) if net_bt is not None else 0
                        r5.metric("vs LUT avg", f"{diff:+.0f}%",
                                  "above avg" if diff > 0 else "below avg")
                    else:
                        r1.metric("📊 Gross P&L", "~ pending" if not has_exit else f"₹{total_pnl:+,.0f}")
                        r2.metric("🏦 Brokerage", f"₹{brokerage_bt:,.0f}")
                        r3.metric("💰 Net P&L", "—" if not has_exit else f"₹{net_bt:+,.0f}")
                        r4.metric("Return %", "—" if not has_exit else (
                            f"{ret_pct_net:+.2f}%" if ret_pct_net is not None else "—"))
                        r5.metric("LUT Avg", f"₹{lut['pnl']:+,}")

                    if (
                        bt_iv_sel == "<13%"
                        and stype != "ss"
                        and is_historical
                        and has_exit
                    ):
                        legs_ss = bt_build_legs(bt_spot_val, dist_pct, "ss", rnd)
                        chain2 = st.session_state.get("nifty_chain", {})
                        gross_ss, ok_ss = bt_gross_pnl_for_legs(
                            bt_df, is_historical, bt_date, exit_date, bt_expiry,
                            bt_entry_hhmm, bt_exit_hhmm, legs_ss, lot,
                            bt_spot_val, chain2, bt_iv_val)
                        brok_ss = round(40 * len(legs_ss), 0)
                        net_ss = (gross_ss - brok_ss) if ok_ss else None
                        st.markdown("---")
                        st.markdown("##### ⚡ Short Strangle — same % OTM (comparison)")
                        st.caption(
                            "LUT pick is **not** SS in this <13% band — this block shows how **Short Strangle** "
                            "would have performed at the **same strike %** for context.")
                        ss1, ss2, ss3 = st.columns(3)
                        if ok_ss:
                            ss1.metric("📊 Gross P&L", f"₹{gross_ss:+,.0f}")
                            ss2.metric("🏦 Brokerage", f"₹{brok_ss:,.0f}")
                            tag = "✅" if net_ss > 0 else "❌" if net_ss < 0 else "➖"
                            ss3.metric("💰 Net P&L", f"₹{net_ss:+,.0f}", tag)
                        else:
                            st.warning("⚠️ Could not price every SS leg from CSV for this date.")
                else:
                    st.info("No legs to display for this strategy.")

                # ── Entry params (expander) ────────────────────────────────────
                with st.expander("📋 Entry Params (Do's & Don'ts)", expanded=False):
                    st.markdown(
                        "LUT fields **`dc` / `dp`** are **option delta targets** (roughly −0.30…+0.30), "
                        "**not** % away from spot. Pick strikes on the live chain whose delta is near those values; "
                        "the **P&L table above** uses the **% OTM slider** vs spot, not these deltas.")
                    if dc is not None:
                        st.markdown(f"**LUT call-side Δ ref (short-strangle context):** `{dc:+}`")
                    if dp is not None:
                        st.markdown(f"**LUT put-side Δ ref (short-strangle context):** `{dp:+}`")
                    st.markdown(
                        f"**Theta check:** Combined short-leg theta ≥ **{lut['th']} pts/day** "
                        f"({lut['tc']}% of **₹1,25,000 per short leg**). Sum theta × {lot} for each short.")
                    st.markdown(
                        f"**Gamma limit:** Short gamma ≤ **{gam['max']}**. {gam['rule']}.")
                    st.markdown("---")
                    col_do, col_dont = st.columns(2)
                    with col_do:
                        st.markdown("**✅ DO**")
                        st.markdown(
                            "- Enter **after 10:30 AM** — let opening auction settle\n"
                            "- Take **50–70% profit** if available before expiry\n"
                            "- Verify theta meets LUT minimum before placing\n"
                            "- Use ATM straddle IV from NSE chain (not individual leg IV)")
                    with col_dont:
                        st.markdown("**❌ DON'T**")
                        st.markdown(
                            f"- Never exceed gamma exit threshold (`{gam['exit']}`)\n"
                            "- Don't hold through RBI / Budget / election surprises\n"
                            "- Avoid entry in the last 15 min of session\n" +
                            ("- **Never use debit spreads in >22% IV** — IV mean reversion destroys long vega"
                             if bt_iv_sel == ">22%" else
                             "- Don't ignore rising VIX trend before entry"))

                # ── Greeks (expander) ──────────────────────────────────────────
                with st.expander("📐 Greeks — ranked by criticality", expanded=False):
                    gp = BT_GP.get(stype, BT_GP["ss"])
                    st.info(
                        f"Greeks for **{BT_STYPE_LABELS.get(stype, stype)}** (structure used in P&L). "
                        f"Check IN ORDER — first two are go/no-go gates.")
                    order = sorted(gp.items(),
                                   key=lambda x: {"critical": 0, "important": 1, "monitor": 2, "low": 3}[x[1][0]])
                    vals = {
                        "delta": f"Net Δ target: {'≈ 0.00' if dc and dp else (f'~+{dc}' if dc else f'~{dp}')}",
                        "gamma": f"Max: {gam['max']} · Exit: {gam['exit']}",
                        "theta": f"Min: {lut['th']} pts/day · {lut['tc']}% of ₹1,25,000 / short leg / day",
                        "vega": "Watch India VIX trend before and during trade",
                    }
                    gsym = {"delta": "Δ", "gamma": "Γ", "theta": "Θ", "vega": "V"}
                    gc1, gc2 = st.columns(2)
                    for i, (gname, (level, note)) in enumerate(order):
                        col = gc1 if i % 2 == 0 else gc2
                        with col:
                            col.markdown(
                                f'<div style="border:1px solid {_LV[level]};border-radius:8px;'
                                f'padding:12px 14px;margin-bottom:10px;background:{_LBG[level]}">'
                                f'<span style="font-size:11px;font-weight:600;color:{_LV[level]}">'
                                f'{_LICO[level]} {level.upper()} — {gsym[gname]} {gname.upper()}</span><br>'
                                f'<span style="font-size:13px;font-weight:500;">{vals[gname]}</span><br>'
                                f'<span style="font-size:11px;color:#808495;">{note}</span></div>',
                                unsafe_allow_html=True)

    with st.expander("Glossary"):
        st.markdown("""
**LUT (Look-up Table)** — 60-entry map from backtest (Oct 2024–Mar 2026, ~1,840 trades). Maps `DTE | IV band | Trend` → recommended strategy + win rate + avg P&L + theta/gamma rules.

**Historical Mode** — Date ≤ Mar 24 2026: entry premium at chosen **entry bar** (10:00 / 14:00 / 15:00); exit at **15:00** on exit date.

**Live Mode** — Date > Mar 24 2026: entry from DhanHQ chain (or estimated). Exit pending until expiry.

**Strike distance** — Slider **1–7%** OTM; defaults: T / T-1 → 2%, T-2 → 3.5%, T-3 → 5%, T-4 / T-5 → 6%. Spreads & Iron Condor use **+1%** further OTM for long legs.

**Capital** — **₹1,25,000 per short leg** (NIFTY). Strangle/IC (2 shorts) = ₹2,50,000. Bull put / Bear call (1 short) = ₹1,25,000. Return % = P&L ÷ total short capital.

**Expiry rule** — Before Sep 2025: Thursday. From Sep 2025 onward: Tuesday (NSE rule change).

**DTE label (STEP 01)** — **T** = trade date equals **Nearest Expiry** (0DTE). **T-5** = 5+ trading days. **T-4** = 4d, **T-3** = 3d, **T-2** = 2d, **T-1** = 1d. LUT rows use T-4…T-1 only; **T** / **T-5** map to **T-1** / **T-4** buckets for win rate & P&L lookup.

**IV Band** — ATM straddle IV derived using Brenner-Subrahmanyam approximation from actual CE+PE close prices.

**Theta/Capital** — Daily theta ÷ **₹1,25,000 per short leg**. Must meet LUT minimum.

**Gamma limit** — Maximum short-leg gamma before forced exit. Accelerates sharply near expiry — the primary risk for naked short strategies.
        """)

# ── TAB VAL: Validation Explorer ───────────────────────────────────────
with tab_val:
    top_bar(tab_id="t3")
    st.markdown("---")
    st.subheader("🔬 Validation Explorer")
    st.caption(
        "Five core strategies at one **% OTM** — slider uses session key **`bt_dist_slider`** (same as Tab 2). "
        "Exit here: **15:00 on expiry** for all legs. **Brokerage** = ₹40 × leg count.")

    if "val_date" not in st.session_state:
        st.session_state["val_date"] = st.session_state.get("bt_date2", date(2025, 10, 14))
    if "val_entry_hhmm" not in st.session_state:
        st.session_state["val_entry_hhmm"] = st.session_state.get("bt_entry_hhmm", "14:00")
    if "val_dist_slider" not in st.session_state:
        st.session_state["val_dist_slider"] = float(
            st.session_state.get("bt_dist_slider", 3.5))

    def _sync_bt_date_from_val():
        st.session_state["bt_date2"] = st.session_state["val_date"]
        st.session_state["iv_analysis_end_date"] = st.session_state["val_date"]

    def _sync_bt_entry_from_val():
        st.session_state["bt_entry_hhmm"] = st.session_state["val_entry_hhmm"]

    def _sync_bt_dist_from_val():
        st.session_state["bt_dist_slider"] = float(st.session_state["val_dist_slider"])

    _val_date_min = date(2024, 9, 23)
    _val_date_max = date.today()
    _vd = st.session_state.get("val_date", date.today())
    if isinstance(_vd, date):
        if _vd < _val_date_min:
            st.session_state["val_date"] = _val_date_min
        elif _vd > _val_date_max:
            st.session_state["val_date"] = _val_date_max
    else:
        st.session_state["val_date"] = date.today()

    _val_bt_df = load_bt_df()

    vc1, vc2, vc3 = st.columns([2, 1, 1])
    with vc1:
        val_date = st.date_input(
            "Entry Date",
            min_value=_val_date_min,
            max_value=_val_date_max,
            key="val_date", on_change=_sync_bt_date_from_val,
            help=f"Same range as Tab 2. CSV history ends **{BT_CSV_END}** — after that, spot/IV may be unavailable.")
        _val_bar_opts = ["14:00", "10:00", "15:00"]
        _ve0 = st.session_state.get("val_entry_hhmm", "14:00")
        if _ve0 not in _val_bar_opts:
            _ve0 = "14:00"
        val_entry_hhmm = st.selectbox(
            "Entry bar",
            _val_bar_opts,
            index=_val_bar_opts.index(_ve0),
            format_func=lambda x: {"14:00": "Closing — 14:00",
                                   "10:00": "Opening — 10:00",
                                   "15:00": "EOD — 15:00"}[x],
            key="val_entry_hhmm",
            on_change=_sync_bt_entry_from_val,
        )
        st.caption(
            "Synced with Tab 2 — changing date or entry bar here updates Tab 2 and vice versa "
            "(via on_change).")
        val_dist_pct = st.slider(
            "Strike distance from spot (% OTM)",
            1.0, 7.0,
            key="val_dist_slider",
            step=0.5,
            on_change=_sync_bt_dist_from_val,
            help="Synced with Tab 2 strike slider.",
        )
        # Do not assign st.session_state["bt_dist_slider"] here (widget-key rule); sync is via on_change.
    with vc2:
        val_capital_pct = st.slider(
            "Capital %", 1, 7, 3, key="val_cap_pct",
            help="% of ₹1,20,000 deployed per trade")
        val_capital_rs = int(round(120_000 * val_capital_pct / 100))
        st.caption(f"= **₹{val_capital_rs:,}** of ₹1,20,000")
    with vc3:
        val_trend = st.radio(
            "Trend override", ["NEUTRAL", "BULLISH", "BEARISH"],
            horizontal=False, key="val_trend")

    show_profitable_only = st.toggle(
        "Show profitable strategies only", value=False, key="val_profitable_only")

    if val_date > BT_CSV_END:
        st.info(
            f"📅 **Entry date after CSV end ({BT_CSV_END})** — Validation uses historical file through that date only; "
            f"expect “no data” below unless the feed is extended.")

    if _val_bt_df.empty:
        st.warning("No historical CSV data. Validation Explorer requires the backtest CSV.")
    else:
        _vsp = (bt_get_spot_at(_val_bt_df, val_date, val_entry_hhmm)
                or bt_get_spot(_val_bt_df, val_date))
        if _vsp is None:
            _vsp = st.session_state.get("nifty_spot_live") or SPOT.get("NIFTY 50")
        if _vsp is None:
            st.error(
                "No spot — use a CSV trading day, or set **Dhan token** + **Fetch Live Chain** for Nifty LTP.")
        else:
            val_spot = float(_vsp)
            val_exp = bt_find_expiry(_val_bt_df, val_date)
            if val_exp is None:
                _exs = st.session_state.get("nifty_exp_used") or st.session_state.get("nifty_exp")
                if isinstance(_exs, str) and _exs and _exs != "—":
                    val_exp = parse_exp(_exs)
            if val_exp is None:
                val_exp = bt_next_expiry_live(val_date)

            _csv_spot = (bt_get_spot_at(_val_bt_df, val_date, val_entry_hhmm)
                         or bt_get_spot(_val_bt_df, val_date))
            if _csv_spot is None:
                st.info(
                    "📡 **Spot from live feed** (no CSV row for this date) — geometry below is valid; "
                    "P&L may be **missing** without CSV premiums.")
            if bt_find_expiry(_val_bt_df, val_date) is None:
                st.caption(
                    f"📅 **Expiry** from sidebar **Nifty Exp** or next weekly rule → **{val_exp}**.")

            val_dte_days = effective_dte(val_date, val_exp)
            val_iv_val, _, _vatm = bt_iv_straddle(
                _val_bt_df, val_date, val_exp, val_spot, val_entry_hhmm)
            # If bt_iv_straddle returned fallback (no historical data), use live Dhan IV
            if val_iv_val == IV_ANN["NIFTY 50"]:
                _vchain = st.session_state.get("nifty_chain", {})
                _vspot  = (st.session_state.get("nifty_spot_live") or val_spot)
                _vexp   = st.session_state.get("nifty_exp_used", sel_n_exp)
                _vcaldte = max((parse_exp(_vexp) - date.today()).days, 1)
                _live_iv = live_iv_from_chain(_vchain, _vspot, "NIFTY 50", _vcaldte)
                if _live_iv != IV_ANN["NIFTY 50"]:
                    val_iv_val = _live_iv
            val_iv_pct  = round(val_iv_val * 100, 1)
            val_dte_lbl = dte_label(val_date, val_exp, val_dte_days)
            val_iv_band = iv_band(val_iv_pct)

            mi1, mi2, mi3, mi4, mi5 = st.columns(5)
            mi1.metric("Spot",   f"₹{val_spot:,.0f}")
            mi2.metric("Expiry", val_exp.strftime("%Y-%m-%d"))
            mi3.metric("DTE",    val_dte_lbl, f"{val_dte_days} trading days")
            mi4.metric("IV%",    f"{val_iv_pct}%", val_iv_band)
            mi5.metric("Trend",  val_trend)
            st.markdown("---")

            STRAT_TYPES = [
                ("Short Strangle",    "ss", val_dist_pct),
                ("Wide Strangle",     "ws", val_dist_pct),
                ("Iron Condor",       "ic", val_dist_pct),
                ("Bull Put Spread",   "bp", val_dist_pct),
                ("Bear Call Spread",  "bc", val_dist_pct),
            ]

            rnd_v = ROUND["NIFTY 50"]
            lot_v = LOT["NIFTY 50"]

            _strike_parts = [
                val_kite_legs_dataframe(val_spot, d, n, t, rnd_v, val_exp, lot_v)
                for n, t, d in STRAT_TYPES]
            _strike_all_df = pd.concat(_strike_parts, ignore_index=True)
            with st.expander(
                    "📍 **Strike layout — all strategies** (IC inner shorts + wings · SS/WS/BP/BC legs · Kite)",
                    expanded=True):
                st.caption(
                    f"**Spot** ₹{val_spot:,.0f} · **Expiry** {val_exp} · **{val_dist_pct:.1f}%** OTM vs spot on shorts "
                    f"(spreads / IC add **+1%** wing buffer). **Geometry** column matches engine / Tab 2.")
                st.dataframe(
                    _strike_all_df,
                    use_container_width=True,
                    hide_index=True,
                    height=min(520, 60 + len(_strike_all_df) * 34),
                )

            lut_dte_k    = bt_lut_dte_key(val_dte_lbl)
            lut_rec_key  = f"{lut_dte_k}|{val_iv_band}|{val_trend}"
            lut_rec      = BT_LUT.get(lut_rec_key)
            lut_rec_base = lut_strategy_base(lut_rec) if lut_rec else ""

            _vexp_spot = (bt_get_spot_at(_val_bt_df, val_exp, "15:00")
                          or bt_get_spot(_val_bt_df, val_exp))

            rows_val = []
            for strat_name, stype_v, dist_v in STRAT_TYPES:
                legs_v = bt_build_legs(val_spot, dist_v, stype_v, rnd_v)
                pnl_total, pnl_ok = 0, True
                ce_short, pe_short = None, None
                ce_any, pe_any = None, None
                for _lbl, _stk, _otype, _side in legs_v:
                    if _otype == "CE":
                        ce_any = _stk
                    if _otype == "PE":
                        pe_any = _stk
                    e_p = bt_prem_at(
                        _val_bt_df, val_date, val_exp, _stk, _otype, val_entry_hhmm)
                    x_p = bt_prem_at(
                        _val_bt_df, val_exp, val_exp, _stk, _otype, "15:00")
                    if x_p is None and _side == "long" and _vexp_spot is not None:
                        x_p = max(0.0, (_vexp_spot - _stk) if _otype == "CE" else (_stk - _vexp_spot))
                    if e_p is None or x_p is None:
                        pnl_ok = False
                        break
                    if _side == "short":
                        pnl_total += round((e_p - x_p) * lot_v)
                        if _otype == "CE":
                            ce_short = _stk
                        if _otype == "PE":
                            pe_short = _stk
                    else:
                        pnl_total += round((x_p - e_p) * lot_v)
                brokerage = round(40 * len(legs_v), 0)
                net_pnl   = (pnl_total - brokerage) if pnl_ok else None
                rows_val.append({
                    "Strategy":   strat_name,
                    "Type":       stype_v.upper(),
                    "Dist%":      dist_v,
                    "CE Strike":  ce_short if ce_short is not None else ce_any,
                    "PE Strike":  pe_short if pe_short is not None else pe_any,
                    "Gross P&L":  round(pnl_total, 0) if pnl_ok else None,
                    "Brokerage":  brokerage if pnl_ok else None,
                    "Net P&L":    net_pnl,
                    "Data":       "✅ real" if pnl_ok else "⚠️ missing",
                })
            df_val = pd.DataFrame(rows_val)

            _ss_p = df_val.loc[(df_val["Type"] == "SS") & (df_val["Dist%"] == val_dist_pct), "Net P&L"]
            _ic_p = df_val.loc[(df_val["Type"] == "IC") & (df_val["Dist%"] == val_dist_pct), "Net P&L"]
            viol_ic = False
            if not _ss_p.empty and not _ic_p.empty:
                try:
                    sv, iv = float(_ss_p.values[0]), float(_ic_p.values[0])
                    if sv < 0 and iv < sv:
                        viol_ic = True
                except Exception:
                    pass

            if val_iv_band == "<13%":
                st.caption(
                    "📉 **<13% IV** — premiums are thin; **Short Strangle still appears** in the table "
                    "below for comparison with spreads/condors.")

            st.markdown(
                f"#### All strategies — Entry {val_date} `{val_entry_hhmm}` | Expiry {val_exp} "
                f"| {val_dte_lbl} | IV {val_iv_pct}%")
            if lut_rec:
                st.success(
                    f"🏆 LUT Rec `{lut_rec_key}`: **{lut_strategy_display(lut_rec)}**")
                st.caption(
                    "SS appears as LUT rec only for DTE **T-2 / T-3 / T-4** + **IV ≥15%** + "
                    "**NEUTRAL / BEARISH**. Pick a T-2 or T-3 date with **IV 15–18%+** to see it in the LUT.")

            if show_profitable_only:
                df_val = df_val[
                    df_val["Net P&L"].apply(
                        lambda v: v is not None
                        and not (isinstance(v, float) and np.isnan(float(v)))
                        and float(v) > 0)]

            def _badge(row):
                sn, t = row["Strategy"], row["Type"]
                b = ""
                if viol_ic and t == "IC":
                    b += " ⚠️IC>SS"
                if lut_rec and t == lut_rec.get("st", "").upper():
                    if norm_strategy_name(sn) == lut_rec_base:
                        b += " 🏆LUT"
                return sn + b

            df_disp = df_val.copy()
            df_disp["Strategy"] = df_disp.apply(_badge, axis=1)

            show_cols = [
                "Strategy", "Type", "Dist%", "CE Strike", "PE Strike",
                "Gross P&L", "Brokerage", "Net P&L", "Data",
            ]
            _disp = df_disp[show_cols].copy()

            def _pnl_color(s):
                out = []
                for v in s:
                    try:
                        fv = float(v)
                        if np.isnan(fv):
                            out.append("")
                        elif fv > 0:
                            out.append("background-color: rgba(0,200,150,0.18); color: #6ee7b7; font-weight: 600")
                        elif fv < 0:
                            out.append("background-color: rgba(255,77,77,0.15); color: #fca5a5; font-weight: 600")
                        else:
                            out.append("color: #e5e7eb")
                    except (TypeError, ValueError):
                        out.append("")
                return out

            def _ru_fmt(v):
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    return "—"
                try:
                    return f"₹{float(v):+,.0f}"
                except (TypeError, ValueError):
                    return "—"

            def _ru_plain(v):
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    return "—"
                try:
                    return f"₹{float(v):,.0f}"
                except (TypeError, ValueError):
                    return "—"

            _styled = (
                _disp.style
                .apply(_pnl_color, subset=["Gross P&L", "Net P&L"], axis=0)
                .format({
                    "Gross P&L": lambda x: _ru_fmt(x),
                    "Brokerage": lambda x: _ru_plain(x),
                    "Net P&L": lambda x: _ru_fmt(x),
                    "CE Strike": lambda x: f"₹{int(x):,}" if x is not None and not (isinstance(x, float) and np.isnan(x)) else "—",
                    "PE Strike": lambda x: f"₹{int(x):,}" if x is not None and not (isinstance(x, float) and np.isnan(x)) else "—",
                    "Dist%": lambda x: f"{x:.1f}%" if x is not None and not (isinstance(x, float) and np.isnan(x)) else "—",
                }, na_rep="—")
            )

            with st.container(border=True):
                st.markdown("**📋 Strategy results** — Gross → Brokerage → **Net** (green / red = profit / loss)")
                st.dataframe(
                    _styled,
                    use_container_width=True,
                    hide_index=True,
                    height=min(520, 76 + len(_disp) * 40),
                )

            if viol_ic:
                st.markdown(
                    '<span style="background:#E08000;color:#fff;padding:3px 10px;'
                    'border-radius:12px;font-size:12px;font-weight:700">'
                    '🟠 IC&gt;SS LOSS VIOLATION — IC loss exceeded SS loss. '
                    'Long wing exit data was missing in CSV; intrinsic value fallback applied.</span>',
                    unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("#### 🛒 Kite Connect — legs & API confirmation")
            st.caption(
                "Pick one strategy for **Zerodha** basket. **`tradingsymbol`** must match Kite’s NFO master "
                "(instrument CSV). **No HTTP call** runs until you tick confirm and press submit.")
            _kite_names = [r["Strategy"] for r in rows_val]
            if not _kite_names:
                _kite_names = ["—"]
            _kite_sel = st.selectbox("Strategy to push", _kite_names, key="val_kite_sel")
            _kite_row = next((r for r in rows_val if r["Strategy"] == _kite_sel), None)
            if _kite_row:
                _kst = _kite_row["Type"].lower()
                _kdist = float(_kite_row["Dist%"])
                _kl = bt_build_legs(val_spot, _kdist, _kst, rnd_v)
                kite_geom = val_kite_legs_dataframe(
                    val_spot, _kdist, _kite_sel, _kst, rnd_v, val_exp, lot_v)
                st.markdown(
                    f"**{_kite_sel}** · Entry **{val_date}** `{val_entry_hhmm}` · Expiry **{val_exp}** · "
                    f"Capital context **₹{val_capital_rs:,}** ({val_capital_pct}% of ₹1,20,000)")
                st.dataframe(
                    kite_geom,
                    use_container_width=True,
                    hide_index=True,
                    height=min(320, 52 + len(kite_geom) * 36),
                )
                kite_api_rows = []
                for lb, stk, ot, si in _kl:
                    _sym_hint = f"NIFTY {val_exp.strftime('%d%b%y').upper()} {int(stk)} {ot}"
                    kite_api_rows.append({
                        "exchange": "NFO",
                        "tradingsymbol": _sym_hint.replace(" ", ""),
                        "symbol_human": _sym_hint,
                        "geometry_note": lb,
                        "strike": int(stk),
                        "instrument_type": ot,
                        "transaction_type": "SELL" if si == "short" else "BUY",
                        "order_type": "MARKET",
                        "product": "NRML",
                        "quantity": int(lot_v),
                        "variety": "regular",
                    })
                kite_payload = {"orders": kite_api_rows, "remarks": "Verify tradingsymbol vs Kite instrument dump."}
                _live, _live_hint = val_kite_live_status()
                if not _live and _live_hint:
                    st.warning(_live_hint)
                    with st.expander("Copy-paste Secrets template (`[kite]` block)", expanded=True):
                        st.code(
                            "[kite]\n"
                            "enable_live = true\n"
                            'api_key = "paste_your_kite_connect_api_key"\n'
                            'access_token = "paste_todays_access_token"\n',
                            language="toml",
                        )
                        st.markdown(
                            "- **Cloud:** App menu → Settings → Secrets → paste the block → Save → Reboot app.\n"
                            "- **Local:** Save as `.streamlit/secrets.toml` next to `app.py` (do not commit).\n"
                            "- Keys must sit **under** `[kite]` — not at the top of the file."
                        )
                c_yes, c_api = st.columns([2, 1])
                with c_yes:
                    _kite_ok = st.checkbox(
                        "✅ I confirm strikes, expiry, **NRML**, SELL/BUY, qty, and market risk.",
                        value=False,
                        key="val_kite_user_confirm",
                    )
                with c_api:
                    st.caption("**Live API**" + (" ✅ ready" if _live else " ⛔ off"))

                if st.button(
                        "Submit to Kite API",
                        type="primary",
                        disabled=not _kite_ok,
                        key="val_kite_api_btn"):
                    _placed, _msg = val_kite_try_place_orders(kite_api_rows, val_exp)
                    if _placed:
                        st.success(_msg)
                    else:
                        st.warning(_msg)
                    st.json(kite_payload)

                if st.button("Show JSON payload only (no API call)", key="val_kite_json_btn"):
                    st.code(json.dumps(kite_payload, indent=2), language="json")

# ── IV ANALYSIS TAB ────────────────────────────────────────────────────────────
with tab_iv_analysis:
    top_bar(tab_id="t4")
    st.markdown("---")
    st.subheader("📊 IV & IVP Trend Analysis (DTE≥2 Rule)")

    # ── Date picker: default to today ──────────────────────────────────────────
    def _sync_trade_date_from_iv():
        st.session_state["bt_date2"] = st.session_state["iv_analysis_end_date"]
        st.session_state["val_date"] = st.session_state["iv_analysis_end_date"]

    _iv_col_date, _iv_col_days, _ = st.columns([2, 1, 3])
    with _iv_col_date:
        _iv_default = st.session_state.get("iv_analysis_end_date",
                                            st.session_state.get("bt_date2", date.today()))
        iv_end_date = st.date_input("End date (shows 30 days ending here)",
                                     value=_iv_default, key="iv_analysis_end_date",
                                     on_change=_sync_trade_date_from_iv)
    with _iv_col_days:
        iv_window = st.number_input("Days", min_value=5, max_value=90, value=30,
                                     step=1, key="iv_window")

    BT_DATA_END = date(2026, 3, 24)  # Last date in parquet

    # ── Cached function: compute IV window from parquet ─────────────────────────
    @st.cache_data(show_spinner=False)
    def compute_iv_window(end_d, n_days):
        """Compute daily IV for n_days ending at end_d using parquet data."""
        df = load_bt_df()
        if df.empty:
            return pd.DataFrame()
        all_dates = sorted(df["tdate"].unique())
        # Get dates up to and including end_d
        eligible = [d for d in all_dates if d <= end_d]
        selected = eligible[-n_days:] if len(eligible) >= n_days else eligible
        rows = []
        for d in selected:
            avail_exp = sorted(df[df["tdate"]==d]["edate"].unique())
            best_ed = next((e for e in avail_exp if effective_dte(d, e) >= 2), None)
            if best_ed is None:
                best_ed = avail_exp[0] if avail_exp else None
            if best_ed is None:
                continue
            spot = bt_get_spot(df, d)
            if spot is None:
                continue
            iv_val, straddle, atm = bt_iv_straddle(df, d, best_ed, spot)
            dte_days = effective_dte(d, best_ed)
            rows.append({"date": d, "iv": round(iv_val*100, 2), "spot": round(spot, 2),
                         "atm_strike": atm, "expiry": str(best_ed),
                         "dte": dte_days, "straddle": straddle or 0})
        return pd.DataFrame(rows)

    # ── Determine data sources for the requested window ─────────────────────────
    hist_end = min(iv_end_date, BT_DATA_END)
    hist_start = hist_end - timedelta(days=iv_window * 2)  # extra buffer for trading day gaps

    try:
        with st.spinner("Computing IV series..."):
            iv_hist_df = compute_iv_window(hist_end, iv_window)

        # ── Inject today's live IV from Dhan chain if end_date >= today ──────────
        live_row = None
        if iv_end_date >= date.today():
            _lchain = st.session_state.get("nifty_chain", {})
            _lspot  = (st.session_state.get("nifty_spot_live") or
                       st.session_state.get("nifty_ltp_live") or SPOT["NIFTY 50"])
            _lexp   = st.session_state.get("nifty_exp_used", sel_n_exp)
            _lcaldte = max((parse_exp(_lexp) - date.today()).days, 1)
            _live_iv = live_iv_from_chain(_lchain, _lspot, "NIFTY 50", _lcaldte)
            if _lchain and _live_iv != IV_ANN["NIFTY 50"]:
                rnd = ROUND["NIFTY 50"]
                _latm = int(round(_lspot/rnd)*rnd)
                # Look up straddle from chain
                _oc = _lchain.get("oc", {})
                _ce = _pe = 0
                for k, v in _oc.items():
                    try:
                        if abs(float(k) - _latm) < 1:
                            _ce = float(v.get("ce",{}).get("last_price",0) or 0)
                            _pe = float(v.get("pe",{}).get("last_price",0) or 0)
                            break
                    except: pass
                live_row = {"date": date.today(), "iv": round(_live_iv*100, 2),
                            "spot": round(_lspot, 2), "atm_strike": _latm,
                            "expiry": _lexp, "dte": _lcaldte,
                            "straddle": round(_ce+_pe, 1)}
            elif not _lchain:
                st.info("💡 Enter Dhan token in sidebar to show today's live IV in this chart.")

        # ── Combine historical + live row ─────────────────────────────────────────
        if live_row and (iv_hist_df.empty or iv_hist_df["date"].max() < date.today()):
            iv_combined = pd.concat([iv_hist_df,
                                     pd.DataFrame([live_row])], ignore_index=True)
        else:
            iv_combined = iv_hist_df.copy()

        if iv_combined.empty:
            st.warning("No IV data for the selected date range.")
        else:
            # ── Live IV banner (today) ────────────────────────────────────────────
            if live_row:
                st.success(f"🔴 **Live IV today ({date.today()}):** {live_row['iv']:.1f}%  "
                           f"| Spot ₹{live_row['spot']:,.0f}  | ATM {live_row['atm_strike']}  "
                           f"| Straddle ₹{live_row['straddle']:.1f}  | DTE {live_row['dte']} calendar days")
            elif iv_end_date > BT_DATA_END:
                st.warning(f"⚠️ Data gap: parquet ends {BT_DATA_END}. "
                           f"Enter Dhan token to show live IV for dates after {BT_DATA_END}.")

            # ── Metrics row ───────────────────────────────────────────────────────
            latest = iv_combined.iloc[-1]
            _mean  = iv_combined["iv"].mean()
            _std   = iv_combined["iv"].std()
            _zscore = (latest["iv"] - _mean) / _std if _std > 0 else 0
            _pct_rank = (iv_combined["iv"] < latest["iv"]).mean() * 100

            m1, m2, m3, m4 = st.columns(4)
            src_lbl = "Live (Dhan)" if (live_row and latest["date"] == date.today()) else f"Parquet ({latest['date']})"
            m1.metric("Latest IV", f"{latest['iv']:.1f}%", f"{src_lbl}")
            m2.metric(f"{len(iv_combined)}-Day Mean", f"{_mean:.1f}%",
                      f"Median: {iv_combined['iv'].median():.1f}%")
            m3.metric("Z-Score ①", f"{_zscore:.2f}σ", f"Pctile: {_pct_rank:.0f}%")
            m4.metric("Range ②", f"{iv_combined['iv'].min():.1f}% – {iv_combined['iv'].max():.1f}%",
                      f"Std: {_std:.2f}%")

            st.caption(
                "① **Z-Score** = (Latest IV − Mean) ÷ Std Dev over the window. "
                "Interpretation: 0 = average | >+1σ = elevated | >+2σ = high | <−1σ = suppressed. "
                "Useful to gauge if current IV is cheap or expensive vs recent history.  \n"
                "② **Range** = Lowest to Highest IV seen in the window. "
                "Wide range = volatile IV regime (e.g. event-driven spikes). "
                "Narrow range = stable/low-vol environment."
            )

            # ── Excel Download ───────────────────────────────────────────────────────
            dl_col1, dl_col2, dl_col3 = st.columns([1, 3, 1])
            with dl_col1:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    disp_copy = disp.copy()
                    disp_copy.to_excel(writer, index=False, sheet_name="IV Trend")
                    if not vix_hist.empty:
                        vix_hist.to_excel(writer, index=False, sheet_name="VIX")
                excel_buffer.seek(0)
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_buffer.getvalue(),
                    file_name=f"IV_Analysis_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            # ── Charts ────────────────────────────────────────────────────────────
            st.markdown(f"**IV % Trend — last {len(iv_combined)} trading days (DTE≥2 rule)**")

            # Load VIX data if available
            vix_hist = load_vix_history_csv()
            iv_combined_vix = iv_combined.copy()

            if not vix_hist.empty:
                # Merge with VIX data
                vix_window = vix_hist[vix_hist["Date"].isin(iv_combined["date"].tolist())].copy()
                if not vix_window.empty:
                    iv_combined_vix = iv_combined.merge(
                        vix_window.rename(columns={"Date": "date", "NIFTY VIX": "vix"})[["date", "vix"]],
                        on="date", how="left"
                    )

            chart_df = iv_combined_vix.copy()
            chart_df["date_str"] = chart_df["date"].astype(str)

            # Plot IV and VIX side-by-side if VIX data exists
            if "vix" in chart_df.columns and chart_df["vix"].notna().any():
                col_iv, col_vix = st.columns(2)
                with col_iv:
                    st.markdown("**ATM Straddle IV %**")
                    st.line_chart(chart_df.set_index("date_str")[["iv"]], use_container_width=True)
                with col_vix:
                    st.markdown("**Nifty VIX (Volatility Index)**")
                    st.line_chart(chart_df.set_index("date_str")[["vix"]], use_container_width=True, color="#FF6B6B")
            else:
                st.line_chart(chart_df.set_index("date_str")[["iv"]], use_container_width=True)
                if vix_hist.empty:
                    st.caption("💡 VIX data not yet populated. Run daily_iv_updater.py to fetch Nifty VIX.")

            # IVP from full history file
            bt_dir = os.path.join(os.path.dirname(__file__), "data")
            ivp_csv_path = os.path.join(bt_dir, "iv_impact_analysis_with_ivp.csv")
            if os.path.exists(ivp_csv_path):
                ivp_df = pd.read_csv(ivp_csv_path)
                ivp_df["date"] = pd.to_datetime(ivp_df["date"]).dt.date
                ivp_window = ivp_df[ivp_df["date"].isin(iv_combined["date"].tolist())].copy()
                if not ivp_window.empty:
                    st.markdown("**IVP (252-day percentile)**")
                    ivp_window["date_str"] = ivp_window["date"].astype(str)
                    st.line_chart(ivp_window.set_index("date_str")[["new_ivp"]],
                                  use_container_width=True)

            # ── Detail table ──────────────────────────────────────────────────────
            st.markdown("**Daily Breakdown**")
            disp = iv_combined.copy()
            disp.columns = ["Date","IV %","Spot","ATM Strike","Expiry","DTE","Straddle"]
            # Mark live row
            disp["Source"] = disp["Date"].apply(
                lambda d: "🔴 Live" if live_row and d == date.today() else "📁 Parquet")
            st.dataframe(disp[["Date","Source","IV %","Straddle","Spot","ATM Strike","DTE","Expiry"]],
                         use_container_width=True, hide_index=True)

            st.info("**Formula:** IV = Straddle / (0.8 × Spot × √(DTE/365))  |  "
                    "DTE≥2 rule: skips 0DTE/T-1 expiries  |  "
                    "IVP = 252-day rolling percentile")

    except Exception as e:
        st.error(f"Error in IV Analysis: {e}")

# ── TAB 3: IV History ─────────────────────────────────────────────────────────
with tab3:
    top_bar(tab_id="t5")
    st.markdown("---")
    st.subheader("📊 IV & Option Chain — Expiry Wise")
    tok3 = st.session_state.get("dhan_tok","")

    def chain_to_df(chain, spot_default, band=4.5):
        spot = chain.get("last_price", spot_default)
        rows = []
        for k,v in chain.get("oc",{}).items():
            s = float(k)
            if not (spot*(1-band/100) <= s <= spot*(1+band/100)): continue
            ce = v.get("ce",{}); pe = v.get("pe",{})
            rows.append({"Strike":int(s),
                         "CE LTP":round(ce.get("last_price",0),1),"CE OI":ce.get("oi",0),
                         "CE IV%":round(ce.get("implied_volatility",0),2),
                         "CE Δ":round(ce.get("greeks",{}).get("delta",0),3),
                         "CE Vol":ce.get("volume",0),
                         "PE LTP":round(pe.get("last_price",0),1),"PE OI":pe.get("oi",0),
                         "PE IV%":round(pe.get("implied_volatility",0),2),
                         "PE Δ":round(pe.get("greeks",{}).get("delta",0),3),
                         "PE Vol":pe.get("volume",0)})
        return pd.DataFrame(rows).sort_values("Strike").reset_index(drop=True), spot

    def render_chain(idx_name, scrip_id, spot_default, t3_key):
        st.markdown(f"#### {idx_name}")
        exps = fetch_expiry_list(scrip_id, tok3)
        if not exps:
            st.warning(f"Could not load {idx_name} expiries — check token.")
            return
        sel = st.selectbox(f"{idx_name} Expiry", exps, key=f"t3_{t3_key}_exp")
        # Auto-load on first visit; button allows manual refresh
        _auto_load = f"t3_{t3_key}_chain" not in st.session_state
        _refresh = st.button(f"🔄 Refresh {idx_name} Chain", key=f"t3_{t3_key}_btn")
        if _auto_load or _refresh:
            ch = fetch_chain(scrip_id, sel, tok3)
            if ch:
                st.session_state[f"t3_{t3_key}_chain"] = ch
                st.session_state[f"t3_{t3_key}_exp_used"] = sel
        if f"t3_{t3_key}_chain" in st.session_state:
            df_c, spot_c = chain_to_df(st.session_state[f"t3_{t3_key}_chain"], spot_default)
            if df_c.empty:
                st.warning(f"No strikes found near spot for {idx_name}.")
                return
            atm = df_c.iloc[(df_c["Strike"]-spot_c).abs().argsort()[:1]]["Strike"].values[0]
            st.caption(f"Spot: ₹{spot_c:,.1f} | ATM: ₹{atm:,} | Expiry: {st.session_state.get(f't3_{t3_key}_exp_used','')}")
            def hl(row): return ["background-color:#2d2d4e;font-weight:bold"]*len(row) if row["Strike"]==atm else [""]*len(row)
            st.dataframe(df_c.style.apply(hl,axis=1).format(
                {"CE LTP":"{:.1f}","PE LTP":"{:.1f}","CE IV%":"{:.2f}","PE IV%":"{:.2f}",
                 "CE Δ":"{:.3f}","PE Δ":"{:.3f}","CE OI":"{:,.0f}","PE OI":"{:,.0f}",
                 "CE Vol":"{:,.0f}","PE Vol":"{:,.0f}"}),
                use_container_width=True, hide_index=True, height=420)

    if not tok3:
        st.info("👆 Enter Dhan token in the sidebar to load chains.")
    else:
        render_chain("NIFTY 50",  NIFTY_SCRIP_ID,  SPOT["NIFTY 50"], "nifty")
        st.markdown("---")
        render_chain("SENSEX", SENSEX_SCRIP_ID, SPOT["SENSEX"],   "sensex")
