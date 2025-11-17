#!/usr/bin/env python3
"""
Company Intelligence Scraper V2 - Robust Internet-Wide Data Gathering
Uses DuckDuckGo + Direct Site Scraping (more reliable than Google)

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
from urllib.parse import quote_plus

# Fix Windows console encoding
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class CompanyIntelligenceScraperV2:
    """Scrape predictive intelligence using DuckDuckGo + direct site scraping"""
    
    # Direct news sites to scrape (more reliable than Google search)
    NEWS_SITES = {
        'lloyds_list': 'https://lloydslist.maritimeintelligence.informa.com/search?q={query}',
        'tradewinds': 'https://www.tradewindsnews.com/search?q={query}',
        'splash247': 'https://splash247.com/?s={query}',
        'maritime_executive': 'https://www.maritime-executive.com/search?term={query}',
    }
    
    # Government/regulatory sites
    REGULATORY_SITES = {
        'eu_funding': 'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/search/projects?keywords={query}',
        'german_subsidy': 'https://www.bundesanzeiger.de/pub/de/start?q={query}',
    }
    
    def __init__(self, verbose: bool = False):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        self.intelligence_data = {}
        self.verbose = verbose
        
        # Respectful rate limiting
        self.min_delay = 2.0
        self.max_delay = 4.0
    
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
    
    def _search_duckduckgo(self, query: str, max_results: int = 5) -> List[str]:
        """Search DuckDuckGo HTML (more lenient than Google)"""
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            if self.verbose:
                print(f"      🔎 DuckDuckGo: {query[:50]}...")
            
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Extract result links
            for result in soup.find_all('a', class_='result__url', limit=max_results):
                url = result.get('href', '')
                if url and url.startswith('http'):
                    # Filter out social media
                    if not any(skip in url.lower() for skip in ['linkedin', 'facebook', 'twitter', 'youtube']):
                        results.append(url)
            
            return results[:max_results]
            
        except Exception as e:
            if self.verbose:
                print(f"        ⚠️  DuckDuckGo search failed: {e}")
            return []
    
    def _scrape_page_snippet(self, url: str, company_name: str) -> Dict[str, Any]:
        """Scrape a page and extract relevant snippet"""
        try:
            resp = self.session.get(url, timeout=10, allow_redirects=True)
            if resp.status_code != 200:
                return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Get title
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ''
            
            # Remove noise
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # Get text
            content = soup.get_text(separator=' ', strip=True)
            
            # Extract snippet around company name
            snippet = self._extract_relevant_snippet(content, company_name)
            
            if snippet and len(snippet) > 100:
                return {
                    'url': url,
                    'title': title_text[:200],
                    'snippet': snippet[:500],
                    'source': self._identify_source(url),
                    'scraped_at': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            if self.verbose:
                print(f"        ⚠️  Failed {url[:40]}: {e}")
            return None
    
    def _extract_relevant_snippet(self, content: str, company_name: str) -> str:
        """Extract sentences mentioning the company"""
        sentences = re.split(r'[.!?]\s+', content)
        relevant = []
        
        for i, sentence in enumerate(sentences):
            if company_name.lower() in sentence.lower():
                # Context: previous + current + next
                start = max(0, i-1)
                end = min(len(sentences), i+2)
                context = '. '.join(sentences[start:end])
                relevant.append(context)
                
                if len(relevant) >= 2:  # Max 2 contexts
                    break
        
        return ' [...] '.join(relevant)
    
    def _identify_source(self, url: str) -> str:
        """Identify source type"""
        url_lower = url.lower()
        
        if any(x in url_lower for x in ['gov.', '.gov', 'europa.eu', 'ec.europa.eu']):
            return 'government'
        elif any(x in url_lower for x in ['court', 'legal', 'law']):
            return 'legal'
        elif any(x in url_lower for x in ['lloydslist', 'tradewinds', 'splash', 'maritime-executive', 'seatrade']):
            return 'maritime_news'
        else:
            return 'news'
    
    def _search_intelligence(self, company_name: str, category: str) -> List[Dict[str, Any]]:
        """Search for intelligence on a category"""
        results = []
        
        # Search queries per category
        queries = {
            'grants_subsidies': [
                f'"{company_name}" grant maritime green shipping',
                f'{company_name} EU funding shipping emissions',
            ],
            'legal_violations': [
                f'"{company_name}" fine penalty environmental shipping',
                f'{company_name} lawsuit emissions violation',
            ],
            'sustainability_news': [
                f'"{company_name}" wind propulsion sailing retrofit',
                f'{company_name} green shipping initiative',
            ],
            'reputation': [
                f'{company_name} sustainability rating shipping',
                f'{company_name} environmental performance maritime',
            ],
            'financial_pressure': [
                f'{company_name} carbon tax EU ETS shipping',
                f'{company_name} emissions cost compliance',
            ]
        }
        
        search_queries = queries.get(category, [])
        
        for query in search_queries[:2]:  # Max 2 queries per category
            # Search DuckDuckGo
            urls = self._search_duckduckgo(query, max_results=3)
            
            # Scrape found pages
            for url in urls:
                snippet_data = self._scrape_page_snippet(url, company_name)
                if snippet_data:
                    snippet_data['category'] = category
                    results.append(snippet_data)
                
                time.sleep(1)  # Small delay between pages
                
                if len(results) >= 3:  # Max 3 findings per category
                    break
            
            if len(results) >= 3:
                break
            
            self._delay()
        
        return results
    
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
        
        # Search categories
        categories = [
            'grants_subsidies',
            'legal_violations',
            'sustainability_news',
            'reputation',
            'financial_pressure'
        ]
        
        for category in categories:
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
        print(f"🕵️  COMPANY INTELLIGENCE SCRAPER V2 (DuckDuckGo)")
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
            filename = 'data/company_intelligence_v2_progress.json'
        else:
            filename = f'data/company_intelligence_v2_{timestamp}.json'
        
        output_file = Path(filename)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'companies': self.intelligence_data,
                'total': len(self.intelligence_data),
                'timestamp': datetime.now().isoformat(),
                'version': 'intelligence-v2-duckduckgo',
                'categories': ['grants_subsidies', 'legal_violations', 'sustainability_news', 'reputation', 'financial_pressure']
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
            
            if len(self.intelligence_data) > 0:
                print(f"  📊 Avg per company: {total_findings/len(self.intelligence_data):.1f}")
            
            print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Company Intelligence Scraper V2 - DuckDuckGo + Direct Sites')
    parser.add_argument('--max-companies', type=int, default=10, help='Max companies to scrape')
    parser.add_argument('--start-from', type=int, default=0, help='Start from company index')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    scraper = CompanyIntelligenceScraperV2(verbose=args.verbose)
    scraper.scrape_batch(
        max_companies=args.max_companies,
        start_from=args.start_from
    )


if __name__ == '__main__':
    main()
