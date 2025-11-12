"""
Test script for the new search-based GT scraper
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.gt_search_scraper import GTSearchScraper

def test_search_scraper():
    """Test the search-based GT scraper with a few vessels."""
    
    print("="*60)
    print("TESTING SEARCH-BASED GT SCRAPER")
    print("="*60)
    
    # Test with known MMSI numbers
    test_mmsi_list = [
        241499000,  # Example large vessel
        235094321,  # Another example
        636015123,  # Different type
    ]
    
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "vessel_static_data.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Please run ais_collector.py first to create the database.")
        return
    
    scraper = GTSearchScraper(str(db_path))
    
    print(f"Testing search for {len(test_mmsi_list)} MMSI numbers...\n")
    
    for i, mmsi in enumerate(test_mmsi_list):
        print(f"[{i+1}/{len(test_mmsi_list)}] Testing MMSI: {mmsi}")
        
        # Get vessel info
        conn = scraper.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name, imo, ship_type, length FROM vessels_static WHERE mmsi = ?', (mmsi,))
        vessel = cursor.fetchone()
        conn.close()
        
        if vessel:
            name, imo, ship_type, length = vessel
            print(f"  Vessel: {name or 'Unknown'} | IMO: {imo or 'N/A'} | Type: {ship_type}")
        else:
            print(f"  Vessel not found in database")
            continue
        
        # Test search
        gt_value = scraper.search_gt_for_mmsi(mmsi, vessel[0] if vessel else None)
        print(f"  Result: {gt_value}")
        
        if i < len(test_mmsi_list) - 1:
            print("  Waiting 30 seconds before next search...")
            import time
            time.sleep(30)
        
        print("-" * 40)
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_search_scraper()
