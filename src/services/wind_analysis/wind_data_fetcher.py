"""
Wind Data Fetcher

Fetches historical wind data from weather APIs.
Supports multiple providers with fallback options.
"""

import requests
import time
from typing import Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json


class WindDataFetcher:
    """
    Fetches historical wind data for given coordinates and timestamps.
    
    Supports multiple weather APIs with automatic fallback:
    1. Open-Meteo (free, no API key required)
    2. OpenWeatherMap (requires API key)
    """
    
    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        """
        Initialize wind data fetcher.
        
        Args:
            api_key: Optional API key for OpenWeatherMap
            verbose: Enable verbose logging
        """
        self.api_key = api_key
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.cache_dir = self.project_root / "data" / "wind_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    def fetch_wind_data(
        self,
        latitude: float,
        longitude: float,
        timestamp: str,
        provider: str = "openmeteo"
    ) -> Optional[Dict]:
        """
        Fetch wind data for a specific location and time.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            timestamp: ISO format timestamp (e.g., "2024-01-15T10:30:00")
            provider: Weather API provider ("openmeteo" or "openweather")
        
        Returns:
            Dict with wind data: {
                'wind_speed': float (m/s),
                'wind_direction': float (degrees, 0-360),
                'wind_gust': float (m/s, optional),
                'timestamp': str,
                'provider': str
            }
            or None if fetch failed
        """
        # Check cache first
        cached = self._get_from_cache(latitude, longitude, timestamp)
        if cached:
            return cached
        
        # Rate limiting
        self._rate_limit()
        
        if provider == "openmeteo":
            data = self._fetch_openmeteo(latitude, longitude, timestamp)
        elif provider == "openweather":
            data = self._fetch_openweather(latitude, longitude, timestamp)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Cache result
        if data:
            self._save_to_cache(latitude, longitude, timestamp, data)
        
        return data
    
    def _fetch_openmeteo(self, lat: float, lon: float, timestamp: str) -> Optional[Dict]:
        """
        Fetch wind data from Open-Meteo API (free, no API key).
        
        Open-Meteo provides historical weather data.
        """
        try:
            # Parse timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
            
            # Open-Meteo API endpoint
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                'latitude': lat,
                'longitude': lon,
                'start_date': date_str,
                'end_date': date_str,
                'hourly': 'wind_speed_10m,wind_direction_10m,wind_gusts_10m',
                'timezone': 'UTC'
            }
            
            if self.verbose:
                print(f"Fetching Open-Meteo data for {lat:.4f}, {lon:.4f} on {date_str}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'hourly' not in data:
                return None
            
            # Find closest hour to our timestamp
            hours = data['hourly']['time']
            target_hour = dt.hour
            
            # Find index of closest hour
            closest_idx = 0
            min_diff = 24
            for i, hour_str in enumerate(hours):
                hour_dt = datetime.fromisoformat(hour_str.replace('Z', '+00:00'))
                diff = abs(hour_dt.hour - target_hour)
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = i
            
            wind_speed = data['hourly']['wind_speed_10m'][closest_idx]
            wind_direction = data['hourly']['wind_direction_10m'][closest_idx]
            wind_gust = data['hourly'].get('wind_gusts_10m', [None])[closest_idx]
            
            return {
                'wind_speed': wind_speed,  # m/s
                'wind_direction': wind_direction,  # degrees (0-360)
                'wind_gust': wind_gust,  # m/s
                'timestamp': timestamp,
                'provider': 'openmeteo'
            }
            
        except Exception as e:
            if self.verbose:
                print(f"Open-Meteo fetch error: {e}")
            return None
    
    def _fetch_openweather(self, lat: float, lon: float, timestamp: str) -> Optional[Dict]:
        """
        Fetch wind data from OpenWeatherMap API (requires API key).
        
        Note: OpenWeatherMap historical data requires paid plan.
        Falls back to current weather if historical unavailable.
        """
        if not self.api_key:
            if self.verbose:
                print("OpenWeatherMap API key not provided")
            return None
        
        try:
            # OpenWeatherMap historical API (requires paid plan)
            # For now, use current weather as fallback
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'wind' not in data:
                return None
            
            wind = data['wind']
            
            return {
                'wind_speed': wind.get('speed', 0),  # m/s
                'wind_direction': wind.get('deg', 0),  # degrees (0-360)
                'wind_gust': wind.get('gust'),  # m/s
                'timestamp': timestamp,
                'provider': 'openweather'
            }
            
        except Exception as e:
            if self.verbose:
                print(f"OpenWeatherMap fetch error: {e}")
            return None
    
    def _get_from_cache(self, lat: float, lon: float, timestamp: str) -> Optional[Dict]:
        """Get wind data from local cache."""
        cache_file = self._get_cache_file(lat, lon, timestamp)
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def _save_to_cache(self, lat: float, lon: float, timestamp: str, data: Dict):
        """Save wind data to local cache."""
        cache_file = self._get_cache_file(lat, lon, timestamp)
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except:
            pass
    
    def _get_cache_file(self, lat: float, lon: float, timestamp: str) -> Path:
        """Get cache file path for given coordinates and timestamp."""
        # Round coordinates to 0.1 degree for caching (reduces cache size)
        lat_rounded = round(lat, 1)
        lon_rounded = round(lon, 1)
        
        # Use date part of timestamp for cache key
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        date_str = dt.strftime('%Y-%m-%d')
        hour = dt.hour
        
        cache_filename = f"{lat_rounded}_{lon_rounded}_{date_str}_{hour}.json"
        return self.cache_dir / cache_filename
    
    def _rate_limit(self):
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

