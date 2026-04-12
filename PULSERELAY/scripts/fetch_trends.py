To expand the scope and increase the volume to a **150-article limit** with better global news coverage, I’ve overhauled the logic. 

Key changes include:
* **Increased Limits:** Now pulls more per source and allows up to 150 total.
* **Global News Boost:** Added `worldnews`, `internationalnews`, and `europe` to the mapping.
* **Enhanced Diversity:** Added a `breakingNews` niche to the `APP_NICHES` list.
* **Optimized AI:** The DeepSeek synthesis now generates 5 trends per niche instead of 2.

```python
#!/usr/bin/env python3
"""
PulseRelay - Multi-Source Real-Time Trend Aggregator v4.0
Expanded version: 150-article capacity & Enhanced Global News Coverage
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

APP_NICHES = [
    "breakingNews", "cinema", "sports", "worldEvents", "streaming", "music",
    "space", "tech", "maker", "privacy", "repair",
    "outdoor", "legal", "local"
]

REDDIT_BASE = "https://www.reddit.com"
HN_BASE = "https://hacker-news.firebaseio.com/v0"
GITHUB_TRENDING = "https://api.github.com/search/repositories"

# ============================================================================
# MULTI-SOURCE DATA FETCHERS
# ============================================================================

class TrendAggregator:
    def __init__(self, deepseek_key: str, github_token: Optional[str] = None):
        self.deepseek_key = deepseek_key
        self.github_token = github_token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PulseRelay/4.0 (iOS Trend Aggregator Expanded)'
        })
    
    def fetch_reddit_trends(self, subreddit: str, niche: str, limit: int = 15) -> List[Dict[str, Any]]:
        try:
            url = f"{REDDIT_BASE}/r/{subreddit}/hot.json?limit={limit}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            trends = []
            for post in data.get('data', {}).get('children', []):
                post_data = post.get('data', {})
                score = post_data.get('score', 0)
                num_comments = post_data.get('num_comments', 0)
                created = post_data.get('created_utc', 0)
                age_hours = (time.time() - created) / 3600
                
                velocity = (score + num_comments * 2) / max(age_hours, 1)
                velocity_score = min(velocity / 100, 1.0)
                
                trends.append({
                    'id': f"reddit_{post_data.get('id', '')}",
                    'niche': niche,
                    'headline': post_data.get('title', '')[:200],
                    'summary': post_data.get('selftext', '')[:300] or f"Trending on r/{subreddit}",
                    'velocity_score': velocity_score,
                    'signal_strength': min(num_comments / max(score, 1), 1.0),
                    'mentions_last_hour': int(score / max(age_hours, 1)),
                    'mentions_previous_24h': score,
                    'source': 'reddit',
                    'source_url': f"https://reddit.com{post_data.get('permalink', '')}",
                    'is_human': num_comments >= 10,
                    'timestamp': datetime.fromtimestamp(created, timezone.utc).isoformat(),
                    'tags': post_data.get('link_flair_text', '').split() if post_data.get('link_flair_text') else []
                })
            return trends
        except Exception as e:
            print(f"⚠️ Reddit r/{subreddit} failed: {e}")
            return []

    def fetch_hackernews_trends(self, niche: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            response = self.session.get(f"{HN_BASE}/topstories.json", timeout=10)
            story_ids = response.json()[:limit]
            trends = []
            for story_id in story_ids:
                story = self.session.get(f"{HN_BASE}/item/{story_id}.json", timeout=5).json()
                if not story: continue
                
                score = story.get('score', 0)
                num_comments = story.get('descendants', 0)
                age_hours = (time.time() - story.get('time', 0)) / 3600
                velocity_score = min(((score + num_comments * 3) / max(age_hours, 1)) / 150, 1.0)
                
                trends.append({
                    'id': f"hn_{story_id}",
                    'niche': niche,
                    'headline': story.get('title', ''),
                    'summary': f"Discussed on Hacker News with {num_comments} comments",
                    'velocity_score': velocity_score,
                    'signal_strength': min((num_comments / max(score, 1)) * 2, 1.0),
                    'mentions_last_hour': int(score / max(age_hours, 1)),
                    'mentions_previous_24h': score,
                    'source': 'hackernews',
                    'source_url': story.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                    'is_human': True,
                    'timestamp': datetime.fromtimestamp(story.get('time', 0), timezone.utc).isoformat(),
                    'tags': []
                })
            return trends
        except Exception as e:
            print(f"⚠️ HN failed: {e}")
            return []

    def fetch_github_trends(self, niche: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            headers = {'Authorization': f"token {self.github_token}"} if self.github_token else {}
            since_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            params = {'q': f'created:>{since_date}', 'sort': 'stars', 'order': 'desc', 'per_page': limit}
            response = self.session.get(GITHUB_TRENDING, params=params, headers=headers, timeout=10)
            
            trends = []
            for repo in response.json().get('items', []):
                trends.append({
                    'id': f"github_{repo.get('id', '')}",
                    'niche': niche,
                    'headline': f"{repo.get('full_name', '')}",
                    'summary': repo.get('description', '')[:300],
                    'velocity_score': 0.8,
                    'signal_strength': 0.9,
                    'mentions_last_hour': 10,
                    'mentions_previous_24h': repo.get('stargazers_count', 0),
                    'source': 'github',
                    'source_url': repo.get('html_url', ''),
                    'is_human': True,
                    'timestamp': repo.get('created_at'),
                    'tags': repo.get('topics', [])
                })
            return trends
        except Exception as e:
            print(f"⚠️ GitHub failed: {e}")
            return []

    def fetch_deepseek_synthesis(self, existing_trends: List[Dict], niche: str) -> List[Dict[str, Any]]:
        try:
            trend_context = "\n".join([f"- {t['headline']}" for t in existing_trends[:10]])
            prompt = f"Analyze these trends for '{niche}':\n{trend_context}\nGenerate 5 more unique, high-velocity trends for today. Output ONLY JSON with a 'trends' array."
            
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.deepseek_key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "system", "content": "You are a news aggregator. Output JSON."}, {"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                }, timeout=30
            )
            data = response.json()
            ai_trends = json.loads(data['choices'][0]['message']['content']).get('trends', [])
            
            results = []
            for t in ai_trends:
                results.append({
                    'id': f"ai_{niche}_{hashlib.md5(t['headline'].encode()).hexdigest()[:8]}",
                    'niche': niche,
                    'headline': t['headline'],
                    'summary': t['summary'],
                    'velocity_score': t.get('velocity_score', 0.8),
                    'signal_strength': 0.85,
                    'mentions_last_hour': 500,
                    'mentions_previous_24h': 2000,
                    'source': 'rss',
                    'source_url': t.get('source_url', 'https://news.google.com'),
                    'is_human': True,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'tags': t.get('tags', [])
                })
            return results
        except Exception as e:
            print(f"⚠️ DeepSeek failed for {niche}: {e}")
            return []

    def aggregate_all_trends(self) -> List[Dict[str, Any]]:
        all_trends = []
        SUBREDDIT_MAP = {
            "breakingNews": ["news", "worldnews", "inthenews"],
            "worldEvents": ["worldnews", "internationalnews", "europe", "asia"],
            "cinema": ["movies", "boxoffice"],
            "sports": ["sports", "nba", "soccer"],
            "tech": ["technology", "gadgets", "artificial"],
            "space": ["space", "spacex"],
            "maker": ["diy", "3Dprinting", "raspberry_pi"],
            "privacy": ["privacy", "privacytoolsIO"],
            "outdoor": ["hiking", "camping"],
            "local": ["atlanta", "georgia"]
        }

        for niche in APP_NICHES:
            print(f"🔄 Aggregating {niche}...")
            niche_pool = []
            
            if niche in SUBREDDIT_MAP:
                for sub in SUBREDDIT_MAP[niche]:
                    niche_pool.extend(self.fetch_reddit_trends(sub, niche, limit=20))
                    time.sleep(0.5)

            if niche in ["tech", "privacy", "maker"]:
                niche_pool.extend(self.fetch_hackernews_trends(niche, limit=10))
                if self.github_token:
                    niche_pool.extend(self.fetch_github_trends(niche, limit=5))

            # Synthesize extra context
            if niche_pool:
                ai_batch = self.fetch_deepseek_synthesis(niche_pool, niche)
                niche_pool.extend(ai_batch)
            
            all_trends.extend(niche_pool)
        return all_trends

# ============================================================================
# PROCESSING
# ============================================================================

def deduplicate(trends):
    seen = set()
    unique = []
    for t in trends:
        key = t['headline'].lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique

def rank_and_filter(trends, max_per_niche=20, total_limit=150):
    niche_groups = defaultdict(list)
    for t in trends:
        niche_groups[t['niche']].append(t)
    
    final = []
    for niche in niche_groups:
        sorted_niche = sorted(niche_groups[niche], key=lambda x: x['velocity_score'], reverse=True)
        final.extend(sorted_niche[:max_per_niche])
    
    final.sort(key=lambda x: x['velocity_score'], reverse=True)
    return final[:total_limit]

# ============================================================================
# MAIN
# ============================================================================

def main():
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    github_token = os.environ.get("GITHUB_TOKEN")
    
    if not deepseek_key:
        print("❌ DEEPSEEK_API_KEY Missing")
        sys.exit(1)

    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "trends.json")
    aggregator = TrendAggregator(deepseek_key, github_token)
    
    raw = aggregator.aggregate_all_trends()
    unique = deduplicate(raw)
    final = rank_and_filter(unique, max_per_niche=20, total_limit=150)
    
    payload = {
        "trends": final,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(final),
        "metadata": {
            "version": "4.0",
            "niches_covered": list(set(t['niche'] for t in final))
        }
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Success! Saved {len(final)} trends to {output_file}")

if __name__ == "__main__":
    main()
```
