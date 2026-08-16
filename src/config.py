"""Shared constants for the daily quote card pipeline."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATE_DIR = ROOT / "state"
OUT_DIR = ROOT / "out"
FONTS_DIR = ROOT / "assets" / "fonts"
AUDIO_DIR = ROOT / "assets" / "audio"

QUOTES_FILE = DATA_DIR / "quotes.json"
USED_QUOTES_FILE = STATE_DIR / "used_quotes.json"
USED_PHOTOS_FILE = STATE_DIR / "used_photos.json"
MUSIC_MANIFEST = DATA_DIR / "music.json"
USED_AUDIO_FILE = STATE_DIR / "used_audio.json"

# 9:16 — required for Reels (posts are Reels, not static feed photos, so
# there's audio behind them; see src/video.py).
CARD_WIDTH = 1080
CARD_HEIGHT = 1920
REEL_DURATION_SECONDS = 11

# Safe box the quote text must fit inside — clear of Reels' own UI chrome:
# top status area, and the bottom zone reserved for username/caption/audio
# disc plus the right-side like/comment/share icon column.
TEXT_BOX = {
    "left": 110,
    "right": 900,
    "top": 420,
    "bottom": 1400,
}

# The @handle is drawn below the quote block at a fixed offset from the
# bottom, comfortably clear of TEXT_BOX's bottom edge and of Instagram's
# own username/caption overlay on Reels.
HANDLE_BOTTOM_MARGIN = 420

# Both are variable fonts; render.py instantiates specific weights via
# Pillow's set_variation_by_axes rather than separate static files.
QUOTE_FONT = FONTS_DIR / "PlayfairDisplay-Variable.ttf"
QUOTE_FONT_WEIGHT = 700
META_FONT = FONTS_DIR / "Inter-Variable.ttf"
META_FONT_AXES = (14, 400)  # (optical size, weight) — regular
META_FONT_BOLD_AXES = (14, 600)  # semibold

HANDLE = "@nocturnalnotesselva"

QUOTE_FONT_MAX_SIZE = 72
QUOTE_FONT_MIN_SIZE = 34
AUTHOR_FONT_SIZE = 32
HANDLE_FONT_SIZE = 28

# Pexels search themes, rotated daily. Keep this list broad — the account's
# existing aesthetic is nature/landscape with occasional automotive shots.
THEMES = [
    "misty mountains landscape",
    "forest sunlight path",
    "ocean waves aerial",
    "calm lake reflection",
    "desert dunes sunset",
    "golden hour sky clouds",
    "waterfall nature",
    "coastline cliffs",
    "winter landscape snow",
    "classic car road",
    "open highway drive",
    "autumn forest road",
]

HASHTAG_POOLS = {
    "general": [
        "#dailyquote", "#quoteoftheday", "#inspirationalquotes", "#mindfulness",
        "#positivevibes", "#wisdomwords", "#motivationdaily", "#innerpeace",
    ],
    "nature": [
        "#naturelovers", "#landscapephotography", "#natureaesthetic",
        "#earthfocus", "#wildernessculture", "#naturequotes",
    ],
    "automotive": [
        "#carsofinstagram", "#roadtrip", "#drivingquotes", "#openroad",
    ],
    "reflective": [
        "#selfgrowth", "#stoicism", "#slowliving", "#eveningthoughts",
        "#nocturnalnotes",
    ],
}

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
# Check developers.facebook.com/docs/graph-api/changelog/versions for the
# current version before it ages out of Meta's ~2-year support window.
IG_API_VERSION = os.environ.get("IG_API_VERSION", "v22.0")

# Filled in by generate.py at runtime with the public raw.githubusercontent.com
# URL for the committed card image (SHA-pinned so it's immutable).
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
