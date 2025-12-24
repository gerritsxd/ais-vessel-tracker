"""
Diagnostic script to understand why normalization coverage is low.
Checks MMSI/IMO matching between tables.
"""

import sqlite3
from pathlib import Path

DB_NAME = "vessel_static_data.db"


def get_db_path():
    """Get database path."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    return db_path


def diagnose_matching():
    """Diagnose why matching rates are low."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    
    print("="*70)
    print("NORMALIZATION DIAGNOSTICS")
    print("="*70)
    
    # Check WASP table
    print("\n1. WASP VESSELS (wind_propulsion_mmsi):")
    cursor.execute('SELECT COUNT(*) FROM wind_propulsion_mmsi')
    wasp_total = cursor.fetchone()[0]
    print(f"   Total WASP vessels: {wasp_total}")
    
    cursor.execute('SELECT COUNT(DISTINCT mmsi) FROM wind_propulsion_mmsi WHERE mmsi IS NOT NULL')
    wasp_with_mmsi = cursor.fetchone()[0]
    print(f"   WASP vessels with MMSI: {wasp_with_mmsi}")
    
    # Check how many WASP vessels match vessels_static
    cursor.execute('''
        SELECT COUNT(DISTINCT w.mmsi)
        FROM wind_propulsion_mmsi w
        WHERE EXISTS (
            SELECT 1 FROM vessels_static v WHERE v.mmsi = w.mmsi
        )
    ''')
    wasp_matched = cursor.fetchone()[0]
    print(f"   WASP vessels matched to vessels_static: {wasp_matched}/{wasp_total} ({100*wasp_matched/wasp_total:.1f}%)")
    
    # Check MRV table
    print("\n2. MRV VESSELS (eu_mrv_emissions):")
    cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions')
    mrv_total = cursor.fetchone()[0]
    print(f"   Total MRV vessels: {mrv_total}")
    
    cursor.execute('SELECT COUNT(DISTINCT imo) FROM eu_mrv_emissions WHERE imo IS NOT NULL')
    mrv_with_imo = cursor.fetchone()[0]
    print(f"   MRV vessels with IMO: {mrv_with_imo}")
    
    # Check how many have gross_tonnage
    cursor.execute('SELECT COUNT(*) FROM eu_mrv_emissions WHERE gross_tonnage IS NOT NULL AND gross_tonnage != "" AND gross_tonnage != "N/A"')
    mrv_with_gt = cursor.fetchone()[0]
    print(f"   MRV vessels with gross_tonnage: {mrv_with_gt}/{mrv_total} ({100*mrv_with_gt/mrv_total:.1f}%)")
    
    # Check how many MRV vessels match vessels_static
    cursor.execute('''
        SELECT COUNT(DISTINCT e.imo)
        FROM eu_mrv_emissions e
        WHERE EXISTS (
            SELECT 1 FROM vessels_static v WHERE v.imo = e.imo
        )
        AND e.gross_tonnage IS NOT NULL 
        AND e.gross_tonnage != ''
        AND e.gross_tonnage != 'N/A'
    ''')
    mrv_matched = cursor.fetchone()[0]
    print(f"   MRV vessels matched to vessels_static: {mrv_matched}/{mrv_with_gt} ({100*mrv_matched/mrv_with_gt:.1f}% of those with GT)")
    
    # Check vessels_static
    print("\n3. VESSELS_STATIC TABLE:")
    cursor.execute('SELECT COUNT(*) FROM vessels_static')
    static_total = cursor.fetchone()[0]
    print(f"   Total vessels: {static_total}")
    
    cursor.execute('SELECT COUNT(*) FROM vessels_static WHERE mmsi IS NOT NULL')
    static_with_mmsi = cursor.fetchone()[0]
    print(f"   Vessels with MMSI: {static_with_mmsi}")
    
    cursor.execute('SELECT COUNT(*) FROM vessels_static WHERE imo IS NOT NULL')
    static_with_imo = cursor.fetchone()[0]
    print(f"   Vessels with IMO: {static_with_imo} ({100*static_with_imo/static_total:.1f}%)")
    
    # Sample some WASP vessels that didn't match
    print("\n4. SAMPLE WASP VESSELS NOT MATCHED:")
    cursor.execute('''
        SELECT w.mmsi, w.vessel_name, w.dwt, w.gt
        FROM wind_propulsion_mmsi w
        WHERE NOT EXISTS (
            SELECT 1 FROM vessels_static v WHERE v.mmsi = w.mmsi
        )
        LIMIT 5
    ''')
    unmatched = cursor.fetchall()
    if unmatched:
        for mmsi, name, dwt, gt in unmatched:
            print(f"   MMSI: {mmsi}, Name: {name}, DWT: {dwt}, GT: {gt}")
    else:
        print("   All WASP vessels matched!")
    
    # Sample MRV vessels that didn't match
    print("\n5. SAMPLE MRV VESSELS NOT MATCHED:")
    cursor.execute('''
        SELECT e.imo, e.vessel_name, e.gross_tonnage
        FROM eu_mrv_emissions e
        WHERE e.gross_tonnage IS NOT NULL 
          AND e.gross_tonnage != ''
          AND e.gross_tonnage != 'N/A'
          AND NOT EXISTS (
            SELECT 1 FROM vessels_static v WHERE v.imo = e.imo
          )
        LIMIT 5
    ''')
    unmatched_mrv = cursor.fetchall()
    if unmatched_mrv:
        for imo, name, gt in unmatched_mrv:
            print(f"   IMO: {imo}, Name: {name}, GT: {gt}")
    else:
        print("   All MRV vessels with GT matched!")
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS:")
    print("="*70)
    
    if wasp_matched < wasp_total * 0.5:
        print(f"⚠️  Only {wasp_matched}/{wasp_total} WASP vessels matched!")
        print("   → Need to investigate MMSI mismatches")
        print("   → May need to match by vessel name as fallback")
    
    if mrv_matched < mrv_with_gt * 0.3:
        print(f"⚠️  Only {mrv_matched}/{mrv_with_gt} MRV vessels matched!")
        print("   → Need to investigate IMO mismatches")
        print("   → May need to match by vessel name as fallback")
    
    remaining_dwt = static_total - wasp_matched
    remaining_gt = static_total - wasp_matched - mrv_matched
    
    print(f"\n📊 REMAINING WORK:")
    print(f"   Vessels needing DWT: ~{remaining_dwt:,} ({100*remaining_dwt/static_total:.1f}%)")
    print(f"   Vessels needing GT: ~{remaining_gt:,} ({100*remaining_gt/static_total:.1f}%)")
    print(f"\n   → Need to scrape DWT/GT for remaining vessels")
    print(f"   → Or use ML prediction based on length/beam/ship_type")
    
    conn.close()


if __name__ == "__main__":
    diagnose_matching()

