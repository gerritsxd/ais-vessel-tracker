"""
Environment Variable Loader

Loads configuration from .env file with validation and defaults.
"""

import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv


class Config:
    """
    Application configuration loaded from environment variables.
    
    Provides typed access to all configuration values with sensible defaults.
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration from .env file.
        
        Args:
            env_file: Path to .env file (default: .env in project root)
        """
        # Load .env file
        if env_file:
            load_dotenv(env_file)
        else:
            project_root = Path(__file__).parent.parent
            load_dotenv(project_root / ".env")
    
    # ========================================================================
    # API Keys
    # ========================================================================
    
    @property
    def ais_api_keys(self) -> List[str]:
        """Get all AISStream API keys from environment."""
        keys = []
        i = 1
        while True:
            key = os.getenv(f'AIS_API_KEY_{i}')
            if not key:
                break
            keys.append(key)
            i += 1
        return keys
    
    @property
    def datalastic_api_key(self) -> Optional[str]:
        """Get Datalastic API key."""
        return os.getenv('DATALASTIC_API_KEY')
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        """Get Google Gemini API key."""
        return os.getenv('GOOGLE_GEMINI_API_KEY')
    
    # ========================================================================
    # Database Configuration
    # ========================================================================
    
    @property
    def db_path(self) -> str:
        """Get database file path."""
        return os.getenv('DB_PATH', 'data/vessel_static_data.db')
    
    @property
    def db_timeout(self) -> int:
        """Get database timeout in seconds."""
        return int(os.getenv('DB_TIMEOUT', '30'))
    
    @property
    def db_wal_mode(self) -> bool:
        """Check if WAL mode is enabled."""
        return os.getenv('DB_WAL_MODE', 'true').lower() == 'true'
    
    # ========================================================================
    # Logging Configuration
    # ========================================================================
    
    @property
    def log_level(self) -> str:
        """Get logging level."""
        return os.getenv('LOG_LEVEL', 'INFO').upper()
    
    @property
    def log_to_file(self) -> bool:
        """Check if logging to file is enabled."""
        return os.getenv('LOG_TO_FILE', 'false').lower() == 'true'
    
    @property
    def log_file_path(self) -> str:
        """Get log file path."""
        return os.getenv('LOG_FILE_PATH', 'logs/ais_tracker.log')
    
    # ========================================================================
    # Flask Configuration
    # ========================================================================
    
    @property
    def flask_host(self) -> str:
        """Get Flask server host."""
        return os.getenv('FLASK_HOST', '0.0.0.0')
    
    @property
    def flask_port(self) -> int:
        """Get Flask server port."""
        return int(os.getenv('FLASK_PORT', '5000'))
    
    @property
    def flask_env(self) -> str:
        """Get Flask environment."""
        return os.getenv('FLASK_ENV', 'development')
    
    @property
    def flask_debug(self) -> bool:
        """Check if Flask debug mode is enabled."""
        return os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    @property
    def flask_secret_key(self) -> str:
        """Get Flask secret key."""
        key = os.getenv('FLASK_SECRET_KEY')
        if not key:
            import secrets
            return secrets.token_hex(32)
        return key
    
    # ========================================================================
    # WebSocket Configuration
    # ========================================================================
    
    @property
    def aisstream_ws_url(self) -> str:
        """Get AISStream WebSocket URL."""
        return os.getenv('AISSTREAM_WS_URL', 'wss://stream.aisstream.io/v0/stream')
    
    @property
    def ws_reconnect_delay(self) -> int:
        """Get WebSocket reconnection delay in seconds."""
        return int(os.getenv('WS_RECONNECT_DELAY', '5'))
    
    @property
    def ws_max_reconnect_delay(self) -> int:
        """Get maximum WebSocket reconnection delay in seconds."""
        return int(os.getenv('WS_MAX_RECONNECT_DELAY', '60'))
    
    # ========================================================================
    # Vessel Filtering
    # ========================================================================
    
    @property
    def min_vessel_length(self) -> int:
        """Get minimum vessel length in meters."""
        return int(os.getenv('MIN_VESSEL_LENGTH', '100'))
    
    @property
    def min_ship_type(self) -> int:
        """Get minimum ship type code."""
        return int(os.getenv('MIN_SHIP_TYPE', '70'))
    
    @property
    def max_ship_type(self) -> int:
        """Get maximum ship type code."""
        return int(os.getenv('MAX_SHIP_TYPE', '89'))
    
    # ========================================================================
    # Geographic Coverage
    # ========================================================================
    
    @property
    def bbox_southwest(self) -> tuple[float, float]:
        """Get bounding box southwest corner (lat, lon)."""
        lat = float(os.getenv('BBOX_SW_LAT', '25.0'))
        lon = float(os.getenv('BBOX_SW_LON', '-80.0'))
        return (lat, lon)
    
    @property
    def bbox_northeast(self) -> tuple[float, float]:
        """Get bounding box northeast corner (lat, lon)."""
        lat = float(os.getenv('BBOX_NE_LAT', '75.0'))
        lon = float(os.getenv('BBOX_NE_LON', '35.0'))
        return (lat, lon)
    
    # ========================================================================
    # Feature Flags
    # ========================================================================
    
    @property
    def enable_ai_profiling(self) -> bool:
        """Check if AI profiling is enabled."""
        return os.getenv('ENABLE_AI_PROFILING', 'false').lower() == 'true'
    
    @property
    def enable_web_scraping(self) -> bool:
        """Check if web scraping is enabled."""
        return os.getenv('ENABLE_WEB_SCRAPING', 'false').lower() == 'true'
    
    @property
    def enable_atlantic_tracker(self) -> bool:
        """Check if Atlantic tracker is enabled."""
        return os.getenv('ENABLE_ATLANTIC_TRACKER', 'false').lower() == 'true'
    
    # ========================================================================
    # Validation
    # ========================================================================
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check for required API keys
        if not self.ais_api_keys:
            errors.append("No AISStream API keys found (AIS_API_KEY_1, etc.)")
        
        # Validate numeric ranges
        if self.flask_port < 1 or self.flask_port > 65535:
            errors.append(f"Invalid FLASK_PORT: {self.flask_port} (must be 1-65535)")
        
        if self.min_vessel_length < 0:
            errors.append(f"Invalid MIN_VESSEL_LENGTH: {self.min_vessel_length}")
        
        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_levels:
            errors.append(f"Invalid LOG_LEVEL: {self.log_level} (must be one of {valid_levels})")
        
        return errors
    
    def print_config(self):
        """Print current configuration (masks sensitive values)."""
        print("="*80)
        print("Current Configuration")
        print("="*80)
        
        print("\nAPI Keys:")
        print(f"  AISStream keys: {len(self.ais_api_keys)} configured")
        print(f"  Datalastic key: {'✓ Set' if self.datalastic_api_key else '✗ Not set'}")
        print(f"  Gemini key: {'✓ Set' if self.gemini_api_key else '✗ Not set'}")
        
        print("\nDatabase:")
        print(f"  Path: {self.db_path}")
        print(f"  Timeout: {self.db_timeout}s")
        print(f"  WAL mode: {self.db_wal_mode}")
        
        print("\nLogging:")
        print(f"  Level: {self.log_level}")
        print(f"  To file: {self.log_to_file}")
        
        print("\nFlask:")
        print(f"  Host: {self.flask_host}")
        print(f"  Port: {self.flask_port}")
        print(f"  Environment: {self.flask_env}")
        print(f"  Debug: {self.flask_debug}")
        
        print("\nVessel Filtering:")
        print(f"  Min length: {self.min_vessel_length}m")
        print(f"  Ship types: {self.min_ship_type}-{self.max_ship_type}")
        
        print("\nFeature Flags:")
        print(f"  AI profiling: {self.enable_ai_profiling}")
        print(f"  Web scraping: {self.enable_web_scraping}")
        print(f"  Atlantic tracker: {self.enable_atlantic_tracker}")
        
        print("="*80)


# Global config instance
config = Config()


if __name__ == "__main__":
    """Test configuration loading."""
    cfg = Config()
    
    # Validate
    errors = cfg.validate()
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  ✗ {error}")
    else:
        print("✓ Configuration valid")
    
    print()
    cfg.print_config()
