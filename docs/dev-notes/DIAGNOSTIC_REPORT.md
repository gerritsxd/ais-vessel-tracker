# 🔍 Diagnostic Report: Production 500 Errors

**Date:** Nov 1, 2025  
**Site:** https://gerritsxd.com/ships/database  
**Status:** ❌ Multiple 500 Internal Server Errors

---

## 🚨 Current Errors

### Console Errors Reported:
1. `GET /ships/api/vessels/combined?limit=1000` → **500 (INTERNAL SERVER ERROR)**
2. `GET /ships/api/emissions/match-stats` → **500 (INTERNAL SERVER ERROR)**  
3. `GET /ships/api/emissions/stats` → **500 (INTERNAL SERVER ERROR)**
4. `TypeError: vessels.forEach is not a function` → API not returning array

---

## 🔎 Root Cause Analysis

### **ISSUE #1: Missing URL Prefix in Flask Routes** ⚠️ **CRITICAL**

**Problem:**
- Frontend HTML calls: `/ships/api/vessels/combined`
- Flask routes defined as: `/api/vessels/combined` (NO `/ships/` prefix)
- Nginx proxy expects: `proxy_pass http://localhost:5000/ships/`

**Evidence:**
- `database_enhanced.html:800` → `fetch('/ships/api/vessels/combined?limit=1000')`
- `database_enhanced.html:868-869` → `fetch('/ships/api/stats')` and `fetch('/ships/api/emissions/match-stats')`
- `database_enhanced.html:876` → `fetch('/ships/api/emissions/stats')`
- `web_tracker.py:363` → `@app.route('/database')` (missing `/ships/` prefix)
- `web_tracker.py:1063` → `@app.route('/api/vessels/combined')` (missing `/ships/` prefix)

**Impact:**
- All API calls are hitting wrong paths
- Returns 404 (which might be masked as 500 by proxy)
- No data reaches the frontend

---

### **ISSUE #2: Missing Database Table** ⚠️ **CRITICAL**

**Problem:**
The `eu_mrv_emissions` table may not exist on the VPS database.

**Required Tables:**
1. ✅ `vessels_static` - Created by `ais_collector.py`
2. ✅ `vessel_positions` - Created by `ais_collector.py`
3. ❌ `eu_mrv_emissions` - **Must be imported manually**

**Evidence:**
- `web_tracker.py:1020-1022` → Queries `eu_mrv_emissions` table
- `web_tracker.py:1086` → `INNER JOIN eu_mrv_emissions e ON v.imo = e.imo`
- `import_mrv_data.py:23-98` → Script to create this table

**Impact:**
- SQL queries fail with "no such table" error
- Returns 500 errors for all emissions endpoints

---

### **ISSUE #3: Services Not Running or Not Communicating** ⚠️ **HIGH**

**Required Services on VPS:**
1. ✅ `ais-collector.service` - Collects AIS data → Populates `vessels_static`
2. ✅ `ais-web-tracker.service` - Flask web app → Serves API and frontend
3. ❓ `ais-emissions-matcher.service` - Background matcher (optional but useful)
4. ❓ `ais-econowind-updater.service` - Updates fit scores (optional)

**Check Status:**
```bash
sudo systemctl status ais-collector
sudo systemctl status ais-web-tracker
sudo systemctl status ais-emissions-matcher
sudo systemctl status ais-econowind-updater
```

---

## 📋 Data Flow (How It Should Work)

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA COLLECTION                          │
├─────────────────────────────────────────────────────────────────┤
│ 1. ais_collector.py                                             │
│    ├─ Connects to AISStream WebSocket                          │
│    ├─ Filters vessels ≥100m                                     │
│    ├─ Saves to vessels_static table                            │
│    └─ Enriches with company names                              │
│                                                                  │
│ 2. import_mrv_data.py (ONE-TIME SETUP)                         │
│    ├─ Reads EU MRV Excel file                                  │
│    ├─ Creates eu_mrv_emissions table                           │
│    └─ Links vessels by IMO number                              │
├─────────────────────────────────────────────────────────────────┤
│                         WEB SERVICE                              │
├─────────────────────────────────────────────────────────────────┤
│ 3. web_tracker.py                                               │
│    ├─ Flask app serves API and HTML                            │
│    ├─ Queries both tables (JOIN on IMO)                        │
│    └─ Returns combined vessel + emissions data                 │
├─────────────────────────────────────────────────────────────────┤
│                         FRONTEND                                 │
├─────────────────────────────────────────────────────────────────┤
│ 4. database_enhanced.html                                       │
│    ├─ Fetches: /ships/api/vessels/combined                     │
│    ├─ Fetches: /ships/api/emissions/stats                      │
│    ├─ Fetches: /ships/api/emissions/match-stats                │
│    └─ Renders interactive table                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ SOLUTION: Step-by-Step Fixes

### **FIX #1: Add URL Prefix to Flask App**

**Option A: Use Flask Blueprint (Recommended)**

Create a Blueprint with `/ships` prefix and register all routes under it.

**Option B: Configure APPLICATION_ROOT**

Add to `web_tracker.py` before route definitions:
```python
app.config['APPLICATION_ROOT'] = '/ships'
```

**Option C: Wrap App with DispatcherMiddleware**

Use Werkzeug's DispatcherMiddleware to mount the app at `/ships`.

**Option D: Manually Add Prefix to All Routes**

Change every `@app.route('/...')` to `@app.route('/ships/...')`.

---

### **FIX #2: Import EU MRV Emissions Data**

**On VPS, run:**
```bash
cd /var/www/apihub
source venv/bin/activate

# Make sure the Excel file exists in data/ directory
ls data/2024-v99-*.xlsx

# Run import script
python src/utils/import_mrv_data.py

# Verify table was created
python -c "
import sqlite3
conn = sqlite3.connect('vessel_static_data.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions')
print(f'Emissions records: {cursor.fetchone()[0]}')
conn.close()
"
```

**Expected Output:**
- Table created with ~16,000+ emissions records
- Matches vessels by IMO number

---

### **FIX #3: Restart Services**

```bash
# Restart web tracker to pick up changes
sudo systemctl restart ais-web-tracker

# Check status
sudo systemctl status ais-web-tracker

# View logs
sudo journalctl -u ais-web-tracker -f
```

---

## 🧪 Testing After Fixes

### Test Endpoints Directly:
```bash
# Test 1: Check if Flask is running
curl http://localhost:5000/ships/

# Test 2: Check vessels endpoint
curl http://localhost:5000/ships/api/vessels/combined?limit=10

# Test 3: Check emissions stats
curl http://localhost:5000/ships/api/emissions/stats

# Test 4: Check match stats
curl http://localhost:5000/ships/api/emissions/match-stats
```

### Expected Responses:
- All should return JSON (not HTML error pages)
- `/api/vessels/combined` should return an array of vessel objects
- `/api/emissions/stats` should return statistics object
- `/api/emissions/match-stats` should return matching statistics

---

## 📁 Files That Need Changes

### Priority 1 (Critical):
1. `src/services/web_tracker.py` - Add `/ships/` prefix to all routes
2. VPS: Import emissions data using `import_mrv_data.py`

### Priority 2 (Verify):
3. Check systemd services are running
4. Verify nginx config has correct proxy settings
5. Ensure database file exists at `/var/www/apihub/vessel_static_data.db`

---

## 🔧 Quick Fix Commands (Copy-Paste for VPS)

```bash
# SSH into VPS
ssh your-vps

# Navigate to project
cd /var/www/apihub

# Check services
sudo systemctl status ais-web-tracker
sudo systemctl status ais-collector

# Check database
ls -lh vessel_static_data.db

# Check if emissions table exists
python3 -c "
import sqlite3
conn = sqlite3.connect('vessel_static_data.db')
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
print('Tables:', [row[0] for row in cursor.fetchall()])
conn.close()
"

# View recent logs
sudo journalctl -u ais-web-tracker -n 50
```

---

## 📊 Current Architecture Issues

```
┌────────────────────────────────────────────────────────────┐
│ Browser: https://gerritsxd.com/ships/database             │
└─────────────────────┬──────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────┐
│ Frontend JS calls:                                         │
│   GET /ships/api/vessels/combined                         │
│   GET /ships/api/emissions/stats                          │
│   GET /ships/api/emissions/match-stats                    │
└─────────────────────┬──────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────┐
│ Nginx proxy: proxy_pass http://localhost:5000/ships/      │
└─────────────────────┬──────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────┐
│ Flask routes: @app.route('/api/vessels/combined')         │
│                                 ⬆ MISSING /ships/ PREFIX!  │
└────────────────────────────────────────────────────────────┘
              ❌ 404 → Masked as 500 error
```

**The mismatch between expected path and actual route causes all 500 errors!**

---

## 🎯 Next Steps

1. **Immediate**: Fix URL prefix in Flask app
2. **Required**: Import emissions data on VPS
3. **Verify**: Check all services are running
4. **Test**: Verify endpoints return correct data
5. **Monitor**: Check logs for any remaining errors

---

## 📞 Need Help?

If issues persist after fixes:
1. Check Flask logs: `sudo journalctl -u ais-web-tracker -n 100`
2. Check Nginx error log: `sudo tail -f /var/log/nginx/error.log`
3. Test database queries manually
4. Verify file permissions on VPS
