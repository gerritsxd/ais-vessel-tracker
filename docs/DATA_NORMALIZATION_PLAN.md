# Data Normalization Plan: DWT & GT for All Vessels

## Problem Statement

**Current State:**
- **WASP vessels (84)**: Have DWT and GT from `wind_propulsion_mmsi` table (100% coverage)
- **Regular vessels (12,896)**: Missing DWT and GT (0% coverage)
- **MRV vessels (5,103)**: Have GT from `eu_mrv_emissions.gross_tonnage` (37% coverage, EU only)

**Goal:**
Normalize data so ALL vessels have the same fields: DWT and GT, regardless of WASP status.

---

## Solution Architecture

### Phase 1: Database Schema Updates

#### 1.1 Add DWT/GT Columns to `vessels_static` Table

```sql
-- Add columns if they don't exist
ALTER TABLE vessels_static 
ADD COLUMN dwt INTEGER DEFAULT NULL;

ALTER TABLE vessels_static 
ADD COLUMN gt INTEGER DEFAULT NULL;

-- Add metadata columns
ALTER TABLE vessels_static 
ADD COLUMN dwt_source TEXT DEFAULT NULL;  -- 'wasp', 'mrv', 'scraped', 'predicted'
ADD COLUMN gt_source TEXT DEFAULT NULL;   -- 'wasp', 'mrv', 'scraped', 'predicted'
ADD COLUMN dwt_updated_at TIMESTAMP DEFAULT NULL;
ADD COLUMN gt_updated_at TIMESTAMP DEFAULT NULL;
```

#### 1.2 Create Normalization Tracking Table

```sql
CREATE TABLE IF NOT EXISTS vessel_normalization_status (
    mmsi INTEGER PRIMARY KEY,
    has_dwt BOOLEAN DEFAULT 0,
    has_gt BOOLEAN DEFAULT 0,
    dwt_attempts INTEGER DEFAULT 0,
    gt_attempts INTEGER DEFAULT 0,
    last_dwt_attempt TIMESTAMP,
    last_gt_attempt TIMESTAMP,
    dwt_source TEXT,
    gt_source TEXT,
    FOREIGN KEY (mmsi) REFERENCES vessels_static(mmsi)
);
```

---

### Phase 2: Data Population Strategy

#### 2.1 Priority Order for DWT/GT Population

1. **WASP Vessels** (84 vessels) - Copy from `wind_propulsion_mmsi`
2. **MRV Vessels** (5,103 vessels) - Copy GT from `eu_mrv_emissions`
3. **Scraping** - Use existing GT scrapers + new DWT scrapers
4. **ML Prediction** - Predict DWT/GT based on length/beam/ship_type patterns

#### 2.2 Data Sources Priority

**For GT (Gross Tonnage):**
1. ✅ `wind_propulsion_mmsi.gt` (84 WASP vessels)
2. ✅ `eu_mrv_emissions.gross_tonnage` (5,103 MRV vessels)
3. 🔄 MarineTraffic scraping (existing `gt_scraper.py`)
4. 🔄 VesselFinder scraping (existing `gt_scraper.py`)
5. 🤖 ML prediction (based on length/beam/ship_type)

**For DWT (Deadweight Tonnage):**
1. ✅ `wind_propulsion_mmsi.dwt` (84 WASP vessels)
2. 🔄 MarineTraffic scraping (NEW - need to add)
3. 🔄 VesselFinder scraping (NEW - need to add)
4. 🔄 Other maritime databases (Equasis, IHS, etc.)
5. 🤖 ML prediction (based on length/beam/ship_type/GT)

---

### Phase 3: Implementation Steps

#### Step 1: Copy Existing Data

**Copy WASP DWT/GT to vessels_static:**
```sql
UPDATE vessels_static v
SET 
    dwt = (SELECT dwt FROM wind_propulsion_mmsi w WHERE w.mmsi = v.mmsi),
    gt = (SELECT gt FROM wind_propulsion_mmsi w WHERE w.mmsi = v.mmsi),
    dwt_source = 'wasp',
    gt_source = 'wasp',
    dwt_updated_at = datetime('now'),
    gt_updated_at = datetime('now')
WHERE EXISTS (
    SELECT 1 FROM wind_propulsion_mmsi w WHERE w.mmsi = v.mmsi
);
```

**Copy MRV GT to vessels_static:**
```sql
UPDATE vessels_static v
SET 
    gt = CAST(e.gross_tonnage AS INTEGER),
    gt_source = 'mrv',
    gt_updated_at = datetime('now')
FROM eu_mrv_emissions e
WHERE v.imo = e.imo 
  AND e.gross_tonnage IS NOT NULL
  AND v.gt IS NULL;  -- Only update if not already set
```

#### Step 2: Enhance GT Scraper for All Vessels

**Modify existing `gt_scraper.py` to:**
- Update `vessels_static.gt` instead of just `eu_mrv_emissions.gross_tonnage`
- Work with MMSI (not just IMO)
- Handle both WASP and non-WASP vessels

#### Step 3: Create DWT Scraper

**New file: `src/services/dwt_scraper.py`**
- Similar structure to `gt_scraper.py`
- Scrapes DWT from MarineTraffic, VesselFinder
- Updates `vessels_static.dwt`
- Rate limiting: 10 requests/minute
- Batch processing: 100 vessels/day

#### Step 4: Create ML Prediction Models

**New file: `src/ml/dwt_gt_predictor.py`**

**DWT Prediction Model:**
- Train on WASP vessels (84 samples with known DWT)
- Features: length, beam, ship_type, gt (if available)
- Model: Random Forest or Gradient Boosting
- Predict DWT for vessels missing it

**GT Prediction Model:**
- Train on WASP + MRV vessels (~5,187 samples)
- Features: length, beam, ship_type
- Model: Random Forest or Gradient Boosting
- Predict GT for vessels missing it

**Prediction Formula (Simple Linear Regression):**
```python
# Based on WASP vessel patterns
def predict_dwt(length, beam, ship_type):
    # Bulk Carrier: dwt ≈ length * beam * 50
    # General Cargo: dwt ≈ length * beam * 8
    # Tanker: dwt ≈ length * beam * 45
    # Ro-Ro: dwt ≈ length * beam * 12
    
    coefficients = {
        70: 50,  # Cargo (Bulk)
        80: 45,  # Tanker
        79: 12,  # Other
        72: 12,  # Cargo (Ro-Ro)
    }
    
    base_coeff = coefficients.get(ship_type, 20)
    predicted_dwt = length * beam * base_coeff
    
    return int(predicted_dwt)

def predict_gt(length, beam, ship_type):
    # GT ≈ DWT * 0.6 (approximate relationship)
    # Or use length/beam ratio
    predicted_gt = length * beam * 0.4
    return int(predicted_gt)
```

#### Step 5: Normalization Service

**New file: `src/services/vessel_normalizer.py`**

**Daily normalization process:**
1. Identify vessels missing DWT/GT
2. Try scraping first (for high-value vessels)
3. Fall back to ML prediction (for remaining vessels)
4. Update normalization tracking table
5. Generate normalization report

---

### Phase 4: Data Quality & Validation

#### 4.1 Validation Rules

**DWT Validation:**
- DWT should be > 0
- DWT should be > GT (typically)
- DWT should correlate with length/beam
- Flag outliers for manual review

**GT Validation:**
- GT should be > 0
- GT should correlate with length/beam
- Compare predicted vs scraped values
- Flag discrepancies > 20%

#### 4.2 Quality Metrics

```sql
-- Coverage metrics
SELECT 
    COUNT(*) as total_vessels,
    COUNT(dwt) as vessels_with_dwt,
    COUNT(gt) as vessels_with_gt,
    COUNT(CASE WHEN dwt IS NOT NULL AND gt IS NOT NULL THEN 1 END) as vessels_with_both,
    ROUND(100.0 * COUNT(dwt) / COUNT(*), 2) as dwt_coverage_pct,
    ROUND(100.0 * COUNT(gt) / COUNT(*), 2) as gt_coverage_pct
FROM vessels_static;

-- Source distribution
SELECT 
    dwt_source,
    COUNT(*) as count
FROM vessels_static
WHERE dwt IS NOT NULL
GROUP BY dwt_source;

SELECT 
    gt_source,
    COUNT(*) as count
FROM vessels_static
WHERE gt IS NOT NULL
GROUP BY gt_source;
```

---

### Phase 5: Integration with Existing Systems

#### 5.1 Update Fit Score Calculation

**Modify fit score to use normalized DWT/GT:**
- Use `vessels_static.dwt` and `vessels_static.gt` for all vessels
- No longer need separate logic for WASP vs non-WASP
- Can use DWT/GT in scoring formula

#### 5.2 Update API Endpoints

**Update `web_tracker.py` endpoints:**
- Include `dwt` and `gt` in vessel responses
- Add `dwt_source` and `gt_source` for transparency
- Filter by DWT/GT ranges

#### 5.3 Update Frontend

**Update UI to show:**
- DWT and GT for all vessels
- Data source indicators (scraped, predicted, etc.)
- Normalization status dashboard

---

## Implementation Priority

### Week 1: Foundation
1. ✅ Database schema updates
2. ✅ Copy WASP data to vessels_static
3. ✅ Copy MRV GT data to vessels_static
4. ✅ Create normalization tracking table

### Week 2: Scraping
1. ✅ Enhance GT scraper for all vessels
2. ✅ Create DWT scraper
3. ✅ Set up daily scraping jobs
4. ✅ Monitor scraping success rates

### Week 3: ML Prediction
1. ✅ Analyze WASP vessel patterns
2. ✅ Train DWT prediction model
3. ✅ Train GT prediction model
4. ✅ Predict DWT/GT for remaining vessels

### Week 4: Integration & Validation
1. ✅ Update fit score calculation
2. ✅ Update API endpoints
3. ✅ Update frontend
4. ✅ Generate normalization report
5. ✅ Validate data quality

---

## Expected Results

**After normalization:**
- **DWT Coverage**: 100% (via WASP + scraping + prediction)
- **GT Coverage**: 100% (via WASP + MRV + scraping + prediction)
- **Data Consistency**: All vessels have same fields
- **Fit Score**: Can use DWT/GT for all vessels

**Coverage Breakdown (estimated):**
- WASP source: 84 vessels (0.65%)
- MRV source: 5,103 vessels (39.5%)
- Scraped: ~3,000 vessels (23.3%)
- Predicted: ~4,709 vessels (36.5%)

---

## Files to Create/Modify

### New Files:
1. `src/services/dwt_scraper.py` - DWT scraping service
2. `src/ml/dwt_gt_predictor.py` - ML prediction models
3. `src/services/vessel_normalizer.py` - Normalization orchestrator
4. `src/utils/normalize_vessel_data.py` - One-time normalization script
5. `config/systemd/ais-dwt-scraper.service` - DWT scraper systemd service
6. `config/systemd/ais-vessel-normalizer.service` - Normalizer systemd service

### Modified Files:
1. `src/services/gt_scraper.py` - Update to write to vessels_static
2. `src/services/web_tracker.py` - Include DWT/GT in API responses
3. `src/ml/predictor.py` - Use normalized DWT/GT for fit scores
4. Database migration scripts

---

## Next Steps

1. Review and approve this plan
2. Create database migration script
3. Implement Phase 1 (schema updates)
4. Implement Phase 2 (data population)
5. Test with sample vessels
6. Deploy to production

