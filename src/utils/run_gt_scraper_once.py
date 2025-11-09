"""
Manual GT Scraper Runner
Run this script on-demand to scrape GT data for a batch of vessels.
Useful for testing or manual updates without waiting for the 24h service.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.gt_scraper import GTScraper

DB_NAME = "vessel_static_data.db"


def main():
    """Run GT scraper once."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Error: Database not found: {db_path}")
        print("Run ais_collector.py first to create the database.")
        return
    
    print("="*80)
    print("MANUAL GT SCRAPER - ONE-TIME RUN")
    print("="*80)
    print("This will scrape GT data for one batch of vessels.")
    print("Press Ctrl+C to cancel.\n")
    
    try:
        scraper = GTScraper(db_path)
        scraper.run_scraping_batch()
        
        print("\n✓ Scraping complete!")
        print("\nTo run the continuous service (24h interval):")
        print("  python src/services/gt_scraper.py")
        print("\nOr on VPS:")
        print("  sudo systemctl start ais-gt-scraper")
        
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
