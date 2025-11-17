#!/usr/bin/env python3
"""
Enhanced Company Profiler v2 - ML Training Data Collection
Scrapes comprehensive company information for WASP fit score prediction model
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
from urllib.parse import quote, urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
import random

# Fix Windows console encoding for emojis
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Try importing optional dependencies
try:
    from googlesearch import search as google_search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    print("⚠️  googlesearch-python not installed. Install with: pip install googlesearch-python")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not installed. Install with: pip install playwright && playwright install chromium")


class CompanyProfilerV2:
    def __init__(self, verbose: bool = False, max_pages_per_site: int = 15, use_browser: bool = False):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.companies_data = {}
        self.failed_companies = []
        self.verbose = verbose
        self.max_pages_per_site = max_pages_per_site
        self.use_browser = use_browser and PLAYWRIGHT_AVAILABLE
        
        # Rate limiting - reduced for faster collection
        self.min_delay = 1.5  # Reduced from 3
        self.max_delay = 3.0  # Reduced from 7
        
        # Data sources priority order
        self.sources = [
            ('wikipedia', self._get_wikipedia_data),
            ('google_search', self._google_search_company),
            ('company_website', self._find_company_website),
            ('website_crawl', self._crawl_website_smart),
        ]
    
    def get_companies_from_db(self):
        """Extract company names from database, ordered by vessel count (most popular first)"""
        conn = sqlite3.connect('data/vessel_static_data.db')
        cursor = conn.cursor()
        
        # Get companies ordered by vessel count (largest fleets first)
        cursor.execute('''
            SELECT company_name, COUNT(*) as vessel_count 
            FROM eu_mrv_emissions 
            WHERE company_name IS NOT NULL 
              AND company_name != "" 
              AND company_name NOT LIKE '"%' 
            GROUP BY company_name 
            ORDER BY vessel_count DESC, company_name
        ''')
        companies = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return companies
    
    def _delay(self):
        """Random delay to respect rate limits"""
        delay = random.uniform(self.min_delay, self.max_delay)
        if self.verbose:
            print(f"    ⏳ Sleeping {delay:.1f}s...")
        time.sleep(delay)
    
    def _get_wikipedia_data(self, company_name):
        """Get structured data from Wikipedia/Wikidata"""
        try:
            # Search Wikipedia - try with "company" keyword first
            search_url = f"https://en.wikipedia.org/w/api.php"
            
            # Try multiple search variations - more specific for shipping
            search_queries = [
                f"{company_name} shipping",
                f"{company_name} maritime",
                f"{company_name.split()[0]} shipping",  # First word + shipping
                company_name
            ]
            
            page_title = None
            page_url = None
            
            for query in search_queries:
                params = {
                    'action': 'opensearch',
                    'search': query,
                    'limit': 5,
                    'namespace': 0,
                    'format': 'json'
                }
                
                if self.verbose:
                    print(f"    [wikipedia] Searching for '{query}'")
                
                response = self.session.get(search_url, params=params, timeout=10)
                data = response.json()
                
                if data[1]:  # Found results
                    # Look for the best match (avoid hijacking, incidents, etc.)
                    for i, title in enumerate(data[1]):
                        title_lower = title.lower()
                        if not any(word in title_lower for word in ['hijacking', 'incident', 'disaster', 'sinking', 'accident']):
                            page_title = title
                            page_url = data[3][i]
                            break
                    
                    if page_title:
                        break
            
            if not page_title:
                return {'error': 'not_found'}
            
            # Get page content
            extract_params = {
                'action': 'query',
                'titles': page_title,
                'prop': 'extracts|info|pageprops',
                'exintro': True,
                'explaintext': True,
                'inprop': 'url',
                'format': 'json'
            }
            
            response = self.session.get(search_url, params=extract_params, timeout=10)
            page_data = response.json()
            
            pages = page_data.get('query', {}).get('pages', {})
            page_info = list(pages.values())[0]
            
            return {
                'title': page_title,
                'url': page_url,
                'extract': page_info.get('extract', ''),
                'full_url': page_info.get('fullurl', '')
            }
            
        except Exception as e:
            if self.verbose:
                print(f"    [wikipedia] Error: {e}")
            return {'error': str(e)}
    
    def _google_search_company(self, company_name):
        """Search Google for company information"""
        if not GOOGLE_SEARCH_AVAILABLE:
            return {'error': 'googlesearch-python not installed'}
        
        try:
            query = f"{company_name} shipping company headquarters fleet"
            if self.verbose:
                print(f"    [google] Searching: {query}")
            
            results = []
            try:
                for url in google_search(query, num_results=10, sleep_interval=3, lang='en'):
                    results.append(url)
                    if len(results) >= 10:
                        break
            except Exception as search_error:
                if self.verbose:
                    print(f"    [google] Search failed: {search_error}")
                # Return empty but not error - will use fallback
                return {'search_results': [], 'note': 'google_blocked'}
            
            return {'search_results': results}
            
        except Exception as e:
            if self.verbose:
                print(f"    [google] Error: {e}")
            return {'error': str(e)}
    
    def _find_company_website(self, company_name):
        """Find official company website using Google search or pattern matching"""
        # Known major shipping companies - direct URLs
        known_companies = {
            'maersk': 'https://www.maersk.com',
            'msc': 'https://www.msc.com',
            'mediterranean shipping': 'https://www.msc.com',
            'cma cgm': 'https://www.cma-cgm.com',
            'cosco': 'https://www.cosco-shipping.com',
            'hapag': 'https://www.hapag-lloyd.com',
            'one': 'https://www.one-line.com',
            'evergreen': 'https://www.evergreen-marine.com',
            'yang ming': 'https://www.yangming.com',
            'hyundai': 'https://www.hmm21.com',
            'hmm': 'https://www.hmm21.com',
            'zim': 'https://www.zim.com',
            'torm': 'https://www.torm.com',
            'stolt': 'https://www.stolt-nielsen.com',
            'nyk': 'https://www.nyk.com',
            'spliethoff': 'https://www.spliethoff.com',
            'wagenborg': 'https://www.wagenborg.com',
            'grimaldi': 'https://www.grimaldi-lines.com',
            'seaspan': 'https://www.seaspanmarine.com',
            'zodiac': 'https://www.zodiacmaritime.com',
            'oldendorff': 'https://www.oldendorff.com',
            'synergy': 'https://www.syngr.com',
        }
        
        # Check if it's a known company
        company_lower = company_name.lower()
        for key, url in known_companies.items():
            if key in company_lower:
                if self.verbose:
                    print(f"    [website] Using known URL for {key}")
                return {'official_websites': [url], 'source': 'known_database'}
        
        # Try Google search if available
        if GOOGLE_SEARCH_AVAILABLE:
            try:
                query = f"{company_name} official website"
                if self.verbose:
                    print(f"    [website] Searching: {query}")
                
                urls = []
                try:
                    for url in google_search(query, num_results=5, sleep_interval=3, lang='en'):
                        # Filter out social media and directories
                        if not any(x in url.lower() for x in ['linkedin', 'facebook', 'twitter', 'wikipedia', 'crunchbase']):
                            urls.append(url)
                        if len(urls) >= 3:
                            break
                except:
                    pass  # Google blocked, continue to fallback
                
                if urls:
                    return {'official_websites': urls, 'source': 'google_search'}
                    
            except Exception as e:
                if self.verbose:
                    print(f"    [website] Search error: {e}")
        
        # Fallback: try common URL patterns
        domain_patterns = [
            company_name.lower().replace(' ', '').replace('.', '').replace('/', ''),
            company_name.lower().split()[0],
        ]
        
        guesses = []
        for pattern in domain_patterns[:2]:  # Only try first 2 patterns
            clean_pattern = ''.join(c for c in pattern if c.isalnum() or c == '-')
            guesses.extend([
                f"https://www.{clean_pattern}.com",
                f"https://{clean_pattern}.com",
                f"https://www.{clean_pattern}.eu",
                f"https://www.{clean_pattern}.de",
            ])
        
        return {'official_websites': guesses[:5], 'source': 'pattern_guessing'}
    
    def _clean_text(self, text):
        """Clean extracted text - remove encoded data, keep only readable content"""
        lines = text.splitlines()
        clean_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip lines that look like base64/encoded data (long strings of random chars)
            if len(line) > 100 and not ' ' in line[:100]:
                continue
            
            # Skip lines with mostly non-alphanumeric characters
            alpha_count = sum(c.isalnum() or c.isspace() for c in line)
            if len(line) > 20 and alpha_count / len(line) < 0.7:
                continue
            
            # Skip single-character or very short noise
            if len(line) < 3:
                continue
            
            # Skip lines that look like URLs
            if line.startswith(('http://', 'https://', '//', 'www.')):
                continue
            
            # Skip lines with excessive special characters (likely code/data)
            special_chars = sum(c in line for c in '{|}[]<>=+*&^%$#@!')
            if special_chars > len(line) * 0.3:
                continue
            
            clean_lines.append(line)
        
        # Join and return
        cleaned = '\n'.join(clean_lines)
        
        # Final check: if text is more than 70% numbers/symbols, discard it
        if len(cleaned) > 100:
            readable_chars = sum(c.isalpha() or c.isspace() for c in cleaned)
            if readable_chars / len(cleaned) < 0.5:
                return ""
        
        return cleaned
    
    def _crawl_with_requests(self, root_url, company_name):
        """Crawl website using requests (fast but no JavaScript)"""
        try:
            parsed_root = urlparse(root_url)
            base_domain = parsed_root.netloc
            if not base_domain:
                return None
            
            if self.verbose:
                print(f"    [crawl:requests] Starting at {root_url}")
            
            visited = set()
            queue = [root_url]
            pages_data = []
            page_count = 0
            
            while queue and page_count < self.max_pages_per_site:
                current_url = queue.pop(0)
                current_url, _ = urldefrag(current_url)
                
                if current_url in visited:
                    continue
                visited.add(current_url)
                
                try:
                    resp = self.session.get(current_url, timeout=15, allow_redirects=True)
                    if resp.status_code != 200 or 'text/html' not in resp.headers.get('Content-Type', ''):
                        continue
                    
                    # Extract text - remove more noise
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # Remove unwanted elements
                    for tag in soup(['script', 'style', 'noscript', 'iframe', 'embed', 
                                     'header', 'footer', 'nav', 'aside', 'form', 'input',
                                     'button', 'svg', 'canvas']):
                        tag.decompose()
                    
                    # Also remove data attributes that contain encoded content
                    for tag in soup.find_all(True):
                        for attr in list(tag.attrs.keys()):
                            if attr.startswith('data-') or attr in ['class', 'id', 'style']:
                                del tag[attr]
                    
                    # Extract text
                    text = soup.get_text(separator='\n', strip=True)
                    
                    # Clean the text
                    text = self._clean_text(text)
                    
                    if len(text) > 300:  # Only save pages with substantial CLEAN content
                        page_count += 1
                        pages_data.append({
                            'url': current_url,
                            'text': text[:10000],  # Limit to 10K chars per page (reduced from 15K)
                            'length': len(text)
                        })
                        
                        if self.verbose:
                            print(f"    [crawl:requests] Page {page_count}/{self.max_pages_per_site}: {current_url[:60]}... ({len(text)} chars)")
                    
                    # Find more links
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                            continue
                        
                        abs_url = urljoin(current_url, href)
                        parsed = urlparse(abs_url)
                        
                        if parsed.netloc != base_domain:
                            continue
                        if parsed.scheme not in ('http', 'https'):
                            continue
                        
                        abs_url, _ = urldefrag(abs_url)
                        if abs_url not in visited and abs_url not in queue:
                            queue.append(abs_url)
                    
                    self._delay()
                    
                except Exception as e:
                    if self.verbose:
                        print(f"    [crawl:requests] Error on {current_url}: {e}")
                    continue
            
            if self.verbose:
                print(f"    [crawl:requests] Collected {len(pages_data)} pages")
            
            return {
                'method': 'requests',
                'pages': pages_data,
                'pages_crawled': len(pages_data)
            }
            
        except Exception as e:
            if self.verbose:
                print(f"    [crawl:requests] Fatal error: {e}")
            return None
    
    def _crawl_with_playwright(self, root_url, company_name):
        """Crawl website using Playwright (handles JavaScript)"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        
        try:
            if self.verbose:
                print(f"    [crawl:playwright] Starting at {root_url}")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                visited = set()
                queue = [root_url]
                pages_data = []
                page_count = 0
                
                parsed_root = urlparse(root_url)
                base_domain = parsed_root.netloc
                
                while queue and page_count < min(10, self.max_pages_per_site):  # Limit Playwright to 10 pages
                    current_url = queue.pop(0)
                    current_url, _ = urldefrag(current_url)
                    
                    if current_url in visited:
                        continue
                    visited.add(current_url)
                    
                    try:
                        page.goto(current_url, wait_until='networkidle', timeout=30000)
                        time.sleep(2)  # Let JS render
                        
                        # Extract text
                        text = page.inner_text('body')
                        
                        if len(text) > 200:
                            page_count += 1
                            pages_data.append({
                                'url': current_url,
                                'text': text[:20000],
                                'length': len(text)
                            })
                        
                        # Find links
                        links = page.eval_on_selector_all('a[href]', 'elements => elements.map(e => e.href)')
                        for link in links:
                            parsed = urlparse(link)
                            if parsed.netloc == base_domain and link not in visited and link not in queue:
                                queue.append(link)
                        
                    except PlaywrightTimeout:
                        if self.verbose:
                            print(f"    [crawl:playwright] Timeout on {current_url}")
                        continue
                    except Exception as e:
                        if self.verbose:
                            print(f"    [crawl:playwright] Error on {current_url}: {e}")
                        continue
                
                browser.close()
            
            if self.verbose:
                print(f"    [crawl:playwright] Collected {len(pages_data)} pages")
            
            return {
                'method': 'playwright',
                'pages': pages_data,
                'pages_crawled': len(pages_data)
            }
            
        except Exception as e:
            if self.verbose:
                print(f"    [crawl:playwright] Fatal error: {e}")
            return None
    
    def _crawl_website_smart(self, company_name, website_data):
        """Smart website crawling - tries both methods"""
        # Extract URL from previous website search
        urls = []
        if isinstance(website_data, dict):
            urls = website_data.get('official_websites', []) or website_data.get('guessed_urls', [])
        
        if not urls:
            return {'error': 'no_website_found'}
        
        root_url = urls[0]  # Try first URL
        
        # Try Playwright first if requested
        if self.use_browser:
            result = self._crawl_with_playwright(root_url, company_name)
            if result and result.get('pages_crawled', 0) > 0:
                return result
        
        # Fallback to requests
        result = self._crawl_with_requests(root_url, company_name)
        if result and result.get('pages_crawled', 0) > 0:
            return result
        
        return {'error': 'crawl_failed', 'attempted_url': root_url}
    
    def profile_company(self, company_name):
        """Create comprehensive profile for a single company"""
        print(f"\n{'='*80}")
        print(f"📊 Profiling: {company_name}")
        print(f"{'='*80}")
        
        profile = {
            'company_name': company_name,
            'search_date': datetime.now().isoformat(),
            'data_sources': {}
        }
        
        website_data = None
        
        # Try each data source
        for source_name, source_func in self.sources:
            try:
                print(f"  🔍 {source_name.replace('_', ' ').title()}...")
                
                if source_name == 'website_crawl':
                    # Website crawl needs the website URL from previous step
                    data = source_func(company_name, website_data)
                else:
                    data = source_func(company_name)
                
                # Store website data for later use
                if source_name == 'company_website':
                    website_data = data
                
                profile['data_sources'][source_name] = data
                
                # Show results
                if isinstance(data, dict):
                    if 'error' in data:
                        print(f"    ❌ {data['error']}")
                    elif source_name == 'wikipedia' and 'title' in data:
                        print(f"    ✅ Found: {data['title']}")
                    elif 'pages_crawled' in data:
                        print(f"    ✅ Crawled {data['pages_crawled']} pages")
                    elif 'search_results' in data:
                        print(f"    ✅ Found {len(data['search_results'])} results")
                    elif 'official_websites' in data:
                        print(f"    ✅ Found {len(data['official_websites'])} websites")
                    else:
                        print(f"    ✅ Success")
                
                self._delay()
                
            except Exception as e:
                profile['data_sources'][source_name] = {'error': str(e)}
                print(f"    ❌ Error: {e}")
        
        return profile
    
    def profile_all_companies(self, max_companies=None, company_filter=None, start_from=0):
        """Profile all companies from database"""
        companies = self.get_companies_from_db()
        print(f"\n{'='*80}")
        print(f"📋 Found {len(companies)} unique companies in database")
        print(f"{'='*80}")
        
        if company_filter:
            companies = [c for c in companies if company_filter.lower() in c.lower()]
            print(f"🔎 Filtered to {len(companies)} companies matching '{company_filter}'")
        
        if start_from > 0:
            companies = companies[start_from:]
            print(f"⏭️  Starting from company #{start_from + 1}")
        
        if max_companies:
            companies = companies[:max_companies]
            print(f"📌 Limiting to {max_companies} companies")
        
        print()
        
        for i, company in enumerate(companies, start_from + 1):
            try:
                print(f"\n[{i}/{len(companies) + start_from}]", end=" ")
                profile = self.profile_company(company)
                self.companies_data[company] = profile
                
                # Save progress every 5 companies
                if i % 5 == 0:
                    self.save_progress()
                    print(f"\n💾 Progress saved at {i} companies")
                
            except KeyboardInterrupt:
                print(f"\n\n⚠️  Interrupted at company {i}. Saving progress...")
                break
            except Exception as e:
                print(f"\n❌ Failed to profile {company}: {e}")
                self.failed_companies.append(company)
                continue
        
        self.save_final_results()
    
    def save_progress(self):
        """Save current progress to file"""
        output_file = Path('data/company_profiles_v2_progress.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'companies': self.companies_data,
                'failed_companies': self.failed_companies,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
    
    def save_final_results(self):
        """Save comprehensive results for ML training"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON format
        json_file = Path(f'data/company_profiles_v2_{timestamp}.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'companies': self.companies_data,
                'failed_companies': self.failed_companies,
                'total_companies': len(self.companies_data),
                'failed_count': len(self.failed_companies),
                'timestamp': datetime.now().isoformat(),
                'version': '2.0'
            }, f, indent=2, ensure_ascii=False)
        
        # ML Training TXT format - concatenated text for each company
        txt_file = Path(f'data/company_training_data_{timestamp}.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("SHIPPING COMPANY ML TRAINING DATA\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Companies: {len(self.companies_data)}\n")
            f.write(f"For: WASP Fit Score Prediction Model\n")
            f.write("=" * 100 + "\n\n")
            
            for company_name, profile in self.companies_data.items():
                f.write("\n" + "=" * 100 + "\n")
                f.write(f"COMPANY: {company_name}\n")
                f.write("=" * 100 + "\n\n")
                
                # Wikipedia extract
                wiki_data = profile['data_sources'].get('wikipedia', {})
                if 'extract' in wiki_data:
                    f.write("--- WIKIPEDIA ---\n")
                    f.write(wiki_data['extract'] + "\n\n")
                
                # Website crawl data
                crawl_data = profile['data_sources'].get('website_crawl', {})
                if 'pages' in crawl_data:
                    f.write(f"--- WEBSITE CONTENT ({len(crawl_data['pages'])} pages) ---\n")
                    for page in crawl_data['pages']:
                        f.write(f"\n[{page['url']}]\n")
                        f.write(page['text'] + "\n")
                
                f.write("\n")
        
        print(f"\n\n{'='*80}")
        print(f"✅ Results saved:")
        print(f"  📄 JSON:     {json_file}")
        print(f"  📝 Training: {txt_file}")
        print(f"  📊 Companies: {len(self.companies_data)}")
        print(f"  ❌ Failed:    {len(self.failed_companies)}")
        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced Company Profiler v2 - ML Training Data Collection"
    )
    parser.add_argument(
        "--max-companies", type=int, default=5,
        help="Maximum number of companies to process (default: 5)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--max-pages-per-site", type=int, default=15,
        help="Maximum pages to crawl per website (default: 15)"
    )
    parser.add_argument(
        "--company", type=str,
        help="Filter: only process companies containing this substring"
    )
    parser.add_argument(
        "--start-from", type=int, default=0,
        help="Skip first N companies (resume from specific position)"
    )
    parser.add_argument(
        "--use-browser", action="store_true",
        help="Use Playwright browser for JavaScript-heavy sites (slower)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🚢 COMPANY PROFILER V2 - ML TRAINING DATA COLLECTION")
    print("=" * 80)
    print("\n📌 Purpose: Gather company data for WASP fit score ML model")
    print(f"⚙️  Settings:")
    print(f"   - Max companies: {args.max_companies}")
    print(f"   - Max pages/site: {args.max_pages_per_site}")
    print(f"   - Use browser: {args.use_browser}")
    print(f"   - Verbose: {args.verbose}")
    if args.company:
        print(f"   - Filter: '{args.company}'")
    if args.start_from:
        print(f"   - Start from: #{args.start_from + 1}")
    
    print("\n⚠️  Note: This may take several hours. Press Ctrl+C to save and exit.")
    print()

    profiler = CompanyProfilerV2(
        verbose=args.verbose, 
        max_pages_per_site=args.max_pages_per_site,
        use_browser=args.use_browser
    )
    
    profiler.profile_all_companies(
        max_companies=args.max_companies, 
        company_filter=args.company,
        start_from=args.start_from
    )


if __name__ == "__main__":
    main()
