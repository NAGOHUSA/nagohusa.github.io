# ── Bluesky - UPDATED with error handling and fallback ───────────────────────

def fetch_bluesky_trending(self) -> List[Dict[str, Any]]:
    """
    Pulls the public What's Hot feed via Bluesky's open AppView API.
    Zero authentication required. Skips private posts gracefully.
    Also includes fallback to Bluesky's public feed endpoint.
    """
    trends = []
    
    # Try primary What's Hot feed first
    try:
        r = self._safe_get(
            BSKY_POSTS_URL,
            timeout=12,
            params={"feed": BSKY_TRENDING_FEED, "limit": 40},  # Get extra to filter
        )
        if r:
            feed_data = r.json()
            for item in feed_data.get("feed", []):
                try:
                    post = item.get("post", {})
                    if not post:
                        continue
                    
                    # Check if post is accessible
                    record = post.get("record", {})
                    text = record.get("text", "").strip()
                    
                    # Skip empty or obviously private posts
                    if not text or text.startswith("Login to view"):
                        continue
                    
                    # Check author's profile for private indicator
                    author = post.get("author", {})
                    if author.get("viewer", {}).get("blocked") or author.get("labels", []):
                        # Could be private or blocked content - skip
                        continue
                    
                    likes = post.get("likeCount", 0)
                    reposts = post.get("repostCount", 0)
                    replies = post.get("replyCount", 0)
                    indexed = post.get("indexedAt", datetime.now(timezone.utc).isoformat())
                    
                    try:
                        epoch = datetime.fromisoformat(indexed.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        epoch = time.time()
                    age_h = self._age_hours(epoch)
                    
                    engagement = likes + reposts * 2 + replies
                    velocity = min((engagement / max(age_h, 0.5)) / 500, 1.0)
                    
                    uri = post.get("uri", "")
                    rkey = uri.split("/")[-1] if uri else ""
                    handle = author.get("handle", "bsky.app")
                    url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else "https://bsky.app"
                    
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
                except Exception as post_error:
                    # Skip individual failed posts, continue with others
                    print(f"    ⚠️  Skipping Bluesky post: {post_error}")
                    continue
                    
    except Exception as e:
        print(f"  ⚠️  Bluesky primary feed failed: {e}")
    
    # If primary feed returned nothing or very little, try alternative public endpoint
    if len(trends) < 5:
        print("  🔄  Bluesky primary feed thin, trying alternative timeline...")
        try:
            # Alternative: Popular feed (different feed ID)
            alt_feed_url = "https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed"
            alt_feed_id = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/popular"
            
            r2 = self._safe_get(
                alt_feed_url,
                timeout=12,
                params={"feed": alt_feed_id, "limit": 30},
            )
            if r2:
                for item in r2.json().get("feed", [])[:15]:
                    try:
                        post = item.get("post", {})
                        record = post.get("record", {})
                        text = record.get("text", "").strip()
                        
                        if not text or text.startswith("Login"):
                            continue
                        
                        likes = post.get("likeCount", 0)
                        trends.append({
                            "id": self._make_id("bsky_alt", post.get("uri", text)),
                            "niche": classify_social(text),
                            "headline": text[:200],
                            "summary": f"Popular on Bluesky — {likes:,} likes",
                            "velocity_score": min(likes / 1000, 1.0),
                            "signal_strength": 0.75,
                            "mentions_last_hour": max(likes // 24, 1),
                            "mentions_previous_24h": likes,
                            "source": "bluesky",
                            "source_url": f"https://bsky.app/profile/{post.get('author', {}).get('handle', '')}/post/{post.get('uri', '').split('/')[-1]}",
                            "is_human": True,
                            "timestamp": post.get("indexedAt", datetime.now(timezone.utc).isoformat()),
                            "tags": [],
                        })
                    except Exception:
                        continue
        except Exception as e:
            print(f"  ⚠️  Bluesky alt feed also failed: {e}")
    
    print(f"   → {len(trends)} valid public posts from Bluesky")
    return trends
