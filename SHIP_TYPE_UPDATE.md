# Ship Type Display Update

## Changes Made

### 1. Backend Changes (`web_tracker.py`)

Added ship type code-to-name mapping functionality:

- **Ship Type Dictionary**: Added `SHIP_TYPE_NAMES` dictionary with 50+ ship type codes mapped to human-readable names
- **Helper Function**: Created `get_ship_type_name()` function to convert codes to names
- **SQL Query Results**: Modified `/api/sql/query` endpoint to automatically replace ship_type codes with names
- **CSV Export**: Modified `/api/sql/export` endpoint to include ship type names in exported CSV files

### 2. Frontend Changes (`templates/sql_query.html`)

- Updated schema documentation to indicate that `ship_type` displays as name in results

## How It Works

When you query the database with a SQL query that includes the `ship_type` column:

**Before:**
```
mmsi        | name           | ship_type
235010926   | AS GOOD AS IT  | 60
477886300   | OOCL PIRAEUS   | 70
```

**After:**
```
mmsi        | name           | ship_type
235010926   | AS GOOD AS IT  | Passenger
477886300   | OOCL PIRAEUS   | Cargo
```

## Ship Type Mappings

The system now recognizes and displays names for:
- **20-29**: Wing in ground (WIG) vessels
- **30**: Fishing vessels
- **40-49**: Towing, dredging, diving, military, sailing, pleasure craft
- **50-59**: Pilot vessels, tugs, port tenders, law enforcement, medical transport
- **60-69**: Passenger vessels (with hazard categories)
- **70-79**: Cargo vessels (with hazard categories)
- **80-89**: Tanker vessels (with hazard categories)
- **90-99**: Other types (with hazard categories)

Unknown codes will display as "Type XX" where XX is the code number.

## Testing

To test the changes:

1. Start the web tracker:
   ```bash
   python web_tracker.py
   ```

2. Navigate to: `http://localhost:5000/ships/sql`

3. Run a test query:
   ```sql
   SELECT mmsi, name, ship_type, length 
   FROM vessels_static 
   WHERE ship_type IS NOT NULL 
   LIMIT 10
   ```

4. Verify that the `ship_type` column shows names like "Passenger", "Cargo", "Tanker" instead of numeric codes

## Backward Compatibility

- The database schema remains unchanged (still stores integer codes)
- Only the display/output is modified
- All existing queries will continue to work
- CSV exports now include readable ship type names
