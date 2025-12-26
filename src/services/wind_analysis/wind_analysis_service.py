"""
Wind Analysis Service

Main orchestrator for wind alignment analysis.
Coordinates data fetching, matching, analysis, and storage.
"""

import sqlite3
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta
from .wind_data_fetcher import WindDataFetcher
from .wind_position_matcher import WindPositionMatcher
from .wind_alignment_analyzer import WindAlignmentAnalyzer


class WindAnalysisService:
    """
    Main service for analyzing vessel wind alignment.
    
    Orchestrates the complete workflow:
    1. Fetch vessel positions
    2. Match with wind data
    3. Analyze alignment
    4. Store results
    """
    
    def __init__(self, db_path: Path, api_key: Optional[str] = None, verbose: bool = False):
        """
        Initialize wind analysis service.
        
        Args:
            db_path: Path to vessel database
            api_key: Optional API key for weather services
            verbose: Enable verbose logging
        """
        self.db_path = db_path
        self.verbose = verbose
        
        # Initialize components
        self.wind_fetcher = WindDataFetcher(api_key=api_key, verbose=verbose)
        self.position_matcher = WindPositionMatcher(db_path, self.wind_fetcher, verbose=verbose)
        self.analyzer = WindAlignmentAnalyzer()
        
        # Initialize database schema
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables for wind analysis results."""
        conn = sqlite3.connect(str(self.db_path), timeout=60)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        try:
            # Create wind alignment results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vessel_wind_alignment (
                    mmsi INTEGER PRIMARY KEY,
                    total_positions INTEGER DEFAULT 0,
                    matched_positions INTEGER DEFAULT 0,
                    favorable_wind_count INTEGER DEFAULT 0,
                    favorable_wind_percentage REAL DEFAULT 0.0,
                    average_alignment_angle REAL,
                    average_wind_assistance_score REAL DEFAULT 0.0,
                    average_wind_speed REAL DEFAULT 0.0,
                    max_wind_speed REAL DEFAULT 0.0,
                    wind_assistance_potential TEXT DEFAULT 'unknown',
                    last_analyzed TEXT,
                    FOREIGN KEY (mmsi) REFERENCES vessels_static(mmsi)
                )
            ''')
            
            # Create index
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_wind_alignment_potential 
                ON vessel_wind_alignment(wind_assistance_potential)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_wind_alignment_score 
                ON vessel_wind_alignment(average_wind_assistance_score DESC)
            ''')
            
            conn.commit()
            
            if self.verbose:
                print("✓ Wind analysis database initialized")
                
        finally:
            conn.close()
    
    def analyze_vessel(
        self,
        mmsi: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_positions: int = 1000
    ) -> Dict:
        """
        Analyze wind alignment for a single vessel.
        
        Args:
            mmsi: Vessel MMSI
            start_date: Start date (ISO format, optional)
            end_date: End date (ISO format, optional)
            max_positions: Maximum positions to analyze
        
        Returns:
            Analysis results dictionary
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Analyzing vessel MMSI: {mmsi}")
            print(f"{'='*60}")
        
        # Step 1: Match positions with wind data
        matched_records = self.position_matcher.match_vessel_positions(
            mmsi,
            start_date=start_date,
            end_date=end_date,
            max_positions=max_positions
        )
        
        if not matched_records:
            if self.verbose:
                print(f"No position data found for MMSI {mmsi}")
            return {}
        
        # Step 2: Analyze alignment
        analysis = self.analyzer.analyze_vessel_alignment(matched_records)
        
        # Step 3: Store results
        self._store_results(mmsi, analysis)
        
        if self.verbose:
            print(f"✓ Analysis complete:")
            print(f"  Matched positions: {analysis['matched_positions']}/{analysis['total_positions']}")
            print(f"  Favorable wind: {analysis['favorable_wind_percentage']:.1f}%")
            print(f"  Average score: {analysis['average_wind_assistance_score']:.1f}/100")
            print(f"  Potential: {analysis['wind_assistance_potential']}")
        
        return analysis
    
    def analyze_multiple_vessels(
        self,
        mmsi_list: List[int],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_positions_per_vessel: int = 500
    ) -> Dict[int, Dict]:
        """
        Analyze wind alignment for multiple vessels.
        
        Returns:
            Dict mapping MMSI to analysis results
        """
        results = {}
        
        for i, mmsi in enumerate(mmsi_list, 1):
            if self.verbose:
                print(f"\n[{i}/{len(mmsi_list)}] Processing MMSI {mmsi}")
            
            try:
                analysis = self.analyze_vessel(
                    mmsi,
                    start_date=start_date,
                    end_date=end_date,
                    max_positions=max_positions_per_vessel
                )
                results[mmsi] = analysis
            except Exception as e:
                if self.verbose:
                    print(f"✗ Error analyzing MMSI {mmsi}: {e}")
                results[mmsi] = {'error': str(e)}
        
        return results
    
    def analyze_all_vessels(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_positions_per_vessel: int = 500,
        limit: Optional[int] = None
    ) -> Dict[int, Dict]:
        """
        Analyze all vessels in database.
        
        Args:
            start_date: Start date (ISO format, optional)
            end_date: End date (ISO format, optional)
            max_positions_per_vessel: Max positions per vessel
            limit: Limit number of vessels to analyze (for testing)
        
        Returns:
            Dict mapping MMSI to analysis results
        """
        conn = sqlite3.connect(str(self.db_path), timeout=60)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        try:
            query = 'SELECT DISTINCT mmsi FROM vessel_positions'
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query)
            mmsi_list = [row[0] for row in cursor.fetchall()]
            
            if self.verbose:
                print(f"Found {len(mmsi_list)} vessels with position data")
            
            return self.analyze_multiple_vessels(
                mmsi_list,
                start_date=start_date,
                end_date=end_date,
                max_positions_per_vessel=max_positions_per_vessel
            )
            
        finally:
            conn.close()
    
    def _store_results(self, mmsi: int, analysis: Dict):
        """Store analysis results in database."""
        conn = sqlite3.connect(str(self.db_path), timeout=60)
        conn.execute('PRAGMA journal_mode=WAL')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO vessel_wind_alignment (
                    mmsi, total_positions, matched_positions, favorable_wind_count,
                    favorable_wind_percentage, average_alignment_angle,
                    average_wind_assistance_score, average_wind_speed,
                    max_wind_speed, wind_assistance_potential, last_analyzed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                mmsi,
                analysis['total_positions'],
                analysis['matched_positions'],
                analysis['favorable_wind_count'],
                analysis['favorable_wind_percentage'],
                analysis['average_alignment_angle'],
                analysis['average_wind_assistance_score'],
                analysis['average_wind_speed'],
                analysis['max_wind_speed'],
                analysis['wind_assistance_potential'],
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def get_vessel_results(self, mmsi: int) -> Optional[Dict]:
        """Get stored analysis results for a vessel."""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM vessel_wind_alignment WHERE mmsi = ?
            ''', (mmsi,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
            
        finally:
            conn.close()
    
    def get_top_vessels_by_potential(self, limit: int = 100) -> List[Dict]:
        """Get vessels with highest wind assistance potential."""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT w.*, v.name, v.ship_type, v.length, v.flag_state
                FROM vessel_wind_alignment w
                LEFT JOIN vessels_static v ON w.mmsi = v.mmsi
                WHERE w.wind_assistance_potential IN ('high', 'medium')
                ORDER BY w.average_wind_assistance_score DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        finally:
            conn.close()

