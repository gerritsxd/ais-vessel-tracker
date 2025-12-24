"""
Enhanced GT Scraper Service
Scrapes GT data for vessels and updates BOTH eu_mrv_emissions AND vessels_static tables.
Prioritizes MRV vessels that match vessels_static.
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
BATCH_SIZE = 100  # Scrape 100 vessels per batch
REQUESTS_PER_MINUTE = 10  # Rate limit: 10 requests per minute
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE  # 6 seconds
REQUEST_TIMEOUT = 15  # 15 second timeout per request
CACHE_FILE = "gt_scraper_enhanced_cache.json"


class GTScraperEnhanced:
    """Enhanced GT scraper that updates both tables."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.stats = {
            'total_scraped': 0,
            'successful': 0,
            'failed': 0,
            'mrv_updated': 0,
            'vessels_static_updated': 0,
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
        """Get database connection."""
        conn = sqlite3.connect(self.db_path, timeout=60)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    
    def get_mrv_vessels_needing_gt(self, limit=BATCH_SIZE):
        """Get MRV vessels that need GT, prioritizing those that match vessels_static."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get MRV vessels that:
            # 1. Don't have GT yet (or have empty/N/A)
            # 2. Have IMO
            # 3. Match vessels_static (prioritize these)
            # 4. Haven't failed recently
            
            current_time = datetime.now().timestamp()
            week_ago = current_time - (7 * 86400)
            
            # First, get MRV vessels that match vessels_static
            cursor.execute('''
                SELECT DISTINCT e.imo, e.vessel_name, v.mmsi
                FROM eu_mrv_emissions e
                INNER JOIN vessels_static v ON v.imo = e.imo
                WHERE e.imo IS NOT NULL
                  AND (e.gross_tonnage IS NULL 
                       OR e.gross_tonnage = '' 
                       OR e.gross_tonnage = 'N/A'
                       OR CAST(e.gross_tonnage AS INTEGER) = 0)
                  AND (v.gt IS NULL OR v.gt = 0)
                ORDER BY RANDOM()
                LIMIT ?
            ''', (limit,))
            
            vessels = cursor.fetchall()
            
            # Filter out recently failed attempts
            filtered = []
            for imo, name, mmsi in vessels:
                imo_str = str(imo)
                last_fail = self.cache.get('failed_imos', {}).get(imo_str, 0)
                if last_fail < week_ago:
                    filtered.append((imo, name, mmsi))
                    if len(filtered) >= limit:
                        break
            
            return filtered
            
        finally:
            if conn:
                conn.close()
    
    def scrape_gt_from_marinetraffic(self, imo):
        """Scrape GT from MarineTraffic."""
        try:
            url = f"https://www.marinetraffic.com/en/ais/details/ships/imo:{imo}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for GT in various formats
            text = soup.get_text()
            
            # Pattern: "Gross Tonnage: 12345" or "GT: 12345"
            patterns = [
                r'Gross\s+Tonnage[:\s]+(\d{1,6})',
                r'GT[:\s]+(\d{1,6})',
                r'gross\s+tonnage[:\s]+(\d{1,6})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    gt = int(match.group(1))
                    if 100 <= gt <= 1000000:  # Sanity check
                        return gt
            
            return None
            
        except Exception as e:
            return None
    
    def scrape_gt_from_vesselfinder(self, imo):
        """Scrape GT from VesselFinder."""
        try:
            url = f"https://www.vesselfinder.com/vessels/details/{imo}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            
            # Pattern matching
            patterns = [
                r'Gross\s+Tonnage[:\s]+(\d{1,6})',
                r'GT[:\s]+(\d{1,6})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    gt = int(match.group(1))
                    if 100 <= gt <= 1000000:
                        return gt
            
            return None
            
        except Exception:
            return None
    
    def scrape_gt(self, imo):
        """Try multiple sources to get GT data."""
        # Try MarineTraffic first
        gt = self.scrape_gt_from_marinetraffic(imo)
        if gt:
            return gt
        
        time.sleep(2)
        
        # Try VesselFinder as fallback
        gt = self.scrape_gt_from_vesselfinder(imo)
        if gt:
            return gt
        
        return None
    
    def update_gt_in_both_tables(self, imo, gt_value, mmsi=None):
        """Update GT in both eu_mrv_emissions and vessels_static."""
        conn = None
        updated_mrv = False
        updated_vessels_static = False
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Update eu_mrv_emissions
            cursor.execute('''
                UPDATE eu_mrv_emissions
                SET gross_tonnage = ?
                WHERE imo = ?
            ''', (str(gt_value), imo))
            
            if cursor.rowcount > 0:
                updated_mrv = True
            
            # Update vessels_static (if mmsi provided)
            if mmsi:
                cursor.execute('''
                    UPDATE vessels_static
                    SET 
                        gt = ?,
                        gt_source = 'scraped',
                        gt_updated_at = datetime('now')
                    WHERE mmsi = ?
                    AND (gt IS NULL OR gt = 0)
                ''', (gt_value, mmsi))
                
                if cursor.rowcount > 0:
                    updated_vessels_static = True
            
            conn.commit()
            
        except Exception as e:
            print(f"    Error updating database: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        return updated_mrv, updated_vessels_static
    
    def run_batch(self):
        """Run one batch of GT scraping."""
        vessels = self.get_mrv_vessels_needing_gt(BATCH_SIZE)
        
        if not vessels:
            print("No MRV vessels need GT scraping")
            return
        
        print(f"\n{'='*80}")
        print(f"ENHANCED GT SCRAPING BATCH - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"Vessels to scrape: {len(vessels)}")
        print(f"Rate limit: {REQUESTS_PER_MINUTE} requests/minute")
        print(f"{'='*80}\n")
        
        for i, (imo, name, mmsi) in enumerate(vessels, 1):
            print(f"[{i}/{len(vessels)}] {name or 'Unknown'} (IMO: {imo}, MMSI: {mmsi})")
            
            # Scrape GT
            gt_value = self.scrape_gt(imo)
            
            if gt_value:
                # Update both tables
                updated_mrv, updated_vessels = self.update_gt_in_both_tables(imo, gt_value, mmsi)
                
                if updated_mrv or updated_vessels:
                    print(f"  ✓ Success! GT = {gt_value:,}")
                    if updated_mrv:
                        self.stats['mrv_updated'] += 1
                    if updated_vessels:
                        self.stats['vessels_static_updated'] += 1
                    self.stats['successful'] += 1
                    
                    # Remove from failed cache
                    if str(imo) in self.cache.get('failed_imos', {}):
                        del self.cache['failed_imos'][str(imo)]
                else:
                    print(f"  ⚠ Found GT but DB update failed")
            else:
                print(f"  ✗ GT not found")
                self.stats['failed'] += 1
                
                # Add to failed cache
                if 'failed_imos' not in self.cache:
                    self.cache['failed_imos'] = {}
                self.cache['failed_imos'][str(imo)] = datetime.now().timestamp()
            
            self.stats['total_scraped'] += 1
            
            # Rate limiting
            if i < len(vessels):
                time.sleep(DELAY_BETWEEN_REQUESTS)
        
        # Save cache
        self.save_cache()
        
        # Print stats
        print(f"\n{'='*80}")
        print("BATCH STATISTICS")
        print(f"{'='*80}")
        print(f"Total scraped: {self.stats['total_scraped']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"MRV table updated: {self.stats['mrv_updated']}")
        print(f"vessels_static updated: {self.stats['vessels_static_updated']}")
        print(f"{'='*80}\n")


def main():
    """Main function."""
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    scraper = GTScraperEnhanced(db_path)
    scraper.run_batch()


if __name__ == "__main__":
    main()

