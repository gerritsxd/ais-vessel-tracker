"""
Standalone ML Service for PC
Runs ML training and predictions on your PC, accessible via HTTP API
This allows VPS to use your PC's resources for ML while serving the web interface

Configuration:
    VPS_URL: URL of the VPS web service (e.g., "http://149.202.53.2:5000" or "https://gerritsxd.com")
             If set, the service will fetch training data from VPS before training.
             If not set, it will use local data files.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path
import sys
import os
from datetime import datetime

# Add project root and src to path
project_root = Path(__file__).parent.parent.parent
src_dir = project_root / 'src'
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_dir))

# Import ML predictor - file is in same directory (src/services/)
# Since we're in src/services/, we can import directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "ml_predictor_service", 
    project_root / "src" / "services" / "ml_predictor_service.py"
)
ml_predictor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ml_predictor_module)
CompanyMLPredictor = ml_predictor_module.CompanyMLPredictor

app = Flask(__name__)
CORS(app)  # Allow VPS to call this service

predictor = CompanyMLPredictor()

# VPS URL for fetching training data
VPS_URL = os.environ.get('VPS_URL', '')


def sync_data_from_vps():
    """Fetch training data from VPS and save locally."""
    if not VPS_URL:
        print("[INFO] VPS_URL not set, using local data files")
        return False
    
    try:
        import requests
        print(f"[INFO] Syncing data from VPS: {VPS_URL}")
        
        data_dir = project_root / 'data'
        data_dir.mkdir(exist_ok=True)
        
        # Fetch intelligence data
        try:
            url = f"{VPS_URL.rstrip('/')}/ships/api/ml/data/intelligence"
            print(f"  Fetching intelligence data...")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            intel_data = response.json()
            
            if 'companies' in intel_data and intel_data['companies']:
                # Save to local file with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                intel_file = data_dir / f"company_intelligence_gemini_{timestamp}.json"
                with open(intel_file, 'w', encoding='utf-8') as f:
                    json.dump(intel_data, f, indent=2, ensure_ascii=False)
                print(f"    Saved {len(intel_data['companies'])} companies to {intel_file.name}")
        except Exception as e:
            print(f"    [WARN] Could not fetch intelligence data: {e}")
        
        # Fetch profile data
        try:
            url = f"{VPS_URL.rstrip('/')}/ships/api/ml/data/profiles"
            print(f"  Fetching profile data...")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            profile_data = response.json()
            
            if 'companies' in profile_data and profile_data['companies']:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                profile_file = data_dir / f"company_profiles_v3_structured_{timestamp}.json"
                with open(profile_file, 'w', encoding='utf-8') as f:
                    json.dump(profile_data, f, indent=2, ensure_ascii=False)
                print(f"    Saved {len(profile_data['companies'])} companies to {profile_file.name}")
        except Exception as e:
            print(f"    [WARN] Could not fetch profile data: {e}")
        
        print("[INFO] Data sync completed")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to sync data from VPS: {e}")
        return False

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'ml-predictor-pc',
        'models_loaded': len(predictor.models) > 0,
        'vps_url': VPS_URL if VPS_URL else None,
        'data_source': 'vps' if VPS_URL else 'local'
    })


@app.route('/sync', methods=['POST'])
def sync_data():
    """Manually sync data from VPS."""
    if not VPS_URL:
        return jsonify({
            'status': 'skipped',
            'message': 'VPS_URL not configured. Set VPS_URL environment variable.'
        })
    
    try:
        success = sync_data_from_vps()
        return jsonify({
            'status': 'success' if success else 'partial',
            'message': 'Data synced from VPS'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/predictions', methods=['GET'])
def get_predictions():
    """Get predictions for all companies."""
    try:
        # Try to load existing predictions first
        predictions_file = project_root / 'data' / 'company_predictions.json'
        if predictions_file.exists():
            with open(predictions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        
        # If no predictions file, generate them
        if not predictor.models:
            if not predictor.load_models():
                return jsonify({
                    'error': 'Models not trained. Call /train first.',
                    'predictions': {},
                    'total_companies': 0
                }), 404
        
        predictions = predictor.predict_all_companies()
        
        return jsonify({
            'predictions': predictions,
            'total_companies': len(predictions),
            'timestamp': predictor.__class__.__module__  # Placeholder
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/predictions/<company_name>', methods=['GET'])
def get_company_prediction(company_name):
    """Get prediction for a specific company."""
    try:
        if not predictor.models:
            if not predictor.load_models():
                return jsonify({
                    'error': 'Models not trained. Call /train first.',
                    'company': company_name
                }), 404
        
        # Load company data
        intelligence_data = predictor.load_intelligence_data()
        profile_data = predictor.load_profile_data()
        
        # Merge data
        company_data = {}
        if company_name in intelligence_data:
            company_data.update(intelligence_data[company_name])
        if company_name in profile_data:
            company_data.update(profile_data[company_name])
        
        if not company_data:
            return jsonify({'error': 'Company not found', 'company': company_name}), 404
        
        # Make prediction
        predictions = predictor.predict_company(company_name, company_data)
        
        return jsonify({
            'company': company_name,
            'predictions': predictions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/train', methods=['POST'])
def train_models():
    """Train ML models (this may take several minutes)."""
    try:
        # Sync data from VPS if configured
        sync_data_from_vps()
        
        # Train models
        models = predictor.train_all_models()
        
        if models:
            predictor.save_models()
            
            # Generate predictions
            predictions = predictor.predict_all_companies()
            
            # Save predictions
            output_file = project_root / 'data' / 'company_predictions.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'predictions': predictions,
                    'total_companies': len(predictions),
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'status': 'success',
                'models_trained': list(models.keys()),
                'total_companies': len(predictions),
                'message': 'Models trained and predictions generated',
                'data_source': 'vps' if VPS_URL else 'local'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No models could be trained. Check data availability.'
            }), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get ML statistics."""
    try:
        import pandas as pd
        
        predictions_file = project_root / 'data' / 'company_predictions.json'
        models_file = project_root / 'data' / 'ml_models.pkl'
        
        stats = {
            'models_available': models_file.exists() or len(predictor.models) > 0,
            'predictions_available': predictions_file.exists(),
            'total_companies': 0,
            'predictions_summary': {}
        }
        
        if predictions_file.exists():
            with open(predictions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            predictions = data.get('predictions', {})
            stats['total_companies'] = len(predictions)
            
            # Summary statistics
            wasp_predictions = [p.get('wasp_adoption', {}).get('prediction', False) 
                              for p in predictions.values() 
                              if 'wasp_adoption' in p]
            sust_predictions = [p.get('sustainability_focus', {}).get('prediction', 'unknown')
                              for p in predictions.values()
                              if 'sustainability_focus' in p]
            
            stats['predictions_summary'] = {
                'wasp_adoption_positive': sum(wasp_predictions),
                'wasp_adoption_total': len(wasp_predictions),
                'sustainability_levels': dict(pd.Series(sust_predictions).value_counts()) if sust_predictions else {}
            }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ML Service for PC')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5001, help='Port to bind to (default: 5001)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print("="*80)
    print("ML PREDICTOR SERVICE (PC)")
    print("="*80)
    print(f"Starting on http://{args.host}:{args.port}")
    print(f"VPS should proxy requests to this address")
    print("="*80)
    
    app.run(host=args.host, port=args.port, debug=args.debug)

