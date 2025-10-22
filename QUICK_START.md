# Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Activate Environment
```powershell
.\hub\Scripts\activate
```

### 2. Run the Collector
```powershell
python ais_collector.py
```

### 3. Query Your Data
```powershell
python query_vessels.py
```

---

## 📊 What You'll See

When running `ais_collector.py`, you'll see:

```
Loading API key from api.txt...
API key loaded successfully.

Initializing database...
Database initialized: C:\Users\gerrit\Desktop\apihub\vessel_static_data.db
Database ready.

Connecting to AISStream...
Press Ctrl+C to stop.

WebSocket connection opened. Sending subscription message...
Subscription message sent.

--- Static Data Report Received ---
  MMSI: 123456789
  Name: EXAMPLE VESSEL
  Type: 70
  Length: 150m
  Beam: 25m
  IMO: 9876543
  Call Sign: ABCD
----------------------------------------
✓ Saved to DB: MMSI 123456789 - EXAMPLE VESSEL
```

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
├── query_vessels.py              # Interactive query tool
├── export_to_csv.py              # CSV export utility
├── api.txt                       # Your API key
├── vessel_static_data.db         # SQLite database (auto-created)
├── requirements.txt              # Python dependencies
├── ship_type_reference.txt       # Ship type codes
├── README.md                     # Full documentation
└── QUICK_START.md               # This file
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
