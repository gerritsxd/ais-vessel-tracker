#!/usr/bin/env python3
"""Export companies that own/operate wind-assisted (WASP) vessels from the SQLite DB.

This matches the existing ML ground truth definition:
- companies where a vessel in vessels_static has wind_assisted=1

Outputs into exports/ (gitignored):
- wasp_adopters_from_db_<ts>.txt  (distinct company names)
- wasp_adopters_from_db_<ts>.csv  (company + vessel + mmsi/imo when available)

Usage:
  python3 scripts/export_wasp_adopters_from_db.py
  python3 scripts/export_wasp_adopters_from_db.py --db data/vessel_static_data.db
"""

import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
import csv


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

    if not table_exists(conn, 'vessels_static') or not table_exists(conn, 'eu_mrv_emissions'):
        print("Missing required tables: vessels_static and/or eu_mrv_emissions")
        return 3

    q = """
    SELECT DISTINCT
        e.company_name AS company_name,
        e.vessel_name AS mrv_vessel_name,
        v.name AS ais_vessel_name,
        v.mmsi AS mmsi,
        v.imo AS imo,
        v.ship_type AS ship_type
    FROM eu_mrv_emissions e
    JOIN vessels_static v ON e.imo = v.imo
    WHERE v.wind_assisted = 1
      AND e.company_name IS NOT NULL
      AND TRIM(e.company_name) != ''
    ORDER BY e.company_name
    """

    rows = conn.execute(q).fetchall()
    conn.close()

    if not rows:
        print("No WASP/wind_assisted matches found (wind_assisted=1).")
        return 4

    companies = sorted({r['company_name'].strip() for r in rows if r['company_name'] and r['company_name'].strip()})

    exports_dir = Path('exports')
    exports_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')

    out_txt = exports_dir / f"wasp_adopters_from_db_{ts}.txt"
    out_csv = exports_dir / f"wasp_adopters_from_db_{ts}.csv"

    out_txt.write_text("\n".join(companies) + "\n", encoding='utf-8')

    with out_csv.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['company_name', 'mrv_vessel_name', 'ais_vessel_name', 'mmsi', 'imo', 'ship_type'])
        for r in rows:
            w.writerow([
                r['company_name'],
                r['mrv_vessel_name'],
                r['ais_vessel_name'],
                r['mmsi'],
                r['imo'],
                r['ship_type'],
            ])

    print(f"Wrote: {out_txt} ({len(companies)} companies)")
    print(f"Wrote: {out_csv} ({len(rows)} vessel->company rows)")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
