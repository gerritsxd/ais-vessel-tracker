# 🌍 EU MRV Emissions Data Integration

## Overview

The AIS Vessel Tracker now includes **EU MRV (Monitoring, Reporting and Verification) emissions data** for 13,964 vessels! This creates a powerful hybrid database combining:

- **Live AIS tracking data** (dynamic, real-time positions)
- **EU MRV emissions data** (static, detailed CO2 emissions and efficiency metrics)

## 📊 Dataset Statistics

- **Total vessels**: 13,964 with emissions data
- **Unique companies**: 3,544
- **Total CO2 emissions**: 145.9 million tonnes
- **Vessels matched with AIS**: 1,220 vessels have both live tracking AND emissions data
- **Reporting period**: 2024

## 🗄️ Database Schema

### New Table: `eu_mrv_emissions`

```sql
CREATE TABLE eu_mrv_emissions (
    id INTEGER PRIMARY KEY,
    imo INTEGER UNIQUE NOT NULL,
    vessel_name TEXT,
    ship_type TEXT,
    reporting_period INTEGER,
    company_name TEXT,
    company_imo INTEGER,
    
    -- CO2 Emissions (in tonnes)
    total_co2_emissions REAL,
    co2_emissions_from_all_voyages REAL,
    co2_emissions_within_ets REAL,
    co2_emissions_from_laden_voyages REAL,
    co2_emissions_at_berth REAL,
    total_co2eq_emissions REAL,
    
    -- Fuel & Distance
    total_fuel_consumption REAL,
    total_distance_travelled REAL,
    distance_travelled_laden REAL,
    total_time_at_sea REAL,
    
    -- Transport Work
    transport_work_mass REAL,
    transport_work_volume REAL,
    transport_work_dwt REAL,
    transport_work_pax REAL,
    
    -- Efficiency Indicators
    avg_co2_per_distance REAL,
    avg_co2_per_transport_work_mass REAL,
    avg_fuel_consumption_per_distance REAL,
    
    FOREIGN KEY (imo) REFERENCES vessels_static(imo)
)
```

## 🚀 API Endpoints

### 1. Get Vessel Emissions by IMO
```
GET /ships/api/emissions/vessel/<imo>
```

**Example:**
```bash
curl http://149.202.53.2:5000/ships/api/emissions/vessel/9321483
```

**Response:**
```json
{
  "imo": 9321483,
  "vessel_name": "MSC FANTASIA",
  "company_name": "MSC Cruise Management UK Ltd",
  "total_co2_emissions": 108758.0,
  "total_fuel_consumption": 34567.2,
  "total_distance_travelled": 89234.5,
  "avg_co2_per_distance": 1218.5,
  "mmsi": 248526000,
  "length": 333,
  "flag_state": "Malta"
}
```

### 2. Get Top CO2 Emitters
```
GET /ships/api/emissions/top?limit=50&ship_type=Passenger
```

**Parameters:**
- `limit` (optional): Number of results (default: 50)
- `ship_type` (optional): Filter by ship type

**Example:**
```bash
curl http://149.202.53.2:5000/ships/api/emissions/top?limit=10
```

### 3. Get Company Emissions
```
GET /ships/api/emissions/company/<company_name>
```

**Example:**
```bash
curl http://149.202.53.2:5000/ships/api/emissions/company/Maersk
```

**Response:**
```json
{
  "company": "Maersk",
  "total_vessels": 145,
  "total_co2_emissions": 8234567.0,
  "average_co2_per_vessel": 56790.0,
  "vessels": [...]
}
```

### 4. Get Emissions Statistics
```
GET /ships/api/emissions/stats
```

**Example:**
```bash
curl http://149.202.53.2:5000/ships/api/emissions/stats
```

**Response:**
```json
{
  "total_vessels": 13964,
  "total_co2_emissions": 145913862.0,
  "average_co2_per_vessel": 10449.0,
  "max_co2_emission": 124615.0,
  "total_companies": 3544,
  "vessels_with_ais_data": 1220,
  "by_ship_type": [...]
}
```

### 5. Get Combined Vessel Data (AIS + Emissions)
```
GET /ships/api/vessels/combined?limit=100&min_co2=50000
```

**Parameters:**
- `limit` (optional): Number of results (default: 100)
- `min_co2` (optional): Minimum CO2 emissions filter

**Example:**
```bash
curl http://149.202.53.2:5000/ships/api/vessels/combined?min_co2=100000
```

Returns vessels that have BOTH live AIS tracking data AND emissions data.

## 📝 SQL Query Examples

### Find High Emitters with Live Tracking
```sql
SELECT v.mmsi, v.name, v.imo, v.length, v.flag_state,
       e.total_co2_emissions, e.company_name
FROM vessels_static v
INNER JOIN eu_mrv_emissions e ON v.imo = e.imo
WHERE e.total_co2_emissions > 50000
ORDER BY e.total_co2_emissions DESC
```

### Company Fleet Emissions
```sql
SELECT e.company_name, 
       COUNT(*) as fleet_size,
       SUM(e.total_co2_emissions) as total_co2,
       AVG(e.total_co2_emissions) as avg_co2_per_vessel
FROM eu_mrv_emissions e
GROUP BY e.company_name
ORDER BY total_co2 DESC
LIMIT 20
```

### Emissions by Ship Type
```sql
SELECT e.ship_type,
       COUNT(*) as vessel_count,
       SUM(e.total_co2_emissions) as total_co2,
       AVG(e.total_co2_emissions) as avg_co2
FROM eu_mrv_emissions e
WHERE e.total_co2_emissions IS NOT NULL
GROUP BY e.ship_type
ORDER BY total_co2 DESC
```

### Most Efficient Vessels (CO2 per distance)
```sql
SELECT e.vessel_name, e.company_name, e.ship_type,
       e.avg_co2_per_distance, e.total_distance_travelled
FROM eu_mrv_emissions e
WHERE e.avg_co2_per_distance IS NOT NULL
ORDER BY e.avg_co2_per_distance ASC
LIMIT 20
```

### Vessels with Both AIS and High Emissions
```sql
SELECT v.mmsi, v.name, v.imo, v.ship_type, v.length,
       e.total_co2_emissions, e.company_name,
       e.total_distance_travelled
FROM vessels_static v
INNER JOIN eu_mrv_emissions e ON v.imo = e.imo
WHERE e.total_co2_emissions > 80000
ORDER BY e.total_co2_emissions DESC
```

## 🔧 Import Process

### Initial Import
```bash
python import_mrv_data.py
```

This script:
1. Reads the EU MRV Excel file
2. Creates the `eu_mrv_emissions` table
3. Imports 13,964 vessel records
4. Links data via IMO numbers
5. Shows statistics and matched vessels

### Re-import (Update Data)
Simply run the import script again with a new Excel file. It will:
- Update existing records
- Insert new records
- Preserve the database structure

## 📈 Top 10 CO2 Emitters

1. **CRUISE BARCELONA** (GRIMALDI EUROMED) - 124,615 tonnes
2. **CMA CGM BENJAMIN FRANKLIN** (CMA SHIPS SAS) - 116,098 tonnes
3. **CRUISE ROMA** (GRIMALDI EUROMED) - 109,712 tonnes
4. **MSC FANTASIA** (MSC Cruise Management) - 108,758 tonnes
5. **EBBA MAERSK** (Maersk A/S) - 107,510 tonnes
6. **VENTURA** (Carnival Plc) - 106,912 tonnes
7. **EVER ALP** (EVERGREEN MARINE) - 106,429 tonnes
8. **MSC WORLD EUROPA** (MSC Cruise Management) - 106,376 tonnes
9. **SUPERFAST XI** (SUPERFAST FERRIES) - 105,445 tonnes
10. **EVER ALOT** (EVERGREEN MARINE) - 104,762 tonnes

## 🎯 Use Cases

### 1. Environmental Impact Analysis
- Track CO2 emissions by company, ship type, or route
- Identify high-emitting vessels
- Monitor efficiency improvements over time

### 2. Fleet Management
- Compare company fleets by emissions
- Analyze fuel efficiency
- Benchmark against industry averages

### 3. Regulatory Compliance
- EU ETS (Emissions Trading System) reporting
- MRV compliance monitoring
- Carbon footprint tracking

### 4. Research & Analytics
- Correlate emissions with vessel characteristics
- Study efficiency by ship type and size
- Analyze transport work efficiency

### 5. Real-Time + Historical Hybrid
- Track live positions of high-emitting vessels
- Combine real-time tracking with historical emissions data
- Monitor vessels entering/leaving EU waters

## 🔗 Data Linking

Vessels are linked between the two databases using **IMO numbers**:

- **vessels_static** (AIS data): `imo` column
- **eu_mrv_emissions**: `imo` column (foreign key)

**1,220 vessels** have both:
- Live AIS tracking data (MMSI, position, speed, etc.)
- Historical emissions data (CO2, fuel, efficiency, etc.)

## 📦 Files

- `import_mrv_data.py` - Import script for EU MRV data
- `2024-v99-22102025-EU MRV Publication of information.xlsx` - Source data file
- `vessel_static_data.db` - SQLite database (now includes emissions table)
- `EMISSIONS_FEATURE.md` - This documentation

## 🚀 Deployment

### VPS Deployment Steps

1. **Upload Excel file to VPS:**
```bash
scp "2024-v99-22102025-EU MRV Publication of information.xlsx" user@vps:/var/www/apihub/
```

2. **SSH into VPS and import:**
```bash
ssh user@vps
cd /var/www/apihub
source venv/bin/activate
pip install pandas openpyxl
python import_mrv_data.py
```

3. **Pull latest code and restart:**
```bash
git pull origin master
pip install -r requirements.txt
sudo systemctl restart ais-web-tracker
```

4. **Test API endpoints:**
```bash
curl http://localhost:5000/ships/api/emissions/stats
```

## 🎉 What's Next?

Potential enhancements:
- Web UI for emissions data visualization
- Charts and graphs for emissions trends
- Filter vessels on map by emissions level
- Company comparison dashboard
- Efficiency rankings and leaderboards
- Export emissions reports
- Historical emissions tracking over multiple years

## 📚 Data Source

EU MRV (Monitoring, Reporting and Verification) system
- Official EU emissions monitoring for maritime transport
- Covers vessels >5000 GT calling at EU ports
- Annual reporting requirement
- Public dataset updated yearly

---

**This is a game-changer for maritime emissions tracking!** 🌊🌍
