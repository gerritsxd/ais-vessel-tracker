# Wind Vessel MMSI Lookup Guide

## ✅ Changes Made:
1. **Wind turbine icon (🌬️)** now shows on wind-assisted vessels instead of sail
2. **MMSI-based matching** - Much more accurate than name matching!

## 🔍 How to Add Wind Vessels:

### Step 1: Look Up MMSI Numbers
Go to these websites and search for each vessel:
- **https://www.marinetraffic.com** (best)
- **https://www.vesselfinder.com**
- **https://www.shipfinder.com**

Search by vessel name, and you'll see the MMSI number (9-digit number).

### Step 2: Add to the Script
Edit `src/utils/import_wind_propulsion_mmsi.py` and add vessels to the `WIND_VESSELS_MMSI` list:

```python
WIND_VESSELS_MMSI = [
    ("Vessel Name", MMSI_NUMBER, "Type", DWT, GT, Length, "Technology", Year, "newbuild/retrofit"),
    
    # Examples:
    ("E-Ship 1", 211281610, "Ro-Ro", 10020, 12968, 130, "4 x 27m fixed rotor sails", 2010, "newbuild"),
    ("Pyxis Ocean", 636019825, "Bulk Carrier", 80962, 43291, 229, "2 x 40m retractable wing sails", 2023, "retrofit"),
    
    # Add your looked-up vessels here:
    ("Your Vessel", 123456789, "Bulk Carrier", 50000, 30000, 200, "2 x 30m rotor sails", 2024, "retrofit"),
]
```

### Step 3: Run on VPS
```bash
cd /var/www/apihub
git pull
source venv/bin/activate
python3 src/utils/import_wind_propulsion_mmsi.py
```

### Step 4: Check Matches
```bash
python3 check_wind_matches.py
```

This will show:
- ✅ How many vessels are matched
- 📋 List of matched vessels currently tracked
- ❌ List of vessels not yet in AIS (waiting to be tracked)

### Step 5: Restart Web Service
```bash
sudo systemctl restart ais-web-tracker
```

## 🎯 Priority Vessels to Look Up:

Start with the largest/most important ones:

### Large Bulk Carriers (easiest to find):
- **Sohar Max** (400,315 DWT) - 5 x 35m rotor sails
- **Berge Neblina** (388,000 DWT) - 4 x 35m hinged rotor sails
- **Sea Zhoushan** (324,268 DWT) - 5 x 24m hinged rotor sails
- **Grand Pioneer** (324,963 DWT) - 4 x 35m rotor sails
- **Berge Olympus** (211,153 DWT) - 4 x 40m retractable wing sails

### Well-Known Vessels:
- **E-Ship 1** (130m) - First commercial vessel with rotor sails (2010)
- **Pyxis Ocean** (229m) - Recent high-profile retrofit
- **Canopee** (121m) - Ariane rocket transporter

### Recent 2024-2025 Installations:
- **Chinook Oldendorff** (235m) - 3 x 24m rotor sails
- **Yodohime** (229m) - 1 x 24m rotor sail
- **Camellia Dream** (299m) - 2 x 35m rotor sails

## 📊 Example MMSI Lookup:

1. Go to https://www.marinetraffic.com
2. Search for "Pyxis Ocean"
3. Click on the vessel
4. You'll see: **MMSI: 636019825**
5. Add to script with that MMSI

## 🌬️ What You'll See on Map:

Once matched, vessels will show:
- **🌬️ icon** on top-right of marker
- **Green border** instead of white
- **"🌬️ Wind-Assisted Propulsion"** badge in popup

## 💡 Tips:

1. **Start with 5-10 vessels** - Don't try to do all 77 at once
2. **Focus on large vessels** - They're easier to find and more likely to be tracked
3. **Check spelling** - Vessel names on MarineTraffic might be slightly different
4. **Some vessels might not be found** - They might be too new or not yet in service
5. **Run the import script multiple times** - Add more MMSIs as you find them

## 🔄 Workflow:

```
Look up MMSI → Add to script → Run import → Check matches → Restart service → Check map
```

Repeat this process as you find more MMSI numbers!

## ❓ Troubleshooting:

**Q: Vessel not showing on map?**
- Check if it's in your AIS tracking area (Atlantic)
- Vessel might be in port or not transmitting
- Run `check_wind_matches.py` to see if it's matched

**Q: Can't find MMSI?**
- Try alternative spellings
- Search by IMO number instead
- Vessel might be too new or not yet in service

**Q: How do I know if it worked?**
- Run `check_wind_matches.py` on VPS
- Check the map for 🌬️ icons
- Look at service logs: `sudo journalctl -u ais-web-tracker -f`
