# STEP 4: Push Database to AWS RDS (Cloud)

## Overview
Move your **103,359 real Kaggle records** to AWS cloud so you can access them from anywhere.

---

## Part 1: Create AWS RDS Instance (5-10 minutes)

### 1. Sign up for AWS (if needed)
- Go to: https://aws.amazon.com
- Click **"Create AWS Account"**
- Use your email: `prabhu.ken01@gmail.com`
- You get **1 year free tier** (no payment needed)

### 2. Create PostgreSQL Database

1. Log into AWS Console: https://console.aws.amazon.com
2. Search for **"RDS"** → Click **RDS** service
3. Click **"Create database"**
4. Fill in:

```
✓ Engine: PostgreSQL
✓ Version: 15.x (latest)
✓ Templates: Free tier
✓ DB instance identifier: nifty-options-db
✓ Master username: postgres
✓ Master password: [CREATE STRONG PASSWORD - SAVE IT!]
✓ Database name: nifty_sensex_options
✓ Public accessibility: YES (to access from anywhere)
✓ Create database
```

5. **WAIT 5-10 MINUTES** for database to be created
6. Once created, click on the instance to see:
   - **Endpoint** (looks like: `nifty-options-db.xxxxx.rds.amazonaws.com`)
   - **Port** (5432)

**Save these credentials:**
```
Host: nifty-options-db.xxxxx.rds.amazonaws.com
Port: 5432
Database: nifty_sensex_options
User: postgres
Password: YOUR_PASSWORD
```

---

## Part 2: Backup Local Database (1 minute)

Open **Command Prompt** and run:

```bash
cd "E:\Personal\Trading_Champion\Projects\Nifty Weekly Options Strategy_v1\Database_v1\Files-v1"

pg_dump -h localhost -U postgres -d nifty_sensex_options > nifty_kaggle_backup.sql
```

This creates a file: `nifty_kaggle_backup.sql` (contains all 103,359 records)

---

## Part 3: Restore to AWS (2 minutes)

Once AWS RDS instance is **AVAILABLE** (status shows green), run:

```bash
psql -h nifty-options-db.xxxxx.rds.amazonaws.com -U postgres -d nifty_sensex_options < nifty_kaggle_backup.sql
```

**Replace:**
- `nifty-options-db.xxxxx.rds.amazonaws.com` with your actual endpoint from AWS

**When prompted for password:** Enter the password you created in Part 1

**Wait for restore** (takes ~1-2 minutes)

---

## Part 4: Verify Cloud Access (1 minute)

Create file: `verify_cloud_db.py`

```python
import psycopg2

# Replace with YOUR values from AWS RDS
connection_params = {
    'host': 'nifty-options-db.xxxxx.rds.amazonaws.com',  # Your AWS endpoint
    'port': 5432,
    'database': 'nifty_sensex_options',
    'user': 'postgres',
    'password': 'YOUR_PASSWORD'  # Your password
}

try:
    conn = psycopg2.connect(**connection_params)
    cur = conn.cursor()

    # Check record count
    cur.execute("SELECT COUNT(*) FROM option_bars_daily")
    count = cur.fetchone()[0]

    # Check date range
    cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM option_bars_daily")
    min_date, max_date = cur.fetchone()

    # Check Greeks
    cur.execute("SELECT AVG(iv), MIN(delta), MAX(delta) FROM option_bars_daily WHERE delta IS NOT NULL")
    avg_iv, min_delta, max_delta = cur.fetchone()

    print("=" * 80)
    print("SUCCESS! Cloud Database Connected!")
    print("=" * 80)
    print(f"Records: {count:,}")
    print(f"Date range: {min_date.date()} to {max_date.date()}")
    print(f"Greeks: IV avg={avg_iv:.2f}%, Delta range={min_delta:.4f} to {max_delta:.4f}")
    print("=" * 80)
    print("\nYour database is now accessible from ANYWHERE!")
    print(f"Connect string: postgres://postgres@nifty-options-db.xxxxx.rds.amazonaws.com:5432/nifty_sensex_options")

    cur.close()
    conn.close()

except Exception as e:
    print(f"ERROR: {e}")
    print("Check your credentials and try again")
```

Run:
```bash
python verify_cloud_db.py
```

---

## Part 5: Access from Anywhere

Once verified, you can access your cloud database from:

### Python Script
```python
import psycopg2

conn = psycopg2.connect(
    host="nifty-options-db.xxxxx.rds.amazonaws.com",
    user="postgres",
    password="YOUR_PASSWORD",
    database="nifty_sensex_options"
)

cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM option_bars_daily")
print(f"Records: {cur.fetchone()[0]:,}")
```

### DBeaver
1. New Database Connection → PostgreSQL
2. Host: `nifty-options-db.xxxxx.rds.amazonaws.com`
3. Database: `nifty_sensex_options`
4. Username: `postgres`
5. Password: `YOUR_PASSWORD`
6. Test Connection → Connect

### Command Line
```bash
psql -h nifty-options-db.xxxxx.rds.amazonaws.com -U postgres -d nifty_sensex_options
```

---

## Summary

| Step | Action | Time |
|------|--------|------|
| 1 | Create AWS RDS instance | 10 min |
| 2 | Backup local database | 1 min |
| 3 | Restore to AWS | 2 min |
| 4 | Verify connection | 1 min |
| **TOTAL** | **Cloud database ready** | **~15 min** |

---

## Cost

- **Free tier:** 1 year free for `db.t3.micro`
- **After free tier:** ~$10-15/month
- **Your usage:** 103K records ≈ minimal cost

---

## Troubleshooting

### Connection refused
- Check AWS security group allows inbound on port 5432
- Verify RDS instance status is "Available" (green)
- Check endpoint URL is correct

### Password not accepted
- Make sure you're using the password from Part 1
- Passwords are case-sensitive

### Records not restored
- Run backup command again (may not have finished)
- Check backup file size: `ls -lah nifty_kaggle_backup.sql`

---

## Next Steps

1. ✅ Create AWS RDS instance
2. ✅ Backup & restore database
3. ✅ Verify cloud access
4. 📊 Build backtesting system using cloud database
5. 🚀 Deploy live trading system

---

**Your database is now production-ready in the cloud!** 🎉
