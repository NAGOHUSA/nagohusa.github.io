#!/usr/bin/env python3
"""
OTAKU-PULSE - Real-Time Anime & Manga Culture Intelligence Agent
Fetches current trends from DeepSeek API focused on anime/manga ecosystem
"""

import os
import json
import sys
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any

# Anime & Manga specific niches
ANIME_NICHES = [
    "Seasonal Anime",
    "Manga Releases",
    "Manhwa/Webtoons",
    "Anime News",
    "Studio News",
    "Voice Actors/Seiyuu",
    "Anime Movies",
    "Manga Adaptations",
    "Light Novels",
    "Doujinshi/Fan Works",
    "Cosplay",
    "Anime Merchandise",
    "Conventions & Events",
    "Anime Streaming",
    "Classic Anime",
    "Anime OST/Music",
    "Anime Figures/Gunpla",
    "Isekai",
    "Shonen",
    "Shojo",
    "Seinen",
    "Slice of Life",
    "Anime Memes",
    "Anime Twitter Drama",
    "Manga Sales Rankings"
]

# Platforms for anime/manga discourse
PLATFORMS = [
    "MyAnimeList",
    "AniList",
    "Reddit",
    "X",
    "Discord",
    "YouTube",
    "TikTok",
    "Instagram",
    "4chan",
    "Crunchyroll",
    "MangaPlus",
    "AnimeNewsNetwork",
    "Twitter"
]

def build_anime_pulse_prompt() -> str:
    """
    Build the comprehensive prompt for DeepSeek to capture anime/manga culture
    """
    
    current_date = datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""You are OTAKU-PULSE, a Real-Time Anime & Manga Culture Intelligence Agent. Your mission is to capture the heartbeat of global anime/manga fandom right now.

Current Date: {current_date} (Spring 2026 Anime Season)

**YOUR MISSION:**
Track EVERYTHING happening in anime/manga culture - from seasonal shows to manga sales, from seiyuu news to convention updates, from memes to drama.

**1. SOURCE LOGIC (Anime/Manga Ecosystem):**
Pull from ALL these platforms:
- **MyAnimeList & AniList:** Seasonal rankings, user scores, most anticipated shows
- **Reddit (r/anime, r/manga, r/manhwa):** Episode discussions, chapter leaks, fan theories
- **X (Twitter):** Trending anime tags, seiyuu announcements, studio news, fanart explosions
- **Discord:** Community obsessions, watch parties, private scans
- **YouTube:** Anime reviewers, reaction channels, AMVs, breakdowns
- **TikTok:** Anime edits, cosplay transformations, scene re-enactments
- **Crunchyroll/MangaPlus:** Official releases, simulcast news
- **AnimeNewsNetwork:** Industry reports, licensing announcements

**2. WHAT TO TRACK (Cast Wide Net Within Anime):**

**Seasonal Anime (Spring 2026):**
- What shows are dominating discussion?
- Which episodes broke the internet this week?
- Unexpected hits vs. disappointing adaptations

**Manga/Manhwa:**
- New chapter reactions (spoiler-free summaries)
- Sales rankings (Oricon, Japanese charts)
- New license announcements
- Series ending or entering final arc

**Industry News:**
- Studio announcements
- Director/writer changes
- Production delays
- Streaming platform acquisitions

**Culture & Community:**
- Viral anime memes
- Cosplay trends
- Convention news (AnimeJapan 2026 recap, upcoming cons)
- Anime Twitter drama
- "What should I watch" megathreads

**Specific Hot Topics Right Now (April 2026):**
- Spring 2026 season: Which shows are the standouts?
- Upcoming summer season anticipation
- Recent manga endings/beginnings
- Any major adaptation announcements
- Studio controversies or wins
- Voice actor news (marriages, roles, scandals)
- Crunchyroll Anime Awards aftermath/discussion

**3. THE "HUMAN" FILTER:**
- Prioritize trends with REAL fan engagement
- Look for passionate discussion, not bot activity
- Capture both mainstream hype and niche obsessions

**4. OUTPUT FORMAT:**
Return a JSON object with a "anime_pulse_items" array containing 12-15 trend objects. Each object MUST follow this exact schema:

{{
  "title": "Short, high-impact headline (under 80 chars)",
  "summary": "2-3 sentence 'Why this matters' for anime/manga fans",
  "sourceURL": "Direct link to source (MyAnimeList, Reddit, ANN, etc.)",
  "timestamp": "ISO8601 UTC timestamp",
  "niche": "One of the anime niches provided",
  "platform_origin": "Where this is trending",
  "velocity_score": "Integer 1-100 (100 = exploding in fandom)",
  "engagement_type": "One of: Discussion | Hype | Controversy | Meme | News | Review | Leak | Announcement"
}}

**5. EXAMPLE REAL ENTRIES (April 2026):**

{{
  "title": "Spring 2026's Hidden Gem: 'Stellar Records' Episode 4 Goes Viral",
  "summary": "Original anime 'Stellar Records' sees 200% MAL ranking jump after emotional Episode 4. Fans calling it 'Frieren-level' storytelling.",
  "sourceURL": "https://myanimelist.net/anime/12345/Stellar_Records",
  "niche": "Seasonal Anime",
  "platform_origin": "Reddit",
  "velocity_score": 94,
  "engagement_type": "Hype"
}}

{{
  "title": "MangaPlus Announces 5 New Simulpub Series for Summer",
  "summary": "Shueisha expands global reach with 5 new simultaneous English releases starting June 1st. Includes sequel to hit manhwa 'Solo Leveling'.",
  "sourceURL": "https://mangaplus.shueisha.co.jp/news",
  "niche": "Manga Releases",
  "platform_origin": "MangaPlus",
  "velocity_score": 82,
  "engagement_type": "Announcement"
}}

**6. REAL SOURCE URLS TO USE:**
- MyAnimeList: https://myanimelist.net/news
- AnimeNewsNetwork: https://www.animenewsnetwork.com/news
- Crunchyroll: https://www.crunchyroll.com/news
- Reddit r/anime: https://www.reddit.com/r/anime
- MangaPlus: https://mangaplus.shueisha.co.jp
- Oricon Sales: https://www.oricon.jp/rank/obc/

**CRITICAL INSTRUCTIONS:**
1. Return ONLY valid JSON - no markdown, no code blocks
2. Focus 100% on anime/manga - no off-topic trends
3. Include mix of: seasonal anime (3-4 items), manga/manhwa (3-4), industry news (2-3), culture/memes (2-3)
4. Find ACTUAL April 2026 anime/manga trends
5. Use real source URLs that work
6. Velocity scores: 90+ = exploding, 70-89 = hot, 50-69 = growing, 30-49 = niche, <30 = micro-trend
7. Current timestamp for all items
8. Make it feel like the LIVING pulse of otaku culture

Generate 12-15 anime/manga pulse items that reflect EXACTLY what the global fandom is talking about RIGHT NOW on April 11, 2026."""

    return prompt

def fetch_anime_trends(api_key: str) -> List[Dict[str, Any]]:
    """
    Fetch anime/manga trends from DeepSeek API
    """
    if not api_key or api_key == "":
        raise ValueError("DEEPSEEK_API_KEY is not set or empty")
    
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = build_anime_pulse_prompt()
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "You are OTAKU-PULSE, an Anime & Manga Culture Intelligence Agent. You output ONLY valid JSON focused on anime/manga trends. Never include markdown or explanatory text outside JSON."
            },
            {
                "role": "user",
                "content": system_prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 5000,
        "response_format": {"type": "json_object"}
    }
    
    try:
        print(f"🎴 OTAKU-PULSE: Scanning the anime/manga multiverse...")
        print(f"📡 Fetching otaku trends for: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"🎯 Covering {len(ANIME_NICHES)} anime/manga niches")
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 401:
            print("❌ Authentication failed (401 Unauthorized)")
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
        
        # Validate and clean
        validated_trends = []
        for i, trend in enumerate(trends):
            if not all(k in trend for k in ["title", "summary", "niche", "platform_origin", "velocity_score"]):
                print(f"⚠️ Skipping invalid trend #{i+1}")
                continue
            
            # Validate niche
            if trend["niche"] not in ANIME_NICHES:
                trend["niche"] = "Anime News"
            
            # Add missing fields
            if "timestamp" not in trend:
                trend["timestamp"] = datetime.now(timezone.utc).isoformat()
            if "sourceURL" not in trend:
                trend["sourceURL"] = "https://myanimelist.net"
            if "engagement_type" not in trend:
                trend["engagement_type"] = "Discussion"
            
            validated_trends.append(trend)
        
        print(f"✅ Captured {len(validated_trends)} anime/manga pulse items")
        
        # Show niche distribution
        niche_counts = {}
        for trend in validated_trends:
            niche = trend["niche"]
            niche_counts[niche] = niche_counts.get(niche, 0) + 1
        print(f"📊 Spread across {len(niche_counts)} different anime/manga categories")
        
        return validated_trends
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def save_trends(trends: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save anime trends to JSON file
    """
    output_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "anime_pulse_items": trends,
        "metadata": {
            "source": "DeepSeek API - OTAKU-PULSE Mode",
            "count": len(trends),
            "niches_covered": len(set(t.get("niche") for t in trends)),
            "platforms_covered": len(set(t.get("platform_origin") for t in trends)),
            "generator": "OTAKU-PULSE v1.0 - Anime/Manga Culture Intelligence"
        }
    }
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Anime pulse saved to {output_file}")
    print(f"🎌 Total otaku pulse items: {len(trends)}")

def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ ERROR: DEEPSEEK_API_KEY not set")
        sys.exit(1)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_file = os.path.join(project_root, "data", "anime_trends.json")
    
    print("=" * 60)
    print("🎌 OTAKU-PULSE - ANIME/MANGA CULTURE INTELLIGENCE")
    print("=" * 60)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🎯 Tracking {len(ANIME_NICHES)} anime/manga categories")
    print("=" * 60)
    
    trends = fetch_anime_trends(api_key)
    save_trends(trends, output_file)
    
    print("\n✅ OTAKU-PULSE complete!")
    print("🎴 Successfully captured the heartbeat of anime/manga fandom")

if __name__ == "__main__":
    main()
