#!/usr/bin/env python3
"""
Company Intelligence Scraper V3 - Gemini-Powered
Uses free Google Gemini API with web search capability
Zero cost, 1,500 requests/day free tier
"""

import google.generativeai as genai
import json
import time
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class GeminiIntelligenceScraper:
    """Use Gemini AI to research companies (FREE!)"""
    
    def __init__(self, api_key: str, verbose: bool = False):
        """Initialize Gemini scraper with API key"""
        genai.configure(api_key=api_key)
        # Use gemini-2.0-flash (stable, fast, free tier)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.verbose = verbose
        self.intelligence_data = {}
    
    def get_companies_from_db(self):
        """Get companies ordered by fleet size"""
        conn = sqlite3.connect('data/vessel_static_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                company_name,
                COUNT(*) as vessel_count,
                AVG(total_co2_emissions) as avg_emissions,
                AVG(avg_co2_per_distance) as avg_co2_distance
            FROM eu_mrv_emissions 
            WHERE company_name IS NOT NULL 
              AND company_name != "" 
            GROUP BY company_name 
            ORDER BY vessel_count DESC, company_name
        ''')
        
        companies = []
        for row in cursor.fetchall():
            companies.append({
                'name': row[0],
                'vessel_count': row[1],
                'avg_emissions': row[2],
                'avg_co2_distance': row[3]
            })
        
        conn.close()
        return companies
    
    def gather_intelligence(self, company_meta: Dict) -> Dict[str, Any]:
        """Use Gemini to research company intelligence"""
        company_name = company_meta['name']
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"🤖 Gemini researching: {company_name} (Fleet: {company_meta['vessel_count']} vessels)")
            print(f"{'='*80}")
        
        prompt = f"""
Research the shipping company "{company_name}" and find information in these 5 categories:

1. **Grants & Subsidies**: Government funding, EU grants, green shipping subsidies, retrofit funding
2. **Legal Violations**: Environmental fines, lawsuits, regulatory violations, penalties
3. **Sustainability News**: Wind propulsion, green technology, retrofit initiatives, decarbonization
4. **Reputation**: Sustainability ratings, environmental performance scores, rankings, certifications
5. **Financial Pressure**: Carbon tax exposure, EU ETS costs, compliance costs, regulatory burden

For EACH finding you discover, provide:
- title: Brief headline (max 100 chars)
- snippet: 2-3 sentence description
- url: Source URL (must be real and accessible)
- date: Publication date in YYYY-MM-DD format if available, otherwise "unknown"
- source: Source type (e.g., "maritime_news", "government", "legal", "rating_agency")

CRITICAL: Return ONLY valid JSON in this exact format (no markdown, no code blocks, just raw JSON):
{{
  "grants_subsidies": [
    {{"title": "...", "snippet": "...", "url": "https://...", "date": "2024-01-15", "source": "government"}}
  ],
  "legal_violations": [],
  "sustainability_news": [],
  "reputation": [],
  "financial_pressure": []
}}

Rules:
- If no findings for a category, use empty array: []
- Focus on recent news (last 3 years: 2022-2025)
- Only include verifiable information with real source URLs
- Max 3 findings per category
- Prioritize maritime industry sources: Lloyd's List, TradeWinds, Splash247, Maritime Executive
"""
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if self.verbose:
                print(f"  📡 Gemini response received ({len(result_text)} chars)")
            
            # Clean up response - remove markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            intelligence = json.loads(result_text)
            
            # Validate structure
            expected_categories = ['grants_subsidies', 'legal_violations', 'sustainability_news', 'reputation', 'financial_pressure']
            for cat in expected_categories:
                if cat not in intelligence:
                    intelligence[cat] = []
            
            # Build final data structure
            full_data = {
                'company_name': company_name,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'vessel_count': company_meta['vessel_count'],
                    'avg_emissions': round(company_meta['avg_emissions'], 2) if company_meta['avg_emissions'] else None,
                    'avg_co2_distance': round(company_meta['avg_co2_distance'], 2) if company_meta['avg_co2_distance'] else None
                },
                'intelligence': {}
            }
            
            # Format findings with counts
            total_findings = 0
            for category, findings in intelligence.items():
                if category in expected_categories:
                    full_data['intelligence'][category] = {
                        'results_count': len(findings),
                        'findings': findings
                    }
                    total_findings += len(findings)
                    
                    if self.verbose:
                        print(f"  ✓ {category.replace('_', ' ').title()}: {len(findings)} findings")
            
            if self.verbose:
                print(f"  📊 Total findings: {total_findings}")
            
            return full_data
            
        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"  ❌ JSON parse error: {e}")
                print(f"  Raw response: {result_text[:200]}...")
            return self._create_empty_intelligence(company_name, company_meta, f"JSON parse error: {str(e)}")
            
        except Exception as e:
            if self.verbose:
                print(f"  ❌ Error: {e}")
            return self._create_empty_intelligence(company_name, company_meta, str(e))
    
    def _create_empty_intelligence(self, company_name: str, company_meta: Dict, error_msg: str) -> Dict:
        """Create empty intelligence structure with error"""
        return {
            'company_name': company_name,
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'vessel_count': company_meta['vessel_count'],
                'avg_emissions': round(company_meta['avg_emissions'], 2) if company_meta['avg_emissions'] else None,
                'avg_co2_distance': round(company_meta['avg_co2_distance'], 2) if company_meta['avg_co2_distance'] else None
            },
            'intelligence': {
                'grants_subsidies': {'results_count': 0, 'findings': []},
                'legal_violations': {'results_count': 0, 'findings': []},
                'sustainability_news': {'results_count': 0, 'findings': []},
                'reputation': {'results_count': 0, 'findings': []},
                'financial_pressure': {'results_count': 0, 'findings': []}
            },
            'error': error_msg
        }
    
    def scrape_batch(self, max_companies: int = 30, start_from: int = 0):
        """Scrape intelligence using Gemini (30 companies = fits in free tier)"""
        companies = self.get_companies_from_db()
        
        print(f"\n{'='*80}")
        print(f"🤖 GEMINI INTELLIGENCE SCRAPER (FREE TIER)")
        print(f"{'='*80}")
        print(f"📋 Total companies in DB: {len(companies)}")
        print(f"📌 Batch size: {max_companies} companies (Free tier: 1,500/day)")
        print(f"⏳ Rate limit: ~2 requests/minute (30s delay)")
        print(f"{'='*80}\n")
        
        if start_from > 0:
            companies = companies[start_from:]
            print(f"⏭️  Starting from #{start_from + 1}")
        
        companies = companies[:max_companies]
        
        for i, company in enumerate(companies, start_from + 1):
            try:
                print(f"\n[{i}/{start_from + len(companies)}]", end=" ")
                
                intelligence = self.gather_intelligence(company)
                self.intelligence_data[company['name']] = intelligence
                
                # Save progress every 5 companies
                if i % 5 == 0:
                    self.save_results(progress=True)
                    if self.verbose:
                        print(f"\n💾 Progress saved at {i} companies")
                
                # Rate limiting: 30 seconds between requests (2 per minute)
                # This keeps us well under the 1,500/day limit
                if i < start_from + len(companies):
                    if self.verbose:
                        print(f"  ⏳ Waiting 30s (rate limit)...")
                    time.sleep(30)
                    
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Interrupted. Saving progress...")
                self.save_results(progress=True)
                break
            except Exception as e:
                print(f"\n❌ Failed {company['name']}: {e}")
                continue
        
        self.save_results(progress=False)
    
    def save_results(self, progress: bool = False):
        """Save intelligence data to JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if progress:
            filename = 'data/company_intelligence_gemini_progress.json'
        else:
            filename = f'data/company_intelligence_gemini_{timestamp}.json'
        
        output_file = Path(filename)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'companies': self.intelligence_data,
                'total': len(self.intelligence_data),
                'timestamp': datetime.now().isoformat(),
                'version': 'gemini-v3-free',
                'model': 'gemini-2.0-flash',
                'categories': ['grants_subsidies', 'legal_violations', 'sustainability_news', 'reputation', 'financial_pressure']
            }, f, indent=2, ensure_ascii=False)
        
        if not progress:
            # Calculate stats
            total_findings = 0
            companies_with_findings = 0
            
            for company_data in self.intelligence_data.values():
                company_findings = sum(
                    cat.get('results_count', 0) 
                    for cat in company_data.get('intelligence', {}).values()
                )
                total_findings += company_findings
                if company_findings > 0:
                    companies_with_findings += 1
            
            print(f"\n{'='*80}")
            print(f"✅ INTELLIGENCE DATA SAVED:")
            print(f"  📄 File: {output_file}")
            print(f"  📊 Companies: {len(self.intelligence_data)}")
            print(f"  🔍 Total findings: {total_findings}")
            
            if len(self.intelligence_data) > 0:
                print(f"  📊 Avg per company: {total_findings/len(self.intelligence_data):.1f}")
                print(f"  ✨ Companies with findings: {companies_with_findings}")
            
            print(f"{'='*80}\n")


if __name__ == '__main__':
    import sys
    
    # Get API key from command line or config file
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        # Try to load from config file
        config_path = Path(__file__).parent.parent.parent / 'config' / 'gemini_api_key.txt'
        if config_path.exists():
            api_key = config_path.read_text().strip()
        else:
            print("❌ No API key provided!")
            print("Usage: python company_intelligence_scraper_gemini.py YOUR_API_KEY")
            print("Or create: config/gemini_api_key.txt")
            sys.exit(1)
    
    scraper = GeminiIntelligenceScraper(api_key=api_key, verbose=True)
    scraper.scrape_batch(max_companies=30)
