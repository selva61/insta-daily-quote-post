"""Pick a previously-unused royalty-free background track for today's Reel.

Same used-tracking pattern as pexels.py: cycles through the curated pool in
data/music.json (built by scripts/seed_music.py), resetting once exhausted.
"""

import json
import random
import sys

import config


def _load_manifest():
    if not config.MUSIC_MANIFEST.exists():
        sys.exit(f"No music manifest at {config.MUSIC_MANIFEST} — run scripts/seed_music.py first.")
    with open(config.MUSIC_MANIFEST) as f:
        return json.load(f)


def _load_used():
    if config.USED_AUDIO_FILE.exists():
        with open(config.USED_AUDIO_FILE) as f:
            return set(json.load(f))
    return set()


def _save_used(used):
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.USED_AUDIO_FILE, "w") as f:
        json.dump(sorted(used), f, indent=2)


def pick_track(mark_used: bool):
    """Returns a dict: {title, filename, credit, path}."""
    tracks = _load_manifest()
    used = _load_used()

    unused = [t for t in tracks if t["filename"] not in used]
    if not unused:
        print("[info] Music pool exhausted — cycling back to the full pool.", file=sys.stderr)
        used = set()
        unused = tracks

    track = random.choice(unused)
    if mark_used:
        used.add(track["filename"])
        _save_used(used)

    path = config.AUDIO_DIR / track["filename"]
    if not path.exists():
        sys.exit(f"Track file missing: {path} — run scripts/seed_music.py")

    return {**track, "path": path}
