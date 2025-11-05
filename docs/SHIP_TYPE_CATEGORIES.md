# Ship Type Categories

This document explains the ship type numbering system used in AIS (Automatic Identification System) and how it maps to the detailed ship types in the EU MRV emissions dataset.

## Overview

The system now filters and tracks **only Cargo (70-79) and Tanker (80-89) vessels** that are **>= 100 meters in length**.

### Why This Filter?
- **Cargo ships and tankers** are the primary vessels that transport goods internationally
- These vessels have significant CO₂ emissions and are key targets for emissions reduction
- The EU MRV (Monitoring, Reporting, Verification) dataset provides detailed ship type classifications for these vessels

## AIS Ship Type Codes (Category Numbers)

### Cargo Ships (70-79)
- **70**: Cargo
- **71**: Cargo, Hazardous category A
- **72**: Cargo, Hazardous category B
- **73**: Cargo, Hazardous category C
- **74**: Cargo, Hazardous category D
- **79**: Cargo, No additional info

### Tankers (80-89)
- **80**: Tanker
- **81**: Tanker, Hazardous category A
- **82**: Tanker, Hazardous category B
- **83**: Tanker, Hazardous category C
- **84**: Tanker, Hazardous category D
- **89**: Tanker, No additional info

## Detailed Ship Types from EU MRV Dataset

The EU MRV emissions dataset provides more granular ship type classifications that give specific information about what cargo type each vessel carries. These are stored in the `detailed_ship_type` field.

### Common Detailed Ship Types in EU MRV:

**Cargo Vessel Types:**
- **Bulk carrier** - Carries unpacked bulk cargo like grain, coal, ore
- **General cargo** - Carries packaged/mixed cargo
- **Ro-Ro cargo ship** - Roll-on/Roll-off cargo (vehicles, trailers)
- **Container ship** - Carries standardized shipping containers
- **Refrigerated cargo carrier** - Carries temperature-controlled goods

**Tanker Types:**
- **Chemical tanker** - Carries liquid chemicals
- **LNG carrier** - Carries liquefied natural gas
- **Oil tanker** - Carries crude oil or petroleum products
- **Crude oil tanker** - Specifically for crude oil

**Other Types:**
- **Other ship types** - Miscellaneous vessels not fitting above categories

## Data Linking

Ships are linked between AIS data and EU MRV emissions data using:
1. **IMO Number** (International Maritime Organization number) - Primary link
2. **MMSI** (Maritime Mobile Service Identity) - Secondary identifier

### Database Schema:

```sql
CREATE TABLE vessels_static (
    mmsi INTEGER PRIMARY KEY,
    name TEXT,
    ship_type INTEGER,              -- AIS type code (70-89 only)
    detailed_ship_type TEXT,        -- EU MRV detailed type
    length INTEGER,
    beam INTEGER,
    imo INTEGER,
    ...
)
```

## How It Works

1. **AIS Collector** filters incoming vessel data to only save cargo (70-79) and tankers (80-89) >= 100m
2. **Emissions Matcher** runs continuously to match vessels by IMO number with EU MRV data
3. When a match is found, the `detailed_ship_type` from EU MRV is populated in `vessels_static`
4. **API endpoints** return both the AIS type code and the detailed ship type

## API Endpoints

### Get All Vessels
```
GET /ships/api/database/vessels
```
Returns all vessels with both `ship_type` (AIS code) and `detailed_ship_type` (EU MRV)

### Get Ship Type Statistics
```
GET /ships/api/statistics/ship-types
```
Returns breakdown of:
- AIS type codes with counts
- Detailed ship types with counts
- Number of vessels missing detailed type

### Get Vessel Emissions
```
GET /ships/api/emissions/vessel/<imo>
```
Returns full emissions data for a specific vessel by IMO number

## Example Output

```json
{
  "mmsi": 244820000,
  "name": "EXAMPLE VESSEL",
  "ship_type": 70,
  "detailed_ship_type": "Bulk carrier",
  "length": 150,
  "imo": 9123456,
  "flag_state": "Netherlands",
  ...
}
```

## Emissions Data Integration

For vessels matched with EU MRV data, additional information includes:
- Total CO₂ emissions (tonnes)
- Ship company name
- Distance traveled
- CO₂ per nautical mile
- Technical efficiency rating
- Econowind fit score (for wind propulsion retrofit potential)

## Use Cases

1. **Filter by specific cargo type**: Use `detailed_ship_type` to find specific vessel categories
2. **Emissions analysis**: Match vessels with their CO₂ emissions data
3. **Fleet analysis**: Group vessels by company and detailed type
4. **Retrofit targeting**: Identify vessels with high emissions potential for retrofitting
