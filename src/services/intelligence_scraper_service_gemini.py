#!/usr/bin/env python3
"""
Gemini Intelligence Scraper Service - Runs continuously
Uses FREE Google Gemini API (1,500 requests/day)
Scrapes batches of companies, then sleeps before next batch
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.company_intelligence_scraper_gemini import GeminiIntelligenceScraper

# Configuration
BATCH_SIZE = 30  # Companies per batch (conservative to stay in free tier)
SLEEP_BETWEEN_BATCHES = 3600 * 24  # 24 hours (run once per day)
MAX_TOTAL_COMPANIES = 500  # Stop after scraping this many total


def load_api_key():
    """Load Gemini API key from config file"""
    config_path = Path(__file__).parent.parent.parent / 'config' / 'gemini_api_key.txt'
    
    if not config_path.exists():
        print("❌ ERROR: Gemini API key not found!")
        print(f"   Create file: {config_path}")
        print("   Content: Your Gemini API key from https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    api_key = config_path.read_text().strip()
    
    if not api_key or api_key == "your-api-key-here":
        print("❌ ERROR: Invalid API key in config file")
        print(f"   Edit: {config_path}")
        print("   Get your key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    
    return api_key


def main():
    """Run scraper service continuously"""
    print("="*80)
    print("🤖 GEMINI INTELLIGENCE SCRAPER SERVICE (FREE TIER)")
    print("="*80)
    print(f"Batch size: {BATCH_SIZE} companies")
    print(f"Sleep between batches: {SLEEP_BETWEEN_BATCHES/3600:.1f} hours")
    print(f"Max total companies: {MAX_TOTAL_COMPANIES}")
    print(f"Free tier limit: 1,500 requests/day")
    print("="*80)
    print()
    
    # Load API key
    try:
        api_key = load_api_key()
        print("✓ Gemini API key loaded")
    except Exception as e:
        print(f"❌ Failed to load API key: {e}")
        return
    
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
            
            scraper = GeminiIntelligenceScraper(api_key=api_key, verbose=True)
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
            print(f"Progress saved. Restart with start_from={start_from}")
            break
            
        except Exception as e:
            print(f"\n❌ Service error: {e}")
            print(f"Waiting 5 minutes before retry...")
            time.sleep(300)  # Wait 5 minutes on error


if __name__ == '__main__':
    main()
