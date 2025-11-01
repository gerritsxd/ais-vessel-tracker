# 🚀 EU MRV Emissions Integration - Deployment Guide

## 🎯 What We Built

A **hybrid database system** that automatically matches your growing AIS vessel database with EU MRV emissions data:

- **13,964 vessels** with emissions data imported
- **Automatic background matching** as new vessels are discovered
- **Real-time statistics** API
- **6 new API endpoints** for emissions queries
- **Continuous monitoring** service

## 📦 New Files Created

### Core Files
1. **`import_mrv_data.py`** - One-time import of EU MRV Excel data
2. **`emissions_matcher.py`** - Background service for continuous matching
3. **`ais-emissions-matcher.service`** - Systemd service file
4. **`EMISSIONS_FEATURE.md`** - Feature documentation
5. **`EMISSIONS_DEPLOYMENT.md`** - This file

### Modified Files
1. **`web_tracker.py`** - Added 6 new API endpoints
2. **`requirements.txt`** - Added pandas and openpyxl

### Analysis Files (Optional)
- `analyze_mrv.py`
- `analyze_mrv_simple.py`
- `mrv_columns.txt`

## 🔧 VPS Deployment Steps

### Step 1: Upload Files to VPS

```bash
# From your local machine
cd c:\Users\gerrit\Desktop\apihub

# Upload the Excel file (if not already on VPS)
scp "2024-v99-22102025-EU MRV Publication of information.xlsx" erik@149.202.53.2:/var/www/apihub/

# Or commit and push everything to GitHub
git add import_mrv_data.py emissions_matcher.py ais-emissions-matcher.service web_tracker.py requirements.txt EMISSIONS_*.md
git commit -m "Add EU MRV emissions integration with automatic matching"
git push origin master
```

### Step 2: SSH into VPS and Pull Changes

```bash
ssh erik@149.202.53.2
cd /var/www/apihub
git pull origin master
```

### Step 3: Install Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
# This will install pandas==2.3.3 and openpyxl==3.1.5
deactivate
```

### Step 4: Import EU MRV Data (One-Time)

```bash
cd /var/www/apihub
source venv/bin/activate
python import_mrv_data.py
```

**Expected output:**
```
================================================================================
EU MRV EMISSIONS DATA IMPORT
================================================================================

✓ EU MRV emissions table created
✓ Loaded 13964 records
✓ Cleaned data: 13964 valid records
✓ Inserted: 13964 new records

Total vessels with emissions data: 13964
Unique companies: 3544
Total CO2 emissions: 145,913,862 tonnes
Vessels matched with AIS data: 1220
```

### Step 5: Set Up Emissions Matcher Service

```bash
# Copy service file
sudo cp ais-emissions-matcher.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable ais-emissions-matcher

# Start the service
sudo systemctl start ais-emissions-matcher

# Check status
sudo systemctl status ais-emissions-matcher
```

### Step 6: Restart Web Tracker

```bash
sudo systemctl restart ais-web-tracker
sudo systemctl status ais-web-tracker
```

### Step 7: Verify Everything is Running

```bash
# Check all services
sudo systemctl status ais-collector
sudo systemctl status ais-web-tracker
sudo systemctl status ais-emissions-matcher

# View matcher logs
sudo journalctl -u ais-emissions-matcher -f
```

## ✅ Testing the Deployment

### Test API Endpoints

```bash
# 1. Get emissions statistics
curl http://localhost:5000/ships/api/emissions/stats | jq

# 2. Get matching statistics
curl http://localhost:5000/ships/api/emissions/match-stats | jq

# 3. Get top emitters
curl http://localhost:5000/ships/api/emissions/top?limit=10 | jq

# 4. Get combined vessel data
curl http://localhost:5000/ships/api/vessels/combined?limit=20 | jq

# 5. Get specific vessel emissions (example IMO)
curl http://localhost:5000/ships/api/emissions/vessel/9321483 | jq

# 6. Get company emissions
curl "http://localhost:5000/ships/api/emissions/company/Maersk" | jq
```

### Test from Browser

```
http://149.202.53.2:5000/ships/api/emissions/stats
http://149.202.53.2:5000/ships/api/emissions/match-stats
http://149.202.53.2:5000/ships/api/emissions/top?limit=20
```

## 📊 How the Matching Works

### Automatic Background Process

The `emissions_matcher.py` service:

1. **Runs every 5 minutes** (configurable)
2. **Scans `vessels_static`** for vessels with IMO numbers
3. **Checks if they exist** in `eu_mrv_emissions`
4. **Reports matches** in real-time
5. **Tracks statistics** (match rate, new matches, etc.)

### Matching Logic

```
AIS Database (vessels_static)
    ↓ (has IMO number?)
    ↓
Check EU MRV Database (eu_mrv_emissions)
    ↓ (IMO exists?)
    ↓
✓ MATCH! → Vessel now has both AIS + Emissions data
```

### What Gets Matched

- **IMO Number** is the primary key for matching
- When matched, you can query:
  - Live AIS data (MMSI, position, speed, etc.)
  - Emissions data (CO2, fuel, efficiency, etc.)
  - Combined queries for powerful analytics

## 🔍 Monitoring

### View Matcher Logs

```bash
# Real-time logs
sudo journalctl -u ais-emissions-matcher -f

# Last 100 lines
sudo journalctl -u ais-emissions-matcher -n 100

# Logs from today
sudo journalctl -u ais-emissions-matcher --since today
```

### Check Matching Statistics

```bash
# Via API
curl http://localhost:5000/ships/api/emissions/match-stats

# Via SQL
sqlite3 /var/www/apihub/vessel_static_data.db "
SELECT 
    (SELECT COUNT(*) FROM vessels_static WHERE imo IS NOT NULL) as ais_with_imo,
    (SELECT COUNT(*) FROM eu_mrv_emissions) as emissions_total,
    (SELECT COUNT(*) FROM vessels_static v INNER JOIN eu_mrv_emissions e ON v.imo = e.imo) as matched
"
```

### Service Management

```bash
# Start/Stop/Restart
sudo systemctl start ais-emissions-matcher
sudo systemctl stop ais-emissions-matcher
sudo systemctl restart ais-emissions-matcher

# Enable/Disable auto-start
sudo systemctl enable ais-emissions-matcher
sudo systemctl disable ais-emissions-matcher

# Check status
sudo systemctl status ais-emissions-matcher
```

## 🎯 Expected Results

### Initial State (After Import)
- **13,964 vessels** in emissions database
- **~1,220 vessels** matched with AIS data (based on your current DB)
- **Match rate**: ~10-20% (depends on your AIS coverage)

### As Your AIS Database Grows
- **New vessels discovered** by `ais_collector.py`
- **Automatically checked** by `emissions_matcher.py` every 5 minutes
- **Match rate increases** as you collect more vessels
- **Real-time statistics** available via API

### Example Growth Scenario

```
Day 1:  1,220 matches (10% match rate)
Day 7:  2,500 matches (15% match rate)
Day 30: 5,000 matches (25% match rate)
```

## 🔧 Configuration

### Adjust Matching Frequency

Edit `emissions_matcher.py`:
```python
CHECK_INTERVAL = 300  # Change to 60 for 1 minute, 600 for 10 minutes, etc.
```

### Adjust Batch Size

```python
BATCH_SIZE = 100  # Process more or fewer vessels per check
```

## 📈 API Endpoints Summary

| Endpoint | Description |
|----------|-------------|
| `/api/emissions/stats` | Overall emissions statistics |
| `/api/emissions/match-stats` | Real-time matching statistics |
| `/api/emissions/top` | Top CO2 emitters |
| `/api/emissions/vessel/<imo>` | Specific vessel emissions |
| `/api/emissions/company/<name>` | Company fleet emissions |
| `/api/vessels/combined` | Vessels with both AIS + emissions |

## 🐛 Troubleshooting

### Matcher Not Running

```bash
# Check service status
sudo systemctl status ais-emissions-matcher

# View errors
sudo journalctl -u ais-emissions-matcher -n 50

# Restart service
sudo systemctl restart ais-emissions-matcher
```

### No Matches Found

```bash
# Check if emissions data was imported
sqlite3 /var/www/apihub/vessel_static_data.db "SELECT COUNT(*) FROM eu_mrv_emissions"

# Check if AIS vessels have IMO numbers
sqlite3 /var/www/apihub/vessel_static_data.db "SELECT COUNT(*) FROM vessels_static WHERE imo IS NOT NULL"
```

### Database Locked Errors

The matcher uses WAL mode and 30-second timeouts. If you still see errors:
```bash
# Check if multiple processes are accessing the DB
ps aux | grep python

# Restart all services
sudo systemctl restart ais-collector
sudo systemctl restart ais-web-tracker
sudo systemctl restart ais-emissions-matcher
```

## 🎉 Success Indicators

✅ All three services running:
```bash
sudo systemctl status ais-collector ais-web-tracker ais-emissions-matcher
```

✅ API endpoints responding:
```bash
curl http://localhost:5000/ships/api/emissions/match-stats
```

✅ Matcher logs showing activity:
```bash
sudo journalctl -u ais-emissions-matcher -n 20
```

✅ Match rate increasing over time

## 📝 Next Steps

1. **Monitor the matcher** for the first few hours
2. **Check match statistics** daily
3. **Build UI dashboards** to visualize emissions data
4. **Create alerts** for high-emitting vessels
5. **Export reports** for analysis

## 🔗 Related Documentation

- `EMISSIONS_FEATURE.md` - Detailed feature documentation
- `SQL_QUERY_CHEATSHEET.txt` - SQL query examples
- `SHIP_TYPE_CHEATSHEET.md` - Ship type reference

---

**You now have a self-updating hybrid database that grows smarter every day!** 🌍🚢📊
