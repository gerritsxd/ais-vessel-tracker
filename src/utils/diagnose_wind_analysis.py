"""
Diagnostic script to verify wind analysis is working correctly.
Shows step-by-step what's happening.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from src.services.wind_analysis import WindAnalysisService, WindPositionMatcher, WindDataFetcher

DB_NAME = "vessel_static_data.db"


def main():
    """Diagnose wind analysis process."""
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print("="*80)
    print("WIND ANALYSIS DIAGNOSTIC")
    print("="*80)
    
    conn = sqlite3.connect(str(db_path), timeout=60)
    cursor = conn.cursor()
    
    # Step 1: Check how many vessels have position data
    print("\n1. CHECKING VESSEL POSITION DATA")
    print("-" * 80)
    cursor.execute('''
        SELECT COUNT(DISTINCT mmsi) as vessel_count,
               COUNT(*) as total_positions,
               MIN(timestamp) as earliest,
               MAX(timestamp) as latest
        FROM vessel_positions
    ''')
    stats = cursor.fetchone()
    print(f"   Vessels with position data: {stats[0]:,}")
    print(f"   Total position records: {stats[1]:,}")
    print(f"   Date range: {stats[2]} to {stats[3]}")
    
    # Step 2: Check vessels with wind analysis results
    print("\n2. CHECKING WIND ANALYSIS RESULTS")
    print("-" * 80)
    cursor.execute('''
        SELECT COUNT(*) as analyzed_count,
               SUM(matched_positions) as total_matched,
               COUNT(CASE WHEN wind_assistance_potential = 'high' THEN 1 END) as high_potential,
               COUNT(CASE WHEN wind_assistance_potential = 'medium' THEN 1 END) as medium_potential
        FROM vessel_wind_alignment
    ''')
    results = cursor.fetchone()
    print(f"   Vessels analyzed: {results[0]}")
    print(f"   Total positions matched with wind: {results[1]:,}")
    print(f"   High potential: {results[2]}")
    print(f"   Medium potential: {results[3]}")
    
    # Step 3: Test wind data fetching for a sample position
    print("\n3. TESTING WIND DATA FETCHING")
    print("-" * 80)
    cursor.execute('''
        SELECT latitude, longitude, cog, timestamp
        FROM vessel_positions
        WHERE cog IS NOT NULL
        LIMIT 1
    ''')
    sample = cursor.fetchone()
    if sample:
        lat, lon, cog, timestamp = sample
        print(f"   Sample position:")
        print(f"     Location: {lat:.4f}, {lon:.4f}")
        print(f"     Course (COG): {cog}°")
        print(f"     Timestamp: {timestamp}")
        
        fetcher = WindDataFetcher(verbose=True)
        wind_data = fetcher.fetch_wind_data(lat, lon, timestamp)
        
        if wind_data:
            print(f"\n   ✓ Wind data fetched:")
            print(f"     Wind speed: {wind_data['wind_speed']} m/s")
            print(f"     Wind direction: {wind_data['wind_direction']}°")
            print(f"     Provider: {wind_data['provider']}")
            
            # Calculate alignment
            from src.services.wind_analysis import WindAlignmentAnalyzer
            analyzer = WindAlignmentAnalyzer()
            angle = analyzer.calculate_alignment_angle(cog, wind_data['wind_direction'])
            score = analyzer.calculate_wind_assistance_score(angle)
            favorable = analyzer.is_favorable_wind(angle)
            
            print(f"\n   ✓ Comparison:")
            print(f"     Vessel course: {cog}°")
            print(f"     Wind direction: {wind_data['wind_direction']}°")
            print(f"     Alignment angle: {angle:.1f}°")
            print(f"     Wind assistance score: {score:.1f}/100")
            print(f"     Favorable wind: {'YES ✓' if favorable else 'NO ✗'}")
        else:
            print(f"   ✗ Failed to fetch wind data")
    
    # Step 4: Show detailed results for high-potential vessels
    print("\n4. DETAILED RESULTS FOR HIGH-POTENTIAL VESSELS")
    print("-" * 80)
    cursor.execute('''
        SELECT w.mmsi, v.name, w.matched_positions, w.favorable_wind_count,
               w.favorable_wind_percentage, w.average_alignment_angle,
               w.average_wind_assistance_score, w.average_wind_speed
        FROM vessel_wind_alignment w
        LEFT JOIN vessels_static v ON w.mmsi = v.mmsi
        WHERE w.wind_assistance_potential = 'high'
        ORDER BY w.average_wind_assistance_score DESC
    ''')
    
    for row in cursor.fetchall():
        mmsi, name, matched, favorable_count, favorable_pct, avg_angle, score, avg_wind = row
        print(f"\n   MMSI: {mmsi} - {name or 'Unknown'}")
        print(f"     Positions analyzed: {matched}")
        print(f"     Favorable wind positions: {favorable_count} ({favorable_pct:.1f}%)")
        print(f"     Average alignment angle: {avg_angle:.1f}°")
        print(f"     Average wind assistance score: {score:.1f}/100")
        print(f"     Average wind speed: {avg_wind:.1f} m/s")
    
    # Step 5: Show sample of matched positions for one vessel
    print("\n5. SAMPLE POSITION-WIND MATCHES (First High-Potential Vessel)")
    print("-" * 80)
    cursor.execute('''
        SELECT mmsi FROM vessel_wind_alignment 
        WHERE wind_assistance_potential = 'high'
        ORDER BY average_wind_assistance_score DESC
        LIMIT 1
    ''')
    top_mmsi = cursor.fetchone()
    
    if top_mmsi:
        mmsi = top_mmsi[0]
        print(f"   Analyzing MMSI: {mmsi}")
        
        service = WindAnalysisService(db_path=db_path, verbose=False)
        matcher = WindPositionMatcher(db_path, service.wind_fetcher, verbose=False)
        
        # Get a few matched positions
        matched = matcher.match_vessel_positions(mmsi, max_positions=5)
        
        if matched:
            print(f"\n   Sample matches:")
            for i, record in enumerate(matched[:3], 1):
                if record.get('matched'):
                    from src.services.wind_analysis import WindAlignmentAnalyzer
                    analyzer = WindAlignmentAnalyzer()
                    angle = analyzer.calculate_alignment_angle(
                        record['cog'], 
                        record['wind_direction']
                    )
                    print(f"\n   Match {i}:")
                    print(f"     Position: {record['latitude']:.4f}, {record['longitude']:.4f}")
                    print(f"     Vessel COG: {record['cog']}°")
                    print(f"     Wind direction: {record['wind_direction']}°")
                    print(f"     Wind speed: {record['wind_speed']} m/s")
                    print(f"     Alignment angle: {angle:.1f}°")
                    print(f"     Favorable: {'YES ✓' if analyzer.is_favorable_wind(angle) else 'NO ✗'}")
        else:
            print(f"   No matched positions found")
    
    conn.close()
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()

