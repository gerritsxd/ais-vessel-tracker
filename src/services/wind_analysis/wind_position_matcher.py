"""
Wind Position Matcher

Matches vessel position data with historical wind data.
"""

import sqlite3
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta
from .wind_data_fetcher import WindDataFetcher


class WindPositionMatcher:
    """
    Matches vessel positions with wind data.
    
    Fetches historical wind data for each vessel position
    and creates matched records for analysis.
    """
    
    def __init__(self, db_path: Path, wind_fetcher: WindDataFetcher, verbose: bool = False):
        """
        Initialize wind position matcher.
        
        Args:
            db_path: Path to vessel database
            wind_fetcher: WindDataFetcher instance
            verbose: Enable verbose logging
        """
        self.db_path = db_path
        self.wind_fetcher = wind_fetcher
        self.verbose = verbose
    
    def match_vessel_positions(
        self,
        mmsi: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_positions: int = 1000
    ) -> List[Dict]:
        """
        Match vessel positions with wind data.
        
        Args:
            mmsi: Vessel MMSI
            start_date: Start date (ISO format, optional)
            end_date: End date (ISO format, optional)
            max_positions: Maximum number of positions to process
        
        Returns:
            List of matched records: [{
                'mmsi': int,
                'latitude': float,
                'longitude': float,
                'cog': float,  # Course over ground (degrees)
                'sog': float,  # Speed over ground (knots)
                'timestamp': str,
                'wind_speed': float,  # m/s
                'wind_direction': float,  # degrees (0-360)
                'wind_gust': float,  # m/s (optional)
                'matched': bool
            }]
        """
        conn = sqlite3.connect(str(self.db_path), timeout=60)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        try:
            # Build query
            query = '''
                SELECT latitude, longitude, sog, cog, timestamp
                FROM vessel_positions
                WHERE mmsi = ?
            '''
            params = [mmsi]
            
            if start_date:
                query += ' AND timestamp >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND timestamp <= ?'
                params.append(end_date)
            
            query += ' ORDER BY timestamp ASC LIMIT ?'
            params.append(max_positions)
            
            cursor.execute(query, params)
            positions = cursor.fetchall()
            
            if self.verbose:
                print(f"Found {len(positions)} positions for MMSI {mmsi}")
            
            matched_records = []
            
            for lat, lon, sog, cog, timestamp in positions:
                # Skip if missing critical data
                if lat is None or lon is None or cog is None:
                    continue
                
                # Fetch wind data
                wind_data = self.wind_fetcher.fetch_wind_data(lat, lon, timestamp)
                
                if wind_data:
                    matched_records.append({
                        'mmsi': mmsi,
                        'latitude': lat,
                        'longitude': lon,
                        'cog': cog,  # Course over ground (degrees, 0-360)
                        'sog': sog,  # Speed over ground (knots)
                        'timestamp': timestamp,
                        'wind_speed': wind_data['wind_speed'],
                        'wind_direction': wind_data['wind_direction'],
                        'wind_gust': wind_data.get('wind_gust'),
                        'matched': True
                    })
                else:
                    # Record position even if wind data unavailable
                    matched_records.append({
                        'mmsi': mmsi,
                        'latitude': lat,
                        'longitude': lon,
                        'cog': cog,
                        'sog': sog,
                        'timestamp': timestamp,
                        'wind_speed': None,
                        'wind_direction': None,
                        'wind_gust': None,
                        'matched': False
                    })
            
            return matched_records
            
        finally:
            conn.close()
    
    def match_multiple_vessels(
        self,
        mmsi_list: List[int],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_positions_per_vessel: int = 500
    ) -> Dict[int, List[Dict]]:
        """
        Match positions for multiple vessels.
        
        Returns:
            Dict mapping MMSI to list of matched records
        """
        results = {}
        
        for i, mmsi in enumerate(mmsi_list, 1):
            if self.verbose:
                print(f"Processing vessel {i}/{len(mmsi_list)}: MMSI {mmsi}")
            
            results[mmsi] = self.match_vessel_positions(
                mmsi,
                start_date=start_date,
                end_date=end_date,
                max_positions=max_positions_per_vessel
            )
        
        return results

