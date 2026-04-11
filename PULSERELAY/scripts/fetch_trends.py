#!/usr/bin/env python3
"""
PulseRelay – fetch_trends.py
Calls the DeepSeek API and writes trending topics to PULSERELAY/data/trends.json.

Required environment variable:
    DEEPSEEK_API_KEY  – your DeepSeek API key (set as a GitHub Secret)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# ── Configuration ─────────────────────────────────────────────────────────────

API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

NICHES = [
    "Cinema",
    "Sports",
    "World Events",
    "Streaming",
    "Music",
    "Space",
    "Tech",
    "3D Printing",
    "Privacy",
    "Repair Economy",
    "Outdoors",
    "Legal Tech",
]

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "trends.json"

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a JSON Trends Generator. "
    "When given a list of niches, you respond ONLY with a valid JSON array. "
    "Each element represents a trending topic and must have exactly these fields:\n"
    "  title        (string)  – short headline of the trend\n"
    "  summary      (string)  – 2-3 sentence explanation\n"
    "  sourceURL    (string)  – a plausible URL to a real or representative source\n"
    "  timestamp    (string)  – current date-time in ISO 8601 format (UTC, e.g. 2025-06-01T12:00:00Z)\n"
    "  niche        (string)  – the niche this trend belongs to\n"
    "  isHuman      (boolean) – true if the story is primarily about human activity, false if it is technology/event-driven\n"
    "  velocityScore (number) – integer 1-100 indicating how fast this trend is growing\n\n"
    "Return ONLY the JSON array. No markdown fences, no commentary, no extra text."
)

USER_PROMPT = (
    f"Today is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}. "
    f"Generate 2 trending topics for each of the following niches: {', '.join(NICHES)}. "
    "Ensure the timestamp field reflects today's date in ISO 8601 UTC format."
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def fetch_trends(api_key: str) -> list[dict]:
    """Call the DeepSeek API and return the parsed list of trend objects."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    raw_content: str = response.json()["choices"][0]["message"]["content"].strip()

    # Strip optional markdown code fences that the model may still include
    if raw_content.startswith("```"):
        raw_content = raw_content.split("```", 2)[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]
        raw_content = raw_content.rsplit("```", 1)[0].strip()

    trends: list[dict] = json.loads(raw_content)

    if not isinstance(trends, list):
        raise ValueError("DeepSeek response is not a JSON array.")

    return trends


def validate_trend(trend: dict, index: int) -> dict:
    """Ensure required fields are present and have the correct types."""
    required = {
        "title": str,
        "summary": str,
        "sourceURL": str,
        "timestamp": str,
        "niche": str,
        "isHuman": bool,
        "velocityScore": (int, float),
    }
    for field, expected_type in required.items():
        if field not in trend:
            raise ValueError(f"Trend #{index} is missing field '{field}'.")
        if not isinstance(trend[field], expected_type):
            # Attempt a light coercion for numeric velocityScore
            if field == "velocityScore":
                trend[field] = int(trend[field])
            else:
                raise TypeError(
                    f"Trend #{index} field '{field}' has wrong type "
                    f"(expected {expected_type}, got {type(trend[field])})."
                )
    return trend


# ── Entry Point ───────────────────────────────────────────────────────────────


def main() -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print("Fetching trends from DeepSeek…")
    trends = fetch_trends(api_key)
    print(f"  Received {len(trends)} trend(s).")

    validated = [validate_trend(t, i) for i, t in enumerate(trends)]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(validated, fh, ensure_ascii=False, indent=2)

    print(f"  Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
