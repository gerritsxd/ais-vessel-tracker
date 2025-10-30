# 🔄 Econowind Fit Score Auto-Updater

## 🎯 What It Does

This background service **continuously recalculates** Econowind fit scores every hour, ensuring scores stay up-to-date as:
- New vessels are added to the AIS database (with length data)
- Vessel data is updated
- The database grows

## 🚀 VPS Setup

### 1. Commit and Push

```bash
# Local machine
cd c:\Users\gerrit\Desktop\apihub
git add econowind_score_updater.py ais-econowind-updater.service requirements.txt ECONOWIND_UPDATER_SETUP.md
git commit -m "Add continuous Econowind fit score updater service"
git push origin master
```

### 2. Deploy on VPS

```bash
# SSH to VPS
ssh erik@149.202.53.2

# Pull changes
cd /var/www/apihub
git pull origin master

# Install numpy (if not already installed)
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Copy service file
sudo cp ais-econowind-updater.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable ais-econowind-updater

# Start the service
sudo systemctl start ais-econowind-updater

# Check status
sudo systemctl status ais-econowind-updater
```

### 3. Verify It's Working

```bash
# View real-time logs
sudo journalctl -u ais-econowind-updater -f

# Check all services
sudo systemctl status ais-collector ais-web-tracker ais-emissions-matcher ais-econowind-updater
```

## ⚙️ Configuration

### Update Frequency

Edit `econowind_score_updater.py` to change how often scores are recalculated:

```python
CHECK_INTERVAL = 3600  # 3600 = 1 hour, 1800 = 30 min, 7200 = 2 hours
```

### Batch Size

```python
BATCH_SIZE = 500  # Process 500 vessels at a time
```

## 📊 How Scoring Works

The service recalculates scores based on:

1. **Ship Type** (0-2 points)
   - Bulk carrier, General cargo, Chemical tanker, LNG carrier, Ro-Ro cargo = +2

2. **Vessel Length** (0-2 points) - **Uses AIS data!**
   - 100-160m = +2 points
   - 80-100m or 160-200m = +1 point

3. **CO₂ Emissions Intensity** (0-2 points)
   - Top 25% emitters = +2 points
   - Above median = +1 point

4. **Technical Efficiency** (0-2 points)
   - > 10 gCO₂/t·nm = +2 points
   - 6-10 gCO₂/t·nm = +1 point

**Total Score: 0-8 points**

## 🔍 Why This Is Better

### Before (Manual Import):
- ❌ Scores only calculated once during import
- ❌ New AIS vessels don't get scored
- ❌ Length data from AIS not used for existing vessels
- ❌ Manual re-import required to update scores

### After (Continuous Updater):
- ✅ Scores recalculated every hour
- ✅ New AIS vessels automatically get scored
- ✅ Length data from AIS continuously integrated
- ✅ Fully automated - no manual intervention

## 📈 Expected Behavior

### First Run:
```
[2025-10-30 15:00:00] Starting score calculation...
  Processing 13964 vessels...
  Progress: 500/13964 vessels processed...
  Progress: 1000/13964 vessels processed...
  ...
  ✓ Complete!
    Total processed: 13964
    Scores changed: 8234
    Scores unchanged: 5730
```

### Subsequent Runs (after 1 hour):
```
[2025-10-30 16:00:00] Starting score calculation...
  Processing 13964 vessels...
  ✓ Complete!
    Total processed: 13964
    Scores changed: 45  # Only vessels with new AIS data
    Scores unchanged: 13919
```

## 🎯 Service Management

```bash
# Start
sudo systemctl start ais-econowind-updater

# Stop
sudo systemctl stop ais-econowind-updater

# Restart
sudo systemctl restart ais-econowind-updater

# Status
sudo systemctl status ais-econowind-updater

# View logs
sudo journalctl -u ais-econowind-updater -n 100

# Follow logs in real-time
sudo journalctl -u ais-econowind-updater -f
```

## 🐛 Troubleshooting

### Service won't start

```bash
# Check for errors
sudo journalctl -u ais-econowind-updater -n 50

# Test manually
cd /var/www/apihub
source venv/bin/activate
python econowind_score_updater.py
```

### Scores still showing 0

```bash
# Check if service is running
sudo systemctl status ais-econowind-updater

# Check logs for errors
sudo journalctl -u ais-econowind-updater -n 100

# Manually trigger calculation
cd /var/www/apihub
source venv/bin/activate
python econowind_score_updater.py
# Press Ctrl+C after first run completes
```

### Database locked errors

```bash
# Check if too many services accessing DB
ps aux | grep python

# Restart all services
sudo systemctl restart ais-collector
sudo systemctl restart ais-web-tracker
sudo systemctl restart ais-emissions-matcher
sudo systemctl restart ais-econowind-updater
```

## 📊 Monitoring

### Check Score Distribution

```bash
sqlite3 /var/www/apihub/vessel_static_data.db "
SELECT 
    econowind_fit_score,
    COUNT(*) as vessel_count
FROM eu_mrv_emissions
GROUP BY econowind_fit_score
ORDER BY econowind_fit_score DESC
"
```

### Find High-Scoring Vessels

```bash
sqlite3 /var/www/apihub/vessel_static_data.db "
SELECT vessel_name, company_name, econowind_fit_score, total_co2_emissions
FROM eu_mrv_emissions
WHERE econowind_fit_score >= 6
ORDER BY econowind_fit_score DESC, total_co2_emissions DESC
LIMIT 20
"
```

## 🎉 Benefits

1. **Always Up-to-Date**: Scores reflect latest AIS data
2. **Fully Automated**: No manual intervention needed
3. **Scalable**: Handles growing database automatically
4. **Efficient**: Only updates changed scores
5. **Reliable**: Runs as systemd service with auto-restart

---

**Your Econowind fit scores now update automatically every hour!** 🔄📊✨
