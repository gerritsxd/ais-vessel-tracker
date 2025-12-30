import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import statsmodels.api as sm


# ======================
# Load data
# ======================
df = pd.read_csv("companies_aggregated.csv")

FEATURES = [
    "sustainability_orientation_score",
    "innovation_orientation_score",
    "economic_orientation_score",
    "high_engagement_score",
    "operational_barriers_score",
    "sentiment_risk"
]

TARGET = "waps_adopted"


# ======================
# Correlation matrix
# ======================
corr_df = (
    df[FEATURES + [TARGET]]
    .apply(pd.to_numeric, errors="coerce")
    .dropna()
)

corr = corr_df.corr()

plt.figure(figsize=(8, 6))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0)
plt.title("Correlation Matrix – Core Predictors")
plt.tight_layout()
plt.show()


# ======================
# VIF calculation
# ======================
X_vif = (
    df[FEATURES]
    .apply(pd.to_numeric, errors="coerce")
    .dropna()
)

vif_df = pd.DataFrame({
    "feature": X_vif.columns,
    "VIF": [
        variance_inflation_factor(X_vif.values, i)
        for i in range(X_vif.shape[1])
    ]
})

print("\nVIF Results")
print(vif_df)

vif_df.to_csv("vif_results.csv", index=False)


# ======================
# Logistic Regression (ONE scaler)
# ======================
X = df[FEATURES].apply(pd.to_numeric, errors="coerce")
y = pd.to_numeric(df[TARGET], errors="coerce")

mask = X.notna().all(axis=1) & y.notna()
X = X[mask]
y = y[mask]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)


# sklearn (for clean coefficients)
logreg = LogisticRegression(
    penalty="l2",
    solver="liblinear"
)
logreg.fit(X_scaled, y)


# ======================
# Coefficients + odds ratios
# ======================
coef_df = pd.DataFrame({
    "feature": FEATURES,
    "coefficient": logreg.coef_[0],
    "odds_ratio": np.exp(logreg.coef_[0])
}).sort_values("odds_ratio", ascending=False)

print("\nLogistic Regression Coefficients")
print(coef_df)

coef_df.to_csv("logreg_coefficients.csv", index=False)


# ======================
# Statsmodels (CI + p-values)
# ======================
X_sm = sm.add_constant(X_scaled)
model = sm.Logit(y, X_sm).fit(disp=False)

summary = model.summary2().tables[1]

summary["odds_ratio"] = np.exp(summary["Coef."])
summary["ci_lower"] = np.exp(summary["Coef."] - 1.96 * summary["Std.Err."])
summary["ci_upper"] = np.exp(summary["Coef."] + 1.96 * summary["Std.Err."])

# Clean index names
summary.index = ["const"] + FEATURES

print("\nLogit model with confidence intervals")
print(summary)

summary.to_csv("logreg_coefficients_with_ci.csv")
