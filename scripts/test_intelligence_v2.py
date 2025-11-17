#!/usr/bin/env python3
"""Test Intelligence Scraper V2 (DuckDuckGo-based)"""
import sys
sys.path.insert(0, 'src')

from utils.company_intelligence_scraper_v2 import CompanyIntelligenceScraperV2

print("="*80)
print("🕵️  TESTING INTELLIGENCE SCRAPER V2 (DuckDuckGo)")
print("="*80)
print("\n✅ Uses DuckDuckGo (more reliable than Google)")
print("✅ Direct site scraping")
print("✅ No googlesearch-python dependency\n")
print("="*80)
print()

scraper = CompanyIntelligenceScraperV2(verbose=True)
scraper.scrape_batch(max_companies=2)

print("\n" + "="*80)
print("✅ TEST COMPLETE - Check output!")
print("="*80)
