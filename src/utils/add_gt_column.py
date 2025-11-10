"""
Database Migration: Add gross_tonnage column to eu_mrv_emissions table
Run this once to add the GT column if it doesn't exist.
"""

import sqlite3
from pathlib import Path

DB_NAME = "vessel_static_data.db"


def add_gt_column():
    """Add gross_tonnage column to eu_mrv_emissions table."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Error: Database not found: {db_path}")
        print("Run ais_collector.py first to create the database.")
        return False
    
    print("="*80)
    print("DATABASE MIGRATION: Adding gross_tonnage column")
    print("="*80)
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='eu_mrv_emissions'
        """)
        
        if not cursor.fetchone():
            print("❌ Error: eu_mrv_emissions table does not exist")
            print("Run import_mrv_data.py first to create the emissions table.")
            return False
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(eu_mrv_emissions)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'gross_tonnage' in columns:
            print("✓ gross_tonnage column already exists!")
            
            # Show statistics
            cursor.execute("""
                SELECT COUNT(*) FROM eu_mrv_emissions 
                WHERE gross_tonnage IS NOT NULL AND gross_tonnage > 0
            """)
            gt_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions")
            total = cursor.fetchone()[0]
            
            print(f"\nCurrent GT data:")
            print(f"  Total vessels: {total:,}")
            print(f"  With GT data: {gt_count:,} ({gt_count/total*100:.1f}%)")
            print(f"  Missing GT: {total - gt_count:,}")
            
        else:
            print("Adding gross_tonnage column...")
            cursor.execute("""
                ALTER TABLE eu_mrv_emissions 
                ADD COLUMN gross_tonnage REAL
            """)
            conn.commit()
            print("✓ gross_tonnage column added successfully!")
            
            cursor.execute("SELECT COUNT(*) FROM eu_mrv_emissions")
            total = cursor.fetchone()[0]
            print(f"\n  Total vessels ready for GT scraping: {total:,}")
        
        print("\n" + "="*80)
        print("✓ Migration complete!")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    success = add_gt_column()
    exit(0 if success else 1)
