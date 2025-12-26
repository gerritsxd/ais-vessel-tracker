# Wind Analysis - VPS Setup Guide

## Quick Start

The wind analysis should run on the VPS where your database is located. This avoids transferring the 3.5GB database and keeps results in the same place.

## Installation

### 1. Pull Latest Code

```bash
cd /var/www/apihub
git pull origin master
```

### 2. Install Dependencies

```bash
source venv/bin/activate
pip install requests  # Should already be installed
```

### 3. Test with One Vessel

```bash
# Test with a single vessel first
python3 src/utils/run_wind_analysis.py 211281610
```

This will:
- Fetch historical wind data for that vessel's positions
- Calculate alignment angles
- Store results in database

### 4. Run for All Vessels

```bash
# Analyze first 10 vessels (test)
python3 src/utils/run_wind_analysis.py --all 10

# Analyze all vessels (this will take a while!)
python3 src/utils/run_wind_analysis.py --all
```

**Note:** Analyzing all vessels can take hours depending on:
- Number of vessels
- Number of positions per vessel
- API rate limits
- Network speed

## Running as Background Service

### Option 1: One-Time Run (Manual)

```bash
cd /var/www/apihub
source venv/bin/activate
nohup python3 src/utils/run_wind_analysis.py --all > /tmp/wind_analysis.log 2>&1 &
```

Check progress:
```bash
tail -f /tmp/wind_analysis.log
```

### Option 2: Systemd Service (Recommended)

```bash
# Copy service file
sudo cp config/systemd/ais-wind-analysis.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Run once manually
sudo systemctl start ais-wind-analysis

# Check status
sudo systemctl status ais-wind-analysis

# View logs
sudo journalctl -u ais-wind-analysis -f
```

### Option 3: Scheduled Daily Run

```bash
# Copy timer file
sudo cp config/systemd/ais-wind-analysis.timer /etc/systemd/system/

# Enable timer (runs daily at 2 AM)
sudo systemctl enable ais-wind-analysis.timer
sudo systemctl start ais-wind-analysis.timer

# Check timer status
sudo systemctl status ais-wind-analysis.timer

# List all timers
systemctl list-timers
```

## Performance Tips

### 1. Start Small

```bash
# Analyze just 10 vessels first
python3 src/utils/run_wind_analysis.py --all 10
```

### 2. Monitor Progress

The script prints progress for each vessel. Watch for:
- API rate limit errors
- Network timeouts
- Database connection issues

### 3. Cache Management

Wind data is cached in `data/wind_cache/`. This speeds up re-runs but uses disk space.

Check cache size:
```bash
du -sh /var/www/apihub/data/wind_cache/
```

Clear cache if needed:
```bash
rm -rf /var/www/apihub/data/wind_cache/*
```

### 4. Batch Processing

The service processes vessels one at a time to respect API limits. For large batches, consider:
- Running overnight
- Using a screen/tmux session
- Splitting into multiple runs

## Checking Results

### Query Database

```bash
sqlite3 /var/www/apihub/data/vessel_static_data.db <<EOF
SELECT 
    mmsi,
    favorable_wind_percentage,
    average_wind_assistance_score,
    wind_assistance_potential
FROM vessel_wind_alignment
ORDER BY average_wind_assistance_score DESC
LIMIT 20;
EOF
```

### Via API

```bash
# Get top vessels
curl http://localhost:5000/ships/api/wind-alignment/top?limit=20

# Get specific vessel
curl http://localhost:5000/ships/api/wind-alignment/211281610
```

## Troubleshooting

### API Rate Limits

If you hit rate limits:
- The script includes rate limiting (100ms between requests)
- Open-Meteo is generous with limits
- If issues persist, add delays in `wind_data_fetcher.py`

### Database Locked

If database is locked:
```bash
# Check what's accessing it
lsof /var/www/apihub/data/vessel_static_data.db

# Stop other services temporarily
sudo systemctl stop ais-web-tracker
# Run analysis
# Restart services
sudo systemctl start ais-web-tracker
```

### Out of Memory

For very large datasets:
- Process in smaller batches
- Reduce `max_positions_per_vessel` parameter
- Monitor memory usage: `htop` or `free -h`

## Expected Results

After analysis, you'll have:
- `vessel_wind_alignment` table with results
- Wind assistance scores (0-100) for each vessel
- Potential categories (high/medium/low/none)
- Percentage of time traveling with favorable winds

Use this data to identify vessels that would benefit most from wind propulsion!

