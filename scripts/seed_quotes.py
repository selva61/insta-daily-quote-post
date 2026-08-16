#!/usr/bin/env python3
"""One-time (or occasional) seeder: pull quotes from free public APIs,
dedupe, filter to a length that renders well on a card, and write
data/quotes.json.

Run locally, then eyeball/prune the result before the first live run:
    python scripts/seed_quotes.py
"""

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / "data" / "quotes.json"

MIN_LEN = 40
MAX_LEN = 180
TARGET_COUNT = 400


def fetch_zenquotes():
    """ZenQuotes /quotes returns ~50 curated quotes per call."""
    quotes = []
    try:
        resp = requests.get("https://zenquotes.io/api/quotes", timeout=15)
        resp.raise_for_status()
        for item in resp.json():
            text = item.get("q", "").strip()
            author = item.get("a", "").strip() or "Unknown"
            if text:
                quotes.append({"text": text, "author": author})
    except requests.RequestException as exc:
        print(f"[warn] ZenQuotes fetch failed: {exc}", file=sys.stderr)
    return quotes


def fetch_dummyjson(page_size=200, max_pages=8):
    """dummyjson.com/quotes: ~1450 quotes, paginated via limit/skip.

    Note: api.quotable.io (the more commonly recommended free quotes API)
    has a dead/expired TLS cert as of this writing and type.fit/api/quotes
    is truncated to a handful of entries — both were verified live and
    dropped in favor of this source.
    """
    quotes = []
    for page in range(max_pages):
        skip = page * page_size
        try:
            resp = requests.get(
                "https://dummyjson.com/quotes",
                params={"limit": page_size, "skip": skip},
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
            for item in payload.get("quotes", []):
                text = item.get("quote", "").strip()
                author = item.get("author", "").strip() or "Unknown"
                if text:
                    quotes.append({"text": text, "author": author})
            if skip + page_size >= payload.get("total", 0):
                break
        except requests.RequestException as exc:
            print(f"[warn] dummyjson fetch failed at skip={skip}: {exc}", file=sys.stderr)
            break
        time.sleep(0.2)
    return quotes


def dedupe_and_filter(quotes):
    seen = set()
    result = []
    for q in quotes:
        text = " ".join(q["text"].split())
        if not (MIN_LEN <= len(text) <= MAX_LEN):
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append({"text": text, "author": q["author"]})
    return result


def main():
    print("Fetching from ZenQuotes...")
    all_quotes = fetch_zenquotes()
    print(f"  got {len(all_quotes)}")

    print("Fetching from dummyjson...")
    dummyjson_quotes = fetch_dummyjson()
    print(f"  got {len(dummyjson_quotes)}")
    all_quotes.extend(dummyjson_quotes)

    filtered = dedupe_and_filter(all_quotes)
    print(f"After dedupe + length filter ({MIN_LEN}-{MAX_LEN} chars): {len(filtered)} quotes")

    if len(filtered) > TARGET_COUNT:
        filtered = filtered[:TARGET_COUNT]

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(filtered)} quotes to {OUT_FILE}")
    print("Review this file by hand before the first live run — remove anything")
    print("off-brand, misattributed, or duplicated in spirit.")


if __name__ == "__main__":
    main()
