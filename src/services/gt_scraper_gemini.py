"""
Gemini-Powered GT Scraper Service
Uses Google Gemini API to search for and extract Gross Tonnage data for vessels.
More reliable than HTML scraping.
"""

import sqlite3
import time
from pathlib import Path
from datetime import datetime
import json
import google.generativeai as genai
from typing import Optional, Tuple

DB_NAME = "vessel_static_data.db"
BATCH_SIZE = 50  # Smaller batches due to API rate limits
DELAY_BETWEEN_REQUESTS = 2  # 2 seconds between API calls
REQUEST_TIMEOUT = 30  # 30 second timeout
CACHE_FILE = "gt_scraper_gemini_cache.json"


class GTScraperGemini:
    """Gemini-powered GT scraper."""
    
    def __init__(self, db_path, api_key: Optional[str] = None):
        self.db_path = db_path
        self.stats = {
            'total_scraped': 0,
            'successful': 0,
            'failed': 0,
            'api_errors': 0,
            'mrv_updated': 0,
            'vessels_static_updated': 0,
        }
        self.cache = self.load_cache()
        
        # Initialize Gemini
        if api_key is None:
            api_key = self.load_api_key()
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def load_api_key(self) -> str:
        """Load Gemini API key from config file."""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / 'config' / 'gemini_api_key.txt'
        
        if not config_path.exists():
            # Try alternative location
            config_path = project_root / 'config' / 'gemini_api_key_wasp.txt'
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Gemini API key not found! Create: {config_path}\n"
                "Get key from: https://aistudio.google.com/app/apikey"
            )
        
        api_key = config_path.read_text().strip()
        
        if not api_key or api_key == "your-api-key-here":
            raise ValueError(f"Invalid API key in: {config_path}")
        
        return api_key
    
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
        """Get MRV vessels that need GT."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now().timestamp()
            week_ago = current_time - (7 * 86400)
            
            # Get MRV vessels that match vessels_static and need GT
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
            ''', (limit * 2,))  # Get 2x to filter failed attempts
            
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
    
    def ask_gemini_for_gt(self, imo: int, vessel_name: Optional[str] = None) -> Optional[int]:
        """Ask Gemini to find GT for a vessel."""
        try:
            # Build prompt
            vessel_info = f"IMO {imo}"
            if vessel_name:
                vessel_info = f"{vessel_name} (IMO {imo})"
            
            prompt = f"""Find the Gross Tonnage (GT) for this vessel: {vessel_info}

Please search for this vessel's specifications and return ONLY the Gross Tonnage number.
If you find it, respond with just the number (e.g., "12345").
If you cannot find it, respond with "NOT_FOUND".

Do not include any explanation, just the number or "NOT_FOUND"."""
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                return None
            
            result = response.text.strip()
            
            # Check if it's "NOT_FOUND"
            if "NOT_FOUND" in result.upper() or "not found" in result.lower():
                return None
            
            # Try to extract number
            import re
            numbers = re.findall(r'\d{3,7}', result)
            
            if numbers:
                # Take the first reasonable number (GT is usually 3-7 digits)
                for num_str in numbers:
                    num = int(num_str)
                    if 100 <= num <= 1000000:  # Sanity check
                        return num
            
            return None
            
        except Exception as e:
            error_str = str(e).lower()
            if 'quota' in error_str or '429' in error_str or 'rate limit' in error_str:
                self.stats['api_errors'] += 1
                print(f"  ⚠ API quota/rate limit error: {e}")
                raise  # Re-raise to stop batch
            else:
                print(f"  ⚠ Gemini API error: {e}")
                return None
    
    def update_gt_in_both_tables(self, imo, gt_value, mmsi=None):
        """Update GT in both tables."""
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
            
            # Update vessels_static
            if mmsi:
                cursor.execute('''
                    UPDATE vessels_static
                    SET 
                        gt = ?,
                        gt_source = 'gemini',
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
        """Run one batch of GT scraping using Gemini."""
        vessels = self.get_mrv_vessels_needing_gt(BATCH_SIZE)
        
        if not vessels:
            print("No MRV vessels need GT scraping")
            return
        
        print(f"\n{'='*80}")
        print(f"GEMINI GT SCRAPING BATCH - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"Vessels to scrape: {len(vessels)}")
        print(f"API delay: {DELAY_BETWEEN_REQUESTS}s between requests")
        print(f"{'='*80}\n")
        
        for i, (imo, name, mmsi) in enumerate(vessels, 1):
            print(f"[{i}/{len(vessels)}] {name or 'Unknown'} (IMO: {imo}, MMSI: {mmsi})")
            
            try:
                # Ask Gemini for GT
                gt_value = self.ask_gemini_for_gt(imo, name)
                
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
                    
            except Exception as e:
                if 'quota' in str(e).lower() or '429' in str(e):
                    print(f"\n⚠️  API quota exceeded! Stopping batch.")
                    break
                else:
                    print(f"  ✗ Error: {e}")
                    self.stats['failed'] += 1
        
        # Save cache
        self.save_cache()
        
        # Print stats
        print(f"\n{'='*80}")
        print("BATCH STATISTICS")
        print(f"{'='*80}")
        print(f"Total scraped: {self.stats['total_scraped']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"API errors: {self.stats['api_errors']}")
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
    
    try:
        scraper = GTScraperGemini(db_path)
        scraper.run_batch()
    except FileNotFoundError as e:
        print(f"❌ {e}")
    except ValueError as e:
        print(f"❌ {e}")


if __name__ == "__main__":
    main()

