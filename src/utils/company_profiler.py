#!/usr/bin/env python3
"""
Comprehensive Company Profiler
Scrapes detailed information for all shipping companies in the database
"""

import sqlite3
import requests
import json
import time
import re
import io
import sys
import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
import random

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class CompanyProfiler:
    def __init__(self, verbose: bool = False, max_pages_per_site: int = 30):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.companies_data = {}
        self.failed_companies = []
        self.verbose = verbose
        self.max_pages_per_site = max_pages_per_site
        
        # Rate limiting
        self.min_delay = 2  # seconds
        self.max_delay = 5  # seconds
        
        # Data sources
        self.sources = {
            'google_search': self._google_search_company,
            'linkedin': self._scrape_linkedin,
            'maritime_database': self._scrape_maritime_databases,
            'corporate_registry': self._scrape_corporate_registries,
            'company_website': self._find_company_website
        }
    
    def get_companies_from_db(self):
        """Extract all company names from database"""
        conn = sqlite3.connect('data/vessel_static_data.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT company_name FROM eu_mrv_emissions WHERE company_name IS NOT NULL AND company_name != "" ORDER BY company_name')
        companies = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return companies
    
    def _delay(self):
        """Random delay to avoid rate limiting"""
        delay = random.uniform(self.min_delay, self.max_delay)
        if self.verbose:
            print(f"    Sleeping for {delay:.2f}s to respect rate limits...")
        time.sleep(delay)
    
    def _clean_company_name(self, name):
        """Clean company name for better search results"""
        # Remove common suffixes and prefixes
        name = re.sub(r'^"|"$', '', name)  # Remove quotes
        name = re.sub(r'\s+(Ltd|Inc|Corp|GmbH|SA|AS|AB|S\.A\.|S\.p\.A\.|Co\.,? Ltd\.?|Limited|LLC|B\.V\.|A/S)\.?$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(Company|Shipping|Maritime|Naval|Transport|Logistics)\.?$', '', name, flags=re.IGNORECASE)
        return name.strip()
    
    def _google_search_company(self, company_name):
        """Search Google for company information"""
        try:
            search_query = f"{company_name} shipping company headquarters CEO founded revenue"
            encoded_query = quote(search_query)
            
            # Use DuckDuckGo for more reliable results
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            if self.verbose:
                print(f"    [google_search] GET {url}")
            response = self.session.get(url, timeout=10)
            if self.verbose:
                print(f"    [google_search] Status: {response.status_code}, {len(response.content)} bytes")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            results = []
            for result in soup.find_all('a', class_='result__a', limit=5):
                title = result.get_text(strip=True)
                snippet = result.find_next('a', class_='result__snippet')
                snippet_text = snippet.get_text(strip=True) if snippet else ""
                
                results.append({
                    'title': title,
                    'snippet': snippet_text,
                    'url': result.get('href', '')
                })
            
            return {'search_results': results}
        except Exception as e:
            return {'error': str(e)}
    
    def _scrape_linkedin(self, company_name):
        """Try to get LinkedIn company information"""
        try:
            search_query = f"site:linkedin.com/company {company_name}"
            encoded_query = quote(search_query)
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            
            if self.verbose:
                print(f"    [linkedin] GET {url}")
            response = self.session.get(url, timeout=10)
            if self.verbose:
                print(f"    [linkedin] Status: {response.status_code}, {len(response.content)} bytes")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            linkedin_results = []
            for result in soup.find_all('a', class_='result__a', limit=3):
                if 'linkedin.com/company' in result.get('href', ''):
                    title = result.get_text(strip=True)
                    linkedin_results.append({
                        'company_name': title,
                        'url': result.get('href', '')
                    })
            
            return {'linkedin_profiles': linkedin_results}
        except Exception as e:
            return {'error': str(e)}
    
    def _scrape_maritime_databases(self, company_name):
        """Search maritime-specific databases"""
        maritime_sources = [
            "site:marinetraffic.com",
            "site:vesselfinder.com", 
            "site:shipspotting.com",
            "site:fleetmon.com"
        ]
        
        results = {}
        for source in maritime_sources:
            try:
                search_query = f"{source} {company_name}"
                encoded_query = quote(search_query)
                url = f"https://duckduckgo.com/html/?q={encoded_query}"
                
                if self.verbose:
                    print(f"    [maritime:{source}] GET {url}")
                response = self.session.get(url, timeout=10)
                if self.verbose:
                    print(f"    [maritime:{source}] Status: {response.status_code}, {len(response.content)} bytes")
                soup = BeautifulSoup(response.content, 'html.parser')
                
                source_results = []
                for result in soup.find_all('a', class_='result__a', limit=3):
                    title = result.get_text(strip=True)
                    source_results.append({
                        'title': title,
                        'url': result.get('href', '')
                    })
                
                results[source.replace('site:', '')] = source_results
                self._delay()
            except Exception as e:
                results[source.replace('site:', '')] = {'error': str(e)}
        
        return {'maritime_databases': results}
    
    def _scrape_corporate_registries(self, company_name):
        """Search corporate registries and business databases"""
        registry_sources = [
            "site:opencorporates.com",
            "site:crunchbase.com",
            "site:orbis.com",
            "site:bloomberg.com"
        ]
        
        results = {}
        for source in registry_sources:
            try:
                search_query = f"{source} {company_name}"
                encoded_query = quote(search_query)
                url = f"https://duckduckgo.com/html/?q={encoded_query}"
                
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                source_results = []
                for result in soup.find_all('a', class_='result__a', limit=3):
                    title = result.get_text(strip=True)
                    source_results.append({
                        'title': title,
                        'url': result.get('href', '')
                    })
                
                results[source.replace('site:', '')] = source_results
                self._delay()
            except Exception as e:
                results[source.replace('site:', '')] = {'error': str(e)}
        
        return {'corporate_registries': results}
    
    def _find_company_website(self, company_name):
        """Find official company website"""
        try:
            search_query = f"{company_name} official website"
            encoded_query = quote(search_query)
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            
            if self.verbose:
                print(f"    [company_website] GET {url}")
            response = self.session.get(url, timeout=10)
            if self.verbose:
                print(f"    [company_website] Status: {response.status_code}, {len(response.content)} bytes")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            websites = []
            for result in soup.find_all('a', class_='result__a', limit=5):
                href = result.get('href', '')
                title = result.get_text(strip=True)
                
                # Try to identify official websites
                if any(keyword in title.lower() for keyword in ['official', 'home', 'company', company_name.lower().split()[0]]):
                    websites.append({
                        'title': title,
                        'url': href,
                        'domain': urlparse(href).netloc if href else ''
                    })
            
            return {'official_websites': websites}
        except Exception as e:
            return {'error': str(e)}
    
    def _pick_best_website(self, website_data):
        """Pick the most likely official website URL from search data."""
        try:
            websites = website_data.get('official_websites') or []
            if not websites:
                return None
            # Prefer HTTPS and domains that don't look like social media / directories
            def score_site(entry):
                url = entry.get('url') or ''
                domain = entry.get('domain') or ''
                score = 0
                if url.startswith('https://'):
                    score += 2
                if 'linkedin.com' in domain or 'facebook.com' in domain or 'wikipedia.org' in domain:
                    score -= 5
                # Shorter domains tend to be closer to root brand
                score -= len(domain)
                return score
            best = sorted(websites, key=score_site, reverse=True)[0]
            return best.get('url')
        except Exception:
            return None
    
    def _extract_text_from_html(self, html_content):
        """Extract readable text from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        text = soup.get_text(separator='\n')
        # Normalize whitespace a bit
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return '\n'.join(lines)
    
    def _crawl_website(self, root_url, company_name):
        """Crawl a company's website and dump all page text to a TXT file."""
        if not root_url:
            return None
        try:
            parsed_root = urlparse(root_url)
            base_domain = parsed_root.netloc
            if not base_domain:
                return None
            if self.verbose:
                print(f"  [crawl] Starting crawl for {company_name} at {root_url}")
                print(f"  [crawl] Max pages per site: {self.max_pages_per_site}")
            visited = set()
            queue = [root_url]
            pages = []
            project_root = Path(__file__).parent.parent.parent
            safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", company_name)[:80]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = project_root / 'data' / 'company_sites'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{safe_name}_{timestamp}.txt"
            page_count = 0
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 100 + "\n")
                f.write(f"COMPANY WEBSITE CRAWL\n")
                f.write(f"Company: {company_name}\n")
                f.write(f"Root URL: {root_url}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write("=" * 100 + "\n\n")
                while queue and page_count < self.max_pages_per_site:
                    current_url = queue.pop(0)
                    current_url, _ = urldefrag(current_url)
                    if current_url in visited:
                        continue
                    visited.add(current_url)
                    try:
                        if self.verbose:
                            print(f"    [crawl] GET {current_url}")
                        resp = self.session.get(current_url, timeout=15)
                        if self.verbose:
                            print(f"    [crawl] Status: {resp.status_code}, {len(resp.content)} bytes")
                        if resp.status_code != 200 or 'text/html' not in resp.headers.get('Content-Type', ''):
                            continue
                        text = self._extract_text_from_html(resp.text)
                        page_count += 1
                        f.write("-" * 80 + "\n")
                        f.write(f"URL: {current_url}\n")
                        f.write("-" * 80 + "\n")
                        f.write(text + "\n\n")
                        # Discover more links on same domain
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        for a in soup.find_all('a', href=True):
                            href = a['href']
                            if href.startswith('mailto:') or href.startswith('tel:'):
                                continue
                            abs_url = urljoin(current_url, href)
                            parsed = urlparse(abs_url)
                            if parsed.netloc != base_domain:
                                continue
                            if parsed.scheme not in ('http', 'https'):
                                continue
                            abs_url, _ = urldefrag(abs_url)
                            if abs_url not in visited and len(queue) + len(visited) < self.max_pages_per_site * 5:
                                queue.append(abs_url)
                        self._delay()
                    except Exception as e:
                        if self.verbose:
                            print(f"    [crawl] Error fetching {current_url}: {e}")
                        continue
            if self.verbose:
                print(f"  [crawl] Finished crawl: {page_count} pages -> {output_file}")
            return {
                'root_url': root_url,
                'output_file': str(output_file),
                'pages_crawled': page_count
            }
        except Exception as e:
            if self.verbose:
                print(f"  [crawl] Fatal crawl error for {company_name}: {e}")
            return None
    
    def profile_company(self, company_name):
        """Create comprehensive profile for a single company"""
        print(f"Profiling: {company_name}")
        
        profile = {
            'company_name': company_name,
            'search_date': datetime.now().isoformat(),
            'data_sources': {}
        }
        
        # Try each data source
        for source_name, source_func in self.sources.items():
            try:
                print(f"  - Checking {source_name}...")
                data = source_func(company_name)
                profile['data_sources'][source_name] = data
                self._delay()
            except Exception as e:
                profile['data_sources'][source_name] = {'error': str(e)}
                print(f"    Error: {e}")
        
        # If we found at least one official website, crawl it
        website_data = profile['data_sources'].get('company_website') or {}
        best_url = self._pick_best_website(website_data) if isinstance(website_data, dict) else None
        if best_url:
            crawl_info = self._crawl_website(best_url, company_name)
            if crawl_info:
                profile['data_sources']['website_crawl'] = crawl_info
            else:
                profile['data_sources']['website_crawl'] = {'error': 'crawl_failed'}
        else:
            profile['data_sources']['website_crawl'] = {'error': 'no_website_found'}
        
        return profile
    
    def profile_all_companies(self, max_companies=None, company_filter=None):
        """Profile all companies from database"""
        companies = self.get_companies_from_db()
        print(f"Found {len(companies)} companies to profile")
        
        if company_filter:
            filtered = [c for c in companies if company_filter.lower() in c.lower()]
            if not filtered:
                print(f"No companies matched filter: {company_filter}")
                return
            companies = filtered
            print(f"Filtered to {len(companies)} companies matching '{company_filter}'")
        
        if max_companies:
            companies = companies[:max_companies]
            print(f"Limiting to first {max_companies} companies")
        
        for i, company in enumerate(companies, 1):
            try:
                print(f"\n[{i}/{len(companies)}] Processing: {company}")
                profile = self.profile_company(company)
                self.companies_data[company] = profile
                
                # Save progress every 10 companies
                if i % 10 == 0:
                    self.save_progress()
                    print(f"Saved progress at {i} companies")
                
            except KeyboardInterrupt:
                print(f"\nInterrupted at company {i}. Saving progress...")
                break
            except Exception as e:
                print(f"Failed to profile {company}: {e}")
                self.failed_companies.append(company)
                continue
        
        self.save_final_results()
    
    def save_progress(self):
        """Save current progress to file"""
        output_file = Path('data/company_profiles_progress.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'companies': self.companies_data,
                'failed_companies': self.failed_companies,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        if self.verbose:
            print(f"  [progress] Saved intermediate results to {output_file}")
    
    def save_final_results(self):
        """Save comprehensive results to multiple formats"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON format
        json_file = Path(f'data/company_profiles_{timestamp}.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'companies': self.companies_data,
                'failed_companies': self.failed_companies,
                'total_companies': len(self.companies_data),
                'failed_count': len(self.failed_companies),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # Raw text format (as requested)
        txt_file = Path(f'data/company_profiles_raw_{timestamp}.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("COMPREHENSIVE SHIPPING COMPANY PROFILES\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Companies: {len(self.companies_data)}\n")
            f.write(f"Failed: {len(self.failed_companies)}\n")
            f.write("=" * 100 + "\n\n")
            
            for company_name, profile in self.companies_data.items():
                f.write("=" * 80 + "\n")
                f.write(f"COMPANY: {company_name}\n")
                f.write("=" * 80 + "\n")
                
                for source, data in profile['data_sources'].items():
                    f.write(f"\n{'-' * 40}\n")
                    f.write(f"SOURCE: {source.upper()}\n")
                    f.write(f"{'-' * 40}\n")
                    
                    if 'error' in data:
                        f.write(f"ERROR: {data['error']}\n")
                    else:
                        for key, value in data.items():
                            f.write(f"\n{key}:\n")
                            if isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict):
                                        for sub_key, sub_value in item.items():
                                            f.write(f"  {sub_key}: {sub_value}\n")
                                    else:
                                        f.write(f"  - {item}\n")
                            else:
                                f.write(f"  {value}\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"\nResults saved:")
        print(f"  JSON: {json_file}")
        print(f"  TXT:  {txt_file}")

def main():
    parser = argparse.ArgumentParser(description="Comprehensive company profiler")
    parser.add_argument(
        "--max-companies",
        type=int,
        default=5,
        help="Maximum number of companies to process (default: 5)"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (show each HTTP request, delay, and save)"
    )
    parser.add_argument(
        "--max-pages-per-site",
        type=int,
        default=30,
        help="Maximum number of pages to crawl per company website (default: 30)"
    )
    parser.add_argument(
        "--company",
        type=str,
        help="Only profile companies whose name contains this substring"
    )

    args = parser.parse_args()

    profiler = CompanyProfiler(verbose=args.verbose, max_pages_per_site=args.max_pages_per_site)
    
    print("Starting comprehensive company profiling...")
    print("WARNING: This may take a very long time (3,544 companies in total)")
    print("Press Ctrl+C to stop and save progress\n")
    
    if args.max_companies:
        print(f"Running batch ({args.max_companies} companies)...")
        profiler.profile_all_companies(max_companies=args.max_companies, company_filter=args.company)
    else:
        print("Running all companies (this will take many hours/days)...")
        profiler.profile_all_companies(company_filter=args.company)

if __name__ == "__main__":
    main()
