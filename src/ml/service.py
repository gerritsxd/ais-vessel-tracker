"""
ML Service API

Flask-based REST API for ML predictions.
Can run standalone on PC or be integrated with VPS web_tracker.

Endpoints:
- GET /health - Health check
- GET /predictions - All company predictions
- GET /predictions/<company> - Single company prediction
- POST /train - Train models
- POST /sync - Sync data from VPS
- GET /stats - Model statistics
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path
import sys
import os
from datetime import datetime

from .predictor import CompanyMLPredictor

# Configuration
VPS_URL = os.environ.get('VPS_URL', '')


def create_app(predictor: CompanyMLPredictor = None) -> Flask:
    """
    Create Flask application for ML service.
    
    Args:
        predictor: Optional pre-configured predictor instance
        
    Returns:
        Flask application
    """
    app = Flask(__name__)
    CORS(app)
    
    # Use provided predictor or create new one
    if predictor is None:
        predictor = CompanyMLPredictor()
    
    # Store predictor in app config
    app.config['predictor'] = predictor
    app.config['project_root'] = Path(__file__).parent.parent.parent
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        pred = app.config['predictor']
        return jsonify({
            'status': 'ok',
            'service': 'ml-predictor',
            'models_loaded': len(pred.models) > 0,
            'vps_url': VPS_URL if VPS_URL else None,
            'data_source': 'vps' if VPS_URL else 'local'
        })
    
    @app.route('/sync', methods=['POST'])
    def sync_data():
        """Sync training data from VPS."""
        if not VPS_URL:
            return jsonify({
                'status': 'skipped',
                'message': 'VPS_URL not configured'
            })
        
        try:
            success = _sync_data_from_vps(app.config['project_root'])
            return jsonify({
                'status': 'success' if success else 'partial',
                'message': 'Data synced from VPS'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/predictions', methods=['GET'])
    def get_predictions():
        """Get predictions for all companies."""
        pred = app.config['predictor']
        project_root = app.config['project_root']
        
        try:
            # Try cached predictions first
            predictions_file = project_root / 'data' / 'company_predictions.json'
            if predictions_file.exists():
                with open(predictions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return jsonify(data)
            
            # Generate predictions if no cache
            if not pred.models:
                if not pred.load_models():
                    return jsonify({
                        'error': 'Models not trained. Call /train first.',
                        'predictions': {},
                        'total_companies': 0
                    }), 404
            
            predictions = pred.predict_all_companies()
            
            return jsonify({
                'predictions': predictions,
                'total_companies': len(predictions),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/predictions/<company_name>', methods=['GET'])
    def get_company_prediction(company_name):
        """Get prediction for a specific company."""
        pred = app.config['predictor']
        
        try:
            if not pred.models:
                if not pred.load_models():
                    return jsonify({
                        'error': 'Models not trained',
                        'company': company_name
                    }), 404
            
            # Load company data
            intelligence_data = pred.load_intelligence_data()
            profile_data = pred.load_profile_data()
            
            # Merge data
            company_data = {}
            if company_name in intelligence_data:
                company_data.update(intelligence_data[company_name])
            if company_name in profile_data:
                company_data.update(profile_data[company_name])
            
            if not company_data:
                return jsonify({
                    'error': 'Company not found',
                    'company': company_name
                }), 404
            
            predictions = pred.predict_company(company_name, company_data)
            
            return jsonify({
                'company': company_name,
                'predictions': predictions
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/train', methods=['POST'])
    def train_models():
        """Train ML models."""
        pred = app.config['predictor']
        project_root = app.config['project_root']
        
        try:
            # Sync data from VPS if configured
            if VPS_URL:
                _sync_data_from_vps(project_root)
            
            # Train models
            models = pred.train_all_models()
            
            if models:
                pred.save_models()
                
                # Generate and save predictions
                predictions = pred.predict_all_companies()
                
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
        """Get ML model statistics."""
        pred = app.config['predictor']
        project_root = app.config['project_root']
        
        try:
            import pandas as pd
            
            predictions_file = project_root / 'data' / 'company_predictions.json'
            models_file = project_root / 'data' / 'ml_models.pkl'
            
            stats = {
                'models_available': models_file.exists() or len(pred.models) > 0,
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
                wasp_predictions = [
                    p.get('wasp_adoption', {}).get('prediction', False)
                    for p in predictions.values()
                    if 'wasp_adoption' in p
                ]
                sust_predictions = [
                    p.get('sustainability_focus', {}).get('prediction', 'unknown')
                    for p in predictions.values()
                    if 'sustainability_focus' in p
                ]
                
                stats['predictions_summary'] = {
                    'wasp_adoption_positive': sum(wasp_predictions),
                    'wasp_adoption_total': len(wasp_predictions),
                    'sustainability_levels': dict(pd.Series(sust_predictions).value_counts()) if sust_predictions else {}
                }
            
            return jsonify(stats)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return app


def _sync_data_from_vps(project_root: Path) -> bool:
    """
    Fetch training data from VPS and save locally.
    
    Args:
        project_root: Project root directory
        
    Returns:
        True if sync successful
    """
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
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                intel_file = data_dir / f"company_intelligence_gemini_{timestamp}.json"
                with open(intel_file, 'w', encoding='utf-8') as f:
                    json.dump(intel_data, f, indent=2, ensure_ascii=False)
                print(f"    Saved {len(intel_data['companies'])} companies")
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
                print(f"    Saved {len(profile_data['companies'])} companies")
        except Exception as e:
            print(f"    [WARN] Could not fetch profile data: {e}")
        
        print("[INFO] Data sync completed")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to sync data from VPS: {e}")
        return False


def run_standalone(host: str = '0.0.0.0', port: int = 5001, debug: bool = False):
    """
    Run ML service as standalone Flask app.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
    """
    print("=" * 80)
    print("ML PREDICTOR SERVICE")
    print("=" * 80)
    print(f"Starting on http://{host}:{port}")
    if VPS_URL:
        print(f"VPS URL: {VPS_URL}")
    print("=" * 80)
    
    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ML Service')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5001, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    run_standalone(host=args.host, port=args.port, debug=args.debug)


