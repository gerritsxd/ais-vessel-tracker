# AIS Stream Collector

This project collects AIS (Automatic Identification System) static data reports from aisstream.io and stores them in a local SQLite database.

## Features

- **Persistent Storage**: Automatically saves vessel data to SQLite database (`vessel_static_data.db`)
- **UPSERT Logic**: Updates existing vessel records or inserts new ones based on MMSI
- **Secure API Key Management**: Reads API key from `api.txt` file (not hardcoded)
- **Comprehensive Data Collection**: Captures MMSI, name, ship type, dimensions, IMO, call sign, and timestamps
- **Real-time Updates**: Continuously receives and processes vessel static data reports

## Setup

1. **Activate the virtual environment:**
   ```bash
   .\hub\Scripts\activate
   ```

2. **Get your API key:**
   - Visit https://aisstream.io/apikeys
   - Copy your API key

3. **Configure the API key:**
   - Your API key should already be in `api.txt` (last non-empty line)
   - If not, add it to `api.txt` on a new line

4. **Run the collector:**
   ```bash
   python ais_collector.py
   ```

5. **Stop the collector:**
   - Press `Ctrl+C` to gracefully stop and close the database connection

## What it does

The script connects to AISStream via WebSocket and:
- Subscribes to StaticDataReport messages only
- Extracts vessel information:
  - **MMSI** (Maritime Mobile Service Identity) - Primary key
  - **Name** - Vessel name
  - **Ship Type** - Numeric ship type code
  - **Length** - Vessel length in meters
  - **Beam** - Vessel width in meters
  - **IMO** - International Maritime Organization number
  - **Call Sign** - Radio call sign
  - **Last Updated** - UTC timestamp of last data update
- Saves/updates data in SQLite database using UPSERT operations
- Prints received data to console with database save confirmation

## Database Schema

**Table: `vessels_static`**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| mmsi | INTEGER | PRIMARY KEY, UNIQUE, NOT NULL | Maritime Mobile Service Identity |
| name | TEXT | | Vessel name |
| ship_type | INTEGER | | Ship type code |
| length | INTEGER | | Length in meters |
| beam | INTEGER | | Width in meters |
| imo | INTEGER | | IMO number |
| call_sign | TEXT | | Radio call sign |
| last_updated | TEXT | NOT NULL | UTC timestamp (ISO format) |

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

### Export to CSV (`export_to_csv.py`)

Export all vessel data to a CSV file:

```bash
# Export with auto-generated filename
python export_to_csv.py

# Export with custom filename
python export_to_csv.py my_vessels.csv
```

## Files

- **`ais_collector.py`** - Main collector script
- **`query_vessels.py`** - Interactive database query tool
- **`export_to_csv.py`** - CSV export utility
- **`api.txt`** - Contains your AISStream API key
- **`vessel_static_data.db`** - SQLite database (created automatically)
- **`requirements.txt`** - Python dependencies
- **`hub/`** - Virtual environment directory

## Dependencies

- websocket-client==1.9.0
- sqlite3 (built-in with Python)

## Error Handling

The script includes comprehensive error handling:
- Database connection errors
- Missing or invalid API key
- WebSocket connection issues
- Malformed message data
- Graceful shutdown on Ctrl+C
