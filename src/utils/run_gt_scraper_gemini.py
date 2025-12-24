"""
One-time runner for Gemini-powered GT scraper.
Run this to scrape GT for MRV vessels using Gemini API.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.gt_scraper_gemini import GTScraperGemini

DB_NAME = "vessel_static_data.db"

if __name__ == "__main__":
    db_path = project_root / "data" / DB_NAME
    if not db_path.exists():
        db_path = project_root / DB_NAME
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        exit(1)
    
    print(f"🚀 Starting Gemini-Powered GT Scraper")
    print(f"📊 Database: {db_path}\n")
    
    try:
        scraper = GTScraperGemini(db_path)
        scraper.run_batch()
        print("✅ Batch complete!")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("\nTo set up Gemini API:")
        print("1. Visit: https://aistudio.google.com/app/apikey")
        print("2. Create API key")
        print("3. Save to: config/gemini_api_key.txt")
        exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

