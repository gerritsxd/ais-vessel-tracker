"""
Try to match remaining WASP vessels by vessel name when MMSI doesn't match.
This helps recover DWT/GT data for WASP vessels not currently in vessels_static.
"""

import sqlite3
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime

DB_NAME = "vessel_static_data.db"


def get_db_path():
    """Get database path."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    return db_path


def similarity(a, b):
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def match_wasp_by_name(conn):
    """Try to match WASP vessels by name."""
    cursor = conn.cursor()
    
    # Get WASP vessels that didn't match by MMSI
    cursor.execute('''
        SELECT w.mmsi, w.vessel_name, w.dwt, w.gt, w.length
        FROM wind_propulsion_mmsi w
        WHERE NOT EXISTS (
            SELECT 1 FROM vessels_static v WHERE v.mmsi = w.mmsi
        )
        AND w.mmsi IS NOT NULL
    ''')
    
    unmatched_wasp = cursor.fetchall()
    print(f"Found {len(unmatched_wasp)} WASP vessels not matched by MMSI")
    
    if not unmatched_wasp:
        print("✅ All WASP vessels already matched!")
        return 0
    
    # Get all vessels_static names for matching
    cursor.execute('SELECT mmsi, name FROM vessels_static WHERE name IS NOT NULL')
    static_vessels = {name.lower(): mmsi for mmsi, name in cursor.fetchall()}
    
    matched_count = 0
    matches_found = []
    
    print("\nAttempting name-based matching...")
    print("="*70)
    
    for wasp_mmsi, wasp_name, wasp_dwt, wasp_gt, wasp_length in unmatched_wasp:
        if not wasp_name:
            continue
        
        wasp_name_lower = wasp_name.lower().strip()
        best_match = None
        best_score = 0.0
        
        # Try exact match first
        if wasp_name_lower in static_vessels:
            best_match = static_vessels[wasp_name_lower]
            best_score = 1.0
        else:
            # Try fuzzy matching
            for static_name, static_mmsi in static_vessels.items():
                score = similarity(wasp_name_lower, static_name)
                if score > best_score and score > 0.85:  # 85% similarity threshold
                    best_score = score
                    best_match = static_mmsi
        
        if best_match and best_score >= 0.85:
            # Update vessels_static with WASP data
            cursor.execute('''
                UPDATE vessels_static
                SET 
                    dwt = ?,
                    gt = ?,
                    dwt_source = 'wasp',
                    gt_source = 'wasp',
                    dwt_updated_at = datetime('now'),
                    gt_updated_at = datetime('now')
                WHERE mmsi = ?
                AND (dwt IS NULL OR gt IS NULL)
            ''', (wasp_dwt, wasp_gt, best_match))
            
            if cursor.rowcount > 0:
                matched_count += 1
                matches_found.append((wasp_name, best_match, best_score))
                print(f"✅ Matched: '{wasp_name}' → MMSI {best_match} (similarity: {best_score:.2f})")
    
    conn.commit()
    
    print("="*70)
    print(f"\n✅ Matched {matched_count} additional WASP vessels by name")
    
    return matched_count


def main():
    """Main function."""
    db_path = get_db_path()
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print(f"📊 Matching WASP vessels by name in: {db_path}")
    print(f"⏰ Started at: {datetime.now()}\n")
    
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute('PRAGMA journal_mode=WAL')
    
    try:
        matched = match_wasp_by_name(conn)
        
        if matched > 0:
            print(f"\n✅ Successfully matched {matched} WASP vessels!")
            print("   Run normalize_vessel_schema.py again to see updated statistics")
        else:
            print("\n⚠️  No additional matches found")
            print("   Remaining WASP vessels may not be in vessels_static table")
            print("   (They might be inactive or not currently tracked)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()

