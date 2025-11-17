# Dual Scraper System Deployment Guide

## Overview
You now have **TWO scrapers** running simultaneously:
1. **Intelligence Scraper** - Collects grants, lawsuits, news, reputation, financial data
2. **Company Profiler** - Collects Wikipedia summaries, company websites, fleet metadata

Both scrapers are visible **LIVE** on the Intelligence Dashboard!

---

## 🚀 Quick Deployment

### 1. Push Code to Git

```bash
# On your PC
cd c:\Users\gerrit\Desktop\apihub
git add .
git commit -m "Add dual scraper system with live dashboard"
git push origin master
```

### 2. Deploy to VPS

```bash
# SSH to VPS
ssh erik@your-vps

# Pull latest code
cd /var/www/apihub
git pull origin master

# Restart web service (for new API endpoints)
sudo systemctl restart ais-web-tracker

# Install profiler service
sudo cp config/systemd/ais-company-profiler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ais-company-profiler
sudo systemctl start ais-company-profiler

# Check both services
sudo systemctl status ais-intelligence-scraper
sudo systemctl status ais-company-profiler
```

---

## 📊 Service Configuration

### Intelligence Scraper (Already Running)
- **Service**: `ais-intelligence-scraper.service`
- **Script**: `src/services/intelligence_scraper_service.py`
- **Batch size**: 50 companies
- **Frequency**: Every 24 hours
- **Max total**: 500 companies
- **Data**: Grants, lawsuits, news, reputation, finance

### Company Profiler (NEW)
- **Service**: `ais-company-profiler.service`
- **Script**: `src/services/company_profiler_service.py`
- **Batch size**: 25 companies
- **Frequency**: Every 12 hours (twice per day)
- **Max total**: 500 companies
- **Data**: Wikipedia, websites, fleet metadata

---

## 🎯 Live Dashboard Features

Visit: `https://gerritsxd.com/ships/intelligence`

You'll see:
- ✅ **2 Live Scraper Boxes** showing real-time progress
- ✅ **Current company** being scraped
- ✅ **Progress bars** with percentage
- ✅ **Findings count** for each scraper
- ✅ **Status indicator** (🟢 Running / ⚪ Idle)
- ✅ **Auto-refresh** every 5 seconds

---

## 📁 Output Files

### Intelligence Data
```
data/company_intelligence_v2_TIMESTAMP.json
data/company_intelligence_v2_progress.json
```

### Profiler Data
```
data/company_profiles_v3_structured_TIMESTAMP.json
data/company_training_v3_TIMESTAMP.txt
```

Both are downloadable from the dashboard!

---

## 🔧 Service Commands

### Check Status
```bash
# Intelligence scraper
sudo systemctl status ais-intelligence-scraper
sudo journalctl -u ais-intelligence-scraper -f

# Company profiler
sudo systemctl status ais-company-profiler
sudo journalctl -u ais-company-profiler -f
```

### View Logs
```bash
# Intelligence scraper logs
tail -f /var/www/apihub/logs/intelligence_scraper.log

# Company profiler logs
tail -f /var/www/apihub/logs/company_profiler.log
```

### Control Services
```bash
# Start both
sudo systemctl start ais-intelligence-scraper
sudo systemctl start ais-company-profiler

# Stop both
sudo systemctl stop ais-intelligence-scraper
sudo systemctl stop ais-company-profiler

# Restart both
sudo systemctl restart ais-intelligence-scraper
sudo systemctl restart ais-company-profiler
```

---

## ⚙️ Configuration

### Change Batch Sizes

Edit `src/services/intelligence_scraper_service.py`:
```python
BATCH_SIZE = 100              # Companies per batch
SLEEP_BETWEEN_BATCHES = 43200 # 12 hours instead of 24
MAX_TOTAL_COMPANIES = 1000    # 1000 total
```

Edit `src/services/company_profiler_service.py`:
```python
BATCH_SIZE = 50               # More companies per batch
SLEEP_BETWEEN_BATCHES = 21600 # 6 hours
MAX_TOTAL_COMPANIES = 1000    # 1000 total
```

After editing, restart:
```bash
sudo systemctl restart ais-intelligence-scraper
sudo systemctl restart ais-company-profiler
```

---

## 📈 Expected Timeline

### Current Configuration:
- **Intelligence**: 50 companies/day × 10 days = 500 companies
- **Profiler**: 25 companies × 2/day × 20 days = 500 companies
- **Total time**: ~20 days for full dataset

### Faster Configuration (example):
- **Intelligence**: 100 companies every 12h = 200/day
- **Profiler**: 50 companies every 6h = 200/day
- **Total time**: ~2.5 days for 500 companies

---

## 🎨 Dashboard Live Updates

The dashboard automatically shows:
- **🟢 Green pulsing dot** = Scraper is running
- **⚪ Gray dot** = Scraper is sleeping/idle
- **Progress bars** = Visual completion percentage
- **Company name** = Current company being processed
- **Auto-refresh** = Every 5 seconds for live updates

---

## 🔥 Quick Test

```bash
# Watch both scrapers live
watch -n 2 'systemctl status ais-intelligence-scraper ais-company-profiler'

# Or monitor logs side-by-side
tail -f /var/www/apihub/logs/intelligence_scraper.log /var/www/apihub/logs/company_profiler.log
```

Then open the dashboard and watch the boxes update in real-time! 🚀

---

## 📊 API Endpoints

- `/ships/api/scrapers/status` - Both scraper statuses
- `/ships/api/intelligence/status` - Intelligence scraper only
- `/ships/api/profiler/status` - Profiler scraper only
- `/ships/api/intelligence/datasets` - List all datasets (both types)
- `/ships/api/intelligence/download/<filename>` - Download dataset

---

## ✅ Success Checklist

- [ ] Code pushed to Git
- [ ] VPS pulled latest code
- [ ] Web tracker restarted (`ais-web-tracker`)
- [ ] Intelligence scraper running (`ais-intelligence-scraper`)
- [ ] Company profiler service installed and started
- [ ] Dashboard shows 2 scraper boxes
- [ ] Both scrapers showing status (green if running)
- [ ] Datasets appearing in dashboard
- [ ] Download buttons working

---

## 🎯 Next Steps

1. **Monitor Progress**: Watch the dashboard for live updates
2. **Check Logs**: Ensure no errors in scraper logs
3. **Download Data**: Once scrapers collect data, download JSON files
4. **Train ML Model**: Use both datasets for WASP score prediction

**The intelligence gathering has begun!** 🕵️📊
