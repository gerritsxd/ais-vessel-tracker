"""
Calculate technical fit scores for all vessels in database.
Uses only basic vessel characteristics: length, ship_type, beam, flag_state
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ml.technical_fit_score import TechnicalFitScorer

DB_NAME = "vessel_static_data.db"


def calculate_fit_scores(db_path, limit=None):
    """Calculate fit scores for all vessels."""
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    
    # Check if technical_fit_score column exists
    cursor.execute("PRAGMA table_info(vessels_static)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'technical_fit_score' not in columns:
        print("Adding technical_fit_score column...")
        cursor.execute('''
            ALTER TABLE vessels_static 
            ADD COLUMN technical_fit_score REAL DEFAULT NULL
        ''')
        conn.commit()
        print("✅ Added technical_fit_score column")
    
    # Get vessels that need scores
    query = '''
        SELECT mmsi, length, ship_type, beam, flag_state, detailed_ship_type
        FROM vessels_static
        WHERE mmsi IS NOT NULL
          AND length IS NOT NULL
          AND length > 0
          AND ship_type IS NOT NULL
    '''
    
    if limit:
        query += f' LIMIT {limit}'
    
    cursor.execute(query)
    vessels = cursor.fetchall()
    
    print(f"Calculating fit scores for {len(vessels)} vessels...")
    print("="*80)
    
    scorer = TechnicalFitScorer()
    updated = 0
    
    for i, (mmsi, length, ship_type, beam, flag_state, detailed_ship_type) in enumerate(vessels, 1):
        if i % 1000 == 0:
            print(f"Processed {i}/{len(vessels)} vessels...")
        
        # Calculate score
        result = scorer.calculate_score(
            length=length,
            ship_type=ship_type,
            beam=beam,
            flag_state=flag_state,
            detailed_ship_type=detailed_ship_type
        )
        
        # Update database
        cursor.execute('''
            UPDATE vessels_static
            SET technical_fit_score = ?
            WHERE mmsi = ?
        ''', (result['total_score'], mmsi))
        
        updated += 1
    
    conn.commit()
    
    # Print statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            COUNT(technical_fit_score) as with_score,
            AVG(technical_fit_score) as avg_score,
            MIN(technical_fit_score) as min_score,
            MAX(technical_fit_score) as max_score
        FROM vessels_static
        WHERE mmsi IS NOT NULL
    ''')
    
    stats = cursor.fetchone()
    
    print("="*80)
    print("FIT SCORE STATISTICS")
    print("="*80)
    print(f"Total vessels: {stats[0]:,}")
    print(f"Vessels with scores: {stats[1]:,}")
    print(f"Average score: {stats[2]:.1f}/100")
    print(f"Score range: {stats[3]:.1f} - {stats[4]:.1f}")
    print("="*80)
    
    # Score distribution
    cursor.execute('''
        SELECT 
            CASE 
                WHEN technical_fit_score >= 80 THEN 'Excellent (80-100)'
                WHEN technical_fit_score >= 60 THEN 'Good (60-79)'
                WHEN technical_fit_score >= 40 THEN 'Moderate (40-59)'
                WHEN technical_fit_score >= 20 THEN 'Low (20-39)'
                ELSE 'Poor (0-19)'
            END as category,
            COUNT(*) as count
        FROM vessels_static
        WHERE technical_fit_score IS NOT NULL
        GROUP BY category
        ORDER BY MIN(technical_fit_score) DESC
    ''')
    
    print("\nScore Distribution:")
    for category, count in cursor.fetchall():
        print(f"  {category}: {count:,} vessels")
    
    conn.close()
    print(f"\n✅ Updated {updated} vessels with fit scores")


def main():
    """Main function."""
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        exit(1)
    
    print("🚀 Calculating Technical Fit Scores")
    print(f"📊 Database: {db_path}\n")
    
    # Optional limit for testing
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        print(f"Limiting to {limit} vessels\n")
    
    calculate_fit_scores(db_path, limit=limit)
    print("\n✅ Complete!")


if __name__ == "__main__":
    main()

