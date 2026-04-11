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

# ── TAB 2: Backtest ───────────────────────────────────────────────────────────
with tab2:
    top_bar()
    st.markdown("---")
    st.subheader("📊 Strategy Backtest Engine")
    st.caption("Select a historical date → view market state → pick strategy → see P&L result for 1 contract")

    # ── Step 1: Date Selection ────────────────────────────────────────────────
    st.markdown("#### 1️⃣ Select Historical Date")
    bt_c1, bt_c2, bt_c3 = st.columns(3)
    with bt_c1:
        bt_date = st.date_input("Trade Date", value=date.today() - timedelta(days=7),
                                 min_value=date(2024,10,1), max_value=date.today(),
                                 key="bt_date")
    # Calculate nearest expiry from that date (Thursday for Nifty)
    def next_expiry_from(d):
        """Find next Thursday (Nifty weekly) from given date"""
        days_ahead = 3 - d.weekday()  # Thursday = 3
        if days_ahead < 0:
            days_ahead += 7
        if days_ahead == 0:
            return d  # It's Thursday, expiry is today
        return d + timedelta(days=days_ahead)

    bt_expiry = next_expiry_from(bt_date)
    # Skip if expiry falls on holiday
    while bt_expiry in NSE_HOLIDAYS or bt_expiry.weekday() >= 5:
        bt_expiry -= timedelta(days=1)

    bt_dte = effective_dte(bt_date, bt_expiry)

    with bt_c2:
        st.metric("Nearest Expiry", bt_expiry.strftime("%Y-%m-%d"))
    with bt_c3:
        st.metric("DTE", f"{bt_dte} trading days")

    st.markdown("---")

    # ── Step 2: Market Snapshot (simulated from constants + date) ─────────
    st.markdown("#### 2️⃣ Market Snapshot on Selected Date")
    # Use spot from live if today, else estimate from stored IV
    bt_spot = SPOT["NIFTY 50"]  # live spot as reference
    bt_iv = IV_ANN["NIFTY 50"]
    bt_ivp = IVP["NIFTY 50"]

    ms1, ms2, ms3, ms4 = st.columns(4)
    ms1.metric("Nifty Spot (ref)", f"₹{bt_spot:,.0f}")
    ms2.metric("IV (annualized)", f"{bt_iv*100:.1f}%")
    ms3.metric("IVP", f"{bt_ivp}")
    ms4.metric("DTE", f"{bt_dte}d")

    # Greeks display for the chosen offset
    st.markdown("##### Greeks at selected strikes")
    bt_off_pct = st.select_slider("Strike offset from spot",
                                    options=[f"{x:+.1f}%" for x in
                                             [-3.5,-3.0,-2.5,-2.0,-1.5,-1.0,
                                              +1.0,+1.5,+2.0,+2.5,+3.0,+3.5]],
                                    value="-2.0%", key="bt_offset")
    bt_off = float(bt_off_pct.replace('%','')) / 100
    bt_side = "put" if bt_off < 0 else "call"
    bt_strike = int(round(bt_spot * (1 + bt_off) / ROUND["NIFTY 50"]) * ROUND["NIFTY 50"])

    bt_delta = delta_bs(bt_spot, bt_strike, bt_iv, bt_dte, bt_side)
    bt_T = bt_dte / 365
    bt_d1, bt_d2 = bs_d1d2(bt_spot, bt_strike, bt_iv, bt_T)
    bt_gamma = float(norm.pdf(bt_d1) / (bt_spot * bt_iv * math.sqrt(bt_T))) if bt_T > 0 and bt_iv > 0 else 0
    bt_theta_day = float(-bt_spot * norm.pdf(bt_d1) * bt_iv / (2 * math.sqrt(bt_T)) / 365) if bt_T > 0 else 0
    bt_vega_pt = float(bt_spot * norm.pdf(bt_d1) * math.sqrt(bt_T) / 100) if bt_T > 0 else 0
    bt_prob = prob_nd2(bt_spot, bt_strike, bt_iv, bt_dte, bt_side)

    gc1, gc2, gc3, gc4, gc5 = st.columns(5)
    gc1.metric("Strike", f"₹{bt_strike:,}")
    gc2.metric("Delta", f"{bt_delta:.4f}")
    gc3.metric("Gamma", f"{bt_gamma:.6f}")
    gc4.metric("Theta/day", f"₹{bt_theta_day:.1f}")
    gc5.metric("Prob OTM", f"{bt_prob*100:.1f}%")

    st.markdown("---")

    # ── Step 3: Market Trend Indicators ──────────────────────────────────────
    st.markdown("#### 3️⃣ Market Trend Indicators")
    ti1, ti2, ti3 = st.columns(3)
    # Simple trend heuristics based on IVP
    trend_signal = "Neutral"
    if bt_ivp > 60:
        trend_signal = "High IV — Favor selling"
    elif bt_ivp < 25:
        trend_signal = "Low IV — Caution on selling"

    regime_signal = "ALLOW" if 20 <= bt_ivp <= 80 else "SKIP"
    ti1.metric("IV Regime", regime_signal, f"IVP {bt_ivp}")
    ti2.metric("Trend Signal", trend_signal)
    ti3.metric("Vega Risk (1pt IV)", f"₹{bt_vega_pt * LOT['NIFTY 50']:.0f}/lot")

    st.markdown("---")

    # ── Step 4: Strategy Selection ───────────────────────────────────────────
    st.markdown("#### 4️⃣ Select Strategy & Exit")
    sc1, sc2 = st.columns(2)
    with sc1:
        bt_strategy = st.selectbox("Strategy",
                                    ["Short Put","Short Call","Short Strangle",
                                     "Short Straddle","Iron Condor"],
                                    key="bt_strategy")
    with sc2:
        bt_exit = st.selectbox("Expected Closing",
                                ["T-1 Close (day before expiry)",
                                 "T Close (expiry day)"],
                                key="bt_exit")

    # ── Step 5: Result for 1 Contract ────────────────────────────────────────
    st.markdown("#### 5️⃣ Result — 1 Contract")
    st.info("🚧 **Live historical P&L calculation coming soon.** This section will use actual "
            "historical premium data from the backtest database to show real profit/loss for the "
            "selected date, strike, and strategy. See the implementation plan below.")

    # Show estimated result using current premium estimates
    chain = st.session_state.get("nifty_chain", {})
    est_prem = ltp_from_chain(chain, bt_strike, bt_side) if chain else None
    if not est_prem:
        base = 1267
        est_prem = round(max(5.0, base * max(0.3, 1 - (abs(bt_off) - 0.005) / 0.02) * (bt_iv / 0.14) / LOT["NIFTY 50"]), 1)
        prem_src = "estimated"
    else:
        prem_src = "live"

    lot = LOT["NIFTY 50"]
    if bt_strategy == "Short Put":
        max_profit = est_prem * lot
        legs_info = f"Sell {bt_strike} PE @ ₹{est_prem:.1f}"
    elif bt_strategy == "Short Call":
        max_profit = est_prem * lot
        legs_info = f"Sell {bt_strike} CE @ ₹{est_prem:.1f}"
    elif bt_strategy == "Short Strangle":
        # Both sides
        opp_off = -bt_off
        opp_strike = int(round(bt_spot * (1 + opp_off) / ROUND["NIFTY 50"]) * ROUND["NIFTY 50"])
        opp_prem = ltp_from_chain(chain, opp_strike, "call" if bt_side == "put" else "put") if chain else None
        if not opp_prem:
            opp_prem = round(max(5.0, base * max(0.3, 1 - (abs(opp_off) - 0.005) / 0.02) * (bt_iv / 0.14) / lot), 1)
        max_profit = (est_prem + opp_prem) * lot
        legs_info = f"Sell {bt_strike} {'PE' if bt_side=='put' else 'CE'} @ ₹{est_prem:.1f} + Sell {opp_strike} {'CE' if bt_side=='put' else 'PE'} @ ₹{opp_prem:.1f}"
    elif bt_strategy == "Short Straddle":
        atm = int(round(bt_spot / ROUND["NIFTY 50"]) * ROUND["NIFTY 50"])
        atm_ce = ltp_from_chain(chain, atm, "call") if chain else None
        atm_pe = ltp_from_chain(chain, atm, "put") if chain else None
        if not atm_ce: atm_ce = round(max(50, 200 * bt_iv / 0.14), 1)
        if not atm_pe: atm_pe = round(max(50, 180 * bt_iv / 0.14), 1)
        max_profit = (atm_ce + atm_pe) * lot
        legs_info = f"Sell {atm} CE @ ₹{atm_ce:.1f} + Sell {atm} PE @ ₹{atm_pe:.1f}"
    else:  # Iron Condor
        max_profit = est_prem * lot * 0.6  # approximate net credit
        legs_info = f"Iron Condor around {bt_strike} (est. net credit)"

    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("Max Profit (if OTM)", f"₹{max_profit:,.0f}")
    rc2.metric("Premium Source", prem_src)
    rc3.metric("Probability OTM", f"{bt_prob*100:.1f}%")
    st.caption(f"Legs: {legs_info} | Lot: {lot} | Capital: ₹{capital_base:,}")

    st.markdown("---")

    # ── Backtest Implementation Plan ─────────────────────────────────────────
    with st.expander("📋 Backtest Engine — Implementation Plan"):
        st.markdown("""
**Phase 1 — Data Foundation** (in progress)
- Load historical NIFTY option chain data from backtest database (CSV/Excel in `Backtest-Engine/`)
- Parse columns: date, expiry, strike, CE/PE premium, OI, IV, Greeks
- Index by (date, expiry, strike) for fast lookup

**Phase 2 — Date-Driven Lookup**
- User selects a historical date → system finds nearest expiry
- Shows actual DTE, spot price, IV, IVP from that date
- Displays actual Greeks (delta, gamma, theta, vega) from the chain

**Phase 3 — Strategy Evaluation**
- User picks strategy (Short Put, Short Call, Strangle, Straddle, Iron Condor)
- System looks up entry premium on selected date
- User picks exit: T-1 close or T close (expiry day)
- System looks up exit premium → calculates actual P&L for 1 lot

**Phase 4 — Batch Backtest**
- Run strategy across all expiries in the dataset (18 months)
- Show aggregate: win rate, avg profit, avg loss, max DD, Sharpe
- Chart: cumulative P&L curve, drawdown chart

**Data needed in `Backtest-Engine/`:**
- Historical option chain snapshots (daily close premiums per strike)
- Historical spot prices (NIFTY close)
- Historical IV data
        """)

    with st.expander("Glossary"):
        st.markdown("""
**DTE** — Trading days to expiry (weekends + NSE holidays excluded).
**Delta** — Rate of change of option price vs ₹1 spot move.
**Gamma** — Rate of change of delta vs ₹1 spot move.
**Theta** — Daily time decay in ₹ per lot.
**Vega** — Change in premium for 1% IV move.
**Prob OTM** — Black-Scholes probability option expires worthless.
**Score** = 40%×Prob + 30%×IVP + 30%×Return.
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
