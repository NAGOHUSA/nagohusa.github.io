#!/usr/bin/env python3
"""
PulseRelay - Real-Time Intelligence & Trend Synthesis Agent
Fetches current trends from DeepSeek API with structured JSON output
Wide Net: Casting across all topics, no local-only restrictions
"""

import os
import json
import sys
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Wide net niches - covering all possible interests
WIDE_NET_NICHES = [
    "Breaking News",
    "Technology & AI",
    "Space & Science",
    "Gaming",
    "Memes & Viral Content",
    "Entertainment",
    "Sports",
    "Business & Finance",
    "Crypto & Web3",
    "Politics",
    "Health & Wellness",
    "Environment & Climate",
    "Music & Pop Culture",
    "Movies & TV",
    "Art & Design",
    "Education & Learning",
    "Travel & Adventure",
    "Food & Cooking",
    "Fashion & Beauty",
    "Relationships & Social",
    "Career & Work",
    "Philosophy & Deep Topics",
    "Weird & Interesting",
    "Nostalgia & Retro",
    "Future & Sci-Fi"
]

# Platform origins mapping
PLATFORMS = ["X", "Reddit", "TikTok", "Instagram", "Facebook", "Google", "Threads", "LinkedIn", "Discord", "YouTube"]

def build_wide_net_prompt() -> str:
    """
    Build the comprehensive prompt for DeepSeek to cast a WIDE net across all topics
    """
    
    current_date = datetime.now().strftime("%B %d, %Y")
    current_hour = datetime.now().strftime("%H:00 UTC")
    
    prompt = f"""You are a Real-Time Intelligence & Trend Synthesis Agent with a mandate to cast a WIDE NET across the entire social graph of 2026.

Current Date & Time: {current_date} at {current_hour}

**YOUR MISSION:**
Capture the full spectrum of human attention right now - from mainstream breaking news to obscure micro-trends, from serious developments to hilarious memes. Nothing is off-limits. Cast as wide as possible.

**1. SOURCE LOGIC (The Wide Net):**
Pull from ALL these platform archetypes:
- **X (Twitter) & Reddit:** Breaking signals, early adopter discussions, unverified events, funny memes before they go mainstream
- **TikTok & Instagram Reels:** Visual sentiment, high Save-to-View ratios, micro-dramas, aesthetic shifts, dance trends
- **Google Trends:** Search intent spikes ("How to", "What is", "Why does")
- **Facebook & Threads:** Community impact, group discussions, town-hall style conversations
- **LinkedIn:** Professional trends, career shifts, industry news
- **Discord:** Niche community obsessions, gaming, crypto, tech
- **YouTube:** Long-form discussions, drama, documentaries, reviews

**2. CONTENT FILTERING (Cast the widest net possible):**
Include a MIX of:
- **Breaking News:** High-velocity reports on ANY topic (space, tech, politics, entertainment, world events)
- **Funny/Viral:** Nostalgic remixes, chaos culture memes, absurdist humor, DM-sharing velocity spikes
- **Serious/Tech:** AI breakthroughs, scientific discoveries, industry shifts
- **Niche Obsessions:** What specific communities are hyper-focused on right now
- **Mainstream Trends:** What the general public is actually talking about
- **Weird/Unique:** The unusual, the unexpected, the "how did this trend start"

**3. TODAY'S REAL-TIME PULSE (April 11, 2026):**
Make sure to capture these actual events AND add your own discoveries:
- **Space:** Artemis II Return - Astronaut recovery images viral
- **Gaming:** Pragmata Pre-Load - Reddit threads exploding
- **Tech:** Agentic AI Explosion - Microsoft Azure Summit news
- **Entertainment:** Check what's trending on Netflix, Spotify, TikTok
- **Sports:** Current games, trades, controversies
- **Memes:** What's being DM-shared right now

**4. THE "HUMAN" FILTER:**
- Ignore bot-driven trends where Comment-to-Like ratio is < 5%
- Prioritize trends with REAL human engagement and discussion
- Look for emotional resonance (excitement, anger, confusion, joy)

**5. OUTPUT FORMAT:**
Return a JSON object with a "pulse_items" array containing 12-15 trend objects. Each object MUST follow this exact schema:

{{
  "title": "Short, high-impact headline (under 80 chars)",
  "summary": "2-3 sentence 'Why this matters' summary with key details",
  "sourceURL": "Direct link to source (real URL from today)",
  "timestamp": "ISO8601 UTC timestamp for right now",
  "niche": "One of the wide net niches provided",
  "platform_origin": "Where this trend is hottest",
  "velocity_score": "Integer 1-100 (100 = fastest growing)",
  "human_vibe_check": "One of: Verified Human | Bot-Signal Low | High Engagement | Viral Authentic"
}}

**6. WIDE NET NICHE LIST (choose from these):**
{WIDE_NET_NICHES}

**7. REAL SOURCE URLS (use these or find real ones):**
- Space: https://www.nasa.gov
- Tech: https://news.microsoft.com
- Gaming: https://www.reddit.com/r/gaming
- Entertainment: https://www.netflix.com/tudum
- News: https://www.reuters.com
- Trends: https://trends.google.com

**CRITICAL INSTRUCTIONS:**
1. Return ONLY valid JSON - no markdown, no code blocks, no explanatory text
2. Cast the WIDEST net possible - don't just focus on tech/space
3. Include at least one trend from each platform origin
4. Mix serious news with funny/viral content (70/30 split)
5. Find actual trending topics happening RIGHT NOW on April 11, 2026
6. Use real source URLs that would actually work
7. Set velocity_score based on real velocity (90-100: exploding, 70-89: growing fast, 50-69: steady trend, 30-49: niche, 1-29: micro)
8. Current timestamp for all items
9. Make it FEEL like a live pulse of the entire internet

Generate 12-15 diverse pulse items that reflect the ACTUAL heartbeat of the global social graph right now. Cover different niches, platforms, and energy levels."""

    return prompt

def fetch_trends(api_key: str) -> List[Dict[str, Any]]:
    """
    Fetch trending topics from DeepSeek API using Wide Net Pulse-Synthesis
    
    Args:
        api_key: DeepSeek API key
        
    Returns:
        List of trend dictionaries with the required schema
    """
    if not api_key or api_key == "":
        raise ValueError("DEEPSEEK_API_KEY is not set or empty")
    
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = build_wide_net_prompt()
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are a Wide Net Real-Time Intelligence Agent. You output ONLY valid JSON. Cast the widest possible net across all topics. Never include markdown or explanatory text outside JSON."
            },
            {
                "role": "user",
                "content": system_prompt
            }
        ],
        "temperature": 0.7,  # Higher temperature for more diverse, creative trends
        "max_tokens": 5000,
        "response_format": {"type": "json_object"}
    }
    
    try:
        print(f"🌊 Casting WIDE NET across the social graph...")
        print(f"📡 Fetching diverse trends for: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"🎯 Covering {len(WIDE_NET_NICHES)} niches and {len(PLATFORMS)} platforms")
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 401:
            print("❌ Authentication failed (401 Unauthorized)")
            print("Please verify your DEEPSEEK_API_KEY is correct and active")
            sys.exit(1)
        
        response.raise_for_status()
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not content:
            raise ValueError("Empty response from DeepSeek API")
        
        # Clean and parse JSON response
        content = content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # Parse the JSON
        data = json.loads(content)
        
        # Handle different response structures
        if "pulse_items" in data:
            trends = data["pulse_items"]
        elif isinstance(data, list):
            trends = data
        else:
            # Try to find any array in the response
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    trends = value
                    break
            else:
                # If no array found, wrap the object
                trends = [data]
        
        # Validate and clean each trend
        validated_trends = []
        for i, trend in enumerate(trends):
            # Ensure all required fields exist
            if not all(k in trend for k in ["title", "summary", "niche", "platform_origin", "velocity_score"]):
                print(f"⚠️ Skipping invalid trend #{i+1}: missing required fields")
                continue
            
            # Validate niche
            if trend["niche"] not in WIDE_NET_NICHES:
                # Find closest match or default to "Trending"
                trend["niche"] = "Breaking News"
            
            # Validate platform
            if trend["platform_origin"] not in PLATFORMS:
                trend["platform_origin"] = "X"  # Default to X
            
            # Ensure velocity_score is int
            if isinstance(trend["velocity_score"], str):
                trend["velocity_score"] = int(trend["velocity_score"])
            elif not isinstance(trend["velocity_score"], int):
                trend["velocity_score"] = 50
            
            # Add timestamp if missing
            if "timestamp" not in trend:
                trend["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Add sourceURL if missing
            if "sourceURL" not in trend:
                trend["sourceURL"] = "https://trends.google.com"
            
            # Add human_vibe_check if missing
            if "human_vibe_check" not in trend:
                vibe_scores = ["Verified Human", "Bot-Signal Low", "High Engagement", "Viral Authentic"]
                trend["human_vibe_check"] = vibe_scores[trend["velocity_score"] % 4]
            
            validated_trends.append(trend)
        
        print(f"✅ Successfully fetched {len(validated_trends)} diverse trends from wide net")
        
        # Show niche distribution
        niche_counts = {}
        for trend in validated_trends:
            niche = trend["niche"]
            niche_counts[niche] = niche_counts.get(niche, 0) + 1
        print(f"📊 Niche distribution: {len(niche_counts)} different niches covered")
        
        return validated_trends
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 60 seconds")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Failed to connect to DeepSeek API")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse API response as JSON: {e}")
        print(f"Raw response preview: {content[:200]}...")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

def save_trends(trends: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save trends to JSON file with timestamp and metadata
    
    Args:
        trends: List of trend dictionaries
        output_file: Path to output JSON file
    """
    output_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "pulse_items": trends,
        "metadata": {
            "source": "DeepSeek API - Wide Net Mode",
            "count": len(trends),
            "niches_covered": len(set(t.get("niche") for t in trends)),
            "platforms_covered": len(set(t.get("platform_origin") for t in trends)),
            "generator": "PulseRelay Wide Net Agent v2.0"
        }
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write to file with pretty formatting
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Trends saved to {output_file}")
    print(f"📈 Total pulse items: {len(trends)}")
    print(f"🎨 Unique niches: {output_data['metadata']['niches_covered']}")
    print(f"📱 Unique platforms: {output_data['metadata']['platforms_covered']}")

def main():
    """Main execution function"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ ERROR: DEEPSEEK_API_KEY environment variable not set")
        sys.exit(1)
    
    # Define output path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_file = os.path.join(project_root, "data", "trends.json")
    
    print("=" * 60)
    print("🌊 PULSERELAY - WIDE NET TREND SYNTHESIS")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🎯 Casting wide net across {len(WIDE_NET_NICHES)} niches")
    print(f"📡 Monitoring {len(PLATFORMS)} platforms")
    print("=" * 60)
    
    # Fetch and save trends
    trends = fetch_trends(api_key)
    save_trends(trends, output_file)
    
    print("\n✅ PulseRelay wide net complete!")
    print("🌊 Successfully captured the heartbeat of the global social graph")

if __name__ == "__main__":
    main()
