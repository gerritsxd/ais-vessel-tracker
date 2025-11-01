# 🚢 Maritime Data Intelligence Platform

A production-grade vessel tracking and emissions analysis system. Combines real-time AIS data streaming, EU MRV emissions data, and interactive 3D visualizations to provide comprehensive maritime intelligence.

🌐 **Live Demo:** [https://gerritsxd.com/ships/](https://gerritsxd.com/ships/)

![Vessels](https://img.shields.io/badge/Vessels-1050+-blue) ![Emissions Data](https://img.shields.io/badge/Emissions-16K+-green) ![Status](https://img.shields.io/badge/Status-Live-success) ![Python](https://img.shields.io/badge/Python-3.13-blue)

## Features

### 🗺️ Web-Based Real-Time Tracker (`web_tracker.py`)
- **Interactive Map**: Live vessel positions on OpenStreetMap with Leaflet.js
- **900 Vessel Tracking**: Monitors up to 900 large vessels simultaneously
- **API Key Rotation**: Distributes load across 6 API keys (18 WebSocket connections)
- **Detailed Sidebar**: Click any vessel to see:
  - Basic info (MMSI, name, flag, type, company)
  - Dimensions (length, beam, IMO, call sign)
  - Current position (lat/lon, speed, course)
  - External links (MarineTraffic, VesselFinder)
- **24-Hour Route Display**: Yellow dashed line showing vessel's path
- **Color-Coded Ships**: Passenger (magenta), Cargo (green), Tanker (red), Other (cyan)
- **Size-Based Markers**: Large dots (≥200m), small dots (100-200m)
- **Real-Time Updates**: WebSocket connection for live position streaming
- **Database Viewer**: Browse all vessels in sortable table format

### 📊 Data Collection (`ais_collector.py`)
- **Persistent Storage**: SQLite database with UPSERT logic
- **Smart Filtering**: Only saves vessels ≥100m (excludes container ships)
- **Company Lookup**: Automatically enriches data with signatory company names
- **Flag State Decoding**: Determines country from MMSI MID
- **Auto-Reconnect**: Exponential backoff on connection loss
- **Systemd Service**: Runs continuously in background on VPS
- **Comprehensive Data**: MMSI, name, type, dimensions, IMO, call sign, flag, destination, ETA, draught

### 🏢 Company Data (`company_lookup.py` & `retrofill_companies.py`)
- **ITF Database Integration**: Scrapes signatory company names from ITF Global lookup
- **Smart Caching**: Saves API calls with JSON cache file
- **Batch Processing**: Retrofills company data for existing vessels
- **Preserved on Update**: Company names persist when vessel data updates

## Quick Start

### Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/gerritsxd/ais-vessel-tracker.git
   cd ais-vessel-tracker
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   - Get API keys from https://aisstream.io/apikeys
   - Add them to `api.txt` (one per line)
   - Recommended: 6 keys for tracking 900 vessels

3. **Run the web tracker:**
   ```bash
   python web_tracker.py
   ```
   Open http://localhost:5000/ships/ in your browser

4. **Run the data collector (separate terminal):**
   ```bash
   python ais_collector.py
   ```

### Production Deployment (VPS)

1. **Setup systemd services:**
   ```bash
   # Copy service files
   sudo cp ais-collector.service /etc/systemd/system/
   sudo cp ais-web-tracker.service /etc/systemd/system/
   
   # Enable and start services
   sudo systemctl enable ais-collector ais-web-tracker
   sudo systemctl start ais-collector ais-web-tracker
   
   # Check status
   sudo systemctl status ais-collector
   sudo systemctl status ais-web-tracker
   ```

2. **Configure Nginx reverse proxy:**
   ```nginx
   location /ships/ {
       proxy_pass http://localhost:5000/ships/;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }
   ```

3. **Enrich with company data:**
   ```bash
   # Run in background (takes ~3 hours for 7000+ vessels)
   nohup python retrofill_companies.py > retrofill.log 2>&1 &
   ```

## Usage

### Step 1: Collect Static Vessel Data

Run `ais_collector.py` to build your vessel database:
- Connects to AISStream via WebSocket
- Subscribes to StaticDataReport and ShipStaticData messages
- Extracts vessel information:
  - **MMSI** (Maritime Mobile Service Identity) - Primary key
  - **Name** - Vessel name
  - **Ship Type** - Numeric ship type code
  - **Length** - Vessel length in meters
  - **Beam** - Vessel width in meters
  - **IMO** - International Maritime Organization number
  - **Call Sign** - Radio call sign
  - **Flag State** - Country of registration (decoded from MMSI)
  - **Last Updated** - UTC timestamp of last data update
- Saves/updates data in SQLite database using UPSERT operations
- Auto-reconnects on connection loss

**Recommended:** Let it run for several hours or overnight to build a comprehensive database.

### Step 2: Track Filtered Vessels

Run `track_filtered_vessels.py` to monitor specific vessels in real-time:
- Queries database for vessels matching criteria:
  - Length >= 100 meters
  - Excludes container ships (type 71, 72)
- Creates WebSocket connections (max 50 MMSIs per connection)
- Tracks real-time position updates:
  - Latitude/Longitude
  - Speed Over Ground (SOG)
  - Course Over Ground (COG)
  - Timestamp
- Displays voyage information when available:
  - Destination
  - ETA (Estimated Time of Arrival)
  - Draught

## Database Schema

**Table: `vessels_static`**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| mmsi | INTEGER | PRIMARY KEY, UNIQUE, NOT NULL | Maritime Mobile Service Identity |
| name | TEXT | | Vessel name |
| ship_type | INTEGER | | Ship type code (see ship_type_reference.txt) |
| length | INTEGER | | Length in meters |
| beam | INTEGER | | Width in meters |
| imo | INTEGER | | IMO number |
| call_sign | TEXT | | Radio call sign |
| flag_state | TEXT | | Country of registration (from MMSI MID) |
| signatory_company | TEXT | | Company name (from ITF database) |
| destination | TEXT | | Current destination |
| eta | TEXT | | Estimated time of arrival (JSON) |
| draught | REAL | | Current draught in meters |
| nav_status | INTEGER | | Navigation status code |
| last_updated | TEXT | NOT NULL | UTC timestamp (ISO format) |

**Table: `vessel_positions`**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| mmsi | INTEGER | Foreign key to vessels_static |
| latitude | REAL | Position latitude |
| longitude | REAL | Position longitude |
| sog | REAL | Speed over ground (knots) |
| cog | REAL | Course over ground (degrees) |
| timestamp | TEXT | UTC timestamp |

## Querying the Database

You can query the database using any SQLite client or Python:

```python
import sqlite3

conn = sqlite3.connect('vessel_static_data.db')
cursor = conn.cursor()

# Get all vessels
cursor.execute('SELECT * FROM vessels_static')
vessels = cursor.fetchall()

# Get vessels by type
cursor.execute('SELECT * FROM vessels_static WHERE ship_type = ?', (70,))

# Get recently updated vessels
cursor.execute('SELECT * FROM vessels_static ORDER BY last_updated DESC LIMIT 10')

conn.close()
```

## Customization

You can modify the subscription in `ais_collector.py`:
- **Add geographical filters** using `FilterBoundingBoxes` to limit coverage area
- **Subscribe to other message types** (PositionReport, etc.)
- **Modify database schema** to capture additional fields
- **Add data processing** or analytics logic

Example geographical filter (Gulf of Mexico):
```python
subscribe_message = {
    "APIKey": API_KEY,
    "FilterMessageTypes": ["StaticDataReport"],
    "FilterBoundingBoxes": [
        {"MinLat": 20, "MaxLat": 30, "MinLon": -90, "MaxLon": -80}
    ]
}
```

## Utility Scripts

### Query Vessels (`query_vessels.py`)

Interactive tool to query and explore the vessel database:

```bash
python query_vessels.py
```

Features:
- Show database statistics
- List recent vessels
- Search by MMSI
- Search by vessel name
- Filter by ship type

### Check Data Quality (`check_data.py`)

View statistics about data completeness:

```bash
python check_data.py
```

Shows:
- Total vessels collected
- Percentage with names, dimensions, ship types, etc.
- Top 10 largest vessels

### Check Big Ships (`check_big_ships.py`)

List all vessels over 100 meters:

```bash
python check_big_ships.py
```

### Export to CSV (`export_to_csv.py`)

Export all vessel data to a CSV file:

```bash
# Export with auto-generated filename
python export_to_csv.py

# Export with custom filename
python export_to_csv.py my_vessels.csv
```

## 📁 Project Structure

```
apihub/
├── src/                              # Core application code
│   ├── collectors/                   # Data collection services
│   │   ├── ais_collector.py          # Real-time AIS data streaming
│   │   ├── company_lookup.py         # ITF company database scraper
│   │   └── mmsi_mid_lookup.py        # MMSI to country decoder
│   ├── services/                     # Background services
│   │   ├── web_tracker.py            # Flask web app + REST API
│   │   ├── emissions_matcher.py      # Match vessels to EU MRV data
│   │   └── econowind_score_updater.py # Calculate retrofit suitability
│   └── utils/                        # Utility scripts
│       ├── cleanup_database.py       # Database maintenance
│       ├── import_mrv_data.py        # Import EU emissions data
│       └── query_vessels.py          # Interactive DB queries
│
├── templates/                        # HTML templates
│   ├── map.html                      # Real-time tracking map
│   ├── database_enhanced.html        # Database browser
│   ├── fleet_visualization.html      # 3D company network viz
│   └── sql_query.html                # SQL query interface
│
├── data/                             # Data files (gitignored)
│   ├── vessel_static_data.db         # SQLite database
│   ├── company_cache.json            # Cached company lookups
│   └── 2024-v99-*.xlsx               # EU MRV emissions data
│
├── config/                           # Configuration
│   ├── requirements.txt              # Python dependencies
│   ├── api.txt                       # AISStream API keys (gitignored)
│   └── systemd/                      # Service files
│       ├── ais-collector.service
│       ├── ais-web-tracker.service
│       ├── ais-emissions-matcher.service
│       └── ais-econowind-updater.service
│
├── scripts/                          # One-off/utility scripts
│   ├── check_big_ships.py            # List vessels >100m
│   ├── export_to_csv.py              # CSV export
│   ├── retrofill_companies.py        # Batch company enrichment
│   └── setup_vps.sh                  # VPS deployment script
│
├── docs/                             # Documentation
│   ├── QUICK_START.md                # Getting started guide
│   ├── DEPLOYMENT.md                 # Production deployment
│   ├── DATA_SOURCES_OVERVIEW.md      # Data sources & APIs
│   └── reference/                    # Reference docs
│       ├── SQL_QUERY_CHEATSHEET.txt
│       └── SHIP_TYPE_CHEATSHEET.md
│
└── exports/                          # Generated exports
    └── vessels_current.csv
```

## API Endpoints

- `GET /ships/` - Main tracking interface
- `GET /ships/database` - Database viewer with filters
- `GET /ships/api/vessels` - JSON list of all tracked vessels
- `GET /ships/api/stats` - Tracking statistics
- `GET /ships/api/vessel/<mmsi>/route?hours=24` - Vessel route history
- `GET /ships/api/companies` - Company statistics
- WebSocket `/ships/socket.io` - Real-time position updates

## Dependencies

```
Flask==3.0.0
Flask-SocketIO==5.3.5
websocket-client==1.9.0
requests==2.31.0
beautifulsoup4==4.12.2
pandas==2.1.3
tqdm==4.66.1
```

## Architecture

### Data Flow

1. **Collection Layer** (`ais_collector.py`)
   - Connects to AISStream WebSocket
   - Filters vessels ≥100m (excludes containers)
   - Saves to SQLite with UPSERT
   - Preserves company data on updates

2. **Enrichment Layer** (`retrofill_companies.py`)
   - Scrapes ITF database for company names
   - Caches results to minimize API calls
   - Runs periodically to update new vessels

3. **Tracking Layer** (`web_tracker.py`)
   - Loads 900 most recent vessels from DB
   - Creates 18 WebSocket connections (6 keys × 3 each)
   - Distributes 50 vessels per connection
   - Streams position updates to web clients

4. **Presentation Layer** (Web Interface)
   - Interactive Leaflet map
   - Real-time position updates via Socket.IO
   - Sidebar with detailed vessel info
   - Route history visualization

### API Key Rotation

With 6 API keys, the system distributes load:
- **Key 1:** Connections 1-3 (150 vessels)
- **Key 2:** Connections 4-6 (150 vessels)
- **Key 3:** Connections 7-9 (150 vessels)
- **Key 4:** Connections 10-12 (150 vessels)
- **Key 5:** Connections 13-15 (150 vessels)
- **Key 6:** Connections 16-18 (150 vessels)

**Total:** 900 vessels tracked simultaneously

## Monitoring

### Check Service Status
```bash
sudo systemctl status ais-collector
sudo systemctl status ais-web-tracker
```

### View Logs
```bash
# Real-time logs
sudo journalctl -u ais-collector -f
sudo journalctl -u ais-web-tracker -f

# Last 100 lines
sudo journalctl -u ais-collector -n 100
```

### Database Statistics
```bash
python check_data.py
```

## Troubleshooting

### "Concurrent connections exceeded" Error
- **Cause:** Too many connections per API key
- **Solution:** Add more API keys to `api.txt` or reduce vessel limit

### Company Names Disappearing
- **Cause:** Old bug (now fixed) - collector was overwriting company data
- **Solution:** Re-run `python retrofill_companies.py`

### No Vessels Showing on Map
- **Check:** Database has vessels: `python check_data.py`
- **Check:** Services running: `sudo systemctl status ais-web-tracker`
- **Check:** Browser console for WebSocket errors

### Database Locked Errors
- **Cause:** Multiple processes accessing DB simultaneously
- **Solution:** Script retries automatically (3 attempts)

## Performance

- **Database Size:** ~50MB per 10,000 vessels
- **Memory Usage:** ~200MB per service
- **CPU Usage:** <5% on modern VPS
- **Network:** ~1-2 Mbps for 900 vessels
- **Position Updates:** ~10-30 per minute per vessel

## License

MIT License - See LICENSE file for details

## Credits

- **AIS Data:** [AISStream.io](https://aisstream.io/)
- **Company Data:** [ITF Global Lookup](https://lookup.itfglobal.org/)
- **Maps:** [OpenStreetMap](https://www.openstreetmap.org/) & [Leaflet.js](https://leafletjs.com/)

## Contributing

Pull requests welcome! Please ensure:
- Code follows existing style
- API keys remain in gitignored `api.txt`
- Database schema changes include migration notes
