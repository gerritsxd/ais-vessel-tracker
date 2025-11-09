# Gross Tonnage (GT) Scraper Guide

## Overview

The GT Scraper is a background service that automatically scrapes Gross Tonnage data for vessels from public maritime databases. Since GT is not available in the AIS data stream, we scrape it from MarineTraffic and VesselFinder.

## Features

- ✅ **Automatic scraping** - Runs every 24 hours
- ✅ **Rate limiting** - 10 requests/minute to avoid being blocked
- ✅ **Smart caching** - Remembers failed attempts, won't retry for 7 days
- ✅ **Multiple sources** - Falls back to VesselFinder if MarineTraffic fails
- ✅ **Batch processing** - Scrapes 100 vessels per day
- ✅ **On-demand mode** - Can run manually for immediate updates

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  eu_mrv_emissions table (16,000+ vessels)                   │
│  - Has IMO numbers                                          │
│  - Missing GT data                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  GT Scraper Service (runs every 24h)                        │
│  1. Query vessels without GT                                │
│  2. Scrape MarineTraffic (primary)                          │
│  3. Scrape VesselFinder (fallback)                          │
│  4. Update database                                         │
│  5. Cache results                                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Updated eu_mrv_emissions table                             │
│  - Now has GT data                                          │
│  - Used in web interface filters                            │
└─────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Add GT Column to Database

First, ensure the `gross_tonnage` column exists:

```bash
# On your PC (Windows)
python src/utils/add_gt_column.py

# Or on VPS
python3 src/utils/add_gt_column.py
```

This will:
- Check if the column exists
- Add it if missing
- Show current GT statistics

### 2. Test Manual Scraping (Optional)

Before setting up the service, test it manually:

```bash
# On your PC
python src/utils/run_gt_scraper_once.py

# On VPS
python3 src/utils/run_gt_scraper_once.py
```

This will scrape GT for one batch (100 vessels) and show results.

### 3. Deploy to VPS

```bash
# 1. Push code to git
git add .
git commit -m "Add GT scraper service"
git push origin main

# 2. SSH to VPS
ssh your-vps

# 3. Pull changes
cd /var/www/apihub
git pull origin main

# 4. Add GT column (if not done)
python3 src/utils/add_gt_column.py

# 5. Install systemd service
sudo cp config/systemd/ais-gt-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ais-gt-scraper
sudo systemctl start ais-gt-scraper

# 6. Check status
sudo systemctl status ais-gt-scraper
```

## Configuration

Edit `src/services/gt_scraper.py` to adjust:

```python
CHECK_INTERVAL = 86400  # 24 hours (in seconds)
BATCH_SIZE = 100        # Vessels per day
REQUESTS_PER_MINUTE = 10  # Rate limit (10 req/min = 6s delay)
```

### Recommended Settings:

- **Conservative**: 50 vessels/day, 5 req/min
- **Balanced**: 100 vessels/day, 10 req/min (default)
- **Aggressive**: 200 vessels/day, 20 req/min (risk of blocking)

## Usage

### Check Service Status

```bash
sudo systemctl status ais-gt-scraper
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u ais-gt-scraper -f

# Last 100 lines
sudo journalctl -u ais-gt-scraper -n 100
```

### Restart Service

```bash
sudo systemctl restart ais-gt-scraper
```

### Stop Service

```bash
sudo systemctl stop ais-gt-scraper
```

### Run Manually (On-Demand)

```bash
# Run one batch immediately
python3 src/utils/run_gt_scraper_once.py
```

## Monitoring

### Check GT Coverage

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/vessel_static_data.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions WHERE gross_tonnage IS NOT NULL AND gross_tonnage > 0')
with_gt = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions')
total = cursor.fetchone()[0]

print(f'GT Coverage: {with_gt:,} / {total:,} ({with_gt/total*100:.1f}%)')
conn.close()
"
```

### View Cache File

The scraper maintains a cache of failed attempts:

```bash
cat data/gt_scraper_cache.json
```

## How It Works

### 1. Vessel Selection

- Queries `eu_mrv_emissions` for vessels without GT
- Excludes vessels that failed within last 7 days
- Randomizes order to avoid patterns
- Limits to batch size (100 vessels)

### 2. Scraping Process

For each vessel:
1. Try MarineTraffic: `https://www.marinetraffic.com/en/ais/details/ships/imo:{imo}`
2. Parse HTML for "Gross Tonnage: XXXXX"
3. If not found, try VesselFinder
4. Validate GT value (100-500,000 range)
5. Update database if found

### 3. Rate Limiting

- Waits 6 seconds between requests (10 req/min)
- Additional 2-second delay between sources
- 15-second timeout per request
- Handles 429 (rate limit) responses

### 4. Caching

- Successful scrapes: Removed from cache
- Failed scrapes: Cached for 7 days
- Cache persists across restarts

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
sudo journalctl -u ais-gt-scraper -n 50

# Check if database exists
ls -lh data/vessel_static_data.db

# Check if GT column exists
python3 src/utils/add_gt_column.py
```

### Getting Blocked

If you see many 429 errors:

1. Reduce `REQUESTS_PER_MINUTE` to 5
2. Reduce `BATCH_SIZE` to 50
3. Wait 24 hours before retrying

### Low Success Rate

Check logs to see why scraping fails:
- Network issues
- Website structure changed
- IMO not in database

## Performance

### Expected Timeline

- **16,000 vessels** ÷ **100 per day** = **160 days** (~5 months)
- Faster if you increase batch size
- Some vessels may never be found (not in public databases)

### Resource Usage

- **CPU**: <1% (mostly waiting)
- **Memory**: ~50MB
- **Network**: ~1-2 MB per batch
- **Disk**: Cache file ~100KB

## Data Sources

### MarineTraffic (Primary)
- Most comprehensive
- Free public access
- May rate limit aggressively

### VesselFinder (Fallback)
- Good coverage
- Less strict rate limiting
- Alternative data format

## Future Improvements

Potential enhancements:

1. **More sources**: Equasis, IMO database
2. **Parallel scraping**: Multiple threads (with caution)
3. **Smart scheduling**: Scrape during off-peak hours
4. **Proxy rotation**: Avoid rate limits
5. **ML validation**: Detect incorrect GT values

## Integration

The GT data is automatically used in:

- **Web interface**: GT filter in map view
- **API endpoints**: `/ships/api/vessels` includes GT
- **Database queries**: Available for analysis

## Support

If you encounter issues:

1. Check logs: `sudo journalctl -u ais-gt-scraper -f`
2. Test manually: `python3 src/utils/run_gt_scraper_once.py`
3. Verify database: `python3 src/utils/add_gt_column.py`
4. Check cache: `cat data/gt_scraper_cache.json`

---

**Last Updated**: November 2025
