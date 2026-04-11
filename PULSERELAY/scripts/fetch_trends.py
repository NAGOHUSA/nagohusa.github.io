#!/usr/bin/env python3
"""
Fetch current technology trends from DeepSeek API and save to trends.json
"""

import os
import json
import sys
import requests
from datetime import datetime
from typing import List, Dict, Any

def fetch_trends(api_key: str) -> List[Dict[str, Any]]:
    """
    Fetch trending topics from DeepSeek API
    
    Args:
        api_key: DeepSeek API key
        
    Returns:
        List of trend dictionaries with 'title' and 'description'
    """
    if not api_key or api_key == "":
        raise ValueError("DEEPSEEK_API_KEY is not set or empty")
    
    # DeepSeek API endpoint
    url = "https://api.deepseek.com/v1/chat/completions"
    
    # Headers with proper authentication
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Request payload
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are a technology trends analyst. Provide current, relevant tech trends."
            },
            {
                "role": "user",
                "content": """List the top 5 current technology trends for today's date. 
Format your response as a JSON array with objects containing 'title' and 'description' fields.
Example format: 
[
  {"title": "Trend 1", "description": "Description of trend 1"},
  {"title": "Trend 2", "description": "Description of trend 2"}
]
Return ONLY the JSON array, no additional text."""
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000,
        "response_format": {"type": "json_object"}
    }
    
    try:
        print(f"Calling DeepSeek API at {url}...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # Check for HTTP errors
        if response.status_code == 401:
            print("ERROR: Authentication failed (401 Unauthorized)")
            print("Please verify your DEEPSEEK_API_KEY is correct and active")
            print(f"API key starts with: {api_key[:8]}...")
            print(f"API key length: {len(api_key)} characters")
            sys.exit(1)
        
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not content:
            raise ValueError("Empty response from DeepSeek API")
        
        # Clean and parse JSON response
        content = content.strip()
        
        # Handle if response has markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # Parse the JSON
        trends_data = json.loads(content)
        
        # Handle both array and object formats
        if isinstance(trends_data, dict) and "trends" in trends_data:
            trends = trends_data["trends"]
        elif isinstance(trends_data, list):
            trends = trends_data
        else:
            raise ValueError(f"Unexpected response format: {type(trends_data)}")
        
        # Validate structure
        for trend in trends:
            if "title" not in trend or "description" not in trend:
                raise ValueError(f"Invalid trend format: {trend}")
        
        print(f"Successfully fetched {len(trends)} trends")
        return trends
        
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out after 30 seconds")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("ERROR: Failed to connect to DeepSeek API")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse API response as JSON: {e}")
        print(f"Raw response: {content[:200]}...")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        sys.exit(1)

def save_trends(trends: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save trends to JSON file with timestamp
    
    Args:
        trends: List of trend dictionaries
        output_file: Path to output JSON file
    """
    output_data = {
        "last_updated": datetime.now().isoformat(),
        "trends": trends,
        "metadata": {
            "source": "DeepSeek API",
            "count": len(trends)
        }
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Trends saved to {output_file}")

def main():
    """Main execution function"""
    # Get API key from environment
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY environment variable not set")
        print("Please set your DeepSeek API key:")
        print("  export DEEPSEEK_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Validate API key format (basic check)
    if len(api_key) < 20:
        print(f"WARNING: API key seems too short ({len(api_key)} chars). Expected 30+ characters.")
    
    # Define output path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_file = os.path.join(project_root, "data", "trends.json")
    
    print(f"Fetching trends from DeepSeek API...")
    print(f"API Key present: {'Yes' if api_key else 'No'} (length: {len(api_key) if api_key else 0})")
    
    # Fetch and save trends
    trends = fetch_trends(api_key)
    save_trends(trends, output_file)
    
    print("\n✅ Success! trends.json has been updated.")
    print(f"Location: {output_file}")

if __name__ == "__main__":
    main()
