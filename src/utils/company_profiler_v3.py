#!/usr/bin/env python3
"""
Enhanced Company Profiler v3 - ML-Ready Structured Data
Addresses V2 weaknesses: adds labels, structure, and preprocessing
"""

import sqlite3
import requests
import json
import os
import time
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup

# Optional Gemini (for official website resolution)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except Exception:
    genai = None
    GEMINI_AVAILABLE = False

import random
from typing import Dict, List, Any

# Fix Windows console encoding
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Try importing optional dependencies
try:
    from googlesearch import search as google_search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    print("⚠️  googlesearch-python not installed.")


class CompanyProfilerV3:
    """Enhanced profiler with structured data and ML-ready preprocessing"""
    
    # Common boilerplate phrases to remove
    BOILERPLATE_PATTERNS = [
        r'\bRead more\b',
        r'\bLearn more\b',
        r'\bClick here\b',
        r'\bGet started\b',
        r'\bContact us\b',
        r'\bSign up\b',
        r'\bSubscribe\b',
        r'\bDownload\b',
        r'\bView all\b',
        r'\bSee more\b',
        r'\bExplore\b',
        r'\bDiscover\b',
        r'\bFind out\b',
        r'\bReady to.*\?',
        r'\bStart your journey\b',
        r'\bBook now\b',
        r'\bGet a quote\b',
        r'\bRequest.*quote\b',
    ]
    
    # Company type classification keywords
    COMPANY_TYPES = {
        'container_carrier': ['container', 'cma cgm', 'maersk', 'msc', 'hapag', 'cosco', 'evergreen', 'yang ming', 'one line'],
        'tanker_operator': ['tanker', 'stolt', 'teekay', 'norden', 'euronav', 'frontline', 'crude', 'chemical tanker'],
        'bulk_carrier': ['bulk', 'oldendorff', 'star bulk', 'dry bulk', 'coal', 'iron ore', 'grain'],
        'ship_management': ['ship management', 'fleet management', 'technical management', 'crew management', 'synergy', 'columbia', 'anglo eastern'],
        'ro_ro_vehicle': ['ro-ro', 'car carrier', 'vehicle', 'wallenius', 'höegh', 'eukor', 'automotive'],
        'passenger_ferry': ['passenger', 'ferry', 'cruise', 'grimaldi', 'stena'],
        'offshore': ['offshore', 'subsea', 'seismic', 'oil rig', 'wind farm'],
        'specialized': ['heavy lift', 'project cargo', 'breakbulk', 'multipurpose', 'spliethoff', 'bbc chartering'],
    }
    
    def __init__(self, verbose: bool = False, max_pages_per_site: int = 10):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.companies_data = {}
        self.verbose = verbose
        self.max_pages_per_site = max_pages_per_site
        
        # Faster rate limiting
        self.min_delay = 1.0
        self.max_delay = 2.0
    
    def get_companies_with_metadata(self):
        """Extract companies WITH structured attributes from database"""
        conn = sqlite3.connect('data/vessel_static_data.db')
        cursor = conn.cursor()
        
        # Get company metadata: vessel count, avg emissions, ship types
        cursor.execute('''
            SELECT 
                company_name,
                COUNT(*) as vessel_count,
                AVG(total_co2_emissions) as avg_emissions,
                AVG(avg_co2_per_distance) as avg_co2_distance,
                AVG(technical_efficiency) as avg_efficiency,
                GROUP_CONCAT(DISTINCT ship_type) as ship_types,
                AVG(CAST(econowind_fit_score AS FLOAT)) as avg_wasp_score
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
                'avg_co2_distance': row[3],
                'avg_efficiency': row[4],
                'ship_types': row[5].split(',') if row[5] else [],
                'avg_wasp_score': row[6]
            })
        
        conn.close()
        return companies
    
    def classify_company_type(self, company_name: str, ship_types: List[str]) -> List[str]:
        """Classify company into categories based on name and ship types"""
        company_lower = company_name.lower()
        ship_types_str = ' '.join(ship_types).lower()
        
        categories = []
        for category, keywords in self.COMPANY_TYPES.items():
            for keyword in keywords:
                if keyword in company_lower or keyword in ship_types_str:
                    categories.append(category)
                    break
        
        return categories if categories else ['general_shipping']
    
    def _delay(self):
        """Random delay to respect rate limits"""
        delay = random.uniform(self.min_delay, self.max_delay)
        if self.verbose:
            print(f"    ⏳ {delay:.1f}s...")
        time.sleep(delay)
    
    def _clean_text_advanced(self, text: str) -> str:
        """Advanced text cleaning - remove boilerplate, normalize, deduplicate"""
        if not text:
            return ""
        
        # Fix encoding issues
        text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII
        
        # Remove boilerplate phrases
        for pattern in self.BOILERPLATE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove URLs
        text = re.sub(r'https?://[^\s]+', '', text)
        text = re.sub(r'www\.[^\s]+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove repeated whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Split into lines and clean
        lines = text.split('\n')
        clean_lines = []
        seen_lines = set()
        
        for line in lines:
            line = line.strip()
            
            # Skip empty, too short, or duplicate lines
            if len(line) < 10 or line in seen_lines:
                continue
            
            # Skip lines with too many special chars
            alpha_ratio = sum(c.isalpha() or c.isspace() for c in line) / max(len(line), 1)
            if alpha_ratio < 0.6:
                continue
            
            # Skip navigation/menu items (short lines with common words)
            if len(line) < 50 and any(word in line.lower() for word in ['home', 'menu', 'search', 'login', 'register', 'about us', 'contact']):
                continue
            
            clean_lines.append(line)
            seen_lines.add(line)
        
        # Join and limit length
        cleaned = ' '.join(clean_lines)
        
        # Remove consecutive duplicate sentences
        sentences = cleaned.split('. ')
        unique_sentences = []
        prev_sentence = ""
        for sent in sentences:
            if sent != prev_sentence:
                unique_sentences.append(sent)
                prev_sentence = sent
        
        return '. '.join(unique_sentences)[:5000]  # Limit to 5K chars
    
    def _get_wikipedia_summary(self, company_name: str) -> Dict[str, Any]:
        """Get clean Wikipedia summary (intro only)"""
        try:
            search_url = "https://en.wikipedia.org/w/api.php"
            search_queries = [
                f"{company_name} shipping",
                f"{company_name} maritime",
                company_name
            ]
            
            for query in search_queries:
                params = {
                    'action': 'opensearch',
                    'search': query,
                    'limit': 3,
                    'namespace': 0,
                    'format': 'json'
                }
                
                response = self.session.get(search_url, params=params, timeout=10)
                data = response.json()
                
                if data[1]:
                    for i, title in enumerate(data[1]):
                        if not any(word in title.lower() for word in ['hijacking', 'incident', 'disaster', 'sinking']):
                            page_title = title
                            
                            # Get INTRO ONLY (not full article)
                            extract_params = {
                                'action': 'query',
                                'titles': page_title,
                                'prop': 'extracts',
                                'exintro': True,  # Intro only
                                'explaintext': True,
                                'exsentences': 5,  # First 5 sentences
                                'format': 'json'
                            }
                            
                            response = self.session.get(search_url, params=extract_params, timeout=10)
                            page_data = response.json()
                            pages = page_data.get('query', {}).get('pages', {})
                            page_info = list(pages.values())[0]
                            
                            extract = page_info.get('extract', '')
                            if extract and len(extract) > 100:
                                return {
                                    'title': page_title,
                                    'summary': extract[:1000],  # Max 1000 chars
                                    'source': 'wikipedia'
                                }
            
            return {'error': 'not_found'}
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_official_website_from_wikidata(self, company_name: str) -> str | None:
        """Try to resolve the official website via Wikipedia->Wikidata (P856).

        This avoids bad domain guesses (e.g., SMT -> Sports Media Tech instead of shipping).
        Returns a base URL like https://example.com or None.
        """
        try:
            # 1) Find best Wikipedia page
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {
                'action': 'opensearch',
                'search': company_name,
                'limit': 1,
                'namespace': 0,
                'format': 'json'
            }
            r = self.session.get(search_url, params=params, timeout=10)
            data = r.json()
            if not data or len(data) < 2 or not data[1]:
                return None
            title = data[1][0]

            # 2) Get Wikidata QID from pageprops
            params2 = {
                'action': 'query',
                'prop': 'pageprops',
                'titles': title,
                'format': 'json'
            }
            r2 = self.session.get(search_url, params=params2, timeout=10)
            j2 = r2.json()
            pages = (j2.get('query') or {}).get('pages') or {}
            page = next(iter(pages.values()), {})
            qid = ((page.get('pageprops') or {}).get('wikibase_item'))
            if not qid:
                return None

            # 3) Fetch Wikidata entity JSON
            wd_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
            r3 = self.session.get(wd_url, timeout=10)
            j3 = r3.json()
            entity = ((j3.get('entities') or {}).get(qid) or {})
            claims = entity.get('claims') or {}
            p856 = claims.get('P856')  # official website
            if not p856:
                return None
            dv = p856[0].get('mainsnak', {}).get('datavalue', {}).get('value')
            if not dv or not isinstance(dv, str):
                return None
            return dv.strip().rstrip('/')
        except Exception:
            return None

    def _looks_like_correct_company_site(self, company_name: str, text: str) -> bool:
        """Heuristic validation to reject obviously wrong websites."""
        if not text:
            return False

        low = text.lower()
        # obvious wrong-industry signals we saw in the wild
        wrong_signals = ['sports', 'tennis', 'nfl', 'nhl', 'mlb', 'pga', 'fans', 'tournament']
        if any(w in low for w in wrong_signals):
            return False

        # require at least one maritime/shipping keyword to reduce false matches
        maritime = ['shipping', 'maritime', 'vessel', 'fleet', 'cargo', 'tanker', 'bulk', 'ship', 'logistics', 'offshore']
        maritime_hits = sum(1 for k in maritime if k in low)
        if maritime_hits == 0:
            return False

        # also require that at least one meaningful token from company name appears
        tokens = [t for t in re.split(r'[^a-z0-9]+', company_name.lower()) if len(t) >= 3]
        token_hits = sum(1 for t in set(tokens) if t in low)
        return token_hits >= 1


    def _search_duckduckgo_html(self, query: str, timeout: int = 20) -> list[str]:
        """Lightweight DuckDuckGo HTML search (often works when other sources fail)."""
        try:
            from urllib.parse import quote
            url = f"https://duckduckgo.com/html/?q={quote(query)}"
            resp = self.session.get(url, timeout=timeout)
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, 'html.parser')
            urls = []
            for a in soup.find_all('a', class_='result__a', limit=8):
                href = a.get('href')
                if href and href.startswith('http'):
                    urls.append(href)
            return urls
        except Exception:
            return []

    def _pick_official_site_from_search(self, company_name: str, candidate_urls: list[str]) -> str | None:
        """Pick a likely official homepage from search results using our validation heuristic."""
        for url in candidate_urls:
            try:
                # normalize to scheme://netloc
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    continue
                base = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')

                # skip obvious non-official sources
                if any(x in base.lower() for x in ['linkedin.com', 'facebook.com', 'twitter.com', 'wikipedia.org', 'crunchbase.com']):
                    continue

                r = self.session.get(base, timeout=10, allow_redirects=True)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'button', 'iframe', 'svg']):
                    tag.decompose()
                txt = soup.get_text(separator=' ', strip=True)
                cleaned = self._clean_text_advanced(txt)
                if self._looks_like_correct_company_site(company_name, cleaned):
                    return r.url.rstrip('/')
            except Exception:
                continue
        return None

    def _discover_internal_key_links(self, base_url: str) -> list[str]:
        """Discover internal links that look like About/Mission/Sustainability pages."""
        try:
            r = self.session.get(base_url, timeout=10, allow_redirects=True)
            if r.status_code != 200:
                return []
            soup = BeautifulSoup(r.text, 'html.parser')
            links = set()
            keywords = ['about', 'company', 'our-story', 'mission', 'values', 'sustainability', 'esg', 'environment']

            for a in soup.find_all('a', href=True):
                href = a.get('href')
                if not href:
                    continue
                href, _ = urldefrag(href)
                abs_url = urljoin(r.url, href)
                if not abs_url.startswith('http'):
                    continue
                # same site only
                if urlparse(abs_url).netloc != urlparse(r.url).netloc:
                    continue
                low = abs_url.lower()
                if any(k in low for k in keywords):
                    links.add(abs_url.rstrip('/'))

            # return a small prioritized set
            return sorted(list(links))[:12]
        except Exception:
            return []


    def _website_cache_path(self) -> Path:
        """Path to JSON cache for company->official website mapping (gitignored via data/)."""
        return Path('data') / 'company_official_websites_cache.json'

    def _load_website_cache(self) -> dict:
        try:
            p = self._website_cache_path()
            if p.exists():
                return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
        return {}

    def _save_website_cache(self, cache: dict) -> None:
        try:
            p = self._website_cache_path()
            p.parent.mkdir(exist_ok=True)
            p.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception:
            pass

    def _read_gemini_key_for_websites(self) -> str | None:
        """Prefer WASP key file if present; otherwise general gemini key. Env var overrides."""
        env_key = os.environ.get('GEMINI_API_KEY')
        if env_key:
            return env_key.strip()

        # Prefer dedicated WASP key if present (works for both, but lets you separate quotas)
        key_files = [
            Path('config') / 'gemini_api_key_wasp.txt',
            Path('config') / 'gemini_api_key.txt',
        ]
        for k in key_files:
            try:
                if k.exists():
                    val = k.read_text().strip()
                    if val and val != 'your-api-key-here':
                        return val
            except Exception:
                continue
        return None

    def _resolve_official_website_with_gemini(self, company_name: str) -> str | None:
        """Ask Gemini for the official website (cached). Returns base URL or None."""
        if not GEMINI_AVAILABLE:
            return None

        key = self._read_gemini_key_for_websites()
        if not key:
            return None

        cache = self._load_website_cache()
        cached = cache.get(company_name)
        if isinstance(cached, dict) and cached.get('official_website'):
            return str(cached['official_website']).rstrip('/')

        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-2.0-flash')

            prompt = f"""
Return the official website URL for this shipping/maritime company.

Company name: {company_name}

Rules:
- Return ONLY valid JSON.
- Must be the company's official website homepage (not LinkedIn, not Wikipedia, not a news site).
- If you are unsure, return null.

JSON schema:
{{
  \"official_website\": \"https://example.com\" | null
}}
""".strip()

            resp = model.generate_content(prompt)
            raw = (resp.text or '').strip()
            # strip code fences if any
            if '```' in raw:
                raw = raw.split('```')[1]
                raw = raw.split('```')[0].strip()

            data = json.loads(raw)
            url = data.get('official_website')
            if not url or not isinstance(url, str):
                cache[company_name] = {
                    'official_website': None,
                    'source': 'gemini',
                    'timestamp': datetime.now().isoformat(),
                }
                self._save_website_cache(cache)
                return None

            url = url.strip().rstrip('/')
            if not url.startswith('http'):
                return None

            # Reject obvious non-officials
            if any(x in url.lower() for x in ['linkedin.com', 'facebook.com', 'twitter.com', 'wikipedia.org']):
                return None

            # Verify homepage content matches company
            try:
                r = self.session.get(url, timeout=10, allow_redirects=True)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'button', 'iframe', 'svg']):
                        tag.decompose()
                    txt = soup.get_text(separator=' ', strip=True)
                    cleaned = self._clean_text_advanced(txt)
                    if not self._looks_like_correct_company_site(company_name, cleaned):
                        return None
                    url = r.url.rstrip('/')
            except Exception:
                # If verification fails, don't cache as valid
                return None

            cache[company_name] = {
                'official_website': url,
                'source': 'gemini',
                'timestamp': datetime.now().isoformat(),
            }
            self._save_website_cache(cache)
            return url

        except Exception:
            # quota / 429 / parsing issues -> just fall back
            return None



    def _crawl_website_key_pages(self, company_name: str) -> Dict[str, Any]:
        """Crawl ONLY key pages: About/Mission/Values/Sustainability (official site)."""
        try:
            # 1) Resolve official website with best-effort order
            official = self._resolve_official_website_with_gemini(company_name)
            if not official:
                official = self._get_official_website_from_wikidata(company_name)

            base_urls = []
            if official:
                base_urls = [official.rstrip('/')]
            else:
                # Known companies
                known_domains = {
                    'maersk': 'https://www.maersk.com',
                    'msc': 'https://www.msc.com',
                    'cma': 'https://www.cma-cgm.com',
                    'cosco': 'https://www.cosco-shipping.com',
                }
                for key, url in known_domains.items():
                    if key in company_name.lower():
                        base_urls = [url]
                        break

            # 2) DuckDuckGo HTML fallback if still unknown
            if not base_urls:
                ddg_urls = self._search_duckduckgo_html(f"{company_name} shipping company official website")
                picked = self._pick_official_site_from_search(company_name, ddg_urls)
                if picked:
                    base_urls = [picked]

            # 3) Last resort: domain guess
            if not base_urls:
                domain_guess = company_name.lower().split()[0].replace('.', '').replace(',', '')
                base_urls = [f"https://www.{domain_guess}.com", f"https://{domain_guess}.com"]

            # Key page paths to try
            key_paths = [
                '/',
                '/about',
                '/about-us',
                '/company',
                '/our-company',
                '/our-story',
                '/mission',
                '/values',
                '/sustainability',
                '/environment',
                '/esg',
            ]

            pages_data = []

            for base_url in base_urls[:1]:
                # internal discovery (helps many sites)
                discovered = self._discover_internal_key_links(base_url)

                fetch_targets = []
                for path in key_paths:
                    fetch_targets.append(base_url.rstrip('/') + path)
                for u in discovered:
                    if u not in fetch_targets:
                        fetch_targets.append(u)

                for url in fetch_targets[:self.max_pages_per_site]:
                    try:
                        resp = self.session.get(url, timeout=10, allow_redirects=True)
                        if resp.status_code != 200:
                            continue

                        soup = BeautifulSoup(resp.text, 'html.parser')
                        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside',
                                        'form', 'button', 'iframe', 'svg']):
                            tag.decompose()

                        text = soup.get_text(separator=' ', strip=True)
                        cleaned = self._clean_text_advanced(text)

                        if len(cleaned) > 200:
                            if not self._looks_like_correct_company_site(company_name, cleaned):
                                continue
                            pages_data.append({
                                'page_type': (urlparse(resp.url).path.strip('/') or 'home') if resp.url else (urlparse(url).path.strip('/') or 'home'),
                                'url': resp.url or url,
                                'text': cleaned[:2000],
                                'length': len(cleaned),
                            })

                        self._delay()

                    except Exception:
                        continue

                if pages_data:
                    break

            if pages_data:
                return {
                    'pages': pages_data,
                    'pages_count': len(pages_data),
                    'source': 'website_crawl',
                }

            return {'error': 'no_pages_found'}

        except Exception as e:
            return {'error': str(e)}


    def profile_company_structured(self, company_meta: Dict) -> Dict[str, Any]:
        """Create ML-ready structured profile"""
        company_name = company_meta['name']
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"📊 {company_name} (Fleet: {company_meta['vessel_count']} vessels)")
            print(f"{'='*80}")
        
        # Classify company type
        categories = self.classify_company_type(company_name, company_meta['ship_types'])
        
        # Initialize structured profile
        profile = {
            'company_name': company_name,
            'timestamp': datetime.now().isoformat(),
            
            # STRUCTURED ATTRIBUTES (from database)
            'attributes': {
                'vessel_count': company_meta['vessel_count'],
                'avg_emissions_tons': round(company_meta['avg_emissions'], 2) if company_meta['avg_emissions'] else None,
                'avg_co2_per_distance': round(company_meta['avg_co2_distance'], 2) if company_meta['avg_co2_distance'] else None,
                'avg_technical_efficiency': round(company_meta['avg_efficiency'], 2) if company_meta['avg_efficiency'] else None,
                'avg_wasp_fit_score': round(company_meta['avg_wasp_score'], 2) if company_meta['avg_wasp_score'] else None,
                'primary_ship_types': list(set(company_meta['ship_types']))[:5],  # Top 5 unique types
            },
            
            # LABELS (ML categories)
            'labels': {
                'company_categories': categories,
                'fleet_size_category': self._categorize_fleet_size(company_meta['vessel_count']),
                'emissions_category': self._categorize_emissions(company_meta['avg_co2_distance']),
            },
            
            # TEXT DATA (separated by source)
            'text_data': {
                'wikipedia': {},
                'website': {}
            }
        }
        
        # Get Wikipedia summary
        if self.verbose:
            print("  🔍 Wikipedia...")
        wiki_data = self._get_wikipedia_summary(company_name)
        if 'summary' in wiki_data:
            profile['text_data']['wikipedia'] = {
                'summary': wiki_data['summary'],
                'title': wiki_data.get('title', ''),
                'length': len(wiki_data['summary'])
            }
            if self.verbose:
                print(f"    ✅ {len(wiki_data['summary'])} chars")
        else:
            if self.verbose:
                print(f"    ❌ Not found")
        
        self._delay()
        
        # Get website content
        if self.verbose:
            print("  🔍 Website...")
        website_data = self._crawl_website_key_pages(company_name)
        if 'pages' in website_data:
            profile['text_data']['website'] = {
                'pages': website_data['pages'],
                'pages_count': website_data['pages_count'],
                'total_length': sum(p['length'] for p in website_data['pages'])
            }
            if self.verbose:
                print(f"    ✅ {website_data['pages_count']} pages, {profile['text_data']['website']['total_length']} chars")
        else:
            if self.verbose:
                print(f"    ❌ Failed")
        
        return profile
    
    def _categorize_fleet_size(self, count: int) -> str:
        """Categorize fleet size"""
        if count >= 100:
            return 'large'
        elif count >= 20:
            return 'medium'
        else:
            return 'small'
    
    def _categorize_emissions(self, co2_per_distance) -> str:
        """Categorize emissions level"""
        if not co2_per_distance:
            return 'unknown'
        if co2_per_distance < 5:
            return 'low'
        elif co2_per_distance < 10:
            return 'medium'
        else:
            return 'high'
    
    def profile_batch(self, max_companies: int = 5, start_from: int = 0):
        """Profile multiple companies with structured output"""
        companies = self.get_companies_with_metadata()
        
        print(f"\n{'='*80}")
        print(f"📋 Found {len(companies)} companies with metadata")
        print(f"{'='*80}")
        
        if start_from > 0:
            companies = companies[start_from:]
        
        companies = companies[:max_companies]
        print(f"📌 Processing {len(companies)} companies")
        
        for i, company_meta in enumerate(companies, start_from + 1):
            try:
                profile = self.profile_company_structured(company_meta)
                self.companies_data[company_meta['name']] = profile
                
            except Exception as e:
                print(f"\n❌ Failed: {company_meta['name']}: {e}")
                continue
        
        self.save_structured_results()
    
    def save_structured_results(self):
        """Save ML-ready structured JSON and training CSV"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Structured JSON (for feature engineering)
        json_file = Path(f'data/company_profiles_v3_structured_{timestamp}.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'companies': self.companies_data,
                'total': len(self.companies_data),
                'timestamp': datetime.now().isoformat(),
                'version': '3.0',
                'schema': {
                    'attributes': 'Structured numerical/categorical features',
                    'labels': 'ML classification labels',
                    'text_data': 'Separated text sources for embeddings'
                }
            }, f, indent=2, ensure_ascii=False)
        
        # 2. ML Training TXT (separated sources, no mixing)
        txt_file = Path(f'data/company_training_v3_{timestamp}.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("="*100 + "\n")
            f.write("COMPANY PROFILES V3 - ML-READY STRUCTURED DATA\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Companies: {len(self.companies_data)}\n")
            f.write("="*100 + "\n\n")
            
            for company_name, profile in self.companies_data.items():
                f.write(f"\n{'='*100}\n")
                f.write(f"COMPANY: {company_name}\n")
                f.write(f"{'='*100}\n\n")
                
                # Structured attributes
                f.write("--- ATTRIBUTES ---\n")
                attrs = profile['attributes']
                f.write(f"Fleet Size: {attrs['vessel_count']} vessels\n")
                if attrs['avg_emissions_tons']:
                    f.write(f"Avg Emissions: {attrs['avg_emissions_tons']:.2f} tons CO2\n")
                if attrs['avg_wasp_fit_score']:
                    f.write(f"Avg WASP Fit Score: {attrs['avg_wasp_fit_score']:.2f}/10\n")
                f.write(f"Ship Types: {', '.join(attrs['primary_ship_types'][:3])}\n\n")
                
                # Labels
                f.write("--- LABELS ---\n")
                labels = profile['labels']
                f.write(f"Categories: {', '.join(labels['company_categories'])}\n")
                f.write(f"Fleet Size: {labels['fleet_size_category']}\n")
                f.write(f"Emissions: {labels['emissions_category']}\n\n")
                
                # Wikipedia (separate section)
                wiki = profile['text_data'].get('wikipedia', {})
                if wiki.get('summary'):
                    f.write("--- WIKIPEDIA SUMMARY ---\n")
                    f.write(wiki['summary'] + "\n\n")
                
                # Website (separate section, by page type)
                website = profile['text_data'].get('website', {})
                if website.get('pages'):
                    f.write(f"--- WEBSITE CONTENT ({website['pages_count']} pages) ---\n")
                    for page in website['pages']:
                        f.write(f"\n[{page['page_type'].upper()}]\n")
                        f.write(page['text'] + "\n")
        
        print(f"\n{'='*80}")
        print(f"✅ V3 STRUCTURED DATA SAVED:")
        print(f"  📄 JSON:     {json_file}")
        print(f"  📝 Training: {txt_file}")
        print(f"  📊 Companies: {len(self.companies_data)}")
        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Company Profiler V3 - ML-Ready Structured Data"
    )
    parser.add_argument("--max-companies", type=int, default=5)
    parser.add_argument("--start-from", type=int, default=0)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--max-pages", type=int, default=6, 
                       help="Max key pages to crawl (default: 6)")
    
    args = parser.parse_args()
    
    print("="*80)
    print("🚢 COMPANY PROFILER V3 - ML-READY STRUCTURED DATA")
    print("="*80)
    print("\n✨ NEW FEATURES:")
    print("  ✅ Structured attributes from database")
    print("  ✅ ML classification labels")
    print("  ✅ Separated text sources (no mixing)")
    print("  ✅ Advanced text preprocessing")
    print("  ✅ Boilerplate removal")
    print("  ✅ Shorter, cleaner output")
    print()
    
    profiler = CompanyProfilerV3(
        verbose=args.verbose,
        max_pages_per_site=args.max_pages
    )
    
    profiler.profile_batch(
        max_companies=args.max_companies,
        start_from=args.start_from
    )


if __name__ == "__main__":
    main()
