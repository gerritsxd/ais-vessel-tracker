"""
Real-time Web-Based Vessel Tracker with Map Visualization
Displays tracked vessels on an interactive map with live updates.
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import websocket
import json
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime

# Configuration
DB_NAME = "vessel_static_data.db"
API_KEY_FILE = "api.txt"
WEBSOCKET_URL = "wss://stream.aisstream.io/v0/stream"
MAX_MMSI_PER_CONNECTION = 50

# Flask app
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['SECRET_KEY'] = 'ais-tracker-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
API_KEY = None
vessel_positions = {}  # {mmsi: {lat, lon, sog, cog, timestamp, name, ...}}
vessel_static_data = {}  # {mmsi: {name, length, type, flag, ...}}
tracking_active = False


def load_api_keys():
    """Load all API keys from api.txt file."""
    try:
        script_dir = Path(__file__).parent
        api_file_path = script_dir / API_KEY_FILE
        
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
    script_dir = Path(__file__).parent
    db_path = script_dir / DB_NAME
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        query = '''
            SELECT mmsi, name, ship_type, length, beam, imo, call_sign, flag_state, signatory_company
            FROM vessels_static
            WHERE length >= 100
              AND mmsi IS NOT NULL
              AND length IS NOT NULL
              AND (ship_type IS NULL OR ship_type NOT IN (71, 72))
              AND last_updated >= datetime('now', '-7 days')
            ORDER BY last_updated DESC
            LIMIT 1050
        '''
        
        cursor.execute(query)
        vessels = cursor.fetchall()
    finally:
        if conn:
            conn.close()
    
    # Store static data
    for vessel in vessels:
        mmsi, name, ship_type, length, beam, imo, call_sign, flag_state, signatory_company = vessel
        vessel_static_data[mmsi] = {
            'name': name or 'Unknown',
            'ship_type': ship_type,
            'length': length,
            'beam': beam,
            'imo': imo,
            'call_sign': call_sign,
            'flag_state': flag_state or 'Unknown',
            'signatory_company': signatory_company
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
                        script_dir = Path(__file__).parent
                        db_path = script_dir / DB_NAME
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


# Flask routes
@app.route('/')
def index():
    """Serve the main map page."""
    return render_template('map.html')


@app.route('/api/vessels')
def get_vessels():
    """Get all tracked vessels and their current positions."""
    vessels = []
    for mmsi, static in vessel_static_data.items():
        vessel_info = {
            'mmsi': mmsi,
            'name': static['name'],
            'length': static['length'],
            'flag_state': static['flag_state'],
            'ship_type': static['ship_type']
        }
        
        # Add position if available
        if mmsi in vessel_positions:
            vessel_info.update(vessel_positions[mmsi])
        
        vessels.append(vessel_info)
    
    return jsonify(vessels)


@app.route('/api/stats')
def get_stats():
    """Get tracking statistics."""
    return jsonify({
        'total_vessels': len(vessel_static_data),
        'vessels_with_position': len(vessel_positions),
        'tracking_active': tracking_active
    })


@app.route('/database')
def database_viewer():
    """Serve the database viewer page."""
    return render_template('database.html')


@app.route('/api/vessel/<int:mmsi>/route')
def get_vessel_route(mmsi):
    """Get position history for a specific vessel."""
    hours = request.args.get('hours', default=24, type=int)
    
    script_dir = Path(__file__).parent
    db_path = script_dir / DB_NAME
    
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
        
        route = []
        for p in positions:
            route.append({
                'lat': p[0],
                'lon': p[1],
                'sog': p[2],
                'cog': p[3],
                'timestamp': p[4]
            })
        
        return jsonify(route)
    finally:
        if conn:
            conn.close()


@app.route('/api/database/vessels')
def get_all_vessels():
    """Get all vessels from database with filtering."""
    script_dir = Path(__file__).parent
    db_path = script_dir / DB_NAME
    
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
        query = 'SELECT mmsi, name, ship_type, length, beam, imo, call_sign, flag_state, destination, eta, draught, last_updated, signatory_company FROM vessels_static WHERE 1=1'
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
                'length': v[3],
                'beam': v[4],
                'imo': v[5],
                'call_sign': v[6],
                'flag_state': v[7],
                'destination': v[8],
                'eta': v[9],
                'draught': v[10],
                'last_updated': v[11],
                'signatory_company': v[12]
            })
        
        return jsonify(results)
    except Exception as e:
        print(f"Error in get_all_vessels: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/companies')
def get_companies():
    """Get company statistics."""
    script_dir = Path(__file__).parent
    db_path = script_dir / DB_NAME
    
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
        print("Loading API keys...")
        api_keys = load_api_keys()
        
        print("Loading vessels from database...")
        mmsi_list = get_filtered_vessels()
        print(f"Loaded {len(mmsi_list)} vessels for tracking")
        
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
