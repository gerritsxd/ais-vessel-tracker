"""
ML Predictor for Company WASP Adoption

This module contains the main CompanyMLPredictor class that:
1. Loads and merges company intelligence + profile data
2. Extracts features for ML models
3. Trains classification models
4. Generates predictions for WASP adoption likelihood

MODELS:
=======
1. WASP Adoption (Binary): GradientBoostingClassifier
   - Predicts: Will company adopt wind propulsion? (True/False)
   - Ground truth: Known WASP adopters from wind_propulsion table

2. Sustainability Focus (Multi-class): RandomForestClassifier
   - Predicts: high / medium / low sustainability focus
   - Derived from emissions category + sustainability news count

3. Company Type (Multi-class): RandomForestClassifier
   - Predicts: container_carrier, tanker_operator, bulk_carrier, etc.
   - From company profile labels
"""

import json
import sqlite3
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

import numpy as np
import pandas as pd

# Try importing ML libraries
try:
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, classification_report
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("Warning: scikit-learn not installed. Install with: pip install scikit-learn")

from .features import FeatureExtractor


class CompanyMLPredictor:
    """
    ML/NLP service for predicting company characteristics from intelligence data.
    """
    
    def __init__(self, db_path: str = "data/vessel_static_data.db"):
        """
        Initialize the predictor.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_names: List[str] = []
        self.feature_extractor = FeatureExtractor()
        
    def load_intelligence_data(self) -> Dict[str, Any]:
        """
        Load latest company intelligence JSON file.
        
        Returns:
            Dictionary mapping company name -> intelligence data
        """
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
        """
        Load latest company profile V3 JSON file.
        
        Returns:
            Dictionary mapping company name -> profile data
        """
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
        """
        Get companies that have adopted WASP (ground truth labels).
        
        Returns:
            Dictionary mapping company name -> True for known adopters
        """
        wasp_companies = {}
        
        # Try database approach first
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if required tables exist
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='eu_mrv_emissions'"
            )
            has_emissions = cursor.fetchone() is not None
            
            if has_emissions:
                # Get companies with wind-assisted vessels
                cursor.execute('''
                    SELECT DISTINCT e.company_name
                    FROM eu_mrv_emissions e
                    INNER JOIN vessels_static v ON e.imo = v.imo
                    WHERE v.wind_assisted = 1
                    AND e.company_name IS NOT NULL
                ''')
                wasp_companies = {row[0]: True for row in cursor.fetchall()}
                
                # Also check wind_propulsion table
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='wind_propulsion'"
                )
                has_wind = cursor.fetchone() is not None
                
                if has_wind:
                    cursor.execute('''
                        SELECT DISTINCT e.company_name
                        FROM eu_mrv_emissions e
                        INNER JOIN wind_propulsion w 
                            ON UPPER(TRIM(e.vessel_name)) = UPPER(TRIM(w.vessel_name))
                        WHERE e.company_name IS NOT NULL
                    ''')
                    for row in cursor.fetchall():
                        wasp_companies[row[0]] = True
            
            conn.close()
        except Exception as e:
            print(f"Database approach failed: {e}")
        
        # Fallback: Known WASP adopter keywords
        if not wasp_companies:
            wasp_companies = self._get_known_wasp_companies()
        
        return wasp_companies

    def get_econowind_adopters(self) -> Dict[str, bool]:
        """Get companies that have adopted Econowind (VentoFoil) (ground truth labels).

        Source of truth:
        - `config/econowind_adopters.txt`
        """
        adopters: Dict[str, bool] = {}

        adopters_file = Path("config/econowind_adopters.txt")
        if not adopters_file.exists():
            return adopters

        for raw_line in adopters_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            company = line.split("|", 1)[0].strip()
            if company:
                adopters[company] = True

        return adopters

    def _get_known_wasp_companies(self) -> Dict[str, bool]:
        """
        Get known WASP adopters based on public information.
        
        These are companies known to have deployed wind propulsion systems.
        """
        # Known WASP-adopting companies (verified deployments)
        known_adopters = {
            'scandlines': True,  # Copenhagen, Berlin ferries
            'enercon': True,  # E-Ship 1
            'wallenius wilhelmsen': True,  # SC Connector
            'berge bulk': True,  # Berge Olympus
            'cargill': True,  # Pyxis Ocean
            'oldendorff': True,  # Various bulk carriers
            'gnv': True,  # GNV Bridge
            'stena': True,  # Various vessels
            'marfret': True,  # Marfret Niolon
            'terntank': True,  # Tern Vik
            'odfjell': True,  # Chemical tankers
            'grimaldi': True,  # Delphine
            'china merchants': True,
        }
        
        return known_adopters
    
    def _check_wasp_match(self, company_name: str, wasp_adopters: Dict[str, bool]) -> bool:
        """
        Check if company name matches any WASP adopter using fuzzy matching.
        
        Args:
            company_name: Company name to check
            wasp_adopters: Dict of known WASP adopters
            
        Returns:
            True if match found
        """
        # Exact match first
        if wasp_adopters.get(company_name, False):
            return True
        
        # Fuzzy match: check if any WASP keyword is in company name
        company_lower = company_name.lower()
        for wasp_company in wasp_adopters.keys():
            wasp_lower = wasp_company.lower()
            if wasp_lower in company_lower:
                return True
            if len(company_lower) > 3 and company_lower in wasp_lower:
                return True
        
        return False
    

    def _check_econowind_match(self, company_name: str, econowind_adopters: Dict[str, bool]) -> bool:
        """Check if company name matches any Econowind adopter using fuzzy matching."""
        if not company_name:
            return False

        if econowind_adopters.get(company_name, False):
            return True

        company_lower = company_name.lower()
        for econ_company in econowind_adopters.keys():
            econ_lower = econ_company.lower()
            if econ_lower in company_lower:
                return True
            if len(company_lower) > 3 and company_lower in econ_lower:
                return True

        return False


    def prepare_training_data(self) -> Tuple[pd.DataFrame, Dict[str, pd.Series]]:
        """
        Prepare training data from intelligence and profile data.
        
        Returns:
            Tuple of (feature_matrix, dict_of_label_series)
        """
        print("=" * 80)
        print("PREPARING ML TRAINING DATA")
        print("=" * 80)
        
        # Load data
        intelligence_data = self.load_intelligence_data()
        profile_data = self.load_profile_data()
        wasp_adopters = self.get_wasp_adopters()
        econowind_adopters = self.get_econowind_adopters()
        
        print(f"Loaded {len(intelligence_data)} companies with intelligence data")
        print(f"Loaded {len(profile_data)} companies with profile data")
        print(f"Found {len(wasp_adopters)} known WASP adopters")
        
        # Merge intelligence and profile data
        merged_data = {}
        all_companies = set(list(intelligence_data.keys()) + list(profile_data.keys()))
        
        for company_name in all_companies:
            merged = {}
            if company_name in intelligence_data:
                merged.update(intelligence_data[company_name])
            if company_name in profile_data:
                merged.update(profile_data[company_name])
            if merged:
                merged_data[company_name] = merged
        
        print(f"Merged {len(merged_data)} companies")
        
        # Build feature matrix
        X, company_names = self.feature_extractor.build_feature_matrix(merged_data)
        print(f"Feature matrix shape: {X.shape}")
        print(f"Features: {list(X.columns)}")
        
        # Prepare labels
        labels = {}
        
        # 1. WASP adoption (binary)
        wasp_labels = []
        for name in company_names:
            is_wasp = self._check_wasp_match(name, wasp_adopters)
            wasp_labels.append(1 if is_wasp else 0)
        labels['wasp_adoption'] = pd.Series(wasp_labels, index=company_names)

        # 1b. Econowind adoption (binary)
        econowind_labels = []
        for name in company_names:
            is_econ = self._check_econowind_match(name, econowind_adopters) if econowind_adopters else False
            econowind_labels.append(1 if is_econ else 0)
        labels['econowind_adoption'] = pd.Series(econowind_labels, index=company_names)

        
        # 2. Sustainability focus (from labels or derived)
        sustainability_labels = []
        for name in company_names:
            company = merged_data.get(name, {})
            labels_data = company.get('labels', {})
            
            emissions_cat = labels_data.get('emissions_category', 'medium')
            sust_count = company.get('intelligence', {}).get(
                'sustainability_news', {}
            ).get('results_count', 0)
            
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
                company_type_labels.append(categories[0])
            else:
                company_type_labels.append('unknown')
        
        labels['company_type'] = pd.Series(company_type_labels, index=company_names)
        
        print(f"\nLabel distributions:")
        print(f"  WASP adoption: {sum(wasp_labels)}/{len(wasp_labels)} "
              f"({100*sum(wasp_labels)/len(wasp_labels):.1f}%)")
        print(f"  Sustainability: {pd.Series(sustainability_labels).value_counts().to_dict()}")
        print(f"  Company types: {pd.Series(company_type_labels).value_counts().to_dict()}")
        
        return X, labels
    
    def train_wasp_adoption_model(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """
        Train binary classifier for WASP adoption prediction.
        
        Args:
            X: Feature matrix
            y: Binary labels (0/1)
            
        Returns:
            Trained model or None if insufficient data
        """
        if not ML_AVAILABLE:
            return None
        
        n_samples = len(X)
        min_class_samples = min(y.value_counts())
        
        scaler = StandardScaler()
        
        # Handle small datasets
        if n_samples < 10 or min_class_samples < 2:
            print("\n[INFO] Small dataset - training on all data without holdout")
            X_scaled = scaler.fit_transform(X)
            
            model = GradientBoostingClassifier(
                n_estimators=50,
                learning_rate=0.1,
                max_depth=3,
                random_state=42
            )
            model.fit(X_scaled, y)
            
            print(f"\nWASP Adoption Model:")
            print(f"  Training samples: {n_samples}")
            print(f"  Class distribution: {dict(y.value_counts())}")
            
            self.scalers['wasp'] = scaler
            return model
        
        # Normal train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
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
    

    def train_econowind_adoption_model(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """Train binary classifier for Econowind adoption prediction."""
        if not ML_AVAILABLE:
            return None

        n_samples = len(X)
        min_class_samples = min(y.value_counts())

        scaler = StandardScaler()

        if min_class_samples < 2 or n_samples < 10:
            X_scaled = scaler.fit_transform(X)
            model = GradientBoostingClassifier(random_state=42)
            model.fit(X_scaled, y)
            self.scalers['econowind'] = scaler
            return model

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = GradientBoostingClassifier(random_state=42)
        model.fit(X_train_scaled, y_train)

        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"\nEconowind Adoption Model: Accuracy={accuracy:.3f}")

        self.scalers['econowind'] = scaler
        return model


    def train_sustainability_classifier(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """
        Train multi-class classifier for sustainability focus.
        
        Args:
            X: Feature matrix
            y: Multi-class labels (high/medium/low)
            
        Returns:
            Trained model or None
        """
        if not ML_AVAILABLE:
            return None
        
        n_samples = len(X)
        min_class_samples = min(y.value_counts())
        
        scaler = StandardScaler()
        
        if n_samples < 10 or min_class_samples < 2:
            print("\n[INFO] Small dataset - training on all data")
            X_scaled = scaler.fit_transform(X)
            
            model = RandomForestClassifier(
                n_estimators=50,
                max_depth=5,
                random_state=42
            )
            model.fit(X_scaled, y)
            
            print(f"\nSustainability Classifier:")
            print(f"  Training samples: {n_samples}")
            print(f"  Class distribution: {dict(y.value_counts())}")
            
            self.scalers['sustainability'] = scaler
            return model
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        model.fit(X_train_scaled, y_train)
        
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\nSustainability Classifier:")
        print(f"  Accuracy: {accuracy:.3f}")
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        self.scalers['sustainability'] = scaler
        return model
    
    def train_company_type_classifier(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """Train company type classifier."""
        if not ML_AVAILABLE:
            return None
        
        n_samples = len(X)
        min_class_samples = min(y.value_counts())
        
        scaler = StandardScaler()
        
        if n_samples < 10 or min_class_samples < 2:
            print("\n[INFO] Small dataset - training on all data")
            X_scaled = scaler.fit_transform(X)
            
            model = RandomForestClassifier(
                n_estimators=50,
                max_depth=5,
                random_state=42
            )
            model.fit(X_scaled, y)
            
            print(f"\nCompany Type Classifier:")
            print(f"  Training samples: {n_samples}")
            
            self.scalers['company_type'] = scaler
            return model
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        model.fit(X_train_scaled, y_train)
        
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\nCompany Type Classifier:")
        print(f"  Accuracy: {accuracy:.3f}")
        
        self.scalers['company_type'] = scaler
        return model
    
    def train_all_models(self) -> Dict[str, Any]:
        """
        Train all ML models.
        
        Returns:
            Dictionary of trained models
        """
        if not ML_AVAILABLE:
            print("ERROR: scikit-learn not available")
            return {}
        
        print("\n" + "=" * 80)
        print("TRAINING ML MODELS")
        print("=" * 80)
        
        # Prepare data
        X, labels = self.prepare_training_data()
        
        # Filter companies with insufficient data
        valid_mask = (X['total_findings'] > 0) | (X['vessel_count'] > 0)
        X_filtered = X[valid_mask]
        labels_filtered = {k: v[valid_mask] for k, v in labels.items()}
        
        print(f"\nFiltered to {len(X_filtered)} companies with sufficient data")
        
        models = {}
        
        # Train WASP model
        if sum(labels_filtered['wasp_adoption']) >= 2:
            print("\n" + "-" * 80)
            models['wasp_adoption'] = self.train_wasp_adoption_model(
                X_filtered,
                labels_filtered['wasp_adoption']
            )
        else:
            print("\n[WARN] Insufficient WASP data (need >= 2 positive examples)")

        # Train Econowind model (labels from config/econowind_adopters.txt)
        if 'econowind_adoption' in labels_filtered and sum(labels_filtered['econowind_adoption']) >= 2:
            print("\n" + "-" * 80)
            models['econowind_adoption'] = self.train_econowind_adoption_model(
                X_filtered,
                labels_filtered['econowind_adoption']
            )
        elif 'econowind_adoption' in labels_filtered:
            print("\n[WARN] Insufficient Econowind data (need >= 2 positive examples). Edit config/econowind_adopters.txt")

        
        # Train sustainability classifier
        if len(labels_filtered['sustainability_focus'].unique()) >= 2:
            print("\n" + "-" * 80)
            models['sustainability_focus'] = self.train_sustainability_classifier(
                X_filtered,
                labels_filtered['sustainability_focus']
            )
        
        # Train company type classifier
        if len(labels_filtered['company_type'].unique()) >= 2:
            print("\n" + "-" * 80)
            models['company_type'] = self.train_company_type_classifier(
                X_filtered,
                labels_filtered['company_type']
            )
        
        self.models = models
        self.feature_names = list(X_filtered.columns)
        
        return models
    
    def predict_company(self, company_name: str, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate predictions for a single company.
        
        Args:
            company_name: Company name
            company_data: Company intelligence/profile data
            
        Returns:
            Dictionary with predictions and confidence scores
        """
        if not self.models:
            return {'error': 'Models not trained. Call train_all_models() first.'}
        
        # Extract features
        features = self.feature_extractor.extract_structured_features(company_data)
        feature_vector = pd.DataFrame([features])
        
        # Ensure all features present
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
        

        # Econowind adoption prediction
        if 'econowind_adoption' in self.models:
            scaler = self.scalers.get('econowind')
            X_scaled = scaler.transform(feature_vector)
            proba = self.models['econowind_adoption'].predict_proba(X_scaled)[0]
            predictions['econowind_adoption'] = {
                'prediction': bool(self.models['econowind_adoption'].predict(X_scaled)[0]),
                'probability': float(max(proba)),
                'confidence': 'high' if max(proba) > 0.7 else 'medium' if max(proba) > 0.5 else 'low'
            }

        # Sustainability prediction
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
        
        # Add key features for interpretability
        predictions['features'] = {
            'vessel_count': features.get('vessel_count', 0),
            'grants_count': features.get('grants_count', 0),
            'sustainability_count': features.get('sustainability_count', 0),
            'has_wind_keywords': bool(features.get('has_wind_keywords', 0)),
            'sentiment_polarity': features.get('polarity', 0)
        }
        
        return predictions
    
    def predict_all_companies(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate predictions for all companies with data.
        
        Returns:
            Dictionary mapping company name -> predictions
        """
        intelligence_data = self.load_intelligence_data()
        profile_data = self.load_profile_data()
        
        # Merge data
        merged_data = {}
        all_companies = set(list(intelligence_data.keys()) + list(profile_data.keys()))
        
        for company_name in all_companies:
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
    
    def save_models(self, filepath: str = "data/ml_models.pkl") -> None:
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
    
    def load_models(self, filepath: str = "data/ml_models.pkl") -> bool:
        """
        Load trained models from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
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
    """Train models and save predictions (CLI entry point)."""
    predictor = CompanyMLPredictor()
    
    models = predictor.train_all_models()
    
    if models:
        predictor.save_models()
        
        print("\n" + "=" * 80)
        print("GENERATING PREDICTIONS")
        print("=" * 80)
        
        predictions = predictor.predict_all_companies()
        
        # Save predictions
        output_file = Path("data/company_predictions.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'predictions': predictions,
                'total_companies': len(predictions),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Predictions saved to: {output_file}")
        print(f"   Total companies: {len(predictions)}")
        
        # Show sample
        print("\nSample Predictions:")
        for i, (company, pred) in enumerate(list(predictions.items())[:5]):
            print(f"\n{i+1}. {company}")
            if 'wasp_adoption' in pred:
                print(f"   WASP: {pred['wasp_adoption']['prediction']} "
                      f"({pred['wasp_adoption']['confidence']} confidence)")
    else:
        print("\n[WARN] No models trained. Check data availability.")


if __name__ == "__main__":
    main()


