#!/usr/bin/env python3
"""Run CompanyProfilerV3 ONLY for WASP adopter companies.

Goal: scrape company websites (About/Mission/Sustainability/etc.) and store text in
`company_profiles_v3_structured_wasp_*.json` so you can do sentiment analysis.

Usage:
  python3 scripts/run_profiler_v3_for_wasp.py
  python3 scripts/run_profiler_v3_for_wasp.py --limit 20 --max-pages 8

Notes:
- Uses the existing logic in CompanyProfilerV3 to crawl key pages.
- Output files go into data/.
"""

import argparse
import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.company_profiler_v3 import CompanyProfilerV3


def get_wasp_companies_with_metadata(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Distinct WASP adopters by company_name (wind_assisted=1)
    cur.execute('''
        SELECT DISTINCT e.company_name
        FROM eu_mrv_emissions e
        INNER JOIN vessels_static v ON e.imo = v.imo
        WHERE v.wind_assisted = 1
          AND e.company_name IS NOT NULL
          AND TRIM(e.company_name) != ''
        ORDER BY e.company_name
    ''')
    adopter_names = [r[0] for r in cur.fetchall()]

    if not adopter_names:
        conn.close()
        return []

    placeholders = ','.join(['?'] * len(adopter_names))

    # Pull same metadata fields as CompanyProfilerV3.get_companies_with_metadata()
    cur.execute(f'''
        SELECT 
            company_name,
            COUNT(*) as vessel_count,
            AVG(total_co2_emissions) as avg_emissions,
            AVG(avg_co2_per_distance) as avg_co2_distance,
            AVG(technical_efficiency) as avg_efficiency,
            GROUP_CONCAT(DISTINCT ship_type) as ship_types,
            AVG(CAST(econowind_fit_score AS FLOAT)) as avg_wasp_score
        FROM eu_mrv_emissions
        WHERE company_name IN ({placeholders})
        GROUP BY company_name
        ORDER BY vessel_count DESC, company_name
    ''', adopter_names)

    companies = []
    for row in cur.fetchall():
        companies.append({
            'name': row[0],
            'vessel_count': row[1],
            'avg_emissions': row[2],
            'avg_co2_distance': row[3],
            'avg_efficiency': row[4],
            'ship_types': row[5].split(',') if row[5] else [],
            'avg_wasp_score': row[6],
        })

    conn.close()
    return companies


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='data/vessel_static_data.db')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--max-pages', type=int, default=6)
    ap.add_argument('--progress-every', type=int, default=2)
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    companies = get_wasp_companies_with_metadata(args.db)
    if not companies:
        print('No WASP adopter companies found (wind_assisted=1).')
        return 2

    if args.limit and args.limit > 0:
        companies = companies[:args.limit]

    profiler = CompanyProfilerV3(verbose=args.verbose, max_pages_per_site=args.max_pages)

    out_dir = project_root / 'data'
    out_dir.mkdir(exist_ok=True)
    progress_path = out_dir / 'company_profiles_v3_structured_wasp_progress.json'

    for idx, meta in enumerate(companies, 1):
        try:
            if args.verbose:
                print(f"\n[{idx}/{len(companies)}] {meta['name']}")
            profile = profiler.profile_company_structured(meta)
            profiler.companies_data[meta['name']] = profile

            if idx % args.progress_every == 0:
                payload = {
                    'companies': profiler.companies_data,
                    'total': len(profiler.companies_data),
                    'timestamp': datetime.now().isoformat(),
                    'version': '3.0-wasp',
                    'scope': 'wasp_adopters',
                }
                progress_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            print(f"Error profiling {meta['name']}: {e}")
            continue

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = out_dir / f'company_profiles_v3_structured_wasp_{ts}.json'
    payload = {
        'companies': profiler.companies_data,
        'total': len(profiler.companies_data),
        'timestamp': datetime.now().isoformat(),
        'version': '3.0-wasp',
        'scope': 'wasp_adopters',
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"Saved: {out_path} (companies={payload['total']})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
