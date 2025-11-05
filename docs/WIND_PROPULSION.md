# Wind Propulsion Technology Tracking

This document explains the wind-assisted propulsion tracking feature.

## Overview

The system tracks **77 vessels** with wind propulsion technology installed (rotor sails, wing sails, suction wings, kites, and traditional sails). These vessels are flagged on the map with a special indicator to highlight Econowind's target market.

## Wind Propulsion Technologies

### Technology Types:
- **Rotor Sails** (Flettner rotors) - Rotating cylinders that use the Magnus effect
- **Wing Sails** - Rigid or retractable wing-like structures
- **Suction Wings** - Boundary layer suction technology
- **Kites** - Dynamic kite systems
- **Traditional Sails** - Mast-based soft sails

### Installation Types:
- **Newbuild** - Installed during ship construction
- **Retrofit** - Added to existing vessels

## Database Schema

### Wind Propulsion Table
```sql
CREATE TABLE wind_propulsion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_name TEXT NOT NULL,
    vessel_type TEXT,
    dwt INTEGER,                    -- Deadweight tonnage
    gt INTEGER,                     -- Gross tonnage
    length INTEGER,
    technology_installed TEXT,
    installation_year INTEGER,
    installation_type TEXT,         -- 'newbuild' or 'retrofit'
    last_updated TEXT NOT NULL,
    UNIQUE(vessel_name, installation_year)
);
```

### Vessels Static Table (Updated)
```sql
ALTER TABLE vessels_static ADD COLUMN wind_assisted INTEGER DEFAULT 0;
```

## Import Process

### 1. Run the Import Script
```bash
cd /var/www/apihub
source venv/bin/activate
python3 src/utils/import_wind_propulsion.py
```

This will:
1. Create the `wind_propulsion` table
2. Add `wind_assisted` column to `vessels_static`
3. Import 77 wind-assisted vessels
4. Match vessels by name to AIS database
5. Flag matched vessels with `wind_assisted = 1`

### 2. Matching Logic
The script matches wind vessels to AIS data using:
- **Exact name match** (case-insensitive)
- **Partial name match** (for vessels with slight variations)

## Map Visualization

### Visual Indicators:
- **⛵ Sail Icon** - Displayed on top-right of vessel marker
- **Green Border** - Wind-assisted vessels have a bright green border instead of white
- **Popup Badge** - Shows "⛵ Wind-Assisted Propulsion" in green

### Example:
```
Regular vessel:  ●  (colored dot with white border)
Wind-assisted:   ●⛵ (colored dot with green border + sail icon)
```

## API Endpoints

### Get All Vessels (includes wind_assisted flag)
```
GET /ships/api/vessels
```

Response includes:
```json
{
  "mmsi": 244820000,
  "name": "E-Ship 1",
  "wind_assisted": 1,
  ...
}
```

### Get Wind Propulsion Statistics
```sql
-- Count wind-assisted vessels in AIS
SELECT COUNT(*) FROM vessels_static WHERE wind_assisted = 1;

-- List all wind vessels
SELECT * FROM wind_propulsion ORDER BY installation_year DESC;

-- Wind vessels by technology
SELECT technology_installed, COUNT(*) 
FROM wind_propulsion 
GROUP BY technology_installed;
```

## Notable Vessels

### Largest Wind-Assisted Vessels:
1. **Sohar Max** - 400,315 DWT Bulk Carrier (5 x 35m rotor sails)
2. **Berge Neblina** - 388,000 DWT Bulk Carrier (4 x 35m hinged rotor sails)
3. **Sea Zhoushan** - 324,268 DWT Bulk Carrier (5 x 24m hinged rotor sails)
4. **Grand Pioneer** - 324,963 DWT Bulk Carrier (4 x 35m rotor sails)

### Earliest Installations:
1. **E-Ship 1** (2010) - 4 x 27m fixed rotor sails
2. **Estraden** (2014) - 2 x 18m fixed rotor sails

### Latest Installations (2025):
- Multiple chemical tankers with rotor sails
- General cargo vessels with suction wings
- **Neoliner Origin** - 2 x 76m solid sails (largest sails)

## Filtering

### Show Only Wind-Assisted Vessels:
```javascript
// Frontend filter (to be implemented)
const windVessels = allVessels.filter(v => v.wind_assisted === 1);
```

### Database Query:
```sql
SELECT v.*, w.technology_installed, w.installation_year
FROM vessels_static v
INNER JOIN wind_propulsion w ON UPPER(TRIM(v.name)) = UPPER(TRIM(w.vessel_name))
WHERE v.wind_assisted = 1;
```

## Use Cases

1. **Market Analysis** - Identify vessels with existing wind propulsion
2. **Competitor Tracking** - Monitor other wind propulsion installations
3. **Technology Trends** - Analyze which technologies are most popular
4. **Retrofit Opportunities** - Compare wind-assisted vs non-assisted vessels

## Maintenance

### Adding New Vessels:
1. Update `WIND_VESSELS` list in `import_wind_propulsion.py`
2. Run import script again
3. Script will automatically match new vessels to AIS data

### Updating Technology Info:
```sql
UPDATE wind_propulsion
SET technology_installed = 'new technology description'
WHERE vessel_name = 'Vessel Name';
```

## Statistics (as of 2025)

- **Total wind-assisted vessels**: 77
- **Newbuilds**: ~35
- **Retrofits**: ~42
- **Installation years**: 2010-2025
- **Peak year**: 2024 (29 vessels)
- **Most common technology**: Rotor sails and suction wings

## Future Enhancements

1. Add filter toggle for wind-assisted vessels only
2. Show technology details in vessel sidebar
3. Add wind propulsion statistics dashboard
4. Track fuel savings and emissions reductions
5. Link to Econowind fit score for retrofit candidates
