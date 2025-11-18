"""
Test script for Datalastic Atlantic Tracker
Runs ONE scan to verify API connectivity and credit usage
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.atlantic_tracker import (
    load_api_key,
    scan_atlantic_zone,
    ATLANTIC_ZONES
)

def test_api_connection():
    """Test Datalastic API connection."""
    print("\n" + "="*60)
    print("TESTING DATALASTIC ATLANTIC TRACKER")
    print("="*60)
    
    # Load API key
    try:
        api_key = load_api_key()
        print("✓ API key loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load API key: {e}")
        return
    
    # Test scan ONE zone
    print(f"\nTesting scan on: {ATLANTIC_ZONES[0]['name']}")
    print("(This is just 1 zone to test, not all 5)")
    print("-"*60)
    
    vessels, credits = scan_atlantic_zone(api_key, ATLANTIC_ZONES[0])
    
    print("\n" + "="*60)
    print("TEST RESULTS:")
    print(f"  Vessels found: {vessels}")
    print(f"  Credits used: {credits}")
    print("\nIf you see vessels and credits, the API is working! 🎉")
    print("\nFull scan (5 zones) will use ~5x these credits.")
    print("Running 4 times/day = ~20 full scans/day")
    print("="*60)


if __name__ == "__main__":
    test_api_connection()
