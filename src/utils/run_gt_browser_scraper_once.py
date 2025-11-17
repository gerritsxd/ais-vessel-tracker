"""
Manual Browser GT Scraper Runner
Run this script on-demand to scrape GT data using browser automation.
Uses Playwright with Chromium to scrape from search results without visiting individual pages.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.gt_scraper_browser import BrowserGTScraper

DB_NAME = "vessel_static_data.db"


async def main():
    """Run browser GT scraper once."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Error: Database not found: {db_path}")
        print("Run ais_collector.py first to create the database.")
        return
    
    print("="*80)
    print("MANUAL BROWSER GT SCRAPER - ONE-TIME RUN")
    print("="*80)
    print("This will scrape GT data using Chromium browser automation.")
    print("Method: Google search → Extract from search snippets")
    print("Press Ctrl+C to cancel.\n")
    
    try:
        scraper = BrowserGTScraper(db_path)
        await scraper.run_scraping_batch()
        
        print("\n✓ Browser scraping complete!")
        print("\nTo run the continuous service (24h interval):")
        print("  python src/services/gt_scraper_browser.py")
        print("\nOr on VPS:")
        print("  sudo systemctl start ais-gt-browser-scraper")
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
