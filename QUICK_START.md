# Quick Start Guide

## Prerequisites
- Python 3.7+
- Virtual environment activated (`.\hub\Scripts\activate`)
- AISStream API key in `api.txt`

## Step 1: Collect Vessel Data

1. **Start the collector:**
   ```bash
   python ais_collector.py
   ```
   Or double-click: `run_collector.bat`

2. **You should see:**
   - "WebSocket connection opened"
   - "Subscription message sent"
   - Incoming vessel data being printed and saved with flag states
   - Example: `Saved to DB: MMSI 235010926 - AS GOOD AS IT GETS (United Kingdom)`

3. **Let it run:**
   - Recommended: Several hours or overnight
   - Auto-reconnects on connection loss
   - Builds comprehensive vessel database

4. **Stop the collector:**
   - Press `Ctrl+C`
   - Database will close gracefully

## Step 2: Track Specific Vessels (Optional)

After collecting data, track filtered vessels in real-time:

1. **Start the tracker:**
   ```bash
   python track_filtered_vessels.py
   ```

2. **You should see:**
   - List of vessels matching filter criteria
   - Number of tracking connections created
   - Real-time position updates as vessels move

3. **Filter criteria:**
   - Length >= 100 meters
   - Excludes container ships (type 71, 72)
   - Automatically batches MMSIs (max 50 per connection)

4. **Stop the tracker:**
   - Press `Ctrl+C`

---

## 🛠️ Common Tasks

### View Statistics
```powershell
python query_vessels.py
# Choose option 1
```

### Export to Excel/CSV
```powershell
python export_to_csv.py
```

### Search for a Specific Vessel
```powershell
python query_vessels.py
# Choose option 3 (search by MMSI) or 4 (search by name)
```

---

## 🔧 Troubleshooting

### API Key Error
- Check that `api.txt` contains your valid API key
- Get a new key from: https://aisstream.io/apikeys

### Database Locked
- Make sure only one instance of `ais_collector.py` is running
- Close any database browser tools

### No Data Received
- Check your internet connection
- Verify your API key is valid
- Wait a few minutes - data may be sparse depending on filters

---

## 📁 Project Structure

```
apihub/
├── hub/                          # Virtual environment
├── ais_collector.py              # Main data collector
├── track_filtered_vessels.py     # Real-time vessel tracker
├── mmsi_mid_lookup.py            # Flag state decoder
├── query_vessels.py              # Interactive query tool
├── export_to_csv.py              # CSV export utility
├── check_data.py                 # Data quality checker
├── check_big_ships.py            # List ships >100m
├── api.txt                       # Your API key
├── vessel_static_data.db         # SQLite database (auto-created)
├── requirements.txt              # Python dependencies
├── ship_type_reference.txt       # Ship type codes
├── README.md                     # Full documentation
├── QUICK_START.md                # This file
└── LONG_RUN_GUIDE.md             # Long-term operation guide
```

---

## 💡 Tips

1. **Run Continuously**: Leave `ais_collector.py` running to build a comprehensive database
2. **Geographical Filters**: Edit the script to add bounding boxes for specific regions
3. **Ship Types**: See `ship_type_reference.txt` for ship type code meanings
4. **Backup**: Periodically backup `vessel_static_data.db`

---

## 🆘 Need Help?

- Full documentation: See `README.md`
- Ship type codes: See `ship_type_reference.txt`
- AIS Stream docs: https://aisstream.io/documentation
