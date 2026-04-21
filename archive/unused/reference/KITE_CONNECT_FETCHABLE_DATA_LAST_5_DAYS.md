# Kite Connect: data you can reason about for the “last ~5 days”

This file is **reference only** (not imported by the app). It summarizes what Zerodha **Kite Connect v3** can return when you care about a **short recent window** (for example the last five **calendar** days or the last five **trading** sessions).

**Security:** Do not put `api_key`, `api_secret`, or `access_token` values into the repository. Store secrets in environment variables or a secrets manager. If credentials were pasted into chat or email, **rotate** them in the developer console.

**Official documentation:** [Kite Connect 3](https://kite.trade/docs/connect/v3/)

---

## 1. Historical market candles (best fit for “last 5 days” of *market* data)

**Endpoint:** `GET /instruments/historical/:instrument_token/:interval`  
**Docs:** [Historical candle data](https://kite.trade/docs/connect/v3/historical/)

You choose `from` and `to` timestamps (`yyyy-mm-dd hh:mm:ss`). A five-day window is **well inside** the published lookback limits for intraday intervals (for example minute data is available for a much longer window than five days).

**Intervals:** `minute`, `3minute`, `5minute`, `10minute`, `15minute`, `30minute`, `60minute`, `day`

**Each candle record includes:**

- Timestamp  
- Open, high, low, close  
- Volume  
- Optional **open interest** when you pass `oi=1` (relevant for F&amp;O); the candle row then includes an OI field as documented.

**Optional flags:**

- `continuous=1` — stitched **daily** history for **expired futures** (NFO/MCX) using a **live** contract’s `instrument_token`, as described in the docs.  
- `oi=1` — include OI in the candle rows where applicable.

**Practical limits called out in docs:**

- Expired **options** / many expired contracts: you need a **cached** `instrument_token` from when the contract was live; the live instrument master only lists active contracts.  
- **Delisted** symbols cannot be queried.

---

## 2. Live quote snapshots (today’s session context, not full 5-day tick replay)

**Endpoints:**

- `GET /quote` — full snapshot (up to 500 symbols per call)  
- `GET /quote/ohlc` — LTP + day OHLC (up to 1000 symbols)  
- `GET /quote/ltp` — LTP only (up to 1000 symbols)  

**Docs:** [Market quotes and instruments](https://kite.trade/docs/connect/v3/market-quotes/)

These return **current** (or latest available) market snapshots: last price, day OHLC, volume **for the current session**, depth, circuit limits, OI fields for F&amp;O, etc. They do **not** replace historical candles for reconstructing five full days of intraday tape unless you had been saving ticks yourself.

---

## 3. Instrument master (not dated, but needed for tokens)

**Endpoints:**

- `GET /instruments` — all exchanges (gzipped CSV)  
- `GET /instruments/:exchange` — one exchange  

**Docs:** [Market quotes and instruments](https://kite.trade/docs/connect/v3/market-quotes/)

**Columns include (among others):** `instrument_token`, `exchange_token`, `tradingsymbol`, `name`, `last_price`, `expiry`, `strike`, `tick_size`, `lot_size`, `instrument_type`, `segment`, `exchange`.

The dump is regenerated **about once per day**; `last_price` in the file is not real time.

---

## 4. Orders and executed trades (important: **same trading day only**)

**Endpoints:**

- `GET /orders` — all orders for **the current day**  
- `GET /trades` — all executed trades for **the current day**  
- `GET /orders/:order_id` — status **history for that order id**  
- `GET /orders/:order_id/trades` — trades for that order  

**Docs:** [Orders](https://kite.trade/docs/connect/v3/orders/)

Official docs state that the **order book is transient** and **only lives for a day** in the system. So you **cannot** pull a clean **five-day order or trade ledger** from these endpoints alone; for that you must **log** orders/trades yourself (for example from [postbacks](https://kite.trade/docs/connect/v3/postbacks/)) or use **broker statements** outside this API.

**Typical fields you *do* see for today’s orders/trades** (when available): exchange, tradingsymbol, order ids, timestamps, quantities, prices, product (CNC/MIS/NRML…), variety, status messages, fills, tags, and related execution metadata as per the docs.

---

## 5. Portfolio: holdings and positions (**state**, not a 5-day P&amp;L history API)

**Endpoints:**

- `GET /portfolio/holdings` — delivery holdings  
- `GET /portfolio/positions` — open and **day** positions with overnight carry  

**Docs:** [Portfolio](https://kite.trade/docs/connect/v3/portfolio/)

You get **current** holdings/positions, quantities, average prices, P&amp;L breakdown fields as documented (including day and net components where applicable). This reflects **now** (and today’s session), not a built-in “export last 5 days of portfolio snapshots” API.

---

## 6. Funds and margins (**snapshot**)

**Endpoints:**

- `GET /user/margins`  
- `GET /user/margins/:segment` (`equity` or `commodity`)  

**Docs:** [User](https://kite.trade/docs/connect/v3/user/)

Returns **current** balances and margin utilisation (cash, collateral, SPAN, exposure, MTM, option premium blocks, etc., as documented). Some fields are explicitly **“during the day”** (for example intraday pay-in). Not a substitute for historical ledger data.

---

## 7. GTT triggers (covers **last 5 days**; official window is **7 days**)

**Endpoints:** `GET /gtt/triggers`, `GET /gtt/triggers/:id`, plus create/modify/delete  

**Docs:** [GTT orders](https://kite.trade/docs/connect/v3/gtt/)

Docs: **active** GTTs plus those in other states from the **previous 7 days** appear in the list. So for a **5-day** lookback you can typically see **recent** GTT activity: ids, type (`single` / `two-leg`), `created_at`, `updated_at`, `expires_at`, `status`, trigger `condition`, child `orders`, and `result` metadata when a trigger fired.

---

## 8. Margin / charges **estimates** (any date you want to model — not historical actuals)

**Endpoints:**

- `POST /margins/orders`, `POST /margins/basket`  
- `POST /charges/orders` (“virtual contract note” style breakdown)  

**Docs:** [Margin calculation](https://kite.trade/docs/connect/v3/margins/)

You POST hypothetical or **known** fills; the API returns **computed** margins and charges. It does **not** fetch “what you were charged five days ago” from the back office; it **calculates** from the payload.

---

## 9. User profile (mostly static; login time is a timestamp)

**Endpoint:** `GET /user/profile`  

**Docs:** [User](https://kite.trade/docs/connect/v3/user/)

User id, name, email, enabled exchanges/products/order types, etc. Session token exchange also returns `login_time` for the **current** session.

---

## 10. WebSocket streaming (forward-looking)

**Docs:** [WebSocket streaming](https://kite.trade/docs/connect/v3/websocket/)

Useful for **live** quotes/ticks **from subscription time onward**. It is not a built-in “replay last five days of tick data” service unless you **record** the stream yourself.

---

## Quick summary table

| Need | Covered for “last ~5 days” via Kite Connect REST? |
|------|-----------------------------------------------------|
| OHLCV (and optional OI) candles for symbols you can tokenize | **Yes** — historical API with `from` / `to` |
| Full market depth / LTP history without your own DB | **No** — use historical candles or your saved stream |
| Order and trade **ledger** for each of the last 5 days | **No** — order book is **daily**; log yourself or use statements |
| Current holdings / positions / margins | **Yes** — snapshot endpoints |
| Recent GTT lifecycle (within ~7 days) | **Yes** — GTT list per docs |
| Charge breakdown for **assumed** trades | **Yes** — `charges/orders` style POST |

---

## Version note

Behavior and limits are defined by **Zerodha’s live API** and terms of use. If something critical depends on retention (for example order history), verify the latest [Orders](https://kite.trade/docs/connect/v3/orders/) and forum announcements.
