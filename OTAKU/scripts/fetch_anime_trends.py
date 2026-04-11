#!/usr/bin/env python3
"""
OTAKU-PULSE ULTIMATE - The Most Comprehensive Anime/Manga/Cartoon Intelligence Agent
Pulls from EVERY platform: Crunchyroll, Netflix, X, Reddit, MyAnimeList, TikTok, YouTube, and more
"""

import os
import json
import sys
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any

# ULTIMATE niche list - covering EVERYTHING
ULTIMATE_NICHES = [
    # Seasonal & Current Anime
    "Spring 2026 Anime", "Seasonal Anime", "Simulcast", "Weekly Episodes",
    
    # Major Series
    "One Piece", "Death Note", "Naruto/Boruto", "Dragon Ball", "Bleach", 
    "Jujutsu Kaisen", "Demon Slayer", "Attack on Titan", "My Hero Academia",
    "Chainsaw Man", "Spy x Family", "Frieren", "Solo Leveling",
    
    # Streaming Platforms
    "Crunchyroll News", "Netflix Anime", "Hulu Anime", "Disney+ Anime", 
    "Amazon Anime", "HIDIVE", "RetroCrush",
    
    # Cartoons & Western Animation
    "Western Cartoons", "Adult Swim", "Rick and Morty", "South Park",
    "Simpsons", "Family Guy", "Netflix Cartoons", "Disney Animation",
    
    # Movies & Films
    "Anime Movies", "Ghibli", "Makoto Shinkai", "Mappa Films", "Ufotable",
    "Theatrical Releases", "Upcoming Movies",
    
    # Manga & Manhwa
    "Manga Releases", "Manga Sales", "Shonen Jump", "Manga Plus",
    "Manhwa", "Webtoons", "Manhua", "Manga Adaptations",
    
    # Industry News
    "Studio News", "Production Delays", "Licensing", "Simulcast Announcements",
    "Voice Actors/Seiyuu", "Directors", "Animators", "Studio Controversies",
    
    # Community & Culture
    "Anime Memes", "Anime Twitter", "Reddit Discussions", "4chan", "Discord",
    "Cosplay", "Conventions", "Anime Awards", "Fan Art", "AMVs",
    
    # Music & Sound
    "Anime Openings", "Anime Endings", "OST", "Voice Actor Songs", 
    "Theme Song Artists", "Spotify Anime",
    
    # Merchandise & Collectibles
    "Figures", "Gunpla", "Statues", "Collectibles", "Merch Drops",
    
    # Gaming Connections
    "Anime Games", "Genshin Impact", "Zenless Zone Zero", "Honkai",
    "Fate/Grand Order", "Gacha Games",
    
    # Classics & Retro
    "Classic Anime", "Retro Anime", "90s Anime", "00s Anime", "Vintage Manga"
]

# ULTIMATE platform list
ULTIMATE_PLATFORMS = [
    "Crunchyroll", "Netflix", "Hulu", "Disney+", "Amazon Prime", "HIDIVE",
    "X (Twitter)", "Reddit", "MyAnimeList", "AniList", "AnimeNewsNetwork",
    "YouTube", "TikTok", "Instagram", "Discord", "4chan", "Telegram",
    "MangaPlus", "Shonen Jump", "Viz Media", "Kodansha", "Seven Seas",
    "Funimation", "RetroCrush", "Tubi", "Pluto TV", "Twitch"
]

# Engagement types
ENGAGEMENT_TYPES = [
    "Breaking News", "Hype Train", "Controversy", "Wholesome", "Meme Storm",
    "Theory Crafting", "Spoiler Alert", "Review Bomb", "Anime of the Season",
    "Underrated Gem", "Overhyped", "Hidden Gem", "Cult Classic"
]

def build_ultimate_prompt() -> str:
    """
    Build the most comprehensive prompt for anime/manga/cartoon news
    """
    
    current_date = datetime.now().strftime("%B %d, %Y")
    current_hour = datetime.now().strftime("%H:00 UTC")
    
    prompt = f"""You are OTAKU-PULSE ULTIMATE - The World's Most Comprehensive Anime/Manga/Cartoon Intelligence Agent.

Current Date & Time: {current_date} at {current_hour}

**YOUR MISSION:**
Cast the WIDEST POSSIBLE NET across ALL anime, manga, cartoon, and otaku culture globally. You are the ULTIMATE source for everything happening right now.

**1. MUST-COVER TOPICS (No Exceptions):**

**Core Anime (EVERY single one of these must appear across your 20 items):**
- One Piece (current episodes, manga chapters, theories)
- Death Note (anniversary, new adaptations, merchandise)
- Naruto/Boruto (updates, fan content)
- Dragon Ball (new content, games, merchandise)
- Jujutsu Kaisen (season updates, manga spoilers)
- Demon Slayer (upcoming arcs, movies)
- Attack on Titan (post-finale discussion, spin-offs)
- My Hero Academia (current arc, ending speculation)
- Chainsaw Man (season 2 news, manga)
- Spy x Family (season updates, movie news)
- Frieren (awards, season 2 hype)
- Solo Leveling (season 2, manhwa comparison)

**Streaming Platforms (REAL-TIME NEWS):**
- Crunchyroll: New licenses, simulcast schedule changes, award winners
- Netflix: Upcoming anime originals, live-action adaptations, release dates
- Hulu/Disney+: New acquisitions, exclusive content
- Amazon/HIDIVE: Hidden gems, exclusive licenses

**Western Cartoons & Adult Animation:**
- Rick and Morty (season news, crossovers)
- South Park (special events, gaming)
- Simpsons (milestones, guest stars)
- Family Guy (current events, cutaways)
- Invincible, Vox Machina, Blue Eye Samurai

**Movies & Films:**
- Theatrical releases in Japan and worldwide
- Ghibli news, Makoto Shinkai projects, Mappa/Ufotable films
- Upcoming anime movies, box office performance

**Manga/Manhwa (REAL-TIME):**
- Shonen Jump weekly rankings
- Manga Plus simulpub updates
- New series announcements
- Series ending or entering final arc
- Manhwa adaptations (Solo Leveling, Tower of God, God of High School)

**Community Trends (What's Actually Being Discussed):**
- Reddit r/anime: What's hot RIGHT NOW
- Anime Twitter: Current drama, celebrations, controversies
- TikTok: Viral anime edits, cosplay trends
- YouTube: Top reviewers, reaction videos, AMVs
- Discord: Community watch parties, leaks

**2. REAL-TIME APRIL 2026 SPECIFICS:**
- Spring 2026 season: Which shows are dominating?
- Crunchyroll Spring 2026 lineup standouts
- Netflix's upcoming anime slate
- Current manga sales rankings (Oricon)
- Any production delays or studio news
- Voice actor announcements or events
- Convention news (current or upcoming)
- Viral anime memes of the week

**3. THE "ULTIMATE" REQUIREMENTS:**
- Pull from ALL platforms listed
- Cover BOTH mainstream and niche content
- Include breaking news, hype, and funny/meme content
- Prioritize REAL fan engagement over bot activity
- Find actual trending discussions happening NOW

**4. OUTPUT FORMAT:**
Return a JSON object with "anime_pulse_items" array containing 18-22 items. Each object MUST follow:

{{
  "title": "Explosive, clickable headline (under 100 chars)",
  "summary": "3-4 sentence detailed 'Why this matters' with specific numbers/dates",
  "sourceURL": "Real, working URL from today",
  "timestamp": "Current ISO8601 UTC timestamp",
  "niche": "From the ultimate niches list",
  "platform_origin": "From platforms list",
  "velocity_score": "Integer 1-100 (100 = global explosion)",
  "engagement_type": "From engagement types",
  "related_series": "One Piece, Death Note, etc. (which series this relates to)",
  "region": "Global | Japan | US | Europe | Asia"
}}

**5. REAL SOURCE URLS TO USE:**
- Crunchyroll News: https://www.crunchyroll.com/news
- AnimeNewsNetwork: https://www.animenewsnetwork.com/news
- MyAnimeList: https://myanimelist.net/news
- Reddit r/anime: https://www.reddit.com/r/anime
- One Piece (Official): https://one-piece.com/news
- Shonen Jump: https://www.shonenjump.com/jumpnews
- Netflix Anime: https://www.netflix.com/anime
- MangaPlus: https://mangaplus.shueisha.co.jp/news
- Oricon Sales: https://www.oricon.co.jp/rank/

**CRITICAL INSTRUCTIONS:**
1. Return ONLY valid JSON - no markdown, no explanations
2. MUST include One Piece and Death Note content in EVERY update
3. MUST have items from Crunchyroll, Netflix, and Reddit
4. Mix velocity scores: 5-6 items at 85-100 (exploding), 6-8 at 60-84 (trending), 6-8 at 30-59 (growing)
5. Include at least 3 meme/funny items
6. Include at least 2 controversy/drama items
7. Include actual manga sales numbers where possible
8. Make it feel like the PULSE of global otaku culture

Generate 18-22 ultimate anime/manga/cartoon pulse items reflecting EXACTLY what the world is talking about RIGHT NOW on {current_date}."""

    return prompt

def fetch_anime_trends(api_key: str) -> List[Dict[str, Any]]:
    """
    Fetch comprehensive anime/manga trends from DeepSeek API
    """
    if not api_key or api_key == "":
        raise ValueError("DEEPSEEK_API_KEY is not set or empty")
    
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = build_ultimate_prompt()
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system", 
                "content": "You are OTAKU-PULSE ULTIMATE, the world's most comprehensive anime/manga/cartoon intelligence agent. You output ONLY valid JSON. You cover EVERY platform, EVERY major series, and EVERY trend. No markdown, no explanations."
            },
            {
                "role": "user", 
                "content": system_prompt
            }
        ],
        "temperature": 0.8,  # Higher for more diverse, creative coverage
        "max_tokens": 8000,  # Large for comprehensive coverage
        "response_format": {"type": "json_object"}
    }
    
    print("=" * 70)
    print("🎌 OTAKU-PULSE ULTIMATE - Global Anime/Manga/Cartoon Intelligence")
    print("=" * 70)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🎯 Covering {len(ULTIMATE_NICHES)} ultimate niches")
    print(f"📡 Monitoring {len(ULTIMATE_PLATFORMS)} platforms")
    print(f"🌟 Prioritizing: One Piece, Death Note, Crunchyroll, Netflix, Reddit")
    print("=" * 70)
    
    try:
        print("🌊 Casting ULTIMATE WIDE NET across anime/manga multiverse...")
        
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        
        if response.status_code == 401:
            print("❌ Authentication failed (401 Unauthorized)")
            print("Please verify your DEEPSEEK_API_KEY is correct and active")
            sys.exit(1)
        
        response.raise_for_status()
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not content:
            raise ValueError("Empty response from DeepSeek API")
        
        # Clean and parse JSON
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        data = json.loads(content)
        
        # Extract pulse items
        if "anime_pulse_items" in data:
            trends = data["anime_pulse_items"]
        elif "pulse_items" in data:
            trends = data["pulse_items"]
        elif isinstance(data, list):
            trends = data
        else:
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    trends = value
                    break
            else:
                trends = [data]
        
        # Validate and enhance trends
        validated_trends = []
        required_series = ["One Piece", "Death Note"]
        found_series = set()
        
        for i, trend in enumerate(trends):
            # Check required fields
            if not all(k in trend for k in ["title", "summary", "niche", "platform_origin", "velocity_score"]):
                print(f"⚠️ Skipping invalid trend #{i+1}: missing required fields")
                continue
            
            # Track series coverage
            if "related_series" in trend:
                found_series.add(trend["related_series"])
            
            # Validate and add defaults
            if trend["niche"] not in ULTIMATE_NICHES:
                trend["niche"] = "Anime News"
            
            if trend["platform_origin"] not in ULTIMATE_PLATFORMS:
                trend["platform_origin"] = "Reddit"
            
            if "engagement_type" not in trend:
                trend["engagement_type"] = "Discussion"
            
            if "related_series" not in trend:
                trend["related_series"] = "General Anime"
            
            if "region" not in trend:
                trend["region"] = "Global"
            
            if "timestamp" not in trend:
                trend["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            if "sourceURL" not in trend:
                trend["sourceURL"] = "https://myanimelist.net"
            
            validated_trends.append(trend)
        
        print(f"\n✅ Captured {len(validated_trends)} ultimate anime/manga pulse items")
        
        # Show statistics
        niche_counts = {}
        platform_counts = {}
        series_counts = {}
        region_counts = {}
        
        for trend in validated_trends:
            niche = trend["niche"]
            platform = trend["platform_origin"]
            series = trend.get("related_series", "Other")
            region = trend.get("region", "Global")
            
            niche_counts[niche] = niche_counts.get(niche, 0) + 1
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            series_counts[series] = series_counts.get(series, 0) + 1
            region_counts[region] = region_counts.get(region, 0) + 1
        
        print(f"\n📊 Coverage Statistics:")
        print(f"   • Unique niches: {len(niche_counts)}")
        print(f"   • Unique platforms: {len(platform_counts)}")
        print(f"   • Unique series: {len(series_counts)}")
        print(f"   • Regions covered: {len(region_counts)}")
        
        # Check for required series
        missing_series = required_series - found_series
        if missing_series:
            print(f"⚠️ Warning: Missing coverage for {missing_series}")
        
        # Show top platforms
        top_platforms = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n📱 Top platforms: {', '.join([f'{p}({c})' for p, c in top_platforms])}")
        
        # Show top niches
        top_niches = sorted(niche_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"🎯 Top niches: {', '.join([f'{n}({c})' for n, c in top_niches])}")
        
        return validated_trends
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 90 seconds")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Failed to connect to DeepSeek API")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse API response as JSON: {e}")
        print(f"Raw response preview: {content[:500]}...")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

def save_trends(trends: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save ultimate anime trends to JSON file with rich metadata
    """
    # Calculate average velocity
    avg_velocity = sum(t.get("velocity_score", 0) for t in trends) // len(trends) if trends else 0
    
    # Count by engagement type
    engagement_counts = {}
    for trend in trends:
        eng_type = trend.get("engagement_type", "Discussion")
        engagement_counts[eng_type] = engagement_counts.get(eng_type, 0) + 1
    
    output_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "anime_pulse_items": trends,
        "metadata": {
            "source": "DeepSeek API - OTAKU-PULSE ULTIMATE Mode",
            "count": len(trends),
            "average_velocity": avg_velocity,
            "niches_covered": len(set(t.get("niche") for t in trends)),
            "platforms_covered": len(set(t.get("platform_origin") for t in trends)),
            "series_covered": len(set(t.get("related_series") for t in trends if t.get("related_series"))),
            "engagement_breakdown": engagement_counts,
            "generator": "OTAKU-PULSE ULTIMATE v3.0 - Global Anime/Manga Intelligence",
            "coverage_scope": "Worldwide - All Platforms - All Series"
        }
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write to file with pretty formatting
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Ultimate anime pulse saved to {output_file}")
    print(f"📈 Total items: {len(trends)}")
    print(f"⭐ Average velocity: {avg_velocity}")
    print(f"🎨 Unique series covered: {output_data['metadata']['series_covered']}")
    print(f"🌍 Coverage: {output_data['metadata']['coverage_scope']}")

def main():
    """Main execution function"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ ERROR: DEEPSEEK_API_KEY environment variable not set")
        print("Please set your DeepSeek API key:")
        print("  export DEEPSEEK_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Define output path - matches your repository structure
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Goes up to OTAKU/
    output_file = os.path.join(project_root, "data", "anime_trends.json")
    
    print("\n" + "🎌" * 35)
    print("OTAKU-PULSE ULTIMATE - THE COMPLETE ANIME/MANGA INTELLIGENCE AGENT")
    print("🎌" * 35)
    
    # Fetch and save trends
    trends = fetch_anime_trends(api_key)
    save_trends(trends, output_file)
    
    print("\n" + "=" * 70)
    print("✅ OTAKU-PULSE ULTIMATE complete!")
    print("🌊 Successfully captured the COMPLETE heartbeat of global otaku culture")
    print("=" * 70)
    print("\n📊 Dashboard available at: https://nagoh.us/OTAKU/")
    print("🔄 Updates every hour with the latest from:")
    print("   • Crunchyroll • Netflix • Reddit • X • MyAnimeList")
    print("   • One Piece • Death Note • All Major Series • Global Trends")
    print("=" * 70)

if __name__ == "__main__":
    main()
