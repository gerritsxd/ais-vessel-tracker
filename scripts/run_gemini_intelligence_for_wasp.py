#!/usr/bin/env python3
"""Run Gemini intelligence scraping ONLY for WASP/wind-assisted adopter companies.

This is what you asked for: targeted scraping just for companies that own ships with
WASP / wind-assisted propulsion (vessels_static.wind_assisted=1).

It:
- Loads Gemini API key from config/gemini_api_key.txt
- Queries DB to get adopter companies (wind_assisted=1) + metadata (vessel_count/emissions)
- Runs GeminiIntelligenceScraper.gather_intelligence() for each company
- Writes progress/final JSON into data/

Usage:
  python3 scripts/run_gemini_intelligence_for_wasp.py
  python3 scripts/run_gemini_intelligence_for_wasp.py --limit 30
  python3 scripts/run_gemini_intelligence_for_wasp.py --sleep 30

Notes:
- Safe to run repeatedly; it writes a timestamped final file.
- Uses the same output schema as the existing gemini scraper.
"""

import argparse
import sqlite3
import time
from pathlib import Path
from datetime import datetime

# Ensure project root on path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.company_intelligence_scraper_gemini import GeminiIntelligenceScraper


def load_api_key() -> str:
    p = project_root / 'config' / 'gemini_api_key.txt'
    if not p.exists():
        raise SystemExit(f"Missing Gemini key file: {p}")
    key = p.read_text().strip()
    if not key or key == 'your-api-key-here':
        raise SystemExit(f"Invalid Gemini key in: {p}")
    return key


def get_wasp_companies_with_meta(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Distinct adopter companies (ground truth)
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

    # Metadata per company (same fields as base scraper)
    # We compute fleet size from MRV rows (not AIS) to match existing behavior.
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
    ap.add_argument('--limit', type=int, default=0, help='0 = all adopters')
    ap.add_argument('--sleep', type=int, default=30, help='Seconds between Gemini calls')
    ap.add_argument('--progress-every', type=int, default=5)
    args = ap.parse_args()

    api_key = load_api_key()

    companies = get_wasp_companies_with_meta(args.db)
    if not companies:
        print('No WASP adopter companies found (wind_assisted=1).')
        print('Make sure wind-assisted marking/import has been run and MRV data is present.')
        return 2

    if args.limit and args.limit > 0:
        companies = companies[:args.limit]

    scraper = GeminiIntelligenceScraper(api_key=api_key, verbose=True)

    print('=' * 80)
    print('GEMINI INTELLIGENCE - WASP ADOPTER COMPANIES ONLY')
    print('=' * 80)
    print(f"DB: {args.db}")
    print(f"Companies to scrape: {len(companies)}")
    print(f"Sleep between calls: {args.sleep}s")
    print('=' * 80)

    out_dir = project_root / 'data'
    out_dir.mkdir(exist_ok=True)

    progress_path = out_dir / 'company_intelligence_gemini_wasp_progress.json'

    for idx, company in enumerate(companies, 1):
        print(f"\n[{idx}/{len(companies)}] {company['name']}")
        intel = scraper.gather_intelligence(company)
        scraper.intelligence_data[company['name']] = intel

        if idx % args.progress_every == 0:
            progress_payload = {
                'generated_at': datetime.now().isoformat(),
                'scope': 'wasp_adopters',
                'companies': scraper.intelligence_data,
            }
            progress_path.write_text(__import__('json').dumps(progress_payload, indent=2), encoding='utf-8')
            print(f"Saved progress: {progress_path}")

        if idx < len(companies):
            time.sleep(args.sleep)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    final_path = out_dir / f'company_intelligence_gemini_wasp_{ts}.json'
    final_payload = {
        'generated_at': datetime.now().isoformat(),
        'scope': 'wasp_adopters',
        'companies': scraper.intelligence_data,
    }
    final_path.write_text(__import__('json').dumps(final_payload, indent=2), encoding='utf-8')

    print(f"\nSaved final: {final_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
