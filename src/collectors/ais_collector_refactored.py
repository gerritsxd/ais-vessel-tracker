"""
AIS Data Collector - Real-time vessel tracking via AISStream WebSocket.

This module connects to the AISStream API, filters for cargo/tanker vessels
>= 100m, and persists static data to SQLite with automatic reconnection.

Key Features:
- Real-time WebSocket streaming from AISStream
- Filters for cargo ships (70-79) and tankers (80-89) >= 100m
- Automatic reconnection with exponential backoff
- SQLite persistence with UPSERT (preserves enrichments)
- Statistics reporting every 5 minutes

Usage:
    python -m src.collectors.ais_collector
"""

import websocket
import json
import sqlite3
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Handle both direct script execution and module import
try:
    from .mmsi_mid_lookup import get_flag_state
    from .constants import *
    from .ais_message_parser import (
        parse_ship_static_data,
        parse_static_data_report,
        parse_position_report,
        should_save_vessel
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from mmsi_mid_lookup import get_flag_state
    from constants import *
    from ais_message_parser import (
        parse_ship_static_data,
        parse_static_data_report,
        parse_position_report,
        should_save_vessel
    )

# Global state (module-level)
_db_conn: Optional[sqlite3.Connection] = None
_api_key: Optional[str] = None
_message_count: int = 0
_last_stats_time: Optional[float] = None


def load_api_key() -> str:
    """
    Load AISStream API key from environment variable or file.
    
    Priority:
        1. AIS_API_KEY environment variable
        2. Last non-empty line in api.txt file
    
    Returns:
        API key string
        
    Raises:
        FileNotFoundError: If api.txt not found
        ValueError: If api.txt is empty
    """
    env_key = os.environ.get('AIS_API_KEY')
    if env_key:
        print("Using API key from environment variable")
        return env_key
    
    project_root = Path(__file__).parent.parent.parent
    api_file_path = project_root / API_KEY_FILENAME
    
    if not api_file_path.exists():
        raise FileNotFoundError(
            f"API key file '{API_KEY_FILENAME}' not found. "
            "Please create it with your AISStream API key."
        )
    
    with open(api_file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
        if not lines:
            raise ValueError(f"No API key found in {API_KEY_FILENAME}")
        return lines[-1]  # Return last non-empty line


def init_database() -> sqlite3.Connection:
    """
    Initialize SQLite database with required tables and indexes.
    
    Creates:
        - vessels_static: Main vessel data table
        - vessel_positions: Position history table
        - Index on (mmsi, timestamp) for fast queries
    
    Returns:
        Database connection object
    """
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / DATABASE_NAME
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    cursor = conn.cursor()
    
    # Create vessels_static table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vessels_static (
            mmsi INTEGER PRIMARY KEY UNIQUE NOT NULL,
            name TEXT,
            ship_type INTEGER,
            detailed_ship_type TEXT,
            length INTEGER,
            beam INTEGER,
            imo INTEGER,
            call_sign TEXT,
            flag_state TEXT,
            signatory_company TEXT,
            destination TEXT,
            eta TEXT,
            draught REAL,
            nav_status INTEGER,
            last_updated TEXT NOT NULL
        )
    ''')
    
    # Create vessel_positions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vessel_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mmsi INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            sog REAL,
            cog REAL,
            heading INTEGER,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (mmsi) REFERENCES vessels_static(mmsi)
        )
    ''')
    
    # Create index for faster position queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_positions_mmsi_time 
        ON vessel_positions(mmsi, timestamp DESC)
    ''')
    
    conn.commit()
    print(f"Database initialized: {db_path}")
    return conn


def save_vessel_data(
    mmsi: int,
    name: Optional[str],
    ship_type: Optional[int],
    length: Optional[int],
    beam: Optional[int],
    imo: Optional[int],
    call_sign: Optional[str],
    destination: Optional[str] = None,
    eta: Optional[str] = None,
    draught: Optional[float] = None,
    nav_status: Optional[int] = None
) -> None:
    """
    Save or update vessel data using UPSERT pattern.
    
    Uses COALESCE to preserve existing data when new data is NULL.
    Preserves signatory_company enrichment from external sources.
    
    Args:
        mmsi: Maritime Mobile Service Identity (primary key)
        name: Vessel name
        ship_type: AIS ship type code (70-89 for cargo/tankers)
        length: Vessel length in meters
        beam: Vessel beam (width) in meters
        imo: International Maritime Organization number
        call_sign: Radio call sign
        destination: Current destination port
        eta: Estimated time of arrival (JSON string)
        draught: Current draught in meters
        nav_status: Navigation status code
    """
    global _db_conn
    
    if _db_conn is None:
        print("Error: Database connection not available")
        return
    
    flag_state = get_flag_state(mmsi)
    timestamp = datetime.utcnow().isoformat()
    
    # Retry logic for database locks
    for attempt in range(DB_MAX_RETRIES):
        try:
            _db_conn.execute("SELECT 1")  # Test connection
            
            cursor = _db_conn.cursor()
            cursor.execute('''
                INSERT INTO vessels_static 
                (mmsi, name, ship_type, length, beam, imo, call_sign, flag_state, 
                 destination, eta, draught, nav_status, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mmsi) DO UPDATE SET
                    name = COALESCE(excluded.name, name),
                    ship_type = COALESCE(excluded.ship_type, ship_type),
                    length = COALESCE(excluded.length, length),
                    beam = COALESCE(excluded.beam, beam),
                    imo = COALESCE(excluded.imo, imo),
                    call_sign = COALESCE(excluded.call_sign, call_sign),
                    flag_state = COALESCE(excluded.flag_state, flag_state),
                    destination = COALESCE(excluded.destination, destination),
                    eta = COALESCE(excluded.eta, eta),
                    draught = COALESCE(excluded.draught, draught),
                    nav_status = COALESCE(excluded.nav_status, nav_status),
                    last_updated = excluded.last_updated
            ''', (mmsi, name, ship_type, length, beam, imo, call_sign, flag_state,
                  destination, eta, draught, nav_status, timestamp))
            
            _db_conn.commit()
            print(f"✓ Saved: MMSI {mmsi} - {name or 'Unknown'} ({flag_state or 'Unknown'})")
            return
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < DB_MAX_RETRIES - 1:
                time.sleep(DB_RETRY_BACKOFF_BASE * (attempt + 1))
                continue
            print(f"Database error saving vessel {mmsi}: {e}")
            return
        except Exception as e:
            print(f"Error saving vessel {mmsi}: {e}")
            return


def print_stats() -> None:
    """
    Print periodic statistics about collection progress.
    
    Displays every STATS_PRINT_INTERVAL_SECONDS (300s = 5 minutes):
        - Total messages processed
        - Total vessels in database
        - Vessels with dimension data
    """
    global _message_count, _last_stats_time, _db_conn
    
    current_time = time.time()
    if _last_stats_time is None:
        _last_stats_time = current_time
        return
    
    if current_time - _last_stats_time < STATS_PRINT_INTERVAL_SECONDS:
        return
    
    try:
        cursor = _db_conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM vessels_static')
        total_vessels = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM vessels_static WHERE length IS NOT NULL AND length > 0')
        vessels_with_dimensions = cursor.fetchone()[0]
        
        elapsed_minutes = int((current_time - _last_stats_time) / 60)
        
        print(f"\n{'=' * 60}")
        print(f"[STATS] Messages processed: {_message_count}")
        print(f"[STATS] Total vessels in DB: {total_vessels}")
        print(f"[STATS] Vessels with dimensions: {vessels_with_dimensions}")
        print(f"[STATS] Uptime: {elapsed_minutes} minutes")
        print(f"{'=' * 60}\n")
    except Exception as e:
        print(f"Error printing stats: {e}")
    
    _last_stats_time = current_time


def process_ais_message(ws, message: str) -> None:
    """
    Process incoming AIS message from WebSocket.
    
    Handles three message types:
        1. ShipStaticData (Type 5) - Full vessel data with IMO
        2. StaticDataReport (Type 24) - Class B transponders
        3. PositionReport (Types 1-3) - Catch vessels already at sea
    
    Args:
        ws: WebSocket instance
        message: Raw JSON message string
    """
    global _message_count, _db_conn
    
    try:
        _message_count += 1
        
        # Print stats periodically
        if _message_count % STATS_MESSAGE_INTERVAL == 0:
            print_stats()
        
        data = json.loads(message)
        
        # Check for server errors
        if "error" in data or "Error" in data:
            print(f"[ERROR] Server error: {data}")
            return
        
        message_type = data.get("MessageType")
        
        # Route to appropriate parser
        if message_type == "ShipStaticData":
            vessel_data = parse_ship_static_data(data)
            _handle_vessel_data(vessel_data, "ShipStaticData")
            
        elif message_type == "StaticDataReport":
            vessel_data = parse_static_data_report(data)
            _handle_vessel_data(vessel_data, "StaticDataReport")
            
        elif message_type == "PositionReport":
            vessel_data = parse_position_report(data)
            _handle_position_report(vessel_data)
            
    except json.JSONDecodeError:
        print(f"Received non-JSON message: {message[:100]}")
    except Exception as e:
        print(f"Error processing message: {e}")


def _handle_vessel_data(vessel_data: Dict[str, Any], source: str) -> None:
    """
    Handle parsed vessel data from static messages.
    
    Args:
        vessel_data: Parsed vessel dictionary
        source: Message type source for logging
    """
    mmsi = vessel_data.get("mmsi")
    name = vessel_data.get("name")
    length = vessel_data.get("length")
    ship_type = vessel_data.get("ship_type")
    
    print(f"\n--- {source} Received ---")
    print(f"  MMSI: {mmsi}")
    print(f"  Name: {name}")
    print(f"  Type: {ship_type}")
    print(f"  Length: {length}m")
    print(f"  Beam: {vessel_data.get('beam')}m")
    print(f"  IMO: {vessel_data.get('imo')}")
    print("-" * 40)
    
    if should_save_vessel(vessel_data, MIN_VESSEL_LENGTH_METERS, MIN_SHIP_TYPE_CODE, MAX_SHIP_TYPE_CODE):
        save_vessel_data(
            mmsi=mmsi,
            name=name,
            ship_type=ship_type,
            length=length,
            beam=vessel_data.get("beam"),
            imo=vessel_data.get("imo"),
            call_sign=vessel_data.get("call_sign"),
            destination=vessel_data.get("destination"),
            eta=vessel_data.get("eta"),
            draught=vessel_data.get("draught"),
            nav_status=vessel_data.get("nav_status")
        )
        print(f"✓ Saved (type {ship_type}, {length}m)")
    else:
        reason = f"length {length}m < {MIN_VESSEL_LENGTH_METERS}m" if length and length < MIN_VESSEL_LENGTH_METERS else f"type {ship_type} not in range {MIN_SHIP_TYPE_CODE}-{MAX_SHIP_TYPE_CODE}"
        print(f"✗ Skipped ({reason})")


def _handle_position_report(vessel_data: Dict[str, Any]) -> None:
    """
    Handle position report - only save if vessel doesn't exist yet.
    
    This catches vessels already in the Atlantic that we haven't seen static data for.
    
    Args:
        vessel_data: Parsed vessel dictionary (minimal data)
    """
    mmsi = vessel_data.get("mmsi")
    ship_type = vessel_data.get("ship_type")
    
    if not mmsi or not ship_type:
        return
    
    if not (MIN_SHIP_TYPE_CODE <= ship_type <= MAX_SHIP_TYPE_CODE):
        return
    
    # Check if vessel already exists
    try:
        cursor = _db_conn.cursor()
        cursor.execute('SELECT mmsi FROM vessels_static WHERE mmsi = ?', (mmsi,))
        exists = cursor.fetchone()
        
        if not exists:
            save_vessel_data(
                mmsi=mmsi,
                name=vessel_data.get("name"),
                ship_type=ship_type,
                length=None,
                beam=None,
                imo=None,
                call_sign=None
            )
            print(f"✓ Added from PositionReport: {mmsi} - {vessel_data.get('name') or 'Unknown'} (type {ship_type})")
    except Exception as e:
        print(f"Error checking vessel existence: {e}")


def on_error(ws, error) -> None:
    """
    WebSocket error handler.
    
    Only logs critical errors, ignoring normal connection drops.
    """
    error_str = str(error)
    if "Connection to remote host was lost" not in error_str:
        print(f"### Error: {error} ###")
        print(f"### Error Type: {type(error).__name__} ###")


def on_close(ws, close_status_code, close_msg) -> None:
    """
    WebSocket close handler.
    
    Commits pending transactions but keeps connection open for reconnect.
    """
    global _db_conn
    
    print(f"\n### WebSocket Closed: {close_status_code} - {close_msg} ###")
    
    if _db_conn:
        try:
            _db_conn.commit()
            print("Database transactions committed.")
        except Exception as e:
            print(f"Error committing database: {e}")


def on_open(ws) -> None:
    """
    WebSocket open handler.
    
    Sends subscription message with Atlantic bounding box.
    """
    global _api_key
    
    print("WebSocket connection opened. Sending subscription message...")
    
    subscribe_message = {
        "APIKey": _api_key,
        "BoundingBoxes": [[
            BOUNDING_BOX_SOUTHWEST,  # Florida, Caribbean
            BOUNDING_BOX_NORTHEAST   # Arctic Norway, Baltic Sea
        ]]
    }
    
    print(f"Subscription: Atlantic coverage ({BOUNDING_BOX_SOUTHWEST} to {BOUNDING_BOX_NORTHEAST})")
    ws.send(json.dumps(subscribe_message))
    print("Subscription sent.\n")


def main() -> None:
    """
    Main entry point - connects to AISStream and runs collection loop.
    
    Features automatic reconnection with exponential backoff.
    """
    global _api_key, _db_conn
    
    try:
        # Initialize
        print("Loading API key...")
        _api_key = load_api_key()
        print("API key loaded.\n")
        
        print("Initializing database...")
        _db_conn = init_database()
        print("Database ready.\n")
        
        # Reconnection loop
        reconnect_delay = INITIAL_RECONNECT_DELAY_SECONDS
        
        while True:
            try:
                print("Connecting to AISStream...")
                print("Press Ctrl+C to stop.\n")
                
                ws_app = websocket.WebSocketApp(
                    WEBSOCKET_URL,
                    on_open=on_open,
                    on_message=process_ais_message,
                    on_error=on_error,
                    on_close=on_close
                )
                
                ws_app.run_forever()
                
                # Connection closed - reconnect with backoff
                print(f"\n[RECONNECT] Connection lost. Reconnecting in {reconnect_delay}s...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY_SECONDS)
                
            except KeyboardInterrupt:
                print("\n\nScript interrupted by user.")
                break
            except Exception as e:
                print(f"\n[ERROR] Unexpected error: {e}")
                print(f"[RECONNECT] Retrying in {reconnect_delay}s...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY_SECONDS)
    
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user.")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
    finally:
        if _db_conn:
            try:
                _db_conn.commit()
                _db_conn.close()
                print("Database connection closed.")
            except:
                pass
        print("Script finished.")


if __name__ == "__main__":
    main()
