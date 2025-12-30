import pandas as pd
from pathlib import Path

# ==========================
# CONFIG
# ==========================

DATA_DIR = Path(r"C:\Users\isark\Desktop\ML_ships\data")
INPUT_CSV = DATA_DIR / "nlp_with_finbert.csv"
OUTPUT_CSV = DATA_DIR / "companies_aggregated.csv"

# ==========================
# LOAD DATA
# ==========================

df = pd.read_csv(INPUT_CSV)

print(f"Loaded {len(df)} chunks from {df['company_name'].nunique()} companies.")

# Keep only relevant chunks (you already cleaned, but safety check)
df = df[df["irrelevant_chunk"] == False].copy()

# ==========================
# DEFINE COLUMN GROUPS
# ==========================

TAG_SCORE_COLS = [
    "sustainability_orientation_score",
    "economic_orientation_score",
    "innovation_orientation_score",
    "risk_aversion_score",
    "regulation_orientation_score",
    "transparency_orientation_score",
    "skeptic_orientation_score",
    "optimistic_tone_score",
    "skeptical_tone_score",
    "data_evidence_score",
    "high_engagement_score",
    "medium_engagement_score",
    "low_engagement_score",
    "financial_barriers_score",
    "operational_barriers_score",
    "knowledge_gap_score",
]

TAG_RAW_COLS = [
    "sustainability_orientation_raw",
    "economic_orientation_raw",
    "innovation_orientation_raw",
    "risk_aversion_raw",
    "regulation_orientation_raw",
    "transparency_orientation_raw",
    "skeptic_orientation_raw",
    "optimistic_tone_raw",
    "skeptical_tone_raw",
    "data_evidence_raw",
    "high_engagement_raw",
    "medium_engagement_raw",
    "low_engagement_raw",
    "financial_barriers_raw",
    "operational_barriers_raw",
    "knowledge_gap_raw",
]

SENTIMENT_COLS = [
    "finbert_compound",
    "sentiment_sustainability",
    "sentiment_innovation",
    "sentiment_cost",
    "sentiment_risk",
]

# ==========================
# AGGREGATION
# ==========================

grouped = df.groupby("company_name")

agg_dict = {}

# Mean tag scores
for col in TAG_SCORE_COLS:
    agg_dict[col] = "mean"

# Max raw counts (did it appear at all?)
for col in TAG_RAW_COLS:
    agg_dict[col] = "max"

# Sentiment averages
for col in SENTIMENT_COLS:
    agg_dict[col] = "mean"

# Meta features
agg_dict["chunk_id"] = "count"
agg_dict["nonzero_tags"] = "mean"

# WAPS adoption (binary, should be constant per company)
agg_dict["waps_adopted"] = "max"

company_df = grouped.agg(agg_dict).reset_index()

# Rename meta columns
company_df = company_df.rename(columns={
    "chunk_id": "n_chunks",
    "nonzero_tags": "avg_nonzero_tags_per_chunk"
})

# ==========================
# POST-CHECKS
# ==========================

print("\n=== AGGREGATION SUMMARY ===")
print(company_df[["company_name", "n_chunks", "waps_adopted"]].head())

print("\nWAPS adoption distribution (company-level):")
print(company_df["waps_adopted"].value_counts())

print("\nChunk count stats:")
print(company_df["n_chunks"].describe())

# ==========================
# SAVE
# ==========================

company_df.to_csv(OUTPUT_CSV, index=False)
print(f"\nAggregation complete.")
print(f"Saved to: {OUTPUT_CSV}")
