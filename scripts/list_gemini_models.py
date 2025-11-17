#!/usr/bin/env python3
"""List available Gemini models"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import google.generativeai as genai

# Load API key
config_path = Path(__file__).parent.parent / 'config' / 'gemini_api_key.txt'
api_key = config_path.read_text().strip()

genai.configure(api_key=api_key)

print("\nAvailable Gemini Models:")
print("="*60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n✓ {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description[:100]}...")
        print(f"  Methods: {', '.join(model.supported_generation_methods)}")

print("\n" + "="*60)
