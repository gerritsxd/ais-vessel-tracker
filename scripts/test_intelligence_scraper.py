#!/usr/bin/env python3
"""
Test Company Intelligence Scraper on 1-2 companies
Shows what kind of intelligence we can gather
"""
import sys
sys.path.insert(0, 'src')

from utils.company_intelligence_scraper import CompanyIntelligenceScraper

print("="*80)
print("🕵️  TESTING COMPANY INTELLIGENCE SCRAPER")
print("="*80)
print()
print("What we're looking for:")
print("  ✅ Government grants & subsidies")
print("  ✅ Environmental lawsuits & violations")
print("  ✅ Sustainability news & initiatives")
print("  ✅ Industry reputation & rankings")
print("  ✅ Financial pressure indicators")
print()
print("What we're NOT looking for:")
print("  ❌ Company marketing websites")
print("  ❌ Social media posts")
print("  ❌ Company press releases")
print()
print("="*80)
print()

scraper = CompanyIntelligenceScraper(verbose=True)
scraper.scrape_batch(max_companies=2)

print("\n" + "="*80)
print("✅ TEST COMPLETE")
print("="*80)
print("\nCheck the output file for gathered intelligence!")
print("This data is MUCH more predictive than company websites!")
