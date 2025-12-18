#!/usr/bin/env python3
"""Export sentiment from NON-WASP company websites.

Reads the latest (or progress) non-wasp profiles JSON and writes a CSV to exports/.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from textblob import TextBlob


def is_aboutish(page_type: str) -> bool:
    s = (page_type or '').lower()
    keys = ['about', 'company', 'our-story', 'mission', 'values', 'sustainability', 'esg', 'environment']
    return any(k in s for k in keys)


def _pick_best_input() -> Path:
    data_dir = Path('data')
    prog = data_dir / 'company_profiles_v3_structured_non_wasp_progress.json'
    latest = sorted(data_dir.glob('company_profiles_v3_structured_non_wasp_*.json'), reverse=True)
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
        raise FileNotFoundError
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='')
    args = ap.parse_args()

    if args.input:
        in_path = Path(args.input)
    else:
        try:
            in_path = _pick_best_input()
        except Exception:
            print('No non-wasp profiles found. Run scripts/run_profiler_v3_for_non_wasp.py first.')
            return 2

    data = json.loads(in_path.read_text(encoding='utf-8'))
    companies = data.get('companies', {}) or {}

    rows = []
    for company_name, profile in companies.items():
        website = (profile.get('text_data') or {}).get('website') or {}
        pages = website.get('pages') or []
        about_pages = [p for p in pages if is_aboutish(p.get('page_type', ''))]
        if not about_pages:
            about_pages = pages
        combined = ' '.join([p.get('text', '') for p in about_pages if p.get('text')])
        blob = TextBlob(combined) if combined else None

        rows.append({
            'company_name': company_name,
            'num_pages_total': len(pages),
            'num_pages_aboutish': len(about_pages),
            'text_len': len(combined),
            'polarity': float(blob.sentiment.polarity) if blob else 0.0,
            'subjectivity': float(blob.sentiment.subjectivity) if blob else 0.0,
        })

    exports_dir = Path('exports')
    exports_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    out_path = exports_dir / f'non_wasp_website_sentiment_{ts}.csv'

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
