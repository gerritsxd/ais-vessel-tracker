#!/usr/bin/env python3
"""Export a regression-ready dataset for Econowind adopters.

What it does:
- Reads Econowind adopter labels from `config/econowind_adopters.txt`
- Loads latest intelligence + profile JSONs from `data/` (if present)
- Builds feature matrix (same as ML predictor)
- Adds label columns:
  - econowind_adoption (0/1)
  - wasp_adoption (0/1)
- Writes a CSV into `exports/` (gitignored)

Usage:
  python3 scripts/export_econowind_dataset.py
  python3 scripts/export_econowind_dataset.py --limit 500

Notes:
- This does NOT scrape new intel/profile data. Run the existing scrapers/services first if you want fresh data.
"""

import sys
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

from src.ml.predictor import CompanyMLPredictor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='Optional limit on number of companies exported (0 = all)')
    args = ap.parse_args()

    predictor = CompanyMLPredictor()

    # Load/merge company data
    intelligence = predictor.load_intelligence_data()
    profile = predictor.load_profile_data()

    all_companies = set(intelligence.keys()) | set(profile.keys())
    if not all_companies:
        print("No intelligence/profile data found in data/.\n")
        print("Run one of these first, then re-run export:")
        print("- python src/services/intelligence_scraper_service.py")
        print("- python src/services/company_profiler_service.py")
        return 2

    merged = {}
    for name in all_companies:
        m = {}
        if name in intelligence:
            m.update(intelligence[name])
        if name in profile:
            m.update(profile[name])
        if m:
            merged[name] = m

    X, company_names = predictor.feature_extractor.build_feature_matrix(merged)

    if args.limit and args.limit > 0:
        company_names = company_names[: args.limit]
        X = X.loc[company_names]

    # Labels
    wasp_adopters = predictor.get_wasp_adopters()
    econ_adopters = predictor.get_econowind_adopters()

    y_wasp = [1 if predictor._check_wasp_match(n, wasp_adopters) else 0 for n in company_names]
    y_econ = [1 if predictor._check_econowind_match(n, econ_adopters) else 0 for n in company_names]

    df = X.copy()
    df.insert(0, 'company_name', company_names)
    df['wasp_adoption'] = y_wasp
    df['econowind_adoption'] = y_econ

    # Output
    exports_dir = project_root / 'exports'
    exports_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    out_path = exports_dir / f"econowind_regression_dataset_{ts}.csv"
    df.to_csv(out_path, index=False)

    print(f"Exported: {out_path}")
    print(f"Rows: {len(df)}")
    print(f"Econowind positives: {sum(y_econ)}")
    print(f"WASP positives: {sum(y_wasp)}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
