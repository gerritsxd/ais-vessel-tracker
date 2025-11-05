# Deployment Instructions - Wind Propulsion Feature

## What's New
✅ **Wind Propulsion Tracking System** - 77 vessels with wind-assisted technology are now flagged on the map!

## Features Added:
1. **Database table** for 77 wind-assisted vessels (rotor sails, wing sails, suction wings, kites)
2. **Visual indicators** on map:
   - ⛵ Sail icon on wind-assisted vessels
   - Green border instead of white
   - "Wind-Assisted Propulsion" badge in popup
3. **Import script** to load and match vessels by name
4. **API updates** to include wind_assisted flag

## Deployment Steps

### 1. Pull Latest Code
```bash
cd /var/www/apihub
git pull
```

### 2. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 3. Run Wind Propulsion Import
```bash
python3 src/utils/import_wind_propulsion.py
```

Expected output:
```
================================================================================
WIND PROPULSION TECHNOLOGY IMPORT
================================================================================

✓ Wind propulsion table created
✓ Added wind_assisted column to vessels_static

================================================================================
WIND PROPULSION DATA IMPORT COMPLETE
================================================================================
✓ Inserted: 77 new vessels
✓ Updated: 0 existing vessels
✓ Total wind-assisted vessels: 77
================================================================================

Matching wind-assisted vessels to AIS database...
  ✓ Matched: E-Ship 1
  ✓ Matched: Estraden
  ... (more matches)

  Total AIS vessels flagged as wind-assisted: XX

================================================================================
WIND PROPULSION STATISTICS
================================================================================
Total wind-assisted vessels in database: 77

By installation type:
  newbuild: 35
  retrofit: 42

By installation year:
  2010: 1
  2014: 1
  2018: 4
  2020: 2
  2021: 5
  2022: 6
  2023: 5
  2024: 29
  2025: 24

Vessels matched with AIS data: XX
================================================================================
```

### 4. Restart Web Service
```bash
sudo systemctl restart ais-web-tracker
```

### 5. Verify
Visit https://gerritsxd.com/ships and look for:
- Vessels with ⛵ icon
- Green borders on wind-assisted vessels
- "Wind-Assisted Propulsion" badge in popups

## Notable Wind-Assisted Vessels to Look For:

### Large Bulk Carriers:
- **Sohar Max** - 400,315 DWT (5 x 35m rotor sails)
- **Berge Neblina** - 388,000 DWT (4 x 35m hinged rotor sails)
- **Sea Zhoushan** - 324,268 DWT (5 x 24m hinged rotor sails)

### Pioneers:
- **E-Ship 1** (2010) - First with 4 x 27m fixed rotor sails
- **Estraden** (2014) - Early adopter with 2 x 18m rotor sails

### Recent Installations:
- **Neoliner Origin** (2025) - Massive 2 x 76m solid sails
- **Brands Hatch** (2025) - 3 x 20m x 37.5m wing sails

## Database Queries

### Check Wind Vessels
```bash
sqlite3 vessel_static_data.db "SELECT COUNT(*) FROM wind_propulsion;"
# Should return: 77

sqlite3 vessel_static_data.db "SELECT COUNT(*) FROM vessels_static WHERE wind_assisted = 1;"
# Shows how many are currently tracked in AIS
```

### List Wind Vessels by Technology
```bash
sqlite3 vessel_static_data.db "SELECT technology_installed, COUNT(*) FROM wind_propulsion GROUP BY technology_installed;"
```

### Find Wind Vessels on Map
```bash
sqlite3 vessel_static_data.db "SELECT name, length, ship_type FROM vessels_static WHERE wind_assisted = 1 ORDER BY length DESC LIMIT 10;"
```

## Troubleshooting

### If vessels don't show wind indicator:
1. Check if import script ran successfully
2. Verify `wind_assisted` column exists:
   ```bash
   sqlite3 vessel_static_data.db "PRAGMA table_info(vessels_static);"
   ```
3. Check if vessels are matched:
   ```bash
   sqlite3 vessel_static_data.db "SELECT name FROM vessels_static WHERE wind_assisted = 1;"
   ```
4. Restart web service

### If import fails:
- Make sure database exists
- Check file permissions
- Verify virtual environment is activated

## Next Steps

Optional enhancements:
1. Add filter toggle to show only wind-assisted vessels
2. Create wind propulsion statistics dashboard
3. Link to Econowind fit score
4. Add technology details in sidebar
5. Track fuel savings estimates

## Files Modified:
- `src/utils/import_wind_propulsion.py` - Import script (NEW)
- `src/services/web_tracker.py` - API updates
- `templates/map.html` - Visual indicators
- `docs/WIND_PROPULSION.md` - Documentation (NEW)

## Support
If you encounter issues, check:
- Service logs: `sudo journalctl -u ais-web-tracker -f`
- Database: `sqlite3 vessel_static_data.db`
- Import output for errors
