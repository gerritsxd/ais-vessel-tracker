"""
Wind Analysis Module

Analyzes historical vessel positions against wind data to identify
vessels that travel more often with favorable wind conditions.
"""

from .wind_data_fetcher import WindDataFetcher
from .wind_position_matcher import WindPositionMatcher
from .wind_alignment_analyzer import WindAlignmentAnalyzer
from .wind_analysis_service import WindAnalysisService

__all__ = [
    'WindDataFetcher',
    'WindPositionMatcher',
    'WindAlignmentAnalyzer',
    'WindAnalysisService',
]

