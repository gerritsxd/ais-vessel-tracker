import pandas as pd
from sklearn.preprocessing import StandardScaler
from pathlib import Path

# =========================================================
# CONFIG
# =========================================================
DATA_DIR = Path(r"C:\Users\isark\Desktop\ML_ships\key-data")
DATA_PATH = DATA_DIR / "companies_aggregated.csv"
COEF_PATH = DATA_DIR / "logreg_coefficients_with_ci.csv"   # you saved this earlier
OUT_PATH = DATA_DIR / "companies_with_waps_score.csv"

# Core features used in the model (MUST match training)
FEATURES = [
    "sustainability_orientation_score",
    "innovation_orientation_score",
    "economic_orientation_score",
    "high_engagement_score",
    "operational_barriers_score",
    "sentiment_risk"
]

# =========================================================
# 1. LOAD DATA
# =========================================================

df = pd.read_csv(DATA_PATH)
coef_df = pd.read_csv(COEF_PATH)

# Safety checks
missing = [f for f in FEATURES if f not in df.columns]
if missing:
    raise ValueError(f"Missing features in dataset: {missing}")

print(f"Loaded {len(df)} companies.")
print("Features used:", FEATURES)

# =========================================================
# 2. STANDARDIZE FEATURES (z-scores)
# =========================================================

scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[FEATURES])

X_scaled_df = pd.DataFrame(
    X_scaled,
    columns=[f"{f}_z" for f in FEATURES]
)

df = pd.concat([df, X_scaled_df], axis=1)

# =========================================================
# 3. BUILD WEIGHT VECTOR
# =========================================================

coef_map = dict(zip(coef_df["feature"], coef_df["Coef."]))

weights = []
for f in FEATURES:
    if f not in coef_map:
        raise ValueError(f"Coefficient missing for feature: {f}")
    weights.append(coef_map[f])

# =========================================================
# 4. COMPUTE ADOPTION SCORE
# =========================================================

z_cols = [f"{f}_z" for f in FEATURES]
df["waps_adoption_score"] = df[z_cols].dot(weights)

# =========================================================
# 4B. COMPUTE PERCENTILE-BASED SCORE (PRIMARY DISPLAY SCORE)
# =========================================================

df["waps_score_percentile"] = (
    df["waps_adoption_score"]
        .rank(pct=True) * 100
)


# =========================================================
# 5. RANK COMPANIES
# =========================================================

# =========================================================
# 5. RANK COMPANIES (BASED ON RAW SCORE)
# =========================================================

df["waps_rank"] = df["waps_adoption_score"].rank(
    ascending=False,
    method="dense"
)


# =========================================================
# 6. SAVE OUTPUT
# =========================================================

df.sort_values("waps_rank").to_csv(OUT_PATH, index=False)

print("\nWAPS adoption score computation complete.")
print(f"Saved to: {OUT_PATH}")

print("\nTop 10 companies by adoption score:")
print(
    df.sort_values("waps_rank")[
        [
            "company_name",
            "waps_score_percentile",
            "waps_rank",
            "waps_adopted"
        ]
    ].head(10)
)

