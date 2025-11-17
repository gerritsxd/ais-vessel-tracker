# 🚀 Setup Intelligence Scraper Service on VPS

## What This Does

Runs the **Intelligence Scraper as a background service** that:
- ✅ Scrapes **50 companies every 24 hours**
- ✅ Runs continuously (auto-restarts if crashes)
- ✅ Logs all activity
- ✅ Saves progress automatically
- ✅ Can be started/stopped like other services

---

## Quick Setup (5 Minutes)

### Step 1: Push Code to Git (Local PC)

```bash
cd c:\Users\gerrit\Desktop\apihub

git add .
git commit -m "Add intelligence scraper service"
git push origin main
```

---

### Step 2: Deploy to VPS

```bash
# SSH to VPS
ssh erik@yourserver

# Go to project
cd /var/www/apihub

# Pull latest code
git pull origin main

# Create logs directory if it doesn't exist
mkdir -p logs

# Copy service file to systemd
sudo cp config/systemd/ais-intelligence-scraper.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable ais-intelligence-scraper

# Start the service
sudo systemctl start ais-intelligence-scraper
```

---

### Step 3: Verify It's Running

```bash
# Check status
sudo systemctl status ais-intelligence-scraper

# Should show:
# ● ais-intelligence-scraper.service - Company Intelligence Scraper Service
#    Loaded: loaded
#    Active: active (running)
```

---

## 📊 Monitor the Service

### View Live Logs

```bash
# Watch scraping in real-time
tail -f /var/www/apihub/logs/intelligence_scraper.log

# OR use journalctl
sudo journalctl -u ais-intelligence-scraper -f
```

**You'll see output like:**
```
================================================================================
🕵️  COMPANY INTELLIGENCE SCRAPER SERVICE
================================================================================
Batch size: 50 companies
Sleep between batches: 24.0 hours
Max total companies: 500
================================================================================

[2025-11-17 14:45:00]
Starting batch: companies 1 to 50
--------------------------------------------------------------------------------

[1/50]
================================================================================
🕵️  MSC Shipmanagement Ltd (Fleet: 374 vessels)
================================================================================
  📡 Grants Subsidies...
      🔎 DuckDuckGo: "MSC Shipmanagement Ltd" grant maritime...
    ⏳ 3.2s...
    ✅ 2 findings
  📡 Legal Violations...
    ✅ 1 findings
...
```

---

### Check Collected Data

```bash
# List intelligence files
ls -lh /var/www/apihub/data/company_intelligence*.json

# View latest stats
cat /var/www/apihub/data/company_intelligence_v2_progress.json | python3 -m json.tool | head -20

# Count total findings
cd /var/www/apihub
python3 -c "import json; data=json.load(open('data/company_intelligence_v2_progress.json')); print(f'Companies: {len(data[\"companies\"])}')"
```

---

### Check Dashboard

Open browser:
```
https://gerritsxd.com/ships/intelligence
```

Should show:
- Number of companies scraped
- Total findings
- Available datasets
- Download buttons

**Dashboard auto-refreshes every 30 seconds!**

---

## 🎛️ Service Management Commands

### Start the Service
```bash
sudo systemctl start ais-intelligence-scraper
```

### Stop the Service
```bash
sudo systemctl stop ais-intelligence-scraper
```

### Restart the Service
```bash
sudo systemctl restart ais-intelligence-scraper
```

### Check Status
```bash
sudo systemctl status ais-intelligence-scraper
```

### View Logs
```bash
# Real-time logs
sudo journalctl -u ais-intelligence-scraper -f

# Last 100 lines
sudo journalctl -u ais-intelligence-scraper -n 100

# Logs from today
sudo journalctl -u ais-intelligence-scraper --since today

# Log file
tail -f /var/www/apihub/logs/intelligence_scraper.log
```

### Disable Service (stop auto-start on boot)
```bash
sudo systemctl disable ais-intelligence-scraper
```

### Enable Service (auto-start on boot)
```bash
sudo systemctl enable ais-intelligence-scraper
```

---

## ⚙️ Configuration

Edit the service settings in `src/services/intelligence_scraper_service.py`:

```python
# How many companies per batch
BATCH_SIZE = 50  # Default: 50

# How long to wait between batches (in seconds)
SLEEP_BETWEEN_BATCHES = 3600 * 24  # Default: 24 hours

# Maximum total companies to scrape (then stops)
MAX_TOTAL_COMPANIES = 500  # Default: 500
```

**Example configurations:**

### Aggressive (Fast Data Collection)
```python
BATCH_SIZE = 100
SLEEP_BETWEEN_BATCHES = 3600 * 12  # 12 hours
MAX_TOTAL_COMPANIES = 1000
```
→ Scrapes 100 companies every 12 hours

### Conservative (Avoid Blocking)
```python
BATCH_SIZE = 20
SLEEP_BETWEEN_BATCHES = 3600 * 48  # 48 hours
MAX_TOTAL_COMPANIES = 200
```
→ Scrapes 20 companies every 2 days

### One-time Collection
```python
BATCH_SIZE = 500
SLEEP_BETWEEN_BATCHES = 3600 * 24 * 365  # 1 year (basically never)
MAX_TOTAL_COMPANIES = 500
```
→ Scrapes 500 companies once, then sleeps

**After changing config:**
```bash
git add .
git commit -m "Update scraper config"
git push

# On VPS
cd /var/www/apihub
git pull
sudo systemctl restart ais-intelligence-scraper
```

---

## 📈 Expected Performance

### Default Settings (50 companies/24 hours)

| Metric | Value |
|--------|-------|
| **Time per company** | 2-5 minutes |
| **Batch duration** | 100-250 minutes (~4 hours) |
| **Companies per week** | ~350 companies |
| **Full 500 companies** | ~10 days |
| **Findings per company** | 3-8 (if successful) |
| **Total findings (500 companies)** | 1,500-4,000 |

---

## 🔍 Troubleshooting

### Service Won't Start

**Check logs:**
```bash
sudo journalctl -u ais-intelligence-scraper -n 50
```

**Common issues:**
- Python not found → Check `/usr/bin/python3` exists
- Permissions → Service runs as user `erik`
- Missing dependencies → `pip install requests beautifulsoup4`

**Fix:**
```bash
# Make service executable
chmod +x /var/www/apihub/src/services/intelligence_scraper_service.py

# Install dependencies
pip3 install requests beautifulsoup4 lxml

# Restart
sudo systemctl restart ais-intelligence-scraper
```

---

### Getting 0 Findings

**Causes:**
- DuckDuckGo blocking requests
- Company names not matching
- Network issues

**Solutions:**

1. **Increase delays** (edit `company_intelligence_scraper_v2.py`):
```python
self.min_delay = 5.0  # Was 2.0
self.max_delay = 10.0  # Was 4.0
```

2. **Reduce batch size**:
```python
BATCH_SIZE = 20  # Was 50
```

3. **Check if VPS is blocked**:
```bash
# Test DuckDuckGo manually
curl "https://html.duckduckgo.com/html/?q=maersk+shipping"
# Should return HTML, not error
```

4. **Try different time of day** (less traffic = less blocking)

---

### Service Keeps Crashing

**Check error logs:**
```bash
tail -f /var/www/apihub/logs/intelligence_scraper_error.log
```

**Common fixes:**
```bash
# Restart service
sudo systemctl restart ais-intelligence-scraper

# Check disk space
df -h

# Check memory
free -h

# Update code
cd /var/www/apihub
git pull
sudo systemctl restart ais-intelligence-scraper
```

---

## 📊 All Services on VPS

After setup, you'll have:

```bash
# Check all services
sudo systemctl status ais-*

# You should see:
● ais-web-tracker.service       - Web interface
● ais-collector.service          - AIS data collection
● ais-intelligence-scraper.service - Intelligence scraping (NEW!)
● ais-emissions-matcher.service  - Emissions matching (optional)
● ais-econowind-updater.service  - WASP scoring (optional)
● ais-gt-scraper.service         - Gross tonnage (optional)
```

---

## 🎯 Quick Start Checklist

- [ ] Pushed code to git
- [ ] Pulled on VPS
- [ ] Copied service file to `/etc/systemd/system/`
- [ ] Ran `systemctl daemon-reload`
- [ ] Ran `systemctl enable ais-intelligence-scraper`
- [ ] Ran `systemctl start ais-intelligence-scraper`
- [ ] Verified with `systemctl status ais-intelligence-scraper`
- [ ] Checked logs with `tail -f logs/intelligence_scraper.log`
- [ ] Visited dashboard at `/ships/intelligence`

---

## 📞 Quick Commands

```bash
# Complete setup (copy-paste)
cd /var/www/apihub && \
git pull && \
mkdir -p logs && \
sudo cp config/systemd/ais-intelligence-scraper.service /etc/systemd/system/ && \
sudo systemctl daemon-reload && \
sudo systemctl enable ais-intelligence-scraper && \
sudo systemctl start ais-intelligence-scraper && \
sudo systemctl status ais-intelligence-scraper

# View live logs
tail -f /var/www/apihub/logs/intelligence_scraper.log

# Check collected data
ls -lh /var/www/apihub/data/company_intelligence*.json

# Restart service
sudo systemctl restart ais-intelligence-scraper
```

---

**Status:** ✅ **Ready to deploy!**  
**Next:** Run the setup commands on your VPS!
