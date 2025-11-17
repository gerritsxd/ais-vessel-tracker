#!/usr/bin/env python3
"""
Quick test script for Company Profiler V2
Tests the scraper on a single well-known company
"""

import sys
from pathlib import Path

# Fix Windows console encoding for emojis
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'utils'))

from company_profiler_v2 import CompanyProfilerV2

def test_single_company():
    """Test scraper on Maersk (well-known company)"""
    print("="*80)
    print("🧪 TESTING COMPANY PROFILER V2")
    print("="*80)
    print("\nTesting on: Maersk A/S")
    print("This will:")
    print("  1. Search Wikipedia")
    print("  2. Search Google for company info")
    print("  3. Find official website")
    print("  4. Crawl website pages")
    print("\nExpected time: ~2-3 minutes\n")
    
    profiler = CompanyProfilerV2(verbose=True, max_pages_per_site=10, use_browser=False)
    
    # Test on Maersk
    profile = profiler.profile_company("Maersk A/S")
    
    # Add to profiler data
    profiler.companies_data["Maersk A/S"] = profile
    
    # Save results
    profiler.save_final_results()
    
    # Show summary
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    for source, data in profile['data_sources'].items():
        status = "❌ Failed" if 'error' in data else "✅ Success"
        print(f"{source:20s} {status}")
        
        if 'error' not in data:
            if source == 'wikipedia' and 'extract' in data:
                print(f"  → Extract length: {len(data['extract'])} chars")
            elif source == 'google_search' and 'search_results' in data:
                print(f"  → Found {len(data['search_results'])} URLs")
            elif source == 'company_website' and 'official_websites' in data:
                print(f"  → Found {len(data['official_websites'])} websites")
            elif source == 'website_crawl' and 'pages' in data:
                total_text = sum(p['length'] for p in data['pages'])
                print(f"  → Crawled {data['pages_crawled']} pages, {total_text:,} chars total")
    
    print("\n✅ Test complete! Check data/company_training_data_*.txt for output")
    print("="*80)

if __name__ == "__main__":
    test_single_company()
