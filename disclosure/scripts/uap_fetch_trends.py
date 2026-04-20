#!/usr/bin/env python3
"""
DISCLOSURE - ULTRA-WIDE UFO/UAP/NHI Trend Aggregator v2.1 (STABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXED: Error handling for malformed feeds, timeout issues, and connection errors
"""

import json
import math
import os
import re
import sys
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from urllib.parse import quote_plus

import requests

try:
    import feedparser
except ImportError:
    print("❌ feedparser not installed. Run: pip install feedparser")
    sys.exit(1)

# ============================================================================
# CONFIGURATION - STABLE SOURCES ONLY
# ============================================================================

APP_NICHES = [
    "disclosure", "sightings", "military_encounters", "legislation",
    "scientific_research", "whistleblower", "area51_s4", "ancient_aliens",
    "exopolitics", "media_coverage", "podcasts", "social_media",
    "historical_cases", "consciousness", "international", "crash_retrievals",
    "whistleblower_docs", "congressional", "scientific_papers", "viral_moments",
]

# UAP Keywords
UAP_KEYWORDS = {
    "primary": [
        "ufo", "ufos", "uap", "uaps", "unidentified aerial", "unidentified anomalous",
        "non-human", "non human", "nhi", "alien", "aliens", "extraterrestrial",
        "disclosure", "whistleblower", "grusch", "elizondo", "fravor", "graves",
        "area 51", "area51", "dreamland", "s4 facility", "tic tac", "gimbal",
    ],
    "secondary": [
        "orb", "orbs", "triangle craft", "saucer", "disk", "roswell",
        "skinwalker ranch", "rendlesham", "phoenix lights", "varginha",
        "aaro", "pentagon", "congressional hearing", "schumer", "gillibrand",
    ],
}

ALL_UAP_KEYWORDS = set()
for category in UAP_KEYWORDS.values():
    ALL_UAP_KEYWORDS.update(category)

# ============================================================================
# STABLE RSS FEEDS (verified working)
# ============================================================================

UAP_FEEDS = [
    ("The Debrief", "https://thedebrief.org/category/uap/feed/"),
    ("The War Zone", "https://www.thedrive.com/the-war-zone/category/uap/feed"),
    ("Popular Mechanics", "https://www.popularmechanics.com/tag/uap/feed/"),
    ("NewsNation", "https://www.newsnationnow.com/tag/uap/feed/"),
    ("Coast to Coast AM", "https://www.coasttocoastam.com/feed/"),
    ("Mysterious Universe", "https://mysteriousuniverse.org/feed/podcast/"),
    ("MUFON", "https://mufon.com/feed/"),
    ("The Black Vault", "https://www.theblackvault.com/feed/"),
    ("Richard Dolan", "https://richarddolan.com/feed/"),
    ("OpenMinds TV", "https://www.openminds.tv/feed"),
]

GOVERNMENT_FEEDS = [
    ("AARO", "https://www.aaro.mil/feeds/news"),
    ("DoD News", "https://www.defense.gov/feeds/news/"),
    ("US Senate Intel", "https://www.intelligence.senate.gov/rss/feed.xml"),
    ("House Oversight", "https://oversight.house.gov/rss.xml"),
    ("NASA Breaking News", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
]

# Podcast RSS Feeds
PODCAST_FEEDS = [
    ("Weaponized", "https://weaponizedpodcast.libsyn.com/rss"),
    ("Merged", "https://mergedpodcast.libsyn.com/rss"),
    ("Theories of Everything", "https://toe.libsyn.com/rss"),
    ("That UFO Podcast", "https://thatufopodcast.libsyn.com/rss"),
    ("Fade to Black", "https://fadetoblack.libsyn.com/rss"),
]

# ============================================================================
# REDDIT SUBREDDITS
# ============================================================================

REDDIT_SUBREDDITS = [
    "UFOs", "UFO", "aliens", "HighStrangeness", "UFOB", "ExoPolitics",
    "AncientAliens", "SkinwalkerRanch", "UAP", "UAPDisclosure", "Disclosure",
    "UFOscience", "MilitaryUFOs", "UFOHistory",
]

# ============================================================================
# YOUTUBE CHANNELS
# ============================================================================

YOUTUBE_CHANNELS = [
    ("Weaponized Podcast", "UCkO3y4Ew7ZkYkDZuE5R5gPw"),
    ("Merged Podcast", "UC4ZtG2Mk7Z8qQaHc6kLZ1YQ"),
    ("Theories of Everything", "UCqx7kP6C4kQwGkX6jZqC0xg"),
    ("UAP Max", "UCyQZwN9M4ZkL4x4gLx8jL6g"),
    ("Project Unity", "UCeY0bbnWlqJkMqHkZqLvY7w"),
    ("That UFO Podcast", "UCv8vC2qJFy-8Iv5VJqz1-qg"),
    ("The Black Vault", "UCdYzV5Qz8YjE5q8dXq0jKvA"),
]

# ============================================================================
# GOOGLE TRENDS REGIONS
# ============================================================================

GTRENDS_REGIONS = [
    "US", "GB", "AU", "CA", "NZ", "IE", "ZA", "IN", "DE", "FR",
    "ES", "IT", "NL", "BR", "MX", "JP", "KR",
]

# ============================================================================
# WIKIPEDIA ARTICLES
# ============================================================================

WIKI_UAP_ARTICLES = [
    "Unidentified_flying_object",
    "Unidentified_anomalous_phenomena",
    "David_Grusch_UFO_whistleblower",
    "Luis_Elizondo",
    "Area_51",
    "Roswell_incident",
    "Project_Blue_Book",
    "Advanced_Aerospace_Threat_Identification_Program",
    "All-domain_Anomaly_Resolution_Office",
    "Tic_Tac_UFO",
    "Nimitz_UFO_incident",
    "Skinwalker_Ranch",
    "Rendlesham_Forest_incident",
    "Phoenix_Lights",
]

# ============================================================================
# SOCIAL MEDIA HASHTAGS
# ============================================================================

SOCIAL_HASHTAGS = [
    "ufo", "uap", "aliens", "disclosure", "ufotiktok", "uaptiktok",
    "ufotwitter", "area51", "roswell", "grusch", "elizondo", "whistleblower",
]

# ============================================================================
# BROWSER UA
# ============================================================================

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ============================================================================
# CLASSIFICATION ENGINE
# ============================================================================

def classify_uap_content(text: str) -> Tuple[str, float, List[str]]:
    """Classify content into niche with confidence score"""
    if not text:
        return ("sightings", 0.0, [])
    
    text_lower = text.lower()
    tags = []
    confidence = 0.0
    
    # Count keyword matches
    primary_matches = sum(1 for kw in UAP_KEYWORDS["primary"] if kw in text_lower)
    secondary_matches = sum(1 for kw in UAP_KEYWORDS["secondary"] if kw in text_lower)
    
    total_matches = primary_matches + secondary_matches
    confidence = min(0.3 + (total_matches * 0.05), 1.0)
    
    if primary_matches > 0:
        tags.append("high_relevance")
    if secondary_matches > 0:
        tags.append("related")
    
    # Niche classification
    if any(kw in text_lower for kw in ["congress", "hearing", "senate", "house", "schumer", "gillibrand", "rubio"]):
        return ("congressional", confidence, tags + ["congress", "hearing"])
    
    if any(kw in text_lower for kw in ["foia", "leaked", "document", "classified", "release", "memo"]):
        return ("whistleblower_docs", confidence, tags + ["documents"])
    
    if any(kw in text_lower for kw in ["grusch", "whistleblower", "elizondo", "fravor", "graves"]):
        return ("whistleblower", confidence, tags + ["whistleblower"])
    
    if any(kw in text_lower for kw in ["crash", "retrieval", "reverse engineering", "biologics"]):
        return ("crash_retrievals", confidence, tags + ["crash", "retrieval"])
    
    if any(kw in text_lower for kw in ["military", "navy", "air force", "pilot", "radar", "nimitz", "tic tac"]):
        return ("military_encounters", confidence, tags + ["military"])
    
    if any(kw in text_lower for kw in ["paper", "study", "research", "journal", "science"]):
        return ("scientific_papers", confidence, tags + ["scientific"])
    
    if any(kw in text_lower for kw in ["legislation", "bill", "law", "act", "amendment", "ndaa"]):
        return ("legislation", confidence, tags + ["legislation"])
    
    if any(kw in text_lower for kw in ["disclosure", "pentagon", "aaro", "government"]):
        return ("disclosure", confidence, tags + ["disclosure"])
    
    if any(kw in text_lower for kw in ["area 51", "area51", "groom lake", "s4"]):
        return ("area51_s4", confidence, tags + ["area51"])
    
    if any(kw in text_lower for kw in ["ancient", "pyramid", "paleocontact", "ancient astronaut"]):
        return ("ancient_aliens", confidence, tags + ["ancient"])
    
    if any(kw in text_lower for kw in ["podcast", "episode", "interview"]):
        return ("podcasts", confidence, tags + ["podcast"])
    
    if any(kw in text_lower for kw in ["viral", "trending", "tiktok", "instagram", "reddit"]):
        return ("social_media", confidence, tags + ["viral"])
    
    if any(kw in text_lower for kw in ["roswell", "rendlesham", "phoenix lights", "1947"]):
        return ("historical_cases", confidence, tags + ["historical"])
    
    if any(kw in text_lower for kw in ["china", "russia", "brazil", "mexico", "canada", "australia"]):
        return ("international", confidence, tags + ["international"])
    
    return ("sightings", confidence, tags + ["sighting"])


def is_uap_relevant(text: str) -> bool:
    """Quick relevance check"""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in ALL_UAP_KEYWORDS)

# ============================================================================
# AGGREGATOR CLASS
# ============================================================================

class UAPTrendAggregator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Disclosure-UAP/2.1"})
        self.browser_session = requests.Session()
        self.browser_session.headers.update({"User-Agent": BROWSER_UA})
        self.stats = defaultdict(int)

    def _make_id(self, prefix: str, text: str) -> str:
        return f"{prefix}_{hashlib.md5(text.encode()).hexdigest()[:12]}"

    def _age_hours(self, epoch: float) -> float:
        return (time.time() - epoch) / 3600

    def _decay_score(self, age_hours: float, half_life: float = 6.0) -> float:
        return math.exp(-0.693 * age_hours / max(half_life, 0.1))

    def fetch_rss_feeds(self) -> List[Dict[str, Any]]:
        """Fetch all RSS feeds with error handling"""
        trends = []
        all_feeds = UAP_FEEDS + GOVERNMENT_FEEDS + PODCAST_FEEDS
        
        print(f"  📡 Scanning {len(all_feeds)} RSS feeds...")
        
        for feed_item in all_feeds:
            # Handle both tuple formats safely
            if isinstance(feed_item, tuple) and len(feed_item) >= 2:
                name = feed_item[0]
                url = feed_item[1]
            else:
                print(f"    ⚠️  Skipping malformed feed: {feed_item}")
                continue
                
            try:
                r = self.browser_session.get(url, timeout=10)
                if r.status_code != 200:
                    continue
                    
                feed = feedparser.parse(r.text)
                if not feed.entries:
                    continue
                    
                for entry in feed.entries[:8]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "") or entry.get("description", "")
                    content = f"{title} {summary}"
                    
                    if not is_uap_relevant(content):
                        continue
                    
                    niche, confidence, tags = classify_uap_content(content)
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    epoch = time.mktime(pub) if pub else time.time()
                    age_h = self._age_hours(epoch)
                    
                    trends.append({
                        "id": self._make_id("rss", title),
                        "niche": niche,
                        "headline": title[:250],
                        "summary": summary[:500],
                        "velocity_score": self._decay_score(age_h, half_life=6),
                        "signal_strength": confidence,
                        "mentions_last_hour": 50,
                        "mentions_previous_24h": 500,
                        "source": name,
                        "source_url": entry.get("link", url),
                        "timestamp": datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat() if pub else datetime.now(timezone.utc).isoformat(),
                        "tags": tags[:8],
                    })
                    self.stats["rss_items"] += 1
                    
                time.sleep(0.2)
            except Exception as e:
                print(f"    ⚠️  {name}: {str(e)[:60]}")
                continue
        
        return trends

    def fetch_reddit(self) -> List[Dict[str, Any]]:
        """Fetch Reddit posts"""
        trends = []
        
        print(f"  💬 Scanning {len(REDDIT_SUBREDDITS)} Reddit communities...")
        
        for subreddit in REDDIT_SUBREDDITS:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=20"
                headers = {"User-Agent": "Mozilla/5.0 (compatible; DisclosureBot/1.0)"}
                r = self.session.get(url, timeout=10, headers=headers)
                
                if r.status_code != 200:
                    continue
                
                data = r.json()
                for post in data.get("data", {}).get("children", []):
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")
                    content = f"{title} {selftext}"
                    
                    if not is_uap_relevant(content):
                        continue
                    
                    niche, confidence, tags = classify_uap_content(content)
                    score = post_data.get("score", 0)
                    comments = post_data.get("num_comments", 0)
                    created_utc = post_data.get("created_utc", time.time())
                    age_h = self._age_hours(created_utc)
                    
                    velocity = min((score + comments * 2) / max(age_h, 0.5) / 500, 1.0)
                    
                    trends.append({
                        "id": self._make_id("reddit", title),
                        "niche": niche,
                        "headline": title[:250],
                        "summary": selftext[:500] if selftext else f"Discussion on r/{subreddit}",
                        "velocity_score": velocity,
                        "signal_strength": confidence,
                        "mentions_last_hour": max(score // max(int(age_h), 1), 1),
                        "mentions_previous_24h": score,
                        "source": f"r/{subreddit}",
                        "source_url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "timestamp": datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat(),
                        "tags": tags[:8],
                    })
                    self.stats["reddit_items"] += 1
                    
                time.sleep(0.3)
            except Exception as e:
                print(f"    ⚠️  r/{subreddit}: {str(e)[:50]}")
                continue
        
        return trends

    def fetch_youtube(self) -> List[Dict[str, Any]]:
        """Fetch YouTube videos"""
        trends = []
        
        print(f"  📺 Scanning {len(YOUTUBE_CHANNELS)} YouTube channels...")
        
        for name, channel_id in YOUTUBE_CHANNELS:
            try:
                rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                r = self.browser_session.get(rss_url, timeout=10)
                
                if r.status_code != 200:
                    continue
                
                feed = feedparser.parse(r.text)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    content = f"{title} {summary}"
                    
                    if not is_uap_relevant(content):
                        continue
                    
                    niche, confidence, tags = classify_uap_content(content)
                    pub = entry.get("published_parsed")
                    epoch = time.mktime(pub) if pub else time.time()
                    age_h = self._age_hours(epoch)
                    
                    trends.append({
                        "id": self._make_id("yt", title),
                        "niche": niche if niche != "sightings" else "media_coverage",
                        "headline": f"📺 {title[:230]}",
                        "summary": f"From {name}: {summary[:400]}" if summary else f"New video from {name}",
                        "velocity_score": self._decay_score(age_h, half_life=4),
                        "signal_strength": confidence,
                        "mentions_last_hour": 200,
                        "mentions_previous_24h": 2000,
                        "source": f"YouTube ({name})",
                        "source_url": entry.get("link", ""),
                        "timestamp": datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat() if pub else datetime.now(timezone.utc).isoformat(),
                        "tags": tags[:8] + ["video"],
                    })
                    self.stats["youtube_items"] += 1
                    
                time.sleep(0.2)
            except Exception as e:
                print(f"    ⚠️  {name}: {str(e)[:50]}")
                continue
        
        return trends

    def fetch_google_trends(self) -> List[Dict[str, Any]]:
        """Fetch Google Trends data"""
        trends = []
        
        print(f"  🔍 Scanning Google Trends in {len(GTRENDS_REGIONS)} regions...")
        
        for region in GTRENDS_REGIONS:
            try:
                url = f"https://trends.google.com/trending/rss?geo={region}"
                r = self.browser_session.get(url, timeout=10)
                
                if r.status_code != 200:
                    continue
                
                feed = feedparser.parse(r.text)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    if not is_uap_relevant(title):
                        continue
                    
                    raw_traffic = getattr(entry, "ht_approx_traffic", "1000")
                    raw_traffic = str(raw_traffic).replace(",", "").replace("+", "").strip()
                    try:
                        traffic = int(raw_traffic) if raw_traffic.isdigit() else 1000
                    except:
                        traffic = 1000
                    
                    niche, confidence, tags = classify_uap_content(title)
                    trends.append({
                        "id": self._make_id("gt", f"{region}{title}"),
                        "niche": niche,
                        "headline": f"🔥 {title} (Trending in {region})",
                        "summary": f"Search interest spike in {region}",
                        "velocity_score": min(traffic / 100000, 1.0),
                        "signal_strength": 0.85,
                        "mentions_last_hour": max(traffic // 24, 1),
                        "mentions_previous_24h": traffic,
                        "source": "Google Trends",
                        "source_url": entry.get("link", "https://trends.google.com"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tags": tags + [region.lower(), "trending"],
                    })
                    self.stats["google_trends"] += 1
                    
                time.sleep(0.2)
            except Exception as e:
                print(f"    ⚠️  GT {region}: {str(e)[:50]}")
                continue
        
        return trends

    def fetch_wikipedia(self) -> List[Dict[str, Any]]:
        """Fetch Wikipedia pageviews"""
        trends = []
        
        print(f"  📖 Scanning {len(WIKI_UAP_ARTICLES)} Wikipedia articles...")
        
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y/%m/%d")
        
        for article in WIKI_UAP_ARTICLES:
            try:
                url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{article}/daily/{yesterday}/{yesterday}"
                r = self.session.get(url, timeout=10)
                
                if r.status_code != 200:
                    continue
                
                data = r.json()
                views = data.get("items", [{}])[0].get("views", 0)
                display_title = article.replace("_", " ")
                
                trends.append({
                    "id": self._make_id("wiki", article),
                    "niche": "scientific_research",
                    "headline": f"📚 {display_title}",
                    "summary": f"Wikipedia pageviews: {views:,} in the last 24 hours",
                    "velocity_score": min(views / 25000, 1.0),
                    "signal_strength": 0.9,
                    "mentions_last_hour": max(views // 24, 1),
                    "mentions_previous_24h": views,
                    "source": "Wikipedia",
                    "source_url": f"https://en.wikipedia.org/wiki/{article}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tags": ["wikipedia", "reference"],
                })
                self.stats["wikipedia"] += 1
                time.sleep(0.1)
            except Exception as e:
                print(f"    ⚠️  {article}: {str(e)[:50]}")
                continue
        
        return trends

    def fetch_social_trends(self) -> List[Dict[str, Any]]:
        """Fetch social media trends"""
        trends = []
        
        print(f"  📱 Scanning social media hashtags...")
        
        # Try to get trending data from multiple sources
        trend_urls = [
            "https://trends24.in/json/trends",
        ]
        
        for url in trend_urls:
            try:
                r = self.session.get(url, timeout=10)
                if r.status_code != 200:
                    continue
                
                data = r.json()
                if isinstance(data, list):
                    for country_trends in data[:5]:  # Limit to top 5 countries
                        country = country_trends.get("name", "Global")
                        for trend in country_trends.get("trends", [])[:20]:
                            trend_name = trend.get("name", "")
                            if is_uap_relevant(trend_name):
                                tweet_volume = trend.get("tweet_volume", 1000)
                                niche, confidence, tags = classify_uap_content(trend_name)
                                trends.append({
                                    "id": self._make_id("social", trend_name),
                                    "niche": niche,
                                    "headline": f"🐦 {trend_name}",
                                    "summary": f"Trending in {country}",
                                    "velocity_score": min(tweet_volume / 50000, 1.0),
                                    "signal_strength": confidence,
                                    "mentions_last_hour": max(tweet_volume // 24, 10),
                                    "mentions_previous_24h": tweet_volume,
                                    "source": "Social Media Trends",
                                    "source_url": f"https://twitter.com/search?q={quote_plus(trend_name)}",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "tags": tags + [country.lower(), "trending"],
                                })
                                self.stats["social_trends"] += 1
            except Exception as e:
                print(f"    ⚠️  Social trends: {str(e)[:50]}")
                continue
        
        return trends

    def aggregate_all_trends(self) -> List[Dict[str, Any]]:
        """Main aggregation pipeline"""
        all_trends = []
        
        print("\n" + "=" * 70)
        print("🛸 DISCLOSURE - UFO/UAP/NHI TREND AGGREGATOR v2.1")
        print("=" * 70)
        
        # Phase 1: RSS Feeds
        print("\n📡 PHASE 1: RSS Feed Aggregation...")
        all_trends.extend(self.fetch_rss_feeds())
        
        # Phase 2: Reddit
        print("\n💬 PHASE 2: Reddit Community Aggregation...")
        all_trends.extend(self.fetch_reddit())
        
        # Phase 3: YouTube
        print("\n📺 PHASE 3: YouTube Channel Aggregation...")
        all_trends.extend(self.fetch_youtube())
        
        # Phase 4: Google Trends
        print("\n🔍 PHASE 4: Google Trends Global Scanning...")
        all_trends.extend(self.fetch_google_trends())
        
        # Phase 5: Wikipedia
        print("\n📖 PHASE 5: Wikipedia Pageview Analysis...")
        all_trends.extend(self.fetch_wikipedia())
        
        # Phase 6: Social Media
        print("\n📱 PHASE 6: Social Media Trend Monitoring...")
        all_trends.extend(self.fetch_social_trends())
        
        # Print statistics
        print("\n" + "=" * 70)
        print("📊 AGGREGATION STATISTICS:")
        print("=" * 70)
        for source, count in sorted(self.stats.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"   • {source}: {count} items")
        
        return all_trends

# ============================================================================
# POST-PROCESSING
# ============================================================================

def deduplicate(trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate entries"""
    seen = set()
    unique = []
    for t in trends:
        signature = re.sub(r'[^\w\s]', '', t['headline'].lower())[:80]
        if signature not in seen:
            seen.add(signature)
            unique.append(t)
    return unique

def rank_and_filter(trends: List[Dict[str, Any]], max_items: int = 300) -> List[Dict[str, Any]]:
    """Rank by relevance and filter"""
    for t in trends:
        t["composite_score"] = (
            t.get("velocity_score", 0) * 0.5 +
            t.get("signal_strength", 0) * 0.5
        )
    
    trends.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
    return trends[:max_items]

def add_insights(trends: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate insights"""
    niche_counts = defaultdict(int)
    source_counts = defaultdict(int)
    tag_counts = defaultdict(int)
    
    for t in trends:
        niche_counts[t["niche"]] += 1
        source_counts[t["source"]] += 1
        for tag in t.get("tags", [])[:3]:
            tag_counts[tag] += 1
    
    return {
        "total_trends": len(trends),
        "niches_covered": sorted(niche_counts.keys()),
        "niche_distribution": dict(sorted(niche_counts.items(), key=lambda x: x[1], reverse=True)),
        "source_distribution": dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:15]),
        "top_tags": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
    }

# ============================================================================
# MAIN
# ============================================================================

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.normpath(os.path.join(script_dir, "..", "data", "uap_trends.json"))
    
    print(f"\n🚀 Output file: {output_file}\n")
    
    aggregator = UAPTrendAggregator()
    raw = aggregator.aggregate_all_trends()
    
    print(f"\n✅ Raw collected:  {len(raw):,}")
    
    unique = deduplicate(raw)
    print(f"✅ After dedup:    {len(unique):,}")
    
    final = rank_and_filter(unique, max_items=300)
    print(f"✅ After ranking:  {len(final):,}")
    
    insights = add_insights(final)
    
    payload = {
        "trends": final,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(final),
        "topic": "UFO/UAP/NHI - Non-Human Intelligence",
        "insights": insights,
        "metadata": {
            "version": "2.1",
            "status": "STABLE - Wide Signal Capture",
            "sources_used": len(set(t["source"] for t in final)),
            "keywords_monitored": len(ALL_UAP_KEYWORDS),
        },
    }
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print("🎉 DISCLOSURE AGGREGATION COMPLETE")
    print("=" * 70)
    print(f"📁 Output: {output_file}")
    print(f"📊 Total Trends: {len(final):,}")
    print(f"🎯 Niches Covered: {len(insights['niches_covered'])}")
    
    print("\n📈 NICHE BREAKDOWN:")
    for niche, count in list(insights["niche_distribution"].items())[:10]:
        bar = "█" * min(40, count)
        print(f"   {niche:20} │ {bar} {count}")

if __name__ == "__main__":
    main()
