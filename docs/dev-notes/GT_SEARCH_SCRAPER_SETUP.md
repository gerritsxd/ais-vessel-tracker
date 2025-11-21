# GT Search Scraper Setup Guide

## 🎯 New Approach: Search-Based GT Collection

Instead of direct website scraping (which causes rate limits), this uses search engine results to find GT data.

## 📋 Setup Instructions

### 1. Database Migration
```bash
# Convert gross_tonnage column to TEXT type (supports NA/NF values)
python src/utils/migrate_gt_search.py
```

### 2. Test the Search Scraper
```bash
# Test with a few vessels to verify it works
python src/utils/test_gt_search_scraper.py
```

### 3. Run Full Scraper
```bash
# Process one batch (50 vessels)
python src/services/gt_search_scraper.py
```

### 4. Deploy as Service (VPS)
```bash
# Install service
sudo cp config/systemd/ais-gt-search-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ais-gt-search-scraper
sudo systemctl start ais-gt-search-scraper

# Check status
sudo systemctl status ais-gt-search-scraper
sudo journalctl -u ais-gt-search-scraper -f
```

## 🔧 How It Works

### Search Process
1. **Takes MMSI** from `vessels_static` table
2. **Searches DuckDuckGo** with queries like:
   - "MMSI 123456789 gross tonnage"
   - "VESSEL_NAME MMSI 123456789 GT"
3. **Extracts GT** from search result snippets
4. **Updates database** with:
   - GT number (if found)
   - "NA" (not available - search failed)
   - "NF" (not found - search succeeded but no GT)

### Rate Limiting Avoidance
- **No direct website requests** - only search engine
- **30 seconds between searches** - very conservative
- **DuckDuckGo** - more lenient than Google
- **Smart caching** - failed attempts cached for 7 days

## 📊 Configuration

Edit `src/services/gt_search_scraper.py`:
```python
BATCH_SIZE = 50          # Vessels per day
DELAY_BETWEEN_REQUESTS = 30  # Seconds between searches
CHECK_INTERVAL = 86400   # Run every 24 hours
```

## 📈 Expected Performance

- **Speed**: ~30 seconds per vessel (search + delay)
- **Success Rate**: 40-60% (depends on vessel visibility)
- **Timeline**: 16,000 vessels ÷ 50/day = ~320 days
- **Resource Usage**: Very low (no heavy scraping)

## 🗂️ Files Created

```
src/
├── services/
│   └── gt_search_scraper.py          # Main search scraper ⭐
├── utils/
│   ├── test_gt_search_scraper.py     # Test script
│   └── migrate_gt_search.py          # Database migration
└── config/systemd/
    └── ais-gt-search-scraper.service # Systemd service
```

## 🚨 Important Notes

### Search Limitations
- Not all vessels appear in search results
- Some vessels have no public GT data
- Search results vary by region and vessel type

### Database Values
- **Numbers**: Actual GT values (e.g., 12345)
- **"NA"**: Search failed/timeout
- **"NF"**: Search succeeded but GT not found

### Monitoring
```bash
# Check GT coverage
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

# View service logs
sudo journalctl -u ais-gt-search-scraper -f
```

## ✅ Benefits Over Direct Scraping

1. **No Rate Limits** - Search engines are more permissive
2. **Simpler** - No need to parse complex websites
3. **More Robust** - Less likely to be blocked
4. **Database Safe** - Handles NA/NF values gracefully
5. **Low Resource** - Minimal CPU and network usage

## 🔄 Migration from Old Scraper

If you were using the old GT scraper:
1. Stop old service: `sudo systemctl stop ais-gt-scraper`
2. Disable: `sudo systemctl disable ais-gt-scraper`
3. Run migration: `python src/utils/migrate_gt_search.py`
4. Start new service: `sudo systemctl start ais-gt-search-scraper`

The new scraper will continue from where the old one left off!
