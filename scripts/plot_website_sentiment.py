#!/usr/bin/env python3
"""Plot normalized sentiment features from website sentiment CSV.

Input CSV columns (expected):
- company_name
- num_pages_total
- num_pages_aboutish
- text_len
- polarity
- subjectivity

Outputs PNG plots to exports/plots/.

Normalization:
- text_len: log1p then z-score
- polarity, subjectivity: z-score

Usage:
  python3 scripts/plot_website_sentiment.py --input wasp_website_sentiment_*.csv
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


@dataclass
class NormSpec:
    col: str
    transform: str  # 'z' or 'log1p_z'


def zscore(x: pd.Series) -> pd.Series:
    x = pd.to_numeric(x, errors='coerce').fillna(0.0)
    std = float(x.std(ddof=0))
    if std == 0.0:
        return x * 0.0
    return (x - float(x.mean())) / std


def log1p_zscore(x: pd.Series) -> pd.Series:
    x = pd.to_numeric(x, errors='coerce').fillna(0.0)
    return zscore(np.log1p(x))


def normalize(df: pd.DataFrame, specs: list[NormSpec]) -> pd.DataFrame:
    out = df.copy()
    for s in specs:
        if s.transform == 'z':
            out[f'{s.col}_z'] = zscore(out[s.col])
        elif s.transform == 'log1p_z':
            out[f'{s.col}_log1p_z'] = log1p_zscore(out[s.col])
        else:
            raise ValueError(f'Unknown transform: {s.transform}')
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--outdir', default='exports/plots')
    ap.add_argument('--title', default='Website sentiment features (normalized)')
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise SystemExit(f'Input not found: {in_path}')

    df = pd.read_csv(in_path)
    for c in ['company_name', 'text_len', 'polarity', 'subjectivity', 'num_pages_total', 'num_pages_aboutish']:
        if c not in df.columns:
            raise SystemExit(f'Missing required column: {c}')

    df['text_len'] = pd.to_numeric(df['text_len'], errors='coerce').fillna(0).astype(int)
    df['polarity'] = pd.to_numeric(df['polarity'], errors='coerce').fillna(0.0)
    df['subjectivity'] = pd.to_numeric(df['subjectivity'], errors='coerce').fillna(0.0)

    df_norm = normalize(
        df,
        [
            NormSpec('text_len', 'log1p_z'),
            NormSpec('polarity', 'z'),
            NormSpec('subjectivity', 'z'),
        ],
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')

    sns.set_theme(style='whitegrid')

    # 1) Coverage plot
    fig, ax = plt.subplots(figsize=(10, 4.5))
    df_norm = df_norm.sort_values('text_len', ascending=False)
    ax.bar(df_norm['company_name'], df_norm['text_len'])
    ax.set_title('Scrape coverage (text_len per company)')
    ax.set_ylabel('text_len (chars)')
    ax.set_xlabel('company')
    ax.tick_params(axis='x', labelrotation=45)
    for t in ax.get_xticklabels():
        t.set_ha('right')
    fig.tight_layout()
    p1 = outdir / f'coverage_text_len_{ts}.png'
    fig.savefig(p1, dpi=180)
    plt.close(fig)

    # 2) Normalized distributions
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    sns.histplot(df_norm['text_len_log1p_z'], ax=axes[0], kde=True)
    axes[0].set_title('text_len (log1p z-score)')
    sns.histplot(df_norm['polarity_z'], ax=axes[1], kde=True)
    axes[1].set_title('polarity (z-score)')
    sns.histplot(df_norm['subjectivity_z'], ax=axes[2], kde=True)
    axes[2].set_title('subjectivity (z-score)')
    fig.suptitle(args.title)
    fig.tight_layout()
    p2 = outdir / f'normalized_distributions_{ts}.png'
    fig.savefig(p2, dpi=180)
    plt.close(fig)

    # 3) Scatter: polarity vs subjectivity sized by text_len
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    sizes = np.clip(df_norm['text_len'].to_numpy(), 0, None)
    # scale bubble sizes for visibility
    s = (np.sqrt(sizes + 1) * 8).clip(10, 220)
    ax.scatter(df_norm['polarity'], df_norm['subjectivity'], s=s, alpha=0.75)
    for _, r in df_norm.iterrows():
        ax.annotate(r['company_name'][:18], (r['polarity'], r['subjectivity']), fontsize=8, alpha=0.8)
    ax.set_title('polarity vs subjectivity (bubble size ~ text_len)')
    ax.set_xlabel('polarity')
    ax.set_ylabel('subjectivity')
    fig.tight_layout()
    p3 = outdir / f'polarity_vs_subjectivity_{ts}.png'
    fig.savefig(p3, dpi=180)
    plt.close(fig)

    # 4) Per-company normalized feature bars
    fig, ax = plt.subplots(figsize=(10, 4.8))
    feat = df_norm[['company_name', 'text_len_log1p_z', 'polarity_z', 'subjectivity_z']].copy()
    feat = feat.sort_values('company_name')
    x = np.arange(len(feat))
    w = 0.28
    ax.bar(x - w, feat['text_len_log1p_z'], width=w, label='text_len_log1p_z')
    ax.bar(x, feat['polarity_z'], width=w, label='polarity_z')
    ax.bar(x + w, feat['subjectivity_z'], width=w, label='subjectivity_z')
    ax.axhline(0, color='black', linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(feat['company_name'], rotation=45)
    for t in ax.get_xticklabels():
        t.set_ha('right')
    ax.set_title('Normalized features per company (z-scores)')
    ax.legend()
    fig.tight_layout()
    p4 = outdir / f'normalized_features_by_company_{ts}.png'
    fig.savefig(p4, dpi=180)
    plt.close(fig)

    print('Saved plots:')
    print(' -', p1)
    print(' -', p2)
    print(' -', p3)
    print(' -', p4)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
