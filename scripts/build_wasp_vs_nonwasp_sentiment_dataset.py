#!/usr/bin/env python3
"""Build a single labeled dataset for WASP vs non-WASP from sentiment CSVs.

Outputs: exports/wasp_vs_nonwasp_sentiment_<ts>.csv
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import argparse


def newest(glob_pat: str) -> str:
    files = sorted(Path('exports').glob(glob_pat), reverse=True)
    if not files:
        raise FileNotFoundError(glob_pat)
    return str(files[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wasp', default='', help='Path to wasp_website_sentiment_*.csv')
    ap.add_argument('--nonwasp', default='', help='Path to non_wasp_website_sentiment_*.csv')
    args = ap.parse_args()

    wasp_path = args.wasp or newest('wasp_website_sentiment_*.csv')
    non_path = args.nonwasp or newest('non_wasp_website_sentiment_*.csv')

    wasp = pd.read_csv(wasp_path)
    non = pd.read_csv(non_path)

    wasp['label_wasp'] = 1
    non['label_wasp'] = 0

    df = pd.concat([wasp, non], ignore_index=True)

    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    out = Path('exports') / f'wasp_vs_nonwasp_sentiment_{ts}.csv'
    df.to_csv(out, index=False)

    print('WASP:', wasp_path, 'rows=', len(wasp))
    print('NON:', non_path, 'rows=', len(non))
    print('OUT:', out, 'rows=', len(df))


if __name__ == '__main__':
    main()
