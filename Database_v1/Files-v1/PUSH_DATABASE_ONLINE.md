# Push PostgreSQL Database Online to AWS RDS

## **STEP-BY-STEP: Host Database in Cloud**

### **OPTION A: AWS RDS (Recommended - Free tier available)**

#### **1. Create AWS Account**
- Go to: https://aws.amazon.com/rds/
- Click **"Get started free"** (1 year free tier)
- Sign up with your email

#### **2. Create RDS PostgreSQL Database**

In AWS Console:
1. Navigate to **RDS → Databases → Create database**

2. Configure:
```
Engine: PostgreSQL
Version: 15.x (latest)
DB instance class: db.t3.micro (free tier)
DB instance identifier: nifty-options-db
Master username: postgres
Master password: (choose strong password - save it!)
```

3. Network:
```
Public accessibility: YES (to access from anywhere)
VPC security group: Create new (allow inbound PostgreSQL 5432)
```

4. Additional configuration:
```
Initial database name: nifty_sensex_options
```

5. **Create database** - Takes ~5-10 minutes

#### **3. Note Your Connection Details**

After creation, you'll see:
```
Endpoint: nifty-options-db.xxxxx.rds.amazonaws.com
Port: 5432
Database: nifty_sensex_options
User: postgres
Password: (your password)
```

---

### **STEP 4: Backup and Restore to Cloud**

#### **4a. Backup Local Database**

```bash
pg_dump -h localhost -U postgres -d nifty_sensex_options > backup.sql
```

Or use Python:
```python
import subprocess

result = subprocess.run([
    "pg_dump",
    "-h", "localhost",
    "-U", "postgres",
    "-d", "nifty_sensex_options"
], capture_output=True, text=True)

with open("backup.sql", "w") as f:
    f.write(result.stdout)

print("Backup created: backup.sql")
```

#### **4b. Restore to AWS RDS**

```bash
psql -h nifty-options-db.xxxxx.rds.amazonaws.com -U postgres -d nifty_sensex_options < backup.sql
```

Or use Python:
```python
import psycopg2

# Read backup
with open("backup.sql", "r") as f:
    backup_content = f.read()

# Connect to AWS RDS
conn = psycopg2.connect(
    host="nifty-options-db.xxxxx.rds.amazonaws.com",  # Your RDS endpoint
    port=5432,
    database="nifty_sensex_options",
    user="postgres",
    password="YOUR_PASSWORD"
)

cur = conn.cursor()
cur.execute(backup_content)
conn.commit()
cur.close()
conn.close()

print("Restored to AWS RDS successfully!")
```

---

### **STEP 5: Verify Connection from Anywhere**

```python
import psycopg2

conn = psycopg2.connect(
    host="nifty-options-db.xxxxx.rds.amazonaws.com",
    port=5432,
    database="nifty_sensex_options",
    user="postgres",
    password="YOUR_PASSWORD"
)

cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM option_bars_daily")
count = cur.fetchone()[0]
print(f"[OK] Connected to cloud! Database has {count} records")

cur.close()
conn.close()
```

---

## **OPTION B: Azure Database for PostgreSQL (Also Free Tier)**

Similar process to AWS but via Azure portal.

---

## **OPTION C: Google Cloud SQL (Also Free Tier)**

Similar process but via Google Cloud Console.

---

## **Security Best Practices**

1. **Never share endpoint + password publicly**
2. Use **VPC security groups** to restrict access to specific IPs
3. **Enable SSL** for connections
4. Regular **automated backups** (AWS handles this)
5. **Rotate passwords** periodically

---

## **Cost Estimate**

| Service | Cost | Free Tier |
|---------|------|-----------|
| **AWS RDS** | $0.02/hour | 750 hrs/month (12 months) |
| **Azure PostgreSQL** | $0.01/hour | 12 months free |
| **Google Cloud SQL** | $0.01/hour | $300 credit |

For 880 records database: **~$5-10/month** after free tier ends

---

## **Alternative: Simple HTTP API (Easiest)**

Instead of exposing database directly, create a REST API:

```python
from flask import Flask, jsonify
import psycopg2

app = Flask(__name__)

@app.route('/api/options', methods=['GET'])
def get_options():
    conn = psycopg2.connect("dbname=nifty_sensex_options ...")
    cur = conn.cursor()
    cur.execute("SELECT * FROM option_bars_daily LIMIT 100")

    results = []
    for row in cur.fetchall():
        results.append({
            'timestamp': str(row[0]),
            'symbol': row[1],
            'strike': row[2],
            # ... more fields
        })

    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

Deploy on **Heroku, Render, Railway** (free tier available)

---

## **Summary**

1. **Create AWS RDS PostgreSQL** (5 mins)
2. **Backup local database** (`pg_dump`)
3. **Restore to RDS** (psql or Python)
4. **Access from anywhere** with connection string
5. **Cost:** Free for 1 year, then ~$5-10/month

**Next:** Once Kaggle download finishes, we process data → load to local DB → backup → push to AWS RDS
