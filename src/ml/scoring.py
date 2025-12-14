"""
Econowind Fit Score Calculator

This module implements the deterministic scoring formula for wind propulsion retrofit candidates.
The Econowind Fit Score ranges from 0-8 points based on four criteria.

SCORING FORMULA:
================

Total Score = Ship Type Score + Length Score + CO2 Intensity Score + Technical Efficiency Score

1. SHIP TYPE SCORE (0-2 points)
   - +2 points: Preferred types (Bulk carrier, General cargo, Chemical tanker, 
                LNG carrier, Ro-Ro cargo ship, Other ship types)
   - +0 points: Non-preferred types (Container ships, Passenger ships, etc.)
   
   Rationale: These ship types have deck space and operational profiles 
   favorable for wind propulsion systems.

2. VESSEL LENGTH SCORE (0-2 points)
   - +2 points: Optimal size (100-160m) - ideal for current wind tech
   - +1 point:  Acceptable size (80-100m or 160-200m) 
   - +0 points: Outside preferred range (<80m or >200m)
   
   Rationale: Medium-sized vessels benefit most from wind propulsion. 
   Too small = insufficient fuel savings, too large = complex installation.

3. CO2 EMISSIONS INTENSITY SCORE (0-2 points)
   - +2 points: Top 25% emitters (highest kg CO2/nautical mile)
   - +1 point:  Above median (50-75th percentile)
   - +0 points: Below median (already efficient)
   
   Rationale: Higher emitters have more savings potential from wind assist.
   Wind propulsion typically saves 5-30% fuel depending on route.

4. TECHNICAL EFFICIENCY SCORE (0-2 points)
   - +2 points: Poor efficiency (EEXI > 10 gCO2/t·nm)
   - +1 point:  Moderate efficiency (6-10 gCO2/t·nm)
   - +0 points: Good efficiency (< 6 gCO2/t·nm)
   
   Rationale: Less efficient vessels have more room for improvement
   and face more regulatory pressure (CII ratings, EU ETS costs).

INTERPRETATION:
===============
- Score 6-8: Excellent candidate for wind propulsion retrofit
- Score 4-5: Good candidate, worth detailed analysis
- Score 2-3: Potential candidate, further evaluation needed
- Score 0-1: Low priority, likely not cost-effective

EXAMPLE:
========
Vessel: Bulk carrier, 145m length, high emissions (top 25%), EEXI 12.5 gCO2/t·nm
- Ship Type: +2 (Bulk carrier is preferred)
- Length: +2 (145m is in optimal 100-160m range)  
- CO2 Intensity: +2 (top 25% emitter)
- Tech Efficiency: +2 (12.5 > 10, poor efficiency)
- TOTAL: 8/8 - Excellent retrofit candidate
"""

from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np

# Scoring configuration - these weights can be adjusted
SCORING_WEIGHTS = {
    'ship_type': {
        'max_score': 2,
        'preferred_types': {
            "Bulk carrier", "General cargo", "Chemical tanker",
            "LNG carrier", "Other ship types", "Ro-Ro cargo ship"
        }
    },
    'length': {
        'max_score': 2,
        'optimal_range': (100, 160),  # +2 points
        'acceptable_ranges': [(80, 100), (160, 200)]  # +1 point each
    },
    'co2_intensity': {
        'max_score': 2,
        'top_quartile_threshold': 0.75,  # percentile for +2 points
        'median_threshold': 0.50  # percentile for +1 point
    },
    'technical_efficiency': {
        'max_score': 2,
        'poor_threshold': 10,  # gCO2/t·nm for +2 points
        'moderate_threshold': 6  # gCO2/t·nm for +1 point
    }
}


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of Econowind fit score calculation."""
    total_score: int
    max_score: int
    
    ship_type_score: int
    ship_type_value: str
    ship_type_explanation: str
    
    length_score: int
    length_value: Optional[float]
    length_explanation: str
    
    co2_score: int
    co2_value: Optional[float]
    co2_explanation: str
    
    efficiency_score: int
    efficiency_value: Optional[str]
    efficiency_explanation: str
    
    recommendation: str
    recommendation_class: str  # 'high', 'medium', 'low', 'na'


class EconowindScorer:
    """
    Calculator for Econowind fit scores.
    
    The scorer evaluates vessels on four dimensions to determine
    suitability for wind propulsion retrofit.
    """
    
    def __init__(self, co2_percentiles: Optional[Dict[str, float]] = None):
        """
        Initialize scorer with optional CO2 percentile thresholds.
        
        Args:
            co2_percentiles: Dict with 'p50' and 'p75' keys for median 
                           and 75th percentile CO2/distance values.
                           If None, must be computed from dataset.
        """
        self.co2_percentiles = co2_percentiles or {}
        
    def set_co2_percentiles(self, co2_values: list) -> None:
        """
        Compute CO2 percentile thresholds from dataset.
        
        Args:
            co2_values: List of avg_co2_per_distance values from fleet
        """
        if co2_values:
            self.co2_percentiles = {
                'p50': float(np.percentile(co2_values, 50)),
                'p75': float(np.percentile(co2_values, 75))
            }
    
    def score_ship_type(self, ship_type: Optional[str]) -> Tuple[int, str]:
        """
        Score based on ship type suitability for wind propulsion.
        
        Returns:
            Tuple of (score, explanation)
        """
        if not ship_type:
            return 0, "No ship type data available"
        
        preferred = SCORING_WEIGHTS['ship_type']['preferred_types']
        
        if ship_type in preferred:
            return 2, f"✓ Preferred type ({ship_type})"
        else:
            return 0, f"✗ Not a preferred type ({ship_type})"
    
    def score_length(self, length: Optional[float]) -> Tuple[int, str]:
        """
        Score based on vessel length.
        
        Returns:
            Tuple of (score, explanation)
        """
        if not length:
            return 0, "No length data available"
        
        optimal = SCORING_WEIGHTS['length']['optimal_range']
        acceptable = SCORING_WEIGHTS['length']['acceptable_ranges']
        
        if optimal[0] <= length <= optimal[1]:
            return 2, f"✓ Optimal size ({length}m is in {optimal[0]}-{optimal[1]}m range)"
        
        for low, high in acceptable:
            if low <= length <= high:
                return 1, f"~ Acceptable size ({length}m is in {low}-{high}m range)"
        
        return 0, f"✗ Outside preferred range ({length}m)"
    
    def score_co2_intensity(self, avg_co2: Optional[float]) -> Tuple[int, str]:
        """
        Score based on CO2 emissions intensity.
        
        Higher emissions = higher score (more savings potential).
        
        Returns:
            Tuple of (score, explanation)
        """
        if not avg_co2:
            return 0, "No CO₂/distance data available"
        
        if not self.co2_percentiles:
            return 0, "CO₂ percentiles not computed"
        
        p75 = self.co2_percentiles.get('p75', float('inf'))
        p50 = self.co2_percentiles.get('p50', float('inf'))
        
        if avg_co2 >= p75:
            return 2, f"✓ High emitter ({avg_co2:.1f} kg/nm, top 25%)"
        elif avg_co2 >= p50:
            return 1, f"~ Above average ({avg_co2:.1f} kg/nm, above median)"
        else:
            return 0, f"✗ Below average ({avg_co2:.1f} kg/nm, already efficient)"
    
    def score_technical_efficiency(self, tech_eff: Optional[str]) -> Tuple[int, str]:
        """
        Score based on technical efficiency (EEXI rating).
        
        Lower efficiency = higher score (more improvement potential).
        
        Returns:
            Tuple of (score, explanation)
        """
        if not tech_eff:
            return 0, "No technical efficiency data"
        
        try:
            # Parse efficiency value from string like "EEXI (10.5 gCO₂/t·nm)"
            eff_value = float(str(tech_eff).split('(')[-1].strip(')').split()[0])
            
            poor_threshold = SCORING_WEIGHTS['technical_efficiency']['poor_threshold']
            mod_threshold = SCORING_WEIGHTS['technical_efficiency']['moderate_threshold']
            
            if eff_value > poor_threshold:
                return 2, f"✓ Poor efficiency ({eff_value:.1f} gCO₂/t·nm)"
            elif eff_value >= mod_threshold:
                return 1, f"~ Moderate efficiency ({eff_value:.1f} gCO₂/t·nm)"
            else:
                return 0, f"✗ Good efficiency ({eff_value:.1f} gCO₂/t·nm)"
        except:
            return 0, f"Could not parse: {tech_eff}"
    
    def calculate_score(
        self,
        ship_type: Optional[str] = None,
        length: Optional[float] = None,
        avg_co2_per_distance: Optional[float] = None,
        technical_efficiency: Optional[str] = None
    ) -> int:
        """
        Calculate total Econowind fit score (0-8).
        
        Args:
            ship_type: Ship type category (e.g., "Bulk carrier")
            length: Vessel length in meters
            avg_co2_per_distance: Average CO2 emissions per nautical mile
            technical_efficiency: EEXI rating string
            
        Returns:
            Total score from 0-8
        """
        ship_score, _ = self.score_ship_type(ship_type)
        length_score, _ = self.score_length(length)
        co2_score, _ = self.score_co2_intensity(avg_co2_per_distance)
        eff_score, _ = self.score_technical_efficiency(technical_efficiency)
        
        return ship_score + length_score + co2_score + eff_score
    
    def calculate_breakdown(
        self,
        ship_type: Optional[str] = None,
        length: Optional[float] = None,
        avg_co2_per_distance: Optional[float] = None,
        technical_efficiency: Optional[str] = None,
        vessel_name: Optional[str] = None,
        imo: Optional[int] = None
    ) -> ScoreBreakdown:
        """
        Calculate detailed score breakdown with explanations.
        
        Returns:
            ScoreBreakdown dataclass with all scoring details
        """
        ship_score, ship_expl = self.score_ship_type(ship_type)
        length_score, length_expl = self.score_length(length)
        co2_score, co2_expl = self.score_co2_intensity(avg_co2_per_distance)
        eff_score, eff_expl = self.score_technical_efficiency(technical_efficiency)
        
        total = ship_score + length_score + co2_score + eff_score
        
        # Generate recommendation
        if total >= 6:
            recommendation = "Excellent candidate for wind propulsion retrofit"
            rec_class = "high"
        elif total >= 4:
            recommendation = "Good candidate for wind propulsion retrofit"
            rec_class = "medium"
        elif total >= 2:
            recommendation = "Potential candidate, further analysis recommended"
            rec_class = "low"
        else:
            recommendation = "Low priority for wind propulsion retrofit"
            rec_class = "na"
        
        return ScoreBreakdown(
            total_score=total,
            max_score=8,
            ship_type_score=ship_score,
            ship_type_value=ship_type or "N/A",
            ship_type_explanation=ship_expl,
            length_score=length_score,
            length_value=length,
            length_explanation=length_expl,
            co2_score=co2_score,
            co2_value=avg_co2_per_distance,
            co2_explanation=co2_expl,
            efficiency_score=eff_score,
            efficiency_value=technical_efficiency,
            efficiency_explanation=eff_expl,
            recommendation=recommendation,
            recommendation_class=rec_class
        )
    
    def to_dict(self, breakdown: ScoreBreakdown) -> Dict[str, Any]:
        """Convert ScoreBreakdown to dictionary for JSON serialization."""
        return {
            'total_score': breakdown.total_score,
            'max_score': breakdown.max_score,
            'breakdown': [
                {
                    'category': 'Ship Type',
                    'score': breakdown.ship_type_score,
                    'max': 2,
                    'value': breakdown.ship_type_value,
                    'explanation': breakdown.ship_type_explanation,
                    'details': f"Preferred: {', '.join(SCORING_WEIGHTS['ship_type']['preferred_types'])}"
                },
                {
                    'category': 'Vessel Length',
                    'score': breakdown.length_score,
                    'max': 2,
                    'value': f"{breakdown.length_value}m" if breakdown.length_value else "N/A",
                    'explanation': breakdown.length_explanation,
                    'details': 'Optimal: 100-160m (+2), Acceptable: 80-100m or 160-200m (+1)'
                },
                {
                    'category': 'CO₂ Emissions Intensity',
                    'score': breakdown.co2_score,
                    'max': 2,
                    'value': f"{breakdown.co2_value:.1f} kg/nm" if breakdown.co2_value else "N/A",
                    'explanation': breakdown.co2_explanation,
                    'details': 'Top 25% emitters (+2), Above median (+1) - Higher emissions = more savings potential'
                },
                {
                    'category': 'Technical Efficiency',
                    'score': breakdown.efficiency_score,
                    'max': 2,
                    'value': breakdown.efficiency_value or "N/A",
                    'explanation': breakdown.efficiency_explanation,
                    'details': 'Poor efficiency >10 (+2), Moderate 6-10 (+1) - Lower efficiency = more improvement potential'
                }
            ],
            'recommendation': breakdown.recommendation,
            'recommendation_class': breakdown.recommendation_class
        }


# Convenience function for quick scoring
def calculate_econowind_score(
    ship_type: Optional[str] = None,
    length: Optional[float] = None,
    avg_co2_per_distance: Optional[float] = None,
    technical_efficiency: Optional[str] = None,
    co2_percentiles: Optional[Dict[str, float]] = None
) -> int:
    """
    Quick function to calculate Econowind fit score.
    
    Args:
        ship_type: Ship type category
        length: Vessel length in meters
        avg_co2_per_distance: Average CO2 per nautical mile
        technical_efficiency: EEXI rating string
        co2_percentiles: Optional dict with 'p50' and 'p75' thresholds
        
    Returns:
        Score from 0-8
    """
    scorer = EconowindScorer(co2_percentiles)
    return scorer.calculate_score(
        ship_type=ship_type,
        length=length,
        avg_co2_per_distance=avg_co2_per_distance,
        technical_efficiency=technical_efficiency
    )

