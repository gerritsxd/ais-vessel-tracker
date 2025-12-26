"""
Run Wind Alignment Analysis

One-time script to analyze vessel wind alignment.
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.wind_analysis import WindAnalysisService

DB_NAME = "vessel_static_data.db"


def main():
    """Run wind analysis for vessels."""
    # Determine database path (check VPS location first)
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print(f"   Checked: {project_root / 'data' / DB_NAME}")
        print(f"   Checked: {project_root / DB_NAME}")
        sys.exit(1)
    
    print("="*80)
    print("WIND ALIGNMENT ANALYSIS")
    print("="*80)
    print(f"Database: {db_path}")
    print(f"Working directory: {project_root}")
    print()
    
    # Initialize service
    # Note: Open-Meteo doesn't require API key, but you can add OpenWeatherMap key if needed
    api_key = None  # Set to your OpenWeatherMap API key if using that provider
    
    # Check if running as systemd service (less verbose)
    verbose = os.environ.get('SYSTEMD_SERVICE') != '1'
    
    service = WindAnalysisService(
        db_path=db_path,
        api_key=api_key,
        verbose=verbose
    )
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            # Analyze all vessels
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
            print(f"Analyzing all vessels (limit: {limit or 'none'})...")
            
            start_time = time.time()
            results = service.analyze_all_vessels(limit=limit)
            elapsed = time.time() - start_time
            
            print(f"\n{'='*80}")
            print(f"✓ Analysis complete!")
            print(f"  Vessels analyzed: {len(results)}")
            print(f"  Time elapsed: {elapsed:.1f} seconds")
            print(f"{'='*80}")
            
            # Print summary statistics
            if results:
                high_potential = sum(1 for r in results.values() if r.get('wind_assistance_potential') == 'high')
                medium_potential = sum(1 for r in results.values() if r.get('wind_assistance_potential') == 'medium')
                print(f"\nSummary:")
                print(f"  High potential: {high_potential}")
                print(f"  Medium potential: {medium_potential}")
                
        elif sys.argv[1].isdigit():
            # Analyze specific MMSI
            mmsi = int(sys.argv[1])
            print(f"Analyzing vessel MMSI: {mmsi}...")
            results = service.analyze_vessel(mmsi)
            print(f"\n✓ Analysis complete")
        else:
            print("Usage:")
            print("  python run_wind_analysis.py <MMSI>     # Analyze specific vessel")
            print("  python run_wind_analysis.py --all [N] # Analyze all vessels (optional limit)")
            sys.exit(1)
    else:
        print("Usage:")
        print("  python run_wind_analysis.py <MMSI>     # Analyze specific vessel")
        print("  python run_wind_analysis.py --all [N] # Analyze all vessels (optional limit)")
        print()
        print("Example:")
        print("  python run_wind_analysis.py 211281610  # Analyze specific vessel")
        print("  python run_wind_analysis.py --all 10   # Analyze first 10 vessels")
        sys.exit(1)


if __name__ == "__main__":
    main()

