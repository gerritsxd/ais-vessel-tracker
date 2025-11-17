"""
Browser-based Gross Tonnage Scraper
Uses Playwright with Chromium to scrape GT from search results without visiting individual pages.
More efficient and less detectable than direct HTTP requests.
"""

import sqlite3
import asyncio
from playwright.async_api import async_playwright
import time
from pathlib import Path
from datetime import datetime
import re
import json

DB_NAME = "vessel_static_data.db"
CHECK_INTERVAL = 86400  # 24 hours
BATCH_SIZE = 50  # Smaller batch for browser scraping (more resource intensive)
REQUESTS_PER_MINUTE = 5  # Conservative rate limit for browser
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE  # 12 seconds
REQUEST_TIMEOUT = 30  # 30 second timeout per search

# Cache file to track scraping attempts
CACHE_FILE = "gt_scraper_browser_cache.json"


class BrowserGTScraper:
    """Browser-based GT scraper using Playwright."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.running = False
        self.stats = {
            'total_scraped': 0,
            'successful': 0,
            'failed': 0,
            'already_had_gt': 0,
            'last_run': None
        }
        self.cache = self.load_cache()
        self.browser = None
        self.context = None
    
    def load_cache(self):
        """Load cache of previously attempted scrapes."""
        try:
            project_root = Path(__file__).parent.parent.parent
            cache_path = project_root / CACHE_FILE
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache: {e}")
        return {'failed_imos': {}, 'last_attempt': {}}
    
    def save_cache(self):
        """Save cache to file."""
        try:
            project_root = Path(__file__).parent.parent.parent
            cache_path = project_root / CACHE_FILE
            cache_path.parent.mkdir(exist_ok=True)
            with open(cache_path, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
    
    def get_connection(self):
        """Get database connection with timeout."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    
    def get_vessels_without_gt(self):
        """Get vessels that need GT data, excluding recently failed attempts."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get vessels with IMO but no GT
            cursor.execute('''
                SELECT e.imo, v.mmsi, v.name
                FROM eu_mrv_emissions e
                LEFT JOIN vessels_static v ON e.imo = v.imo
                WHERE e.imo IS NOT NULL 
                  AND e.imo > 0
                  AND (e.gross_tonnage IS NULL OR e.gross_tonnage = 0)
                ORDER BY RANDOM()
                LIMIT ?
            ''', (BATCH_SIZE * 3,))  # Get 3x batch size to filter out failed attempts
            
            all_vessels = cursor.fetchall()
            
            # Filter out vessels that failed recently (within last 7 days)
            current_time = datetime.now().timestamp()
            week_ago = current_time - (7 * 86400)
            
            filtered_vessels = []
            for imo, mmsi, name in all_vessels:
                imo_str = str(imo)
                last_fail = self.cache.get('failed_imos', {}).get(imo_str, 0)
                
                # Skip if failed within last week
                if last_fail > week_ago:
                    continue
                
                filtered_vessels.append((imo, mmsi, name))
                
                if len(filtered_vessels >= BATCH_SIZE):
                    break
            
            return filtered_vessels
            
        finally:
            if conn:
                conn.close()
    
    async def init_browser(self):
        """Initialize browser with stealth settings."""
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',  # Faster loading
                    '--disable-javascript',  # We only need static content
                ]
            )
            
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
    
    async def scrape_gt_from_marinetraffic_search(self, imo):
        """
        Scrape GT from MarineTraffic search results page.
        Uses Google search to find MarineTraffic page and extracts GT from search results.
        """
        try:
            page = await self.context.new_page()
            
            # Use Google search to find the vessel
            search_query = f"site:marinetraffic.com {imo} gross tonnage"
            await page.goto(f"https://www.google.com/search?q={search_query}", timeout=REQUEST_TIMEOUT)
            
            # Wait for results to load
            await page.wait_for_timeout(2000)
            
            # Get page content
            content = await page.content()
            
            # Look for GT in search results
            gt_patterns = [
                r'Gross Tonnage[:\s]+(\d+(?:,\d+)*)',
                r'GT[:\s]+(\d+(?:,\d+)*)',
                r'Tonnage[:\s]+(\d+(?:,\d+)*)',
            ]
            
            for pattern in gt_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    gt_str = match.group(1).replace(',', '')
                    try:
                        gt_value = int(gt_str)
                        if 100 <= gt_value <= 500000:  # Sanity check
                            await page.close()
                            return gt_value
                    except ValueError:
                        continue
            
            # If not found in search snippets, try to click the first result and extract from snippet
            try:
                first_result = await page.query_selector('h3')
                if first_result:
                    await first_result.click()
                    await page.wait_for_timeout(3000)
                    
                    # Extract from the page content
                    page_content = await page.content()
                    for pattern in gt_patterns:
                        match = re.search(pattern, page_content, re.IGNORECASE)
                        if match:
                            gt_str = match.group(1).replace(',', '')
                            try:
                                gt_value = int(gt_str)
                                if 100 <= gt_value <= 500000:
                                    await page.close()
                                    return gt_value
                            except ValueError:
                                continue
            except:
                pass
            
            await page.close()
            return None
            
        except Exception as e:
            print(f"    MarineTraffic search error for IMO {imo}: {e}")
            try:
                await page.close()
            except:
                pass
            return None
    
    async def scrape_gt_from_vesselfinder_search(self, imo):
        """
        Scrape GT from VesselFinder search results.
        Uses Google search to find VesselFinder page and extracts GT from search results.
        """
        try:
            page = await self.context.new_page()
            
            # Use Google search to find the vessel
            search_query = f"site:vesselfinder.com {imo} gross tonnage"
            await page.goto(f"https://www.google.com/search?q={search_query}", timeout=REQUEST_TIMEOUT)
            
            # Wait for results to load
            await page.wait_for_timeout(2000)
            
            # Get page content
            content = await page.content()
            
            # Look for GT in search results
            gt_patterns = [
                r'Gross tonnage[:\s]+(\d+(?:,\d+)*)',
                r'GT[:\s]+(\d+(?:,\d+)*)',
            ]
            
            for pattern in gt_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    gt_str = match.group(1).replace(',', '')
                    try:
                        gt_value = int(gt_str)
                        if 100 <= gt_value <= 500000:
                            await page.close()
                            return gt_value
                    except ValueError:
                        continue
            
            await page.close()
            return None
            
        except Exception as e:
            print(f"    VesselFinder search error for IMO {imo}: {e}")
            try:
                await page.close()
            except:
                pass
            return None
    
    async def scrape_gt(self, imo):
        """
        Try multiple sources to get GT data using browser automation.
        Returns GT value or None.
        """
        # Try MarineTraffic search first
        gt = await self.scrape_gt_from_marinetraffic_search(imo)
        if gt:
            return gt
        
        # Wait a bit before trying next source
        await asyncio.sleep(3)
        
        # Try VesselFinder search as fallback
        gt = await self.scrape_gt_from_vesselfinder_search(imo)
        if gt:
            return gt
        
        return None
    
    def update_gt_in_database(self, imo, gt_value):
        """Update GT value in database."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE eu_mrv_emissions
                SET gross_tonnage = ?
                WHERE imo = ?
            ''', (gt_value, imo))
            
            conn.commit()
            return cursor.rowcount > 0
            
        finally:
            if conn:
                conn.close()
    
    async def run_scraping_batch(self):
        """Run one batch of GT scraping using browser."""
        vessels = self.get_vessels_without_gt()
        
        if not vessels:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No vessels need GT scraping")
            return
        
        print(f"\n{'='*80}")
        print(f"BROWSER GT SCRAPING BATCH - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"Vessels to scrape: {len(vessels)}")
        print(f"Rate limit: {REQUESTS_PER_MINUTE} requests/minute ({DELAY_BETWEEN_REQUESTS:.1f}s delay)")
        print(f"Method: Google search → Extract from search snippets")
        print(f"{'='*80}\n")
        
        # Initialize browser
        await self.init_browser()
        
        for i, (imo, mmsi, name) in enumerate(vessels, 1):
            print(f"[{i}/{len(vessels)}] {name or 'Unknown'} (IMO: {imo})")
            
            # Scrape GT using browser
            gt_value = await self.scrape_gt(imo)
            
            if gt_value:
                # Update database
                if self.update_gt_in_database(imo, gt_value):
                    print(f"  ✓ Success! GT = {gt_value:,}")
                    self.stats['successful'] += 1
                    
                    # Remove from failed cache if present
                    if str(imo) in self.cache.get('failed_imos', {}):
                        del self.cache['failed_imos'][str(imo)]
                else:
                    print(f"  ⚠ Found GT = {gt_value:,} but DB update failed")
            else:
                print(f"  ✗ GT not found")
                self.stats['failed'] += 1
                
                # Add to failed cache
                if 'failed_imos' not in self.cache:
                    self.cache['failed_imos'] = {}
                self.cache['failed_imos'][str(imo)] = datetime.now().timestamp()
            
            self.stats['total_scraped'] += 1
            
            # Rate limiting: wait between requests
            if i < len(vessels):  # Don't wait after last vessel
                print(f"  Waiting {DELAY_BETWEEN_REQUESTS:.1f}s (rate limit)...")
                await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
        
        # Close browser
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        # Save cache
        self.save_cache()
        
        # Print summary
        print(f"\n{'='*80}")
        print("BATCH SUMMARY")
        print(f"{'='*80}")
        print(f"Total processed: {self.stats['total_scraped']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Success rate: {self.stats['successful']/max(self.stats['total_scraped'], 1)*100:.1f}%")
        print(f"{'='*80}\n")
        
        self.stats['last_run'] = datetime.now().isoformat()
    
    async def run_continuous(self):
        """Run the browser scraper continuously in the background."""
        self.running = True
        print("="*80)
        print("BROWSER GROSS TONNAGE SCRAPER - STARTED")
        print("="*80)
        print(f"Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//3600} hours)")
        print(f"Batch size: {BATCH_SIZE} vessels per run")
        print(f"Rate limit: {REQUESTS_PER_MINUTE} requests/minute")
        print(f"Method: Chromium browser + Google search")
        print("="*80 + "\n")
        
        while self.running:
            try:
                await self.run_scraping_batch()
                
                print(f"\nNext scraping run in {CHECK_INTERVAL//3600} hours...")
                print("  " + "-"*76 + "\n")
                
                # Sleep in small intervals to allow graceful shutdown
                for _ in range(CHECK_INTERVAL):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n\nShutting down browser scraper...")
                self.running = False
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
        
        # Clean up browser
        if self.browser:
            await self.browser.close()
        
        print("\nBrowser GT scraper stopped.")
        print(f"Total vessels scraped: {self.stats['total_scraped']}")
        print(f"Successful: {self.stats['successful']}")
    
    def stop(self):
        """Stop the scraper."""
        self.running = False


async def main():
    """Main entry point for browser-based scraper."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        print("Run ais_collector.py first to create the database.")
        return
    
    scraper = BrowserGTScraper(db_path)
    
    try:
        await scraper.run_continuous()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        scraper.stop()


if __name__ == "__main__":
    asyncio.run(main())
