"""
ML/NLP Prediction Service for Company Intelligence
Uses sentiment analysis, feature engineering, and classification models to predict:
- WASP adoption likelihood
- Sustainability focus classification
- Company type classification
"""

import json
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import re

# ML Libraries
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    import pickle
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("Warning: scikit-learn not installed. Install with: pip install scikit-learn")

# NLP Libraries (lightweight)
try:
    from textblob import TextBlob
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    print("Warning: textblob not installed. Install with: pip install textblob")


class CompanyMLPredictor:
    """
    ML/NLP service for predicting company characteristics from intelligence data.
    """
    
    def __init__(self, db_path: str = "data/vessel_static_data.db"):
        self.db_path = db_path
        self.models = {}
        self.scalers = {}
        self.vectorizers = {}
        self.feature_names = []
        
    def load_intelligence_data(self) -> Dict[str, Any]:
        """Load latest company intelligence JSON file."""
        data_dir = Path("data")
        
        # Find latest Gemini intelligence file
        intel_files = sorted(
            data_dir.glob("company_intelligence_gemini_*.json"),
            reverse=True
        )
        
        if not intel_files:
            print("No intelligence data found")
            return {}
        
        latest_file = intel_files[0]
        print(f"Loading intelligence data from: {latest_file.name}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('companies', {})
    
    def load_profile_data(self) -> Dict[str, Any]:
        """Load latest company profile V3 JSON file."""
        data_dir = Path("data")
        
        # Find latest V3 structured profile file
        profile_files = sorted(
            data_dir.glob("company_profiles_v3_structured_*.json"),
            reverse=True
        )
        
        if not profile_files:
            print("No profile data found")
            return {}
        
        latest_file = profile_files[0]
        print(f"Loading profile data from: {latest_file.name}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('companies', {})
    
    def get_wasp_adopters(self) -> Dict[str, bool]:
        """Get companies that have adopted WASP (ground truth labels)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get companies with wind-assisted vessels
        cursor.execute('''
            SELECT DISTINCT e.company_name
            FROM eu_mrv_emissions e
            INNER JOIN vessels_static v ON e.imo = v.imo
            WHERE v.wind_assisted = 1
            AND e.company_name IS NOT NULL
        ''')
        
        wasp_companies = {row[0]: True for row in cursor.fetchall()}
        
        # Also check wind_propulsion table by company name matching
        cursor.execute('''
            SELECT DISTINCT e.company_name
            FROM eu_mrv_emissions e
            INNER JOIN wind_propulsion w ON UPPER(TRIM(e.vessel_name)) = UPPER(TRIM(w.vessel_name))
            WHERE e.company_name IS NOT NULL
        ''')
        
        for row in cursor.fetchall():
            wasp_companies[row[0]] = True
        
        conn.close()
        return wasp_companies
    
    def extract_text_features(self, company_data: Dict[str, Any]) -> str:
        """Extract all text from intelligence findings for NLP."""
        text_parts = []
        
        # From intelligence data
        if 'intelligence' in company_data:
            for category, cat_data in company_data['intelligence'].items():
                findings = cat_data.get('findings', [])
                for finding in findings:
                    text_parts.append(finding.get('title', ''))
                    text_parts.append(finding.get('snippet', ''))
        
        # From profile data (text_data)
        if 'text_data' in company_data:
            wiki = company_data['text_data'].get('wikipedia', {})
            if wiki.get('summary'):
                text_parts.append(wiki['summary'])
            
            website = company_data['text_data'].get('website', {})
            for page in website.get('pages', []):
                text_parts.append(page.get('text', ''))
        
        return ' '.join(text_parts)
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Perform sentiment analysis on text."""
        if not NLP_AVAILABLE or not text:
            return {
                'polarity': 0.0,
                'subjectivity': 0.0,
                'positive_score': 0.0,
                'negative_score': 0.0
            }
        
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            subjectivity = blob.sentiment.subjectivity  # 0 to 1
            
            # Simple positive/negative classification
            positive_score = max(0, polarity)
            negative_score = abs(min(0, polarity))
            
            return {
                'polarity': float(polarity),
                'subjectivity': float(subjectivity),
                'positive_score': float(positive_score),
                'negative_score': float(negative_score)
            }
        except:
            return {
                'polarity': 0.0,
                'subjectivity': 0.0,
                'positive_score': 0.0,
                'negative_score': 0.0
            }
    
    def extract_structured_features(self, company_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract structured numerical features from company data."""
        features = {}
        
        # From metadata/attributes
        metadata = company_data.get('metadata', {}) or company_data.get('attributes', {})
        
        features['vessel_count'] = float(metadata.get('vessel_count', 0))
        features['avg_emissions'] = float(metadata.get('avg_emissions', 0) or metadata.get('avg_emissions_tons', 0) or 0)
        features['avg_co2_distance'] = float(metadata.get('avg_co2_distance', 0) or metadata.get('avg_co2_per_distance', 0) or 0)
        features['avg_wasp_score'] = float(metadata.get('avg_wasp_fit_score', 0) or 0)
        
        # Intelligence category counts
        intelligence = company_data.get('intelligence', {})
        features['grants_count'] = float(intelligence.get('grants_subsidies', {}).get('results_count', 0))
        features['violations_count'] = float(intelligence.get('legal_violations', {}).get('results_count', 0))
        features['sustainability_count'] = float(intelligence.get('sustainability_news', {}).get('results_count', 0))
        features['reputation_count'] = float(intelligence.get('reputation', {}).get('results_count', 0))
        features['financial_pressure_count'] = float(intelligence.get('financial_pressure', {}).get('results_count', 0))
        features['total_findings'] = sum([
            features['grants_count'],
            features['violations_count'],
            features['sustainability_count'],
            features['reputation_count'],
            features['financial_pressure_count']
        ])
        
        # Sentiment scores from all text
        text = self.extract_text_features(company_data)
        sentiment = self.analyze_sentiment(text)
        features.update(sentiment)
        
        # Keyword-based features
        text_lower = text.lower()
        features['has_wind_keywords'] = float(1.0 if any(kw in text_lower for kw in [
            'wind propulsion', 'rotor sail', 'wing sail', 'wasp', 'econowind',
            'flettner', 'wind-assisted', 'wind power'
        ]) else 0.0)
        
        features['has_grant_keywords'] = float(1.0 if any(kw in text_lower for kw in [
            'grant', 'subsidy', 'funding', 'eu fund', 'government support'
        ]) else 0.0)
        
        features['has_sustainability_keywords'] = float(1.0 if any(kw in text_lower for kw in [
            'sustainability', 'green', 'decarbonization', 'carbon neutral', 'emissions reduction'
        ]) else 0.0)
        
        return features
    
    def build_feature_matrix(self, companies_data: Dict[str, Any]) -> Tuple[pd.DataFrame, List[str]]:
        """Build feature matrix from all companies."""
        features_list = []
        company_names = []
        
        for company_name, company_data in companies_data.items():
            features = self.extract_structured_features(company_data)
            features_list.append(features)
            company_names.append(company_name)
        
        df = pd.DataFrame(features_list, index=company_names)
        return df, company_names
    
    def train_wasp_adoption_model(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """Train classifier to predict WASP adoption."""
        if not ML_AVAILABLE:
            return None
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train ensemble model
        model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\nWASP Adoption Model:")
        print(f"  Accuracy: {accuracy:.3f}")
        print(f"  Training samples: {len(X_train)}")
        print(f"  Test samples: {len(X_test)}")
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        self.scalers['wasp'] = scaler
        return model
    
    def train_sustainability_classifier(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """Train classifier to predict sustainability focus level."""
        if not ML_AVAILABLE:
            return None
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\nSustainability Classifier:")
        print(f"  Accuracy: {accuracy:.3f}")
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        self.scalers['sustainability'] = scaler
        return model
    
    def train_company_type_classifier(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """Train classifier to predict company type."""
        if not ML_AVAILABLE:
            return None
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\nCompany Type Classifier:")
        print(f"  Accuracy: {accuracy:.3f}")
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        self.scalers['company_type'] = scaler
        return model
    
    def prepare_training_data(self) -> Tuple[pd.DataFrame, Dict[str, pd.Series]]:
        """Prepare training data from intelligence and profile data."""
        print("="*80)
        print("PREPARING ML TRAINING DATA")
        print("="*80)
        
        # Load data
        intelligence_data = self.load_intelligence_data()
        profile_data = self.load_profile_data()
        wasp_adopters = self.get_wasp_adopters()
        
        print(f"Loaded {len(intelligence_data)} companies with intelligence data")
        print(f"Loaded {len(profile_data)} companies with profile data")
        print(f"Found {len(wasp_adopters)} companies with WASP adoption")
        
        # Merge intelligence and profile data
        merged_data = {}
        for company_name in set(list(intelligence_data.keys()) + list(profile_data.keys())):
            merged = {}
            if company_name in intelligence_data:
                merged.update(intelligence_data[company_name])
            if company_name in profile_data:
                merged.update(profile_data[company_name])
            if merged:
                merged_data[company_name] = merged
        
        print(f"Merged {len(merged_data)} companies")
        
        # Build feature matrix
        X, company_names = self.build_feature_matrix(merged_data)
        print(f"Feature matrix shape: {X.shape}")
        print(f"Features: {list(X.columns)}")
        
        # Prepare labels
        labels = {}
        
        # 1. WASP adoption (binary)
        wasp_labels = []
        for name in company_names:
            wasp_labels.append(1 if wasp_adopters.get(name, False) else 0)
        labels['wasp_adoption'] = pd.Series(wasp_labels, index=company_names)
        
        # 2. Sustainability focus (from labels or derived)
        sustainability_labels = []
        for name in company_names:
            company = merged_data.get(name, {})
            labels_data = company.get('labels', {})
            
            # Use emissions_category as proxy, or derive from sustainability_count
            emissions_cat = labels_data.get('emissions_category', 'medium')
            sust_count = company.get('intelligence', {}).get('sustainability_news', {}).get('results_count', 0)
            
            if sust_count >= 3 or emissions_cat == 'low':
                sustainability_labels.append('high')
            elif sust_count >= 1 or emissions_cat == 'medium':
                sustainability_labels.append('medium')
            else:
                sustainability_labels.append('low')
        
        labels['sustainability_focus'] = pd.Series(sustainability_labels, index=company_names)
        
        # 3. Company type (from labels)
        company_type_labels = []
        for name in company_names:
            company = merged_data.get(name, {})
            labels_data = company.get('labels', {})
            categories = labels_data.get('company_categories', [])
            
            if categories:
                company_type_labels.append(categories[0])  # Use primary category
            else:
                company_type_labels.append('unknown')
        
        labels['company_type'] = pd.Series(company_type_labels, index=company_names)
        
        print(f"\nLabel distributions:")
        print(f"  WASP adoption: {sum(wasp_labels)}/{len(wasp_labels)} ({100*sum(wasp_labels)/len(wasp_labels):.1f}%)")
        print(f"  Sustainability focus: {pd.Series(sustainability_labels).value_counts().to_dict()}")
        print(f"  Company types: {pd.Series(company_type_labels).value_counts().to_dict()}")
        
        return X, labels
    
    def train_all_models(self) -> Dict[str, Any]:
        """Train all ML models."""
        if not ML_AVAILABLE:
            print("ERROR: scikit-learn not available. Install with: pip install scikit-learn")
            return {}
        
        print("\n" + "="*80)
        print("TRAINING ML MODELS")
        print("="*80)
        
        # Prepare data
        X, labels = self.prepare_training_data()
        
        # Filter out companies with insufficient data
        valid_mask = (X['total_findings'] > 0) | (X['vessel_count'] > 0)
        X_filtered = X[valid_mask]
        labels_filtered = {k: v[valid_mask] for k, v in labels.items()}
        
        print(f"\nFiltered to {len(X_filtered)} companies with sufficient data")
        
        # Train models
        models = {}
        
        # 1. WASP Adoption Model
        if sum(labels_filtered['wasp_adoption']) >= 2:  # Need at least 2 positive examples
            print("\n" + "-"*80)
            models['wasp_adoption'] = self.train_wasp_adoption_model(
                X_filtered,
                labels_filtered['wasp_adoption']
            )
        else:
            print("\n⚠️  Insufficient WASP adoption data for training (need at least 2 examples)")
        
        # 2. Sustainability Classifier
        if len(labels_filtered['sustainability_focus'].unique()) >= 2:
            print("\n" + "-"*80)
            models['sustainability_focus'] = self.train_sustainability_classifier(
                X_filtered,
                labels_filtered['sustainability_focus']
            )
        else:
            print("\n⚠️  Insufficient sustainability data for training")
        
        # 3. Company Type Classifier
        if len(labels_filtered['company_type'].unique()) >= 2:
            print("\n" + "-"*80)
            models['company_type'] = self.train_company_type_classifier(
                X_filtered,
                labels_filtered['company_type']
            )
        else:
            print("\n⚠️  Insufficient company type data for training")
        
        self.models = models
        self.feature_names = list(X_filtered.columns)
        
        return models
    
    def predict_company(self, company_name: str, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make predictions for a single company."""
        if not self.models:
            return {
                'error': 'Models not trained. Call train_all_models() first.'
            }
        
        # Extract features
        features = self.extract_structured_features(company_data)
        feature_vector = pd.DataFrame([features])
        
        # Ensure all features are present
        for feat in self.feature_names:
            if feat not in feature_vector.columns:
                feature_vector[feat] = 0.0
        
        feature_vector = feature_vector[self.feature_names]
        
        predictions = {}
        
        # WASP adoption prediction
        if 'wasp_adoption' in self.models:
            scaler = self.scalers.get('wasp')
            X_scaled = scaler.transform(feature_vector)
            proba = self.models['wasp_adoption'].predict_proba(X_scaled)[0]
            predictions['wasp_adoption'] = {
                'prediction': bool(self.models['wasp_adoption'].predict(X_scaled)[0]),
                'probability': float(max(proba)),
                'confidence': 'high' if max(proba) > 0.7 else 'medium' if max(proba) > 0.5 else 'low'
            }
        
        # Sustainability focus prediction
        if 'sustainability_focus' in self.models:
            scaler = self.scalers.get('sustainability')
            X_scaled = scaler.transform(feature_vector)
            prediction = self.models['sustainability_focus'].predict(X_scaled)[0]
            proba = self.models['sustainability_focus'].predict_proba(X_scaled)[0]
            predictions['sustainability_focus'] = {
                'prediction': str(prediction),
                'probability': float(max(proba)),
                'confidence': 'high' if max(proba) > 0.6 else 'medium' if max(proba) > 0.4 else 'low'
            }
        
        # Company type prediction
        if 'company_type' in self.models:
            scaler = self.scalers.get('company_type')
            X_scaled = scaler.transform(feature_vector)
            prediction = self.models['company_type'].predict(X_scaled)[0]
            proba = self.models['company_type'].predict_proba(X_scaled)[0]
            predictions['company_type'] = {
                'prediction': str(prediction),
                'probability': float(max(proba)),
                'confidence': 'high' if max(proba) > 0.5 else 'medium' if max(proba) > 0.3 else 'low'
            }
        
        # Add feature importance for interpretability
        predictions['features'] = {
            'vessel_count': features.get('vessel_count', 0),
            'grants_count': features.get('grants_count', 0),
            'sustainability_count': features.get('sustainability_count', 0),
            'has_wind_keywords': bool(features.get('has_wind_keywords', 0)),
            'sentiment_polarity': features.get('polarity', 0)
        }
        
        return predictions
    
    def predict_all_companies(self) -> Dict[str, Dict[str, Any]]:
        """Make predictions for all companies."""
        intelligence_data = self.load_intelligence_data()
        profile_data = self.load_profile_data()
        
        # Merge data
        merged_data = {}
        for company_name in set(list(intelligence_data.keys()) + list(profile_data.keys())):
            merged = {}
            if company_name in intelligence_data:
                merged.update(intelligence_data[company_name])
            if company_name in profile_data:
                merged.update(profile_data[company_name])
            if merged:
                merged_data[company_name] = merged
        
        all_predictions = {}
        for company_name, company_data in merged_data.items():
            predictions = self.predict_company(company_name, company_data)
            if 'error' not in predictions:
                all_predictions[company_name] = predictions
        
        return all_predictions
    
    def save_models(self, filepath: str = "data/ml_models.pkl"):
        """Save trained models to disk."""
        if not self.models:
            print("No models to save")
            return
        
        model_data = {
            'models': self.models,
            'scalers': self.scalers,
            'feature_names': self.feature_names,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Models saved to: {filepath}")
    
    def load_models(self, filepath: str = "data/ml_models.pkl"):
        """Load trained models from disk."""
        if not Path(filepath).exists():
            print(f"Model file not found: {filepath}")
            return False
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.models = model_data.get('models', {})
        self.scalers = model_data.get('scalers', {})
        self.feature_names = model_data.get('feature_names', [])
        
        print(f"Models loaded from: {filepath}")
        print(f"Loaded {len(self.models)} models")
        return True


def main():
    """Train models and save predictions."""
    predictor = CompanyMLPredictor()
    
    # Train models
    models = predictor.train_all_models()
    
    if models:
        # Save models
        predictor.save_models()
        
        # Generate predictions for all companies
        print("\n" + "="*80)
        print("GENERATING PREDICTIONS")
        print("="*80)
        
        predictions = predictor.predict_all_companies()
        
        # Save predictions to JSON
        output_file = Path("data/company_predictions.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'predictions': predictions,
                'total_companies': len(predictions),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Predictions saved to: {output_file}")
        print(f"   Total companies: {len(predictions)}")
        
        # Show sample predictions
        print("\nSample Predictions:")
        for i, (company, pred) in enumerate(list(predictions.items())[:5]):
            print(f"\n{i+1}. {company}")
            if 'wasp_adoption' in pred:
                print(f"   WASP Adoption: {pred['wasp_adoption']['prediction']} ({pred['wasp_adoption']['confidence']} confidence)")
            if 'sustainability_focus' in pred:
                print(f"   Sustainability: {pred['sustainability_focus']['prediction']} ({pred['sustainability_focus']['confidence']} confidence)")
            if 'company_type' in pred:
                print(f"   Company Type: {pred['company_type']['prediction']}")
    else:
        print("\n⚠️  No models trained. Check data availability.")


if __name__ == "__main__":
    main()

