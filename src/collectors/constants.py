"""
Configuration constants for AIS data collection.

This module centralizes all configuration values to avoid magic numbers
and improve maintainability.
"""

# Database configuration
DATABASE_NAME = "vessel_static_data.db"
API_KEY_FILENAME = "config/aisstream_keys"

# AISStream WebSocket endpoint
WEBSOCKET_URL = "wss://stream.aisstream.io/v0/stream"

# Vessel filtering criteria
MIN_VESSEL_LENGTH_METERS = 100  # Only track vessels >= 100m
MIN_SHIP_TYPE_CODE = 70  # Cargo ships start at 70
MAX_SHIP_TYPE_CODE = 89  # Tankers end at 89

# Statistics and reporting
STATS_PRINT_INTERVAL_SECONDS = 300  # Print stats every 5 minutes
STATS_MESSAGE_INTERVAL = 1000  # Print stats every N messages

# Database retry configuration
DB_MAX_RETRIES = 3
DB_RETRY_BACKOFF_BASE = 0.1  # seconds

# WebSocket reconnection
INITIAL_RECONNECT_DELAY_SECONDS = 5
MAX_RECONNECT_DELAY_SECONDS = 60

# Geographic coverage (Atlantic Ocean + surrounding areas)
# Southwest: Florida, Caribbean
# Northeast: Arctic Norway, Baltic Sea
BOUNDING_BOX_SOUTHWEST = [25.0, -80.0]
BOUNDING_BOX_NORTHEAST = [75.0, 35.0]
