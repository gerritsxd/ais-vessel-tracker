# Developer Guide

## Overview

This is your central reference for all development tasks. If you're setting up locally, deploying to VPS, or debugging, start here.

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Running Services Locally](#running-services-locally)
3. [Testing](#testing)
4. [Database Management](#database-management)
5. [VPS Deployment](#vps-deployment)
6. [Systemd Service Management](#systemd-service-management)
7. [Debugging & Troubleshooting](#debugging--troubleshooting)
8. [Common Tasks](#common-tasks)

---

## Local Development Setup

### First Time Setup

```bash
# 1. Clone repository
git clone https://github.com/gerritsxd/ais-vessel-tracker.git
cd ais-vessel-tracker

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r config/requirements.txt

# 5. Create environment configuration
cp .env.example .env
# Edit .env with your API keys

# 6. Create data directory
mkdir data
```

### API Keys Setup

Create your API key files:

```bash
# AISStream keys (recommended method)
cp config/aisstream_keys.example config/aisstream_keys
# Edit config/aisstream_keys with your actual keys (one per line)

# Or use .env (alternative)
# AIS_API_KEY_1=your_key_1
# AIS_API_KEY_2=your_key_2
# DATALASTIC_API_KEY=your_datalastic_key
# GOOGLE_GEMINI_API_KEY=your_gemini_key
```

**Get API keys:**
- AISStream: https://aisstream.io/
- Datalastic: https://www.datalastic.com/
- Google Gemini: https://makersuite.google.com/app/apikey

---

## Running Services Locally

### Core Services

#### 1. AIS Data Collector (Real-time)
```bash
# Collects vessel data from AISStream WebSocket
python src/collectors/ais_collector.py

# Or use batch file (Windows)
config\run_collector.bat
```

**What it does:**
- Connects to AISStream WebSocket
- Filters for cargo/tanker vessels ≥100m
- Saves to `data/vessel_static_data.db`
- Auto-reconnects on disconnect
- Prints stats every 5 minutes

**Stop:** `Ctrl+C` (graceful shutdown)

#### 2. Flask Web Tracker
```bash
# Main web application with real-time tracking
python src/services/web_tracker.py
```

**Access:** http://localhost:5000/ships/

**What it does:**
- Serves web interface
- Real-time WebSocket updates
- REST API endpoints
- Tracks 900 vessels (with 6 API keys)

**Stop:** `Ctrl+C`

#### 3. Atlantic Tracker (Optional)
```bash
# Polls Datalastic API for mid-ocean coverage
python src/collectors/atlantic_tracker.py
```

**What it does:**
- Scans Atlantic Ocean grid cells
- Fills gaps between continents
- Uses Datalastic REST API
- Runs every 30 minutes

#### 4. Emissions Matcher (Optional)
```bash
# Matches vessels with EU MRV emissions data
python src/services/emissions_matcher.py
```

**What it does:**
- Matches by IMO number
- Syncs detailed ship types
- Runs every 5 minutes

#### 5. Econowind Score Updater (Optional)
```bash
# Calculates wind propulsion fit scores
python src/services/econowind_score_updater.py
```

**What it does:**
- Scores vessels 0-8 scale
- Based on type, size, emissions
- Runs every hour

---

## Testing

### Run All Tests

```bash
# Run pytest suite
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

### Run Specific Tests

```bash
# Test AIS parsing only
pytest tests/test_parsing.py -v

# Test specific function
pytest tests/test_parsing.py::test_parse_ship_static_data -v
```

### Linting

```bash
# Critical checks (must pass)
flake8 src/collectors/ais_collector.py --count --select=E9,F63,F7 --show-source

# Style checks (warnings)
flake8 src/collectors/ais_collector.py --max-line-length=120 --statistics

# Check all files
flake8 src/ --max-line-length=120 --ignore=F824
```

### Manual Testing

```bash
# Test database connection
python -c "import sqlite3; conn = sqlite3.connect('data/vessel_static_data.db'); print('OK')"

# Test API key loading
python -c "from config.env_loader import config; print(f'Keys: {len(config.ais_api_keys)}')"

# Test imports
python -c "from src.collectors.ais_collector import init_database; print('OK')"
```

---

## Database Management

### View Database Contents

```bash
# Open SQLite shell
sqlite3 data/vessel_static_data.db

# Or use a GUI
# - DB Browser for SQLite (https://sqlitebrowser.org/)
# - VSCode SQLite extension
```

**Common queries:**
```sql
-- Count vessels
SELECT COUNT(*) FROM vessels_static;

-- View recent vessels
SELECT mmsi, name, ship_type, length, last_updated 
FROM vessels_static 
ORDER BY last_updated DESC 
LIMIT 10;

-- Count by ship type
SELECT ship_type, COUNT(*) as count 
FROM vessels_static 
GROUP BY ship_type 
ORDER BY count DESC;

-- View large vessels
SELECT mmsi, name, length, beam, flag_state 
FROM vessels_static 
WHERE length >= 200 
ORDER BY length DESC;
```

### Flush/Reset Database

#### Option 1: Delete Database File (Nuclear)
```bash
# Stop all services first!
# Then delete database
rm data/vessel_static_data.db

# Or Windows:
del data\vessel_static_data.db

# Database will be recreated on next run
```

#### Option 2: Clear Specific Tables (Surgical)
```bash
sqlite3 data/vessel_static_data.db

# Delete all vessel positions (keep vessel data)
DELETE FROM vessel_positions;

# Delete all vessels (keep table structure)
DELETE FROM vessels_static;

# Or drop and recreate tables
DROP TABLE vessels_static;
DROP TABLE vessel_positions;
-- Tables will be recreated on next run
```

#### Option 3: Clean Old Data (Maintenance)
```bash
# Remove position history older than 7 days
python src/utils/cleanup_database.py

# Remove non-cargo/tanker vessels
python src/utils/cleanup_non_cargo_tankers.py
```

### Backup Database

```bash
# Create backup
cp data/vessel_static_data.db data/vessel_static_data.db.backup

# Or with timestamp
cp data/vessel_static_data.db "data/vessel_static_data_$(date +%Y%m%d_%H%M%S).db"

# Windows:
copy data\vessel_static_data.db data\vessel_static_data.db.backup
```

### Export Data

```bash
# Export to CSV
sqlite3 data/vessel_static_data.db <<EOF
.mode csv
.headers on
.output vessels_export.csv
SELECT * FROM vessels_static;
.quit
EOF

# Or use Python script
python src/utils/export_to_csv.py
```

---

## VPS Deployment

### Initial Setup

```bash
# On VPS (as user 'erik')
cd /var/www
sudo git clone https://github.com/gerritsxd/ais-vessel-tracker.git apihub
cd apihub
sudo chown -R erik:erik .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r config/requirements.txt

# Setup environment
cp .env.example .env
nano .env  # Fill in production API keys
chmod 600 .env  # Secure the file

# Create data directory
mkdir -p data logs

# Initialize database (optional - will auto-create)
python src/collectors/ais_collector.py
# Press Ctrl+C after a few seconds
```

### Deploy Code Updates

```bash
# On local machine: Push changes
git add .
git commit -m "Your changes"
git push origin main

# On VPS: Pull and restart
cd /var/www/apihub
git pull origin main
source venv/bin/activate
pip install -r config/requirements.txt --upgrade  # If dependencies changed
sudo systemctl restart ais-web-tracker
sudo systemctl restart ais-collector
```

**One-liner update:**
```bash
cd /var/www/apihub && git pull && sudo systemctl restart ais-web-tracker ais-collector
```

---

## Systemd Service Management

### Service Files Location

```
/etc/systemd/system/
├── ais-collector.service           # AIS data collection
├── ais-web-tracker.service         # Flask web app
├── ais-atlantic-tracker.service    # Atlantic coverage (optional)
├── ais-emissions-matcher.service   # Emissions sync (optional)
└── ais-econowind-updater.service   # Score calculation (optional)
```

### Install Services

```bash
# Copy service files
sudo cp config/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable ais-collector
sudo systemctl enable ais-web-tracker

# Start services
sudo systemctl start ais-collector
sudo systemctl start ais-web-tracker
```

### Service Commands

#### Check Status
```bash
# Single service
sudo systemctl status ais-web-tracker

# All AIS services
sudo systemctl status ais-*

# Compact view
systemctl status ais-* --no-pager
```

#### Start/Stop/Restart
```bash
# Start
sudo systemctl start ais-web-tracker

# Stop
sudo systemctl stop ais-web-tracker

# Restart (after code changes)
sudo systemctl restart ais-web-tracker

# Restart all
sudo systemctl restart ais-*
```

#### Enable/Disable Auto-start
```bash
# Enable (start on boot)
sudo systemctl enable ais-web-tracker

# Disable (don't start on boot)
sudo systemctl disable ais-web-tracker
```

#### View Logs
```bash
# Live logs (follow)
sudo journalctl -u ais-web-tracker -f

# Last 100 lines
sudo journalctl -u ais-web-tracker -n 100

# Since specific time
sudo journalctl -u ais-web-tracker --since "1 hour ago"

# All AIS services
sudo journalctl -u ais-* -f

# Filter by priority (error and above)
sudo journalctl -u ais-web-tracker -p err -f
```

### Quick Service Debugging

```bash
# Is it running?
sudo systemctl is-active ais-web-tracker

# Is it enabled (auto-start)?
sudo systemctl is-enabled ais-web-tracker

# When did it start?
sudo systemctl show ais-web-tracker --property=ActiveEnterTimestamp

# What's the PID?
sudo systemctl show ais-web-tracker --property=MainPID

# Full status with recent logs
sudo systemctl status ais-web-tracker -l
```

---

## Debugging & Troubleshooting

### Service Won't Start

```bash
# Check detailed status
sudo systemctl status ais-web-tracker -l

# Check logs for errors
sudo journalctl -u ais-web-tracker -n 50

# Try running manually
cd /var/www/apihub
source venv/bin/activate
python src/services/web_tracker.py
# See the actual error
```

### Database Locked Error

```bash
# Check what's accessing the database
lsof data/vessel_static_data.db

# Or on Linux
fuser data/vessel_static_data.db

# Kill processes holding the lock
sudo systemctl stop ais-collector
sudo systemctl stop ais-web-tracker
```

### Import Errors

```bash
# Verify Python path
python -c "import sys; print('\n'.join(sys.path))"

# Check if module exists
python -c "from src.collectors.ais_collector import init_database; print('OK')"

# Reinstall dependencies
pip install -r config/requirements.txt --force-reinstall
```

### Port Already in Use

```bash
# Check what's using port 5000
sudo lsof -i :5000

# Or
sudo netstat -tulpn | grep 5000

# Kill process
sudo kill <PID>

# Or change port in .env
FLASK_PORT=5001
```

### API Connection Issues

```bash
# Test AISStream WebSocket
python -c "
import websocket
ws = websocket.create_connection('wss://stream.aisstream.io/v0/stream')
print('Connected!')
ws.close()
"

# Test Datalastic API
curl -X GET "https://api.datalastic.com/api/v0/vessel" \
  -H "apikey: YOUR_KEY"

# Check network
ping aisstream.io
```

### Check Configuration

```bash
# Validate environment config
python config/env_loader.py

# Check API keys are loaded
python -c "
from config.env_loader import config
print(f'AISStream keys: {len(config.ais_api_keys)}')
print(f'Datalastic: {\"Set\" if config.datalastic_api_key else \"Not set\"}')
"
```

---

## Common Tasks

### Update Dependencies

```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install flask --upgrade

# Update all packages (careful!)
pip install -r config/requirements.txt --upgrade

# Regenerate pinned requirements
pip freeze > config/requirements-freeze.txt
```

### Import Data

```bash
# Import EU MRV emissions data
python src/utils/import_mrv_data.py

# Import wind propulsion data
python src/utils/import_wind_propulsion_mmsi.py

# Restart web tracker to see new data
sudo systemctl restart ais-web-tracker
```

### Run Scrapers

```bash
# Company intelligence scraper (Gemini AI)
python src/utils/company_intelligence_scraper_gemini.py --max-companies 50

# Gross tonnage scraper
python src/collectors/gt_search_scraper.py

# Browser-based scraper (requires Playwright)
python src/utils/browser_gt_scraper.py
```

### Generate Reports

```bash
# Export vessel data to CSV
python src/utils/export_to_csv.py

# Query database interactively
python src/utils/query_vessels.py

# Check data quality
python src/utils/check_data.py
```

### Monitor Services

```bash
# Watch all service statuses (refreshes every 2s)
watch -n 2 'systemctl status ais-* --no-pager'

# Monitor resource usage
htop  # Or top

# Check disk space
df -h /var/www/apihub/data

# Check database size
ls -lh data/*.db
```

### Clean Up

```bash
# Remove old position data (>7 days)
python src/utils/cleanup_database.py

# Remove non-cargo/tanker vessels
python src/utils/cleanup_non_cargo_tankers.py

# Vacuum database (reclaim space)
sqlite3 data/vessel_static_data.db "VACUUM;"

# Clear logs
sudo journalctl --vacuum-time=7d  # Keep only last 7 days
```

---

## Environment-Specific Notes

### Local Development (Windows/Mac)

- Use `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
- Database at `data/vessel_static_data.db`
- Web interface: http://localhost:5000/ships/
- Stop services with `Ctrl+C`

### Production VPS (Linux)

- Services managed by systemd
- Database at `/var/www/apihub/data/vessel_static_data.db`
- Web interface: https://gerritsxd.com/ships/
- Behind Nginx reverse proxy
- Logs via `journalctl`

---

## Quick Reference

### One-Liners

```bash
# Full restart after code changes
cd /var/www/apihub && git pull && sudo systemctl restart ais-*

# Check all services
sudo systemctl status ais-* --no-pager

# Tail all logs
sudo journalctl -u ais-* -f

# Count vessels in DB
sqlite3 data/vessel_static_data.db "SELECT COUNT(*) FROM vessels_static;"

# Backup database
cp data/vessel_static_data.db "data/backup_$(date +%Y%m%d).db"

# Test configuration
python config/env_loader.py && pytest tests/ -v
```

### File Locations

```
Project Root: /var/www/apihub (VPS) or c:\Users\gerrit\Desktop\apihub (local)
├── data/
│   ├── vessel_static_data.db      # Main database
│   ├── company_cache.json         # Cached company lookups
│   └── *.xlsx                     # Imported data files
├── logs/                          # Application logs (if enabled)
├── src/
│   ├── collectors/                # Data collection scripts
│   ├── services/                  # Background services
│   └── utils/                     # Utility scripts
├── tests/                         # Test suite
├── config/
│   ├── requirements.txt           # Python dependencies
│   ├── systemd/                   # Service files
│   └── env_loader.py              # Config loader
├── .env                           # Environment variables (gitignored)
└── config/
    ├── aisstream_keys             # AISStream API keys (gitignored)
    └── *_api_key.txt              # Other API keys (gitignored)
```

---

## Getting Help

### Documentation

- **This file**: Central developer reference
- `docs/QUICK_START.md`: First-time setup
- `docs/DEPLOYMENT.md`: VPS deployment details
- `docs/ENVIRONMENT_CONFIG.md`: Configuration guide
- `docs/DEPENDENCY_MANAGEMENT.md`: Package management
- `README.md`: Project overview

### Logs

```bash
# Application logs
tail -f logs/*.log

# Systemd logs
sudo journalctl -u ais-web-tracker -f

# Python errors
python src/services/web_tracker.py  # Run directly to see errors
```

### Testing

```bash
# Verify everything works
pytest tests/ -v
python config/env_loader.py
python -m src.collectors.ais_collector  # Should start without errors (Ctrl+C to stop)
```

---

## Workflow Summary

### Daily Development
1. `git pull` - Get latest code
2. Make changes
3. `pytest tests/` - Run tests
4. `python src/services/web_tracker.py` - Test locally
5. `git add . && git commit -m "..."` - Commit
6. `git push` - Push to GitHub

### Deploying to VPS
1. `git push` - Push local changes
2. SSH to VPS
3. `cd /var/www/apihub && git pull`
4. `sudo systemctl restart ais-*` - Restart services
5. `sudo systemctl status ais-*` - Verify running

### Troubleshooting
1. `sudo systemctl status ais-web-tracker` - Check status
2. `sudo journalctl -u ais-web-tracker -n 50` - Check logs
3. `python src/services/web_tracker.py` - Run manually to see errors
4. Fix issue
5. `sudo systemctl restart ais-web-tracker` - Restart

---

**This guide centralizes all developer operations in one place. Bookmark it!** 📚
