#!/usr/bin/env python3
"""
Disclosure - UFO/UAP/NHI Trend Aggregator v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dedicated to tracking global discussions on:
  • UFO / UAP sightings and news
  • Non-Human Intelligence (NHI)
  • Government disclosure and whistleblowers
  • Area 51 and military encounters
  • Alien phenomena and exopolitics
  • Congressional hearings and legislation

All data stored in /disclosure/data/uap_trends.json
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
# CONFIGURATION
# ============================================================================

# UAP/UFO/NHI specific niches
APP_NICHES = [
    "disclosure",       # Government disclosure, whistleblowers, hearings
    "sightings",        # Recent UFO/UAP sightings worldwide
    "military",         # Military encounters, radar data, pilot reports
    "legislation",      # Laws, congressional actions, policy changes
    "scientific",       # Scientific analysis, papers, academic discussion
    "whistleblower",    # Grusch, Elizondo, Fravor, Graves, etc.
    "area51",           # Area 51, S4, Dreamland, covert bases
    "ancient_aliens",   # Ancient astronaut theory, paleocontact
    "exopolitics",      # International disclosure, global coordination
    "media_coverage",   # Mainstream media reporting on UAP
]

# UAP/UFO/NHI keywords for filtering
UAP_KEYWORDS = {
    "primary": [
        "ufo", "ufos", "uap", "uaps", "unidentified aerial", "unidentified anomalous",
        "non-human", "non human", "nhi", "alien", "aliens", "extraterrestrial",
        "disclosure", "whistleblower", "grusch", "elizondo", "fravor", "graves",
        "area 51", "area51", "dreamland", "s4 facility", "rogue alien",
    ],
    "secondary": [
        "orb", "orbs", "triangle craft", "tic tac", "gimbal", "go fast",
        "nimitz", "roosevelt", "omalley", "luis elizondo", "david grusch",
        "ryan graves", "alex dietrich", "chris mellon", "steve justice",
        "aaro", "aaro office", "pentagon uap", "all-domain anomaly",
        "congressional hearing", "schumer", "gillibrand", "rubio",
        "immaculate constellation", "kona blue", "crash retrieval",
        "reverse engineering", "biologics", "psi phenomenon",
    ],
    "locations": [
        "skinwalker ranch", "bradley ranch", "rendlesham", "bentwaters",
        "roswell", "aztec", "varginha", "cattle mutilation",
        "mexican air force", "chilean navy", "belgian wave",
    ],
}

ALL_UAP_KEYWORDS = set(UAP_KEYWORDS["primary"] + UAP_KEYWORDS["secondary"] + UAP_KEYWORDS["locations"])

# RSS feeds that frequently cover UAP topics
UAP_FEEDS: List[Tuple[str, str]] = [
    ("The Debrief - UAP", "https://thedebrief.org/category/uap/feed/"),
    ("Liberty Nation - UAP", "https://libertynation.com/tag/unidentified-aerial-phenomena/feed/"),
    ("The War Zone - UAP", "https://www.thedrive.com/the-war-zone/category/uap/feed"),
    ("Popular Mechanics - UAP", "https://www.popularmechanics.com/tag/uap/feed/"),
    ("NewsNation - UAP", "https://www.newsnationnow.com/tag/uap/feed/"),
    ("VICE - Motherboard UAP", "https://www.vice.com/en/topic/ufo/feed"),
    ("Coast to Coast AM", "https://www.coasttocoastam.com/feed/"),
    ("Mysterious Universe", "https://mysteriousuniverse.org/feed/podcast/"),
]

# Government/Military sources for official UAP info
GOVERNMENT_FEEDS: List[Tuple[str, str]] = [
    ("AARO (All-domain Anomaly Resolution Office)", "https://www.aaro.mil/feeds/news"),
    ("DoD News - UAP", "https://www.defense.gov/feeds/news/"),
    ("Senate Intel Committee", "https://www.intelligence.senate.gov/rss/feed.xml"),
    ("House Oversight Committee", "https://oversight.house.gov/rss.xml"),
]

# Reddit subreddits for UAP discussion
REDDIT_SUBREDDITS = [
    "UFOs", "UFO", "aliens", "HighStrangeness", "UFOB",
    "ExoPolitics", "AncientAliens", "SkinwalkerRanch",
]

# YouTube channels focused on UAP content
YOUTUBE_CHANNELS = [
    ("Weaponized Podcast", "UCkO3y4Ew7ZkYkDZuE5R5gPw"),  # Fravor, Dietrich, Corbell
    ("Merged Podcast", "UC4ZtG2Mk7Z8qQaHc6kLZ1YQ"),      # Ryan Graves
    ("Theories of Everything", "UCqx7kP6C4kQwGkX6jZqC0xg"),
    ("Red Panda Koala", "UCyNvM8QxE5QkZ7a2gLqQhPg"),
    ("UAP Max", "UCyQZwN9M4ZkL4x4gLx8jL6g"),
    ("Project Unity", "UCeY0bbnWlqJkMqHkZqLvY7w"),
]

# Google Trends regions for UAP searches
GTRENDS_REGIONS = ["US", "GB", "AU", "CA", "NZ", "IE", "ZA"]

# Wikipedia UAP-related articles to monitor
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
    "Belgian_UFO_wave",
]

# Browser UA
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ============================================================================
# UAP CLASSIFICATION ENGINE
# ============================================================================

def classify_uap_content(text: str) -> Tuple[str, float]:
    """
    Classify UAP-related content into specific niches and return confidence score.
    Returns (niche, confidence) where confidence is 0-1.
    """
    if not text:
        return ("sightings", 0.0)
    
    text_lower = text.lower()
    confidence = 0.0
    
    # Check for primary keyword matches
    primary_matches = sum(1 for kw in UAP_KEYWORDS["primary"] if kw in text_lower)
    secondary_matches = sum(1 for kw in UAP_KEYWORDS["secondary"] if kw in text_lower)
    location_matches = sum(1 for kw in UAP_KEYWORDS["locations"] if kw in text_lower)
    
    total_matches = primary_matches + secondary_matches + location_matches
    confidence = min(0.3 + (total_matches * 0.05), 1.0)
    
    # Niche classification rules
    # Disclosure (government official)
    if any(kw in text_lower for kw in ["disclosure", "congress", "hearing", "pentagon", "aaro", "senate", "house", "schumer", "gillibrand", "rubio", "white house", "official statement"]):
        if any(kw in text_lower for kw in ["disclosure", "congressional hearing", "aaro", "senate"]):
            return ("disclosure", confidence)
    
    # Whistleblower specific
    if any(kw in text_lower for kw in ["grusch", "whistleblower", "elizondo", "fravor", "graves", "dietrich", "mellon"]):
        return ("whistleblower", confidence)
    
    # Military encounters
    if any(kw in text_lower for kw in ["military", "navy", "air force", "pilot", "radar", "fighter jet", "missile", "nuclear", "nuke", "pentagon", "nimitz", "roosevelt", "tic tac", "gimbal", "go fast"]):
        return ("military", confidence)
    
    # Legislation
    if any(kw in text_lower for kw in ["legislation", "bill", "law", "act", "congressional", "amendment", "ndaa", "uap disclosure act", "national defense"]):
        return ("legislation", confidence)
    
    # Area 51 specific
    if any(kw in text_lower for kw in ["area 51", "area51", "groom lake", "s4", "dreamland", "papoose lake"]):
        return ("area51", confidence)
    
    # Ancient aliens
    if any(kw in text_lower for kw in ["ancient", "pyramid", "paleocontact", "ancient astronaut", "nazca", "puma punku", "gobekli tepe"]):
        return ("ancient_aliens", confidence)
    
    # Scientific analysis
    if any(kw in text_lower for kw in ["science", "research", "study", "data", "analysis", "paper", "peer review", "evidence", "scientific"]):
        return ("scientific", confidence)
    
    # Exopolitics
    if any(kw in text_lower for kw in ["exopolitics", "international", "global", "united nations", "foreign government", "china uap", "russia ufo", "brazil uap", "chile ufo"]):
        return ("exopolitics", confidence)
    
    # Media coverage
    if any(kw in text_lower for kw in ["news", "reporter", "cnn", "fox", "msnbc", "nyt", "washington post", "bbc", "documentary", "interview"]):
        return ("media_coverage", confidence)
    
    # Sightings (default)
    if any(kw in text_lower for kw in ["sighting", "witness", "orb", "triangle", "cigar shaped", "disk", "saucer", "light in sky"]):
        return ("sightings", confidence)
    
    return ("sightings", confidence)


def is_uap_relevant(text: str) -> bool:
    """Determine if content is relevant to UAP/UFO/NHI topics."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in ALL_UAP_KEYWORDS)


# ============================================================================
# AGGREGATOR
# ============================================================================

class UAPTrendAggregator:

    def __init__(
        self,
        reddit_client_id: Optional[str] = None,
        reddit_client_secret: Optional[str] = None,
        twitter_bearer: Optional[str] = None,
    ):
        self.reddit_client_id = reddit_client_id
        self.reddit_client_secret = reddit_client_secret
        self.twitter_bearer = twitter_bearer

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Disclosure-UAP/1.0 (UAP Trend Monitor)"
        })

        self.browser_session = requests.Session()
        self.browser_session.headers.update({
            "User-Agent": BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

    def _make_id(self, prefix: str, text: str) -> str:
        return f"{prefix}_{hashlib.md5(text.encode()).hexdigest()[:12]}"

    def _age_hours(self, epoch: float) -> float:
        return (time.time() - epoch) / 3600

    def _decay_score(self, age_hours: float, half_life: float = 8.0) -> float:
        return math.exp(-0.693 * age_hours / max(half_life, 0.1))

    def _safe_get(self, url: str, timeout: int = 15, use_browser: bool = False, **kwargs) -> Optional[requests.Response]:
        sess = self.browser_session if use_browser else self.session
        try:
            r = sess.get(url, timeout=timeout, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:
            print(f"  ⚠️  GET {url[:60]}…: {e}")
            return None

    # ── RSS Feed Fetcher (UAP-filtered) ─────────────────────────────────────

    def fetch_uap_rss_feeds(self) -> List[Dict[str, Any]]:
        """Fetch and filter RSS feeds for UAP content."""
        trends = []
        
        # News feeds
        print("  📰 News RSS feeds (UAP filtered)...")
        for name, url in UAP_FEEDS:
            try:
                r = self.browser_session.get(url, timeout=12)
                if r.status_code != 200:
                    continue
                feed = feedparser.parse(r.text)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    content = f"{title} {summary}"
                    
                    if not is_uap_relevant(content):
                        continue
                    
                    niche, confidence = classify_uap_content(content)
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    epoch = time.mktime(pub) if pub else time.time()
                    age_h = self._age_hours(epoch)
                    
                    trends.append({
                        "id": self._make_id("rss", title),
                        "niche": niche,
                        "headline": title[:200],
                        "summary": summary[:400],
                        "velocity_score": self._decay_score(age_h, half_life=8),
                        "signal_strength": confidence,
                        "mentions_last_hour": 50,
                        "mentions_previous_24h": 500,
                        "source": name,
                        "source_url": entry.get("link", url),
                        "is_human": True,
                        "timestamp": datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat() if pub else datetime.now(timezone.utc).isoformat(),
                        "tags": [niche, "uap", "news"],
                    })
                time.sleep(0.3)
            except Exception as e:
                print(f"    ⚠️  {name}: {e}")
        
        # Government feeds
        print("  🏛️  Government/Military feeds...")
        for name, url in GOVERNMENT_FEEDS:
            try:
                r = self.browser_session.get(url, timeout=12)
                if r.status_code != 200:
                    continue
                feed = feedparser.parse(r.text)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    content = f"{title} {summary}"
                    
                    if not is_uap_relevant(content):
                        continue
                    
                    niche, confidence = classify_uap_content(content)
                    if niche not in ["disclosure", "military", "legislation"]:
                        niche = "disclosure"  # Government content defaults to disclosure
                    
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    epoch = time.mktime(pub) if pub else time.time()
                    age_h = self._age_hours(epoch)
                    
                    trends.append({
                        "id": self._make_id("gov", title),
                        "niche": niche,
                        "headline": title[:200],
                        "summary": summary[:400],
                        "velocity_score": self._decay_score(age_h, half_life=12),
                        "signal_strength": 0.95,
                        "mentions_last_hour": 100,
                        "mentions_previous_24h": 1000,
                        "source": name,
                        "source_url": entry.get("link", url),
                        "is_human": True,
                        "timestamp": datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat() if pub else datetime.now(timezone.utc).isoformat(),
                        "tags": [niche, "government", "official"],
                    })
                time.sleep(0.3)
            except Exception as e:
                print(f"    ⚠️  {name}: {e}")
        
        return trends

    # ── Reddit (UAP subreddits) ─────────────────────────────────────────────

    def fetch_reddit_trends(self) -> List[Dict[str, Any]]:
        """Fetch trending posts from UAP-related subreddits."""
        trends = []
        
        # Use public API (no auth required for reading)
        for subreddit in REDDIT_SUBREDDITS:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
                r = self._safe_get(url, timeout=10)
                if not r:
                    continue
                
                data = r.json()
                for post in data.get("data", {}).get("children", []):
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")
                    content = f"{title} {selftext}"
                    
                    if not is_uap_relevant(content):
                        continue
                    
                    niche, confidence = classify_uap_content(content)
                    score = post_data.get("score", 0)
                    comments = post_data.get("num_comments", 0)
                    created_utc = post_data.get("created_utc", time.time())
                    age_h = self._age_hours(created_utc)
                    
                    velocity = min((score + comments * 2) / max(age_h, 0.5) / 500, 1.0)
                    
                    trends.append({
                        "id": self._make_id("reddit", title),
                        "niche": niche,
                        "headline": title[:200],
                        "summary": selftext[:400] if selftext else f"Discussion on r/{subreddit}",
                        "velocity_score": velocity,
                        "signal_strength": confidence,
                        "mentions_last_hour": max(score // max(int(age_h), 1), 1),
                        "mentions_previous_24h": score,
                        "source": f"r/{subreddit}",
                        "source_url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "is_human": True,
                        "timestamp": datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat(),
                        "tags": [niche, "reddit", subreddit.lower()],
                    })
                time.sleep(0.5)
            except Exception as e:
                print(f"    ⚠️  r/{subreddit}: {e}")
        
        return trends

    # ── YouTube (recent UAP videos) ──────────────────────────────────────────

    def fetch_youtube_trends(self) -> List[Dict[str, Any]]:
        """Fetch recent videos from UAP-focused YouTube channels."""
        trends = []
        
        # RSS feeds from YouTube channels (public, no API key needed)
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
                    
                    niche, confidence = classify_uap_content(content)
                    pub = entry.get("published_parsed")
                    epoch = time.mktime(pub) if pub else time.time()
                    age_h = self._age_hours(epoch)
                    
                    trends.append({
                        "id": self._make_id("yt", title),
                        "niche": niche if niche != "sightings" else "media_coverage",
                        "headline": f"📺 {title[:180]}",
                        "summary": f"From {name}: {summary[:300]}" if summary else f"New video from {name}",
                        "velocity_score": self._decay_score(age_h, half_life=6),
                        "signal_strength": confidence,
                        "mentions_last_hour": 200,
                        "mentions_previous_24h": 2000,
                        "source": f"YouTube ({name})",
                        "source_url": entry.get("link", ""),
                        "is_human": False,
                        "timestamp": datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat() if pub else datetime.now(timezone.utc).isoformat(),
                        "tags": [niche, "youtube", "video"],
                    })
                time.sleep(0.3)
            except Exception as e:
                print(f"    ⚠️  {name}: {e}")
        
        return trends

    # ── Google Trends (UAP search terms) ─────────────────────────────────────

    def fetch_google_uap_trends(self) -> List[Dict[str, Any]]:
        """Monitor Google Trends for UAP-related search interest."""
        trends = []
        
        # Search for UAP-related trending queries
        for region in GTRENDS_REGIONS:
            try:
                url = f"https://trends.google.com/trending/rss?geo={region}"
                r = self.browser_session.get(url, timeout=12)
                if r.status_code != 200:
                    continue
                
                feed = feedparser.parse(r.text)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    if not any(uap_kw in title.lower() for uap_kw in ["ufo", "uap", "alien", "disclosure", "grusch", "elizondo"]):
                        continue
                    
                    raw_traffic = getattr(entry, "ht_approx_traffic", "1000").replace(",", "").replace("+", "").strip()
                    try:
                        traffic = int(raw_traffic)
                    except ValueError:
                        traffic = 1000
                    
                    niche, confidence = classify_uap_content(title)
                    trends.append({
                        "id": self._make_id("gt", f"{region}{title}"),
                        "niche": niche,
                        "headline": f"🔥 {title} (Trending in {region})",
                        "summary": f"Search interest spike in {region}",
                        "velocity_score": min(traffic / 500000, 1.0),
                        "signal_strength": 0.9,
                        "mentions_last_hour": max(traffic // 24, 1),
                        "mentions_previous_24h": traffic,
                        "source": "Google Trends",
                        "source_url": entry.get("link", "https://trends.google.com"),
                        "is_human": False,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tags": [region.lower()],
                    })
                time.sleep(0.3)
            except Exception as e:
                print(f"    ⚠️  GT {region}: {e}")
        
        return trends

    # ── Wikipedia (UAP article pageviews) ────────────────────────────────────

    def fetch_wikipedia_uap_trends(self) -> List[Dict[str, Any]]:
        """Fetch pageview statistics for UAP-related Wikipedia articles."""
        trends = []
        
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y/%m/%d")
        
        for article in WIKI_UAP_ARTICLES:
            try:
                url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{article}/daily/{yesterday}/{yesterday}"
                r = self._safe_get(url, timeout=10)
                if not r:
                    continue
                
                data = r.json()
                views = data.get("items", [{}])[0].get("views", 0)
                
                # Decode article title for display
                display_title = article.replace("_", " ")
                
                trends.append({
                    "id": self._make_id("wiki", article),
                    "niche": "scientific",
                    "headline": f"📚 {display_title}",
                    "summary": f"Wikipedia pageviews: {views:,} in the last 24 hours",
                    "velocity_score": min(views / 50000, 1.0),
                    "signal_strength": 0.85,
                    "mentions_last_hour": max(views // 24, 1),
                    "mentions_previous_24h": views,
                    "source": "Wikipedia",
                    "source_url": f"https://en.wikipedia.org/wiki/{article}",
                    "is_human": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tags": ["wikipedia", "pageviews", "reference"],
                })
                time.sleep(0.2)
            except Exception as e:
                print(f"    ⚠️  {article}: {e}")
        
        return trends

    # ── X/Twitter trend monitoring (UAP hashtags) ───────────────────────────

    def fetch_twitter_uap_trends(self) -> List[Dict[str, Any]]:
        """Monitor trending UAP hashtags and discussions on X/Twitter."""
        trends = []
        
        # Use unofficial trending API (free, no auth required)
        try:
            url = "https://trends24.in/json/trends"
            r = self._safe_get(url, timeout=10)
            if r:
                data = r.json()
                for country_trends in data:
                    country = country_trends.get("name", "Global")
                    for trend in country_trends.get("trends", []):
                        trend_name = trend.get("name", "")
                        if is_uap_relevant(trend_name):
                            tweet_volume = trend.get("tweet_volume", 1000)
                            niche, confidence = classify_uap_content(trend_name)
                            trends.append({
                                "id": self._make_id("twitter", trend_name),
                                "niche": niche,
                                "headline": f"🐦 {trend_name}",
                                "summary": f"Trending on X in {country}",
                                "velocity_score": min(tweet_volume / 100000, 1.0),
                                "signal_strength": confidence,
                                "mentions_last_hour": max(tweet_volume // 24, 10),
                                "mentions_previous_24h": tweet_volume,
                                "source": "X/Twitter Trends",
                                "source_url": f"https://twitter.com/search?q={quote_plus(trend_name)}",
                                "is_human": False,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "tags": [country.lower(), "twitter", "trending"],
                            })
        except Exception as e:
            print(f"  ⚠️  Twitter trends: {e}")
        
        return trends

    # ── Main Pipeline ─────────────────────────────────────────────────────────

    def aggregate_all_trends(self) -> List[Dict[str, Any]]:
        all_trends: List[Dict[str, Any]] = []
        
        print("\n" + "=" * 60)
        print("🛸 DISCLOSURE - UFO/UAP/NHI TREND AGGREGATOR")
        print("=" * 60)
        
        # 1. RSS Feeds (News + Government)
        print("\n📡 Fetching UAP-focused RSS feeds...")
        rss_trends = self.fetch_uap_rss_feeds()
        print(f"   → {len(rss_trends)} UAP items from RSS")
        all_trends.extend(rss_trends)
        
        # 2. Reddit
        print("\n💬 Fetching Reddit discussions...")
        reddit_trends = self.fetch_reddit_trends()
        print(f"   → {len(reddit_trends)} UAP posts from Reddit")
        all_trends.extend(reddit_trends)
        
        # 3. YouTube
        print("\n📺 Fetching YouTube videos...")
        youtube_trends = self.fetch_youtube_trends()
        print(f"   → {len(youtube_trends)} UAP videos from YouTube")
        all_trends.extend(youtube_trends)
        
        # 4. Google Trends
        print("\n🔍 Fetching Google Trends data...")
        google_trends = self.fetch_google_uap_trends()
        print(f"   → {len(google_trends)} UAP search trends")
        all_trends.extend(google_trends)
        
        # 5. Wikipedia
        print("\n📖 Fetching Wikipedia pageviews...")
        wiki_trends = self.fetch_wikipedia_uap_trends()
        print(f"   → {len(wiki_trends)} Wikipedia article trends")
        all_trends.extend(wiki_trends)
        
        # 6. X/Twitter
        print("\n🐦 Fetching X/Twitter trends...")
        twitter_trends = self.fetch_twitter_uap_trends()
        print(f"   → {len(twitter_trends)} UAP hashtags trending")
        all_trends.extend(twitter_trends)
        
        return all_trends


# ============================================================================
# POST-PROCESSING
# ============================================================================

def deduplicate(trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    unique = []
    for t in trends:
        key = f"{t['headline'][:80]}_{t['source']}".lower()
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


def rank_and_filter(
    trends: List[Dict[str, Any]],
    max_per_niche: int = 25,
    total_limit: int = 200,
) -> List[Dict[str, Any]]:
    niche_groups: Dict[str, List] = defaultdict(list)
    for t in trends:
        niche_groups[t["niche"]].append(t)
    
    final = []
    for niche in APP_NICHES:
        group = sorted(niche_groups.get(niche, []), key=lambda x: (x["velocity_score"] * x["signal_strength"]), reverse=True)
        final.extend(group[:max_per_niche])
    
    final.sort(key=lambda x: x["velocity_score"] * x["signal_strength"], reverse=True)
    return final[:total_limit]


def add_insights_metadata(trends: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Add detailed insights about the UAP trend landscape."""
    niche_counts = defaultdict(int)
    source_counts = defaultdict(int)
    signal_by_niche = defaultdict(list)
    
    for t in trends:
        niche_counts[t["niche"]] += 1
        source_counts[t["source"]] += 1
        signal_by_niche[t["niche"]].append(t["signal_strength"])
    
    insights = {
        "top_activity_niches": sorted(
            [{"niche": n, "count": c} for n, c in niche_counts.items()],
            key=lambda x: x["count"], reverse=True
        )[:5],
        "signal_strength_by_niche": {
            niche: round(sum(scores) / len(scores), 2) if scores else 0
            for niche, scores in signal_by_niche.items()
        },
        "source_distribution": dict(source_counts),
        "total_trends": len(trends),
        "niches_covered": sorted(niche_counts.keys()),
        "monitoring_keywords": list(ALL_UAP_KEYWORDS)[:20],
    }
    
    return insights


# ============================================================================
# ENTRY POINT
# ============================================================================

def main() -> None:
    # Optional API keys (not required for basic operation)
    reddit_client_id = os.environ.get("REDDIT_CLIENT_ID")
    reddit_client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    twitter_bearer = os.environ.get("TWITTER_BEARER_TOKEN")
    
    # Get the directory where this script is located (disclosure/scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to disclosure/, then to disclosure/data/
    output_file = os.path.normpath(os.path.join(script_dir, "..", "data", "uap_trends.json"))
    
    print(f"\n🚀 Disclosure UAP v1.0 — output → {output_file}\n")
    
    aggregator = UAPTrendAggregator(
        reddit_client_id=reddit_client_id,
        reddit_client_secret=reddit_client_secret,
        twitter_bearer=twitter_bearer,
    )
    
    raw = aggregator.aggregate_all_trends()
    print(f"\n✅ Raw collected:  {len(raw)}")
    
    unique = deduplicate(raw)
    print(f"✅ After dedup:    {len(unique)}")
    
    final = rank_and_filter(unique, max_per_niche=25, total_limit=200)
    print(f"✅ After ranking:  {len(final)}")
    
    # Add insights
    insights = add_insights_metadata(final)
    
    payload = {
        "trends": final,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(final),
        "topic": "UFO/UAP/NHI - Non-Human Intelligence",
        "insights": insights,
        "metadata": {
            "version": "1.0",
            "niches_covered": insights["niches_covered"],
            "sources_used": sorted(set(t["source"] for t in final)),
            "keywords_monitored": list(ALL_UAP_KEYWORDS),
        },
    }
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Saved {len(final)} UAP trends to {output_file}")
    print(f"\n📊 UAP Trend Summary:")
    print(f"   Niches covered: {', '.join(insights['niches_covered'])}")
    print(f"   Top activity niches:")
    for n in insights["top_activity_niches"]:
        print(f"      • {n['niche']}: {n['count']} items")
    print(f"\n   Signal strength by niche:")
    for niche, strength in sorted(insights["signal_strength_by_niche"].items(), key=lambda x: x[1], reverse=True):
        print(f"      • {niche}: {strength}")
    
    print(f"\n📱 Source breakdown:")
    for source, count in sorted(insights["source_distribution"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"      • {source}: {count}")


if __name__ == "__main__":
    main()
