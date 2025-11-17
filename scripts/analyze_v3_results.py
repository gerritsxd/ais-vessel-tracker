#!/usr/bin/env python3
"""Analyze V3 scraping results"""
import json
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def analyze_results(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    companies = data['companies']
    total = len(companies)
    
    # Count data sources
    wiki_count = 0
    web_count = 0
    both_count = 0
    neither_count = 0
    
    for company_name, profile in companies.items():
        has_wiki = bool(profile['text_data'].get('wikipedia', {}).get('summary'))
        has_web = bool(profile['text_data'].get('website', {}).get('pages'))
        
        if has_wiki:
            wiki_count += 1
        if has_web:
            web_count += 1
        if has_wiki and has_web:
            both_count += 1
        if not has_wiki and not has_web:
            neither_count += 1
    
    success_count = total - neither_count
    
    print("="*80)
    print("📊 V3 SCRAPING RESULTS ANALYSIS")
    print("="*80)
    print(f"\nTotal companies: {total}")
    print(f"Success (any data): {success_count} ({success_count/total*100:.1f}%)")
    print(f"\nData source breakdown:")
    print(f"  Wikipedia only: {wiki_count - both_count}")
    print(f"  Website only: {web_count - both_count}")
    print(f"  Both sources: {both_count}")
    print(f"  No data: {neither_count}")
    
    print(f"\n📈 Source statistics:")
    print(f"  Wikipedia success rate: {wiki_count/total*100:.1f}%")
    print(f"  Website success rate: {web_count/total*100:.1f}%")
    
    # Calculate average text lengths
    wiki_lengths = []
    web_lengths = []
    
    for profile in companies.values():
        if profile['text_data'].get('wikipedia', {}).get('summary'):
            wiki_lengths.append(profile['text_data']['wikipedia']['length'])
        if profile['text_data'].get('website', {}).get('pages'):
            web_lengths.append(profile['text_data']['website']['total_length'])
    
    if wiki_lengths:
        print(f"\n📝 Wikipedia text:")
        print(f"  Avg length: {sum(wiki_lengths)/len(wiki_lengths):.0f} chars")
        print(f"  Total: {sum(wiki_lengths):,} chars")
    
    if web_lengths:
        print(f"\n🌐 Website text:")
        print(f"  Avg length: {sum(web_lengths)/len(web_lengths):.0f} chars")
        print(f"  Total: {sum(web_lengths):,} chars")
    
    # Show companies with no data
    if neither_count > 0 and neither_count < 10:
        print(f"\n❌ Companies with NO data:")
        for name, profile in companies.items():
            has_wiki = bool(profile['text_data'].get('wikipedia', {}).get('summary'))
            has_web = bool(profile['text_data'].get('website', {}).get('pages'))
            if not has_wiki and not has_web:
                print(f"  - {name}")
    
    print("\n" + "="*80)
    
    # Assessment
    if success_count / total >= 0.7:
        print("✅ GOOD: >70% success rate")
    elif success_count / total >= 0.5:
        print("⚠️  MODERATE: 50-70% success rate")
    else:
        print("❌ LOW: <50% success rate - needs improvement")
    
    print("="*80)

if __name__ == "__main__":
    # Find most recent file
    files = sorted(Path('data').glob('company_profiles_v3_structured_*.json'))
    if not files:
        print("❌ No V3 results found!")
        sys.exit(1)
    
    latest = files[-1]
    print(f"Analyzing: {latest.name}\n")
    analyze_results(latest)
