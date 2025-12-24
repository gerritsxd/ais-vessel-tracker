"""
One-time runner for enhanced GT scraper.
Run this to scrape GT for MRV vessels.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.gt_scraper_enhanced import GTScraperEnhanced

DB_NAME = "vessel_static_data.db"

if __name__ == "__main__":
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        exit(1)
    
    print(f"🚀 Starting Enhanced GT Scraper")
    print(f"📊 Database: {db_path}\n")
    
    scraper = GTScraperEnhanced(db_path)
    scraper.run_batch()
    
    print("✅ Batch complete!")

