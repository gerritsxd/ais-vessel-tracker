"""
Simplified Technical Fit Score Calculator
Uses only basic vessel characteristics: length, ship_type, beam (if available), flag_state

Based on WASP vessel patterns from FIT_SCORE_FORMULA_PROPOSAL.md
"""

from typing import Optional, Tuple, Dict


class TechnicalFitScorer:
    """
    Calculate technical fit score for WASP installation.
    
    Uses only:
    - Length (100% coverage)
    - Ship Type (100% coverage)
    - Beam (99.9% coverage - optional)
    - Flag State (available - optional bonus)
    """
    
    def __init__(self):
        """Initialize scorer with WASP vessel patterns."""
        # WASP vessel length sweet spot: 120-200m (46% of WASP vessels)
        self.optimal_length_range = (120, 200)
        self.good_length_ranges = [(100, 120), (200, 250)]
        
        # WASP vessel ship types (from actual installations)
        self.preferred_ship_types = {
            70: 30,  # Cargo (Bulk, General Cargo, Ro-Ro) - 16 WASP vessels
            80: 28,  # Tanker (Chemical, Oil, Gas) - 8 WASP vessels
            79: 25,  # Other (includes some cargo) - 5 WASP vessels
            72: 25,  # Cargo (Ro-Ro) - 1 WASP vessel
            83: 20,  # Other (CO2 Tanker) - 2 WASP vessels
            89: 15,  # Other - 1 WASP vessel
        }
        
        # WASP average length/beam ratio: 6.59 (range: 5.13-9.08)
        self.optimal_ratio_range = (5.0, 7.0)
        self.good_ratio_ranges = [(4.5, 5.0), (7.0, 8.0)]
        
        # Flag states with high WASP adoption (optional bonus)
        # Based on WASP vessel flag distribution
        self.preferred_flags = {
            'NL': 2,  # Netherlands - many WASP vessels
            'DK': 2,  # Denmark
            'NO': 2,  # Norway
            'DE': 1,  # Germany
            'FI': 1,  # Finland
            'SE': 1,  # Sweden
        }
    
    def score_length(self, length: Optional[float]) -> Tuple[float, str]:
        """
        Score based on vessel length (0-40 points).
        
        WASP pattern: Sweet spot is 150-200m (21 vessels), good coverage 120-250m.
        """
        if not length or length <= 0:
            return 0.0, "No length data"
        
        # Peak range: 150-200m (35-40 points)
        if 150 <= length <= 200:
            score = 35 + 5 * min((length - 150) / 50, 1)
            return score, f"Optimal length ({length}m)"
        
        # Good range: 120-150m (30-35 points)
        elif 120 <= length < 150:
            score = 30 + 5 * ((length - 120) / 30)
            return score, f"Good length ({length}m)"
        
        # Good range: 200-250m (35-30 points)
        elif 200 < length <= 250:
            score = 35 - 5 * ((length - 200) / 50)
            return score, f"Good length ({length}m)"
        
        # Acceptable: 100-120m (20-30 points)
        elif 100 <= length < 120:
            score = 20 + 10 * ((length - 100) / 20)
            return score, f"Acceptable length ({length}m)"
        
        # Acceptable: 250-300m (30-25 points)
        elif 250 < length <= 300:
            score = 30 - 5 * ((length - 250) / 50)
            return score, f"Acceptable length ({length}m)"
        
        # Smaller vessels: 80-100m (10-20 points)
        elif 80 <= length < 100:
            score = 10 + 10 * ((length - 80) / 20)
            return score, f"Small vessel ({length}m)"
        
        # Very small: <80m (0-10 points)
        elif length < 80:
            score = 10 * (length / 80)
            return score, f"Very small ({length}m)"
        
        # Very large: >300m (20-25 points)
        else:  # length > 300
            score = 25 - 5 * min((length - 300) / 100, 1)
            return score, f"Very large ({length}m)"
    
    def score_ship_type(self, ship_type: Optional[int]) -> Tuple[float, str]:
        """
        Score based on ship type (0-30 points).
        
        Based on actual WASP installations by ship_type code.
        """
        if ship_type is None:
            return 10.0, "Unknown ship type"
        
        score = self.preferred_ship_types.get(ship_type, 10)
        
        type_names = {
            70: "Cargo",
            80: "Tanker",
            79: "Other",
            72: "Cargo (Ro-Ro)",
            83: "Other (CO2 Tanker)",
            89: "Other",
        }
        
        type_name = type_names.get(ship_type, f"Type {ship_type}")
        return score, f"{type_name} (score: {score}/30)"
    
    def score_length_beam_ratio(self, length: Optional[float], beam: Optional[float]) -> Tuple[float, str]:
        """
        Score based on length/beam ratio (0-20 points).
        
        WASP vessels average 6.59 ratio (range: 5.13-9.08).
        Optimal: 5.0-7.0
        """
        if not length or length <= 0:
            return 10.0, "No length data"
        
        if not beam or beam <= 0:
            return 10.0, "No beam data (neutral score)"
        
        ratio = length / beam
        
        # Optimal range: 5.0-7.0 (20 points)
        if 5.0 <= ratio <= 7.0:
            return 20.0, f"Optimal ratio ({ratio:.2f})"
        
        # Good range: 4.5-5.0 or 7.0-8.0 (15 points)
        elif (4.5 <= ratio < 5.0) or (7.0 < ratio <= 8.0):
            return 15.0, f"Good ratio ({ratio:.2f})"
        
        # Acceptable: 4.0-4.5 or 8.0-9.0 (10 points)
        elif (4.0 <= ratio < 4.5) or (8.0 < ratio <= 9.0):
            return 10.0, f"Acceptable ratio ({ratio:.2f})"
        
        # Poor: outside ranges (5 points)
        else:
            return 5.0, f"Poor ratio ({ratio:.2f})"
    
    def score_flag_state(self, flag_state: Optional[str]) -> Tuple[float, str]:
        """
        Optional bonus for flag states with high WASP adoption (0-2 points).
        
        Based on WASP vessel flag distribution.
        """
        if not flag_state:
            return 0.0, "No flag data"
        
        flag_upper = flag_state.upper()
        bonus = self.preferred_flags.get(flag_upper, 0)
        
        if bonus > 0:
            return float(bonus), f"Preferred flag ({flag_state})"
        else:
            return 0.0, f"Standard flag ({flag_state})"
    
    def calculate_score(
        self,
        length: Optional[float] = None,
        ship_type: Optional[int] = None,
        beam: Optional[float] = None,
        flag_state: Optional[str] = None,
        detailed_ship_type: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Calculate technical fit score using only basic vessel characteristics.
        
        Args:
            length: Vessel length in meters
            ship_type: Numeric ship type code (70, 80, etc.)
            beam: Vessel beam/width in meters (optional)
            flag_state: Flag state code (optional)
            detailed_ship_type: Text ship type (optional bonus)
        
        Returns:
            Dict with score breakdown and total score (0-100)
        """
        # Component 1: Length (40% weight = 40 points max)
        length_score, length_explanation = self.score_length(length)
        
        # Component 2: Ship Type (30% weight = 30 points max)
        ship_type_score, ship_type_explanation = self.score_ship_type(ship_type)
        
        # Component 3: Length/Beam Ratio (20% weight = 20 points max)
        ratio_score, ratio_explanation = self.score_length_beam_ratio(length, beam)
        
        # Component 4: Flag State Bonus (optional, 2 points max)
        flag_score, flag_explanation = self.score_flag_state(flag_state)
        
        # Component 5: Detailed Ship Type Bonus (optional, 10 points max)
        text_bonus = 0.0
        text_explanation = "No detailed ship type"
        if detailed_ship_type:
            wasp_types = [
                'bulk carrier', 'general cargo', 'ro-ro', 'ro/ro',
                'chemical tanker', 'tanker', 'ferry', 'gas carrier',
                'container', 'cement carrier'
            ]
            detailed_lower = detailed_ship_type.lower()
            if any(wasp_type in detailed_lower for wasp_type in wasp_types):
                text_bonus = 10.0
                text_explanation = f"Matches WASP type: {detailed_ship_type}"
        
        # Total score (0-100)
        total_score = length_score + ship_type_score + ratio_score + flag_score + text_bonus
        total_score = min(100.0, max(0.0, total_score))  # Clamp to 0-100
        
        # Determine fit level
        if total_score >= 80:
            fit_level = "Excellent"
            recommendation = "Highly suitable for WASP installation"
        elif total_score >= 60:
            fit_level = "Good"
            recommendation = "Good candidate for WASP"
        elif total_score >= 40:
            fit_level = "Moderate"
            recommendation = "Possible but may require evaluation"
        elif total_score >= 20:
            fit_level = "Low"
            recommendation = "Less suitable, may have constraints"
        else:
            fit_level = "Poor"
            recommendation = "Unlikely to be suitable"
        
        return {
            'total_score': round(total_score, 1),
            'max_score': 100.0,
            'fit_level': fit_level,
            'recommendation': recommendation,
            'breakdown': {
                'length': {
                    'score': round(length_score, 1),
                    'max': 40.0,
                    'explanation': length_explanation
                },
                'ship_type': {
                    'score': round(ship_type_score, 1),
                    'max': 30.0,
                    'explanation': ship_type_explanation
                },
                'length_beam_ratio': {
                    'score': round(ratio_score, 1),
                    'max': 20.0,
                    'explanation': ratio_explanation
                },
                'flag_state': {
                    'score': round(flag_score, 1),
                    'max': 2.0,
                    'explanation': flag_explanation
                },
                'text_match': {
                    'score': round(text_bonus, 1),
                    'max': 10.0,
                    'explanation': text_explanation
                }
            }
        }


def calculate_fit_score_simple(
    length: Optional[float],
    ship_type: Optional[int],
    beam: Optional[float] = None,
    flag_state: Optional[str] = None
) -> float:
    """
    Quick function to calculate fit score (0-100).
    
    Args:
        length: Vessel length in meters
        ship_type: Numeric ship type code
        beam: Vessel beam (optional)
        flag_state: Flag state (optional)
    
    Returns:
        Fit score from 0-100
    """
    scorer = TechnicalFitScorer()
    result = scorer.calculate_score(length, ship_type, beam, flag_state)
    return result['total_score']


if __name__ == "__main__":
    # Test the scorer
    scorer = TechnicalFitScorer()
    
    # Test cases
    test_vessels = [
        {"length": 150, "ship_type": 70, "beam": 25, "flag_state": "NL"},
        {"length": 200, "ship_type": 80, "beam": 30, "flag_state": "DK"},
        {"length": 100, "ship_type": 70, "beam": 15, "flag_state": "US"},
        {"length": 300, "ship_type": 70, "beam": 40, "flag_state": "CN"},
    ]
    
    print("="*80)
    print("TECHNICAL FIT SCORE TEST")
    print("="*80)
    
    for vessel in test_vessels:
        result = scorer.calculate_score(**vessel)
        print(f"\nVessel: {vessel['length']}m, Type {vessel['ship_type']}, Beam {vessel['beam']}m")
        print(f"Total Score: {result['total_score']}/100 ({result['fit_level']})")
        print(f"Recommendation: {result['recommendation']}")
        print("\nBreakdown:")
        for component, data in result['breakdown'].items():
            print(f"  {component}: {data['score']}/{data['max']} - {data['explanation']}")

