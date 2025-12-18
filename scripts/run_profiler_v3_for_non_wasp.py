#!/usr/bin/env python3
"""Run CompanyProfilerV3 for NON-WASP companies (control group).

Selects companies from eu_mrv_emissions joined to vessels_static where wind_assisted=0.
Processes in batches via --start-from/--limit to build a large dataset over time.

Outputs:
- data/company_profiles_v3_structured_non_wasp_progress.json
- data/company_profiles_v3_structured_non_wasp_<timestamp>.json

Usage:
  python3 scripts/run_profiler_v3_for_non_wasp.py --limit 50 --start-from 0
  python3 scripts/run_profiler_v3_for_non_wasp.py --limit 50 --start-from 50
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


def get_non_wasp_companies_with_metadata(db_path: str, start_from: int, limit: int):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Company list ordered by fleet size, excluding wind_assisted=1
    # We join to vessels_static via imo to get wind_assisted flag.
    cur.execute('''
        SELECT
            e.company_name,
            COUNT(*) as vessel_count,
            AVG(e.total_co2_emissions) as avg_emissions,
            AVG(e.avg_co2_per_distance) as avg_co2_distance,
            AVG(e.technical_efficiency) as avg_efficiency,
            GROUP_CONCAT(DISTINCT e.ship_type) as ship_types,
            AVG(CAST(e.econowind_fit_score AS FLOAT)) as avg_wasp_score
        FROM eu_mrv_emissions e
        LEFT JOIN vessels_static v ON e.imo = v.imo
        WHERE e.company_name IS NOT NULL
          AND TRIM(e.company_name) != ''
          AND COALESCE(v.wind_assisted, 0) = 0
        GROUP BY e.company_name
        ORDER BY vessel_count DESC, e.company_name
        LIMIT ? OFFSET ?
    ''', (limit, start_from))

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
    ap.add_argument('--limit', type=int, default=50)
    ap.add_argument('--start-from', type=int, default=0)
    ap.add_argument('--max-pages', type=int, default=8)
    ap.add_argument('--progress-every', type=int, default=10)
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    companies = get_non_wasp_companies_with_metadata(args.db, args.start_from, args.limit)
    if not companies:
        print('No non-WASP companies returned (check DB).')
        return 2

    profiler = CompanyProfilerV3(verbose=args.verbose, max_pages_per_site=args.max_pages)

    out_dir = project_root / 'data'
    out_dir.mkdir(exist_ok=True)
    progress_path = out_dir / 'company_profiles_v3_structured_non_wasp_progress.json'

    for idx, meta in enumerate(companies, 1):
        try:
            if args.verbose:
                print(f"\n[{args.start_from + idx}/{args.start_from + len(companies)}] {meta['name']}")
            profile = profiler.profile_company_structured(meta)
            profiler.companies_data[meta['name']] = profile

            if idx % args.progress_every == 0:
                payload = {
                    'companies': profiler.companies_data,
                    'total': len(profiler.companies_data),
                    'timestamp': datetime.now().isoformat(),
                    'version': '3.0-non-wasp',
                    'scope': 'non_wasp',
                    'start_from': args.start_from,
                    'limit': args.limit,
                }
                progress_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            print(f"Error profiling {meta['name']}: {e}")
            continue

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = out_dir / f'company_profiles_v3_structured_non_wasp_{ts}.json'
    payload = {
        'companies': profiler.companies_data,
        'total': len(profiler.companies_data),
        'timestamp': datetime.now().isoformat(),
        'version': '3.0-non-wasp',
        'scope': 'non_wasp',
        'start_from': args.start_from,
        'limit': args.limit,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"Saved: {out_path} (companies={payload['total']})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
