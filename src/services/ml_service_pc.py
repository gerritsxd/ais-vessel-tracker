"""
Standalone ML Service for PC
Runs ML training and predictions on your PC, accessible via HTTP API
This allows VPS to use your PC's resources for ML while serving the web interface
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path
import sys
import os

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

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'service': 'ml-predictor-pc',
        'models_loaded': len(predictor.models) > 0
    })

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
                    'timestamp': predictor.__class__.__module__  # Placeholder
                }, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'status': 'success',
                'models_trained': list(models.keys()),
                'total_companies': len(predictions),
                'message': 'Models trained and predictions generated'
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

