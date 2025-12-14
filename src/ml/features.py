"""
Feature Extraction for ML Predictions

This module handles extracting features from company intelligence and profile data
for use in ML models predicting WASP adoption, sustainability focus, etc.

FEATURE CATEGORIES:
==================

1. STRUCTURED FEATURES (from database/metadata):
   - vessel_count: Number of vessels in fleet
   - avg_emissions: Average total CO2 emissions
   - avg_co2_distance: Average CO2 per nautical mile
   - avg_wasp_score: Average Econowind fit score

2. INTELLIGENCE FEATURES (from Gemini scraper):
   - grants_count: Number of grant/subsidy findings
   - violations_count: Number of legal violation findings
   - sustainability_count: Sustainability news mentions
   - reputation_count: Reputation-related findings
   - financial_pressure_count: Financial pressure indicators
   - total_findings: Sum of all intelligence findings

3. NLP/SENTIMENT FEATURES (from text analysis):
   - polarity: Sentiment polarity (-1 to 1, negative to positive)
   - subjectivity: How subjective vs objective (0 to 1)
   - positive_score: Normalized positive sentiment
   - negative_score: Normalized negative sentiment

4. KEYWORD FEATURES (boolean indicators):
   - has_wind_keywords: Wind propulsion terms found
   - has_grant_keywords: Grant/subsidy terms found
   - has_sustainability_keywords: Green/sustainability terms found
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import re

# Try to import NLP library
try:
    from textblob import TextBlob
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False


# Keyword dictionaries for feature extraction
WIND_KEYWORDS = [
    'wind propulsion', 'rotor sail', 'wing sail', 'wasp', 'econowind',
    'flettner', 'wind-assisted', 'wind power', 'wind assisted',
    'norsepower', 'bound4blue', 'anemoi', 'windship'
]

GRANT_KEYWORDS = [
    'grant', 'subsidy', 'funding', 'eu fund', 'government support',
    'incentive', 'tax credit', 'financial support', 'public funding'
]

SUSTAINABILITY_KEYWORDS = [
    'sustainability', 'green', 'decarbonization', 'carbon neutral', 
    'emissions reduction', 'net zero', 'climate', 'environmental',
    'esg', 'sustainable shipping', 'green shipping', 'eco-friendly'
]


class FeatureExtractor:
    """
    Extracts ML features from company intelligence and profile data.
    
    Features are designed to predict:
    - WASP adoption likelihood
    - Sustainability focus level
    - Company type classification
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        
    def extract_text(self, company_data: Dict[str, Any]) -> str:
        """
        Extract all text content from company data for NLP analysis.
        
        Combines text from:
        - Intelligence findings (titles, snippets)
        - Wikipedia summary
        - Website page content
        
        Args:
            company_data: Dictionary containing company intelligence/profile data
            
        Returns:
            Combined text string for analysis
        """
        text_parts = []
        
        # From intelligence data (Gemini scraper results)
        if 'intelligence' in company_data:
            for category, cat_data in company_data['intelligence'].items():
                findings = cat_data.get('findings', [])
                for finding in findings:
                    text_parts.append(finding.get('title', ''))
                    text_parts.append(finding.get('snippet', ''))
        
        # From profile data (Company Profiler V3)
        if 'text_data' in company_data:
            wiki = company_data['text_data'].get('wikipedia', {})
            if wiki.get('summary'):
                text_parts.append(wiki['summary'])
            
            website = company_data['text_data'].get('website', {})
            for page in website.get('pages', []):
                text_parts.append(page.get('text', ''))
        
        return ' '.join(filter(None, text_parts))
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Perform sentiment analysis on text using TextBlob.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with:
            - polarity: -1 (negative) to 1 (positive)
            - subjectivity: 0 (objective) to 1 (subjective)
            - positive_score: max(0, polarity)
            - negative_score: abs(min(0, polarity))
        """
        if not NLP_AVAILABLE or not text:
            return {
                'polarity': 0.0,
                'subjectivity': 0.0,
                'positive_score': 0.0,
                'negative_score': 0.0
            }
        
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            return {
                'polarity': float(polarity),
                'subjectivity': float(subjectivity),
                'positive_score': float(max(0, polarity)),
                'negative_score': float(abs(min(0, polarity)))
            }
        except Exception as e:
            if self.verbose:
                print(f"Sentiment analysis error: {e}")
            return {
                'polarity': 0.0,
                'subjectivity': 0.0,
                'positive_score': 0.0,
                'negative_score': 0.0
            }
    
    def check_keywords(self, text: str, keywords: List[str]) -> bool:
        """
        Check if any keywords are present in text.
        
        Args:
            text: Text to search
            keywords: List of keywords/phrases to look for
            
        Returns:
            True if any keyword found, False otherwise
        """
        if not text:
            return False
        
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)
    
    def extract_structured_features(self, company_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract all structured (numerical) features from company data.
        
        This is the main feature extraction method for ML models.
        
        Args:
            company_data: Dictionary with company intelligence/profile data
            
        Returns:
            Dictionary of feature name -> float value
        """
        features = {}
        
        # ===== METADATA/ATTRIBUTES FEATURES =====
        # Try multiple possible locations for metadata
        metadata = (
            company_data.get('metadata', {}) or 
            company_data.get('attributes', {}) or 
            {}
        )
        
        features['vessel_count'] = float(metadata.get('vessel_count', 0))
        features['avg_emissions'] = float(
            metadata.get('avg_emissions', 0) or 
            metadata.get('avg_emissions_tons', 0) or 0
        )
        features['avg_co2_distance'] = float(
            metadata.get('avg_co2_distance', 0) or 
            metadata.get('avg_co2_per_distance', 0) or 0
        )
        features['avg_wasp_score'] = float(
            metadata.get('avg_wasp_fit_score', 0) or 0
        )
        
        # ===== INTELLIGENCE CATEGORY COUNTS =====
        intelligence = company_data.get('intelligence', {})
        
        features['grants_count'] = float(
            intelligence.get('grants_subsidies', {}).get('results_count', 0)
        )
        features['violations_count'] = float(
            intelligence.get('legal_violations', {}).get('results_count', 0)
        )
        features['sustainability_count'] = float(
            intelligence.get('sustainability_news', {}).get('results_count', 0)
        )
        features['reputation_count'] = float(
            intelligence.get('reputation', {}).get('results_count', 0)
        )
        features['financial_pressure_count'] = float(
            intelligence.get('financial_pressure', {}).get('results_count', 0)
        )
        
        features['total_findings'] = sum([
            features['grants_count'],
            features['violations_count'],
            features['sustainability_count'],
            features['reputation_count'],
            features['financial_pressure_count']
        ])
        
        # ===== SENTIMENT FEATURES =====
        text = self.extract_text(company_data)
        sentiment = self.analyze_sentiment(text)
        features.update(sentiment)
        
        # ===== KEYWORD FEATURES =====
        text_lower = text.lower() if text else ""
        
        features['has_wind_keywords'] = float(
            1.0 if self.check_keywords(text, WIND_KEYWORDS) else 0.0
        )
        features['has_grant_keywords'] = float(
            1.0 if self.check_keywords(text, GRANT_KEYWORDS) else 0.0
        )
        features['has_sustainability_keywords'] = float(
            1.0 if self.check_keywords(text, SUSTAINABILITY_KEYWORDS) else 0.0
        )
        
        return features
    
    def build_feature_matrix(
        self, 
        companies_data: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Build feature matrix from multiple companies.
        
        Args:
            companies_data: Dict mapping company name -> company data
            
        Returns:
            Tuple of (feature_dataframe, list_of_company_names)
        """
        features_list = []
        company_names = []
        
        for company_name, company_data in companies_data.items():
            features = self.extract_structured_features(company_data)
            features_list.append(features)
            company_names.append(company_name)
        
        df = pd.DataFrame(features_list, index=company_names)
        return df, company_names
    
    def get_feature_names(self) -> List[str]:
        """
        Get list of all feature names in extraction order.
        
        Returns:
            List of feature names
        """
        return [
            # Metadata features
            'vessel_count',
            'avg_emissions', 
            'avg_co2_distance',
            'avg_wasp_score',
            # Intelligence counts
            'grants_count',
            'violations_count',
            'sustainability_count',
            'reputation_count',
            'financial_pressure_count',
            'total_findings',
            # Sentiment features
            'polarity',
            'subjectivity',
            'positive_score',
            'negative_score',
            # Keyword features
            'has_wind_keywords',
            'has_grant_keywords',
            'has_sustainability_keywords'
        ]
    
    def describe_features(self) -> Dict[str, str]:
        """
        Get human-readable descriptions of all features.
        
        Returns:
            Dict mapping feature name -> description
        """
        return {
            'vessel_count': 'Number of vessels in company fleet',
            'avg_emissions': 'Average total CO2 emissions (tonnes)',
            'avg_co2_distance': 'Average CO2 per nautical mile (kg/nm)',
            'avg_wasp_score': 'Average Econowind fit score (0-8)',
            'grants_count': 'Number of grant/subsidy intelligence findings',
            'violations_count': 'Number of legal violation findings',
            'sustainability_count': 'Number of sustainability news findings',
            'reputation_count': 'Number of reputation-related findings',
            'financial_pressure_count': 'Number of financial pressure indicators',
            'total_findings': 'Total intelligence findings across all categories',
            'polarity': 'Text sentiment polarity (-1 negative to +1 positive)',
            'subjectivity': 'Text subjectivity (0 objective to 1 subjective)',
            'positive_score': 'Positive sentiment component',
            'negative_score': 'Negative sentiment component',
            'has_wind_keywords': 'Wind propulsion keywords found in text',
            'has_grant_keywords': 'Grant/subsidy keywords found in text',
            'has_sustainability_keywords': 'Sustainability keywords found in text'
        }


# Database-only feature extraction (for simple predictor)
def extract_database_features(
    company_name: str,
    ship_type: str,
    avg_emissions: float,
    avg_co2_distance: float,
    avg_fuel_consumption: float,
    avg_tech_efficiency: float,
    avg_tonnage: float,
    avg_distance: float,
    fleet_size: int
) -> Dict[str, float]:
    """
    Extract features using only database fields (no web scraping).
    
    This is used by the simple WASP predictor that only uses EU MRV data.
    
    Args:
        company_name: Company name
        ship_type: Primary ship type
        avg_emissions: Average CO2 emissions
        avg_co2_distance: Average CO2/nm
        avg_fuel_consumption: Average fuel/distance
        avg_tech_efficiency: Average technical efficiency
        avg_tonnage: Average gross tonnage
        avg_distance: Average distance travelled
        fleet_size: Number of vessels
        
    Returns:
        Feature dictionary
    """
    features = {
        'avg_emissions': avg_emissions or 0,
        'avg_co2_distance': avg_co2_distance or 0,
        'avg_fuel_consumption': avg_fuel_consumption or 0,
        'avg_tech_efficiency': avg_tech_efficiency or 0,
        'avg_tonnage': avg_tonnage or 0,
        'avg_distance': avg_distance or 0,
        'fleet_size': fleet_size or 0,
    }
    
    # Derived features
    if avg_tonnage and avg_tonnage > 0:
        features['emissions_per_tonnage'] = avg_emissions / (avg_tonnage + 1)
    else:
        features['emissions_per_tonnage'] = 0
        
    if avg_distance and avg_distance > 0:
        features['fuel_efficiency_ratio'] = avg_fuel_consumption / (avg_distance + 1)
    else:
        features['fuel_efficiency_ratio'] = 0
    
    return features


