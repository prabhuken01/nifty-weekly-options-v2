# Shoonya API Setup Guide

Get real-time live market data for Tab 2 using Shoonya API (Finvasia).

## What is Shoonya API?

Shoonya is a **free, real-time market data API** provided by Finvasia. It provides:
- ✅ Live NIFTY/SENSEX spot prices
- ✅ Real-time option premiums (CE/PE)
- ✅ Bid/ask spreads, volumes, open interest
- ✅ No per-API-call charges
- ✅ 1-second tick data

## Setup Steps

### 1. Create Finvasia Account
1. Go to https://www.shoonya.com/
2. Sign up with email/phone
3. Complete KYC verification
4. Get API credentials from dashboard

### 2. Get API Credentials
After account activation, you'll receive:
- **User ID** (client code)
- **Password**
- **API Key** (authentication token)
- **PIN** (if 2FA enabled)

### 3. Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:SHOONYA_USER_ID = "YOUR_USER_ID"
$env:SHOONYA_PASSWORD = "YOUR_PASSWORD"
$env:SHOONYA_API_KEY = "YOUR_API_KEY"
$env:SHOONYA_PIN = "YOUR_PIN"
```

**Windows (CMD):**
```cmd
set SHOONYA_USER_ID=YOUR_USER_ID
set SHOONYA_PASSWORD=YOUR_PASSWORD
set SHOONYA_API_KEY=YOUR_API_KEY
set SHOONYA_PIN=YOUR_PIN
```

**Linux/Mac (Bash):**
```bash
export SHOONYA_USER_ID="YOUR_USER_ID"
export SHOONYA_PASSWORD="YOUR_PASSWORD"
export SHOONYA_API_KEY="YOUR_API_KEY"
export SHOONYA_PIN="YOUR_PIN"
```

### 4. Or Create `.env` File
Create `.env` in project root:
```
SHOONYA_USER_ID=YOUR_USER_ID
SHOONYA_PASSWORD=YOUR_PASSWORD
SHOONYA_API_KEY=YOUR_API_KEY
SHOONYA_PIN=YOUR_PIN
```

Then load in Python:
```python
from dotenv import load_dotenv
load_dotenv()
```

### 5. Install Dependencies
```bash
pip install -r requirements.txt
# or specifically:
pip install norenapi
```

### 6. Test Connection
```bash
python Live-Signal-Generator/shoonya_fetcher.py
```

Expected output:
```
🔗 Shoonya API Live Data Fetcher
✓ Shoonya API connected
📊 Fetching live NIFTY data...
✓ NIFTY: 22,713.45 +157.35 (+0.69%)
  IV: 14.2% | OI: 2,156,450 | Volume: 1,234,567
```

## How It Works in Tab 2

1. **Real-time Updates**: Every hour, fetches live NIFTY spot
2. **Live Option Premiums**: Pulls actual CE/PE prices from NSE option chain
3. **Automatic Fallback**: If Shoonya unavailable, reverts to formula-based estimation
4. **Market Hours Only**: Data updates during NSE trading hours (9:15 AM - 3:30 PM IST)

## Troubleshooting

### ❌ "Connection refused"
- Check internet connection
- Verify credentials are correct
- Ensure Shoonya servers are online (api.shoonya.com)

### ❌ "Invalid API key"
- Regenerate API key in Shoonya dashboard
- Re-set environment variables
- Restart Streamlit app

### ❌ "Token not found"
- Some strikes may not have liquidity
- App automatically skips illiquid strikes
- Formula fallback calculates premiums

### ❌ "SHOONYA_USER_ID not found"
- Check environment variables are set
- Restart terminal/IDE after setting env vars
- Use `.env` file as alternative

## Supported Symbols

| Symbol | Exchange | Example |
|--------|----------|---------|
| NIFTY | NSE | NIFTY50, NIFTY (spot) |
| SENSEX | BSE | SENSEX (spot) |
| NIFTY25CE | NFO | Option: Strike 25, Call |
| NIFTY25PE | NFO | Option: Strike 25, Put |

## API Rate Limits

- **Free tier**: ~100 quotes/second
- **No daily limit**: Unlimited data requests
- **Reconnect**: Auto-reconnect if connection drops

## Security

⚠️ **DO NOT** commit credentials to Git!
- Use environment variables or `.env`
- Add `.env` to `.gitignore`
- Never hardcode API keys in code

```bash
# In .gitignore
.env
*.env
.env.local
credentials.json
```

## Alternative: Use Without Shoonya

If Shoonya not available:
1. Tab 2 will use formula-based premium estimation
2. Spot price will fallback to NSE yesterday's close
3. Accuracy decreases without real-time data
4. Still functional for testing/paper trading

## Next Steps

1. ✅ Set up Shoonya credentials
2. ✅ Run `streamlit run app.py`
3. ✅ Check Tab 2 for live NIFTY data
4. ✅ Monitor "Prices: ✨ Shoonya API (Real-time)" indicator

---

**Questions?** Check Shoonya API docs: https://shoonya.finvasia.com/
