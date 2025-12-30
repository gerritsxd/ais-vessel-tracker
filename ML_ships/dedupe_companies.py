import pandas as pd
from pathlib import Path
from rapidfuzz import fuzz
import re

# ==========================
# CONFIG
# ==========================

DATA_DIR = Path(r"C:\Users\Isar\Desktop\ML_ships\data")
CSV_PATH = DATA_DIR / "companies_clean.csv"

# Fuzzy match threshold (core-to-core similarity)
SIMILARITY_THRESHOLD = 80


# ==========================
# NAME NORMALIZATION
# ==========================

LEGAL_SUFFIXES = [
    "ltd", "ltd.", "limited",
    "inc", "inc.", "corporation", "corp", "corp.",
    "sa", "s.a", "s.a.", "gmbh",
    "pte", "pte.", "plc", "llc", "llp",
    "co", "co.", "bv", "bv.", "company"
]

GENERIC_WORDS = set([
    "ship", "shipping", "shipmanagement",
    "international", "marine", "trading",
    "management", "services"
])


def clean_name(name: str) -> str:
    """Remove legal suffixes and punctuation, but KEEP industry words."""
    if not isinstance(name, str):
        return ""

    name = name.lower()

    # Remove legal suffixes only
    for suffix in LEGAL_SUFFIXES:
        name = re.sub(rf"\b{suffix}\b", "", name)

    # Remove punctuation / symbols
    name = re.sub(r"[^a-z0-9 ]+", " ", name)

    # Collapse multiple spaces
    name = " ".join(name.split())
    return name


def extract_core(name: str) -> str:
    """
    Extract the company core identity.
    Keeps first 1–2 meaningful tokens (not generic shipping words).
    """
    tokens = name.split()
    core_tokens = [t for t in tokens if t not in GENERIC_WORDS]

    if not core_tokens:
        return name

    return " ".join(core_tokens[:2])


# ==========================
# FUZZY GROUPING
# ==========================

def fuzzy_group(names, threshold=80):
    groups = []
    used = set()

    cleaned = {name: clean_name(name) for name in names}
    cores = {name: extract_core(cleaned[name]) for name in names}

    for name in names:
        if name in used:
            continue

        group = [name]
        used.add(name)

        for other in names:
            if other in used:
                continue

            score = fuzz.partial_ratio(cores[name], cores[other])

            if score >= threshold:
                group.append(other)
                used.add(other)

        groups.append(group)

    return groups


# ==========================
# MERGE GROUPS
# ==========================

def merge_group(df, group):
    """Merge all names in this fuzzy group into a single record."""
    subset = df[df["company_name"].isin(group)]

    # Canonical name = longest (most descriptive)
    canonical_name = max(group, key=len)

    # Merge text
    merged_text = " ".join(subset["clean_text"].dropna().astype(str))

    # Metadata (take maximum available)
    vessel_count = subset["vessel_count"].max()
    avg_emissions = subset["avg_emissions"].max()
    avg_co2_distance = subset["avg_co2_distance"].max()

    # ✅ WAPS adoption logic
    # If ANY company in the group adopted WAPS → merged company adopted
    waps_adopted = int(subset["waps_adopted"].max())

    # Optional diagnostics
    adopter_count = int(subset["waps_adopted"].sum())

    return {
        "company_name": canonical_name,
        "merged_names": group,
        "clean_text": merged_text,
        "text_length": len(merged_text),
        "vessel_count": vessel_count,
        "avg_emissions": avg_emissions,
        "avg_co2_distance": avg_co2_distance,
        "waps_adopted": waps_adopted,          # ✅ KEEP LABEL
        "adopter_records_in_group": adopter_count  # optional but useful
    }


# ==========================
# MAIN EXECUTION
# ==========================

if __name__ == "__main__":
    df = pd.read_csv(CSV_PATH)

    # Safety check
    if "waps_adopted" not in df.columns:
        raise ValueError("waps_adopted column not found in input CSV.")

    names = df["company_name"].tolist()

    print(f"Loaded {len(df)} companies for fuzzy dedupe.")
    print("\nComputing core-based fuzzy groups...\n")

    groups = fuzzy_group(names, threshold=SIMILARITY_THRESHOLD)

    print(f"Found {len(groups)} deduplicated groups (from {len(df)} companies).")

    print("\nSample groups:")
    for g in groups[:10]:
        print(" →", g)

    # Merge each group
    merged_records = [merge_group(df, group) for group in groups]
    merged_df = pd.DataFrame(merged_records)

    out_path = DATA_DIR / "companies_merged_80_core.csv"
    merged_df.to_csv(out_path, index=False, encoding="utf-8")

    print("\nDEDUPLICATION COMPLETE.")
    print(f"Saved merged dataset to: {out_path}")
    print(f"Final unique companies after fuzzy merge: {len(merged_df)}")

    print("\n=== WAPS ADOPTION COUNTS (MERGED) ===")
    print(merged_df["waps_adopted"].value_counts(dropna=False))
