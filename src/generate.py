#!/usr/bin/env python3
"""Orchestrator: pick an unused quote + unused themed photo, render the
card, and write it (plus a caption/metadata sidecar) into out/.

Usage:
    python src/generate.py                      # real run, dated filename, marks quote+photo used
    python src/generate.py --dry-run --count 10  # local preview, doesn't touch state/
"""

import argparse
import json
import random
import sys
from datetime import date, datetime, timezone

import config
import pexels
import render


def _load_quotes():
    if not config.QUOTES_FILE.exists():
        sys.exit(f"No quote bank at {config.QUOTES_FILE} — run scripts/seed_quotes.py first.")
    with open(config.QUOTES_FILE) as f:
        return json.load(f)


def _load_used_quotes():
    if config.USED_QUOTES_FILE.exists():
        with open(config.USED_QUOTES_FILE) as f:
            return set(json.load(f))
    return set()


def _save_used_quotes(used):
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.USED_QUOTES_FILE, "w") as f:
        json.dump(sorted(used), f, indent=2)


def pick_quote(mark_used: bool):
    quotes = _load_quotes()
    used = _load_used_quotes()

    unused = [q for q in quotes if q["text"] not in used]
    if not unused:
        print("[info] Quote bank exhausted — cycling back to the full bank.", file=sys.stderr)
        used = set()
        unused = quotes

    quote = random.choice(unused)
    if mark_used:
        used.add(quote["text"])
        _save_used_quotes(used)
    return quote


def build_caption(quote: dict, theme: str) -> str:
    tags = list(config.HASHTAG_POOLS["general"])
    if "car" in theme or "highway" in theme or "road" in theme:
        tags += config.HASHTAG_POOLS["automotive"]
    else:
        tags += config.HASHTAG_POOLS["nature"]
    tags += config.HASHTAG_POOLS["reflective"]

    random.shuffle(tags)
    tags = tags[:11]

    return f'"{quote["text"]}"\n— {quote["author"]}\n\n' + " ".join(tags)


def generate_one(out_name: str, mark_used: bool):
    quote = pick_quote(mark_used=mark_used)
    photo, photo_meta = pexels.fetch_themed_photo()

    card = render.render_card(photo, quote["text"], quote["author"])

    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    image_path = config.OUT_DIR / f"{out_name}.jpg"
    render.save_jpeg(card, image_path)

    caption = build_caption(quote, photo_meta["theme"])
    meta = {
        "quote": quote,
        "photo": photo_meta,
        "caption": caption,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = config.OUT_DIR / f"{out_name}.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Wrote {image_path}")
    print(f"Wrote {meta_path}")
    print(f"Photo credit: {photo_meta['photographer']} ({photo_meta['pexels_url']})")
    print("--- caption ---")
    print(caption)
    return image_path, meta_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="preview only, does not mark quote/photo as used")
    parser.add_argument("--count", type=int, default=1, help="how many cards to generate (dry-run preview)")
    parser.add_argument("--date", type=str, default=None, help="override the date used in the output filename")
    args = parser.parse_args()

    if args.dry_run:
        for i in range(args.count):
            generate_one(f"dryrun-{i+1:02d}", mark_used=False)
            print()
    else:
        out_name = args.date or date.today().isoformat()
        generate_one(out_name, mark_used=True)


if __name__ == "__main__":
    main()
