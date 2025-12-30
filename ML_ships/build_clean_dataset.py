import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

# =========================================================
# 1) POINT THIS TO YOUR FOLDER WITH JSON FILES
# =========================================================
DATA_DIR = Path(r"C:\Users\Isar\Desktop\ML_ships\data")  # <-- CHANGE THIS

# =========================================================
# 2) FILE PATTERNS
# =========================================================
BASE_PATTERNS = [
    "company_profiles_v3_structured_*.json",
    "company_intelligence_gemini_*.json",
    "company_intelligence_v2_progress.json",
]

WAPS_ADOPTER_PATTERNS = [
    "waps_adopters.json",  # <-- your file name
]

# =========================================================
# 3) TEXT QUALITY PARAMETERS
# =========================================================
MIN_TEXT_ITEMS = 3
MIN_MARITIME_MATCHES = 2

MARITIME_KEYWORDS = [
    "fleet", "vessel", "marine", "maritime", "ship", "shipping",
    "bulk", "tanker", "carrier", "container", "containers", "imo",
    "propulsion", "hull", "shipmanagement", "ro-ro", "roro"
]

BAD_KEYWORDS = [
    "wedding", "event rentals", "catalog", "bitcoin", "crypto",
    "cryptocurrency", "football", "quarterback", "restaurant",
    "tourism", "luxury tours", "skincare", "sportsmedia", "sports technology"
]

# =========================================================
# HELPERS
# =========================================================
def list_files(data_dir: Path, patterns: List[str]) -> List[Path]:
    fps: List[Path] = []
    for pat in patterns:
        fps.extend(sorted(data_dir.glob(pat)))
    return sorted(set(fps))


def load_json(fp: Path) -> Any:
    with fp.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_company_records(obj: Any, source_file: str, waps_adopted: int) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    # CASE 0: dict of companies keyed by company name (WAPS ADOPTER FORMAT)
    if isinstance(obj, dict) and "companies" not in obj and "company_name" not in obj:
        records = []
        for name, data in obj.items():
            if isinstance(data, dict):
                flat = {"company_name": name, **data}
                flat["_source_file"] = source_file
                flat["waps_adopted"] = int(waps_adopted)
                records.append(flat)
        return records

    # Case 1: { "companies": { "Name": {...}, ... } }
    if isinstance(obj, dict) and "companies" in obj and isinstance(obj["companies"], dict):
        for name, data in obj["companies"].items():
            flat = {"company_name": name, **(data if isinstance(data, dict) else {})}
            flat["_source_file"] = source_file
            flat["waps_adopted"] = int(waps_adopted)
            records.append(flat)
        return records

    # Case 2: single object with company_name
    if isinstance(obj, dict) and "company_name" in obj:
        out = dict(obj)
        out["_source_file"] = source_file
        out["waps_adopted"] = int(waps_adopted)
        return [out]

    # Case 3: list of objects
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                out = dict(item)
                out["_source_file"] = source_file
                out["waps_adopted"] = int(waps_adopted)
                records.append(out)
        return records

    print(f"⚠️ Unknown JSON format in {source_file}")
    return []


def extract_all_text(company: Dict[str, Any]) -> List[str]:
    """
    Supports BOTH:
      A) Old format: company['intelligence'][category]['findings'][...]['title'/'snippet']
      B) Adopter format: company['text_data']['website']['pages'][...]['text']
    Returns: list of text items (strings)
    """
    text_items: List[str] = []

    # ---- A) Existing pipeline format: intelligence/findings ----
    intelligence = company.get("intelligence", {})
    if isinstance(intelligence, dict):
        for _, data in intelligence.items():
            if not isinstance(data, dict):
                continue
            findings = data.get("findings", [])
            if not isinstance(findings, list):
                continue
            for f in findings:
                if not isinstance(f, dict):
                    continue
                title = f.get("title")
                snippet = f.get("snippet")
                if isinstance(title, str) and title.strip():
                    text_items.append(title.strip())
                if isinstance(snippet, str) and snippet.strip():
                    text_items.append(snippet.strip())

    # ---- B) Adopter file format: text_data/website/pages ----
    text_data = company.get("text_data", {})
    if isinstance(text_data, dict):
        website = text_data.get("website", {})
        if isinstance(website, dict):
            pages = website.get("pages", [])
            if isinstance(pages, list):
                for p in pages:
                    if not isinstance(p, dict):
                        continue
                    page_text = p.get("text")
                    if isinstance(page_text, str) and page_text.strip():
                        text_items.append(page_text.strip())

    return text_items


def count_keyword_matches(text_items: List[str], keywords: List[str]) -> int:
    count = 0
    for t in text_items:
        lower = t.lower()
        if any(kw in lower for kw in keywords):
            count += 1
    return count


def classify_text_quality(text_items: List[str]) -> str:
    if not text_items:
        return "none"

    bad_hits = count_keyword_matches(text_items, BAD_KEYWORDS)
    if bad_hits > 0:
        return "bad"

    maritime_hits = count_keyword_matches(text_items, MARITIME_KEYWORDS)

    if len(text_items) >= MIN_TEXT_ITEMS and maritime_hits >= MIN_MARITIME_MATCHES:
        return "good"

    return "bad"


def load_all_records(data_dir: Path) -> Tuple[List[Path], List[Dict[str, Any]]]:
    base_files = list_files(data_dir, BASE_PATTERNS)
    adopter_files = list_files(data_dir, WAPS_ADOPTER_PATTERNS)

    print(f"Found {len(base_files)} base JSON files.")
    print(f"Found {len(adopter_files)} WAPS-adopter JSON files.")

    all_records: List[Dict[str, Any]] = []

    for fp in base_files:
        try:
            obj = load_json(fp)
            all_records.extend(extract_company_records(obj, fp.name, waps_adopted=0))
        except Exception as e:
            print(f"❌ Error reading {fp.name}: {e}")

    for fp in adopter_files:
        try:
            obj = load_json(fp)
            all_records.extend(extract_company_records(obj, fp.name, waps_adopted=1))
        except Exception as e:
            print(f"❌ Error reading {fp.name}: {e}")

    print(f"Extracted {len(all_records)} total company records (flattened).")
    return base_files + adopter_files, all_records


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    _, raw_records = load_all_records(DATA_DIR)

    if not raw_records:
        raise SystemExit("No company records found. Check DATA_DIR + file patterns.")

    # Compute text fields & quality
    for company in raw_records:
        text_items = extract_all_text(company)
        company["text_items"] = text_items
        company["text_item_count"] = len(text_items)
        company["maritime_matches"] = count_keyword_matches(text_items, MARITIME_KEYWORDS)
        company["bad_matches"] = count_keyword_matches(text_items, BAD_KEYWORDS)
        company["text_quality"] = classify_text_quality(text_items)

    from collections import Counter
    print("\n=== QUALITY LABEL COUNTS ===")
    print(Counter([c["text_quality"] for c in raw_records]))

    print("\n=== WAPS ADOPTION LABEL COUNTS (raw) ===")
    print(Counter([c.get("waps_adopted", 0) for c in raw_records]))

    print("\n=== ADOPTER DEBUG (name | items | maritime | bad | quality) ===")
    for c in raw_records:
        if c.get("waps_adopted") == 1:
            print(
                c.get("company_name"),
                "| items:", c.get("text_item_count"),
                "| maritime:", c.get("maritime_matches"),
                "| bad:", c.get("bad_matches"),
                "| quality:", c.get("text_quality")
            )

    # Build clean dataset with only GOOD companies
    print("\nBuilding clean dataset with only GOOD companies...")

    clean_records = []
    for company in raw_records:
        if company["text_quality"] != "good":
            continue

        clean_text = " ".join(company["text_items"])

        # metadata may be in "metadata" (old) or "attributes" (adopters)
        metadata = company.get("metadata", {})
        attributes = company.get("attributes", {})

        if not isinstance(metadata, dict):
            metadata = {}
        if not isinstance(attributes, dict):
            attributes = {}

        vessel_count = metadata.get("vessel_count", attributes.get("vessel_count"))
        avg_emissions = metadata.get("avg_emissions", attributes.get("avg_emissions_tons"))
        avg_co2_distance = metadata.get("avg_co2_distance", attributes.get("avg_co2_per_distance"))

        clean_records.append({
            "company_name": company.get("company_name"),
            "clean_text": clean_text,
            "text_quality": company["text_quality"],
            "text_item_count": company["text_item_count"],
            "maritime_matches": company["maritime_matches"],
            "vessel_count": vessel_count,
            "avg_emissions": avg_emissions,
            "avg_co2_distance": avg_co2_distance,
            "waps_adopted": int(company.get("waps_adopted", 0)),
            "_source_file": company.get("_source_file"),
        })

    df = pd.DataFrame(clean_records)
    print(f"GOOD companies retained: {len(df)}")

    output_dir = DATA_DIR
    csv_path = output_dir / "companies_clean.csv"
    json_path = output_dir / "companies_clean.json"

    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)

    print("\nExport complete!")
    print(f"CSV saved to:  {csv_path}")
    print(f"JSON saved to: {json_path}")

    if "waps_adopted" in df.columns:
        print("\n=== WAPS ADOPTION LABEL COUNTS (clean GOOD-only) ===")
        print(df["waps_adopted"].value_counts(dropna=False))
