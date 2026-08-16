"""Fetch a themed, previously-unused, portrait nature/automotive photo
from the Pexels API.
"""

import io
import json
import random
import sys

import requests
from PIL import Image

import config

API_URL = "https://api.pexels.com/v1/search"
CANDIDATES_PER_THEME = 5


def _load_used():
    if config.USED_PHOTOS_FILE.exists():
        with open(config.USED_PHOTOS_FILE) as f:
            return set(json.load(f))
    return set()


def _save_used(used_ids):
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.USED_PHOTOS_FILE, "w") as f:
        json.dump(sorted(used_ids), f, indent=2)


def _busy_score(image: Image.Image, box: dict) -> float:
    """Rough 'how busy is this region' heuristic: stddev of luminance
    inside the text safe-box. Low stddev = flat sky/water = good for text.
    """
    region = image.crop((box["left"], box["top"], box["right"], box["bottom"])).convert("L")
    pixels = list(region.getdata())
    mean = sum(pixels) / len(pixels)
    variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
    return variance ** 0.5


def fetch_themed_photo():
    """Search a random theme, download the first unused candidate that
    isn't too visually busy behind the text box. Returns (PIL.Image, meta dict).
    """
    if not config.PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY is not set")

    used = _load_used()
    headers = {"Authorization": config.PEXELS_API_KEY}
    themes = config.THEMES[:]
    random.shuffle(themes)

    for theme in themes:
        params = {
            "query": theme,
            "orientation": "portrait",
            "size": "large",
            "per_page": CANDIDATES_PER_THEME,
            "page": random.randint(1, 5),
        }
        resp = requests.get(API_URL, headers=headers, params=params, timeout=20)
        if resp.status_code != 200:
            print(f"[warn] Pexels search failed for '{theme}': {resp.status_code}", file=sys.stderr)
            continue
        photos = resp.json().get("photos", [])
        random.shuffle(photos)

        best = None
        best_score = None
        for photo in photos:
            if str(photo["id"]) in used:
                continue
            img_url = photo["src"]["large2x"]
            img_resp = requests.get(img_url, timeout=30)
            if img_resp.status_code != 200:
                continue
            image = Image.open(io.BytesIO(img_resp.content)).convert("RGB")

            # Cover-fit to card aspect ratio before scoring the text-box region.
            image = _cover_fit(image, config.CARD_WIDTH, config.CARD_HEIGHT)
            score = _busy_score(image, config.TEXT_BOX)
            if best_score is None or score < best_score:
                best, best_score = (image, photo), score

        if best is not None:
            image, photo = best
            used.add(str(photo["id"]))
            _save_used(used)
            meta = {
                "id": photo["id"],
                "theme": theme,
                "photographer": photo["photographer"],
                "pexels_url": photo["url"],
            }
            return image, meta

    raise RuntimeError("No unused Pexels photo found across all themes — top up data/quotes.json themes or clear state/used_photos.json")


def _cover_fit(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = image.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)

    image = image.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return image.crop((left, top, left + target_w, top + target_h))
