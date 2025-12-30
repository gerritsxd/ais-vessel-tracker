import pandas as pd

# =========================================================
# 1. LOAD CHUNKED DATA
# =========================================================
df = pd.read_csv(
    r"C:\Users\isark\Desktop\ML_ships\data\nlp_tag_scores_chunks.csv"
)

# If chunk_length not already present, uncomment:
# df["chunk_length"] = df["chunk_text"].str.len()

# =========================================================
# 2. TAG SIGNAL PER CHUNK
# =========================================================
tag_cols = [c for c in df.columns if c.endswith("_raw")]

df["nonzero_tags"] = df[tag_cols].sum(axis=1)

# =========================================================
# 3. FLAG IRRELEVANT CHUNKS
# =========================================================
df["irrelevant_chunk"] = False

df.loc[df["chunk_length"] < 200, "irrelevant_chunk"] = True
df.loc[df["nonzero_tags"] == 0, "irrelevant_chunk"] = True

print("\n=== IRRELEVANT CHUNKS (sample) ===")
print(
    df[df["irrelevant_chunk"]][
        ["company_name", "chunk_id", "chunk_length", "nonzero_tags"]
    ].head(20)
)


company_summary = (
    df.groupby("company_name")
    .agg(
        total_chunks=("chunk_id", "count"),
        good_chunks=("irrelevant_chunk", lambda x: (~x).sum()),
        total_tag_signal=("nonzero_tags", "sum"),
        avg_chunk_length=("chunk_length", "mean"),
    )
    .reset_index()
)

company_summary["irrelevant_company"] = company_summary["good_chunks"] == 0


relevant_companies = company_summary.loc[
    company_summary["irrelevant_company"] == False, "company_name"
]

df_clean = df[df["company_name"].isin(relevant_companies)].reset_index(drop=True)

print("\n=== DATASET SIZE AFTER FILTERING ===")
print(len(df_clean))


df_clean.to_csv("nlp_filtered_chunks.csv", index=False)
company_summary.to_csv("nlp_company_summary.csv", index=False)

print("Saved:")
print("- nlp_filtered_chunks.csv")
print("- nlp_company_summary.csv")
