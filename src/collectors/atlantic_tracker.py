"""
Datalastic Atlantic Coverage Tracker

Scans strategic points across the Atlantic Ocean to track vessels
that are out of terrestrial AIS range. Integrates with existing database.

Free Tier: 20,000 credits/month
Strategy: Smart scanning of 5 Atlantic zones every 6 hours
"""

import requests
import sqlite3
import time
from datetime import datetime
from pathlib import Path
import json


# Configuration
API_KEY_FILE = "config/datalastic_api_key.txt"
DB_NAME = "data/vessel_static_data.db"
BASE_URL = "https://api.datalastic.com/api/v0"

# Atlantic scanning zones (latitude, longitude, radius in NM)
ATLANTIC_ZONES = [
    {"name": "Mid-Atlantic North", "lat": 45.0, "lon": -40.0, "radius": 50},
    {"name": "Mid-Atlantic Central", "lat": 35.0, "lon": -40.0, "radius": 50},
    {"name": "Mid-Atlantic South", "lat": 25.0, "lon": -40.0, "radius": 50},
    {"name": "Western Approach", "lat": 50.0, "lon": -20.0, "radius": 50},
    {"name": "Caribbean Approach", "lat": 20.0, "lon": -50.0, "radius": 50},
]

# Scan every 6 hours (4 times/day)
SCAN_INTERVAL = 6 * 3600  # 6 hours in seconds

# Statistics
stats = {
    'scans_completed': 0,
    'vessels_found': 0,
    'credits_used': 0,
    'last_scan': None,
    'errors': 0
}


def load_api_key():
    """Load Datalastic API key from config file."""
    project_root = Path(__file__).parent.parent.parent
    api_file_path = project_root / API_KEY_FILE
    
    try:
        with open(api_file_path, 'r') as f:
            key = f.read().strip()
            if not key:
                raise ValueError("API key file is empty")
            return key
    except FileNotFoundError:
        raise FileNotFoundError(f"API key file not found: {api_file_path}")


def get_db_connection():
    """Get database connection."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def scan_atlantic_zone(api_key, zone):
    """
    Scan a specific Atlantic zone for vessels.
    
    Returns: (vessels_found, credits_used)
    """
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning: {zone['name']}")
    print(f"   Location: {zone['lat']}°N, {zone['lon']}°W")
    print(f"   Radius: {zone['radius']} NM")
    
    try:
        # API Request
        url = f"{BASE_URL}/vessel_inradius"
        params = {
            'api-key': api_key,
            'lat': zone['lat'],
            'lon': zone['lon'],
            'radius': zone['radius'],
            'exclude': 'Fishing,Pleasure Craft,Pilot Vessel,Tug'  # Focus on cargo/tanker
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract vessel data
            vessels = data.get('data', [])
            meta = data.get('meta', {})
            credits_used = meta.get('total', len(vessels))
            
            print(f"   ✓ Found {len(vessels)} vessels (used {credits_used} credits)")
            
            # Save to database
            saved_count = save_vessels_to_db(vessels)
            print(f"   ✓ Saved/updated {saved_count} vessels")
            
            return len(vessels), credits_used
            
        elif response.status_code == 429:
            print(f"   ⚠️  Rate limit hit - waiting...")
            return 0, 0
        else:
            print(f"   ❌ Error {response.status_code}: {response.text}")
            return 0, 0
            
    except Exception as e:
        print(f"   ❌ Error scanning zone: {e}")
        return 0, 0


def save_vessels_to_db(vessels):
    """Save vessel data to database."""
    if not vessels:
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    saved_count = 0
    
    try:
        for vessel in vessels:
            mmsi = vessel.get('mmsi')
            if not mmsi:
                continue
            
            # Extract vessel data
            name = vessel.get('name', 'Unknown')
            imo = vessel.get('imo')
            ship_type = vessel.get('type')
            detailed_type = vessel.get('type_specific')
            length = vessel.get('length')
            beam = vessel.get('beam')
            call_sign = vessel.get('callsign')
            flag = vessel.get('country_iso')
            destination = vessel.get('destination')
            eta = vessel.get('eta')
            
            # Position data
            lat = vessel.get('lat')
            lon = vessel.get('lon')
            sog = vessel.get('speed')
            cog = vessel.get('course')
            timestamp = vessel.get('timestamp', datetime.utcnow().isoformat())
            
            # Update or insert vessel static data
            cursor.execute('''
                INSERT INTO vessels_static (
                    mmsi, name, imo, ship_type, detailed_ship_type,
                    length, beam, call_sign, flag_state, destination, eta, last_updated
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mmsi) DO UPDATE SET
                    name = COALESCE(excluded.name, vessels_static.name),
                    imo = COALESCE(excluded.imo, vessels_static.imo),
                    ship_type = COALESCE(excluded.ship_type, vessels_static.ship_type),
                    detailed_ship_type = COALESCE(excluded.detailed_ship_type, vessels_static.detailed_ship_type),
                    length = COALESCE(excluded.length, vessels_static.length),
                    beam = COALESCE(excluded.beam, vessels_static.beam),
                    call_sign = COALESCE(excluded.call_sign, vessels_static.call_sign),
                    flag_state = COALESCE(excluded.flag_state, vessels_static.flag_state),
                    destination = excluded.destination,
                    eta = excluded.eta,
                    last_updated = excluded.last_updated
            ''', (
                mmsi, name, imo, ship_type, detailed_type,
                length, beam, call_sign, flag, destination, eta, timestamp
            ))
            
            # Save position history
            if lat and lon:
                cursor.execute('''
                    INSERT INTO vessel_positions (mmsi, latitude, longitude, sog, cog, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (mmsi, lat, lon, sog, cog, timestamp))
            
            saved_count += 1
        
        conn.commit()
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    return saved_count


def save_stats():
    """Save statistics to JSON file."""
    project_root = Path(__file__).parent.parent.parent
    stats_file = project_root / "data" / "atlantic_tracker_stats.json"
    
    try:
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save stats: {e}")


def run_atlantic_scan():
    """Run a complete Atlantic scan cycle."""
    print("\n" + "="*80)
    print("🌊  ATLANTIC COVERAGE SCAN")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scanning {len(ATLANTIC_ZONES)} zones...")
    
    # Load API key
    try:
        api_key = load_api_key()
    except Exception as e:
        print(f"❌ Failed to load API key: {e}")
        stats['errors'] += 1
        return
    
    # Scan each zone
    total_vessels = 0
    total_credits = 0
    
    for zone in ATLANTIC_ZONES:
        vessels, credits = scan_atlantic_zone(api_key, zone)
        total_vessels += vessels
        total_credits += credits
        
        # Rate limiting: Wait 1 second between zones
        time.sleep(1)
    
    # Update statistics
    stats['scans_completed'] += 1
    stats['vessels_found'] += total_vessels
    stats['credits_used'] += total_credits
    stats['last_scan'] = datetime.now().isoformat()
    
    # Calculate efficiency
    credits_remaining = 20000 - stats['credits_used']
    scans_per_month = 4 * 30  # 4 scans/day * 30 days
    credits_per_scan = stats['credits_used'] / stats['scans_completed'] if stats['scans_completed'] > 0 else 0
    estimated_monthly = credits_per_scan * scans_per_month
    
    print("\n" + "-"*80)
    print(f"✓ Scan complete!")
    print(f"  Vessels found: {total_vessels}")
    print(f"  Credits used: {total_credits}")
    print(f"  Total credits this month: {stats['credits_used']}")
    print(f"  Credits remaining: {credits_remaining}")
    print(f"  Avg credits/scan: {credits_per_scan:.1f}")
    print(f"  Estimated monthly usage: {estimated_monthly:.0f} / 20,000")
    print("-"*80)
    
    # Save statistics
    save_stats()


def main():
    """Main service loop."""
    print("\n" + "="*80)
    print("🌊  DATALASTIC ATLANTIC TRACKER SERVICE")
    print("="*80)
    print(f"Free Tier: 20,000 credits/month")
    print(f"Scan interval: Every {SCAN_INTERVAL/3600:.0f} hours")
    print(f"Zones: {len(ATLANTIC_ZONES)} coverage areas")
    print(f"Strategy: {len(ATLANTIC_ZONES)} zones × 4 scans/day = ~20 scans/day")
    print("="*80)
    print()
    
    # Load previous stats if available
    project_root = Path(__file__).parent.parent.parent
    stats_file = project_root / "data" / "atlantic_tracker_stats.json"
    
    try:
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                loaded_stats = json.load(f)
                stats.update(loaded_stats)
            print(f"📊 Loaded previous stats:")
            print(f"   Scans completed: {stats['scans_completed']}")
            print(f"   Credits used: {stats['credits_used']}")
            if stats['last_scan']:
                print(f"   Last scan: {stats['last_scan']}")
            print()
    except Exception as e:
        print(f"⚠️  Could not load previous stats: {e}\n")
    
    while True:
        try:
            # Run scan
            run_atlantic_scan()
            
            # Wait for next scan
            print(f"\n⏰ Next scan in {SCAN_INTERVAL/3600:.0f} hours...")
            print(f"   {datetime.fromtimestamp(time.time() + SCAN_INTERVAL).strftime('%Y-%m-%d %H:%M:%S')}")
            
            time.sleep(SCAN_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Service stopped by user")
            print(f"Total scans: {stats['scans_completed']}")
            print(f"Total credits used: {stats['credits_used']}")
            save_stats()
            break
            
        except Exception as e:
            print(f"\n❌ Service error: {e}")
            stats['errors'] += 1
            print(f"Waiting 5 minutes before retry...")
            time.sleep(300)


if __name__ == "__main__":
    main()
