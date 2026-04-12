"""
Nifty Weekly Options Strategy Dashboard
Tabs: 1-Live Signal  2-Backtest  3-IV History
"""
import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import date, timedelta, datetime
import math, requests, sys, os

for d in ['Live-Signal-Generator', 'Live-fetching']:
    p = os.path.join(os.path.dirname(__file__), d)
    if os.path.exists(p):
        sys.path.insert(0, p); break

st.set_page_config(page_title="Nifty Options Dashboard", layout="wide",
                   page_icon="📈", initial_sidebar_state="expanded")

# ── Mobile-friendly CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global font size bump for mobile */
@media (max-width: 768px) {
    .stApp { font-size: 15px !important; }
    [data-testid="stMetric"] { padding: 6px 8px !important; }
    [data-testid="stMetricLabel"] { font-size: 13px !important; }
    [data-testid="stMetricValue"] { font-size: 20px !important; }
    [data-testid="stMetricDelta"] { font-size: 12px !important; }
    .stDataFrame { font-size: 13px !important; }
    .stDataFrame td, .stDataFrame th { padding: 4px 6px !important; min-width: 60px !important; }
    .stTabs [data-baseweb="tab"] { font-size: 14px !important; padding: 8px 12px !important; }
    .stCaption { font-size: 12px !important; }
    .stAlert p { font-size: 13px !important; }
    [data-testid="stSidebar"] { min-width: 280px !important; }
    h1 { font-size: 22px !important; }
    h2, .stSubheader { font-size: 18px !important; }
    h3 { font-size: 16px !important; }
    /* Make columns stack on very small screens */
    [data-testid="column"] { min-width: 140px !important; }
}
/* Desktop: slightly larger dataframe text */
.stDataFrame { font-size: 14px; }
.stDataFrame th { font-weight: 700 !important; background-color: rgba(50,50,50,0.3) !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
DHAN_CLIENT_ID  = "1109450231"
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
IV_ANN= {"NIFTY 50": 0.142,   "SENSEX": 0.138}
IVP   = {"NIFTY 50": 42,      "SENSEX": 38}

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

def ivp_quality(ivp): return min(100, ivp * 1.25)
def comp_score(prob, ivp, ret_pct=0):
    """Score = 40% × Prob(OTM) + 30% × IVP quality + 30% × Return attractiveness"""
    prob_component = prob * 100 * 0.40
    ivp_component  = ivp_quality(ivp) * 0.30
    ret_component  = min(100, ret_pct * 25) * 0.30   # 4% ret = 100 score
    return round(prob_component + ivp_component + ret_component)
def sig_label(sc, thr=65): return "SELL" if sc>=thr else ("MONITOR" if sc>=50 else "AVOID")
def sig_color(lbl): return {"SELL":"#C6EFCE","MONITOR":"#FFEB9C","AVOID":"#FFC7CE"}[lbl]

# ── Dhan API ──────────────────────────────────────────────────────────────────
def _hdr(tok): return {"Content-Type":"application/json","client-id":DHAN_CLIENT_ID,"access-token":tok}

@st.cache_data(ttl=60, show_spinner=False)
def fetch_ltp(tok):
    try:
        r = requests.post("https://api.dhan.co/v2/marketfeed/ltp",
                          json={"IDX_I":[13,51]}, headers=_hdr(tok), timeout=8)
        idx = r.json().get("data",{}).get("IDX_I",{})
        n = idx.get("13",{}).get("last_price",0)
        s = idx.get("51",{}).get("last_price",0)
        if n and s:
            return {"nifty":float(n),"sensex":float(s),"ts":datetime.now().strftime("%H:%M:%S")}
    except: pass
    return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_funds(tok):
    try:
        r = requests.get("https://api.dhan.co/v2/fundlimit", headers=_hdr(tok), timeout=8)
        d = r.json()
        return {"available":d.get("availabelBalance",0),"used":d.get("utilizedAmount",0),"total":d.get("sodLimit",0)}
    except: return None

@st.cache_data(ttl=300, show_spinner=False)
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

# ── Token: secrets → session ──────────────────────────────────────────────────
if not st.session_state.get("dhan_tok"):
    try:
        t = st.secrets["dhan"]["access_token"]
        if t: st.session_state["dhan_tok"] = t
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
    if st.session_state.get("dhan_tok"):
        st.success("🔑 Token active — shared across all devices via Streamlit Secrets")
        with st.expander("Override token (this session only)"):
            _ov = st.text_input("New token", type="password", key="dhan_token_override")
            if _ov:
                st.session_state["dhan_tok"] = _ov
                st.session_state["_tok_manually_set"] = True
    else:
        st.warning("No token found in Secrets")
        _inp = st.text_input("Dhan Token (this session)", type="password", key="dhan_token")
        if _inp:
            st.session_state["dhan_tok"] = _inp
            st.session_state["_tok_manually_set"] = True
        st.caption(f"To share across devices: add to Streamlit Secrets as `dhan.access_token`")

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

    # Fetch button
    fetch_btn = st.button("📡 Fetch Live Chain", type="primary", disabled=not has_tok,
                          use_container_width=True, key="fetch_live_btn")

    # Strike parameters (below Fetch)
    _sc1, _sc2 = st.columns(2)
    with _sc1:
        dist_pct = st.number_input("Dist from spot (%)", 0.1, 5.0, 0.5, 0.1,
                                   key="dist_pct", help="Closest strike distance from spot")
    with _sc2:
        step_pct = st.number_input("Offset step (%)", 0.1, 2.0, 0.5, 0.1,
                                   key="step_pct", help="Gap between each of the 5 strikes")
    st.caption(f"Put strikes: -{dist_pct:.1f}% to -{dist_pct+4*step_pct:.1f}% | "
               f"Call: +{dist_pct:.1f}% to +{dist_pct+4*step_pct:.1f}%")
    st.markdown("---")

    # ── SECTION 2: Backtest + Signal Filters ─────────────────────────────────
    st.markdown("### 2️⃣ Backtest & Filters")
    _b1, _b2 = st.columns(2)
    with _b1:
        lookback_m = st.selectbox("Lookback", [6,12,24,36], index=1, key="lookback",
                                   format_func=lambda x: f"{x}m")
    with _b2:
        sig_thresh = st.number_input("Score thr.", 50, 90, 65, key="sig_thresh")
    entry_time = st.selectbox("Entry", ["T-2 close","T-1 open","T-1 close","T open","T close"], key="entry")
    exit_time  = st.selectbox("Exit",  ["T-1 close","T open","T close"], key="exit")
    ivp_range  = st.slider("IVP regime (%)", 0, 100, (20,80), key="ivp")
    _f1, _f2 = st.columns(2)
    with _f1:
        excl_fri = st.toggle("Excl. Friday", value=True, key="excl_fri")

# ── Live data ─────────────────────────────────────────────────────────────────
_ltp   = fetch_ltp(tok)   if tok else None
_funds = fetch_funds(tok) if tok else None

SPOT = {"NIFTY 50": _ltp["nifty"]  if _ltp else 22700,
        "SENSEX":   _ltp["sensex"] if _ltp else 73320}
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

ivp_ok = ivp_range[0] <= IVP["NIFTY 50"] <= ivp_range[1]

# ── Handle fetch button ───────────────────────────────────────────────────────
# Auto-fetch on first load if token available but no chain cached yet
_auto_fetch = has_tok and "nifty_chain" not in st.session_state
if (fetch_btn or _auto_fetch) and has_tok:
    with st.spinner("Fetching Nifty & Sensex option chains…"):
        nc = fetch_chain(NIFTY_SCRIP_ID,  sel_n_exp, tok)
        sc = fetch_chain(SENSEX_SCRIP_ID, sel_s_exp, tok)
    ts = datetime.now().strftime("%H:%M:%S")
    if nc:
        st.session_state.update({"nifty_chain":nc,"nifty_exp_used":sel_n_exp,
                                  "nifty_spot_live":nc.get("last_price",SPOT["NIFTY 50"])})
    if sc:
        st.session_state.update({"sensex_chain":sc,"sensex_exp_used":sel_s_exp,
                                  "sensex_spot_live":sc.get("last_price",SPOT["SENSEX"])})
    if nc or sc:
        st.session_state["chain_ts"] = ts

# ── Build leg table ───────────────────────────────────────────────────────────
def make_leg(offsets, side, idx):
    spot       = st.session_state.get("nifty_spot_live" if idx=="NIFTY 50" else "sensex_spot_live", SPOT[idx])
    chain      = st.session_state.get("nifty_chain"     if idx=="NIFTY 50" else "sensex_chain",     {})
    iv         = IV_ANN[idx]; ivp_val = IVP[idx]
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
        score   = comp_score(prob, ivp_val, ret)
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
            return [f"background-color:{sig_color(v)};color:{'black' if sig_color(v)=='#C6EFCE' else 'white'};font-weight:bold"
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
    ivp_val   = IVP[idx]

    if not ivp_ok:
        st.error(f"REGIME: SKIP — IVP={ivp_val} outside {ivp_range[0]}-{ivp_range[1]}%")
    else:
        st.success(f"REGIME: ALLOW | IVP={ivp_val} | DTE={dte_adj}d | {src_lbl}")
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

def top_bar():
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("NIFTY 50",  f"₹{SPOT['NIFTY 50']:,.0f}")
    c2.metric("NIFTY IV",  f"{IV_ANN['NIFTY 50']*100:.1f}%", f"IVP {IVP['NIFTY 50']}")
    c3.metric("SENSEX",    f"₹{SPOT['SENSEX']:,.0f}")
    c4.metric("SENSEX IV", f"{IV_ANN['SENSEX']*100:.1f}%",   f"IVP {IVP['SENSEX']}")
    regime = "ALLOW" if ivp_ok else "SKIP"
    st.info(f"**Regime:** {regime} | IVP {IVP['NIFTY 50']} | DTE {dte_adj} | {'Fri excluded' if excl_fri else 'All days'}")
    st.caption(f"🕐 {PRICE_SRC} | {PRICE_TS} | auto-refresh 1 min")

# ── Backtest Engine helpers ────────────────────────────────────────────────────
BT_CSV_END = date(2026, 3, 24)

@st.cache_data(show_spinner=False)
def load_bt_df():
    p = os.path.join(os.path.dirname(__file__), "Backtest-Engine",
                     "final_merged_output_30m_strike_within_6pct.csv")
    if not os.path.exists(p): return pd.DataFrame()
    df = pd.read_csv(p, parse_dates=["timestamp_30m","expiry"])
    df["tdate"] = df["timestamp_30m"].dt.date
    df["edate"] = df["expiry"].dt.date
    df["hhmm"]  = df["timestamp_30m"].dt.strftime("%H:%M")
    return df

def bt_find_expiry(df, d):
    fut = sorted(df[df["edate"] > d]["edate"].unique())
    return fut[0] if fut else None

def bt_get_spot(df, d):
    r = df[(df["tdate"]==d) & (df["hhmm"]=="15:00")]
    return float(r["underlying_spot_close"].iloc[0]) if len(r) else None

def bt_iv_straddle(df, d, ed, spot):
    rnd = ROUND["NIFTY 50"]
    atm = int(round(spot/rnd)*rnd)
    rows = df[(df["tdate"]==d) & (df["edate"]==ed) & (df["hhmm"]=="15:00")]
    ce = rows[(rows["strike_price"]==atm) & (rows["option_type"]=="CE")]["close"]
    pe = rows[(rows["strike_price"]==atm) & (rows["option_type"]=="PE")]["close"]
    if len(ce) and len(pe):
        stv = float(ce.iloc[0]) + float(pe.iloc[0])
        T   = effective_dte(d, ed) / 365
        iv  = round(stv / (0.8 * spot * math.sqrt(T)), 4) if T > 0 else IV_ANN["NIFTY 50"]
        return iv, round(stv, 1), atm
    return IV_ANN["NIFTY 50"], None, atm

def bt_get_prem(df, entry_d, exit_d, ed, strike, otype):
    def _q(d):
        r = df[(df["tdate"]==d) & (df["edate"]==ed) &
               (df["strike_price"]==float(strike)) & (df["option_type"]==otype) &
               (df["hhmm"]=="15:00")]
        return float(r["close"].iloc[0]) if len(r) else None
    return _q(entry_d), _q(exit_d)

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

def dte_label(d):
    if d >= 4: return "T-4"
    if d == 3: return "T-3"
    if d == 2: return "T-2"
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
tab1, tab2, tab3 = st.tabs(["Tab 1 - Live Signal", "Tab 2 - Backtest", "Tab 3 - IV History"])

# ── TAB 1: Live Signal ────────────────────────────────────────────────────────
with tab1:
    top_bar()
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
**Score** = 40% × Prob N(d2) + 30% × min(IVP×1.25, 100) + 30% × min(Return%×25, 100). SELL ≥ threshold, MONITOR ≥50, else AVOID.

**Prob N(d2)** — BS probability option expires worthless. Inputs: spot, strike, IV, r=6.5%, DTE (holidays excluded).

**Delta** — Put: N(d1)−1, Call: N(d1). Magnitude = sensitivity to ₹1 spot move.

**Cushion (Theta/|Vega|)** — IV points needed to wipe one day's Theta. ≥2x safe, 1-2x watch, <1x risky.

**Strike rounding** — Nifty: ₹50, Sensex: ₹100 (BSE standard).

**Ext. loss** — Estimated loss if spot moves 0.5% beyond the strike at expiry.

**DTE** — Trading days to expiry (weekends + NSE holidays excluded).
        """)

# ── TAB 2: Historical Strategy Simulator ─────────────────────────────────────
with tab2:
    top_bar()
    st.markdown("---")
    st.subheader("📊 Historical Strategy Simulator")
    st.caption("Select any date → get real market data → choose your 3-step inputs → validate actual P&L vs expectation")

    bt_df = load_bt_df()

    # ── Section 1: Date & Mode ────────────────────────────────────────────────
    st.markdown("#### 1️⃣ Select Date & Exit Timing")
    s1c1, s1c2 = st.columns([2, 2])
    with s1c1:
        bt_date = st.date_input("Trade Date", value=date(2025, 10, 14),
                                min_value=date(2024, 9, 23), max_value=date.today(),
                                key="bt_date2")
    with s1c2:
        bt_exit_mode = st.selectbox("Exit Timing",
                                    ["T-1 Close (day before expiry)",
                                     "T Close (expiry day close)"],
                                    key="bt_exit2")
    exit_is_T1   = "T-1" in bt_exit_mode
    is_historical = (not bt_df.empty) and (bt_date <= BT_CSV_END)

    if is_historical:
        st.success("📁 **Historical Mode — Real P&L** · Actual CSV data (Sep 2024 – Mar 2026). Premiums are real 15:00 close prices.")
    else:
        st.warning("📡 **Live Mode — Estimated P&L** · Beyond CSV database. Entry from DhanHQ chain if available; exit estimated from LUT avg.")

    # Snapshot
    bt_valid = True
    if is_historical:
        _sp = bt_get_spot(bt_df, bt_date)
        if _sp is None:
            st.error("No data for this date — market may have been closed. Try a nearby trading day.")
            bt_valid = False
        else:
            bt_spot_val = _sp
            bt_expiry   = bt_find_expiry(bt_df, bt_date)
            if bt_expiry is None:
                st.error("Could not find a future expiry in data for this date.")
                bt_valid = False
            else:
                bt_iv_val, bt_straddle_val, bt_atm = bt_iv_straddle(bt_df, bt_date, bt_expiry, bt_spot_val)
    else:
        bt_spot_val     = SPOT["NIFTY 50"]
        bt_expiry       = bt_next_expiry_live(bt_date)
        bt_iv_val       = IV_ANN["NIFTY 50"]
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
                   "● actual" if is_historical else "~ live")
        sm2.metric("Nearest Expiry", bt_expiry.strftime("%Y-%m-%d"),
                   bt_expiry.strftime("%A"))
        sm3.metric("DTE", f"{bt_dte_val} trading days")
        sm4.metric("ATM IV%", f"{bt_iv_pct}%",
                   "from ATM straddle" if is_historical else "~ live")
        sm5.metric("ATM Straddle",
                   f"₹{bt_straddle_val:.0f}" if bt_straddle_val else "~ live",
                   "actual CE+PE" if is_historical else "est.")

        st.markdown("---")

        # ── Section 2: 3-Step Selection ───────────────────────────────────────
        st.markdown("#### 2️⃣ 3-Step Strategy Selection")
        auto_dte = dte_label(bt_dte_val)
        auto_iv  = iv_band(bt_iv_pct)
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.caption("STEP 01 — DTE · auto-set, override if needed")
            dte_opts  = ["T-4","T-3","T-2","T-1"]
            bt_dte_sel = st.radio("DTE", dte_opts,
                                  index=dte_opts.index(auto_dte),
                                  horizontal=True, key="bt_dte_sel",
                                  label_visibility="collapsed")
            if bt_dte_sel != auto_dte:
                st.caption(f"⚡ Overriding auto ({auto_dte})")
        with sc2:
            st.caption("STEP 02 — IV Band · auto-set from ATM straddle")
            iv_opts  = ["<13%","13-15%","15-18%","18-22%",">22%"]
            bt_iv_sel = st.radio("IV Band", iv_opts,
                                 index=iv_opts.index(auto_iv),
                                 horizontal=True, key="bt_iv_sel",
                                 label_visibility="collapsed")
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

        # ── Section 3: Strategy Recommendation + Do's & Don'ts ───────────────
        st.markdown("#### 3️⃣ Strategy Recommendation + Do's & Don'ts")
        lut_key = f"{bt_dte_sel}|{bt_iv_sel}|{bt_trend}"
        lut = BT_LUT.get(lut_key)
        gam = BT_GAMMA.get(bt_dte_sel, BT_GAMMA["T-4"])
        rnd = ROUND["NIFTY 50"]
        lot = LOT["NIFTY 50"]

        if not lut:
            st.error(f"No LUT entry for `{lut_key}`")
        else:
            skip_flag = lut.get("skip")
            warn_flag = lut.get("warn")
            if skip_flag:
                st.error(f"⊘ **No Trade — Skip This Setup**\n\n{skip_flag}\n\n"
                         f"Win rate: {lut['win']}% · Avg P&L: ₹{lut['pnl']:+,}")
            else:
                if warn_flag:
                    st.warning(f"⚠️ {warn_flag}")

                kc1, kc2, kc3, kc4 = st.columns(4)
                kc1.metric("Recommended Strategy", lut["s"])
                kc2.metric("Historical Win Rate", f"{lut['win']}%")
                kc3.metric("Avg P&L / Trade", f"₹{lut['pnl']:+,}")
                kc4.metric("Max Loss (backtest)",
                           f"₹{lut['ml']:,}" if lut["ml"] else "None in dataset")
                st.caption(
                    f"Theta/Capital: **{lut['tc']}%/day** · Min theta: **{lut['th']} pts/day** · "
                    f"Gamma max: **{gam['max']}** · LUT key: `{lut_key}`")

                dc = lut.get("dc"); dp = lut.get("dp")
                ce_strike = int(round(bt_spot_val*(1+dc)/rnd)*rnd) if dc else None
                pe_strike = int(round(bt_spot_val*(1+dp)/rnd)*rnd) if dp else None

                t_entry, t_greeks, t_pnl = st.tabs(
                    ["📋 Entry Params (Do's & Don'ts)", "📐 Greeks", "💰 Actual P&L Result"])

                # ── Entry Params ───────────────────────────────────────────────
                with t_entry:
                    if dc:
                        st.markdown(f"**CE Short Δ:** `+{dc}` → Strike ≈ **₹{ce_strike:,}** "
                                    f"(~{dc*100:.0f}% OTM call)")
                    if dp:
                        st.markdown(f"**PE Short Δ:** `{dp}` → Strike ≈ **₹{pe_strike:,}** "
                                    f"(~{abs(dp)*100:.0f}% OTM put)")
                    st.markdown(
                        f"**Theta check:** Combined theta must be ≥ **{lut['th']} pts/day** "
                        f"({lut['tc']}% of ₹1,20,000). Sum theta × {lot} for all short legs from chain.")
                    st.markdown(
                        f"**Gamma limit:** Short leg gamma ≤ **{gam['max']}**. {gam['rule']}.")
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

                # ── Greeks ─────────────────────────────────────────────────────
                with t_greeks:
                    gp = BT_GP.get(lut["st"], BT_GP["ss"])
                    st.info(f"Greeks ranked by criticality for **{lut['s']}**. "
                            f"Check IN ORDER — first two are your go/no-go gates.")
                    order = sorted(gp.items(),
                                   key=lambda x: {"critical":0,"important":1,"monitor":2,"low":3}[x[1][0]])
                    vals = {
                        "delta": f"Net Δ target: {'≈ 0.00 (both legs cancel)' if dc and dp else (f'~+{dc} net' if dc else f'~{dp} net')}",
                        "gamma": f"Max: {gam['max']} · Exit threshold: {gam['exit']}",
                        "theta": f"Min: {lut['th']} pts/day · {lut['tc']}% of ₹1,20,000 capital",
                        "vega":  "Watch India VIX trend direction before and during trade",
                    }
                    gsym = {"delta":"Δ","gamma":"Γ","theta":"Θ","vega":"V"}
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

                # ── P&L Result ─────────────────────────────────────────────────
                with t_pnl:
                    st.info(
                        f"Entry date: **{bt_date.strftime('%Y-%m-%d')}** at 15:00 close · "
                        f"Exit date: **{exit_date.strftime('%Y-%m-%d')}** ({bt_exit_mode})")
                    rows_data = []
                    _s = {"pnl": 0, "has_exit": True}  # mutable state for leg accumulator

                    def _add_leg(strike, otype, label):
                        if not strike: return
                        if is_historical:
                            e_p, x_p = bt_get_prem(bt_df, bt_date, exit_date,
                                                    bt_expiry, strike, otype)
                            src = "● real"
                        else:
                            chain2 = st.session_state.get("nifty_chain", {})
                            e_p = ltp_from_chain(chain2, strike,
                                                 "call" if otype=="CE" else "put") if chain2 else None
                            if not e_p:
                                off = abs(strike/bt_spot_val - 1)
                                e_p = round(max(5.0, 1267*max(0.3,1-(off-0.005)/0.02)
                                               *(bt_iv_val/0.14)/lot), 1)
                            x_p  = None
                            src  = "~ est"
                        leg_pnl = round((e_p - x_p) * lot) if (e_p and x_p) else None
                        if leg_pnl is not None:
                            _s["pnl"] += leg_pnl
                        else:
                            _s["has_exit"] = False
                        rows_data.append({
                            "Leg": label, "Strike": f"₹{strike:,}", "Type": otype,
                            "Entry Prem": f"₹{e_p:.1f}" if e_p else "—",
                            "Exit Prem":  f"₹{x_p:.1f}" if x_p else "pending",
                            "P&L / Lot":  f"₹{leg_pnl:+,.0f}" if leg_pnl is not None else "~ est",
                            "Source": src,
                        })

                    if ce_strike: _add_leg(ce_strike, "CE", "Short Call")
                    if pe_strike: _add_leg(pe_strike, "PE", "Short Put")
                    total_pnl = _s["pnl"]; has_exit = _s["has_exit"]

                    if rows_data:
                        df_legs = pd.DataFrame(rows_data)

                        def _style_legs(df):
                            def _rc(col):
                                if col.name == "P&L / Lot":
                                    return [("color:#21c55d" if "+" in str(v) else
                                             "color:#ef4444" if "-" in str(v) else "")
                                            for v in col]
                                if col.name == "Type":
                                    return [("color:#3b82f6" if v=="CE" else
                                             "color:#ef4444" if v=="PE" else "")
                                            for v in col]
                                if col.name == "Source":
                                    return [("color:#21c55d" if "real" in str(v) else "color:#6b7280")
                                            for v in col]
                                return [""]*len(col)
                            return df.style.apply(_rc)

                        st.dataframe(_style_legs(df_legs),
                                     use_container_width=True, hide_index=True)

                        r1, r2, r3 = st.columns(3)
                        if is_historical and has_exit:
                            outcome = "✅ PROFIT" if total_pnl > 0 else "❌ LOSS"
                            r1.metric("Actual P&L (1 lot)", f"₹{total_pnl:+,.0f}", outcome)
                            r2.metric("LUT Avg Expected", f"₹{lut['pnl']:+,}")
                            diff = round((total_pnl - lut["pnl"]) / max(abs(lut["pnl"]), 1) * 100)
                            r3.metric("vs LUT Expected", f"{diff:+.0f}%",
                                      "above avg" if diff > 0 else "below avg")
                        else:
                            r1.metric("Estimated Max P&L", f"~₹{lut['th']*lot:,.0f}",
                                      "if both legs expire OTM")
                            r2.metric("LUT Avg Expected", f"₹{lut['pnl']:+,}")
                            r3.metric("Status", "⏳ Pending — exit date not reached")
                    else:
                        st.info("Select a strategy with defined delta targets to see P&L details.")

    with st.expander("Glossary"):
        st.markdown("""
**LUT (Look-up Table)** — 60-entry map from backtest (Oct 2024–Mar 2026, ~1,840 trades). Maps `DTE | IV band | Trend` → recommended strategy + win rate + avg P&L + theta/gamma rules.

**Historical Mode** — Date ≤ Mar 24 2026: all premiums are real 15:00 close prices from the CSV database. P&L is actual.

**Live Mode** — Date > Mar 24 2026: entry premium from DhanHQ option chain (or estimated). Exit P&L estimated from LUT avg until expiry passes.

**Expiry rule** — Before Sep 2025: Thursday. From Sep 2025 onward: Tuesday (NSE rule change).

**DTE label** — T-4 = 4+ trading days, T-3 = 3d, T-2 = 2d, T-1 = 1d to expiry.

**IV Band** — ATM straddle IV derived using Brenner-Subrahmanyam approximation from actual CE+PE close prices.

**Theta/Capital** — Daily theta ÷ ₹1,20,000. Must meet LUT minimum; if not, premium is too thin for the risk.

**Gamma limit** — Maximum short-leg gamma before forced exit. Accelerates sharply near expiry — the primary risk for naked short strategies.
        """)

# ── TAB 3: IV History ─────────────────────────────────────────────────────────
with tab3:
    top_bar()
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
