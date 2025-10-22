# Long-Term Data Collection Guide

## 🚀 Quick Start

**Double-click:** `run_collector.bat`

Or manually:
```cmd
cd c:\Users\gerrit\Desktop\apihub
hub\Scripts\python.exe ais_collector.py
```

## ✅ What's Been Made Bulletproof

### 1. **Auto-Reconnect**
- Automatically reconnects if connection drops
- Exponential backoff (5s → 10s → 20s → 60s max)
- Infinite retry loop

### 2. **Database Resilience**
- Connection stays open across reconnects
- Retry logic for database locks (3 attempts)
- Connection health checks before saving
- Commits after every save

### 3. **Error Handling**
- Catches all exceptions without crashing
- Continues on individual message errors
- Logs errors but keeps running

### 4. **Progress Monitoring**
- Stats printed every 1000 messages
- Shows:
  - Messages processed
  - Total vessels in database
  - Vessels with dimensions
  - Uptime

### 5. **Clean Reconnection**
- Reduced error spam
- Database stays open
- Seamless resume after disconnect

## 📊 Monitoring Your Collection

### Check Statistics
```cmd
hub\Scripts\python.exe check_data.py
```

### Check Big Ships (>100m)
```cmd
hub\Scripts\python.exe check_big_ships.py
```

### Query Database
```cmd
hub\Scripts\python.exe query_vessels.py
```

### Export to CSV
```cmd
hub\Scripts\python.exe export_to_csv.py
```

## 🎯 What You're Collecting

### Message Types:
- **StaticDataReport (Type 24)** - Class B vessels (yachts, small boats)
  - Name, sometimes dimensions
  - No IMO numbers
  
- **ShipStaticData (Type 5)** - Class A vessels (commercial ships)
  - Name, dimensions, ship type
  - **IMO numbers** ✅
  - Call signs

### Coverage Area:
- **English Channel / North Sea**
- Coordinates: 50°N to 52°N, 5°W to 2°E
- One of the busiest shipping lanes in the world

## 💡 Tips for Long Runs

### 1. **Leave it Running Overnight**
- You'll collect hundreds/thousands of vessels
- More complete data as ships broadcast both Part A and Part B

### 2. **Check Progress Periodically**
- Stats print every 1000 messages
- Run `check_data.py` to see totals

### 3. **Database is Safe**
- SQLite handles concurrent reads
- You can query while collector is running
- Auto-commits prevent data loss

### 4. **Expected Data Rates**
- ~10-50 messages per second (busy times)
- ~100-500 vessels per hour
- ~2,000-10,000 vessels per day

### 5. **Disk Space**
- Database grows slowly (~1-5 MB per 1000 vessels)
- Safe to run for days/weeks

## 🛑 Stopping the Collector

**Press Ctrl+C** in the terminal window

The script will:
1. Catch the interrupt
2. Commit final database transactions
3. Close database cleanly
4. Exit gracefully

## 🔧 Troubleshooting

### Connection Keeps Dropping?
- **Normal!** The script auto-reconnects
- Network issues are handled automatically
- Data collection continues seamlessly

### Database Locked Error?
- Script retries automatically (3 attempts)
- Rare, usually resolves itself

### No Data Coming In?
- Check internet connection
- Verify API key is valid at https://aisstream.io/apikeys
- Try restarting the script

### Want More Coverage?
Edit `ais_collector.py` and change the BoundingBoxes to cover different areas:
- Mediterranean: `[[30.0, -6.0], [45.0, 36.0]]`
- US East Coast: `[[25.0, -80.0], [45.0, -65.0]]`
- Global (warning: LOTS of data): Remove BoundingBoxes entirely

## 📈 Expected Results

### After 1 Hour:
- 100-500 vessels
- 10-50 with dimensions
- 5-20 large ships (>100m)

### After 24 Hours:
- 2,000-10,000 vessels
- 500-2,000 with dimensions
- 100-500 large ships (>100m)

### After 1 Week:
- 10,000-50,000 vessels
- 3,000-10,000 with dimensions
- 500-2,000 large ships (>100m)

## 🎉 You're All Set!

The collector is now **production-ready** for long-term unattended operation.

**Just run it and let it collect!** 🚢📊
