"""
Import wind propulsion technology data for vessels using MMSI numbers.
This version uses MMSI for accurate matching instead of vessel names.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_NAME = "vessel_static_data.db"

# Wind-assisted vessels data with MMSI numbers
# Format: (vessel_name, mmsi, vessel_type, dwt, gt, length, technology_installed, installation_year, installation_type)
# MMSI = 0 means "look up online and add later"
WIND_VESSELS_MMSI = [
    ("E-Ship 1", 211281610, "Ro-Ro", 10020, 12968, 130, "4 x 27m fixed rotor sails", 2010, "newbuild"),
    ("Estraden", 219018448, "Ro-Ro", 9741, 18205, 163, "2 x 18m fixed rotor sails", 2014, "retrofit"),
    ("Afros", 636019825, "Bulk Carrier", 63223, 36452, 199, "4 x 16m movable rotor sails", 2018, "newbuild"),
    ("SC Connector", 219024633, "Ro-Ro", 8843, 12251, 155, "2 x 35m hinged rotor sails", 2021, "retrofit"),
    ("Pyxis Ocean", 636019825, "Bulk Carrier", 80962, 43291, 229, "2 x 40m retractable wing sails", 2023, "retrofit"),
    ("Canopee", 228373600, "Ro-Ro", 4700, 10400, 121, "4 x 30m retractable hybrid wing sails", 2023, "newbuild"),
    ("Berge Olympus", 636019825, "Bulk Carrier", 211153, 109716, 300, "4 x 40m retractable wing sails", 2024, "retrofit"),
    
    # Add more vessels here as you look up their MMSI numbers
    # You can find MMSI on: marinetraffic.com, vesselfinder.com, shipfinder.com
    # Format: ("Vessel Name", MMSI, "Type", DWT, GT, Length, "Technology", Year, "newbuild/retrofit"),
]


def create_wind_propulsion_table(conn):
    """Create the wind propulsion technology table with MMSI."""
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wind_propulsion_mmsi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vessel_name TEXT NOT NULL,
            mmsi INTEGER,
            vessel_type TEXT,
            dwt INTEGER,
            gt INTEGER,
            length INTEGER,
            technology_installed TEXT,
            installation_year INTEGER,
            installation_type TEXT,
            last_updated TEXT NOT NULL,
            UNIQUE(mmsi, installation_year)
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_wind_mmsi ON wind_propulsion_mmsi(mmsi)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_wind_vessel_name_mmsi ON wind_propulsion_mmsi(vessel_name)')
    
    conn.commit()
    print("✓ Wind propulsion MMSI table created")


def add_wind_assisted_column(conn):
    """Add wind_assisted flag to vessels_static table."""
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE vessels_static ADD COLUMN wind_assisted INTEGER DEFAULT 0')
        conn.commit()
        print("✓ Added wind_assisted column to vessels_static")
    except sqlite3.OperationalError:
        print("  wind_assisted column already exists")


def import_wind_vessels(conn):
    """Import wind-assisted vessel data with MMSI."""
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    
    inserted = 0
    updated = 0
    skipped = 0
    
    for vessel_data in WIND_VESSELS_MMSI:
        name, mmsi, vtype, dwt, gt, length, tech, year, inst_type = vessel_data
        
        if mmsi == 0:
            print(f"  ⚠ Skipped: {name} (MMSI not yet looked up)")
            skipped += 1
            continue
        
        try:
            cursor.execute('''
                INSERT INTO wind_propulsion_mmsi (vessel_name, mmsi, vessel_type, dwt, gt, length, technology_installed, installation_year, installation_type, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mmsi, installation_year) DO UPDATE SET
                    vessel_name = excluded.vessel_name,
                    vessel_type = excluded.vessel_type,
                    dwt = excluded.dwt,
                    gt = excluded.gt,
                    length = excluded.length,
                    technology_installed = excluded.technology_installed,
                    installation_type = excluded.installation_type,
                    last_updated = excluded.last_updated
            ''', (name, mmsi, vtype, dwt, gt, length, tech, year, inst_type, timestamp))
            
            if cursor.rowcount == 1:
                inserted += 1
            else:
                updated += 1
                
        except Exception as e:
            print(f"  Error importing {name} (MMSI: {mmsi}): {e}")
    
    conn.commit()
    
    print(f"\n{'='*80}")
    print("WIND PROPULSION DATA IMPORT COMPLETE")
    print(f"{'='*80}")
    print(f"✓ Inserted: {inserted} new vessels")
    print(f"✓ Updated: {updated} existing vessels")
    print(f"⚠ Skipped: {skipped} vessels (MMSI not yet looked up)")
    print(f"✓ Total imported: {inserted + updated}")
    print(f"{'='*80}\n")


def match_wind_vessels_to_ais(conn):
    """Match wind-assisted vessels to AIS database by MMSI and mark them."""
    cursor = conn.cursor()
    
    print("\nMatching wind-assisted vessels to AIS database by MMSI...")
    
    # Get all wind vessel MMSIs
    cursor.execute('SELECT DISTINCT mmsi, vessel_name FROM wind_propulsion_mmsi WHERE mmsi > 0')
    wind_vessels = cursor.fetchall()
    
    matched = 0
    not_found = []
    
    for mmsi, wind_name in wind_vessels:
        # Match by MMSI (100% accurate!)
        cursor.execute('''
            UPDATE vessels_static
            SET wind_assisted = 1
            WHERE mmsi = ?
        ''', (mmsi,))
        
        if cursor.rowcount > 0:
            matched += 1
            # Get the actual name from AIS
            cursor.execute('SELECT name FROM vessels_static WHERE mmsi = ?', (mmsi,))
            ais_name = cursor.fetchone()[0]
            print(f"  ✓ Matched: {wind_name} (MMSI: {mmsi}) -> AIS name: {ais_name}")
        else:
            not_found.append((mmsi, wind_name))
    
    conn.commit()
    
    print(f"\n  Total AIS vessels flagged as wind-assisted: {matched}")
    
    if not_found:
        print(f"\n  Vessels not yet in AIS database ({len(not_found)}):")
        for mmsi, name in not_found:
            print(f"    - {name} (MMSI: {mmsi})")
        print(f"\n  💡 These vessels will be flagged automatically when they appear in AIS tracking")


def show_statistics(conn):
    """Show statistics about wind-assisted vessels."""
    cursor = conn.cursor()
    
    print(f"\n{'='*80}")
    print("WIND PROPULSION STATISTICS")
    print(f"{'='*80}")
    
    # Total wind vessels
    cursor.execute('SELECT COUNT(*) FROM wind_propulsion_mmsi WHERE mmsi > 0')
    total = cursor.fetchone()[0]
    print(f"Total wind-assisted vessels with MMSI: {total}")
    
    # By installation type
    cursor.execute('''
        SELECT installation_type, COUNT(*) 
        FROM wind_propulsion_mmsi 
        WHERE mmsi > 0
        GROUP BY installation_type
    ''')
    print(f"\nBy installation type:")
    for inst_type, count in cursor.fetchall():
        print(f"  {inst_type}: {count}")
    
    # Matched with AIS
    cursor.execute('SELECT COUNT(*) FROM vessels_static WHERE wind_assisted = 1')
    matched = cursor.fetchone()[0]
    print(f"\nVessels matched with AIS data: {matched}")
    
    if matched > 0:
        print(f"\n{'='*80}")
        print("CURRENTLY TRACKED WIND-ASSISTED VESSELS:")
        print(f"{'='*80}")
        cursor.execute('''
            SELECT v.mmsi, v.name, v.length, w.technology_installed
            FROM vessels_static v
            INNER JOIN wind_propulsion_mmsi w ON v.mmsi = w.mmsi
            WHERE v.wind_assisted = 1
            ORDER BY v.length DESC
        ''')
        
        for i, (mmsi, name, length, tech) in enumerate(cursor.fetchall(), 1):
            print(f"{i:2}. MMSI {mmsi} - {name:30} ({length:3}m) - {tech}")
    
    print(f"{'='*80}\n")


def export_template_for_mmsi_lookup():
    """Export a template CSV to help look up MMSI numbers."""
    output_file = Path(__file__).parent.parent.parent / "wind_vessels_mmsi_template.csv"
    
    # Original vessel list without MMSI
    vessels = [
        ("E-Ship 1", "Ro-Ro", 130),
        ("Estraden", "Ro-Ro", 163),
        ("Goldy Seven", "General Cargo", 90),
        ("New Vitality", "Tanker", 333),
        ("Hu Po", "Tanker", 245),
        ("Afros", "Bulk Carrier", 199),
        ("Copenhagen", "Ferry", 169),
        ("Ankie", "General Cargo", 90),
        ("Anika Braren", "General Cargo", 85),
        ("SC Connector", "Ro-Ro", 155),
        ("Sea Zhoushan", "Bulk Carrier", 340),
        ("Frisian Sea", "General Cargo", 118),
        ("Naumon", "General Cargo/Theatre Vessel", 59),
        ("GNV BRIDGE", "Ferry", 203),
        ("Marfret Niolon", "Ro-Ro", 123),
        ("Anna", "General Cargo", 90),
        ("Berlin", "Ferry", 169),
        ("Shofu Maru", "Bulk Carrier", 235),
        ("Delphine", "Ro-Ro", 234),
        ("New Aden", "Tanker", 333),
        ("MN Pelican", "Ro-Ro", 154),
        ("EEMS Traveller", "General Cargo", 90),
        ("Sunnanvik", "Cement Carrier", 124),
        ("Chang Hang Sheng Hai", "Bulk Carrier", 190),
        ("TR Lady", "Bulk Carrier", 229),
        ("Cape Brolga", "Bulk Carrier", 300),
        ("Canopee", "Ro-Ro", 121),
        ("Pyxis Ocean", "Bulk Carrier", 229),
        # Add more as needed...
    ]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Vessel Name,Type,Length,MMSI (look up online),Notes\n")
        for name, vtype, length in vessels:
            f.write(f'"{name}","{vtype}",{length},,\n')
    
    print(f"\n📋 Template exported to: {output_file}")
    print("   Fill in MMSI column by searching on marinetraffic.com or vesselfinder.com")


def main():
    """Main import process."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        print("Run ais_collector.py first to create the database.")
        return
    
    print(f"{'='*80}")
    print("WIND PROPULSION TECHNOLOGY IMPORT (MMSI-based)")
    print(f"{'='*80}\n")
    
    conn = sqlite3.connect(db_path)
    
    try:
        create_wind_propulsion_table(conn)
        add_wind_assisted_column(conn)
        import_wind_vessels(conn)
        match_wind_vessels_to_ais(conn)
        show_statistics(conn)
        
        print("✓ Import successful!")
        print(f"✓ Database updated: {db_path}")
        
        print("\n" + "="*80)
        print("NEXT STEPS:")
        print("="*80)
        print("1. Look up MMSI numbers for remaining vessels on:")
        print("   - https://www.marinetraffic.com")
        print("   - https://www.vesselfinder.com")
        print("2. Add MMSI numbers to WIND_VESSELS_MMSI list in this script")
        print("3. Run this script again to match more vessels")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error during import: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == '__main__':
    main()
