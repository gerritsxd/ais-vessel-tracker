# 📊 Scraping System Summary (For Video Production)

## Quick Overview

**What**: AI-powered system that automatically researches shipping companies across the internet

**How**: Uses Google Gemini AI to search and extract structured intelligence

**Why**: Predict which companies will adopt wind propulsion technology (WASP)

**Output**: Structured JSON data with 5 categories of intelligence per company

---

## The Two Scrapers

### 1. **Company Intelligence Scraper** (Gemini-Powered)
**Purpose**: Research companies from external sources (news, government, legal)

**Technology**: Google Gemini 2.0 Flash (free tier - 1,500 requests/day)

**Process**:
1. Gets company list from database (ordered by fleet size)
2. For each company, sends structured prompt to Gemini AI
3. Gemini searches web and returns JSON with findings
4. Extracts 5 categories of intelligence
5. Saves to `company_intelligence_gemini_*.json`

**Data Collected** (5 categories):
- 💰 **Grants & Subsidies**: Government funding, EU grants, green shipping subsidies
- ⚖️ **Legal Violations**: Environmental fines, lawsuits, regulatory violations
- 🌱 **Sustainability News**: Wind propulsion projects, green tech adoption
- 🏆 **Reputation**: Sustainability ratings, industry rankings
- 💸 **Financial Pressure**: Carbon tax exposure, EU ETS costs

**Each Finding Contains**:
- Title (headline)
- Snippet (2-3 sentence description)
- URL (source link)
- Date (publication date)
- Source type (government, maritime_news, legal, etc.)

---

### 2. **Company Profiler** (Web Scraper)
**Purpose**: Extract structured data from company websites and Wikipedia

**Technology**: BeautifulSoup, requests, Playwright

**Process**:
1. Gets company list from database
2. Searches for company website and Wikipedia page
3. Scrapes key pages (home, about, services)
4. Extracts structured attributes (vessel count, emissions, ship types)
5. Classifies company type (container_carrier, tanker_operator, etc.)
6. Removes boilerplate text (marketing fluff)
7. Saves to `company_profiles_v3_structured_*.json`

**Data Collected**:
- **Structured Attributes**: Vessel count, emissions, WASP fit scores
- **Labels**: Company type, fleet size category, emissions category
- **Text Data**: Cleaned website content, Wikipedia summaries

---

## The Flow

```
┌─────────────────┐
│  Database       │
│  (Companies)    │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│ Intelligence    │  │ Company Profiler│
│ Scraper         │  │ (Web Scraper)   │
│ (Gemini AI)     │  │                 │
└────────┬────────┘  └────────┬────────┘
         │                     │
         │ Searches web        │ Scrapes websites
         │ (news, gov, legal)  │ (home, about, etc.)
         │                     │
         ▼                     ▼
┌─────────────────┐  ┌─────────────────┐
│ Intelligence    │  │ Profile Data     │
│ JSON            │  │ JSON            │
│ (5 categories)  │  │ (structured)    │
└────────┬────────┘  └────────┬────────┘
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
         ┌──────────────────┐
         │  ML Predictor    │
         │  (Sentiment +    │
         │   Classification)│
         └──────────┬───────┘
                    │
                    ▼
         ┌──────────────────┐
         │  Predictions     │
         │  (WASP adoption  │
         │   probability)   │
         └──────────────────┘
```

---

## Key Features

### Intelligence Scraper:
- ✅ **AI-Powered**: Uses Gemini for intelligent web research
- ✅ **Free**: 1,500 requests/day on free tier
- ✅ **Structured**: Returns clean JSON (not raw HTML)
- ✅ **Targeted**: 5 specific categories relevant to WASP adoption
- ✅ **Automated**: Runs continuously, processes companies in batches
- ✅ **Rate Limited**: 30 seconds between requests (respectful scraping)

### Company Profiler:
- ✅ **Structured Data**: Extracts attributes directly (no parsing needed)
- ✅ **ML-Ready**: Includes labels for supervised learning
- ✅ **Clean Text**: Removes boilerplate, deduplicates content
- ✅ **Source Separation**: Wikipedia vs. website content separated
- ✅ **Fast**: 30-45 seconds per company (vs. 1-2 min in V2)

---

## Example Output

### Intelligence Data:
```json
{
  "Maersk A/S": {
    "intelligence": {
      "grants_subsidies": {
        "results_count": 1,
        "findings": [
          {
            "title": "Maersk secures Danish funding for green methanol project",
            "snippet": "Maersk's project to establish green methanol production...",
            "url": "https://...",
            "date": "2023-04-11",
            "source": "maritime_news"
          }
        ]
      },
      "sustainability_news": {
        "results_count": 2,
        "findings": [...]
      }
    }
  }
}
```

### Profile Data:
```json
{
  "Maersk A/S": {
    "attributes": {
      "vessel_count": 146,
      "avg_emissions_tons": 40835.07,
      "avg_wasp_fit_score": 1.78
    },
    "labels": {
      "company_categories": ["container_carrier"],
      "fleet_size_category": "large"
    }
  }
}
```

---

## Why This Matters

1. **Predictive Intelligence**: Not just current data, but signals that predict future behavior
2. **Automated Research**: No manual research needed - AI does it all
3. **Structured Output**: Ready for machine learning models
4. **Scalable**: Can process hundreds of companies automatically
5. **Free**: Uses free AI tier (Gemini) - no API costs
6. **Actionable**: Directly feeds into sales targeting and ML predictions

---

## Technical Stack

- **Python 3.13+**
- **Google Gemini AI** (generativeai library)
- **BeautifulSoup4** (HTML parsing)
- **Playwright** (browser automation)
- **SQLite** (database)
- **JSON** (data storage)

---

## Files

- `src/utils/company_intelligence_scraper_gemini.py` - Main intelligence scraper
- `src/utils/company_profiler_v3.py` - Company website profiler
- `src/services/intelligence_scraper_service_gemini.py` - Background service
- `data/company_intelligence_gemini_*.json` - Output files
- `data/company_profiles_v3_structured_*.json` - Profile output files

---

## For Video: Key Points to Emphasize

1. **AI Does the Research**: Not manual scraping - AI searches and extracts
2. **5 Categories**: Structured intelligence, not random data
3. **Predictive**: Helps predict future behavior (WASP adoption)
4. **Automated**: Runs 24/7, processes companies automatically
5. **Free**: Uses free AI tier - no costs
6. **Actionable**: Feeds directly into ML models for predictions

