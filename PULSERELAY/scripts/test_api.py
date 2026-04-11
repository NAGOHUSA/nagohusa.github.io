#!/usr/bin/env python3
"""
Test script to verify DeepSeek API key is working
"""

import os
import sys
import requests

def test_api_key():
    """Test if the DeepSeek API key is valid"""
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ ERROR: DEEPSEEK_API_KEY environment variable not set")
        return False
    
    print(f"✅ API key found: {api_key[:10]}... (length: {len(api_key)})")
    
    # Test API endpoint
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Simple test payload
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Say 'API key works!'"}
        ],
        "max_tokens": 20,
        "temperature": 0
    }
    
    print(f"\nTesting connection to {url}...")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: API key is valid and working!")
            result = response.json()
            message = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"Response: {message}")
            return True
        elif response.status_code == 401:
            print("❌ FAILED: Authentication error - Invalid API key")
            print("Please check that:")
            print("  1. The API key is correct")
            print("  2. The API key hasn't expired")
            print("  3. You have credits/usage available")
            return False
        elif response.status_code == 429:
            print("⚠️ RATE LIMIT: Too many requests, try again later")
            return False
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ FAILED: Connection timeout")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Cannot connect to DeepSeek API")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error - {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("DeepSeek API Key Test")
    print("=" * 50)
    
    success = test_api_key()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ API test PASSED")
        sys.exit(0)
    else:
        print("❌ API test FAILED")
        sys.exit(1)
