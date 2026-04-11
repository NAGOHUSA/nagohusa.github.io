#!/usr/bin/env python3
import os
import json
import sys
import requests
from datetime import datetime, timezone

def fetch_anime_trends(api_key):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""You are OTAKU-PULSE. Return a JSON object with "anime_pulse_items" array (10 items).
Current date: {datetime.now().strftime('%B %d, %Y')}

Each item must have: title, summary, sourceURL, timestamp (current UTC), niche, platform_origin, velocity_score (1-100), engagement_type.

Focus on Spring 2026 anime, manga news, and otaku culture.
Return ONLY valid JSON."""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Output ONLY valid JSON. No markdown."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}
    }
    
    print("🎴 Fetching anime trends...")
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    
    content = response.json()["choices"][0]["message"]["content"]
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    
    data = json.loads(content)
    return data.get("anime_pulse_items", [])

def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ Missing API key")
        sys.exit(1)
    
    trends = fetch_anime_trends(api_key)
    
    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "anime_pulse_items": trends,
        "metadata": {"count": len(trends)}
    }
    
    os.makedirs("OTAKU/data", exist_ok=True)
    with open("OTAKU/data/anime_trends.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Saved {len(trends)} trends to OTAKU/data/anime_trends.json")

if __name__ == "__main__":
    main()
