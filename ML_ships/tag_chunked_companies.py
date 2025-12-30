import pandas as pd
import re
from sklearn.preprocessing import MinMaxScaler

# =========================================================
# 1. LOAD CHUNK-LEVEL DATASET
# =========================================================

# 👉 This should be your chunk output file
df = pd.read_csv(r"C:\Users\isark\Desktop\ML_ships\data\company_text_chunks.csv")

# Safety checks
required_cols = {"company_name", "chunk_text", "waps_adopted"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["chunk_text"] = df["chunk_text"].fillna("").astype(str).str.lower()

print(f"Loaded {len(df)} text chunks from {df['company_name'].nunique()} companies.")

# =========================================================
# 2. DEFINE TAG LEXICONS (ETHNOGRAPHY-DERIVED)
# =========================================================

TAG_LEXICONS = {
    # --- ORIENTATION TAGS ---
    "sustainability_orientation": [
        "decarbon", "net-zero", "net zero", "esg", "climate", "renewable",
        "green shipping", "emissions reduction", "carbon intensity", "imo"
    ],
    "economic_orientation": [
        "cost", "profit", "roi", "operational savings", "lower opex",
        "efficiency", "financial", "margin"
    ],
    "innovation_orientation": [
        "pilot project", "r&d", "research", "innovation", "digitalisation",
        "cutting-edge", "testbed", "early adopter", "collaboration"
    ],
    "risk_aversion": [
        "proven solution", "safety", "compliance", "minimising risk",
        "established practice"
    ],
    "regulation_orientation": [
        "eu ets", "cii", "compliance", "regulation", "imo requirements",
        "penalties"
    ],
    "transparency_orientation": [
        "transparency", "disclosure", "report", "open data", "benchmarking"
    ],
    "skeptic_orientation": [
        "uncertain", "questionable", "greenwashing", "concern", "skeptic",
        "doubt", "challenge"
    ],

    # --- CONTENT & TONE TAGS ---
    "optimistic_tone": [
        "successful", "promising", "leading", "positive", "ahead of",
        "strong performance"
    ],
    "skeptical_tone": [
        "risk", "challenge", "barrier", "limitation", "uncertain",
        "difficult", "concern"
    ],
    "data_evidence": [
        "data", "benchmark", "metric", "percentage", "tonnes", "analysis"
    ],

    # --- ENGAGEMENT TAGS ---
    "high_engagement": [
        "strategy", "timeline", "pilot", "investment", "partnership",
        "roadmap", "implementation"
    ],
    "medium_engagement": [
        "exploring", "considering", "assessment"
    ],
    "low_engagement": [
        "delayed", "postponed", "not a priority", "budget limitation"
    ],

    # --- BARRIERS ---
    "financial_barriers": [
        "high cost", "expensive", "budget constraint", "investment challenge"
    ],
    "operational_barriers": [
        "retrofit", "crew training", "technical feasibility", "deck space"
    ],
    "knowledge_gap": [
        "lack of awareness", "lack of knowledge", "no information", "not familiar"
    ]
}

# =========================================================
# 3. TAG MATCHING (CHUNK-LEVEL)
# =========================================================

def count_matches(text, keywords):
    count = 0
    for kw in keywords:
        pattern = re.compile(re.escape(kw))
        count += len(pattern.findall(text))
    return count


for tag, lexicon in TAG_LEXICONS.items():
    df[f"{tag}_raw"] = df["chunk_text"].apply(lambda t: count_matches(t, lexicon))

# =========================================================
# 4. NORMALIZE TAG SCORES (GLOBAL, ACROSS ALL CHUNKS)
# =========================================================

raw_cols = [c for c in df.columns if c.endswith("_raw")]
scaler = MinMaxScaler()

if raw_cols:
    score_cols = [c.replace("_raw", "_score") for c in raw_cols]
    df[score_cols] = scaler.fit_transform(df[raw_cols])
else:
    raise RuntimeError("No raw tag columns found.")

# =========================================================
# 5. SAVE CHUNK-LEVEL OUTPUT
# =========================================================

out_path = r"C:\Users\isark\Desktop\ML_ships\data\nlp_tag_scores_chunks.csv"
df.to_csv(out_path, index=False)

print("\nTag scoring (chunk-level) complete.")
print(f"Saved to: {out_path}")
print("\nWAPS adoption distribution (chunks):")
print(df["waps_adopted"].value_counts())
