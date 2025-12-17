#!/usr/bin/env python3
"""Run NON-Gemini intelligence scraping (DuckDuckGo + direct scraping) ONLY for WASP adopters.

This is the fallback when Gemini is rate-limited / quota-exhausted.
Writes:
- data/company_intelligence_v2_wasp_progress.json
- data/company_intelligence_v2_wasp_<timestamp>.json

Usage:
  python3 scripts/run_intelligence_v2_for_wasp.py
  python3 scripts/run_intelligence_v2_for_wasp.py --limit 20
"""

import argparse
import sqlite3
import time
from pathlib import Path
from datetime import datetime
import sys
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.company_intelligence_scraper_v2 import CompanyIntelligenceScraperV2


def get_wasp_companies_with_meta(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

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
    cur.execute(f'''
        SELECT
            company_name,
            COUNT(*) as vessel_count,
            AVG(total_co2_emissions) as avg_emissions,
            AVG(avg_co2_per_distance) as avg_co2_distance
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
        })

    conn.close()
    return companies


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='data/vessel_static_data.db')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--progress-every', type=int, default=2)
    args = ap.parse_args()

    companies = get_wasp_companies_with_meta(args.db)
    if not companies:
        print('No WASP adopter companies found (wind_assisted=1).')
        return 2

    if args.limit and args.limit > 0:
        companies = companies[:args.limit]

    scraper = CompanyIntelligenceScraperV2(verbose=True)

    out_dir = project_root / 'data'
    out_dir.mkdir(exist_ok=True)
    progress_path = out_dir / 'company_intelligence_v2_wasp_progress.json'

    print('=' * 80)
    print('INTELLIGENCE V2 (DuckDuckGo) - WASP ADOPTERS ONLY')
    print('=' * 80)
    print(f"Companies: {len(companies)}")

    for idx, meta in enumerate(companies, 1):
        try:
            print(f"\n[{idx}/{len(companies)}] {meta['name']}")
            intel = scraper.gather_intelligence(meta)
            scraper.intelligence_data[meta['name']] = intel

            if idx % args.progress_every == 0:
                payload = {
                    'generated_at': datetime.now().isoformat(),
                    'scope': 'wasp_adopters',
                    'version': 'intelligence-v2-duckduckgo',
                    'companies': scraper.intelligence_data,
        'total': len(scraper.intelligence_data),
                'total': len(scraper.intelligence_data),
                }
                progress_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
                print(f"Saved progress: {progress_path}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            continue

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    final_path = out_dir / f'company_intelligence_v2_wasp_{ts}.json'
    final_payload = {
        'generated_at': datetime.now().isoformat(),
        'scope': 'wasp_adopters',
        'version': 'intelligence-v2-duckduckgo',
        'companies': scraper.intelligence_data,
    }
    final_path.write_text(json.dumps(final_payload, indent=2), encoding='utf-8')
    print(f"Saved final: {final_path}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
