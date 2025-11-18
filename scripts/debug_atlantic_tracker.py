"""
Debug Atlantic Tracker - Check all components
"""

import sys
import io
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("="*80)
print("ATLANTIC TRACKER DEBUG REPORT")
print("="*80)

# 1. Check API key
print("\n[1] API KEY CHECK")
print("-"*80)
api_key_file = project_root / "config" / "datalastic_api_key.txt"
if api_key_file.exists():
    with open(api_key_file, 'r') as f:
        key = f.read().strip()
    print(f"✓ API key file exists")
    print(f"  Key: {key[:10]}...{key[-10:]}")
else:
    print(f"✗ API key file NOT FOUND: {api_key_file}")

# 2. Check stats file
print("\n[2] STATS FILE CHECK")
print("-"*80)
stats_file = project_root / "data" / "atlantic_tracker_stats.json"
if stats_file.exists():
    import json
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    print(f"✓ Stats file exists")
    print(f"  Scans completed: {stats.get('scans_completed', 0)}")
    print(f"  Vessels found: {stats.get('vessels_found', 0)}")
    print(f"  Credits used: {stats.get('credits_used', 0)}")
    print(f"  Last scan: {stats.get('last_scan', 'Never')}")
    print(f"  Errors: {stats.get('errors', 0)}")
else:
    print(f"✗ Stats file NOT FOUND: {stats_file}")
    print("  (This is normal if no scans have completed yet)")

# 3. Check database for recent Atlantic vessels
print("\n[3] DATABASE CHECK - Recent Vessels (Last 24h)")
print("-"*80)
db_path = project_root / "data" / "vessel_static_data.db"

if not db_path.exists():
    print(f"✗ Database NOT FOUND: {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check total vessels
    cursor.execute("SELECT COUNT(*) FROM vessels_static")
    total = cursor.fetchone()[0]
    print(f"Total vessels in database: {total:,}")
    
    # Check vessels with positions in last 24 hours
    cursor.execute("""
        SELECT COUNT(DISTINCT mmsi) 
        FROM vessel_positions 
        WHERE timestamp >= datetime('now', '-24 hours')
    """)
    recent = cursor.fetchone()[0]
    print(f"Vessels with positions (last 24h): {recent:,}")
    
    # Check vessels in Atlantic zones (rough coordinates)
    # Mid-Atlantic: -50 to -30 longitude, 20 to 50 latitude
    cursor.execute("""
        SELECT COUNT(DISTINCT p.mmsi)
        FROM vessel_positions p
        WHERE p.timestamp >= datetime('now', '-24 hours')
          AND p.longitude BETWEEN -50 AND -30
          AND p.latitude BETWEEN 20 AND 50
    """)
    atlantic = cursor.fetchone()[0]
    print(f"Vessels in Atlantic region (last 24h): {atlantic:,}")
    
    # Show sample Atlantic vessels
    if atlantic > 0:
        print("\n  Sample Atlantic vessels:")
        cursor.execute("""
            SELECT v.mmsi, v.name, p.latitude, p.longitude, p.timestamp
            FROM vessel_positions p
            JOIN vessels_static v ON p.mmsi = v.mmsi
            WHERE p.timestamp >= datetime('now', '-24 hours')
              AND p.longitude BETWEEN -50 AND -30
              AND p.latitude BETWEEN 20 AND 50
            ORDER BY p.timestamp DESC
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            mmsi, name, lat, lon, ts = row
            print(f"    {mmsi} - {name}")
            print(f"      Position: {lat:.4f}°N, {lon:.4f}°W")
            print(f"      Time: {ts}")
    
    # Check most recent positions overall
    print("\n  Most recent positions (any location):")
    cursor.execute("""
        SELECT v.mmsi, v.name, p.latitude, p.longitude, p.timestamp
        FROM vessel_positions p
        JOIN vessels_static v ON p.mmsi = v.mmsi
        ORDER BY p.timestamp DESC
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        mmsi, name, lat, lon, ts = row
        print(f"    {mmsi} - {name}")
        print(f"      Position: {lat:.4f}°, {lon:.4f}°")
        print(f"      Time: {ts}")
    
    conn.close()

# 4. Test API connection
print("\n[4] API CONNECTION TEST")
print("-"*80)
try:
    from src.collectors.atlantic_tracker import load_api_key, ATLANTIC_ZONES
    
    api_key = load_api_key()
    print(f"✓ API key loaded: {api_key[:10]}...{api_key[-10:]}")
    print(f"✓ Zones configured: {len(ATLANTIC_ZONES)}")
    for zone in ATLANTIC_ZONES:
        print(f"  - {zone['name']}: {zone['lat']}°N, {zone['lon']}°W (radius: {zone['radius']} NM)")
    
except Exception as e:
    print(f"✗ Error loading Atlantic tracker: {e}")

# 5. Test live API call
print("\n[5] LIVE API TEST (Testing one zone)")
print("-"*80)
try:
    import requests
    from src.collectors.atlantic_tracker import load_api_key, ATLANTIC_ZONES, BASE_URL
    
    api_key = load_api_key()
    zone = ATLANTIC_ZONES[0]  # Test first zone
    
    print(f"Testing: {zone['name']}")
    
    url = f"{BASE_URL}/vessel_inradius"
    params = {
        'api-key': api_key,
        'lat': zone['lat'],
        'lon': zone['lon'],
        'radius': zone['radius']
    }
    
    print(f"Making request to Datalastic API...")
    response = requests.get(url, params=params, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        vessels = data.get('data', [])
        meta = data.get('meta', {})
        
        print(f"✓ API Response: SUCCESS")
        print(f"  Vessels found: {len(vessels)}")
        print(f"  Credits used: {meta.get('total', len(vessels))}")
        
        if vessels:
            print(f"\n  Sample vessels:")
            for v in vessels[:3]:
                print(f"    {v.get('mmsi')} - {v.get('name', 'Unknown')}")
                print(f"      {v.get('lat'):.4f}°N, {v.get('lon'):.4f}°W")
                print(f"      Type: {v.get('type_specific', 'Unknown')}")
        else:
            print("  ⚠️  No vessels found in this zone")
            
    else:
        print(f"✗ API Response: ERROR {response.status_code}")
        print(f"  {response.text}")
        
except Exception as e:
    print(f"✗ API Test failed: {e}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("""
Next steps:
1. If API test works but no vessels in database -> Check Atlantic tracker service logs
2. If vessels in database but not on map -> Check browser console for errors
3. If API test fails -> Check API key or network connectivity

To check service logs on VPS:
  tail -f logs/atlantic_tracker.log

To check if service is running:
  sudo systemctl status ais-atlantic-tracker
""")
