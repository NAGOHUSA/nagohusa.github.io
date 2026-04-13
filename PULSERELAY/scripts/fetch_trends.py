#!/usr/bin/env python3
"""
PulseRelay - Multi-Source Real-Time Trend Aggregator v5.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Changes from v5.2:
  • Google Trends — tries new URL format first, falls back to legacy (fixes 404)
  • Reuters feeds.reuters.com — DNS-blocked on Actions, replaced with Guardian/ABC/NPR
  • AP feeds.apnews.com — DNS-blocked on Actions, replaced with apnews.com/hub RSS
  • DeepSeek — catches ConnectionError wrapping ReadTimeoutError (fixes crash)
Sources (all free, no mandatory keys):
  • Google Trends   — multi-region, dual URL format fallback
  • News RSS        — BBC, Guardian, Al Jazeera, DW, NYT, NPR, Ars, Verge…
  • Wikipedia       — pageviews REST API
  • Hacker News     — Firebase JSON API
  • Lobste.rs       — JSON API (short timeout, graceful skip)
  • Dev.to          — public articles API
  • GitHub          — search API (optional token for higher rate limit)
  • Bluesky         — AT Protocol What's Hot feed, no auth
  • Mastodon        — mastodon.social + fosstodon + infosex.change, no auth
Optional:
  • DeepSeek        — AI synthesis for thin niches (set DEEPSEEK_API_KEY)
  • GitHub token    — higher rate limit (set GITHUB_TOKEN)
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
