"""
Search-Based GT Scraper Service
Uses search engine results to find GT data for vessels, avoiding direct website requests.
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
BATCH_SIZE = 50  # Process 50 vessels per day (search is slower but avoids rate limits)
DELAY_BETWEEN_REQUESTS = 30  # 30 seconds between searches to be safe
REQUEST_TIMEOUT = 20  # 20 second timeout per search

# Cache file to track search attempts
CACHE_FILE = "gt_search_cache.json"


class GTSearchScraper:
    """Search-based GT scraper that uses search engine results."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.running = False
        self.stats = {
            'total_searched': 0,
            'successful': 0,
            'not_found': 0,
            'already_had_gt': 0,
            'last_run': None
        }
        self.cache = self.load_cache()
    
    def load_cache(self):
        """Load cache of previously attempted searches."""
        try:
            project_root = Path(__file__).parent.parent.parent
            cache_path = project_root / CACHE_FILE
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache: {e}")
        return {'failed_mmsi': {}, 'last_attempt': {}}
    
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
            
            # Get vessels from vessels_static table (using MMSI)
            cursor.execute('''
                SELECT mmsi, name, imo, ship_type, length
                FROM vessels_static
                WHERE mmsi IS NOT NULL 
                  AND mmsi > 0
                ORDER BY RANDOM()
                LIMIT ?
            ''', (BATCH_SIZE * 3,))  # Get 3x batch size to filter out failed attempts
            
            all_vessels = cursor.fetchall()
            
            # Filter out vessels that failed recently (within last 7 days)
            current_time = datetime.now().timestamp()
            week_ago = current_time - (7 * 86400)
            
            filtered_vessels = []
            for mmsi, name, imo, ship_type, length in all_vessels:
                mmsi_str = str(mmsi)
                last_fail = self.cache.get('failed_mmsi', {}).get(mmsi_str, 0)
                
                # Skip if failed within last week
                if last_fail > week_ago:
                    continue
                
                filtered_vessels.append((mmsi, name, imo, ship_type, length))
                
                if len(filtered_vessels) >= BATCH_SIZE:
                    break
            
            return filtered_vessels
            
        finally:
            if conn:
                conn.close()
    
    def search_gt_for_mmsi(self, mmsi, vessel_name=None):
        """
        Search for GT data using MMSI number via search engine.
        Returns GT value, "NA" (not available), or "NF" (not found).
        """
        try:
            # Create search queries
            search_queries = [
                f"MMSI {mmsi} gross tonnage",
                f"MMSI {mmsi} GT",
                f"vessel {mmsi} tonnage"
            ]
            
            # Add vessel name to search if available
            if vessel_name and vessel_name.strip():
                search_queries.insert(0, f'"{vessel_name}" MMSI {mmsi} gross tonnage')
            
            # Try DuckDuckGo (more lenient than Google)
            for query in search_queries:
                print(f"    Searching: {query}")
                
                # DuckDuckGo search URL
                search_url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                response = requests.get(search_url, headers=headers, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    gt_value = self.extract_gt_from_search_results(response.text, mmsi)
                    if gt_value:
                        return gt_value
                
                # Small delay between searches
                time.sleep(2)
            
            # If no GT found in any search, mark as not found
            return "NF"
            
        except requests.Timeout:
            print(f"    Timeout searching for MMSI {mmsi}")
            return "NA"
        except Exception as e:
            print(f"    Error searching for MMSI {mmsi}: {e}")
            return "NA"
    
    def extract_gt_from_search_results(self, html_content, mmsi):
        """Extract GT from search result snippets."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text()
            
            # Look for GT patterns in search results
            gt_patterns = [
                # GT: 12345 format
                r'(?:GT|gross tonnage)[:\s]+(\d+(?:,\d+)*)',
                # "12345 gross tonnage"
                r'(\d+(?:,\d+)*)\s*(?:GT|gross tonnage)',
                # MMSI 123456789 - 12345 GT
                rf'MMSI\s*{mmsi}[^0-9]*?(\d+(?:,\d+)*)\s*(?:GT|gross tonnage)',
                # Vessel details patterns
                rf'{mmsi}[^0-9]*?(\d+(?:,\d+)*)\s*(?:GT|gross tonnage)',
            ]
            
            for pattern in gt_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    gt_str = match.replace(',', '')
                    try:
                        gt_value = int(gt_str)
                        if 100 <= gt_value <= 500000:  # Sanity check
                            print(f"    ✓ Found GT: {gt_value}")
                            return gt_value
                    except ValueError:
                        continue
            
            return None
            
        except Exception as e:
            print(f"    Error extracting GT from search results: {e}")
            return None
    
    def update_vessel_gt(self, mmsi, gt_value):
        """Update GT data for a vessel in the database."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if vessel has emissions record
            cursor.execute('''
                SELECT imo FROM eu_mrv_emissions 
                WHERE imo = (SELECT imo FROM vessels_static WHERE mmsi = ?)
            ''', (mmsi,))
            
            emissions_record = cursor.fetchone()
            
            if emissions_record:
                # Update emissions table
                if gt_value in ["NA", "NF"]:
                    cursor.execute('''
                        UPDATE eu_mrv_emissions 
                        SET gross_tonnage = ?, last_updated = ?
                        WHERE imo = (SELECT imo FROM vessels_static WHERE mmsi = ?)
                    ''', (gt_value, datetime.now().isoformat(), mmsi))
                else:
                    cursor.execute('''
                        UPDATE eu_mrv_emissions 
                        SET gross_tonnage = ?, last_updated = ?
                        WHERE imo = (SELECT imo FROM vessels_static WHERE mmsi = ?)
                    ''', (gt_value, datetime.now().isoformat(), mmsi))
                
                conn.commit()
                print(f"    ✓ Updated GT for MMSI {mmsi}: {gt_value}")
                return True
            else:
                # No emissions record - create a basic one or skip
                print(f"    ⚠ No emissions record for MMSI {mmsi}")
                return False
                
        except Exception as e:
            print(f"    Error updating GT for MMSI {mmsi}: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def process_vessels(self):
        """Process a batch of vessels."""
        vessels = self.get_vessels_without_gt()
        
        if not vessels:
            print("No vessels to process")
            return
        
        print(f"\nProcessing {len(vessels)} vessels...")
        
        for i, (mmsi, name, imo, ship_type, length) in enumerate(vessels):
            print(f"\n[{i+1}/{len(vessels)}] MMSI: {mmsi} | Name: {name or 'Unknown'}")
            
            # Check if already has GT
            conn = None
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT gross_tonnage FROM eu_mrv_emissions 
                    WHERE imo = (SELECT imo FROM vessels_static WHERE mmsi = ?)
                ''', (mmsi,))
                
                result = cursor.fetchone()
                if result and result[0] and result[0] not in ["NA", "NF"]:
                    print(f"    ✓ Already has GT: {result[0]}")
                    self.stats['already_had_gt'] += 1
                    continue
                    
            except Exception as e:
                print(f"    Error checking existing GT: {e}")
            finally:
                if conn:
                    conn.close()
            
            # Search for GT
            self.stats['total_searched'] += 1
            gt_value = self.search_gt_for_mmsi(mmsi, name)
            
            if gt_value in ["NA", "NF"]:
                # Mark as failed in cache
                self.cache['failed_mmsi'][str(mmsi)] = datetime.now().timestamp()
                self.stats['not_found'] += 1
                print(f"    ✗ GT not found: {gt_value}")
            else:
                self.stats['successful'] += 1
            
            # Update database
            self.update_vessel_gt(mmsi, gt_value)
            
            # Delay between searches
            if i < len(vessels) - 1:  # Don't delay after last vessel
                print(f"    Waiting {DELAY_BETWEEN_REQUESTS}s...")
                time.sleep(DELAY_BETWEEN_REQUESTS)
        
        # Save cache
        self.save_cache()
        
        # Print statistics
        print(f"\n{'='*60}")
        print("BATCH COMPLETE")
        print(f"{'='*60}")
        print(f"Total searched: {self.stats['total_searched']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Not found: {self.stats['not_found']}")
        print(f"Already had GT: {self.stats['already_had_gt']}")
        print(f"Success rate: {self.stats['successful']/self.stats['total_searched']*100:.1f}%")
    
    def run_service(self):
        """Run as a background service."""
        self.running = True
        print("GT Search Scraper service started")
        
        while self.running:
            try:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting GT search batch...")
                self.process_vessels()
                
                self.stats['last_run'] = datetime.now().isoformat()
                
                print(f"\nNext run in {CHECK_INTERVAL//3600} hours...")
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("\nService stopped by user")
                break
            except Exception as e:
                print(f"Service error: {e}")
                time.sleep(300)  # Wait 5 minutes before retry
        
        self.running = False


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    scraper = GTSearchScraper(str(db_path))
    
    # Run one batch for testing
    scraper.process_vessels()


if __name__ == "__main__":
    main()
