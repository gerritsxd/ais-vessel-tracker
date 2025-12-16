#!/usr/bin/env python3
"""Derive Econowind/VentoFoil-style adopter companies from the local SQLite DB.

Why:
- Your repo already tracks 77 wind-propulsion vessels (incl. suction wings/sails).
- The “20–30 Econowind adopters” you were remembering corresponds closely to the
  subset with 'suction wing/sail' technology (currently 28 vessels in the list).
- This script maps those suction-tech vessels to MRV company names using the DB.

Outputs (into exports/, gitignored):
- econowind_adopters_from_db_<ts>.txt (distinct company names)
- econowind_adopters_from_db_<ts>.csv (company + vessel + tech + year)

Usage:
  python3 scripts/export_econowind_adopters_from_db.py
  python3 scripts/export_econowind_adopters_from_db.py --db data/vessel_static_data.db
"""

import argparse
import sqlite3
from pathlib import Path
from datetime import datetime


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='data/vessel_static_data.db', help='Path to SQLite database')
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 2

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    has_wind = table_exists(conn, 'wind_propulsion')
    has_wind_mmsi = table_exists(conn, 'wind_propulsion_mmsi')
    has_static = table_exists(conn, 'vessels_static')
    has_mrv = table_exists(conn, 'eu_mrv_emissions')

    if not has_mrv:
        print("Missing table eu_mrv_emissions; cannot map vessels -> company_name")
        return 3

    rows = []

    # Best path: wind_propulsion_mmsi -> vessels_static (mmsi->imo) -> eu_mrv_emissions (imo->company)
    if has_wind_mmsi and has_static:
        q = """
        SELECT
            e.company_name AS company_name,
            w.vessel_name AS vessel_name,
            w.technology_installed AS technology_installed,
            w.installation_year AS installation_year,
            'wind_propulsion_mmsi' AS source
        FROM wind_propulsion_mmsi w
        JOIN vessels_static v ON v.mmsi = w.mmsi
        JOIN eu_mrv_emissions e ON e.imo = v.imo
        WHERE w.mmsi IS NOT NULL
          AND w.technology_installed IS NOT NULL
          AND LOWER(w.technology_installed) LIKE '%suction%'
          AND e.company_name IS NOT NULL
        """
        rows = conn.execute(q).fetchall()

    # Fallback: wind_propulsion (name list) -> eu_mrv_emissions by vessel_name
    if not rows and has_wind:
        q = """
        SELECT
            e.company_name AS company_name,
            w.vessel_name AS vessel_name,
            w.technology_installed AS technology_installed,
            w.installation_year AS installation_year,
            'wind_propulsion' AS source
        FROM wind_propulsion w
        JOIN eu_mrv_emissions e
          ON UPPER(TRIM(e.vessel_name)) = UPPER(TRIM(w.vessel_name))
        WHERE w.technology_installed IS NOT NULL
          AND LOWER(w.technology_installed) LIKE '%suction%'
          AND e.company_name IS NOT NULL
        """
        rows = conn.execute(q).fetchall()

    conn.close()

    if not rows:
        print("No matches found. Likely causes:")
        print("- wind_propulsion(_mmsi) tables not populated yet")
        print("- vessels_static missing imo/mmsi fields")
        print("- MRV vessel_name doesn't match wind_propulsion vessel_name")
        print("Try running: python3 src/utils/import_wind_propulsion.py (or _mmsi) on the VPS DB")
        return 4

    # Normalize + de-dupe company list
    companies = sorted({r['company_name'].strip() for r in rows if r['company_name'] and r['company_name'].strip()})

    exports_dir = Path('exports')
    exports_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')

    out_txt = exports_dir / f"econowind_adopters_from_db_{ts}.txt"
    out_csv = exports_dir / f"econowind_adopters_from_db_{ts}.csv"

    out_txt.write_text("\n".join(companies) + "\n", encoding='utf-8')

    import csv
    with out_csv.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['company_name', 'vessel_name', 'technology_installed', 'installation_year', 'source'])
        for r in rows:
            w.writerow([
                r['company_name'],
                r['vessel_name'],
                r['technology_installed'],
                r['installation_year'],
                r['source'],
            ])

    print(f"Wrote: {out_txt} ({len(companies)} companies)")
    print(f"Wrote: {out_csv} ({len(rows)} vessel->company rows)")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
