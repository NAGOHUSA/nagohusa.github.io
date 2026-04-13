#!/usr/bin/env python3
"""
PulseRelay - Multi-Source Real-Time Trend Aggregator v5.2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sources (all free, no mandatory keys):
  • Google Trends   — browser UA fix, multi-region daily RSS
  • News RSS        — BBC, Reuters, AP, Al Jazeera, DW, NYT, Ars, Verge…
  • Wikipedia       — pageviews REST API
  • Hacker News     — Firebase JSON API
  • Lobste.rs       — JSON API (short timeout, graceful skip)
  • Dev.to          — public articles API
  • GitHub          — search API (optional token for higher rate limit)
  • Bluesky         — AT Protocol What's Hot feed, no auth
  • Mastodon        — mastodon.social + fosstodon + infosec.exchange, no auth
  • Niche extras    — Hackaday, Adafruit, Makezine, Outside, Backpacker,
                      iFixit, Courthouse News, AP local/state wire
Optional:
  • DeepSeek        — AI synthesis for niches still thin after real data
                      (set DEEPSEEK_API_KEY env var)
  • GitHub token    — higher rate limit (set GITHUB_TOKEN env var)
"""

import json
import math
import os
import re
import sys
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

import requests

try:
    import feedparser
except ImportError:
    print("❌ feedparser not installed. Run: pip install feedparser")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

APP_NICHES = [
    "breakingNews", "worldEvents", "cinema", "sports", "streaming", "music",
    "space", "tech", "maker", "privacy", "repair", "outdoor", "legal", "local",
]

# ── News RSS feeds per niche — all free, no auth ─────────────────────────────
NEWS_FEEDS: Dict[str, List[str]] = {
    "breakingNews": [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "https://feeds.reuters.com/reuters/topNews",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://feeds.npr.org/1001/rss.xml",
    ],
    "worldEvents": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.reuters.com/reuters/worldNews",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.dw.com/rdf/rss-en-all",
        "https://feeds.npr.org/1004/rss.xml",
    ],
    "tech": [
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://www.zdnet.com/news/rss.xml",
    ],
    "space": [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://www.space.com/feeds/all",
        "https://spacenews.com/feed/",
        "https://www.universetoday.com/feed/",
    ],
    "sports": [
        "http://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news",
        "https://api.foxsports.com/v1/rss",
    ],
    "cinema": [
        "https://www.hollywoodreporter.com/feed/",
        "https://variety.com/feed/",
        "https://collider.com/feed/",
        "https://www.indiewire.com/feed/",
    ],
    "music": [
        "https://pitchfork.com/rss/news/feed.iu/?format=xml",
        "https://www.rollingstone.com/music/feed/",
        "https://www.nme.com/feed",
        "https://consequence.net/feed/",
    ],
    "streaming": [
        "https://www.hollywoodreporter.com/t/streaming/feed/",
        "https://variety.com/v/streaming/feed/",
        "https://www.whats-on-netflix.com/feed/",
        "https://www.thestreamable.com/feed",
    ],
    "privacy": [
        "https://www.eff.org/rss/updates.xml",
        "https://krebsonsecurity.com/feed/",
        "https://feeds.feedburner.com/TheHackersNews",
        "https://www.schneier.com/feed/atom/",
    ],
    "legal": [
        "https://feeds.reuters.com/reuters/legalNews",
        "https://abovethelaw.com/feed/",
        "https://lawandcrime.com/feed/",
        "https://www.courthousenews.com/feed/",
    ],
    "repair": [
        "https://www.ifixit.com/News/rss",
        "https://hackaday.com/feed/",
    ],
    "outdoor": [
        "https://www.outsideonline.com/feed/",
        "https://www.backpacker.com/feed/",
        "https://www.trailrunnermag.com/feed/",
        "https://www.climbing.com/feed/",
    ],
    "maker": [
        "https://hackaday.com/feed/",
        "https://blog.adafruit.com/feed/",
        "https://makezine.com/feed/",
        "https://www.instructables.com/feed/",
    ],
    "local": [
        "https://feeds.apnews.com/rss/apf-localnews",
        "https://feeds.apnews.com/rss/apf-southeaststate",
        "https://feeds.apnews.com/rss/apf-usstate",
        "https://statescoop.com/feed/",
    ],
}

# ── Google Trends regions ─────────────────────────────────────────────────────
GTRENDS_REGIONS = ["US", "GB", "IN", "AU", "DE", "BR", "JP", "ZA", "NG"]

# ── Mastodon servers ──────────────────────────────────────────────────────────
MASTODON_SERVERS = [
    "https://mastodon.social",
    "https://fosstodon.org",
    "https://infosec.exchange",
]

# ── Bluesky What's Hot feed (public AppView, no auth) ────────────────────────
BSKY_POSTS_URL   = "https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed"
BSKY_TRENDING_FEED = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot"

# ── API base URLs ─────────────────────────────────────────────────────────────
HN_BASE      = "https://hacker-news.firebaseio.com/v0"
GITHUB_API   = "https://api.github.com/search/repositories"
LOBSTERS_API = "https://lobste.rs/hottest.json"
DEVTO_API    = "https://dev.to/api/articles"
WIKI_API     = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access"

# Browser UA — required for Google Trends from CI runners
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ── Keyword classifier for social posts ──────────────────────────────────────
SOCIAL_NICHE_KEYWORDS: Dict[str, List[str]] = {
    "tech":         ["ai", "llm", "software", "coding", "programming", "apple", "google", "openai", "tech", "dev"],
    "privacy":      ["privacy", "hack", "breach", "security", "surveillance", "vpn", "encryption", "infosec"],
    "space":        ["nasa", "spacex", "rocket", "mars", "moon", "asteroid", "launch", "orbit", "astronomy"],
    "sports":       ["nfl", "nba", "mlb", "soccer", "football", "basketball", "game", "match", "score", "fifa"],
    "cinema":       ["movie", "film", "oscar", "box office", "trailer", "actor", "director", "cinema"],
    "music":        ["album", "song", "music", "concert", "tour", "grammy", "artist", "band", "playlist"],
    "streaming":    ["netflix", "hbo", "disney+", "streaming", "series", "episode", "season", "prime video"],
    "maker":        ["3d print", "arduino", "raspberry pi", "diy", "build", "circuit", "maker", "electronics"],
    "repair":       ["repair", "fix", "ifixit", "right to repair", "broken", "replace", "teardown"],
    "outdoor":      ["hiking", "climbing", "camping", "trail", "nature", "park", "wilderness", "backpacking"],
    "legal":        ["court", "lawsuit", "judge", "trial", "verdict", "law", "supreme court", "attorney"],
    "worldEvents":  ["war", "election", "ukraine", "gaza", "protest", "government", "president", "climate"],
    "breakingNews": ["breaking", "just in", "alert", "update", "developing"],
}

def classify_social(text: str) -> str:
    lower = text.lower()
    for niche, keywords in SOCIAL_NICHE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return niche
    return "breakingNews"


# ============================================================================
# AGGREGATOR
# ============================================================================

class TrendAggregator:

    def __init__(
        self,
        deepseek_key: Optional[str] = None,
        github_token: Optional[str] = None,
    ):
        self.deepseek_key = deepseek_key
        self.github_token = github_token

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PulseRelay/5.2 (Global Trend Aggregator)"
        })

        # Separate session with browser UA for sources that block bots
        self.browser_session = requests.Session()
        self.browser_session.headers.update({
            "User-Agent": BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        })

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_id(self, prefix: str, text: str) -> str:
        return f"{prefix}_{hashlib.md5(text.encode()).hexdigest()[:10]}"

    def _age_hours(self, epoch: float) -> float:
        return (time.time() - epoch) / 3600

    def _decay_score(self, age_hours: float, half_life: float = 12.0) -> float:
        return math.exp(-0.693 * age_hours / max(half_life, 0.1))

    def _parsed_time_to_epoch(self, parsed_time) -> float:
        try:
            return time.mktime(parsed_time)
        except Exception:
            return time.time()

    def _safe_get(
        self,
        url: str,
        timeout: int = 10,
        use_browser: bool = False,
        **kwargs,
    ) -> Optional[requests.Response]:
        sess = self.browser_session if use_browser else self.session
        try:
            r = sess.get(url, timeout=timeout, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:
            print(f"  ⚠️  GET {url[:70]}…: {e}")
            return None

    # ── Google Trends ─────────────────────────────────────────────────────────

    def fetch_google_trends(self, niche: str = "breakingNews") -> List[Dict[str, Any]]:
        """
        Uses browser UA session to bypass the CI runner block.
        Fetches raw XML then passes to feedparser for parsing.
        """
        trends = []
        for region in GTRENDS_REGIONS:
            try:
                url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={region}"
                r = self.browser_session.get(url, timeout=12)
                if r.status_code != 200:
                    print(f"  ⚠️  Google Trends {region}: HTTP {r.status_code}")
                    continue
                feed = feedparser.parse(r.text)
                if not feed.entries:
                    print(f"  ⚠️  Google Trends {region}: no entries")
                    continue
                for entry in feed.entries[:8]:
                    raw = (
                        getattr(entry, "ht_approx_traffic", "1000")
                        .replace(",", "").replace("+", "").strip()
                    )
                    try:
                        traffic = int(raw)
                    except ValueError:
                        traffic = 1000
                    summary = getattr(entry, "summary", "") or f"Trending in {region}"
                    trends.append({
                        "id": self._make_id("gtrends", f"{region}{entry.title}"),
                        "niche": niche,
                        "headline": entry.title,
                        "summary": summary[:300],
                        "velocity_score": min(traffic / 2_000_000, 1.0),
                        "signal_strength": 0.95,
                        "mentions_last_hour": max(traffic // 24, 1),
                        "mentions_previous_24h": traffic,
                        "source": "google_trends",
                        "source_url": getattr(entry, "link", "https://trends.google.com"),
                        "is_human": True,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "tags": [region.lower()],
                    })
                time.sleep(0.5)
            except Exception as e:
                print(f"  ⚠️  Google Trends {region}: {e}")
        return trends

    # ── News RSS ──────────────────────────────────────────────────────────────

    def fetch_rss_feed(self, url: str, niche: str, limit: int = 12) -> List[Dict[str, Any]]:
        try:
            r = self.browser_session.get(url, timeout=10)
            feed = feedparser.parse(r.text if r.status_code == 200 else url)
            if feed.bozo and not feed.entries:
                return []
            trends = []
            for entry in feed.entries[:limit]:
                pub   = entry.get("published_parsed") or entry.get("updated_parsed")
                epoch = self._parsed_time_to_epoch(pub) if pub else time.time()
                age_h = self._age_hours(epoch)
                ts    = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
                trends.append({
                    "id": self._make_id("rss", url + entry.get("title", "")),
                    "niche": niche,
                    "headline": entry.get("title", "")[:200],
                    "summary": entry.get("summary", "")[:300],
                    "velocity_score": self._decay_score(age_h, half_life=12),
                    "signal_strength": 0.80,
                    "mentions_last_hour": 100,
                    "mentions_previous_24h": 1000,
                    "source": "rss",
                    "source_url": entry.get("link", url),
                    "is_human": True,
                    "timestamp": ts,
                    "tags": [t.get("term", "") for t in entry.get("tags", [])][:5],
                })
            return trends
        except Exception as e:
            print(f"  ⚠️  RSS {url[:70]}…: {e}")
            return []

    def fetch_all_rss(self) -> List[Dict[str, Any]]:
        trends = []
        for niche, feeds in NEWS_FEEDS.items():
            print(f"  📰  RSS → {niche}")
            for url in feeds:
                trends.extend(self.fetch_rss_feed(url, niche))
                time.sleep(0.2)
        return trends

    # ── Wikipedia ─────────────────────────────────────────────────────────────

    def fetch_wikipedia_trending(self, niche: str = "worldEvents") -> List[Dict[str, Any]]:
        SKIP = ("Main_Page", "Special:", "Wikipedia:", "Portal:", "Help:", "File:")
        try:
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y/%m/%d")
            r = self._safe_get(f"{WIKI_API}/{yesterday}", timeout=10)
            if not r:
                return []
            articles = r.json()["items"][0]["articles"]
            trends = []
            for article in articles:
                title = article["article"]
                if any(title.startswith(p) for p in SKIP):
                    continue
                views = article.get("views", 0)
                trends.append({
                    "id": self._make_id("wiki", title),
                    "niche": niche,
                    "headline": title.replace("_", " "),
                    "summary": f"Trending on Wikipedia — {views:,} views yesterday",
                    "velocity_score": min(views / 3_000_000, 1.0),
                    "signal_strength": 0.75,
                    "mentions_last_hour": max(views // 24, 1),
                    "mentions_previous_24h": views,
                    "source": "wikipedia",
                    "source_url": f"https://en.wikipedia.org/wiki/{title}",
                    "is_human": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tags": [],
                })
                if len(trends) >= 20:
                    break
            return trends
        except Exception as e:
            print(f"  ⚠️  Wikipedia: {e}")
            return []

    # ── Hacker News ───────────────────────────────────────────────────────────

    def fetch_hackernews_trends(self, niche: str, limit: int = 15) -> List[Dict[str, Any]]:
        try:
            r = self._safe_get(f"{HN_BASE}/topstories.json", timeout=10)
            if not r:
                return []
            ids = r.json()[:limit]
            trends = []
            for story_id in ids:
                sr = self._safe_get(f"{HN_BASE}/item/{story_id}.json", timeout=5)
                if not sr:
                    continue
                story = sr.json()
                if not story or story.get("type") != "story":
                    continue
                score    = story.get("score", 0)
                comments = story.get("descendants", 0)
                age_h    = self._age_hours(story.get("time", time.time()))
                velocity = min(((score + comments * 3) / max(age_h, 0.5)) / 200, 1.0)
                trends.append({
                    "id": f"hn_{story_id}",
                    "niche": niche,
                    "headline": story.get("title", ""),
                    "summary": f"Hacker News — {score} points, {comments} comments",
                    "velocity_score": velocity,
                    "signal_strength": min((comments / max(score, 1)) * 2, 1.0),
                    "mentions_last_hour": max(int(score / max(age_h, 1)), 1),
                    "mentions_previous_24h": score,
                    "source": "hackernews",
                    "source_url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                    "is_human": True,
                    "timestamp": datetime.fromtimestamp(
                        story.get("time", 0), tz=timezone.utc
                    ).isoformat(),
                    "tags": [],
                })
            return trends
        except Exception as e:
            print(f"  ⚠️  Hacker News: {e}")
            return []

    # ── Lobste.rs ─────────────────────────────────────────────────────────────

    def fetch_lobsters(self, niche: str = "tech") -> List[Dict[str, Any]]:
        try:
            r = self._safe_get(LOBSTERS_API, timeout=8)
            if not r:
                return []
            trends = []
            for story in r.json()[:15]:
                score    = story.get("score", 0)
                comments = story.get("comment_count", 0)
                trends.append({
                    "id": self._make_id("lobsters", story.get("short_id", story.get("title", ""))),
                    "niche": niche,
                    "headline": story.get("title", ""),
                    "summary": f"Lobste.rs — {score} points, {comments} comments",
                    "velocity_score": min((score + comments * 2) / 200, 1.0),
                    "signal_strength": 0.85,
                    "mentions_last_hour": score,
                    "mentions_previous_24h": score * 4,
                    "source": "lobsters",
                    "source_url": story.get("url", f"https://lobste.rs/s/{story.get('short_id','')}"),
                    "is_human": True,
                    "timestamp": story.get("created_at", datetime.now(timezone.utc).isoformat()),
                    "tags": story.get("tags", []),
                })
            return trends
        except Exception as e:
            print(f"  ⚠️  Lobste.rs: {e}")
            return []

    # ── Dev.to ────────────────────────────────────────────────────────────────

    def fetch_devto(self, niche: str = "tech") -> List[Dict[str, Any]]:
        try:
            r = self._safe_get(DEVTO_API, timeout=10, params={"top": 1, "per_page": 15})
            if not r:
                return []
            trends = []
            for article in r.json():
                reactions = article.get("positive_reactions_count", 0)
                comments  = article.get("comments_count", 0)
                trends.append({
                    "id": self._make_id("devto", str(article.get("id", ""))),
                    "niche": niche,
                    "headline": article.get("title", ""),
                    "summary": article.get("description", "")[:300],
                    "velocity_score": min((reactions + comments * 3) / 600, 1.0),
                    "signal_strength": 0.70,
                    "mentions_last_hour": max(reactions // 24, 1),
                    "mentions_previous_24h": reactions,
                    "source": "devto",
                    "source_url": article.get("url", "https://dev.to"),
                    "is_human": True,
                    "timestamp": article.get("published_at", datetime.now(timezone.utc).isoformat()),
                    "tags": article.get("tag_list", []),
                })
            return trends
        except Exception as e:
            print(f"  ⚠️  Dev.to: {e}")
            return []

    # ── GitHub Trending ───────────────────────────────────────────────────────

    def fetch_github_trends(self, niche: str = "tech", limit: int = 8) -> List[Dict[str, Any]]:
        try:
            headers = {}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
            r = self._safe_get(
                GITHUB_API, timeout=10,
                params={"q": f"created:>{since}", "sort": "stars", "order": "desc", "per_page": limit},
            )
            if not r:
                return []
            trends = []
            for repo in r.json().get("items", []):
                stars = repo.get("stargazers_count", 0)
                trends.append({
                    "id": self._make_id("github", str(repo.get("id", ""))),
                    "niche": niche,
                    "headline": repo.get("full_name", ""),
                    "summary": (repo.get("description") or "")[:300],
                    "velocity_score": min(stars / 5000, 1.0),
                    "signal_strength": 0.90,
                    "mentions_last_hour": max(stars // 72, 1),
                    "mentions_previous_24h": stars,
                    "source": "github",
                    "source_url": repo.get("html_url", ""),
                    "is_human": True,
                    "timestamp": repo.get("created_at", datetime.now(timezone.utc).isoformat()),
                    "tags": repo.get("topics", []),
                })
            return trends
        except Exception as e:
            print(f"  ⚠️  GitHub: {e}")
            return []

    # ── Bluesky ───────────────────────────────────────────────────────────────

    def fetch_bluesky_trending(self) -> List[Dict[str, Any]]:
        """
        Pulls the public What's Hot feed via Bluesky's open AppView API.
        Zero authentication required.
        """
        trends = []
        try:
            r = self._safe_get(
                BSKY_POSTS_URL,
                timeout=12,
                params={"feed": BSKY_TRENDING_FEED, "limit": 30},
            )
            if not r:
                return []
            for item in r.json().get("feed", []):
                post   = item.get("post", {})
                record = post.get("record", {})
                text   = record.get("text", "").strip()
                if not text:
                    continue

                likes   = post.get("likeCount", 0)
                reposts = post.get("repostCount", 0)
                replies = post.get("replyCount", 0)
                indexed = post.get("indexedAt", datetime.now(timezone.utc).isoformat())

                try:
                    epoch = datetime.fromisoformat(indexed.replace("Z", "+00:00")).timestamp()
                except Exception:
                    epoch = time.time()
                age_h = self._age_hours(epoch)

                engagement = likes + reposts * 2 + replies
                velocity   = min((engagement / max(age_h, 0.5)) / 500, 1.0)

                uri    = post.get("uri", "")
                rkey   = uri.split("/")[-1] if uri else ""
                handle = post.get("author", {}).get("handle", "bsky.app")
                url    = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else "https://bsky.app"

                trends.append({
                    "id": self._make_id("bsky", uri or text),
                    "niche": classify_social(text),
                    "headline": text[:200],
                    "summary": f"Trending on Bluesky — {likes:,} likes, {reposts:,} reposts",
                    "velocity_score": velocity,
                    "signal_strength": min(reposts / max(likes, 1), 1.0),
                    "mentions_last_hour": max(engagement // max(int(age_h), 1), 1),
                    "mentions_previous_24h": engagement,
                    "source": "bluesky",
                    "source_url": url,
                    "is_human": True,
                    "timestamp": indexed,
                    "tags": [],
                })
        except Exception as e:
            print(f"  ⚠️  Bluesky: {e}")
        return trends

    # ── Mastodon ──────────────────────────────────────────────────────────────

    def fetch_mastodon_trending(self) -> List[Dict[str, Any]]:
        """
        Polls /api/v1/trends/statuses on multiple Mastodon servers.
        Completely open — no auth needed.
        """
        trends = []
        for server in MASTODON_SERVERS:
            try:
                r = self._safe_get(
                    f"{server}/api/v1/trends/statuses",
                    timeout=10,
                    params={"limit": 20},
                )
                if not r:
                    continue
                for status in r.json():
                    content = status.get("content", "")
                    text    = re.sub(r"<[^>]+>", " ", content).strip()
                    text    = re.sub(r"\s+", " ", text).strip()
                    if not text:
                        continue

                    favourites = status.get("favourites_count", 0)
                    reblogs    = status.get("reblogs_count", 0)
                    replies    = status.get("replies_count", 0)
                    created_at = status.get("created_at", datetime.now(timezone.utc).isoformat())

                    try:
                        epoch = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        epoch = time.time()
                    age_h = self._age_hours(epoch)

                    engagement = favourites + reblogs * 2 + replies
                    velocity   = min((engagement / max(age_h, 0.5)) / 200, 1.0)
                    server_name = server.split("//")[-1]

                    trends.append({
                        "id": self._make_id("mastodon", status.get("id", text)),
                        "niche": classify_social(text),
                        "headline": text[:200],
                        "summary": f"Trending on Mastodon ({server_name}) — {favourites} favourites, {reblogs} boosts",
                        "velocity_score": velocity,
                        "signal_strength": min(reblogs / max(favourites, 1), 1.0),
                        "mentions_last_hour": max(engagement // max(int(age_h), 1), 1),
                        "mentions_previous_24h": engagement,
                        "source": "mastodon",
                        "source_url": status.get("url", server),
                        "is_human": True,
                        "timestamp": created_at,
                        "tags": [t.get("name", "") for t in status.get("tags", [])][:5],
                    })
                time.sleep(0.3)
            except Exception as e:
                print(f"  ⚠️  Mastodon {server}: {e}")
        return trends

    # ── DeepSeek Synthesis ────────────────────────────────────────────────────

    def fetch_deepseek_synthesis(self, context_trends: List[Dict], niche: str) -> List[Dict[str, Any]]:
        if not self.deepseek_key:
            return []
        context = "\n".join(f"- {t['headline']}" for t in context_trends[:10])
        prompt = (
            f"You are a global trend analyst. Based on these trending topics for the '{niche}' niche:\n"
            f"{context}\n\n"
            f"Generate 5 additional unique high-velocity trending topics for today that are NOT in the list above. "
            f"Output ONLY a JSON object with a 'trends' array. Each item must have: "
            f"headline (string), summary (string), velocity_score (float 0-1), tags (string array), source_url (string)."
        )
        response = None
        for attempt in range(2):
            try:
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.deepseek_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "You are a JSON-only trend analyst. Output raw JSON, no markdown."},
                            {"role": "user", "content": prompt},
                        ],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 1000,
                    },
                    timeout=20,
                )
                break
            except requests.exceptions.Timeout:
                if attempt == 1:
                    print(f"  ⚠️  DeepSeek timed out twice for '{niche}', skipping")
                    return []
                print(f"  ⚠️  DeepSeek timeout for '{niche}', retrying in 3s…")
                time.sleep(3)

        if response is None:
            return []

        try:
            items = json.loads(
                response.json()["choices"][0]["message"]["content"]
            ).get("trends", [])
            results = []
            for t in items:
                results.append({
                    "id": self._make_id("ai", t.get("headline", "")),
                    "niche": niche,
                    "headline": t.get("headline", ""),
                    "summary": t.get("summary", ""),
                    "velocity_score": float(t.get("velocity_score", 0.75)),
                    "signal_strength": 0.70,
                    "mentions_last_hour": 200,
                    "mentions_previous_24h": 1500,
                    "source": "ai_synthesis",
                    "source_url": t.get("source_url", "https://news.google.com"),
                    "is_human": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tags": t.get("tags", []),
                })
            return results
        except Exception as e:
            print(f"  ⚠️  DeepSeek parse error ({niche}): {e}")
            return []

    # ── Main Pipeline ─────────────────────────────────────────────────────────

    def aggregate_all_trends(self) -> List[Dict[str, Any]]:
        all_trends: List[Dict[str, Any]] = []

        # 1. Google Trends (browser UA fix)
        print("\n🌍 Google Trends (multi-region, browser UA)...")
        gt = self.fetch_google_trends(niche="breakingNews")
        print(f"   → {len(gt)} items")
        all_trends.extend(gt)
        time.sleep(1.0)

        # 2. Wikipedia
        print("\n📖 Wikipedia trending...")
        wiki = self.fetch_wikipedia_trending(niche="worldEvents")
        print(f"   → {len(wiki)} items")
        all_trends.extend(wiki)
        time.sleep(0.5)

        # 3. News RSS
        print("\n📰 News RSS feeds...")
        rss = self.fetch_all_rss()
        print(f"   → {len(rss)} items")
        all_trends.extend(rss)

        # 4. Tech communities
        print("\n💻 Tech communities (HN + Lobste.rs + Dev.to)...")
        hn = self.fetch_hackernews_trends("tech", limit=15)
        lb = self.fetch_lobsters("tech")
        dt = self.fetch_devto("tech")
        print(f"   → HN: {len(hn)}, Lobste.rs: {len(lb)}, Dev.to: {len(dt)}")
        all_trends.extend(hn)
        all_trends.extend(lb)
        all_trends.extend(dt)
        time.sleep(0.5)

        # 5. GitHub
        label = "authenticated" if self.github_token else "unauthenticated"
        print(f"\n🐙 GitHub trending ({label})...")
        gh = self.fetch_github_trends("tech", limit=8)
        print(f"   → {len(gh)} items")
        all_trends.extend(gh)
        time.sleep(0.5)

        # 6. Bluesky (open social, no auth)
        print("\n🦋 Bluesky trending (What's Hot)...")
        bsky = self.fetch_bluesky_trending()
        print(f"   → {len(bsky)} items")
        all_trends.extend(bsky)
        time.sleep(0.5)

        # 7. Mastodon (federated social, no auth)
        print("\n🐘 Mastodon trending (multi-server)...")
        masto = self.fetch_mastodon_trending()
        print(f"   → {len(masto)} items")
        all_trends.extend(masto)
        time.sleep(0.5)

        # 8. DeepSeek synthesis for niches still thin
        if self.deepseek_key:
            print("\n🤖 DeepSeek synthesis for thin niches...")
            niche_counts: Dict[str, int] = defaultdict(int)
            for t in all_trends:
                niche_counts[t["niche"]] += 1
            for niche in APP_NICHES:
                if niche_counts[niche] < 5:
                    print(f"   → Synthesising '{niche}' ({niche_counts[niche]} items so far)...")
                    synth = self.fetch_deepseek_synthesis(all_trends[:20], niche)
                    all_trends.extend(synth)
                    time.sleep(0.5)
        else:
            print("\n⚪ DeepSeek synthesis skipped (no DEEPSEEK_API_KEY set)")

        return all_trends


# ============================================================================
# POST-PROCESSING
# ============================================================================

def deduplicate(trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    unique = []
    for t in trends:
        key = t["headline"].lower().strip()[:60]
        if key and key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


def rank_and_filter(
    trends: List[Dict[str, Any]],
    max_per_niche: int = 20,
    total_limit: int = 150,
) -> List[Dict[str, Any]]:
    niche_groups: Dict[str, List] = defaultdict(list)
    for t in trends:
        niche_groups[t["niche"]].append(t)
    final = []
    for niche in APP_NICHES:
        group = sorted(niche_groups[niche], key=lambda x: x["velocity_score"], reverse=True)
        final.extend(group[:max_per_niche])
    final.sort(key=lambda x: x["velocity_score"], reverse=True)
    return final[:total_limit]


# ============================================================================
# ENTRY POINT
# ============================================================================

def main() -> None:
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    github_token = os.environ.get("GITHUB_TOKEN")

    if not deepseek_key:
        print("ℹ️  DEEPSEEK_API_KEY not set — AI synthesis will be skipped.")
    if not github_token:
        print("ℹ️  GITHUB_TOKEN not set — GitHub will use unauthenticated rate limits.")

    script_dir  = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.normpath(os.path.join(script_dir, "..", "data", "trends.json"))

    print(f"\n🚀 PulseRelay v5.2 — output → {output_file}\n")

    aggregator = TrendAggregator(deepseek_key=deepseek_key, github_token=github_token)

    raw    = aggregator.aggregate_all_trends()
    print(f"\n✅ Raw collected:  {len(raw)}")

    unique = deduplicate(raw)
    print(f"✅ After dedup:    {len(unique)}")

    final  = rank_and_filter(unique, max_per_niche=20, total_limit=150)
    print(f"✅ After ranking:  {len(final)}")

    payload = {
        "trends": final,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(final),
        "metadata": {
            "version": "5.2",
            "niches_covered": sorted(set(t["niche"] for t in final)),
            "sources_used":   sorted(set(t["source"] for t in final)),
        },
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Saved {len(final)} trends to {output_file}")
    print(f"   Niches:  {', '.join(payload['metadata']['niches_covered'])}")
    print(f"   Sources: {', '.join(payload['metadata']['sources_used'])}")


if __name__ == "__main__":
    main()
