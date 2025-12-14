"""
ML Module for AIS Vessel Tracker

This module provides machine learning capabilities for predicting:
- WASP (Wind-Assisted Ship Propulsion) adoption likelihood
- Sustainability focus classification  
- Company type classification

Submodules:
- predictor: Main CompanyMLPredictor class
- features: Feature extraction and engineering
- scoring: Econowind fit score calculation
- service: Flask API service for ML predictions
"""

from .predictor import CompanyMLPredictor
from .features import FeatureExtractor
from .scoring import EconowindScorer, SCORING_WEIGHTS

__all__ = [
    'CompanyMLPredictor',
    'FeatureExtractor', 
    'EconowindScorer',
    'SCORING_WEIGHTS'
]


