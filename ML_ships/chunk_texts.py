import pandas as pd
from pathlib import Path
import math

# ==========================
# CONFIG
# ==========================

DATA_DIR = Path(r"C:\Users\isark\Desktop\ML_ships\data")
INPUT_CSV = DATA_DIR / "companies_merged_80_core.csv"
OUTPUT_CSV = DATA_DIR / "company_text_chunks.csv"

CHUNK_SIZE = 400      # words
CHUNK_OVERLAP = 100   # words


# ==========================
# CHUNK FUNCTION
# ==========================

def chunk_text(text, chunk_size=400, overlap=100):
    """
    Split text into overlapping word chunks.
    Returns a list of chunk strings.
    """
    if not isinstance(text, str) or not text.strip():
        return []

    words = text.split()
    chunks = []

    step = chunk_size - overlap
    if step <= 0:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

    for start in range(0, len(words), step):
        end = start + chunk_size
        chunk_words = words[start:end]
        if len(chunk_words) < 50:  # drop tiny fragments
            continue
        chunks.append(" ".join(chunk_words))

    return chunks


# ==========================
# MAIN
# ==========================

if __name__ == "__main__":
    df = pd.read_csv(INPUT_CSV)

    required_cols = ["company_name", "clean_text", "waps_adopted"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    print(f"Loaded {len(df)} companies for chunking.")

    rows = []

    for _, row in df.iterrows():
        company = row["company_name"]
        text = row["clean_text"]
        adopted = row["waps_adopted"]

        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            rows.append({
                "company_name": company,
                "chunk_id": i,
                "chunk_text": chunk,
                "chunk_length": len(chunk.split()),
                "waps_adopted": adopted
            })

    chunk_df = pd.DataFrame(rows)

    print(f"Created {len(chunk_df)} text chunks.")
    print("\nChunks per company (summary):")
    print(chunk_df.groupby("company_name").size().describe())

    chunk_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    print(f"\nSaved chunk dataset to: {OUTPUT_CSV}")
