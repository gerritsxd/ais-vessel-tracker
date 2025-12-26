"""
Real-time Web-Based Vessel Tracker with Map Visualization
Displays tracked vessels on an interactive map with live updates.
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import websocket
import json
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime
import requests  # For proxying to PC ML service
import sys
import os

# Optional sentiment (used for website profile summaries shown in Intelligence UI)
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except Exception:
    TextBlob = None
    TEXTBLOB_AVAILABLE = False

# Add project root to path for imports
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

# Configuration
DB_NAME = "vessel_static_data.db"

# Cache for match-stats (refresh every 5 minutes)
_match_stats_cache = None
_match_stats_cache_time = 0
_match_stats_cache_ttl = 300  # 5 minutes


def ensure_econowind_column(conn):
    """Ensure the econowind_fit_score column exists before running queries."""
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(eu_mrv_emissions)")
        columns = {row[1] for row in cursor.fetchall()}
        if "econowind_fit_score" not in columns:
            cursor.execute(
                "ALTER TABLE eu_mrv_emissions ADD COLUMN econowind_fit_score INTEGER DEFAULT 0"
            )
            conn.commit()
    except sqlite3.OperationalError:
        # Table may not exist yet (e.g., before MRV import). Ignore so API can fail gracefully.
        pass


def ensure_technical_fit_score_column(conn):
    """Ensure the technical_fit_score column exists in vessels_static table."""
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(vessels_static)")
        columns = {row[1] for row in cursor.fetchall()}
        if "technical_fit_score" not in columns:
            cursor.execute(
                "ALTER TABLE vessels_static ADD COLUMN technical_fit_score REAL DEFAULT NULL"
            )
            conn.commit()
    except sqlite3.OperationalError:
        # Table may not exist yet. Ignore so API can fail gracefully.
        pass


API_KEY_FILE = "config/aisstream_keys"
WEBSOCKET_URL = "wss://stream.aisstream.io/v0/stream"
MAX_MMSI_PER_CONNECTION = 50

# Flask app
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import sys

# Get project root directory (two levels up from this file)
project_root = Path(__file__).parent.parent.parent
template_dir = project_root / 'templates'
static_dir = project_root / 'static'
frontend_dist = project_root / 'frontend' / 'dist'

app = Flask(__name__, 
            template_folder=str(template_dir),
            static_folder=str(static_dir))
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['SECRET_KEY'] = 'ais-tracker-secret'
# Configure Socket.IO to work with /ships/ path prefix
socketio = SocketIO(app, cors_allowed_origins="*", path="/ships/socket.io")

# Global state
API_KEY = None
vessel_positions = {}  # {mmsi: {lat, lon, sog, cog, timestamp, name, ...}}
vessel_static_data = {}  # {mmsi: {name, length, type, flag, ...}}
tracking_active = False


# Ship type mapping
SHIP_TYPE_NAMES = {
    20: "Wing in ground (WIG)",
    21: "WIG, Hazardous category A",
    22: "WIG, Hazardous category B",
    23: "WIG, Hazardous category C",
    24: "WIG, Hazardous category D",
    30: "Fishing",
    40: "Towing",
    41: "Towing (large)",
    42: "Towing (large)",
    43: "Dredging or underwater ops",
    44: "Diving ops",
    45: "Military ops",
    46: "Sailing",
    47: "Pleasure Craft",
    50: "Pilot Vessel",
    51: "Search and Rescue",
    52: "Tug",
    53: "Port Tender",
    54: "Anti-pollution equipment",
    55: "Law Enforcement",
    56: "Spare - Local Vessel",
    57: "Spare - Local Vessel",
    58: "Medical Transport",
    59: "Noncombatant ship",
    60: "Passenger",
    61: "Passenger, Hazardous category A",
    62: "Passenger, Hazardous category B",
    63: "Passenger, Hazardous category C",
    64: "Passenger, Hazardous category D",
    69: "Passenger, No additional info",
    70: "Cargo",
    71: "Cargo, Hazardous category A",
    72: "Cargo, Hazardous category B",
    73: "Cargo, Hazardous category C",
    74: "Cargo, Hazardous category D",
    79: "Cargo, No additional info",
    80: "Tanker",
    81: "Tanker, Hazardous category A",
    82: "Tanker, Hazardous category B",
    83: "Tanker, Hazardous category C",
    84: "Tanker, Hazardous category D",
    89: "Tanker, No additional info",
    90: "Other Type",
    91: "Other Type, Hazardous category A",
    92: "Other Type, Hazardous category B",
    93: "Other Type, Hazardous category C",
    94: "Other Type, Hazardous category D",
    99: "Other Type, no additional info"
}


def get_ship_type_name(ship_type_code):
    """Convert ship type code to human-readable name."""
    if ship_type_code is None:
        return None
    try:
        code = int(ship_type_code)
        return SHIP_TYPE_NAMES.get(code, f"Type {code}")
    except (ValueError, TypeError):
        return str(ship_type_code)


def load_api_keys():
    """Load all API keys from api.txt file."""
    try:
        project_root = Path(__file__).parent.parent.parent
        api_file_path = project_root / API_KEY_FILE
        
        api_keys = []
        with open(api_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    api_keys.append(line)
        
        if not api_keys:
            raise ValueError("No API keys found in api.txt")
        
        print(f"Loaded {len(api_keys)} API key(s)")
        return api_keys
    except Exception as e:
        raise Exception(f"Error loading API keys: {e}")


def get_filtered_vessels():
    """Get vessels from database matching filter criteria."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        # Try query with gross_tonnage first
        # Note: e.ship_type contains the EU MRV detailed type (e.g., "Bulk carrier", "Container ship")
        try:
            query = '''
                SELECT v.mmsi, v.name, v.ship_type, e.ship_type as detailed_ship_type, v.length, v.beam, v.imo, 
                       v.call_sign, v.flag_state, v.signatory_company, v.wind_assisted, e.gross_tonnage
                FROM vessels_static v
                LEFT JOIN eu_mrv_emissions e ON v.imo = e.imo
                WHERE v.mmsi IS NOT NULL
                  AND v.last_updated >= datetime('now', '-30 days')
                ORDER BY v.last_updated DESC
                LIMIT 2000
            '''
            cursor.execute(query)
            vessels = cursor.fetchall()
            has_gross_tonnage = True
        except sqlite3.OperationalError:
            # Fallback query without gross_tonnage if column doesn't exist
            print("Warning: gross_tonnage column not found, using fallback query")
            query = '''
                SELECT v.mmsi, v.name, v.ship_type, NULL as detailed_ship_type, v.length, v.beam, v.imo, 
                       v.call_sign, v.flag_state, v.signatory_company, v.wind_assisted
                FROM vessels_static v
                WHERE v.mmsi IS NOT NULL
                  AND v.last_updated >= datetime('now', '-30 days')
                ORDER BY v.last_updated DESC
                LIMIT 2000
            '''
            cursor.execute(query)
            vessels = cursor.fetchall()
            has_gross_tonnage = False
    finally:
        if conn:
            conn.close()
    
    # Store static data
    for vessel in vessels:
        if has_gross_tonnage:
            mmsi, name, ship_type, detailed_ship_type, length, beam, imo, call_sign, flag_state, signatory_company, wind_assisted, gross_tonnage = vessel
        else:
            mmsi, name, ship_type, detailed_ship_type, length, beam, imo, call_sign, flag_state, signatory_company, wind_assisted = vessel
            gross_tonnage = None
            
        vessel_static_data[mmsi] = {
            'name': name or 'Unknown',
            'ship_type': ship_type,
            'detailed_ship_type': detailed_ship_type,  # From CO2 emissions dataset
            'length': length,
            'beam': beam,
            'imo': imo,
            'call_sign': call_sign,
            'flag_state': flag_state or 'Unknown',
            'signatory_company': signatory_company,
            'wind_assisted': wind_assisted or 0,  # Wind propulsion flag
            'gross_tonnage': gross_tonnage  # From EU MRV emissions
        }
    
    return [vessel[0] for vessel in vessels]


class VesselTrackerWebSocket:
    """Handles WebSocket connection for tracking vessels."""
    
    def __init__(self, batch_id, mmsi_batch, api_key):
        self.batch_id = batch_id
        self.mmsi_batch = mmsi_batch
        self.api_key = api_key
        self.ws_app = None
        self.thread = None
        self.running = False
        
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            if "error" in data or "Error" in data:
                print(f"[Batch {self.batch_id}] ERROR: {data}")
                return
            
            msg_type = data.get("MessageType")
            
            if msg_type == "PositionReport":
                metadata = data.get("MetaData", {})
                position_data = data.get("Message", {}).get("PositionReport", {})
                
                mmsi = metadata.get("MMSI")
                lat = metadata.get("latitude")
                lon = metadata.get("longitude")
                sog = position_data.get("Sog", 0)
                cog = position_data.get("Cog", 0)
                timestamp = metadata.get("time_utc", datetime.utcnow().isoformat())
                
                if mmsi and lat and lon:
                    # Update vessel position
                    vessel_positions[mmsi] = {
                        'lat': lat,
                        'lon': lon,
                        'sog': sog,
                        'cog': cog,
                        'timestamp': timestamp,
                        'name': vessel_static_data.get(mmsi, {}).get('name', 'Unknown'),
                        'length': vessel_static_data.get(mmsi, {}).get('length'),
                        'flag_state': vessel_static_data.get(mmsi, {}).get('flag_state', 'Unknown')
                    }
                    
                    # Save position to history database
                    conn = None
                    try:
                        project_root = Path(__file__).parent.parent.parent
                        db_path = project_root / DB_NAME
                        conn = sqlite3.connect(db_path, timeout=5)
                        conn.execute('PRAGMA journal_mode=WAL')
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO vessel_positions (mmsi, latitude, longitude, sog, cog, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (mmsi, lat, lon, sog, cog, timestamp))
                        conn.commit()
                    except Exception as e:
                        print(f"[Position DB] Error saving: {e}")
                    finally:
                        if conn:
                            conn.close()
                    
                    # Emit to all connected web clients
                    socketio.emit('vessel_update', {
                        'mmsi': mmsi,
                        'position': vessel_positions[mmsi]
                    })
                    
                    print(f"[Position] {mmsi} - {vessel_positions[mmsi]['name']}: {lat:.4f}, {lon:.4f}")
                
        except Exception as e:
            print(f"[Batch {self.batch_id}] Error: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors."""
        error_str = str(error)
        if "Connection to remote host was lost" not in error_str:
            print(f"[Batch {self.batch_id}] Error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        print(f"[Batch {self.batch_id}] Connection closed")
    
    def on_open(self, ws):
        """Handle WebSocket open and send subscription."""
        print(f"[Batch {self.batch_id}] Connected - Tracking {len(self.mmsi_batch)} vessels")
        
        mmsi_strings = [str(mmsi) for mmsi in self.mmsi_batch]
        
        subscribe_message = {
            "APIKey": self.api_key,
            "FiltersShipMMSI": mmsi_strings,
            "BoundingBoxes": [[[90, -180], [-90, 180]]]
        }
        
        ws.send(json.dumps(subscribe_message))
        print(f"[Batch {self.batch_id}] Subscription sent")
    
    def start(self):
        """Start the WebSocket connection."""
        self.running = True
        self.thread = threading.Thread(target=self._run_forever, daemon=True)
        self.thread.start()
    
    def _run_forever(self):
        """Run WebSocket with auto-reconnect."""
        while self.running:
            try:
                self.ws_app = websocket.WebSocketApp(
                    WEBSOCKET_URL,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                )
                self.ws_app.run_forever()
                
                if self.running:
                    time.sleep(5)
                    
            except Exception as e:
                print(f"[Batch {self.batch_id}] Exception: {e}")
                time.sleep(5)


# Flask routes - Serving React frontend
@app.route('/ships/')
def serve_index():
    """Serve the React frontend entry point."""
    return send_from_directory(str(frontend_dist), 'index.html')

@app.route('/ships/<path:path>')
def serve_frontend(path):
    """Serve static files or React frontend for SPA routing."""
    # Allow API routes to pass through (handled by other routes or return 404)
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
        
    # Try to serve static file if it exists in dist
    if (frontend_dist / path).exists():
        return send_from_directory(str(frontend_dist), path)
        
    # Otherwise serve index.html for client-side routing
    return send_from_directory(str(frontend_dist), 'index.html')


@app.route('/ships/api/vessels')
def get_vessels():
    """Get all tracked vessels including Atlantic (database) vessels with recent positions."""
    vessels = []
    seen_mmsi = set()
    
    # First: Add real-time AIS vessels (in-memory)
    for mmsi, static in vessel_static_data.items():
        vessel_info = {
            'mmsi': mmsi,
            'name': static['name'],
            'length': static['length'],
            'flag_state': static['flag_state'],
            'ship_type': static['ship_type'],
            'detailed_ship_type': static.get('detailed_ship_type'),
            'wind_assisted': static.get('wind_assisted', 0),
            'gross_tonnage': static.get('gross_tonnage')
        }
        
        # Add position if available
        if mmsi in vessel_positions:
            vessel_info.update(vessel_positions[mmsi])
        
        vessels.append(vessel_info)
        seen_mmsi.add(mmsi)
    
    # Second: Add recent database vessels (Atlantic, etc.) with last known positions
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=60)
        conn.execute('PRAGMA journal_mode=WAL')
        ensure_technical_fit_score_column(conn)
        cursor = conn.cursor()
        
        # FAST approach: Get latest positions first (simple indexed query)
        # Then join with vessel info - avoids complex nested queries
        cursor.execute('''
            SELECT p.mmsi, p.latitude, p.longitude, p.sog, p.cog, MAX(p.timestamp) as timestamp
            FROM vessel_positions p
            WHERE p.timestamp >= datetime('now', '-6 hours')
            GROUP BY p.mmsi
            ORDER BY timestamp DESC
            LIMIT 3000
        ''')
        recent_positions = {row[0]: {'lat': row[1], 'lon': row[2], 'sog': row[3], 'cog': row[4], 'timestamp': row[5]} 
                          for row in cursor.fetchall()}
        
        if not recent_positions:
            return jsonify(vessels)
        
        # Get vessel info for those MMSIs (fast lookup by primary key)
        mmsi_list = ','.join(map(str, recent_positions.keys()))
        cursor.execute(f'''
            SELECT v.mmsi, v.name, v.ship_type, e.ship_type as detailed_ship_type, v.length, v.beam,
                   v.imo, v.call_sign, v.flag_state, v.wind_assisted, e.gross_tonnage,
                   v.technical_fit_score
            FROM vessels_static v
            LEFT JOIN eu_mrv_emissions e ON v.imo = e.imo
            WHERE v.mmsi IN ({mmsi_list})
        ''')
        
        db_vessels = cursor.fetchall()
        
        for vessel in db_vessels:
            mmsi, name, ship_type, detailed_type, length, beam, imo, call_sign, flag, wind_assisted, gt, technical_fit_score = vessel
            
            # Skip if already in real-time data
            if mmsi in seen_mmsi:
                continue
                
            pos = recent_positions.get(mmsi, {})
            if not pos:
                continue
            
            vessels.append({
                'mmsi': mmsi,
                'name': name or 'Unknown',
                'ship_type': ship_type,
                'detailed_ship_type': detailed_type,
                'length': length,
                'beam': beam,
                'imo': imo,
                'call_sign': call_sign,
                'flag_state': flag or 'Unknown',
                'wind_assisted': wind_assisted or 0,
                'gross_tonnage': gt,
                'technical_fit_score': technical_fit_score,
                'lat': pos.get('lat'),
                'lon': pos.get('lon'),
                'sog': pos.get('sog'),
                'cog': pos.get('cog'),
                'timestamp': pos.get('timestamp')
            })
            
    except Exception as e:
        print(f"Error loading database vessels: {e}")
    finally:
        if conn:
            conn.close()
    
    return jsonify(vessels)


@app.route('/ships/api/stats')
def get_stats():
    """Get tracking statistics."""
    return jsonify({
        'total_vessels': len(vessel_static_data),
        'vessels_with_position': len(vessel_positions),
        'tracking_active': tracking_active
    })


# @app.route('/ships/database')
# def database_viewer():
#     """Serve the enhanced database viewer page with emissions data."""
#     return render_template('database_enhanced.html')

# @app.route('/ships/database')
# def serve_react_database():
#    """Serve the React frontend for database route."""
#    return send_from_directory(str(frontend_dist), 'index.html')


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers using Haversine formula."""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2), radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def filter_route_outliers(positions, max_speed_knots=60, max_jump_km=500, max_time_gap_hours=2):
    """
    Remove outlier positions and mark segment breaks from route based on realistic ship movement.
    
    Args:
        positions: List of position dicts with lat, lon, timestamp
        max_speed_knots: Maximum realistic speed (default 60 knots for fast vessels)
        max_jump_km: Maximum distance jump allowed (default 500km)
        max_time_gap_hours: Maximum time gap before breaking segment (default 2 hours)
    
    Returns:
        Filtered list of positions with 'segment_break' flag added
    """
    if len(positions) <= 1:
        return positions
    
    filtered = [positions[0]]  # Always keep first position
    
    for i in range(1, len(positions)):
        current = positions[i].copy()  # Create a copy to add segment_break flag
        previous = filtered[-1]  # Compare to last valid position
        
        try:
            # Calculate distance between points
            distance_km = haversine_distance(
                previous['lat'], previous['lon'],
                current['lat'], current['lon']
            )
            
            # Parse timestamps
            from datetime import datetime
            t1 = datetime.fromisoformat(previous['timestamp'].replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(current['timestamp'].replace('Z', '+00:00'))
            time_diff_hours = abs((t2 - t1).total_seconds()) / 3600
            
            # Avoid division by zero
            if time_diff_hours < 0.001:  # Less than ~3 seconds
                # Points are too close in time, skip duplicate
                continue
            
            # Check for large time gap (tracking stopped and resumed)
            if time_diff_hours > max_time_gap_hours:
                print(f"[Route Filter] Time gap detected: {time_diff_hours:.1f} hours between points")
                current['segment_break'] = True  # Mark as start of new segment
                filtered.append(current)
                continue  # Don't check speed for time gaps
            
            # Calculate implied speed
            implied_speed_kmh = distance_km / time_diff_hours
            implied_speed_knots = implied_speed_kmh / 1.852  # Convert to knots
            
            # Check for outliers
            is_outlier = False
            
            # Check 1: Unrealistic speed
            if implied_speed_knots > max_speed_knots:
                print(f"[Route Filter] Outlier detected: {implied_speed_knots:.1f} knots (max: {max_speed_knots})")
                is_outlier = True
            
            # Check 2: Sudden huge jump
            if distance_km > max_jump_km:
                print(f"[Route Filter] Outlier detected: {distance_km:.1f} km jump (max: {max_jump_km})")
                is_outlier = True
            
            # Keep the point if it's not an outlier
            if not is_outlier:
                filtered.append(current)
            
        except Exception as e:
            print(f"[Route Filter] Error processing point: {e}")
            # On error, keep the point to avoid data loss
            filtered.append(current)
    
    removed_count = len(positions) - len(filtered)
    segment_breaks = sum(1 for p in filtered if p.get('segment_break', False))
    
    if removed_count > 0:
        print(f"[Route Filter] Removed {removed_count} outlier points from {len(positions)} total")
    if segment_breaks > 0:
        print(f"[Route Filter] Found {segment_breaks} segment breaks (time gaps > {max_time_gap_hours}h)")
    
    return filtered


@app.route('/ships/api/vessel/<int:mmsi>/route')
def get_vessel_route(mmsi):
    """Get position history for a specific vessel with outlier filtering."""
    hours = request.args.get('hours', default=24, type=int)
    
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT latitude, longitude, sog, cog, timestamp
            FROM vessel_positions
            WHERE mmsi = ?
              AND timestamp >= datetime('now', '-' || ? || ' hours')
            ORDER BY timestamp ASC
        ''', (mmsi, hours))
        
        positions = cursor.fetchall()
        
        # Build raw route
        route = []
        for p in positions:
            route.append({
                'lat': p[0],
                'lon': p[1],
                'sog': p[2],
                'cog': p[3],
                'timestamp': p[4]
            })
        
        # Apply intelligent outlier filtering
        filtered_route = filter_route_outliers(route)
        
        return jsonify(filtered_route)
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/database/vessels')
def get_all_vessels():
    """Get all vessels from database with filtering."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        # Get filter parameters
        min_length = request.args.get('min_length', type=int)
        max_length = request.args.get('max_length', type=int)
        ship_type = request.args.get('ship_type', type=int)
        flag_state = request.args.get('flag_state', type=str)
        search = request.args.get('search', type=str)
        
        # Build query
        query = 'SELECT mmsi, name, ship_type, detailed_ship_type, length, beam, imo, call_sign, flag_state, destination, eta, draught, last_updated, signatory_company FROM vessels_static WHERE 1=1'
        params = []
        
        if min_length:
            query += ' AND length >= ?'
            params.append(min_length)
        
        if max_length:
            query += ' AND length <= ?'
            params.append(max_length)
        
        if ship_type:
            query += ' AND ship_type >= ? AND ship_type < ?'
            params.append(ship_type)
            params.append(ship_type + 10)
        
        if flag_state:
            query += ' AND flag_state = ?'
            params.append(flag_state)
        
        if search:
            query += ' AND (name LIKE ? OR CAST(mmsi AS TEXT) LIKE ? OR signatory_company LIKE ?)'
            search_param = f'%{search}%'
            params.append(search_param)
            params.append(search_param)
            params.append(search_param)
        
        query += ' ORDER BY last_updated DESC LIMIT 1000'
        
        cursor.execute(query, params)
        vessels = cursor.fetchall()
        
        # Format results
        results = []
        for v in vessels:
            results.append({
                'mmsi': v[0],
                'name': v[1],
                'ship_type': v[2],
                'detailed_ship_type': v[3],
                'length': v[4],
                'beam': v[5],
                'imo': v[6],
                'call_sign': v[7],
                'flag_state': v[8],
                'destination': v[9],
                'eta': v[10],
                'draught': v[11],
                'last_updated': v[12],
                'signatory_company': v[13]
            })
        
        return jsonify(results)
    except Exception as e:
        print(f"Error in get_all_vessels: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/companies')
def get_companies():
    """Get company statistics."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        # Get company statistics
        cursor.execute('''
            SELECT signatory_company, COUNT(*) as vessel_count, 
                   AVG(length) as avg_length, MAX(length) as max_length
            FROM vessels_static
            WHERE signatory_company IS NOT NULL AND signatory_company != ''
            GROUP BY signatory_company
            ORDER BY vessel_count DESC
            LIMIT 50
        ''')
        
        companies = cursor.fetchall()
        results = []
        for c in companies:
            results.append({
                'company': c[0],
                'vessel_count': c[1],
                'avg_length': round(c[2], 1) if c[2] else 0,
                'max_length': c[3]
            })
        
        return jsonify(results)
    except Exception as e:
        print(f"Error in get_companies: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/sql')
def sql_query_page():
    """Render SQL query interface."""
    return render_template('sql_query.html')


@app.route('/ships/api/sql/query', methods=['POST'])
def execute_sql_query():
    """Execute a raw SQL query (READ-ONLY)."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Security: Only allow SELECT queries
        if not query.upper().startswith('SELECT'):
            return jsonify({'error': 'Only SELECT queries are allowed'}), 403
        
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / DB_NAME
        
        conn = None
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(db_path, timeout=30)
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.cursor()
            
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            
            # Convert ship_type codes to names if ship_type column exists
            ship_type_idx = None
            if 'ship_type' in columns:
                ship_type_idx = columns.index('ship_type')
            
            # Process rows to replace ship_type codes with names
            processed_rows = []
            for row in rows:
                row_list = list(row)
                if ship_type_idx is not None and row_list[ship_type_idx] is not None:
                    row_list[ship_type_idx] = get_ship_type_name(row_list[ship_type_idx])
                processed_rows.append(row_list)
            
            execution_time = int((time.time() - start_time) * 1000)  # ms
            
            return jsonify({
                'columns': columns,
                'rows': processed_rows,
                'row_count': len(processed_rows),
                'execution_time': execution_time
            })
            
        except sqlite3.Error as e:
            return jsonify({'error': f'SQL Error: {str(e)}'}), 400
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ships/api/sql/export', methods=['POST'])
def export_sql_query():
    """Export SQL query results to CSV."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Security: Only allow SELECT queries
        if not query.upper().startswith('SELECT'):
            return jsonify({'error': 'Only SELECT queries are allowed'}), 403
        
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / DB_NAME
        
        conn = None
        try:
            conn = sqlite3.connect(db_path, timeout=30)
            conn.execute('PRAGMA journal_mode=WAL')
            cursor = conn.cursor()
            
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            
            # Convert ship_type codes to names if ship_type column exists
            ship_type_idx = None
            if 'ship_type' in columns:
                ship_type_idx = columns.index('ship_type')
            
            # Process rows to replace ship_type codes with names
            processed_rows = []
            for row in rows:
                row_list = list(row)
                if ship_type_idx is not None and row_list[ship_type_idx] is not None:
                    row_list[ship_type_idx] = get_ship_type_name(row_list[ship_type_idx])
                processed_rows.append(row_list)
            
            # Generate CSV
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            writer.writerows(processed_rows)
            
            # Return as downloadable file
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=query_results.csv'}
            )
            
        except sqlite3.Error as e:
            return jsonify({'error': f'SQL Error: {str(e)}'}), 400
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('Client connected')
    emit('initial_data', {
        'vessels': list(vessel_static_data.keys()),
        'positions': vessel_positions
    })


def start_tracking():
    """Start tracking vessels via WebSocket."""
    global tracking_active, API_KEY
    
    try:
        print("Loading vessels from database...")
        mmsi_list = get_filtered_vessels()
        print(f"Loaded {len(mmsi_list)} vessels for tracking")
        
        print("Loading API keys...")
        try:
            api_keys = load_api_keys()
        except Exception as e:
            print(f"WARNING: Could not load API keys: {e}")
            print("Real-time tracking will be DISABLED. Showing database positions only.")
            return

        # Create batches
        batches = []
        for i in range(0, len(mmsi_list), MAX_MMSI_PER_CONNECTION):
            batches.append(mmsi_list[i:i + MAX_MMSI_PER_CONNECTION])
        
        # Limit to 3 connections per API key
        max_connections = len(api_keys) * 3
        if len(batches) > max_connections:
            print(f"WARNING: {len(batches)} batches requested, but only {max_connections} connections available")
            print(f"Limiting to first {max_connections} batches ({max_connections * MAX_MMSI_PER_CONNECTION} vessels)")
            batches = batches[:max_connections]
        
        print(f"Creating {len(batches)} tracking connections across {len(api_keys)} API key(s)...")
        
        # Start trackers - rotate API keys (3 connections per key)
        for i, batch in enumerate(batches, 1):
            api_key_index = (i - 1) // 3  # Use each API key for 3 connections
            api_key = api_keys[api_key_index % len(api_keys)]
            print(f"Batch {i}: Using API key #{api_key_index + 1}")
            tracker = VesselTrackerWebSocket(i, batch, api_key)
            tracker.start()
            time.sleep(1)
        
        tracking_active = True
        print(f"Tracking {sum(len(b) for b in batches)} vessels across {len(batches)} connections")
        
    except Exception as e:
        print(f"Error starting tracking: {e}")


@app.route('/ships/api/emissions/vessel/<int:imo>')
def get_vessel_emissions(imo):
    """Get emissions data for a specific vessel by IMO."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        ensure_econowind_column(conn)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.*, v.mmsi, v.name as ais_name, v.length, v.flag_state
            FROM eu_mrv_emissions e
            LEFT JOIN vessels_static v ON e.imo = v.imo
            WHERE e.imo = ?
        ''', (imo,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Vessel not found'}), 404
        
        columns = [description[0] for description in cursor.description]
        result = dict(zip(columns, row))
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/emissions/vessel/<int:imo>/score-breakdown')
def get_score_breakdown(imo):
    """Get detailed breakdown of Econowind fit score for a vessel."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        ensure_econowind_column(conn)
        cursor = conn.cursor()
        
        # Get vessel data
        cursor.execute('''
            SELECT e.imo, e.vessel_name, e.ship_type, e.avg_co2_per_distance, 
                   e.technical_efficiency, e.econowind_fit_score, e.total_co2_emissions,
                   v.length
            FROM eu_mrv_emissions e
            LEFT JOIN vessels_static v ON e.imo = v.imo
            WHERE e.imo = ?
        ''', (imo,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Vessel not found'}), 404
        
        imo, vessel_name, ship_type, avg_co2, tech_eff, total_score, total_co2, length = row
        
        # Calculate score breakdown
        breakdown = {
            'vessel_name': vessel_name,
            'imo': imo,
            'total_score': total_score or 0,
            'max_score': 8,
            'breakdown': []
        }
        
        # 1. Ship type scoring
        preferred_types = {
            "Bulk carrier", "General cargo", "Chemical tanker",
            "LNG carrier", "Other ship types", "Ro-Ro cargo ship"
        }
        ship_type_score = 2 if ship_type in preferred_types else 0
        breakdown['breakdown'].append({
            'category': 'Ship Type',
            'score': ship_type_score,
            'max': 2,
            'value': ship_type,
            'explanation': f"{'✓ Preferred type' if ship_type_score == 2 else '✗ Not a preferred type'} ({ship_type})",
            'details': 'Preferred: Bulk carrier, General cargo, Chemical tanker, LNG carrier, Ro-Ro cargo, Other'
        })
        
        # 2. Length scoring
        length_score = 0
        length_explanation = 'No length data available'
        if length:
            if 100 <= length <= 160:
                length_score = 2
                length_explanation = f'✓ Optimal size ({length}m is in 100-160m range)'
            elif 80 <= length < 100 or 160 < length <= 200:
                length_score = 1
                length_explanation = f'~ Acceptable size ({length}m is in 80-100m or 160-200m range)'
            else:
                length_explanation = f'✗ Outside preferred range ({length}m)'
        
        breakdown['breakdown'].append({
            'category': 'Vessel Length',
            'score': length_score,
            'max': 2,
            'value': f'{length}m' if length else 'N/A',
            'explanation': length_explanation,
            'details': 'Optimal: 100-160m (+2), Acceptable: 80-100m or 160-200m (+1)'
        })
        
        # 3. CO2 emissions intensity
        co2_score = 0
        co2_explanation = 'No CO₂/distance data available'
        if avg_co2:
            # Get quantiles
            cursor.execute('SELECT avg_co2_per_distance FROM eu_mrv_emissions WHERE avg_co2_per_distance IS NOT NULL')
            co2_values = [r[0] for r in cursor.fetchall()]
            if co2_values:
                import numpy as np
                co2_75 = np.percentile(co2_values, 75)
                co2_50 = np.percentile(co2_values, 50)
                
                if avg_co2 >= co2_75:
                    co2_score = 2
                    co2_explanation = f'✓ High emitter ({avg_co2:.1f} kg/nm, top 25%)'
                elif avg_co2 >= co2_50:
                    co2_score = 1
                    co2_explanation = f'~ Above average ({avg_co2:.1f} kg/nm, above median)'
                else:
                    co2_explanation = f'✗ Below average ({avg_co2:.1f} kg/nm, already efficient)'
        
        breakdown['breakdown'].append({
            'category': 'CO₂ Emissions Intensity',
            'score': co2_score,
            'max': 2,
            'value': f'{avg_co2:.1f} kg/nm' if avg_co2 else 'N/A',
            'explanation': co2_explanation,
            'details': 'Top 25% emitters (+2), Above median (+1) - Higher emissions = more savings potential'
        })
        
        # 4. Technical efficiency
        eff_score = 0
        eff_explanation = 'No technical efficiency data'
        if tech_eff:
            try:
                eff_value = float(str(tech_eff).split('(')[-1].strip(')').split()[0])
                if eff_value > 10:
                    eff_score = 2
                    eff_explanation = f'✓ Poor efficiency ({eff_value:.1f} gCO₂/t·nm)'
                elif eff_value >= 6:
                    eff_score = 1
                    eff_explanation = f'~ Moderate efficiency ({eff_value:.1f} gCO₂/t·nm)'
                else:
                    eff_explanation = f'✗ Good efficiency ({eff_value:.1f} gCO₂/t·nm)'
            except:
                eff_explanation = f'Could not parse: {tech_eff}'
        
        breakdown['breakdown'].append({
            'category': 'Technical Efficiency',
            'score': eff_score,
            'max': 2,
            'value': tech_eff or 'N/A',
            'explanation': eff_explanation,
            'details': 'Poor efficiency >10 (+2), Moderate 6-10 (+1) - Lower efficiency = more improvement potential'
        })
        
        # Summary
        calculated_total = sum(item['score'] for item in breakdown['breakdown'])
        breakdown['calculated_total'] = calculated_total
        breakdown['total_co2_emissions'] = total_co2
        
        # Recommendation
        if calculated_total >= 6:
            breakdown['recommendation'] = 'Excellent candidate for wind propulsion retrofit'
            breakdown['recommendation_class'] = 'high'
        elif calculated_total >= 4:
            breakdown['recommendation'] = 'Good candidate for wind propulsion retrofit'
            breakdown['recommendation_class'] = 'medium'
        elif calculated_total >= 2:
            breakdown['recommendation'] = 'Potential candidate, further analysis recommended'
            breakdown['recommendation_class'] = 'low'
        else:
            breakdown['recommendation'] = 'Low priority for wind propulsion retrofit'
            breakdown['recommendation_class'] = 'na'
        
        return jsonify(breakdown)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/emissions/top')
def get_top_emitters():
    """Get top CO2 emitters."""
    limit = request.args.get('limit', 50, type=int)
    ship_type = request.args.get('ship_type', type=str)
    
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        ensure_econowind_column(conn)
        cursor = conn.cursor()
        
        query = '''
            SELECT e.imo, e.vessel_name, e.ship_type, e.company_name,
                   e.total_co2_emissions, e.total_distance_travelled,
                   e.avg_co2_per_distance, e.econowind_fit_score,
                   v.mmsi, v.length, v.flag_state
            FROM eu_mrv_emissions e
            LEFT JOIN vessels_static v ON e.imo = v.imo
            WHERE e.total_co2_emissions IS NOT NULL
        '''
        
        params = []
        if ship_type:
            query += ' AND e.ship_type = ?'
            params.append(ship_type)
        
        query += ' ORDER BY e.total_co2_emissions DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/emissions/company/<company_name>')
def get_company_emissions(company_name):
    """Get emissions data for all vessels of a specific company."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        ensure_econowind_column(conn)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.imo, e.vessel_name, e.ship_type, e.total_co2_emissions,
                   e.total_distance_travelled, e.avg_co2_per_distance,
                   e.econowind_fit_score, v.mmsi, v.length, v.flag_state
            FROM eu_mrv_emissions e
            LEFT JOIN vessels_static v ON e.imo = v.imo
            WHERE e.company_name LIKE ?
            ORDER BY e.total_co2_emissions DESC
        ''', (f'%{company_name}%',))
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        
        # Calculate company totals
        total_co2 = sum(r['total_co2_emissions'] for r in results if r['total_co2_emissions'])
        total_vessels = len(results)
        
        return jsonify({
            'company': company_name,
            'total_vessels': total_vessels,
            'total_co2_emissions': total_co2,
            'average_co2_per_vessel': total_co2 / total_vessels if total_vessels > 0 else 0,
            'vessels': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/emissions/stats')
def get_emissions_stats():
    """Get overall emissions statistics."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        ensure_econowind_column(conn)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_vessels,
                SUM(total_co2_emissions) as total_co2,
                AVG(total_co2_emissions) as avg_co2,
                MAX(total_co2_emissions) as max_co2,
                COUNT(DISTINCT company_name) as total_companies
            FROM eu_mrv_emissions
            WHERE total_co2_emissions IS NOT NULL
        ''')
        
        overall = cursor.fetchone()
        
        # By ship type
        cursor.execute('''
            SELECT ship_type, COUNT(*) as count, SUM(total_co2_emissions) as total_co2
            FROM eu_mrv_emissions
            WHERE total_co2_emissions IS NOT NULL AND ship_type IS NOT NULL
            GROUP BY ship_type
            ORDER BY total_co2 DESC
            LIMIT 10
        ''')
        
        by_type = cursor.fetchall()
        
        # Vessels with AIS data
        cursor.execute('''
            SELECT COUNT(*) 
            FROM eu_mrv_emissions e
            INNER JOIN vessels_static v ON e.imo = v.imo
        ''')
        
        matched = cursor.fetchone()[0]
        
        return jsonify({
            'total_vessels': overall[0],
            'total_co2_emissions': overall[1],
            'average_co2_per_vessel': overall[2],
            'max_co2_emission': overall[3],
            'total_companies': overall[4],
            'vessels_with_ais_data': matched,
            'by_ship_type': [{'ship_type': row[0], 'count': row[1], 'total_co2': row[2]} for row in by_type]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


# Simple in-memory cache for vessel data (5 minute TTL)
_vessel_cache = {}
_vessel_cache_time = {}

@app.route('/ships/api/vessels/combined')
def get_combined_vessel_data():
    """Get vessels with both AIS and emissions data."""
    import time
    
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    min_co2 = request.args.get('min_co2', type=float)
    
    # Create cache key
    cache_key = f"{limit}_{offset}_{min_co2}"
    current_time = time.time()
    
    # Check cache (5 minute TTL)
    if cache_key in _vessel_cache:
        cache_time = _vessel_cache_time.get(cache_key, 0)
        if current_time - cache_time < 300:  # 5 minutes
            response = jsonify(_vessel_cache[cache_key])
            response.headers['X-Cache'] = 'HIT'
            response.headers['Cache-Control'] = 'public, max-age=300'
            return response
    
    project_root = Path(__file__).parent.parent.parent
    # Try data/ subdirectory first, then root
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    
    conn = None
    try:
        if not db_path.exists():
            return jsonify({'error': f'Database not found: {db_path}'}), 500
        
        conn = sqlite3.connect(str(db_path), timeout=30)
        ensure_econowind_column(conn)
        ensure_technical_fit_score_column(conn)
        cursor = conn.cursor()
        
        # Ensure indexes exist for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vessels_static_imo ON vessels_static(imo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_imo ON eu_mrv_emissions(imo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_co2 ON eu_mrv_emissions(total_co2_emissions)')
        conn.commit()
        
        query = '''
            SELECT v.mmsi, v.name, v.imo, v.ship_type, v.length, v.flag_state,
                   v.signatory_company, v.last_updated as ais_last_updated,
                   e.company_name as mrv_company, e.total_co2_emissions,
                   e.total_fuel_consumption, e.total_distance_travelled,
                   e.avg_co2_per_distance, e.reporting_period,
                   e.econowind_fit_score, v.technical_fit_score
            FROM vessels_static v
            INNER JOIN eu_mrv_emissions e ON v.imo = e.imo
            WHERE e.total_co2_emissions IS NOT NULL
        '''
        
        params = []
        if min_co2:
            query += ' AND e.total_co2_emissions >= ?'
            params.append(min_co2)
        
        query += ' ORDER BY e.total_co2_emissions DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        
        # Cache the results
        _vessel_cache[cache_key] = results
        _vessel_cache_time[cache_key] = current_time
        
        # Clean old cache entries (older than 10 minutes)
        for key in list(_vessel_cache_time.keys()):
            if current_time - _vessel_cache_time[key] > 600:
                _vessel_cache.pop(key, None)
                _vessel_cache_time.pop(key, None)
        
        response = jsonify(results)
        response.headers['X-Cache'] = 'MISS'
        response.headers['Cache-Control'] = 'public, max-age=300'
        return response
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"ERROR in get_combined_vessel_data: {error_msg}")
        return jsonify({'error': str(e), 'details': error_msg}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/visualization/fleet-network')
def get_fleet_network():
    """Get company-ship network data for 3D visualization."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        ensure_econowind_column(conn)
        cursor = conn.cursor()
        
        # Get vessels with both AIS and emissions data
        cursor.execute('''
            SELECT 
                v.mmsi, v.name, v.imo, v.length, v.ship_type, v.flag_state,
                COALESCE(v.signatory_company, e.company_name) as company,
                e.total_co2_emissions, e.total_fuel_consumption,
                e.avg_co2_per_distance, e.econowind_fit_score
            FROM vessels_static v
            INNER JOIN eu_mrv_emissions e ON v.imo = e.imo
            WHERE e.total_co2_emissions IS NOT NULL
              AND v.length IS NOT NULL
              AND COALESCE(v.signatory_company, e.company_name) IS NOT NULL
            ORDER BY e.total_co2_emissions DESC
            LIMIT 500
        ''')
        
        vessels = cursor.fetchall()
        
        # Build nodes and links
        nodes = []
        links = []
        companies = {}
        
        for vessel in vessels:
            mmsi, name, imo, length, ship_type, flag, company, co2, fuel, co2_per_nm, fit_score = vessel
            
            # Track companies
            if company not in companies:
                companies[company] = {
                    'total_co2': 0,
                    'vessel_count': 0,
                    'total_length': 0
                }
            
            companies[company]['total_co2'] += co2 or 0
            companies[company]['vessel_count'] += 1
            companies[company]['total_length'] += length or 0
            
            # Create ship node
            nodes.append({
                'id': f'ship_{mmsi}',
                'type': 'ship',
                'mmsi': mmsi,
                'name': name or 'Unknown',
                'imo': imo,
                'length': length,
                'ship_type': ship_type,
                'flag_state': flag,
                'company': company,
                'co2': co2,
                'fuel': fuel,
                'co2_per_nm': co2_per_nm,
                'fit_score': fit_score or 0
            })
            
            # Create link from ship to company
            links.append({
                'source': f'ship_{mmsi}',
                'target': f'company_{company}'
            })
        
        # Create company nodes
        for company_name, stats in companies.items():
            nodes.append({
                'id': f'company_{company_name}',
                'type': 'company',
                'name': company_name,
                'vessel_count': stats['vessel_count'],
                'total_co2': stats['total_co2'],
                'avg_vessel_length': stats['total_length'] / stats['vessel_count'] if stats['vessel_count'] > 0 else 0
            })
        
        return jsonify({
            'nodes': nodes,
            'links': links,
            'stats': {
                'total_ships': len(vessels),
                'total_companies': len(companies),
                'total_co2': sum(c['total_co2'] for c in companies.values())
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/emissions/match-stats')
def get_match_statistics():
    """Get real-time matching statistics between AIS and emissions data."""
    global _match_stats_cache, _match_stats_cache_time
    
    # Return cached result if still valid
    current_time = time.time()
    if _match_stats_cache and (current_time - _match_stats_cache_time) < _match_stats_cache_ttl:
        return jsonify(_match_stats_cache)
    
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        # Ensure indexes exist for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vessels_static_imo ON vessels_static(imo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mrv_imo ON eu_mrv_emissions(imo)')
        conn.commit()
        
        # Optimized queries using LEFT JOINs instead of NOT EXISTS (much faster with indexes)
        cursor.execute('SELECT COUNT(*) FROM vessels_static')
        total_ais = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM vessels_static WHERE imo IS NOT NULL AND imo > 0')
        total_ais_with_imo = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions')
        total_emissions = cursor.fetchone()[0]
        
        # Matched vessels - use INNER JOIN (fast with index)
        cursor.execute('''
            SELECT COUNT(DISTINCT v.imo)
            FROM vessels_static v
            INNER JOIN eu_mrv_emissions e ON v.imo = e.imo
            WHERE v.imo IS NOT NULL AND v.imo > 0
        ''')
        matched = cursor.fetchone()[0]
        
        # Emissions only - use LEFT JOIN (faster than NOT EXISTS)
        cursor.execute('''
            SELECT COUNT(*)
            FROM eu_mrv_emissions e
            LEFT JOIN vessels_static v ON e.imo = v.imo
            WHERE v.imo IS NULL
        ''')
        emissions_only = cursor.fetchone()[0]
        
        # AIS only - use LEFT JOIN (faster than NOT EXISTS)
        cursor.execute('''
            SELECT COUNT(*)
            FROM vessels_static v
            LEFT JOIN eu_mrv_emissions e ON v.imo = e.imo
            WHERE v.imo IS NOT NULL AND v.imo > 0 AND e.imo IS NULL
        ''')
        ais_only = cursor.fetchone()[0]
        
        # Recent matches - simplified query
        cursor.execute('''
            SELECT COUNT(DISTINCT v.imo)
            FROM vessels_static v
            INNER JOIN eu_mrv_emissions e ON v.imo = e.imo
            WHERE v.imo IS NOT NULL AND v.imo > 0
            AND v.last_updated > datetime('now', '-1 day')
        ''')
        recent_matches = cursor.fetchone()[0]
        
        result = {
            'total_ais_vessels': total_ais,
            'total_ais_with_imo': total_ais_with_imo,
            'total_emissions_database': total_emissions,
            'matched_vessels': matched,
            'match_rate_percentage': round((matched / total_ais_with_imo * 100), 2) if total_ais_with_imo > 0 else 0,
            'ais_only': ais_only,
            'emissions_only': emissions_only,
            'recent_matches_24h': recent_matches,
            'potential_new_matches': ais_only  # Vessels that could potentially be matched
        }
        
        # Cache the result
        _match_stats_cache = result
        _match_stats_cache_time = current_time
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/statistics/ship-types')
def get_ship_type_statistics():
    """Get statistics about ship types in the database."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        # Get breakdown by AIS ship type
        cursor.execute('''
            SELECT ship_type, COUNT(*) as count
            FROM vessels_static
            WHERE ship_type IS NOT NULL
            GROUP BY ship_type
            ORDER BY count DESC
        ''')
        ais_types = cursor.fetchall()
        
        # Get breakdown by detailed ship type from EU MRV
        cursor.execute('''
            SELECT detailed_ship_type, COUNT(*) as count
            FROM vessels_static
            WHERE detailed_ship_type IS NOT NULL
            GROUP BY detailed_ship_type
            ORDER BY count DESC
        ''')
        detailed_types = cursor.fetchall()
        
        # Get vessels without detailed type but with IMO
        cursor.execute('''
            SELECT COUNT(*)
            FROM vessels_static
            WHERE imo IS NOT NULL AND imo > 0
            AND detailed_ship_type IS NULL
        ''')
        missing_detailed = cursor.fetchone()[0]
        
        # Format AIS types with names
        ais_breakdown = []
        for ship_type, count in ais_types:
            ais_breakdown.append({
                'code': ship_type,
                'name': get_ship_type_name(ship_type),
                'count': count
            })
        
        # Format detailed types
        detailed_breakdown = []
        for ship_type, count in detailed_types:
            detailed_breakdown.append({
                'type': ship_type,
                'count': count
            })
        
        return jsonify({
            'ais_types': ais_breakdown,
            'detailed_types': detailed_breakdown,
            'vessels_missing_detailed_type': missing_detailed,
            'total_vessels': sum(t['count'] for t in ais_breakdown)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/detailed-ship-types')
def get_detailed_ship_types():
    """Get list of unique detailed ship types for filtering."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        # Check if column exists first
        cursor.execute("PRAGMA table_info(vessels_static)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'detailed_ship_type' not in columns:
            print("Warning: detailed_ship_type column does not exist yet")
            return jsonify([])  # Return empty array
        
        # Get unique detailed ship types with counts
        cursor.execute('''
            SELECT detailed_ship_type, COUNT(*) as count
            FROM vessels_static
            WHERE detailed_ship_type IS NOT NULL
            GROUP BY detailed_ship_type
            ORDER BY detailed_ship_type
        ''')
        
        types = []
        for ship_type, count in cursor.fetchall():
            types.append({
                'name': ship_type,
                'count': count
            })
        
        return jsonify(types)
    except Exception as e:
        print(f"Error in get_detailed_ship_types: {e}")
        return jsonify([]), 200  # Return empty array instead of error
    finally:
        if conn:
            conn.close()


@app.route('/ships/api/vessel/<int:mmsi>/photo')
def get_vessel_photo(mmsi):
    """Get vessel photo URL from public sources."""
    try:
        # Use direct photo URLs from public sources
        # These are publicly accessible and don't require scraping
        
        # Try MarineTraffic photo service (public API)
        photo_url = f"https://photos.marinetraffic.com/ais/showphoto.aspx?mmsi={mmsi}"
        
        # Return the URL - the frontend will handle if it loads or not
        return jsonify({
            'photo_url': photo_url,
            'source': 'MarineTraffic',
            'mmsi': mmsi
        })
        
    except Exception as e:
        print(f"Error generating photo URL for MMSI {mmsi}: {e}")
        return jsonify({'photo_url': None, 'source': None, 'error': str(e)}), 500


@app.route('/ships/api/vessel/<int:mmsi>/wind-tech')
def get_vessel_wind_tech(mmsi):
    """Get wind propulsion technology details for a vessel."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        # Try MMSI-based table first
        cursor.execute('''
            SELECT technology_installed, installation_year, installation_type
            FROM wind_propulsion_mmsi
            WHERE mmsi = ?
        ''', (mmsi,))
        
        result = cursor.fetchone()
        
        if result:
            return jsonify({
                'technology': result[0],
                'year': result[1],
                'type': result[2],
                'found': True
            })
        
        # Fallback to name-based table
        cursor.execute('''
            SELECT w.technology_installed, w.installation_year, w.installation_type
            FROM wind_propulsion w
            INNER JOIN vessels_static v ON UPPER(TRIM(v.name)) = UPPER(TRIM(w.vessel_name))
            WHERE v.mmsi = ?
        ''', (mmsi,))
        
        result = cursor.fetchone()
        
        if result:
            return jsonify({
                'technology': result[0],
                'year': result[1],
                'type': result[2],
                'found': True
            })
        
        return jsonify({'found': False})
        
    except Exception as e:
        print(f"Error fetching wind tech for MMSI {mmsi}: {e}")
        return jsonify({'error': str(e), 'found': False}), 500
    finally:
        if conn:
            conn.close()


# ==================== INTELLIGENCE DASHBOARD ROUTES ====================

# Global scraper states
intelligence_scraper_status = {
    'running': False,
    'current_company': None,
    'companies_processed': 0,
    'total_companies': 0,
    'findings_count': 0,
    'start_time': None,
    'progress': 0,
    'type': 'intelligence'
}

profiler_scraper_status = {
    'running': False,
    'current_company': None,
    'companies_processed': 0,
    'total_companies': 0,
    'profiles_count': 0,
    'start_time': None,
    'progress': 0,
    'type': 'profiler'
}

# @app.route('/ships/intelligence')
# def intelligence_dashboard():
#     """Render Intelligence Dashboard."""
#     return render_template('intelligence.html')


@app.route('/ships/api/intelligence/datasets')
def list_intelligence_datasets():
    """List all available intelligence datasets."""
    try:
        project_root = Path(__file__).parent.parent.parent
        # VPS stores datasets under /data; local analysis often stores under /intelligence
        search_dirs = []
        if (project_root / 'data').exists():
            search_dirs.append(project_root / 'data')
        if (project_root / 'intelligence').exists():
            search_dirs.append(project_root / 'intelligence')
        
        datasets = []
        
        # Find all intelligence JSON files
        intel_files = []
        for d in search_dirs:
            intel_files.extend(list(d.glob('company_intelligence*.json')))
        for file_path in intel_files:
            try:
                stat = file_path.stat()                # Load file to get stats
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    companies_obj = data.get('companies', {})
                    if isinstance(companies_obj, dict):
                        companies_count = data.get('total', len(companies_obj))
                        company_iter = companies_obj.values()
                    elif isinstance(companies_obj, list):
                        companies_count = data.get('total', len(companies_obj))
                        company_iter = companies_obj
                    else:
                        companies_count = data.get('total', 0)
                        company_iter = []

                    # Count findings
                    findings_count = 0
                    for company in company_iter:
                        if isinstance(company, dict) and 'intelligence' in company:
                            for category in company['intelligence'].values():
                                if isinstance(category, dict):
                                    findings_count += category.get('results_count', 0)

                
                datasets.append({
                    'filename': file_path.name,
                    'type': 'intelligence',
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / (1024*1024), 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'companies': companies_count,
                    'findings': findings_count,
                    'download_url': f'/ships/api/intelligence/download/{file_path.name}'
                })
            except Exception as e:
                print(f"Error reading dataset {file_path}: {e}")
                continue
        
        # Find all profiler JSON files
        prof_files = []
        for d in search_dirs:
            prof_files.extend(list(d.glob('company_profiles_v3*.json')))
        for file_path in prof_files:
            try:
                stat = file_path.stat()
                
                # Load file to get stats
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    companies_count = data.get('total', 0)
                    
                    # Count profiles (profilers count wiki + website pages as "findings")
                    profiles_count = 0
                    if 'companies' in data:
                        for company in data['companies'].values():
                            if 'text_data' in company:
                                # Count Wikipedia + website pages
                                wiki = company['text_data'].get('wikipedia', {})
                                website = company['text_data'].get('website', {})
                                if wiki.get('summary'):
                                    profiles_count += 1
                                if website.get('pages'):
                                    profiles_count += len(website['pages'])
                
                datasets.append({
                    'filename': file_path.name,
                    'type': 'profiler',
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / (1024*1024), 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'companies': companies_count,
                    'findings': profiles_count,  # Use profile count instead
                    'download_url': f'/ships/api/intelligence/download/{file_path.name}'
                })
            except Exception as e:
                print(f"Error reading dataset {file_path}: {e}")
                continue
        
        # Sort by modified date (newest first)
        datasets.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'datasets': datasets,
            'count': len(datasets)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ships/api/intelligence/download/<filename>')
def download_intelligence_dataset(filename):
    """Download a specific intelligence or profiler dataset."""
    try:
        # Security: only allow intelligence and profiler files
        allowed_prefixes = ['company_intelligence', 'company_profiles_v3']
        if not any(filename.startswith(prefix) for prefix in allowed_prefixes) or not filename.endswith('.json'):
            return jsonify({'error': 'Invalid filename'}), 403
        
        project_root = Path(__file__).parent.parent.parent
        file_path = project_root / 'data' / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        from flask import send_file
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ships/api/intelligence/status')
def get_intelligence_status():
    """Get current intelligence scraper status."""
    return jsonify(intelligence_scraper_status)


@app.route('/ships/api/profiler/status')
def get_profiler_status():
    """Get current profiler scraper status."""
    return jsonify(profiler_scraper_status)


@app.route('/ships/api/scrapers/status')
def get_all_scrapers_status():
    """Get status of both scrapers by reading progress files."""
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / 'data'
    
    # Intelligence Scraper Status
    intel_status = {
        'running': False,
        'current_company': None,
        'companies_processed': 0,
        'total_companies': 30,  # Default batch size
        'findings_count': 0,
        'progress': 0
    }
    
    try:
        # Check Gemini progress file
        gemini_progress = data_dir / 'company_intelligence_gemini_progress.json'
        if gemini_progress.exists():
            # Check if file was modified in last 5 minutes (scraper is running)
            import time
            file_age = time.time() - gemini_progress.stat().st_mtime
            intel_status['running'] = file_age < 300  # 5 minutes
            
            with open(gemini_progress, 'r', encoding='utf-8') as f:
                data = json.load(f)
                companies = data.get('companies', {})
                intel_status['companies_processed'] = len(companies)
                intel_status['total_companies'] = data.get('total', 30)
                
                # Count total findings
                total_findings = 0
                last_company = None
                for company_name, company_data in companies.items():
                    last_company = company_name
                    for category in company_data.get('intelligence', {}).values():
                        total_findings += category.get('results_count', 0)
                
                intel_status['findings_count'] = total_findings
                intel_status['current_company'] = last_company if intel_status['running'] else None
                intel_status['progress'] = int((intel_status['companies_processed'] / intel_status['total_companies']) * 100) if intel_status['total_companies'] > 0 else 0
    except Exception as e:
        print(f"Error reading intelligence status: {e}")
    
    # Company Profiler Status
    profiler_status = {
        'running': False,
        'current_company': None,
        'companies_processed': 0,
        'total_companies': 25,  # Default batch size
        'profiles_count': 0,
        'progress': 0
    }
    
    try:
        # Check for most recent V3 structured file
        v3_files = sorted(data_dir.glob('company_profiles_v3_structured_*.json'), reverse=True)
        if v3_files:
            latest_file = v3_files[0]
            
            # Check if file was modified in last 5 minutes
            import time
            file_age = time.time() - latest_file.stat().st_mtime
            profiler_status['running'] = file_age < 300  # 5 minutes
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                companies = data.get('companies', {})
                profiler_status['companies_processed'] = len(companies)
                profiler_status['profiles_count'] = len(companies)
                profiler_status['total_companies'] = data.get('total', 25)
                
                # Get last company name
                if companies:
                    last_company = list(companies.keys())[-1]
                    profiler_status['current_company'] = last_company if profiler_status['running'] else None
                
                profiler_status['progress'] = int((profiler_status['companies_processed'] / profiler_status['total_companies']) * 100) if profiler_status['total_companies'] > 0 else 0
    except Exception as e:
        print(f"Error reading profiler status: {e}")
    
    return jsonify({
        'intelligence': intel_status,
        'profiler': profiler_status
    })


@app.route('/ships/api/intelligence/stats')
def get_intelligence_stats():
    """Get aggregate intelligence statistics."""
    try:
        project_root = Path(__file__).parent.parent.parent
        # VPS stores datasets under /data; local analysis often stores under /intelligence
        search_dirs = []
        if (project_root / 'data').exists():
            search_dirs.append(project_root / 'data')
        if (project_root / 'intelligence').exists():
            search_dirs.append(project_root / 'intelligence')
        
        # Find most recent intelligence file (prioritize Gemini over v2)
        gemini_files = []
        v2_files = []
        for d in search_dirs:
            gemini_files.extend(list(d.glob('company_intelligence_gemini_*.json')))
            v2_files.extend(list(d.glob('company_intelligence_v2_*.json')))
        gemini_files = sorted(gemini_files, reverse=True)
        v2_files = sorted(v2_files, reverse=True)
        
        # Use Gemini if available, otherwise fall back to v2
        files = gemini_files if gemini_files else v2_files
        
        if not files:
            return jsonify({
                'total_companies': 0,
                'total_findings': 0,
                'avg_findings_per_company': 0,
                'categories': {},
                'top_companies': []
            })
        
        latest_file = files[0]
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_companies = len(data.get('companies', {}))
        category_stats = {
            'grants_subsidies': 0,
            'legal_violations': 0,
            'sustainability_news': 0,
            'reputation': 0,
            'financial_pressure': 0
        }
        
        top_companies = []
        
        for company_name, company_data in data.get('companies', {}).items():
            company_findings = 0
            
            for category_name, category_data in company_data.get('intelligence', {}).items():
                count = category_data.get('results_count', 0)
                category_stats[category_name] += count
                company_findings += count
            
            if company_findings > 0:
                top_companies.append({
                    'name': company_name,
                    'findings': company_findings,
                    'fleet_size': company_data.get('metadata', {}).get('vessel_count', 0)
                })
        
        # Sort by findings
        top_companies.sort(key=lambda x: x['findings'], reverse=True)
        
        total_findings = sum(category_stats.values())
        
        return jsonify({
            'total_companies': total_companies,
            'total_findings': total_findings,
            'avg_findings_per_company': round(total_findings / total_companies, 1) if total_companies > 0 else 0,
            'categories': category_stats,
            'top_companies': top_companies[:10],
            'latest_file': latest_file.name,
            'timestamp': data.get('timestamp')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== PROFILE + SENTIMENT SUMMARY (FOR INTELLIGENCE UI) ====================

def _intel_search_dirs(project_root: Path) -> list[Path]:
    """Search dirs that may contain intelligence/profiler JSON files (VPS uses data/, local often uses intelligence/)."""
    dirs: list[Path] = []
    d1 = project_root / 'data'
    d2 = project_root / 'intelligence'
    if d1.exists():
        dirs.append(d1)
    if d2.exists():
        dirs.append(d2)
    return dirs


def _latest_matching_file(search_dirs: list[Path], glob_pat: str, name_contains: str = '') -> Path | None:
    candidates: list[Path] = []
    for d in search_dirs:
        candidates.extend(list(d.glob(glob_pat)))
    if name_contains:
        candidates = [p for p in candidates if name_contains.lower() in p.name.lower()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _iter_companies_obj(companies_obj):
    """Yield (company_name, company_data) pairs from either dict or list formats."""
    if isinstance(companies_obj, dict):
        for k, v in companies_obj.items():
            yield k, v
    elif isinstance(companies_obj, list):
        for item in companies_obj:
            if isinstance(item, dict):
                name = item.get('company_name') or item.get('name')
                if name:
                    yield name, item


def _is_aboutish(page_type: str) -> bool:
    s = (page_type or '').lower()
    keys = ['about', 'company', 'our-story', 'mission', 'values', 'sustainability', 'esg', 'environment']
    return any(k in s for k in keys)


def _website_sentiment_from_profile(company_profile: dict) -> dict:
    """Compute sentiment metrics from profile website pages (mirrors exporter logic)."""
    website = (company_profile.get('text_data') or {}).get('website') or {}
    pages = website.get('pages') or []
    about_pages = [p for p in pages if isinstance(p, dict) and _is_aboutish(p.get('page_type', ''))]
    if not about_pages:
        about_pages = pages
    combined = ' '.join([p.get('text', '') for p in about_pages if isinstance(p, dict) and p.get('text')])
    text_len = len(combined)

    if TEXTBLOB_AVAILABLE and combined:
        blob = TextBlob(combined)
        polarity = float(blob.sentiment.polarity)
        subjectivity = float(blob.sentiment.subjectivity)
    else:
        polarity = 0.0
        subjectivity = 0.0

    return {
        'num_pages_total': len(pages),
        'num_pages_aboutish': len(about_pages),
        'text_len': text_len,
        'polarity': polarity,
        'subjectivity': subjectivity,
    }


@app.route('/ships/api/intelligence/company-profiles/summary')
def get_company_profiles_summary():
    """Aggregate latest company profiles + website sentiment (and merge intel counts when available)."""
    try:
        project_root = Path(__file__).parent.parent.parent
        search_dirs = _intel_search_dirs(project_root)

        scope = (request.args.get('scope') or '').strip().lower()  # e.g. 'wasp', 'non_wasp'
        limit = int(request.args.get('limit', 30))
        limit = max(1, min(limit, 200))

        profile_file = _latest_matching_file(search_dirs, 'company_profiles_v3_structured_*.json', name_contains=scope)
        if profile_file is None and scope:
            profile_file = _latest_matching_file(search_dirs, 'company_profiles_v3_structured_*.json', name_contains=scope.replace('_', ''))

        if profile_file is None:
            return jsonify({'error': 'No profile data found', 'file': None, 'total': 0, 'companies': []}), 404

        with open(profile_file, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)

        # Optional intelligence merge (latest file)
        intel_file = _latest_matching_file(search_dirs, 'company_intelligence_gemini_*.json', name_contains=scope) \
            or _latest_matching_file(search_dirs, 'company_intelligence_v2_*.json', name_contains=scope)
        if intel_file is None and scope:
            intel_file = _latest_matching_file(search_dirs, 'company_intelligence_gemini_*.json', name_contains=scope.replace('_', '')) \
                or _latest_matching_file(search_dirs, 'company_intelligence_v2_*.json', name_contains=scope.replace('_', ''))

        intel_map = {}
        if intel_file and intel_file.exists():
            try:
                with open(intel_file, 'r', encoding='utf-8') as f:
                    intel_data = json.load(f)
                for cname, cdata in _iter_companies_obj(intel_data.get('companies', {})):
                    total_findings = 0
                    by_cat = {}
                    for cat, cat_data in (cdata.get('intelligence', {}) or {}).items():
                        if isinstance(cat_data, dict):
                            cnt = int(cat_data.get('results_count', 0) or 0)
                            by_cat[cat] = cnt
                            total_findings += cnt
                    intel_map[cname] = {'total_findings': total_findings, 'categories': by_cat}
            except Exception:
                intel_map = {}

        companies_out = []
        for cname, prof in _iter_companies_obj(profile_data.get('companies', {})):
            if not isinstance(prof, dict):
                continue

            attrs = prof.get('attributes', {}) or {}
            labels = prof.get('labels', {}) or {}
            wiki = (prof.get('text_data') or {}).get('wikipedia') or {}
            website = (prof.get('text_data') or {}).get('website') or {}

            sent = _website_sentiment_from_profile(prof)
            intel = intel_map.get(cname, {'total_findings': 0, 'categories': {}})

            companies_out.append({
                'company_name': cname,
                'attributes': {
                    'vessel_count': attrs.get('vessel_count'),
                    'avg_emissions_tons': attrs.get('avg_emissions_tons'),
                    'avg_co2_per_distance': attrs.get('avg_co2_per_distance'),
                    'avg_wasp_fit_score': attrs.get('avg_wasp_fit_score'),
                    'primary_ship_types': attrs.get('primary_ship_types') or [],
                },
                'labels': labels,
                'wikipedia': {
                    'title': wiki.get('title'),
                    'length': wiki.get('length'),
                    'summary': wiki.get('summary', '')[:500] if isinstance(wiki.get('summary'), str) else '',
                },
                'website': {
                    'pages_count': website.get('pages_count', 0),
                    'total_length': website.get('total_length', 0),
                },
                'sentiment': sent,
                'intelligence': intel,
            })

        companies_out.sort(
            key=lambda x: (
                x.get('sentiment', {}).get('text_len', 0) or 0,
                x.get('intelligence', {}).get('total_findings', 0) or 0,
            ),
            reverse=True,
        )
        companies_out = companies_out[:limit]

        return jsonify({
            'file': profile_file.name,
            'file_modified': datetime.fromtimestamp(profile_file.stat().st_mtime).isoformat(),
            'timestamp': profile_data.get('timestamp'),
            'total': int(profile_data.get('total', len(profile_data.get('companies', {})))),
            'scope': scope or None,
            'intelligence_file': intel_file.name if intel_file else None,
            'companies': companies_out,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ML PREDICTION ROUTES ====================

# ML Service Configuration (PC)
# Set ML_PC_URL environment variable to use PC resources, e.g.:
# export ML_PC_URL="http://YOUR_PC_IP:5001"
# Or set to None/empty to use VPS resources
ML_PC_URL = os.environ.get('ML_PC_URL', '')

def proxy_to_pc(endpoint, method='GET', data=None):
    """Proxy request to PC ML service."""
    if not ML_PC_URL:
        return None
    
    try:
        import requests
        url = f"{ML_PC_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        
        if method == 'GET':
            response = requests.get(url, timeout=30)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=300)  # Longer timeout for training
        else:
            return None
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error proxying to PC: {e}")
        return None

@app.route('/ships/api/ml/predictions')
def get_ml_predictions():
    """Get ML predictions for all companies."""
    # Try PC first if configured
    if ML_PC_URL:
        pc_response = proxy_to_pc('/predictions')
        if pc_response:
            return jsonify(pc_response)
    
    # Fallback to VPS
    try:
        project_root = Path(__file__).parent.parent.parent
        predictions_file = project_root / 'data' / 'company_predictions.json'
        
        if not predictions_file.exists():
            return jsonify({
                'error': 'Predictions not available. Train models first.',
                'predictions': {},
                'total_companies': 0
            })
        
        with open(predictions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ships/api/ml/predictions/company/<company_name>')
def get_company_prediction(company_name):
    """Get ML predictions for a specific company."""
    # Try PC first if configured
    if ML_PC_URL:
        pc_response = proxy_to_pc(f'/predictions/{company_name}')
        if pc_response:
            return jsonify(pc_response)
    
    # Fallback to VPS
    try:
        # Import from new ML module (with fallback to old location)
        try:
            from src.ml.predictor import CompanyMLPredictor
        except ImportError:
            from src.services.ml_predictor_service import CompanyMLPredictor
        
        predictor = CompanyMLPredictor()
        
        # Try to load existing models
        if not predictor.load_models():
            return jsonify({
                'error': 'Models not trained. Train models first.',
                'company': company_name
            }), 404
        
        # Load company data
        intelligence_data = predictor.load_intelligence_data()
        profile_data = predictor.load_profile_data()
        
        # Merge data
        company_data = {}
        if company_name in intelligence_data:
            company_data.update(intelligence_data[company_name])
        if company_name in profile_data:
            company_data.update(profile_data[company_name])
        
        if not company_data:
            return jsonify({'error': 'Company not found', 'company': company_name}), 404
        
        # Make prediction
        predictions = predictor.predict_company(company_name, company_data)
        
        return jsonify({
            'company': company_name,
            'predictions': predictions,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ships/api/ml/train', methods=['POST'])
def train_ml_models():
    """Train ML models (admin endpoint)."""
    # Try PC first if configured
    if ML_PC_URL:
        pc_response = proxy_to_pc('/train', method='POST')
        if pc_response:
            return jsonify(pc_response)
    
    # Fallback to VPS
    try:
        # Import from new ML module (with fallback to old location)
        try:
            from src.ml.predictor import CompanyMLPredictor
        except ImportError:
            from src.services.ml_predictor_service import CompanyMLPredictor
        
        predictor = CompanyMLPredictor()
        models = predictor.train_all_models()
        
        if models:
            predictor.save_models()
            
            # Generate predictions
            predictions = predictor.predict_all_companies()
            
            # Save predictions
            project_root = Path(__file__).parent.parent.parent
            output_file = project_root / 'data' / 'company_predictions.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'predictions': predictions,
                    'total_companies': len(predictions),
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'status': 'success',
                'models_trained': list(models.keys()),
                'total_companies': len(predictions),
                'message': 'Models trained and predictions generated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No models could be trained. Check data availability.'
            }), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ships/api/ml/stats')
def get_ml_stats():
    """Get ML model statistics and performance metrics."""
    # Try PC first if configured
    if ML_PC_URL:
        pc_response = proxy_to_pc('/stats')
        if pc_response:
            return jsonify(pc_response)
    
    # Fallback to VPS
    try:
        import pandas as pd
        
        project_root = Path(__file__).parent.parent.parent
        predictions_file = project_root / 'data' / 'company_predictions.json'
        models_file = project_root / 'data' / 'ml_models.pkl'
        
        stats = {
            'models_available': models_file.exists(),
            'predictions_available': predictions_file.exists(),
            'total_companies': 0,
            'predictions_summary': {}
        }
        
        if predictions_file.exists():
            with open(predictions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            predictions = data.get('predictions', {})
            stats['total_companies'] = len(predictions)
            
            # Summary statistics
            wasp_predictions = [p.get('wasp_adoption', {}).get('prediction', False) 
                              for p in predictions.values() 
                              if 'wasp_adoption' in p]
            sust_predictions = [p.get('sustainability_focus', {}).get('prediction', 'unknown')
                              for p in predictions.values()
                              if 'sustainability_focus' in p]
            
            stats['predictions_summary'] = {
                'wasp_adoption_positive': sum(wasp_predictions),
                'wasp_adoption_total': len(wasp_predictions),
                'sustainability_levels': dict(pd.Series(sust_predictions).value_counts()) if sust_predictions else {}
            }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ML DATA ENDPOINTS (for PC ML Service) ====================

@app.route('/ships/api/ml/data/intelligence')
def get_ml_intelligence_data():
    """Serve intelligence data for PC ML service."""
    try:
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / 'data'
        
        # Find latest Gemini intelligence file
        intel_files = sorted(
            data_dir.glob("company_intelligence_gemini_*.json"),
            reverse=True
        )
        
        if not intel_files:
            return jsonify({'error': 'No intelligence data found', 'companies': {}}), 404
        
        with open(intel_files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ships/api/ml/data/profiles')
def get_ml_profile_data():
    """Serve profile data for PC ML service."""
    try:
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / 'data'
        
        # Find latest V3 structured profile file
        profile_files = sorted(
            data_dir.glob("company_profiles_v3_structured_*.json"),
            reverse=True
        )
        
        if not profile_files:
            return jsonify({'error': 'No profile data found', 'companies': {}}), 404
        
        with open(profile_files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/ships/api/ml/data/wasp')
def get_ml_wasp_data():
    """Serve WASP adopters data for PC ML service."""
    try:
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / 'data' / 'vessel_static_data.db'
        
        if not db_path.exists():
            return jsonify({'error': 'Database not found', 'wasp_companies': {}}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        wasp_companies = {}
        
        # Check if required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eu_mrv_emissions'")
        has_emissions = cursor.fetchone() is not None
        
        if has_emissions:
            # Get companies with wind-assisted vessels
            try:
                cursor.execute('''
                    SELECT DISTINCT e.company_name
                    FROM eu_mrv_emissions e
                    INNER JOIN vessels_static v ON e.imo = v.imo
                    WHERE v.wind_assisted = 1
                    AND e.company_name IS NOT NULL
                ''')
                wasp_companies = {row[0]: True for row in cursor.fetchall()}
            except Exception:
                pass
            
            # Also check wind_propulsion table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wind_propulsion'")
            has_wind = cursor.fetchone() is not None
            
            if has_wind:
                try:
                    cursor.execute('''
                        SELECT DISTINCT e.company_name
                        FROM eu_mrv_emissions e
                        INNER JOIN wind_propulsion w ON UPPER(TRIM(e.vessel_name)) = UPPER(TRIM(w.vessel_name))
                        WHERE e.company_name IS NOT NULL
                    ''')
                    for row in cursor.fetchall():
                        wasp_companies[row[0]] = True
                except Exception:
                    pass
        
        conn.close()
        return jsonify({'wasp_companies': wasp_companies})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Start tracking in background
    tracking_thread = threading.Thread(target=start_tracking, daemon=True)
    tracking_thread.start()
    
    # Give tracking a moment to initialize
    time.sleep(2)
    
    print("\n" + "="*70)
    print("VESSEL TRACKER WEB INTERFACE")
    print("="*70)
    print("Open your browser and go to:")
    print("  http://localhost:5000")
    print("="*70 + "\n")
    
    # Start Flask server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
