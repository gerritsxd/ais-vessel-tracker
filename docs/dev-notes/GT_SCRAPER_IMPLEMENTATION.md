# GT Scraper Implementation Summary

## ✅ What Was Created

### 1. **Database Migration** (`src/utils/add_gt_column.py`)
- Adds `gross_tonnage` column to `eu_mrv_emissions` table
- Checks if column already exists
- Shows current GT coverage statistics
- Safe to run multiple times

### 2. **GT Scraper Service** (`src/services/gt_scraper.py`)
- **Main scraping engine** - Runs continuously every 24 hours
- **Rate limiting** - 10 requests/minute (6 seconds between requests)
- **Smart caching** - Remembers failed attempts for 7 days
- **Multi-source** - Tries MarineTraffic first, then VesselFinder
- **Batch processing** - 100 vessels per day
- **Error handling** - Graceful failures, automatic retries

### 3. **Manual Runner** (`src/utils/run_gt_scraper_once.py`)
- Run GT scraper on-demand
- Perfect for testing or immediate updates
- Scrapes one batch (100 vessels) and exits

### 4. **Systemd Service** (`config/systemd/ais-gt-scraper.service`)
- Auto-start on VPS boot
- Auto-restart on failure
- Logs to journald
- Runs as user `erik`

### 5. **Documentation** (`docs/GT_SCRAPER_GUIDE.md`)
- Complete setup guide
- Configuration options
- Troubleshooting tips
- Monitoring commands

### 6. **Updated Import Script** (`src/utils/import_mrv_data.py`)
- Now ensures `gross_tonnage` column exists
- Backward compatible with older databases

## 🎯 Key Features

### Rate Limiting (Prevents Blocking)
```python
REQUESTS_PER_MINUTE = 10  # 10 requests/minute
DELAY_BETWEEN_REQUESTS = 6 seconds
REQUEST_TIMEOUT = 15 seconds
```

### Smart Caching
- Failed scrapes cached for 7 days
- Successful scrapes remove from cache
- Cache persists across restarts
- Stored in `data/gt_scraper_cache.json`

### Multi-Source Scraping
1. **MarineTraffic** (primary)
   - `https://www.marinetraffic.com/en/ais/details/ships/imo:{imo}`
   - Most comprehensive data
   
2. **VesselFinder** (fallback)
   - `https://www.vesselfinder.com/vessels/details/{imo}`
   - Alternative source if MarineTraffic fails

### Data Validation
- GT must be between 100 and 500,000 tons
- Sanity checks prevent bad data
- Handles various number formats (with/without commas)

## 📋 Quick Start

### On Your PC (Windows)

```bash
# 1. Add GT column to database
python src/utils/add_gt_column.py

# 2. Test scraper manually (optional)
python src/utils/run_gt_scraper_once.py

# 3. Commit and push to git
git add .
git commit -m "Add GT scraper service with rate limiting"
git push origin main
```

### On VPS (Production)

```bash
# 1. Pull changes
cd /var/www/apihub
git pull origin main

# 2. Add GT column
python3 src/utils/add_gt_column.py

# 3. Install and start service
sudo cp config/systemd/ais-gt-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ais-gt-scraper
sudo systemctl start ais-gt-scraper

# 4. Check status
sudo systemctl status ais-gt-scraper

# 5. View logs
sudo journalctl -u ais-gt-scraper -f
```

## 📊 Expected Performance

### Timeline
- **16,000 vessels** ÷ **100 per day** = **~160 days** (5 months)
- Adjust `BATCH_SIZE` to speed up or slow down

### Success Rate
- Expected: **60-80%** (some vessels not in public databases)
- Failures are cached and retried after 7 days

### Resource Usage
- **CPU**: <1%
- **Memory**: ~50MB
- **Network**: ~1-2 MB per batch
- **Disk**: Cache file ~100KB

## 🔧 Configuration Options

Edit `src/services/gt_scraper.py`:

```python
# Timing
CHECK_INTERVAL = 86400  # 24 hours (change to 43200 for 12h)

# Batch size
BATCH_SIZE = 100  # Vessels per run (50-200 recommended)

# Rate limiting
REQUESTS_PER_MINUTE = 10  # 5-20 recommended
```

### Recommended Presets

**Conservative** (avoid blocking):
```python
BATCH_SIZE = 50
REQUESTS_PER_MINUTE = 5
```

**Balanced** (default):
```python
BATCH_SIZE = 100
REQUESTS_PER_MINUTE = 10
```

**Aggressive** (faster, higher risk):
```python
BATCH_SIZE = 200
REQUESTS_PER_MINUTE = 20
```

## 🎛️ Monitoring

### Check GT Coverage
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/vessel_static_data.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions WHERE gross_tonnage IS NOT NULL')
with_gt = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions')
total = cursor.fetchone()[0]
print(f'GT Coverage: {with_gt:,}/{total:,} ({with_gt/total*100:.1f}%)')
"
```

### View Service Logs
```bash
# Real-time
sudo journalctl -u ais-gt-scraper -f

# Last 100 lines
sudo journalctl -u ais-gt-scraper -n 100

# Today's logs
sudo journalctl -u ais-gt-scraper --since today
```

### Check Cache
```bash
cat data/gt_scraper_cache.json | python3 -m json.tool
```

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u ais-gt-scraper -n 50

# Verify database
ls -lh data/vessel_static_data.db

# Test manually
python3 src/utils/run_gt_scraper_once.py
```

### Getting Rate Limited (429 errors)
1. Reduce `REQUESTS_PER_MINUTE` to 5
2. Reduce `BATCH_SIZE` to 50
3. Wait 24 hours before retrying

### Low Success Rate
- Check logs for specific errors
- Some vessels may not exist in public databases
- Verify IMO numbers are correct

## 📁 Files Created

```
apihub/
├── src/
│   ├── services/
│   │   └── gt_scraper.py              # Main scraper service ⭐
│   └── utils/
│       ├── add_gt_column.py           # Database migration
│       ├── run_gt_scraper_once.py     # Manual runner
│       └── import_mrv_data.py         # Updated (GT column)
│
├── config/
│   └── systemd/
│       └── ais-gt-scraper.service     # Systemd service
│
├── docs/
│   └── GT_SCRAPER_GUIDE.md            # Full documentation
│
├── data/
│   └── gt_scraper_cache.json          # Cache (created on first run)
│
└── GT_SCRAPER_IMPLEMENTATION.md       # This file
```

## ✨ Integration

The GT data is automatically available in:

### Web Interface
- GT filter in map view (`templates/map.html`)
- Vessel details sidebar
- Database browser

### API Endpoints
- `GET /ships/api/vessels` - Includes GT in response
- `GET /ships/api/vessel/<mmsi>` - Shows GT if available

### Database Queries
```sql
-- Vessels with GT data
SELECT * FROM eu_mrv_emissions WHERE gross_tonnage IS NOT NULL;

-- Average GT by ship type
SELECT ship_type, AVG(gross_tonnage) 
FROM eu_mrv_emissions 
WHERE gross_tonnage IS NOT NULL 
GROUP BY ship_type;
```

## 🎉 Summary

You now have a **fully automated GT scraper** that:

✅ Runs every 24 hours automatically  
✅ Respects rate limits (10 req/min)  
✅ Caches failures intelligently  
✅ Scrapes from multiple sources  
✅ Can run on-demand for testing  
✅ Integrates with existing system  
✅ Logs everything for monitoring  

**Next Steps:**
1. Run `python src/utils/add_gt_column.py` locally to test
2. Push to git
3. Deploy to VPS
4. Monitor logs for first 24 hours
5. Adjust rate limits if needed

---

**Created**: November 2025  
**Author**: Cascade AI  
**Status**: Ready for deployment 🚀
