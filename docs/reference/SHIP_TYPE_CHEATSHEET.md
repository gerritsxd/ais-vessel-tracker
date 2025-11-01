# Ship Type Codes - Quick Reference Cheat Sheet

## 🚢 Common Ship Types

| Code | Name | Category |
|------|------|----------|
| 30 | Fishing | Fishing Vessel |
| 40 | Towing | Towing Vessel |
| 50 | Pilot Vessel | Service Vessel |
| 51 | Search and Rescue | Service Vessel |
| 52 | Tug | Service Vessel |
| 60 | Passenger | Passenger Ship |
| 70 | Cargo | Cargo Ship |
| 80 | Tanker | Tanker |
| 90 | Other Type | Other |

## 🔧 Service & Special Vessels (40-59)

| Code | Name |
|------|------|
| 40 | Towing |
| 41 | Towing (large) |
| 43 | Dredging or underwater ops |
| 44 | Diving ops |
| 45 | Military ops |
| 46 | Sailing |
| 47 | Pleasure Craft |
| 50 | Pilot Vessel |
| 51 | Search and Rescue |
| 52 | Tug |
| 53 | Port Tender |
| 54 | Anti-pollution equipment |
| 55 | Law Enforcement |
| 58 | Medical Transport |

## 🛳️ Passenger Ships (60-69)

| Code | Name |
|------|------|
| 60 | Passenger |
| 61 | Passenger, Hazardous category A |
| 62 | Passenger, Hazardous category B |
| 63 | Passenger, Hazardous category C |
| 64 | Passenger, Hazardous category D |
| 69 | Passenger, No additional info |

## 📦 Cargo Ships (70-79)

| Code | Name |
|------|------|
| 70 | Cargo |
| 71 | Cargo, Hazardous category A |
| 72 | Cargo, Hazardous category B |
| 73 | Cargo, Hazardous category C |
| 74 | Cargo, Hazardous category D |
| 79 | Cargo, No additional info |

## 🛢️ Tankers (80-89)

| Code | Name |
|------|------|
| 80 | Tanker |
| 81 | Tanker, Hazardous category A |
| 82 | Tanker, Hazardous category B |
| 83 | Tanker, Hazardous category C |
| 84 | Tanker, Hazardous category D |
| 89 | Tanker, No additional info |

## ✈️ Wing in Ground (WIG) (20-29)

| Code | Name |
|------|------|
| 20 | Wing in ground (WIG) |
| 21 | WIG, Hazardous category A |
| 22 | WIG, Hazardous category B |
| 23 | WIG, Hazardous category C |
| 24 | WIG, Hazardous category D |

## 🔄 Other Types (90-99)

| Code | Name |
|------|------|
| 90 | Other Type |
| 91 | Other Type, Hazardous category A |
| 92 | Other Type, Hazardous category B |
| 93 | Other Type, Hazardous category C |
| 94 | Other Type, Hazardous category D |
| 99 | Other Type, no additional info |

## 🎯 Hazardous Categories

- **Category A**: Major hazard (e.g., explosives, toxic gases)
- **Category B**: Significant hazard (e.g., flammable liquids)
- **Category C**: Moderate hazard (e.g., flammable solids)
- **Category D**: Minor hazard (e.g., combustible liquids)

## 💡 Usage in SQL Queries

The SQL query interface automatically converts codes to names:

```sql
-- Query by ship type code
SELECT mmsi, name, ship_type, length 
FROM vessels_static 
WHERE ship_type = 70;  -- Returns "Cargo"

-- Query by type range (all passenger ships)
SELECT mmsi, name, ship_type 
FROM vessels_static 
WHERE ship_type >= 60 AND ship_type < 70;

-- Query by type range (all tankers)
SELECT mmsi, name, ship_type 
FROM vessels_static 
WHERE ship_type >= 80 AND ship_type < 90;

-- Count vessels by type
SELECT ship_type, COUNT(*) as count
FROM vessels_static 
WHERE ship_type IS NOT NULL
GROUP BY ship_type 
ORDER BY count DESC;
```

## 📊 Quick Stats Query

```sql
SELECT 
    CASE 
        WHEN ship_type >= 60 AND ship_type < 70 THEN 'Passenger'
        WHEN ship_type >= 70 AND ship_type < 80 THEN 'Cargo'
        WHEN ship_type >= 80 AND ship_type < 90 THEN 'Tanker'
        WHEN ship_type >= 50 AND ship_type < 60 THEN 'Service'
        ELSE 'Other'
    END as category,
    COUNT(*) as count,
    AVG(length) as avg_length
FROM vessels_static 
WHERE ship_type IS NOT NULL
GROUP BY category
ORDER BY count DESC;
```

## 🔍 Filter Examples

```sql
-- Large passenger ships
SELECT * FROM vessels_static 
WHERE ship_type >= 60 AND ship_type < 70 
AND length >= 200;

-- Hazardous cargo carriers
SELECT * FROM vessels_static 
WHERE ship_type IN (71, 72, 73, 74);

-- All tankers
SELECT * FROM vessels_static 
WHERE ship_type >= 80 AND ship_type < 90;
```
