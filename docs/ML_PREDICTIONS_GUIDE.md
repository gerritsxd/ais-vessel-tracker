# 🤖 ML Predictions Guide

## Overview

The ML Predictions system uses **Natural Language Processing (NLP)** and **Machine Learning** to predict company characteristics from intelligence data:

1. **WASP Adoption Prediction** - Binary classifier predicting if a company will adopt Wind-Assisted Propulsion
2. **Sustainability Focus Classification** - Multi-class classifier (high/medium/low)
3. **Company Type Classification** - Predicts company category (container_carrier, tanker_operator, etc.)

## Features

### Sentiment Analysis
- Analyzes text from intelligence findings and company profiles
- Extracts polarity (-1 to 1) and subjectivity scores
- Identifies positive/negative sentiment in sustainability news

### Feature Engineering
- **Structured Features**: Vessel count, emissions, WASP fit scores
- **Intelligence Features**: Counts per category (grants, violations, sustainability news, etc.)
- **NLP Features**: Sentiment scores, keyword detection (wind, grants, sustainability)
- **Text Features**: Combined text from all intelligence findings and company profiles

### ML Models
- **Gradient Boosting Classifier** for WASP adoption (binary)
- **Random Forest Classifier** for sustainability focus (multi-class)
- **Random Forest Classifier** for company type (multi-class)

## Setup

### 1. Install Dependencies

```bash
pip install scikit-learn textblob
```

Or install from requirements:
```bash
pip install -r config/requirements.txt
```

### 2. Prepare Data

You need:
- **Intelligence Data**: Run the intelligence scraper to generate `company_intelligence_gemini_*.json`
- **Profile Data**: Run the company profiler V3 to generate `company_profiles_v3_structured_*.json`
- **WASP Data**: Ensure wind propulsion data is imported (for ground truth labels)

### 3. Train Models

#### Option A: Via Web Interface
1. Navigate to `/ml-predictions` page
2. Click "🚀 Train Models" button
3. Wait for training to complete (may take a few minutes)

#### Option B: Via Python Script
```bash
python src/services/ml_predictor_service.py
```

#### Option C: Via Test Script
```bash
python scripts/test_ml_predictor.py
```

## Usage

### Web Interface

1. **View Predictions**: Navigate to `/ml-predictions` page
2. **Filter Companies**: 
   - All Companies
   - High WASP Probability
   - High Sustainability Focus
3. **Sort Results**: By WASP probability, sustainability level, or company name
4. **View Details**: Each row shows predictions with confidence scores

### API Endpoints

#### Get All Predictions
```bash
GET /ships/api/ml/predictions
```

Returns:
```json
{
  "predictions": {
    "Maersk A/S": {
      "wasp_adoption": {
        "prediction": true,
        "probability": 0.85,
        "confidence": "high"
      },
      "sustainability_focus": {
        "prediction": "high",
        "probability": 0.92,
        "confidence": "high"
      },
      "company_type": {
        "prediction": "container_carrier",
        "probability": 0.88,
        "confidence": "high"
      },
      "features": {
        "vessel_count": 146,
        "grants_count": 1,
        "sustainability_count": 2,
        "has_wind_keywords": true,
        "sentiment_polarity": 0.65
      }
    }
  },
  "total_companies": 50,
  "timestamp": "2025-11-17T12:00:00"
}
```

#### Get Company-Specific Prediction
```bash
GET /ships/api/ml/predictions/company/Maersk%20A%2FS
```

#### Train Models
```bash
POST /ships/api/ml/train
```

#### Get ML Statistics
```bash
GET /ships/api/ml/stats
```

## Model Training Details

### Data Requirements

- **Minimum for WASP Model**: At least 2 companies with WASP adoption (positive examples)
- **Minimum for Sustainability**: At least 2 different sustainability levels
- **Minimum for Company Type**: At least 2 different company types

### Feature Set

The models use these features:

1. **Vessel Metrics**:
   - `vessel_count`: Number of vessels
   - `avg_emissions`: Average CO2 emissions
   - `avg_co2_distance`: Average CO2 per distance
   - `avg_wasp_score`: Average WASP fit score

2. **Intelligence Counts**:
   - `grants_count`: Number of grant/subsidy findings
   - `violations_count`: Number of legal violation findings
   - `sustainability_count`: Number of sustainability news findings
   - `reputation_count`: Number of reputation findings
   - `financial_pressure_count`: Number of financial pressure findings
   - `total_findings`: Sum of all findings

3. **Sentiment Scores**:
   - `polarity`: Sentiment polarity (-1 to 1)
   - `subjectivity`: Subjectivity score (0 to 1)
   - `positive_score`: Positive sentiment score
   - `negative_score`: Negative sentiment score

4. **Keyword Features**:
   - `has_wind_keywords`: Boolean (wind propulsion keywords found)
   - `has_grant_keywords`: Boolean (grant/subsidy keywords found)
   - `has_sustainability_keywords`: Boolean (sustainability keywords found)

### Model Performance

Models are evaluated using:
- **Accuracy**: Overall classification accuracy
- **Classification Report**: Precision, recall, F1-score per class
- **Confidence Scores**: Probability-based confidence levels

## File Structure

```
data/
  ├── company_intelligence_gemini_*.json    # Intelligence data
  ├── company_profiles_v3_structured_*.json  # Profile data
  ├── ml_models.pkl                          # Trained models (saved)
  └── company_predictions.json               # Generated predictions

src/services/
  └── ml_predictor_service.py               # ML service implementation

frontend/src/pages/
  └── MLPredictions.jsx                     # React frontend page
```

## Troubleshooting

### "No predictions available"
- **Cause**: Models haven't been trained yet
- **Solution**: Click "Train Models" button or run training script

### "Insufficient data for training"
- **Cause**: Not enough companies with intelligence/profile data
- **Solution**: Run intelligence scraper and company profiler first

### "Models not trained"
- **Cause**: Training failed or no positive examples
- **Solution**: Check that you have:
  - At least 2 companies with WASP adoption (for WASP model)
  - Intelligence data with findings
  - Profile data with structured attributes

### Import Errors
- **Cause**: Missing dependencies
- **Solution**: 
  ```bash
  pip install scikit-learn textblob
  ```

## Next Steps

1. **Collect More Data**: More companies = better model performance
2. **Feature Engineering**: Add more features (e.g., financial data, fleet age)
3. **Model Tuning**: Adjust hyperparameters for better accuracy
4. **Ensemble Methods**: Combine multiple models for better predictions
5. **Real-time Updates**: Retrain models as new intelligence data arrives

## Example Workflow

```bash
# 1. Collect intelligence data
python src/utils/company_intelligence_scraper_gemini.py --max-companies 50

# 2. Collect profile data
python src/utils/company_profiler_v3.py --max-companies 50

# 3. Train ML models
python src/services/ml_predictor_service.py

# 4. View predictions in web interface
# Navigate to http://localhost:5000/ml-predictions
```

## Notes

- Models are saved to `data/ml_models.pkl` after training
- Predictions are cached in `data/company_predictions.json`
- Models use 80/20 train/test split
- Features are standardized (StandardScaler) before training
- Confidence levels: high (>70%), medium (50-70%), low (<50%)

