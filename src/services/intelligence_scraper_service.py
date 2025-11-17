#!/usr/bin/env python3
"""
Intelligence Scraper Service - Runs continuously
Scrapes batches of companies, then sleeps before next batch
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.company_intelligence_scraper_v2 import CompanyIntelligenceScraperV2

# Configuration
BATCH_SIZE = 50  # Companies per batch
SLEEP_BETWEEN_BATCHES = 3600 * 24  # 24 hours (run once per day)
MAX_TOTAL_COMPANIES = 500  # Stop after scraping this many total


def main():
    """Run scraper service continuously"""
    print("="*80)
    print("🕵️  COMPANY INTELLIGENCE SCRAPER SERVICE")
    print("="*80)
    print(f"Batch size: {BATCH_SIZE} companies")
    print(f"Sleep between batches: {SLEEP_BETWEEN_BATCHES/3600:.1f} hours")
    print(f"Max total companies: {MAX_TOTAL_COMPANIES}")
    print("="*80)
    print()
    
    start_from = 0
    
    while True:
        try:
            # Check if we've reached the limit
            if start_from >= MAX_TOTAL_COMPANIES:
                print(f"\n✅ Reached maximum of {MAX_TOTAL_COMPANIES} companies. Stopping.")
                print("To continue, increase MAX_TOTAL_COMPANIES or restart from 0.")
                break
            
            # Run scraper batch
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
            print(f"Starting batch: companies {start_from+1} to {start_from+BATCH_SIZE}")
            print("-"*80)
            
            scraper = CompanyIntelligenceScraperV2(verbose=True)
            scraper.scrape_batch(
                max_companies=BATCH_SIZE,
                start_from=start_from
            )
            
            # Update start position for next batch
            start_from += BATCH_SIZE
            
            print(f"\n✅ Batch complete! Total scraped: {start_from} companies")
            print(f"⏰ Sleeping for {SLEEP_BETWEEN_BATCHES/3600:.1f} hours...")
            print(f"   Next batch: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Sleep until next batch
            time.sleep(SLEEP_BETWEEN_BATCHES)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Service stopped by user")
            print(f"Progress saved. Restart with --start-from {start_from}")
            break
            
        except Exception as e:
            print(f"\n❌ Service error: {e}")
            print(f"Waiting 5 minutes before retry...")
            time.sleep(300)  # Wait 5 minutes on error


if __name__ == '__main__':
    main()
