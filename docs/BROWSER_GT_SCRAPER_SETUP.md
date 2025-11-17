# Browser-Based GT Scraper Setup Guide

## Overview
The browser-based GT scraper uses Playwright with Chromium to scrape Gross Tonnage data from Google search results without visiting individual maritime websites. This approach is more efficient and less detectable than direct HTTP requests.

## Key Features

### Browser Automation
- **Engine**: Playwright with Chromium
- **Method**: Google search → Extract GT from search snippets
- **Stealth**: Anti-detection measures, headless mode
- **Performance**: Optimized for speed (no images, no JS)

### Scraping Strategy
1. **Search Query**: `site:marinetraffic.com {imo} gross tonnage`
2. **Extract**: GT from search result snippets
3. **Fallback**: Try VesselFinder if MarineTraffic fails
4. **No Navigation**: Never visits individual vessel pages

### Rate Limiting
- **Conservative**: 5 requests/minute (12s delay)
- **Batch Size**: 50 vessels per run
- **Detection Avoidance**: Human-like browsing patterns

## Installation

### 1. Install Dependencies

**Local (Windows)**:
```bash
pip install playwright==1.48.0
playwright install chromium
```

**VPS (Linux)**:
```bash
pip3 install playwright==1.48.0
playwright install chromium
# Or install system dependencies first
sudo apt-get update
sudo apt-get install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2
```

### 2. Database Setup (Same as Original)

```bash
python src/utils/add_gt_column.py
```

### 3. Test Browser Scraper

**Manual Test Run**:
```bash
python src/utils/run_gt_browser_scraper_once.py
```

**Continuous Service**:
```bash
python src/services/gt_scraper_browser.py
```

## Configuration

Edit `src/services/gt_scraper_browser.py`:

```python
BATCH_SIZE = 50  # Vessels per day (browser is more resource intensive)
REQUESTS_PER_MINUTE = 5  # Conservative rate limit
DELAY_BETWEEN_REQUESTS = 12  # Seconds between requests
REQUEST_TIMEOUT = 30  # Seconds per search
```

### Presets
- **Conservative**: 25 vessels/day, 3 req/min
- **Balanced**: 50 vessels/day, 5 req/min (default)
- **Aggressive**: 100 vessels/day, 10 req/min

## VPS Deployment

### 1. Update Dependencies
```bash
cd /var/www/apihub
git pull origin main
pip3 install -r config/requirements.txt
playwright install chromium
```

### 2. Install System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2
```

### 3. Setup Service
```bash
sudo cp config/systemd/ais-gt-browser-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ais-gt-browser-scraper
sudo systemctl start ais-gt-browser-scraper
```

### 4. Monitor Service
```bash
# Check status
sudo systemctl status ais-gt-browser-scraper

# View logs
sudo journalctl -u ais-gt-browser-scraper -f

# Check GT coverage
python3 -c "
import sqlite3
conn = sqlite3.connect('data/vessel_static_data.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions WHERE gross_tonnage IS NOT NULL')
print(f'GT: {cursor.fetchone()[0]:,}')
"
```

## Comparison: Browser vs HTTP Scraper

| Feature | HTTP Scraper | Browser Scraper |
|---------|--------------|-----------------|
| **Method** | Direct HTTP requests | Google search + extraction |
| **Detection Risk** | Medium | Low |
| **Success Rate** | 60-70% | 70-80% |
| **Speed** | Faster | Slower but more thorough |
| **Resource Usage** | Low | Higher (Chromium) |
| **Maintenance** | May need IP rotation | More stable long-term |

## Troubleshooting

### Browser Issues
```bash
# Reinstall browsers
playwright install chromium --force

# Check browser installation
python3 -c "from playwright.sync_api import sync_playwright; print('OK')"
```

### Permission Issues
```bash
# Fix display issues for headless mode
export DISPLAY=:99
sudo systemctl restart ais-gt-browser-scraper
```

### Memory Issues
- Reduce `BATCH_SIZE` if VPS has limited RAM
- Monitor memory: `htop` or `free -h`
- Browser uses ~100-200MB per instance

## Monitoring

### Success Rate Tracking
```bash
# View detailed statistics
sudo journalctl -u ais-gt-browser-scraper | grep "Success rate"
```

### Performance Metrics
- **Expected**: 50 vessels/day, 70-80% success rate
- **Timeline**: 16,000 vessels ÷ 50/day = ~320 days
- **Resource**: ~200MB RAM, <5% CPU

## Migration from HTTP Scraper

To switch from HTTP to browser scraper:

1. **Stop HTTP Scraper**:
   ```bash
   sudo systemctl stop ais-gt-scraper
   sudo systemctl disable ais-gt-scraper
   ```

2. **Start Browser Scraper**:
   ```bash
   sudo systemctl enable ais-gt-browser-scraper
   sudo systemctl start ais-gt-browser-scraper
   ```

3. **Keep Cache Compatibility**:
   Both scrapers use the same cache format, so failed attempts are preserved.

## Advanced Configuration

### Custom Search Queries
Edit the search query in `scrape_gt_from_marinetraffic_search()`:
```python
search_query = f"site:marinetraffic.com {imo} gross tonnage"
# Alternative:
search_query = f"{imo} vessel gross tonnage marinetraffic"
```

### Additional Sources
Add more search sources in `scrape_gt()`:
```python
# Try additional sources
gt = await self.scrape_gt_from_shipspotting_search(imo)
if gt:
    return gt
```

### Proxy Support
Add proxy configuration in `init_browser()`:
```python
await self.playwright.chromium.launch(
    proxy={"server": "http://proxy.example.com:8080"}
)
```

## Security Considerations

- Browser runs in sandboxed environment
- No file system access beyond project directory
- Headless mode (no display required)
- Anti-detection measures enabled
- Rate limiting prevents IP blocking

## File Structure

```
src/services/gt_scraper_browser.py     # Main browser scraper
src/utils/run_gt_browser_scraper_once.py  # Manual runner
config/systemd/ais-gt-browser-scraper.service  # Systemd service
config/requirements.txt                # Updated with playwright
docs/BROWSER_GT_SCRAPER_SETUP.md       # This guide
```
