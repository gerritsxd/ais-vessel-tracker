# 🚢 Fix Summary: Production 500 Errors

## 🎯 Problem Identified

Your restructured project had **2 critical issues** causing 500 errors on https://gerritsxd.com/ships/database:

### Issue 1: Missing URL Prefix ⚠️ CRITICAL
- **Frontend calls:** `/ships/api/vessels/combined`
- **Flask routes defined as:** `/api/vessels/combined` ❌
- **Nginx expects:** `http://localhost:5000/ships/` → mismatch!

### Issue 2: Missing Database Table ⚠️ CRITICAL
- The `eu_mrv_emissions` table was never imported on VPS
- API queries fail when trying to JOIN with non-existent table

---

## ✅ Fixes Applied (On Your PC)

### 1. Updated Flask Routes
**File:** `src/services/web_tracker.py`

Changed **all 19 routes** from:
```python
@app.route('/api/vessels/combined')
@app.route('/api/emissions/stats')
@app.route('/database')
```

To:
```python
@app.route('/ships/api/vessels/combined')
@app.route('/ships/api/emissions/stats')
@app.route('/ships/database')
```

Now the routes match what the frontend calls AND what Nginx proxies!

---

## 📤 Next Steps (On VPS)

### Quick Deploy (Recommended)
```bash
# 1. Push changes from PC
cd c:\Users\gerrit\Desktop\apihub
git add .
git commit -m "Fix: Add /ships/ prefix to Flask routes"
git push origin main

# 2. SSH to VPS and run deployment script
ssh erik@your-vps
cd /var/www/apihub
bash deploy_to_vps.sh
```

The script will:
- ✅ Pull latest code
- ✅ Check & import emissions data if missing
- ✅ Restart services
- ✅ Test all endpoints
- ✅ Show database statistics

---

## 🗂️ Files Created

1. **DIAGNOSTIC_REPORT.md** - Detailed technical analysis
2. **deploy_to_vps.sh** - Automated deployment script
3. **VPS_DEPLOYMENT_CHECKLIST.md** - Step-by-step manual guide
4. **SUMMARY.md** - This file

---

## 🏗️ Architecture Overview

Your project has these components:

```
┌─────────────────────────────────────────────────────────┐
│  COLLECTOR LAYER (Background Services)                  │
├─────────────────────────────────────────────────────────┤
│  ais-collector.service                                  │
│  ├─ Streams AIS data from AISStream WebSocket          │
│  ├─ Filters vessels ≥100m                              │
│  ├─ Populates: vessels_static table                    │
│  └─ Enriches with company names                        │
│                                                         │
│  ONE-TIME SETUP: import_mrv_data.py                    │
│  ├─ Imports EU MRV Excel file                          │
│  └─ Creates: eu_mrv_emissions table                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  WEB SERVICE LAYER                                      │
├─────────────────────────────────────────────────────────┤
│  ais-web-tracker.service (Flask App)                   │
│  ├─ Serves HTML templates                              │
│  ├─ Exposes REST API                                   │
│  └─ JOINs vessels_static + eu_mrv_emissions           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  FRONTEND LAYER                                         │
├─────────────────────────────────────────────────────────┤
│  database_enhanced.html                                │
│  ├─ Calls: /ships/api/vessels/combined                │
│  ├─ Calls: /ships/api/emissions/stats                 │
│  ├─ Calls: /ships/api/emissions/match-stats           │
│  └─ Renders interactive vessel table                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  PROXY LAYER                                            │
├─────────────────────────────────────────────────────────┤
│  Nginx: /ships/ → http://localhost:5000/ships/        │
└─────────────────────────────────────────────────────────┘
```

---

## 🧪 How to Verify It's Fixed

After deploying, test:

### 1. Service Status
```bash
sudo systemctl status ais-web-tracker
# Should show: active (running)
```

### 2. API Endpoints (on VPS)
```bash
curl http://localhost:5000/ships/api/stats
curl http://localhost:5000/ships/api/vessels/combined?limit=5
curl http://localhost:5000/ships/api/emissions/stats
```
**Expected:** JSON responses, not HTML errors

### 3. Website
Visit: https://gerritsxd.com/ships/database
- ✅ Vessel table populates
- ✅ Statistics show numbers
- ✅ No console errors (F12)

---

## 🔍 Why This Happened

After your project restructure:
1. Services moved to `src/services/` ✅
2. Collectors moved to `src/collectors/` ✅
3. **But routes weren't updated with `/ships/` prefix** ❌
4. **And emissions data wasn't imported on VPS** ❌

This broke the connection between:
- Frontend → API (wrong URLs)
- API → Database (missing table)

---

## 📊 Database Schema

Your SQLite database should have:

| Table | Records | Created By | Purpose |
|-------|---------|------------|---------|
| `vessels_static` | ~1,050 | ais-collector | AIS vessel data |
| `vessel_positions` | Many | ais-collector | Position history |
| `eu_mrv_emissions` | ~16,000 | import_mrv_data.py | CO2 emissions data |

**Join key:** `vessels_static.imo = eu_mrv_emissions.imo`

---

## 🎓 What You Learned

### Communication Between Services:
- **Data Collectors** → Write to database
- **Web Service** → Reads from database, serves API
- **Frontend** → Calls API endpoints
- **Nginx** → Proxies requests to Flask

### Common Pitfalls:
- ✅ Routes must match frontend calls
- ✅ Routes must match proxy configuration
- ✅ Database tables must exist before querying
- ✅ Services need to run for system to work

---

## 🚀 Production Checklist

### Required Services:
- [x] `ais-collector` - Populates vessel data
- [x] `ais-web-tracker` - Serves API and frontend
- [ ] `ais-emissions-matcher` - Optional, auto-matches vessels
- [ ] `ais-econowind-updater` - Optional, calculates fit scores

### Required Data:
- [x] `vessels_static` table - From AIS collector
- [x] `vessel_positions` table - From AIS collector
- [x] `eu_mrv_emissions` table - **Must import manually!**

### Configuration:
- [x] API keys in `api.txt`
- [x] Nginx proxy configured
- [x] Flask routes with `/ships/` prefix
- [x] Systemd services enabled

---

## 💡 Pro Tips

### Monitor Services:
```bash
# Watch logs in real-time
sudo journalctl -u ais-web-tracker -f

# Check all services at once
systemctl status ais-* --no-pager
```

### Query Database:
```bash
sqlite3 vessel_static_data.db
> SELECT COUNT(*) FROM vessels_static;
> SELECT COUNT(*) FROM eu_mrv_emissions;
> .quit
```

### Restart After Changes:
```bash
# After code changes
sudo systemctl restart ais-web-tracker

# After database changes
# No restart needed, Flask reconnects each query
```

---

## 🎉 Expected Results

Once deployed:

### API Responses:
- `/ships/api/vessels/combined` → Array of vessels with emissions
- `/ships/api/emissions/stats` → Overall CO2 statistics
- `/ships/api/emissions/match-stats` → Matching statistics

### Website Features:
- Interactive vessel table with sorting/filtering
- CO2 emissions data integrated
- Company information displayed
- Match statistics visible

### No More Errors:
- ✅ No 500 Internal Server Errors
- ✅ No "vessels.forEach is not a function"
- ✅ No missing table errors

---

## 📞 Still Having Issues?

Check in this order:

1. **Services running?**
   ```bash
   sudo systemctl status ais-web-tracker
   ```

2. **Code updated?**
   ```bash
   grep "@app.route('/ships/" src/services/web_tracker.py | head -3
   ```

3. **Database has emissions?**
   ```bash
   sqlite3 vessel_static_data.db "SELECT COUNT(*) FROM eu_mrv_emissions;"
   ```

4. **Check logs:**
   ```bash
   sudo journalctl -u ais-web-tracker -n 50
   ```

---

## ✨ You're Ready to Deploy!

Run the deployment script and your database page should work perfectly! 🚀
