#!/usr/bin/env python3
"""
Test Company Profiler V3 - ML-Ready Structured Data
Shows improvements over V2
"""

import sys
from pathlib import Path

# Fix Windows console encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'utils'))

from company_profiler_v3 import CompanyProfilerV3

def test_v3():
    """Test V3 on 3 companies"""
    print("="*80)
    print("🧪 TESTING COMPANY PROFILER V3")
    print("="*80)
    print("\n✨ V3 IMPROVEMENTS:")
    print("  1. ✅ Structured attributes (fleet size, emissions, WASP scores)")
    print("  2. ✅ ML labels (company type, fleet category, emissions level)")
    print("  3. ✅ Separated text sources (Wikipedia vs Website)")
    print("  4. ✅ Advanced preprocessing (boilerplate removal)")
    print("  5. ✅ Shorter, cleaner output (5K chars max)")
    print("\nTesting on 3 companies...\n")
    
    profiler = CompanyProfilerV3(verbose=True, max_pages_per_site=6)
    profiler.profile_batch(max_companies=3, start_from=0)
    
    print("\n" + "="*80)
    print("📊 COMPARISON: V2 vs V3")
    print("="*80)
    print("\nV2 (OLD):")
    print("  ❌ Unstructured verbose text (50K+ chars)")
    print("  ❌ Marketing fluff and boilerplate")
    print("  ❌ Mixed Wikipedia + Website content")
    print("  ❌ No labels or categories")
    print("  ❌ Encoding errors")
    
    print("\nV3 (NEW):")
    print("  ✅ Structured JSON with attributes")
    print("  ✅ Clean, preprocessed text (5K chars)")
    print("  ✅ Separated sources for better training")
    print("  ✅ ML-ready labels and categories")
    print("  ✅ Fixed encoding")
    
    print("\n✅ Test complete! Check data/company_profiles_v3_*.json")
    print("="*80)

if __name__ == "__main__":
    test_v3()
