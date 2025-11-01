# 📊 Data Sources Overview for 3D Real-Time Simulation

## 🎯 Project Summary
Real-time 3D vessel tracking simulation powered by **3 integrated data sources** that work together to provide comprehensive maritime intelligence.

---

## 🗄️ **DATABASE 1: Live AIS Data** (Main Database - Real-Time)
**File:** `vessel_static_data.db`  
**Source:** AISStream.io WebSocket API (scanning the sea in real-time)  
**Collector:** `ais_collector.py`

### What It Contains:
```sql
-- Table: vessels_static
- MMSI (unique vessel identifier)
- Vessel Name
- Ship Type (Cargo, Tanker, Passenger, etc.)
- Length & Beam (dimensions in meters)
- IMO Number (international maritime ID)
- Call Sign
- Flag State (country)
- Destination
- ETA (Estimated Time of Arrival)
- Draught (how deep vessel sits in water)
- Navigation Status
- Last Updated (timestamp)

-- Table: vessel_positions (historical tracking)
- Latitude & Longitude
- Speed Over Ground (SOG)
- Course Over Ground (COG)
- Heading
- Timestamp
```

### How It Works:
1. **Connects to AISStream WebSocket** - Real-time global vessel tracking
2. **Receives AIS messages** - Position reports, static data, voyage info
3. **Stores in SQLite** - Continuously updated as vessels move
4. **Runs 24/7** - Background service on VPS

### Current Stats:
- **~13,000+ vessels** tracked
- **Updates every few seconds** for active vessels
- **Global coverage** (all oceans)

---

## 🏢 **DATABASE 2: Company Ownership Data** (Web Scraper)
**File:** Enriched into `vessel_static_data.db` (column: `signatory_company`)  
**Source:** ITF Global Lookup (https://lookup.itfglobal.org)  
**Scraper:** `company_lookup.py`

### What It Contains:
```python
# For each vessel:
- Vessel Name → Company Name
- Signatory Company (ship owner/operator)
```

### How It Works:
1. **Takes vessel names** from AIS database
2. **Searches ITF Lookup** - International Transport Workers' Federation database
3. **Scrapes company information** - Ship owners, operators, managers
4. **Enriches AIS data** - Adds `signatory_company` column

### Example:
```
Vessel: "MAERSK ESSEX"
→ Scrapes ITF → 
Company: "Maersk Line A/S"
```

### Usage:
```python
from company_lookup import get_signatory_company

company = get_signatory_company("MAERSK ESSEX")
# Returns: "Maersk Line A/S"
```

---

## 🌍 **DATABASE 3: EU MRV CO₂ Emissions Data** (Huge Dataset)
**File:** Stored in `vessel_static_data.db` (table: `eu_mrv_emissions`)  
**Source:** EU MRV (Monitoring, Reporting, Verification) Excel file  
**Importer:** `import_mrv_data.py`  
**File:** `2024-v99-22102025-EU MRV Publication of information.xlsx`

### What It Contains:
```sql
-- Table: eu_mrv_emissions
-- 13,964 vessels with detailed emissions data

VESSEL IDENTIFICATION:
- IMO Number (links to AIS data)
- Vessel Name
- Ship Type
- Company Name
- Company IMO
- Reporting Period (year)

CO₂ EMISSIONS:
- Total CO₂ Emissions (million tonnes)
- CO₂ from all voyages
- CO₂ within EU ETS (Emissions Trading System)
- CO₂ from laden voyages
- CO₂ at berth (in port)
- Total CO₂ equivalent emissions

FUEL & EFFICIENCY:
- Total Fuel Consumption (million tonnes)
- Total Distance Travelled (nautical miles)
- Distance Travelled Laden
- Time at Sea (hours)
- Average CO₂ per Distance (kg/nm)
- Average Fuel Consumption per Distance
- Technical Efficiency (EEXI rating)

TRANSPORT WORK:
- Transport Work (mass) - cargo carried
- Transport Work (volume)
- Transport Work (DWT) - deadweight tonnage
- Transport Work (passengers)

ECONOWIND FIT SCORE:
- Calculated score (0-8 points)
- Based on: ship type, length, emissions, efficiency
```

### How It Works:
1. **Reads massive Excel file** - EU official emissions data
2. **Parses complex multi-level headers** - Nested column structure
3. **Calculates Econowind Fit Score** - Identifies best candidates for wind propulsion
4. **Links to AIS via IMO** - Matches emissions to live vessel positions

### Example Record:
```json
{
  "imo": 9253342,
  "vessel_name": "ZHONG REN 121",
  "ship_type": "Bulk carrier",
  "company_name": "SHANGHAI SALVAGE CO.",
  "total_co2_emissions": 15441.1,  // tonnes
  "avg_co2_per_distance": 405.4,   // kg/nm
  "technical_efficiency": "EEXI (10.5 gCO₂/t·nm)",
  "econowind_fit_score": 7         // High fit!
}
```

---

## 🔗 **How The 3 Databases Work Together**

### Data Flow:
```
┌─────────────────────────────────────────────────────────────┐
│                    REAL-TIME 3D SIMULATION                  │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    ┌─────────┴─────────┐
                    │   API Endpoints   │
                    │  (web_tracker.py) │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌──────────────┐
│  DATABASE 1   │    │  DATABASE 2    │    │ DATABASE 3   │
│   AIS Data    │◄───┤ Company Names  │◄───┤ CO₂ Data     │
│               │    │                │    │              │
│ • Position    │    │ • Owner        │    │ • Emissions  │
│ • Speed       │    │ • Operator     │    │ • Efficiency │
│ • Course      │    │ • Manager      │    │ • Fuel Use   │
│ • Dimensions  │    │                │    │ • Fit Score  │
│               │    │                │    │              │
│ LIVE UPDATES  │    │   ENRICHMENT   │    │  ANALYTICS   │
└───────────────┘    └────────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                    Linked by IMO Number
```

### Integration Example:
```python
# Get complete vessel data for 3D simulation
vessel = {
    # From DATABASE 1 (AIS - Real-time)
    "mmsi": 412346220,
    "position": {"lat": 52.3676, "lon": 4.9041},
    "speed": 12.5,
    "course": 180,
    "length": 169,
    "beam": 25,
    
    # From DATABASE 2 (Company Scraper)
    "signatory_company": "SHANGHAI SALVAGE CO.",
    
    # From DATABASE 3 (EU MRV Emissions)
    "total_co2_emissions": 15441.1,
    "avg_co2_per_distance": 405.4,
    "econowind_fit_score": 7,
    "technical_efficiency": "EEXI (10.5 gCO₂/t·nm)"
}
```

---

## 🔄 **Background Services (Continuous Updates)**

### 1. **AIS Collector** (`ais-collector.service`)
- Runs 24/7
- Connects to AISStream WebSocket
- Updates vessel positions in real-time
- Stores static data (name, type, dimensions)

### 2. **Emissions Matcher** (`ais-emissions-matcher.service`)
- Runs every 5 minutes
- Matches new AIS vessels with emissions data
- Links by IMO number
- Reports matching statistics

### 3. **Econowind Score Updater** (`ais-econowind-updater.service`)
- Runs every hour
- Recalculates fit scores
- Integrates new AIS length data
- Updates scores automatically

### 4. **Web Tracker** (`ais-web-tracker.service`)
- Flask web server
- Serves API endpoints
- Real-time WebSocket updates
- Powers the 3D simulation

---

## 📡 **API Endpoints for 3D Simulation**

### Get All Vessels (with all 3 data sources):
```http
GET /ships/api/vessels/combined?limit=1000
```

**Returns:**
```json
[
  {
    "mmsi": 412346220,
    "name": "ZHONG REN 121",
    "imo": 9253342,
    "ship_type": 79,
    "length": 169,
    "beam": 25,
    "flag_state": "China",
    "signatory_company": "SHANGHAI SALVAGE CO.",
    "total_co2_emissions": 15441.1,
    "avg_co2_per_distance": 405.4,
    "econowind_fit_score": 7,
    "technical_efficiency": "EEXI (10.5 gCO₂/t·nm)",
    "ais_last_updated": "2025-11-01T02:43:15.123Z"
  }
]
```

### Get Real-Time Positions:
```http
GET /ships/api/vessels
```

### Get Emissions Data:
```http
GET /ships/api/emissions/vessel/<imo>
```

### Get Score Breakdown:
```http
GET /ships/api/emissions/vessel/<imo>/score-breakdown
```

### Get Statistics:
```http
GET /ships/api/emissions/stats
GET /ships/api/emissions/match-stats
```

---

## 📊 **Data Statistics**

| Data Source | Records | Update Frequency | Coverage |
|-------------|---------|------------------|----------|
| **AIS Data** | ~13,000 vessels | Real-time (seconds) | Global |
| **Company Data** | ~8,000 enriched | On-demand scraping | ITF Database |
| **Emissions Data** | 13,964 vessels | Annual (EU MRV) | EU waters |

### Matching Statistics:
- **Matched vessels** (all 3 sources): ~5,000+
- **AIS only**: ~8,000 (no emissions data)
- **Emissions only**: ~9,000 (not currently tracked by AIS)
- **Match rate**: ~38% (continuously improving)

---

## 🎮 **For Your 3D Simulation**

### What You Can Visualize:

1. **Real-Time Vessel Movement**
   - Live positions from AIS
   - Speed & course vectors
   - 3D ship models scaled by length/beam

2. **Color-Coded by Emissions**
   - Green: Low emissions / High efficiency
   - Yellow: Medium emissions
   - Red: High emissions / Poor efficiency

3. **Company Clustering**
   - Group vessels by owner
   - Show fleet movements
   - Company-level analytics

4. **Econowind Fit Score Overlay**
   - Highlight best candidates (score 6-8)
   - Show potential savings
   - Filter by retrofit suitability

5. **Historical Trails**
   - Show vessel paths
   - Emissions per route
   - Port-to-port analysis

---

## 🚀 **Quick Start for 3D Dev**

### 1. Get All Data:
```javascript
fetch('/ships/api/vessels/combined?limit=5000')
  .then(r => r.json())
  .then(vessels => {
    vessels.forEach(v => {
      // v.mmsi, v.name, v.length, v.beam
      // v.signatory_company
      // v.total_co2_emissions, v.econowind_fit_score
      renderVessel3D(v);
    });
  });
```

### 2. Real-Time Updates (WebSocket):
```javascript
const socket = io();
socket.on('vessel_update', (data) => {
  updateVesselPosition3D(data);
});
```

### 3. Filter High-Value Targets:
```javascript
const highFitVessels = vessels.filter(v => 
  v.econowind_fit_score >= 6 &&
  v.total_co2_emissions > 50000
);
```

---

## 📝 **Summary**

You have **3 powerful data sources** working together:

1. ✅ **Live AIS Data** - Real-time vessel tracking (scanning the sea)
2. ✅ **Company Scraper** - Ship ownership information (ITF Lookup)
3. ✅ **EU MRV Emissions** - Huge CO₂ dataset (13,964 vessels)

All integrated into **one SQLite database** with **continuous background updates** and **REST API endpoints** ready for your **3D real-time simulation**! 🚢🌍📊

---

**Database File:** `vessel_static_data.db`  
**API Base URL:** `http://your-vps/ships/api/`  
**WebSocket:** `ws://your-vps/socket.io/`
