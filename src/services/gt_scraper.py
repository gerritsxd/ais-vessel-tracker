"""
Gross Tonnage Scraper Service
Scrapes GT data for vessels missing this information from public maritime databases.
Runs daily (24h interval) to gradually populate GT values with rate limiting.
"""

import sqlite3
import requests
from bs4 import BeautifulSoup
import time
from pathlib import Path
from datetime import datetime
import re
import json

DB_NAME = "vessel_static_data.db"
CHECK_INTERVAL = 86400  # 24 hours
BATCH_SIZE = 100  # Scrape 100 vessels per day
REQUESTS_PER_MINUTE = 10  # Rate limit: 10 requests per minute (6 seconds between requests)
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE  # 6 seconds
REQUEST_TIMEOUT = 15  # 15 second timeout per request

# Cache file to track scraping attempts
CACHE_FILE = "data/gt_scraper_cache.json"


class GTScraper:
    """Background service to scrape and update Gross Tonnage data."""
    
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
                
                if len(filtered_vessels) >= BATCH_SIZE:
                    break
            
            return filtered_vessels
            
        finally:
            if conn:
                conn.close()
    
    def scrape_gt_from_marinetraffic(self, imo):
        """
        Scrape GT from MarineTraffic using IMO number.
        Returns GT value or None if not found.
        """
        try:
            url = f"https://www.marinetraffic.com/en/ais/details/ships/imo:{imo}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.marinetraffic.com/',
            }
            
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Method 1: Look for "Gross Tonnage" label
                # MarineTraffic typically shows: "Gross Tonnage: 12345"
                text = soup.get_text()
                
                # Try to find GT in various formats
                patterns = [
                    r'Gross Tonnage[:\s]+(\d+(?:,\d+)*)',
                    r'GT[:\s]+(\d+(?:,\d+)*)',
                    r'Tonnage[:\s]+(\d+(?:,\d+)*)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        gt_str = match.group(1).replace(',', '')
                        try:
                            gt_value = int(gt_str)
                            if 100 <= gt_value <= 500000:  # Sanity check
                                return gt_value
                        except ValueError:
                            continue
                
                # Method 2: Look in structured data (JSON-LD)
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and 'tonnage' in str(data).lower():
                            # Try to extract GT from structured data
                            pass
                    except:
                        continue
            
            elif response.status_code == 404:
                print(f"    IMO {imo} not found on MarineTraffic")
            elif response.status_code == 429:
                print(f"    Rate limited! Waiting 60 seconds...")
                time.sleep(60)
            
            return None
            
        except requests.Timeout:
            print(f"    Timeout for IMO {imo}")
            return None
        except Exception as e:
            print(f"    Error scraping IMO {imo}: {e}")
            return None
    
    def scrape_gt_from_vesselfinder(self, imo):
        """
        Scrape GT from VesselFinder as fallback.
        Returns GT value or None if not found.
        """
        try:
            url = f"https://www.vesselfinder.com/vessels/details/{imo}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                text = soup.get_text()
                
                # VesselFinder format
                patterns = [
                    r'Gross tonnage[:\s]+(\d+(?:,\d+)*)',
                    r'GT[:\s]+(\d+(?:,\d+)*)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        gt_str = match.group(1).replace(',', '')
                        try:
                            gt_value = int(gt_str)
                            if 100 <= gt_value <= 500000:
                                return gt_value
                        except ValueError:
                            continue
            
            return None
            
        except Exception as e:
            print(f"    VesselFinder error for IMO {imo}: {e}")
            return None
    
    def scrape_gt(self, imo):
        """
        Try multiple sources to get GT data.
        Returns GT value or None.
        """
        # Try MarineTraffic first (most comprehensive)
        gt = self.scrape_gt_from_marinetraffic(imo)
        if gt:
            return gt
        
        # Wait a bit before trying next source
        time.sleep(2)
        
        # Try VesselFinder as fallback
        gt = self.scrape_gt_from_vesselfinder(imo)
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
    
    def run_scraping_batch(self):
        """Run one batch of GT scraping."""
        vessels = self.get_vessels_without_gt()
        
        if not vessels:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] No vessels need GT scraping")
            return
        
        print(f"\n{'='*80}")
        print(f"GT SCRAPING BATCH - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"Vessels to scrape: {len(vessels)}")
        print(f"Rate limit: {REQUESTS_PER_MINUTE} requests/minute ({DELAY_BETWEEN_REQUESTS:.1f}s delay)")
        print(f"{'='*80}\n")
        
        for i, (imo, mmsi, name) in enumerate(vessels, 1):
            print(f"[{i}/{len(vessels)}] {name or 'Unknown'} (IMO: {imo})")
            
            # Scrape GT
            gt_value = self.scrape_gt(imo)
            
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
                time.sleep(DELAY_BETWEEN_REQUESTS)
        
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
    
    def run_continuous(self):
        """Run the scraper continuously in the background."""
        self.running = True
        print("="*80)
        print("GROSS TONNAGE SCRAPER - STARTED")
        print("="*80)
        print(f"Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//3600} hours)")
        print(f"Batch size: {BATCH_SIZE} vessels per run")
        print(f"Rate limit: {REQUESTS_PER_MINUTE} requests/minute")
        print("="*80 + "\n")
        
        while self.running:
            try:
                self.run_scraping_batch()
                
                print(f"\nNext scraping run in {CHECK_INTERVAL//3600} hours...")
                print("  " + "-"*76 + "\n")
                
                # Sleep in small intervals to allow graceful shutdown
                for _ in range(CHECK_INTERVAL):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n\nShutting down scraper...")
                self.running = False
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(300)  # Wait 5 minutes before retrying
        
        print("\nGT scraper stopped.")
        print(f"Total vessels scraped: {self.stats['total_scraped']}")
        print(f"Successful: {self.stats['successful']}")
    
    def stop(self):
        """Stop the scraper."""
        self.running = False


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / DB_NAME
    
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        print("Run ais_collector.py first to create the database.")
        return
    
    scraper = GTScraper(db_path)
    
    try:
        scraper.run_continuous()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        scraper.stop()


if __name__ == "__main__":
    main()
