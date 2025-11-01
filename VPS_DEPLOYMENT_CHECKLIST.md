# VPS Deployment Checklist

## ✅ Changes Made Locally (DONE)

- [x] Added `/ships/` prefix to all Flask routes in `web_tracker.py`
- [x] Created diagnostic report
- [x] Created deployment script

## 📤 Push to VPS

### Step 1: Push changes to Git
```bash
# On your PC (in project directory)
cd c:\Users\gerrit\Desktop\apihub

git add src/services/web_tracker.py
git add DIAGNOSTIC_REPORT.md
git add deploy_to_vps.sh
git add VPS_DEPLOYMENT_CHECKLIST.md

git commit -m "Fix: Add /ships/ prefix to all Flask routes for proxy compatibility"
git push origin main
```

### Step 2: Deploy on VPS
```bash
# SSH into your VPS
ssh erik@your-vps-ip

# Navigate to project directory
cd /var/www/apihub

# Run the deployment script
bash deploy_to_vps.sh
```

**OR manually:**

```bash
# Pull latest code
git pull origin main

# Check if emissions data needs importing
python3 -c "import sqlite3; conn = sqlite3.connect('vessel_static_data.db'); cursor = conn.cursor(); cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='eu_mrv_emissions'\"); print('EXISTS' if cursor.fetchone() else 'MISSING')"

# If MISSING, import emissions data
source venv/bin/activate
python src/utils/import_mrv_data.py

# Restart web tracker
sudo systemctl restart ais-web-tracker

# Check status
sudo systemctl status ais-web-tracker
```

## 🧪 Testing

### Test 1: Check Service Status
```bash
sudo systemctl status ais-web-tracker
sudo systemctl status ais-collector
```

**Expected:** Both services should be `active (running)`

### Test 2: Test Endpoints Locally
```bash
# From VPS terminal
curl -s http://localhost:5000/ships/api/stats | python3 -m json.tool
curl -s http://localhost:5000/ships/api/vessels/combined?limit=5 | python3 -m json.tool
curl -s http://localhost:5000/ships/api/emissions/stats | python3 -m json.tool
curl -s http://localhost:5000/ships/api/emissions/match-stats | python3 -m json.tool
```

**Expected:** All should return valid JSON (not HTML error pages)

### Test 3: Check Website
Visit: https://gerritsxd.com/ships/database

**Check:**
- [ ] Page loads without errors
- [ ] Vessel table displays data
- [ ] Statistics cards show numbers
- [ ] No console errors (press F12)

### Test 4: Verify Data Flow
```bash
# Check database exists
ls -lh /var/www/apihub/vessel_static_data.db

# Check tables
sqlite3 /var/www/apihub/vessel_static_data.db "SELECT name FROM sqlite_master WHERE type='table';"

# Should show:
# - vessels_static
# - vessel_positions
# - eu_mrv_emissions (MUST exist!)

# Check record counts
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/var/www/apihub/vessel_static_data.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM vessels_static")
print(f"AIS vessels: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions")
print(f"Emissions records: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM vessels_static v INNER JOIN eu_mrv_emissions e ON v.imo = e.imo")
print(f"Matched: {cursor.fetchone()[0]}")
conn.close()
EOF
```

## 🚨 If Still Getting 500 Errors

### Check Flask Logs
```bash
sudo journalctl -u ais-web-tracker -n 100 --no-pager
```

Look for:
- Python exceptions
- Database errors
- Missing table errors

### Check Nginx Logs
```bash
sudo tail -50 /var/log/nginx/error.log
```

### Common Issues & Fixes

#### Issue: "no such table: eu_mrv_emissions"
**Fix:**
```bash
cd /var/www/apihub
source venv/bin/activate
python src/utils/import_mrv_data.py
sudo systemctl restart ais-web-tracker
```

#### Issue: Routes still returning 404
**Fix:**
```bash
# Verify web_tracker.py has /ships/ prefix
grep "@app.route" src/services/web_tracker.py | head -5

# Should show:
# @app.route('/ships/')
# @app.route('/ships/api/vessels')
# etc.

# If not, git pull again
git pull origin main
sudo systemctl restart ais-web-tracker
```

#### Issue: Services not running
**Fix:**
```bash
sudo systemctl start ais-collector
sudo systemctl start ais-web-tracker
sudo systemctl enable ais-collector
sudo systemctl enable ais-web-tracker
```

## 📊 Expected Results

After successful deployment:

### Browser (https://gerritsxd.com/ships/database)
- ✅ Vessel table with data
- ✅ Statistics: Total vessels, matched vessels, match rate
- ✅ CO2 emissions totals
- ✅ Filters working
- ✅ No console errors

### API Responses
```json
// /ships/api/vessels/combined?limit=5
[
  {
    "mmsi": 123456789,
    "name": "VESSEL NAME",
    "imo": 9876543,
    "total_co2_emissions": 123456.78,
    ...
  }
]

// /ships/api/emissions/stats
{
  "total_vessels": 16000,
  "total_co2_emissions": 123456789.0,
  "average_co2_per_vessel": 7716.0,
  ...
}

// /ships/api/emissions/match-stats
{
  "total_ais_vessels": 1050,
  "matched_vessels": 250,
  "match_rate_percentage": 23.81,
  ...
}
```

## 🎯 Success Criteria

- [ ] All systemd services running
- [ ] Database has all 3 tables
- [ ] API endpoints return JSON (not 500 errors)
- [ ] Website loads and displays vessel data
- [ ] No browser console errors
- [ ] Statistics cards populate with real numbers

## 📞 Need Help?

1. Share logs: `sudo journalctl -u ais-web-tracker -n 100 > logs.txt`
2. Check route registration: `grep "@app.route" src/services/web_tracker.py`
3. Test database: `sqlite3 vessel_static_data.db "SELECT COUNT(*) FROM eu_mrv_emissions;"`
