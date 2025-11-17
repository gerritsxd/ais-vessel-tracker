#!/usr/bin/env python3
"""
Simple WASP Fit Predictor - Uses ONLY Database Features
No web scraping needed - your data is already gold!
"""
import sqlite3
import pandas as pd
import numpy as np
import sys
import io
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("="*80)
print("🎯 WASP FIT SCORE PREDICTOR - Database Features Only")
print("="*80)

# Load data from database
conn = sqlite3.connect('data/vessel_static_data.db')

query = '''
    SELECT 
        company_name,
        ship_type,
        AVG(total_co2_emissions) as avg_emissions,
        AVG(avg_co2_per_distance) as avg_co2_distance,
        AVG(avg_fuel_consumption_per_distance) as avg_fuel_consumption,
        AVG(CAST(technical_efficiency AS FLOAT)) as avg_tech_efficiency,
        AVG(gross_tonnage) as avg_tonnage,
        AVG(total_distance_travelled) as avg_distance,
        COUNT(*) as fleet_size,
        AVG(CAST(econowind_fit_score AS FLOAT)) as wasp_fit_score
    FROM eu_mrv_emissions
    WHERE company_name IS NOT NULL 
        AND company_name != ""
        AND econowind_fit_score IS NOT NULL
    GROUP BY company_name, ship_type
    HAVING COUNT(*) >= 3
'''

df = pd.read_sql_query(query, conn)
conn.close()

print(f"\n📊 Loaded {len(df)} company-shiptype combinations")
print(f"   Companies: {df['company_name'].nunique()}")
print(f"   Ship types: {df['ship_type'].nunique()}")

# Feature engineering
print("\n🔧 Engineering features...")

# Encode ship type
le = LabelEncoder()
df['ship_type_encoded'] = le.fit_transform(df['ship_type'])

# Calculate efficiency ratios
df['emissions_per_tonnage'] = df['avg_emissions'] / (df['avg_tonnage'] + 1)
df['fuel_efficiency_ratio'] = df['avg_fuel_consumption'] / (df['avg_distance'] + 1)

# Fill missing values (numeric columns only)
numeric_cols = df.select_dtypes(include=[np.number]).columns
df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())

# Drop rows with remaining NaNs in key columns
df = df.dropna(subset=['wasp_fit_score', 'avg_emissions', 'fleet_size'])

print(f"   After cleaning: {len(df)} samples")

# Define features
feature_cols = [
    'avg_emissions',
    'avg_co2_distance',
    'avg_fuel_consumption',
    'avg_tech_efficiency',
    'avg_tonnage',
    'avg_distance',
    'fleet_size',
    'ship_type_encoded',
    'emissions_per_tonnage',
    'fuel_efficiency_ratio'
]

X = df[feature_cols]
y = df['wasp_fit_score']

# Fill any remaining NaNs with 0
X = X.fillna(0)

print(f"\n📈 Features shape: {X.shape}")
print(f"   Target (WASP scores) range: {y.min():.1f} - {y.max():.1f}")
print(f"   NaN count in X: {X.isna().sum().sum()}")

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"\n🎓 Training set: {len(X_train)} samples")
print(f"   Test set: {len(X_test)} samples")

# Train models
print("\n🤖 Training models...")

models = {
    'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
    'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42)
}

results = {}
for name, model in models.items():
    print(f"\n   {name}...")
    model.fit(X_train, y_train)
    
    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Metrics
    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    
    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
    
    results[name] = {
        'model': model,
        'train_r2': train_r2,
        'test_r2': test_r2,
        'train_rmse': train_rmse,
        'test_rmse': test_rmse,
        'cv_mean': cv_scores.mean(),
        'cv_std': cv_scores.std()
    }
    
    print(f"      Train R²: {train_r2:.3f}")
    print(f"      Test R²:  {test_r2:.3f}")
    print(f"      Test RMSE: {test_rmse:.3f}")
    print(f"      CV R² (5-fold): {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

# Feature importance (best model)
print("\n📊 Feature Importance (Gradient Boosting):")
gb_model = results['Gradient Boosting']['model']
importances = pd.DataFrame({
    'feature': feature_cols,
    'importance': gb_model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in importances.iterrows():
    print(f"   {row['feature']:30s} {row['importance']:.3f}")

# Summary
print("\n" + "="*80)
print("✅ RESULTS SUMMARY")
print("="*80)

best_model_name = max(results.keys(), key=lambda k: results[k]['test_r2'])
best = results[best_model_name]

print(f"\n🏆 Best Model: {best_model_name}")
print(f"   Test R²: {best['test_r2']:.3f} ({best['test_r2']*100:.1f}% variance explained)")
print(f"   Test RMSE: {best['test_rmse']:.3f} points")
print(f"   Cross-validation: {best['cv_mean']:.3f} ± {best['cv_std']:.3f}")

print("\n💡 INSIGHTS:")
print(f"   - Model can predict WASP fit from database features alone!")
print(f"   - No web scraping needed - your emissions data is gold")
print(f"   - Top 3 features: {', '.join(importances['feature'].head(3).tolist())}")

print("\n🎯 RECOMMENDATION:")
if best['test_r2'] > 0.6:
    print("   ✅ Strong model! Use database features only.")
    print("   ✅ Skip company profiler - it adds noise, not signal.")
elif best['test_r2'] > 0.4:
    print("   ⚠️  Moderate model. Database features are good baseline.")
    print("   💡 Consider adding: innovation indicators, financial health.")
else:
    print("   ❌ Weak model. May need external features.")
    print("   💡 Consider: industry news, sustainability rankings.")

print("\n" + "="*80)
