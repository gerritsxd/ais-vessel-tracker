"""
Wind Alignment Analyzer

Analyzes vessel course alignment with wind direction.
Calculates statistics on how often vessels travel with favorable winds.
"""

import math
from typing import List, Dict, Optional


class WindAlignmentAnalyzer:
    """
    Analyzes how well vessel courses align with wind direction.
    
    Calculates:
    - Angle between vessel course (COG) and wind direction
    - Percentage of time traveling with favorable winds
    - Average wind alignment score
    - Wind assistance potential
    """
    
    @staticmethod
    def calculate_alignment_angle(cog: float, wind_direction: float) -> float:
        """
        Calculate angle between vessel course and wind direction.
        
        Args:
            cog: Course over ground (degrees, 0-360)
            wind_direction: Wind direction (degrees, 0-360, direction wind is FROM)
        
        Returns:
            Angle difference (degrees, 0-180)
            - 0° = traveling directly with wind (best)
            - 90° = traveling perpendicular to wind
            - 180° = traveling directly against wind (worst)
        """
        # Normalize angles to 0-360
        cog = cog % 360
        wind_direction = wind_direction % 360
        
        # Calculate absolute difference
        diff = abs(cog - wind_direction)
        
        # Take smaller angle (wind can be from either side)
        if diff > 180:
            diff = 360 - diff
        
        return diff
    
    @staticmethod
    def is_favorable_wind(alignment_angle: float, threshold: float = 45.0) -> bool:
        """
        Determine if wind alignment is favorable for wind propulsion.
        
        Args:
            alignment_angle: Angle between COG and wind direction (degrees)
            threshold: Maximum angle for favorable wind (default 45°)
        
        Returns:
            True if wind is favorable (vessel traveling with wind)
        """
        return alignment_angle <= threshold
    
    @staticmethod
    def calculate_wind_assistance_score(alignment_angle: float) -> float:
        """
        Calculate wind assistance score (0-100).
        
        Args:
            alignment_angle: Angle between COG and wind direction (degrees)
        
        Returns:
            Score from 0-100:
            - 100 = traveling directly with wind
            - 50 = traveling perpendicular
            - 0 = traveling directly against wind
        """
        # Normalize to 0-180 range
        angle = min(alignment_angle, 180)
        
        # Linear scale: 0° = 100, 180° = 0
        score = 100 * (1 - (angle / 180))
        
        return max(0, min(100, score))
    
    @staticmethod
    def analyze_vessel_alignment(matched_records: List[Dict]) -> Dict:
        """
        Analyze wind alignment for a vessel.
        
        Args:
            matched_records: List of position-wind matched records
        
        Returns:
            Analysis results: {
                'total_positions': int,
                'matched_positions': int,
                'favorable_wind_count': int,
                'favorable_wind_percentage': float,
                'average_alignment_angle': float,
                'average_wind_assistance_score': float,
                'average_wind_speed': float,
                'max_wind_speed': float,
                'wind_assistance_potential': str  # 'high', 'medium', 'low'
            }
        """
        if not matched_records:
            return {
                'total_positions': 0,
                'matched_positions': 0,
                'favorable_wind_count': 0,
                'favorable_wind_percentage': 0.0,
                'average_alignment_angle': None,
                'average_wind_assistance_score': 0.0,
                'average_wind_speed': 0.0,
                'max_wind_speed': 0.0,
                'wind_assistance_potential': 'unknown'
            }
        
        total = len(matched_records)
        matched = [r for r in matched_records if r.get('matched') and r.get('wind_direction') is not None]
        matched_count = len(matched)
        
        if matched_count == 0:
            return {
                'total_positions': total,
                'matched_positions': 0,
                'favorable_wind_count': 0,
                'favorable_wind_percentage': 0.0,
                'average_alignment_angle': None,
                'average_wind_assistance_score': 0.0,
                'average_wind_speed': 0.0,
                'max_wind_speed': 0.0,
                'wind_assistance_potential': 'unknown'
            }
        
        # Calculate alignment angles and scores
        alignment_angles = []
        wind_assistance_scores = []
        wind_speeds = []
        favorable_count = 0
        
        for record in matched:
            cog = record['cog']
            wind_dir = record['wind_direction']
            
            if cog is None or wind_dir is None:
                continue
            
            angle = WindAlignmentAnalyzer.calculate_alignment_angle(cog, wind_dir)
            alignment_angles.append(angle)
            
            score = WindAlignmentAnalyzer.calculate_wind_assistance_score(angle)
            wind_assistance_scores.append(score)
            
            if WindAlignmentAnalyzer.is_favorable_wind(angle):
                favorable_count += 1
            
            if record.get('wind_speed'):
                wind_speeds.append(record['wind_speed'])
        
        # Calculate statistics
        avg_alignment = sum(alignment_angles) / len(alignment_angles) if alignment_angles else None
        avg_score = sum(wind_assistance_scores) / len(wind_assistance_scores) if wind_assistance_scores else 0.0
        avg_wind_speed = sum(wind_speeds) / len(wind_speeds) if wind_speeds else 0.0
        max_wind_speed = max(wind_speeds) if wind_speeds else 0.0
        
        favorable_percentage = (favorable_count / matched_count * 100) if matched_count > 0 else 0.0
        
        # Determine wind assistance potential
        if favorable_percentage >= 50 and avg_score >= 60:
            potential = 'high'
        elif favorable_percentage >= 30 and avg_score >= 40:
            potential = 'medium'
        elif favorable_percentage > 0:
            potential = 'low'
        else:
            potential = 'none'
        
        return {
            'total_positions': total,
            'matched_positions': matched_count,
            'favorable_wind_count': favorable_count,
            'favorable_wind_percentage': round(favorable_percentage, 2),
            'average_alignment_angle': round(avg_alignment, 2) if avg_alignment else None,
            'average_wind_assistance_score': round(avg_score, 2),
            'average_wind_speed': round(avg_wind_speed, 2),
            'max_wind_speed': round(max_wind_speed, 2),
            'wind_assistance_potential': potential
        }

