#!/usr/bin/env python3
"""
Quick test script for Gemini Intelligence Scraper
Tests with 3 companies to verify setup
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.company_intelligence_scraper_gemini import GeminiIntelligenceScraper


def main():
    print("\n" + "="*80)
    print("GEMINI SCRAPER TEST - 3 Companies")
    print("="*80)
    print()
    
    # Load API key
    config_path = Path(__file__).parent.parent / 'config' / 'gemini_api_key.txt'
    
    if not config_path.exists():
        print("❌ ERROR: API key not found!")
        print(f"   Create file: {config_path}")
        print("   Get key from: https://aistudio.google.com/app/apikey")
        return
    
    api_key = config_path.read_text().strip()
    
    if api_key == "your-api-key-here":
        print("❌ ERROR: Please add your real API key to:")
        print(f"   {config_path}")
        print()
        print("Steps:")
        print("1. Visit: https://aistudio.google.com/app/apikey")
        print("2. Click 'Create API Key'")
        print("3. Copy your key")
        print("4. Paste it in config/gemini_api_key.txt")
        return
    
    print(f"✓ API key loaded: {api_key[:10]}...{api_key[-5:]}")
    print()
    
    # Create scraper
    scraper = GeminiIntelligenceScraper(api_key=api_key, verbose=True)
    
    # Test with 3 companies
    print("Testing with 3 companies...")
    print()
    scraper.scrape_batch(max_companies=3, start_from=0)
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    print()
    print("Check the output file:")
    print("  data/company_intelligence_gemini_*.json")
    print()
    print("If results look good, deploy to VPS with:")
    print("  1. git add . && git commit -m 'Add Gemini scraper' && git push")
    print("  2. SSH to VPS and follow GEMINI_SETUP.md")
    print()


if __name__ == '__main__':
    main()
