#!/usr/bin/env python3
"""
PulseRelay - Multi-Source Real-Time Trend Aggregator v5.1
Global-first, no mandatory API keys (DeepSeek + GitHub optional).
Primary sources: Google Trends RSS, News RSS, Wikipedia, HN, Lobste.rs, Dev.to
Niche extras:   Hackaday, Makezine, Outside, Backpacker, AJC, GPB
Reddit removed: blocks all unauthenticated server requests (403)
"""

import os
import json
import sys
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
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
    "space", "tech", "maker", "privacy", "repair", "outdoor", "legal", "local"
]

# News RSS feeds per niche — all free, no auth
NEWS_FEEDS: Dict[str, List[str]] = {
    "breakingNews": [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "https://feeds.reuters.com/reuters/topNews",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    ],
    "worldEvents": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.reuters.com/reuters/worldNews",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.dw.com/rdf/rss-en-all",
    ],
    "tech": [
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
    ],
    "space": [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://www.space.com/feeds/all",
        "https://spacenews.com/feed/",
    ],
    "sports": [
        "http://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news",
        "https://theathletic.com/feeds/rss/news",
    ],
    "cinema": [
        "https://www.hollywoodreporter.com/feed/",
        "https://variety.com/feed/",
        "https://collider.com/feed/",
    ],
    "music": [
        "https://pitchfork.com/rss/news/feed.iu/?format=xml",
        "https://www.rollingstone.com/music/feed/",
        "https://www.nme.com/feed",
    ],
    "streaming": [
        "https://www.hollywoodreporter.com/t/streaming/feed/",
        "https://variety.com/v/streaming/feed/",
        "https://www.whats-on-netflix.com/feed/",
    ],
    "privacy": [
        "https://www.eff.org/rss/updates.xml",
        "https://krebsonsecurity.com/feed/",
        "https://feeds.feedburner.com/TheHackersNews",
    ],
    "legal": [
        "https://feeds.reuters.com/reuters/legalNews",
        "https://abovethelaw.com/feed/",
        "https://lawandcrime.com/feed/",
    ],
    "repair": [
        "https://www.ifixit.com/News/rss",
        "https://hackaday.com/feed/",
    ],
    "outdoor": [
        "https://www.outsideonline.com/feed/",
        "https://www.rei.com/blog/feed",
    ],
}

# Google Trends regions — pulled in parallel for global spread
GTRENDS_REGIONS = ["US", "GB", "IN", "AU", "DE", "BR", "JP"]

# Extra RSS feeds for niches not fully covered by NEWS_FEEDS
# Reddit removed — blocks all unauthenticated server-side requests with 403
NICHE_EXTRAS: Dict[str, List[str]] = {
    "maker": [
        "https://hackaday.com/feed/",
        "https://blog.adafruit.com/feed/",
        "https://makezine.com/feed/",
    ],
    "outdoor": [
        "https://www.outsideonline.com/feed/",
        "https://www.backpacker.com/feed/",
        "https://www.rei.com/blog/feed",
    ],
    "local": [
        "https://www.ajc.com/news/local/rss.xml",
        "https://www.gpb.org/rss/news",
    ],
    "repair": [
        "https://www.ifixit.com/News/rss",
        "https://hackaday.com/feed/",
    ],
}

HN_BASE      = "https://hacker-news.firebaseio.com/v0"
GITHUB_API   = "https://api.github.com/search/repositories"
LOBSTERS_API = "https://lobste.rs/hottest.json"
DEVTO_API    = "https://dev.to/api/articles"
WIKI_API     = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access"

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
            "User-Agent": "PulseRelay/5.0 (Global Trend Aggregator; +https://example.com)"
        })

    # ── Helpers ──────────────────────────────────────────────────────────

    def _make_id(self, prefix: str, text: str) -> str:
        return f"{prefix}_{hashlib.md5(text.encode()).hexdigest()[:10]}"

    def _age_hours(self, epoch: float) -> float:
        return (time.time() - epoch) / 3600

    def _decay_score(self, age_hours: float, half_life: float = 24.0) -> float:
        """Exponential decay — score halves every half_life hours."""
        import math
        return math.exp(-0.693 * age_hours / half_life)

    def _parsed_time_to_epoch(self, parsed_time) -> float:
        """Convert feedparser time_struct to epoch seconds."""
        try:
            return time.mktime(parsed_time)
        except Exception:
            return time.time()

    # ── Google Trends RSS ────────────────────────────────────────────────

    def fetch_google_trends(self, niche: str = "breakingNews") -> List[Dict[str, Any]]:
        """
        Pulls daily trending searches from multiple regions.
        No auth required.
        """
        trends = []
        for region in GTRENDS_REGIONS:
            try:
                url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={region}"
                feed = feedparser.parse(url)
                for entry in feed.entries[:8]:
                    raw_traffic = (
                        getattr(entry, "ht_approx_traffic", "1000")
                        .replace(",", "")
                        .replace("+", "")
                        .strip()
                    )
                    try:
                        traffic = int(raw_traffic)
                    except ValueError:
                        traffic = 1000

                    # Related queries come through as <ht:news_item_title> tags
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
                time.sleep(0.4)
            except Exception as e:
                print(f"  ⚠️  Google Trends {region}: {e}")
        return trends

    # ── News RSS ─────────────────────────────────────────────────────────

    def fetch_rss_feed(self, url: str, niche: str) -> List[Dict[str, Any]]:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                return []
            trends = []
            for entry in feed.entries[:12]:
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                epoch = self._parsed_time_to_epoch(pub) if pub else time.time()
                age_h = self._age_hours(epoch)
                ts = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()

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
            print(f"  ⚠️  RSS {url}: {e}")
            return []

    def fetch_all_rss(self) -> List[Dict[str, Any]]:
        trends = []
        for niche, feeds in NEWS_FEEDS.items():
            print(f"  📰  RSS → {niche}")
            for url in feeds:
                trends.extend(self.fetch_rss_feed(url, niche))
                time.sleep(0.25)
        return trends

    # ── Wikipedia Trending ───────────────────────────────────────────────

    def fetch_wikipedia_trending(self, niche: str = "worldEvents") -> List[Dict[str, Any]]:
        """
        Wikimedia pageviews REST API — top articles yesterday.
        Completely free, no auth.
        """
        SKIP_PREFIXES = ("Main_Page", "Special:", "Wikipedia:", "Portal:", "Help:", "File:")
        try:
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y/%m/%d")
            url = f"{WIKI_API}/{yesterday}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            articles = response.json()["items"][0]["articles"]

            trends = []
            for article in articles:
                title = article["article"]
                if any(title.startswith(p) for p in SKIP_PREFIXES):
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
            print(f"  ⚠️  Wikipedia trending: {e}")
            return []

    # ── Hacker News ──────────────────────────────────────────────────────

    def fetch_hackernews_trends(self, niche: str, limit: int = 15) -> List[Dict[str, Any]]:
        try:
            ids = self.session.get(f"{HN_BASE}/topstories.json", timeout=10).json()[:limit]
            trends = []
            for story_id in ids:
                story = self.session.get(f"{HN_BASE}/item/{story_id}.json", timeout=5).json()
                if not story or story.get("type") != "story":
                    continue
                score = story.get("score", 0)
                comments = story.get("descendants", 0)
                age_h = self._age_hours(story.get("time", time.time()))
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
                    "timestamp": datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc).isoformat(),
                    "tags": [],
                })
            return trends
        except Exception as e:
            print(f"  ⚠️  Hacker News: {e}")
            return []

    # ── Lobste.rs ─────────────────────────────────────────────────────────

    def fetch_lobsters(self, niche: str = "tech") -> List[Dict[str, Any]]:
        try:
            response = self.session.get(LOBSTERS_API, timeout=10)
            response.raise_for_status()
            trends = []
            for story in response.json()[:15]:
                score = story.get("score", 0)
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

    # ── Dev.to ────────────────────────────────────────────────────────────

    def fetch_devto(self, niche: str = "tech") -> List[Dict[str, Any]]:
        """Public read API — no auth needed."""
        try:
            response = self.session.get(
                DEVTO_API,
                params={"top": 1, "per_page": 15},
                timeout=10,
            )
            response.raise_for_status()
            trends = []
            for article in response.json():
                reactions = article.get("positive_reactions_count", 0)
                comments = article.get("comments_count", 0)
                trends.append({
                    "id": self._make_id("devto", str(article.get("id", article.get("title", "")))),
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

    # ── GitHub Trending (optional, needs token for reliable rate limits) ──

    def fetch_github_trends(self, niche: str = "tech", limit: int = 8) -> List[Dict[str, Any]]:
        try:
            headers = {}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
            params = {
                "q": f"created:>{since}",
                "sort": "stars",
                "order": "desc",
                "per_page": limit,
            }
            response = self.session.get(GITHUB_API, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            trends = []
            for repo in response.json().get("items", []):
                stars = repo.get("stargazers_count", 0)
                trends.append({
                    "id": self._make_id("github", str(repo.get("id", ""))),
                    "niche": niche,
                    "headline": repo.get("full_name", ""),
                    "summary": (repo.get("description") or "")[:300],
                    "velocity_score": min(stars / 5000, 1.0),
                    "signal_strength": 0.90,
                    "mentions_last_hour": stars // 72,
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

    # ── DeepSeek Synthesis (optional) ────────────────────────────────────

    def fetch_deepseek_synthesis(self, context_trends: List[Dict], niche: str) -> List[Dict[str, Any]]:
        if not self.deepseek_key:
            return []
        try:
            context = "\n".join(f"- {t['headline']}" for t in context_trends[:10])
            prompt = (
                f"You are a global trend analyst. Based on these trending topics for the '{niche}' niche:\n"
                f"{context}\n\n"
                f"Generate 5 additional unique high-velocity trending topics for today that are NOT in the list above. "
                f"Output ONLY a JSON object with a 'trends' array. Each trend must have: "
                f"headline (string), summary (string), velocity_score (0.0-1.0), tags (array of strings), source_url (string)."
            )
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
                    print(f"  ⚠️  DeepSeek timeout for '{niche}', retrying...")
                    time.sleep(2)
            ai_trends = response.json()["choices"][0]["message"]["content"]
            items = json.loads(ai_trends).get("trends", [])
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
            print(f"  ⚠️  DeepSeek synthesis ({niche}): {e}")
            return []

    # ── Main Aggregation Pipeline ─────────────────────────────────────────

    def aggregate_all_trends(self) -> List[Dict[str, Any]]:
        all_trends: List[Dict[str, Any]] = []

        # 1. Google Trends — best real-time global signal
        print("\n🌍 Google Trends (multi-region)...")
        gt = self.fetch_google_trends(niche="breakingNews")
        print(f"   → {len(gt)} items")
        all_trends.extend(gt)
        time.sleep(1.0)

        # 2. Wikipedia — strong world events + entertainment signal
        print("\n📖 Wikipedia trending...")
        wiki = self.fetch_wikipedia_trending(niche="worldEvents")
        print(f"   → {len(wiki)} items")
        all_trends.extend(wiki)
        time.sleep(0.5)

        # 3. News RSS per niche — most reliable global coverage
        print("\n📰 News RSS feeds...")
        rss = self.fetch_all_rss()
        print(f"   → {len(rss)} items")
        all_trends.extend(rss)

        # 4. Tech community signals
        print("\n💻 Tech communities (HN + Lobste.rs + Dev.to)...")
        hn = self.fetch_hackernews_trends("tech", limit=15)
        lb = self.fetch_lobsters("tech")
        dt = self.fetch_devto("tech")
        print(f"   → HN: {len(hn)}, Lobste.rs: {len(lb)}, Dev.to: {len(dt)}")
        all_trends.extend(hn)
        all_trends.extend(lb)
        all_trends.extend(dt)
        time.sleep(0.5)

        # 5. GitHub (optional — works without token but rate-limited)
        if self.github_token:
            print("\n🐙 GitHub trending (authenticated)...")
        else:
            print("\n🐙 GitHub trending (unauthenticated — may be rate limited)...")
        gh = self.fetch_github_trends("tech", limit=8)
        print(f"   → {len(gh)} items")
        all_trends.extend(gh)
        time.sleep(0.5)

        # 6. Niche extras — RSS for maker / outdoor / local / repair
        print("\n🔧 Niche extra RSS (maker / outdoor / local / repair)...")
        for niche, feeds in NICHE_EXTRAS.items():
            for url in feeds:
                results = self.fetch_rss_feed(url, niche)
                domain = url.split("/")[2]
                print(f"   → {domain}: {len(results)} items")
                all_trends.extend(results)
                time.sleep(0.25)

        # 7. DeepSeek synthesis — fills niches still thin after real data
        if self.deepseek_key:
            print("\n🤖 DeepSeek synthesis for thin niches...")
            niche_counts: Dict[str, int] = defaultdict(int)
            for t in all_trends:
                niche_counts[t["niche"]] += 1
            for niche in APP_NICHES:
                if niche_counts[niche] < 5:
                    print(f"   → Synthesising '{niche}' (only {niche_counts[niche]} items so far)...")
                    pool = all_trends[:20]
                    synth = self.fetch_deepseek_synthesis(pool, niche)
                    all_trends.extend(synth)
                    time.sleep(0.5)
        else:
            print("\n⚪ DeepSeek synthesis skipped (no DEEPSEEK_API_KEY set)")

        return all_trends


# ============================================================================
# POST-PROCESSING
# ============================================================================

def deduplicate(trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove near-duplicate headlines (first 60 chars, lowercased)."""
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
    """Sort by velocity within each niche, cap per-niche, then globally."""
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
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")      # optional
    github_token = os.environ.get("GITHUB_TOKEN")           # optional

    if not deepseek_key:
        print("ℹ️  DEEPSEEK_API_KEY not set — AI synthesis will be skipped.")
    if not github_token:
        print("ℹ️  GITHUB_TOKEN not set — GitHub fetch will use unauthenticated rate limits.")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "..", "data", "trends.json")
    output_file = os.path.normpath(output_file)

    print(f"\n🚀 PulseRelay v5.1 — output → {output_file}\n")

    aggregator = TrendAggregator(deepseek_key=deepseek_key, github_token=github_token)

    raw = aggregator.aggregate_all_trends()
    print(f"\n✅ Raw collected:  {len(raw)}")

    unique = deduplicate(raw)
    print(f"✅ After dedup:    {len(unique)}")

    final = rank_and_filter(unique, max_per_niche=20, total_limit=150)
    print(f"✅ After ranking:  {len(final)}")

    payload = {
        "trends": final,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(final),
        "metadata": {
            "version": "5.1",
            "niches_covered": sorted(set(t["niche"] for t in final)),
            "sources_used": sorted(set(t["source"] for t in final)),
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
