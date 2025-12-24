"""
One-time runner for enhanced GT scraper.
Run this to scrape GT for MRV vessels.
"""

from pathlib import Path
from src.services.gt_scraper_enhanced import GTScraperEnhanced

DB_NAME = "vessel_static_data.db"

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
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

