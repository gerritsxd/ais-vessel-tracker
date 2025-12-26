# Wind Alignment Analysis

## Overview

This module analyzes historical vessel positions against wind data to identify vessels that travel more often with favorable wind conditions. This helps identify candidates for wind propulsion systems.

## Architecture

### Components

1. **WindDataFetcher** (`wind_data_fetcher.py`)
   - Fetches historical wind data from weather APIs
   - Supports Open-Meteo (free) and OpenWeatherMap (paid)
   - Implements caching to reduce API calls
   - Rate limiting to respect API limits

2. **WindPositionMatcher** (`wind_position_matcher.py`)
   - Matches vessel positions with wind data
   - Handles time and location matching
   - Processes multiple vessels efficiently

3. **WindAlignmentAnalyzer** (`wind_alignment_analyzer.py`)
   - Calculates angle between vessel course (COG) and wind direction
   - Determines favorable wind conditions
   - Computes wind assistance scores (0-100)
   - Analyzes alignment statistics

4. **WindAnalysisService** (`wind_analysis_service.py`)
   - Main orchestrator
   - Coordinates data fetching, matching, and analysis
   - Stores results in database
   - Provides query interface

## Database Schema

### `vessel_wind_alignment` Table

```sql
CREATE TABLE vessel_wind_alignment (
    mmsi INTEGER PRIMARY KEY,
    total_positions INTEGER DEFAULT 0,
    matched_positions INTEGER DEFAULT 0,
    favorable_wind_count INTEGER DEFAULT 0,
    favorable_wind_percentage REAL DEFAULT 0.0,
    average_alignment_angle REAL,
    average_wind_assistance_score REAL DEFAULT 0.0,
    average_wind_speed REAL DEFAULT 0.0,
    max_wind_speed REAL DEFAULT 0.0,
    wind_assistance_potential TEXT DEFAULT 'unknown',
    last_analyzed TEXT,
    FOREIGN KEY (mmsi) REFERENCES vessels_static(mmsi)
)
```

## Usage

### Analyze Single Vessel

```bash
python src/utils/run_wind_analysis.py <MMSI>
```

Example:
```bash
python src/utils/run_wind_analysis.py 211281610
```

### Analyze All Vessels

```bash
python src/utils/run_wind_analysis.py --all [LIMIT]
```

Example:
```bash
python src/utils/run_wind_analysis.py --all 10  # Analyze first 10 vessels
python src/utils/run_wind_analysis.py --all     # Analyze all vessels
```

### Python API

```python
from pathlib import Path
from src.services.wind_analysis import WindAnalysisService

db_path = Path("data/vessel_static_data.db")
service = WindAnalysisService(db_path=db_path, verbose=True)

# Analyze single vessel
results = service.analyze_vessel(mmsi=211281610)

# Analyze multiple vessels
results = service.analyze_multiple_vessels([211281610, 219018448])

# Get stored results
vessel_data = service.get_vessel_results(mmsi=211281610)

# Get top vessels by potential
top_vessels = service.get_top_vessels_by_potential(limit=50)
```

## API Endpoints

### Get Wind Alignment for Vessel

```
GET /ships/api/wind-alignment/<MMSI>
```

Returns analysis results for a specific vessel.

### Get Top Wind Alignment Vessels

```
GET /ships/api/wind-alignment/top?limit=100
```

Returns vessels with highest wind assistance potential, sorted by score.

## Analysis Metrics

### Alignment Angle

Angle between vessel course (COG) and wind direction:
- **0°**: Traveling directly with wind (best)
- **45°**: Favorable wind (good for wind propulsion)
- **90°**: Perpendicular to wind
- **180°**: Traveling directly against wind (worst)

### Wind Assistance Score

Score from 0-100:
- **80-100**: Excellent wind alignment
- **60-79**: Good wind alignment
- **40-59**: Moderate wind alignment
- **0-39**: Poor wind alignment

### Wind Assistance Potential

Categorical assessment:
- **high**: ≥50% favorable wind, score ≥60
- **medium**: ≥30% favorable wind, score ≥40
- **low**: Some favorable wind
- **none**: No favorable wind detected

## Wind Data Sources

### Open-Meteo (Default)

- **Free**: No API key required
- **Historical data**: Available
- **Rate limit**: Generous
- **Coverage**: Global

### OpenWeatherMap (Optional)

- **Requires**: API key
- **Historical data**: Paid plan required
- **Rate limit**: Varies by plan
- **Coverage**: Global

## Caching

Wind data is cached locally to:
- Reduce API calls
- Improve performance
- Handle offline scenarios

Cache location: `data/wind_cache/`

Cache files are organized by:
- Location (rounded to 0.1°)
- Date
- Hour

## Performance Considerations

- **Batch processing**: Processes multiple vessels efficiently
- **Rate limiting**: Respects API limits
- **Caching**: Reduces redundant API calls
- **Database indexing**: Fast queries on results

## Future Enhancements

- [ ] Support for more weather APIs
- [ ] Real-time wind data integration
- [ ] Route optimization suggestions
- [ ] Wind propulsion ROI calculations
- [ ] Visualization of wind alignment patterns

