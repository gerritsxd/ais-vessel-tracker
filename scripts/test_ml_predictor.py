#!/usr/bin/env python3
"""
Test script for ML Predictor Service
Tests model training and prediction generation
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from new ML module location
try:
    from src.ml.predictor import CompanyMLPredictor
except ImportError:
    # Fallback to old location
from src.services.ml_predictor_service import CompanyMLPredictor

def main():
    print("="*80)
    print("ML PREDICTOR SERVICE TEST")
    print("="*80)
    
    predictor = CompanyMLPredictor()
    
    # Test data loading
    print("\n1. Testing data loading...")
    intelligence_data = predictor.load_intelligence_data()
    profile_data = predictor.load_profile_data()
    wasp_adopters = predictor.get_wasp_adopters()
    
    print(f"   [OK] Intelligence data: {len(intelligence_data)} companies")
    print(f"   [OK] Profile data: {len(profile_data)} companies")
    print(f"   [OK] WASP adopters: {len(wasp_adopters)} companies")
    
    if len(intelligence_data) == 0 and len(profile_data) == 0:
        print("\n[WARN] No data available. Run intelligence scraper and profiler first.")
        return
    
    # Test feature extraction
    print("\n2. Testing feature extraction...")
    if intelligence_data:
        sample_company = list(intelligence_data.keys())[0]
        sample_data = intelligence_data[sample_company]
        features = predictor.extract_structured_features(sample_data)
        print(f"   [OK] Sample company: {sample_company}")
        print(f"   [OK] Features extracted: {len(features)} features")
        print(f"   [OK] Key features: vessel_count={features.get('vessel_count', 0)}, "
              f"grants={features.get('grants_count', 0)}, "
              f"sustainability={features.get('sustainability_count', 0)}")
    
    # Test sentiment analysis
    print("\n3. Testing sentiment analysis...")
    test_text = "Maersk is investing heavily in green technology and wind propulsion systems."
    sentiment = predictor.analyze_sentiment(test_text)
    print(f"   [OK] Test text: '{test_text[:50]}...'")
    print(f"   [OK] Polarity: {sentiment['polarity']:.2f}")
    print(f"   [OK] Subjectivity: {sentiment['subjectivity']:.2f}")
    
    # Test model training (if enough data)
    print("\n4. Testing model training...")
    try:
        models = predictor.train_all_models()
        if models:
            print(f"   [OK] Models trained: {list(models.keys())}")
            predictor.save_models()
            print("   [OK] Models saved to data/ml_models.pkl")
            
            # Test predictions
            print("\n5. Testing predictions...")
            predictions = predictor.predict_all_companies()
            print(f"   [OK] Predictions generated: {len(predictions)} companies")
            
            # Show sample predictions
            print("\n6. Sample predictions:")
            for i, (company, pred) in enumerate(list(predictions.items())[:3]):
                print(f"\n   {i+1}. {company}")
                if 'wasp_adoption' in pred:
                    print(f"      WASP: {pred['wasp_adoption']['prediction']} "
                          f"({pred['wasp_adoption']['probability']:.2%} confidence)")
                if 'sustainability_focus' in pred:
                    print(f"      Sustainability: {pred['sustainability_focus']['prediction']}")
                if 'company_type' in pred:
                    print(f"      Type: {pred['company_type']['prediction']}")
        else:
            print("   [WARN] No models trained (insufficient data)")
    except Exception as e:
        print(f"   [ERROR] Error training models: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()

