#!/usr/bin/env python3
"""Export sentiment from WASP company websites (About/Mission/Sustainability pages).

Reads the latest (or progress) WASP profiles produced by run_profiler_v3_for_wasp.py.
Outputs a CSV into exports/ for regression.

Usage:
  python3 scripts/export_wasp_website_sentiment.py
  python3 scripts/export_wasp_website_sentiment.py --input data/company_profiles_v3_structured_wasp_progress.json
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

from textblob import TextBlob


def _pick_best_input() -> Path:
    data_dir = Path('data')
    prog = data_dir / 'company_profiles_v3_structured_wasp_progress.json'
    latest = sorted(data_dir.glob('company_profiles_v3_structured_wasp_*.json'), reverse=True)

    cand = []
    if prog.exists():
        cand.append(prog)
    if latest:
        cand.append(latest[0])

    best = None
    best_n = -1
    for c in cand:
        try:
            data = json.loads(c.read_text(encoding='utf-8'))
            n = len(data.get('companies', {}) or {})
            if n > best_n:
                best_n = n
                best = c
        except Exception:
            continue

    if best is None:
        raise FileNotFoundError('No WASP profiles found')
    return best



def is_aboutish(page_type: str) -> bool:
    s = (page_type or '').lower()
    keys = ['about', 'company', 'mission', 'values', 'sustainability', 'environment', 'esg']
    return any(k in s for k in keys)


def polarity(text: str) -> float:
    if not text:
        return 0.0
    return float(TextBlob(text).sentiment.polarity)


def subjectivity(text: str) -> float:
    if not text:
        return 0.0
    return float(TextBlob(text).sentiment.subjectivity)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='', help='Optional path to a specific WASP profiles JSON')
    args = ap.parse_args()

    data_dir = Path('data')
    if args.input:
        in_path = Path(args.input)
    else:
        try:
            in_path = _pick_best_input()
        except Exception:
            print('No WASP profiles found. Run scripts/run_profiler_v3_for_wasp.py first.')
            return 2

    data = json.loads(in_path.read_text(encoding='utf-8'))
    companies = data.get('companies', {}) or {}

    rows = []
    for company_name, profile in companies.items():
        website = (profile.get('text_data') or {}).get('website') or {}
        pages = website.get('pages') or []

        about_pages = [p for p in pages if is_aboutish(p.get('page_type', ''))]
        if not about_pages:
            # fall back to all pages if nothing matched
            about_pages = pages

        combined = ' '.join([p.get('text', '') for p in about_pages if p.get('text')])

        rows.append({
            'company_name': company_name,
            'num_pages_total': len(pages),
            'num_pages_aboutish': len(about_pages),
            'text_len': len(combined),
            'polarity': polarity(combined),
            'subjectivity': subjectivity(combined),
        })

    exports_dir = Path('exports')
    exports_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    out_path = exports_dir / f'wasp_website_sentiment_{ts}.csv'

    import csv
    with out_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['company_name'])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f'Wrote: {out_path} (rows={len(rows)}) from {in_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
