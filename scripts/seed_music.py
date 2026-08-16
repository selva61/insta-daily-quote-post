#!/usr/bin/env python3
"""One-time seeder: download a curated pool of calm/ambient Kevin MacLeod
tracks (incompetech.com, CC BY 4.0) into assets/audio/, and write
data/music.json with per-track attribution.

License requires attribution — generate.py appends the credit line to the
caption automatically, no action needed at post time.

Run locally, then listen through the pool once before the first live run:
    python scripts/seed_music.py
"""

import json
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "assets" / "audio"
MANIFEST_FILE = ROOT / "data" / "music.json"

BASE_URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/"

# Source tracks run minutes long; we only ever use ~11s per post, so trim
# and re-encode at a modest bitrate before committing — keeps the repo
# lean instead of carrying full-length, full-bitrate music files.
SNIPPET_SECONDS = 40
SNIPPET_BITRATE = "96k"

# Verified live (HTTP 200) against incompetech.com before adding here.
# Picked for a calm/ambient/reflective mood matching the account.
TRACKS = [
    "Wallpaper",
    "Meditation Impromptu 01",
    "Meditation Impromptu 02",
    "Meditation Impromptu 03",
    "Relaxing Piano Music",
    "Canon in D Major",
    "Gymnopedie No 1",
    "Dreams Become Real",
    "Floating Cities",
    "Ethereal Relaxation",
    "Healing",
]


def credit_for(title: str) -> str:
    return (
        f'"{title}" by Kevin MacLeod (incompetech.com) '
        "Licensed under Creative Commons: By Attribution 4.0 "
        "https://creativecommons.org/licenses/by/4.0/"
    )


def main():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for title in TRACKS:
        filename = title.replace(" ", "_") + ".mp3"
        dest = AUDIO_DIR / filename
        url = BASE_URL + urllib.parse.quote(title) + ".mp3"

        if dest.exists() and dest.stat().st_size > 0:
            print(f"[skip] {title} already downloaded")
        else:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200 or len(resp.content) < 10_000:
                print(f"[warn] failed to fetch '{title}' ({resp.status_code}, "
                      f"{len(resp.content)} bytes) — skipping", file=sys.stderr)
                continue

            with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
                tmp.write(resp.content)
                tmp.flush()
                result = subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", tmp.name,
                        "-t", str(SNIPPET_SECONDS),
                        "-b:a", SNIPPET_BITRATE,
                        "-ac", "2",
                        str(dest),
                    ],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    print(f"[warn] ffmpeg trim failed for '{title}': {result.stderr[-500:]}",
                          file=sys.stderr)
                    continue

            print(f"[ok] {title} -> {dest.name} ({dest.stat().st_size // 1024} KB, "
                  f"trimmed from {len(resp.content) // 1024} KB)")

        manifest.append({
            "title": title,
            "filename": filename,
            "credit": credit_for(title),
        })

    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(manifest)} tracks to {MANIFEST_FILE}")
    print("Listen through these once before the first live run — title alone")
    print("doesn't guarantee mood fit, remove anything that doesn't match.")


if __name__ == "__main__":
    main()
