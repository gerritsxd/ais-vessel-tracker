#!/usr/bin/env python3
"""
Company Intelligence Scraper - Internet-Wide Data Gathering
Searches news, legal databases, government sites for predictive signals

Focus Areas:
1. Government grants/subsidies (Germany, EU, etc.)
2. Environmental lawsuits & violations
3. News coverage (sustainability initiatives)
4. Industry reputation & rankings
5. Financial pressure / regulatory compliance
"""

import sqlite3
import requests
import json
import time
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import random
from typing import Dict, List, Any

# Fix Windows console encoding
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Try importing search library
try:
    from googlesearch import search as google_search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    print("⚠️  googlesearch-python not installed. Install with: pip install googlesearch-python")


class CompanyIntelligenceScraper:
    """Scrape predictive intelligence from the internet (not company websites)"""
    
    # Intelligence search queries - highly targeted
    INTELLIGENCE_QUERIES = {
        'grants_subsidies': [
            '"{company}" grant subsidy green shipping',
            '"{company}" EU funding climate maritime',
            '"{company}" government support emissions reduction',
            '"{company}" Germany subsidy retrofit',
        ],
        'legal_violations': [
            '"{company}" lawsuit environmental violation',
            '"{company}" fine penalty emissions',
            '"{company}" court case pollution',
            '"{company}" regulatory compliance breach',
        ],
        'sustainability_news': [
            '"{company}" wind propulsion retrofit',
            '"{company}" green technology adoption',
            '"{company}" sustainability initiative announced',
            '"{company}" carbon reduction program',
        ],
        'reputation': [
            '"{company}" sustainability rating ranking',
            '"{company}" environmental performance score',
            '"{company}" CDP climate disclosure',
            '"{company}" RightShip GHG rating',
        ],
        'financial_pressure': [
            '"{company}" carbon tax exposure',
            '"{company}" emissions trading scheme',
            '"{company}" EU ETS compliance cost',
            '"{company}" fuel cost crisis',
        ]
    }
    
    # Sources to prioritize (news, not company sites)
    TRUSTED_SOURCES = [
        'lloydslist.com',
        'tradewindsnews.com',
        'reuters.com',
        'shiptechnology.com',
        'maritime-executive.com',
        'seatrade-maritime.com',
        'splash247.com',
        'euractiv.com',  # EU policy news
        'ec.europa.eu',  # EU official
        'bmwk.de',       # German ministry
        'gov.uk',        # UK gov
        'courtlistener.com',  # Legal cases
    ]
    
    # Sources to SKIP (company marketing)
    SKIP_SOURCES = [
        'linkedin.com',
        'facebook.com',
        'twitter.com',
        'instagram.com',
        'youtube.com',
    ]
    
    def __init__(self, verbose: bool = False):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.intelligence_data = {}
        self.verbose = verbose
        
        # Respectful rate limiting (Google can block)
        self.min_delay = 3.0
        self.max_delay = 6.0
    
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
    
    def _delay(self):
        """Random delay to respect rate limits"""
        delay = random.uniform(self.min_delay, self.max_delay)
        if self.verbose:
            print(f"    ⏳ {delay:.1f}s...")
        time.sleep(delay)
    
    def _search_intelligence(self, company_name: str, category: str) -> List[Dict[str, Any]]:
        """Search for intelligence on a specific category"""
        if not GOOGLE_SEARCH_AVAILABLE:
            return []
        
        queries = self.INTELLIGENCE_QUERIES.get(category, [])
        results = []
        
        for query_template in queries[:2]:  # Limit to 2 queries per category
            try:
                query = query_template.format(company=company_name)
                
                if self.verbose:
                    print(f"      🔎 {query[:60]}...")
                
                # Search Google
                search_results = []
                for url in google_search(query, num_results=5, sleep_interval=2, lang='en'):
                    # Skip social media and company's own website
                    if any(skip in url.lower() for skip in self.SKIP_SOURCES):
                        continue
                    
                    # Skip if it's the company's own domain
                    company_domain = company_name.lower().split()[0].replace('.', '')
                    if company_domain in url.lower() and len(company_domain) > 4:
                        continue
                    
                    search_results.append(url)
                    if len(search_results) >= 3:  # Max 3 results per query
                        break
                
                # Scrape content from results
                for url in search_results:
                    try:
                        # Prioritize trusted sources
                        is_trusted = any(source in url for source in self.TRUSTED_SOURCES)
                        
                        resp = self.session.get(url, timeout=10, allow_redirects=True)
                        if resp.status_code != 200:
                            continue
                        
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        
                        # Extract title and snippet
                        title = soup.find('title')
                        title_text = title.get_text(strip=True) if title else ''
                        
                        # Remove scripts, styles, nav
                        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                            tag.decompose()
                        
                        # Get main content
                        content = soup.get_text(separator=' ', strip=True)
                        
                        # Extract relevant snippet (around company name)
                        snippet = self._extract_relevant_snippet(content, company_name)
                        
                        if snippet:
                            results.append({
                                'url': url,
                                'title': title_text[:200],
                                'snippet': snippet,
                                'source': self._identify_source(url),
                                'is_trusted': is_trusted,
                                'category': category,
                                'scraped_at': datetime.now().isoformat()
                            })
                        
                        time.sleep(1)  # Small delay between page scrapes
                        
                    except Exception as e:
                        if self.verbose:
                            print(f"        ⚠️  Failed to scrape {url[:40]}: {e}")
                        continue
                
                self._delay()
                
            except Exception as e:
                if self.verbose:
                    print(f"        ❌ Search failed: {e}")
                continue
        
        return results
    
    def _extract_relevant_snippet(self, content: str, company_name: str, max_length: int = 500) -> str:
        """Extract snippet around company mentions"""
        # Find sentences mentioning the company
        sentences = content.split('. ')
        relevant = []
        
        for i, sentence in enumerate(sentences):
            if company_name.lower() in sentence.lower():
                # Get context: previous, current, next sentence
                start = max(0, i-1)
                end = min(len(sentences), i+2)
                context = '. '.join(sentences[start:end])
                relevant.append(context)
        
        snippet = ' [...] '.join(relevant[:3])  # Max 3 contexts
        return snippet[:max_length] if snippet else ''
    
    def _identify_source(self, url: str) -> str:
        """Identify source type"""
        url_lower = url.lower()
        
        if any(source in url_lower for source in ['gov.', '.gov', 'europa.eu', 'ec.europa.eu']):
            return 'government'
        elif any(source in url_lower for source in ['court', 'legal', 'law']):
            return 'legal'
        elif any(source in url_lower for source in ['lloydslist', 'tradewinds', 'reuters', 'seatrade']):
            return 'maritime_news'
        elif any(source in url_lower for source in ['cdp.', 'rightship', 'rating']):
            return 'rating_agency'
        else:
            return 'news_media'
    
    def gather_intelligence(self, company_meta: Dict) -> Dict[str, Any]:
        """Gather comprehensive intelligence on a company"""
        company_name = company_meta['name']
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"🕵️  {company_name} (Fleet: {company_meta['vessel_count']} vessels)")
            print(f"{'='*80}")
        
        intelligence = {
            'company_name': company_name,
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'vessel_count': company_meta['vessel_count'],
                'avg_emissions': round(company_meta['avg_emissions'], 2) if company_meta['avg_emissions'] else None,
                'avg_co2_distance': round(company_meta['avg_co2_distance'], 2) if company_meta['avg_co2_distance'] else None
            },
            'intelligence': {}
        }
        
        # Search each intelligence category
        for category in self.INTELLIGENCE_QUERIES.keys():
            if self.verbose:
                print(f"  📡 {category.replace('_', ' ').title()}...")
            
            results = self._search_intelligence(company_name, category)
            
            intelligence['intelligence'][category] = {
                'results_count': len(results),
                'findings': results
            }
            
            if self.verbose:
                print(f"    ✅ {len(results)} findings")
        
        return intelligence
    
    def scrape_batch(self, max_companies: int = 10, start_from: int = 0):
        """Scrape intelligence for multiple companies"""
        companies = self.get_companies_from_db()
        
        print(f"\n{'='*80}")
        print(f"🕵️  COMPANY INTELLIGENCE SCRAPER")
        print(f"{'='*80}")
        print(f"📋 Total companies in DB: {len(companies)}")
        
        if start_from > 0:
            companies = companies[start_from:]
            print(f"⏭️  Starting from #{start_from + 1}")
        
        companies = companies[:max_companies]
        print(f"📌 Gathering intelligence on {len(companies)} companies")
        print(f"{'='*80}\n")
        
        for i, company_meta in enumerate(companies, start_from + 1):
            try:
                print(f"\n[{i}/{start_from + len(companies)}]", end=" ")
                
                intelligence = self.gather_intelligence(company_meta)
                self.intelligence_data[company_meta['name']] = intelligence
                
                # Save progress every 5 companies
                if i % 5 == 0:
                    self.save_results(progress=True)
                    if self.verbose:
                        print(f"\n💾 Progress saved at {i} companies")
                
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Interrupted. Saving progress...")
                self.save_results(progress=True)
                break
            except Exception as e:
                print(f"\n❌ Failed: {company_meta['name']}: {e}")
                continue
        
        self.save_results(progress=False)
    
    def save_results(self, progress: bool = False):
        """Save intelligence data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if progress:
            filename = 'data/company_intelligence_progress.json'
        else:
            filename = f'data/company_intelligence_{timestamp}.json'
        
        output_file = Path(filename)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'companies': self.intelligence_data,
                'total': len(self.intelligence_data),
                'timestamp': datetime.now().isoformat(),
                'version': 'intelligence-v1',
                'categories': list(self.INTELLIGENCE_QUERIES.keys())
            }, f, indent=2, ensure_ascii=False)
        
        if not progress:
            print(f"\n{'='*80}")
            print(f"✅ INTELLIGENCE DATA SAVED:")
            print(f"  📄 File: {output_file}")
            print(f"  📊 Companies: {len(self.intelligence_data)}")
            
            # Stats
            total_findings = sum(
                sum(cat['results_count'] for cat in company['intelligence'].values())
                for company in self.intelligence_data.values()
            )
            print(f"  🔍 Total findings: {total_findings}")
            print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Company Intelligence Scraper - Internet-wide data gathering')
    parser.add_argument('--max-companies', type=int, default=10, help='Max companies to scrape')
    parser.add_argument('--start-from', type=int, default=0, help='Start from company index')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not GOOGLE_SEARCH_AVAILABLE:
        print("❌ googlesearch-python not installed!")
        print("   Install: pip install googlesearch-python")
        return
    
    scraper = CompanyIntelligenceScraper(verbose=args.verbose)
    scraper.scrape_batch(
        max_companies=args.max_companies,
        start_from=args.start_from
    )


if __name__ == '__main__':
    main()
