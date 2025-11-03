#!/usr/bin/env python3
"""
Script to check available Gemini models for the API key
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY") or "AIzaSyCu6SB2b0iWeLWv_MdXcTg6ZVSLE7mnPyw"

if not api_key:
    print("❌ No GEMINI_API_KEY found!")
    exit(1)

print(f"🔑 Using API Key: {api_key[:20]}...")
print("\n" + "="*60)
print("Checking available Gemini models...")
print("="*60 + "\n")

try:
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # List available models
    print("📋 Available models:\n")
    models = genai.list_models()
    
    available_models = []
    for model in models:
        # Only show models that support generateContent
        if 'generateContent' in model.supported_generation_methods:
            available_models.append(model.name)
            print(f"  ✅ {model.name}")
            if model.display_name:
                print(f"     Display Name: {model.display_name}")
            print(f"     Methods: {', '.join(model.supported_generation_methods)}")
            print()
    
    if not available_models:
        print("  ❌ No models found that support generateContent")
    else:
        print("\n" + "="*60)
        print("Testing models with a simple query...")
        print("="*60 + "\n")
        
        # Test each model
        test_prompt = "Say 'Hello, this is a test' in one sentence."
        working_models = []
        
        for model_name in available_models:
            try:
                print(f"🧪 Testing: {model_name}...", end=" ")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(test_prompt)
                
                if response.text:
                    print(f"✅ WORKING")
                    working_models.append({
                        'name': model_name,
                        'response': response.text.strip()[:50]
                    })
                else:
                    print(f"⚠️  No response text")
            except Exception as e:
                print(f"❌ ERROR: {str(e)[:50]}")
        
        print("\n" + "="*60)
        print("✅ WORKING MODELS:")
        print("="*60 + "\n")
        
        if working_models:
            # Recommend the best model (prefer flash for speed, or pro for quality)
            recommended = None
            for model in working_models:
                name = model['name']
                # Prefer flash models for speed, or pro for quality
                if 'flash' in name.lower() and not recommended:
                    recommended = model
                elif 'pro' in name.lower() and 'flash' not in recommended['name'].lower() if recommended else True:
                    if not recommended or 'pro' in name.lower():
                        recommended = model
            
            if not recommended and working_models:
                recommended = working_models[0]
            
            print("Recommended model (best balance of speed and quality):")
            print(f"  🎯 {recommended['name']}")
            print(f"  Response: {recommended['response']}")
            print()
            
            print("All working models:")
            for model in working_models:
                marker = "🎯" if model == recommended else "  "
                print(f"{marker} {model['name']}")
            
            # Extract short model name
            short_name = recommended['name'].split('/')[-1] if '/' in recommended['name'] else recommended['name']
            print("\n" + "="*60)
            print(f"📝 Recommended model name for config: {short_name}")
            print("="*60)
        else:
            print("❌ No working models found!")
            
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

