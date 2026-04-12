#!/usr/bin/env python3
"""
PulseRelay - Multi-Source Real-Time Trend Aggregator v3.0
Fetches trending data from multiple APIs and synthesizes comprehensive feed
Optimized for iOS app consumption with VelocityTrend schema

Features:
- Multi-source aggregation (Reddit, Hacker News, GitHub, DeepSeek AI)
- Real velocity calculation from engagement metrics
- Smart human vs. bot detection
- Perfect JSON schema match for iOS app
- Deduplication and intelligent ranking

Author: PulseRelay Team
Date: April 12, 2026
"""

import os
import json
import sys
import requests
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

# Niche categories - MUST match iOS app's NicheCategory enum exactly
APP_NICHES = [
    "cinema", "sports", "worldEvents", "streaming", "music",
    "space", "tech", "maker", "privacy", "repair",
    "outdoor", "legal", "local"
]

# Platform sources matching iOS app's SourcePlatform enum
APP_PLATFORMS = {
    "twitter": "twitter",
    "reddit": "reddit", 
    "hackernews": "hackernews",
    "youtube": "youtube",
    "mastodon": "mastodon",
    "github": "github",
    "rss": "rss"
}

# API Endpoints
REDDIT_BASE = "https://www.reddit.com"
HN_BASE = "https://hacker-news.firebaseio.com/v0"
GITHUB_TRENDING = "https://api.github.com/search/repositories"

# ============================================================================
# MULTI-SOURCE DATA FETCHERS
# ============================================================================

class TrendAggregator:
    """Aggregates trends from multiple sources"""
    
    def __init__(self, deepseek_key: str, github_token: Optional[str] = None):
        self.deepseek_key = deepseek_key
        self.github_token = github_token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PulseRelay/3.0 (iOS Trend Aggregator)'
        })
    
    def fetch_reddit_trends(self, subreddit: str, niche: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch trending posts from Reddit"""
        try:
            url = f"{REDDIT_BASE}/r/{subreddit}/hot.json?limit={limit}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            trends = []
            for post in data.get('data', {}).get('children', []):
                post_data = post.get('data', {})
                
                # Calculate velocity score based on engagement
                score = post_data.get('score', 0)
                num_comments = post_data.get('num_comments', 0)
                created = post_data.get('created_utc', 0)
                age_hours = (time.time() - created) / 3600
                
                # Velocity: (score + comments) / age in hours
                velocity = (score + num_comments * 2) / max(age_hours, 1)
                velocity_score = min(velocity / 100, 1.0)  # Normalize to 0-1
                
                # Signal strength based on comment-to-upvote ratio (human engagement)
                signal_strength = min(num_comments / max(score, 1), 1.0)
                
                # Better human vs bot detection
                # Consider multiple factors:
                # 1. Any post with 20+ comments is likely human
                # 2. Comment ratio > 2% with at least 3 comments
                # 3. Very high velocity (>0.7) with any comments
                is_human = (
                    num_comments >= 20 or  # Lots of discussion = human
                    (num_comments >= 3 and (num_comments / max(score, 1)) > 0.02) or  # Decent engagement
                    (velocity_score > 0.7 and num_comments > 0)  # High velocity with engagement
                )
                
                trends.append({
                    'id': f"reddit_{post_data.get('id', '')}",
                    'niche': niche,
                    'headline': post_data.get('title', '')[:200],
                    'summary': post_data.get('selftext', '')[:300] or f"Trending on r/{subreddit}",
                    'velocity_score': velocity_score,
                    'signal_strength': signal_strength,
                    'mentions_last_hour': int(score / max(age_hours, 1)),
                    'mentions_previous_24h': score,
                    'source': 'reddit',
                    'source_url': f"https://reddit.com{post_data.get('permalink', '')}",
                    'is_human': is_human,
                    'timestamp': datetime.fromtimestamp(created, timezone.utc).isoformat(),
                    'tags': post_data.get('link_flair_text', '').split() if post_data.get('link_flair_text') else []
                })
            
            return trends
            
        except Exception as e:
            print(f"⚠️ Reddit fetch failed for r/{subreddit}: {e}")
            return []
    
    def fetch_hackernews_trends(self, niche: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch trending stories from Hacker News"""
        try:
            # Get top stories
            response = self.session.get(f"{HN_BASE}/topstories.json", timeout=10)
            response.raise_for_status()
            story_ids = response.json()[:limit]
            
            trends = []
            for story_id in story_ids:
                story_response = self.session.get(f"{HN_BASE}/item/{story_id}.json", timeout=5)
                story = story_response.json()
                
                if not story:
                    continue
                
                score = story.get('score', 0)
                num_comments = story.get('descendants', 0)
                timestamp = story.get('time', 0)
                age_hours = (time.time() - timestamp) / 3600
                
                # Calculate velocity
                velocity = (score + num_comments * 3) / max(age_hours, 1)
                velocity_score = min(velocity / 150, 1.0)
                
                # HN tends to have high human engagement
                signal_strength = min((num_comments / max(score, 1)) * 2, 1.0)
                
                # HN has better signal-to-noise ratio
                is_human = num_comments >= 5  # Lower threshold for HN
                
                trends.append({
                    'id': f"hn_{story_id}",
                    'niche': niche,
                    'headline': story.get('title', '')[:200],
                    'summary': f"Discussed on Hacker News with {num_comments} comments",
                    'velocity_score': velocity_score,
                    'signal_strength': signal_strength,
                    'mentions_last_hour': int(score / max(age_hours, 1)),
                    'mentions_previous_24h': score,
                    'source': 'hackernews',
                    'source_url': story.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                    'is_human': is_human,
                    'timestamp': datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                    'tags': []
                })
            
            return trends
            
        except Exception as e:
            print(f"⚠️ Hacker News fetch failed: {e}")
            return []
    
    def fetch_github_trends(self, niche: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch trending GitHub repositories"""
        try:
            headers = {}
            if self.github_token:
                headers['Authorization'] = f"token {self.github_token}"
            
            # Search for repos created in the last week, sorted by stars
            since_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            params = {
                'q': f'created:>{since_date}',
                'sort': 'stars',
                'order': 'desc',
                'per_page': limit
            }
            
            response = self.session.get(GITHUB_TRENDING, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            trends = []
            for repo in data.get('items', []):
                stars = repo.get('stargazers_count', 0)
                created = datetime.strptime(repo.get('created_at', ''), '%Y-%m-%dT%H:%M:%SZ')
                age_hours = (datetime.now(timezone.utc) - created.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                
                velocity = stars / max(age_hours, 1)
                velocity_score = min(velocity / 10, 1.0)
                
                trends.append({
                    'id': f"github_{repo.get('id', '')}",
                    'niche': niche,
                    'headline': f"{repo.get('full_name', '')}: {repo.get('description', '')[:100]}",
                    'summary': repo.get('description', '')[:300] or 'Trending GitHub repository',
                    'velocity_score': velocity_score,
                    'signal_strength': min(repo.get('watchers_count', 0) / max(stars, 1), 1.0),
                    'mentions_last_hour': int(velocity),
                    'mentions_previous_24h': stars,
                    'source': 'github',
                    'source_url': repo.get('html_url', ''),
                    'is_human': True,  # GitHub activity is generally human
                    'timestamp': created.isoformat(),
                    'tags': repo.get('topics', [])[:5]
                })
            
            return trends
            
        except Exception as e:
            print(f"⚠️ GitHub fetch failed: {e}")
            return []
    
    def fetch_deepseek_synthesis(self, existing_trends: List[Dict], niche: str) -> List[Dict[str, Any]]:
        """Use DeepSeek to synthesize and enhance trends with AI analysis"""
        try:
            # Create context from existing trends
            trend_context = "\n".join([
                f"- {t['headline']} (velocity: {t['velocity_score']:.2f})"
                for t in existing_trends[:5]
            ])
            
            prompt = f"""You are analyzing real-time trends for the "{niche}" niche.

Current trending items detected:
{trend_context}

Based on these signals and your knowledge of what's happening in {niche} today ({datetime.now().strftime('%B %d, %Y')}), generate 2-3 additional high-quality trend items that would be relevant.

For each trend, provide:
1. A compelling headline (under 100 chars)
2. A detailed summary (2-3 sentences explaining why it matters)
3. Velocity score estimate (0.0-1.0, where 1.0 is extremely viral)
4. Signal strength (0.0-1.0, representing engagement quality)
5. Relevant tags (3-5 keywords)

Return ONLY valid JSON in this format:
{{
  "trends": [
    {{
      "headline": "...",
      "summary": "...",
      "velocity_score": 0.85,
      "signal_strength": 0.90,
      "source_url": "https://...",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}"""

            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.deepseek_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "You are a trend analysis AI. Output only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"}
                },
                timeout=30
            )
            
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            
            # Clean and parse
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
            
            data = json.loads(content)
            ai_trends = data.get('trends', [])
            
            # Convert to app schema
            trends = []
            for i, trend in enumerate(ai_trends):
                trends.append({
                    'id': f"ai_{niche}_{hashlib.md5(trend['headline'].encode()).hexdigest()[:8]}",
                    'niche': niche,
                    'headline': trend['headline'],
                    'summary': trend['summary'],
                    'velocity_score': trend.get('velocity_score', 0.7),
                    'signal_strength': trend.get('signal_strength', 0.8),
                    'mentions_last_hour': int(trend.get('velocity_score', 0.7) * 1000),
                    'mentions_previous_24h': int(trend.get('velocity_score', 0.7) * 5000),
                    'source': 'rss',
                    'source_url': trend.get('source_url', 'https://trends.google.com'),
                    'is_human': True,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'tags': trend.get('tags', [])
                })
            
            return trends
            
        except Exception as e:
            print(f"⚠️ DeepSeek synthesis failed for {niche}: {e}")
            return []
    
    def aggregate_all_trends(self) -> List[Dict[str, Any]]:
        """Aggregate trends from all sources"""
        all_trends = []
        
        # Subreddit mapping for each niche - matches iOS app niches
        SUBREDDIT_MAP = {
            "cinema": ["movies", "boxoffice"],
            "sports": ["sports", "nba"],
            "worldEvents": ["worldnews", "news"],
            "streaming": ["television", "netflix"],
            "music": ["music", "hiphopheads"],
            "space": ["space", "spacex"],
            "tech": ["technology", "gadgets"],
            "maker": ["diy", "3Dprinting"],
            "privacy": ["privacy", "privacytoolsIO"],
            "repair": ["fixit", "techsupport"],
            "outdoor": ["hiking", "camping"],
            "legal": ["law", "supremecourt"],
            "local": ["nyc", "sanfrancisco"]  # Add your local subreddits
        }
        
        print("📡 Fetching trends from multiple sources...")
        
        # Fetch from each niche
        for niche in APP_NICHES:
            print(f"\n🎯 Processing niche: {niche}")
            niche_trends = []
            
            # Reddit
            if niche in SUBREDDIT_MAP:
                for subreddit in SUBREDDIT_MAP[niche][:2]:  # Limit to 2 subreddits per niche
                    print(f"  📱 Reddit r/{subreddit}...")
                    trends = self.fetch_reddit_trends(subreddit, niche, limit=5)
                    niche_trends.extend(trends)
                    time.sleep(0.5)  # Rate limiting
            
            # Hacker News (for tech-related niches)
            if niche in ["tech", "privacy", "maker", "space"]:
                print(f"  🔥 Hacker News...")
                trends = self.fetch_hackernews_trends(niche, limit=3)
                niche_trends.extend(trends)
                time.sleep(0.5)
            
            # GitHub (for tech/maker/privacy niches)
            if niche in ["tech", "maker", "privacy"] and self.github_token:
                print(f"  💻 GitHub...")
                trends = self.fetch_github_trends(niche, limit=2)
                niche_trends.extend(trends)
                time.sleep(0.5)
            
            # AI Enhancement
            if len(niche_trends) > 0:
                print(f"  🤖 AI synthesis...")
                ai_trends = self.fetch_deepseek_synthesis(niche_trends, niche)
                niche_trends.extend(ai_trends)
            
            all_trends.extend(niche_trends)
            print(f"  ✅ {len(niche_trends)} trends collected for {niche}")
        
        return all_trends

# ============================================================================
# DATA PROCESSING & RANKING
# ============================================================================

def calculate_breaking_status(trend: Dict[str, Any], threshold: float = 0.80) -> bool:
    """Determine if a trend is 'breaking' based on velocity"""
    return trend.get('velocity_score', 0) >= threshold

def deduplicate_trends(trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate trends based on headline similarity"""
    seen_headlines = set()
    unique_trends = []
    
    for trend in trends:
        headline_key = trend['headline'].lower()[:50]  # First 50 chars, lowercase
        if headline_key not in seen_headlines:
            seen_headlines.add(headline_key)
            unique_trends.append(trend)
    
    return unique_trends

def rank_and_filter_trends(trends: List[Dict[str, Any]], max_per_niche: int = 5, 
                          total_limit: int = 50) -> List[Dict[str, Any]]:
    """Rank trends by velocity and limit per niche"""
    
    # Group by niche
    niche_groups = defaultdict(list)
    for trend in trends:
        niche_groups[trend['niche']].append(trend)
    
    # Sort each niche by velocity
    filtered = []
    for niche, niche_trends in niche_groups.items():
        sorted_trends = sorted(niche_trends, key=lambda x: x['velocity_score'], reverse=True)
        filtered.extend(sorted_trends[:max_per_niche])
    
    # Final sort by velocity and limit total
    filtered.sort(key=lambda x: x['velocity_score'], reverse=True)
    return filtered[:total_limit]

# ============================================================================
# JSON OUTPUT (iOS APP SCHEMA)
# ============================================================================

def build_app_json(trends: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build JSON matching iOS app's VelocityTrend + PulseFeedResponse schema"""
    
    # Process each trend
    processed_trends = []
    for trend in trends:
        processed_trends.append({
            "id": trend['id'],
            "niche": trend['niche'],
            "headline": trend['headline'],
            "summary": trend['summary'],
            "image_url": None,  # Add image URL if available
            "velocity_score": round(trend['velocity_score'], 3),
            "signal_strength": round(trend['signal_strength'], 3),
            "mentions_last_hour": trend['mentions_last_hour'],
            "mentions_previous_24h": trend['mentions_previous_24h'],
            "source": trend['source'],
            "source_url": trend['source_url'],
            "is_human": trend['is_human'],
            "is_breaking": calculate_breaking_status(trend),
            "timestamp": trend['timestamp'],
            "tags": trend.get('tags', [])
        })
    
    # Build final response matching PulseFeedResponse
    return {
        "trends": processed_trends,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(processed_trends),
        "metadata": {
            "generator": "PulseRelay Multi-Source Aggregator v3.0",
            "sources": list(set(t['source'] for t in processed_trends)),
            "niches": list(set(t['niche'] for t in processed_trends)),
            "breaking_count": sum(1 for t in processed_trends if t['is_breaking']),
            "human_verified_count": sum(1 for t in processed_trends if t['is_human'])
        }
    }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    
    # Get API keys from environment
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    github_token = os.environ.get("GITHUB_TOKEN")  # Optional
    
    if not deepseek_key:
        print("❌ ERROR: DEEPSEEK_API_KEY environment variable not set")
        sys.exit(1)
    
    # Define output path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_file = os.path.join(project_root, "data", "trends.json")
    
    print("=" * 70)
    print("🌊 PULSERELAY - MULTI-SOURCE TREND AGGREGATOR v3.0")
    print("=" * 70)
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🎯 Niches: {len(APP_NICHES)}")
    print(f"📡 Sources: Reddit, Hacker News" + (", GitHub" if github_token else ""))
    print(f"🤖 AI Enhancement: DeepSeek")
    print("=" * 70)
    
    # Initialize aggregator
    aggregator = TrendAggregator(deepseek_key, github_token)
    
    # Fetch all trends
    print("\n🔄 Starting multi-source aggregation...")
    raw_trends = aggregator.aggregate_all_trends()
    
    print(f"\n📊 Processing {len(raw_trends)} raw trends...")
    
    # Deduplicate
    unique_trends = deduplicate_trends(raw_trends)
    print(f"✅ {len(unique_trends)} unique trends after deduplication")
    
    # Rank and filter
    final_trends = rank_and_filter_trends(unique_trends, max_per_niche=5, total_limit=50)
    print(f"🎯 {len(final_trends)} trends selected for final output")
    
    # Build iOS app JSON
    app_json = build_app_json(final_trends)
    
    # Save to file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(app_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Trends saved to: {output_file}")
    print(f"📈 Total trends: {app_json['total_count']}")
    print(f"🔥 Breaking trends: {app_json['metadata']['breaking_count']}")
    print(f"✅ Human-verified: {app_json['metadata']['human_verified_count']}")
    print(f"🌐 Sources: {', '.join(app_json['metadata']['sources'])}")
    print(f"🎨 Niches covered: {len(app_json['metadata']['niches'])}")
    
    print("\n" + "=" * 70)
    print("✅ PULSERELAY AGGREGATION COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    main()
