"""Compose a 1080x1920 (9:16) quote card: background photo + legibility scrim +
auto-fit quote text + author + handle. This still frame becomes the visual
for a Reel — see src/video.py for the zoom + audio composite.

Legibility is the thing that makes or breaks these cards, so contrast is
measured against the actual pixels behind the text box rather than assumed.
"""

import math
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config

MIN_CONTRAST_RATIO = 4.5  # WCAG AA for normal text


def _font(path, size, axes=None):
    font = ImageFont.truetype(str(path), size)
    if axes is not None:
        font.set_variation_by_axes(list(axes))
    return font


def _srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(rgb):
    r, g, b = rgb
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def _region_luminance(image: Image.Image, box: dict) -> float:
    region = image.crop((box["left"], box["top"], box["right"], box["bottom"]))
    small = region.resize((40, 40))
    total = 0.0
    pixels = list(small.getdata())
    for p in pixels:
        total += _relative_luminance(p[:3])
    return total / len(pixels)


def _contrast_ratio(l1, l2):
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _apply_scrim(image: Image.Image, box: dict) -> Image.Image:
    """Darken behind the text box (soft-edged) until white text clears
    MIN_CONTRAST_RATIO, plus a light full-frame gradient for overall mood.
    """
    image = image.convert("RGB")

    # Full-frame vertical gradient vignette (subtle, aesthetic).
    gradient = Image.new("L", (1, config.CARD_HEIGHT), 0)
    for y in range(config.CARD_HEIGHT):
        t = y / config.CARD_HEIGHT
        # darker at top and bottom, clearer in the middle
        v = 0.45 * (1 - math.sin(t * math.pi)) + 0.10
        gradient.putpixel((0, y), int(v * 255))
    gradient = gradient.resize((config.CARD_WIDTH, config.CARD_HEIGHT))
    black = Image.new("RGB", image.size, (0, 0, 0))
    image = Image.composite(black, image, gradient)

    # Iteratively darken the text-box region until contrast target is met.
    pad = 40
    scrim_box = (
        max(0, box["left"] - pad),
        max(0, box["top"] - pad),
        min(config.CARD_WIDTH, box["right"] + pad),
        min(config.CARD_HEIGHT, box["bottom"] + pad),
    )
    mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(scrim_box, radius=32, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(60))

    opacity = 0.0
    white_luminance = 1.0
    for _ in range(20):
        candidate = Image.composite(
            Image.new("RGB", image.size, (0, 0, 0)),
            image,
            mask.point(lambda p, o=opacity: int(p * o)),
        )
        region_lum = _region_luminance(candidate, box)
        if _contrast_ratio(white_luminance, region_lum) >= MIN_CONTRAST_RATIO:
            return candidate
        opacity += 0.05
        if opacity >= 0.9:
            return candidate

    return image


def _wrap_and_fit(draw, text, font_path, max_size, min_size, box_w, box_h):
    """Try font sizes from max down to min; return the largest size whose
    wrapped block fits inside box_w x box_h, along with the wrapped lines.
    """
    for size in range(max_size, min_size - 1, -2):
        font = _font(font_path, size, [config.QUOTE_FONT_WEIGHT])
        # Estimate chars-per-line from average glyph width, then wrap.
        avg_char_w = font.getlength("abcdefghijklmnopqrstuvwxyz ") / 27
        chars_per_line = max(8, int(box_w / avg_char_w))
        lines = textwrap.wrap(text, width=chars_per_line) or [text]

        line_heights = []
        max_line_w = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            max_line_w = max(max_line_w, bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])

        line_gap = int(size * 0.35)
        total_h = sum(line_heights) + line_gap * (len(lines) - 1)

        if max_line_w <= box_w and total_h <= box_h:
            return font, lines, total_h, line_gap

    # Fall back to smallest size regardless of fit.
    font = _font(font_path, min_size, [config.QUOTE_FONT_WEIGHT])
    avg_char_w = font.getlength("abcdefghijklmnopqrstuvwxyz ") / 27
    chars_per_line = max(8, int(box_w / avg_char_w))
    lines = textwrap.wrap(text, width=chars_per_line) or [text]
    line_gap = int(min_size * 0.35)
    total_h = sum(
        draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]
        for line in lines
    ) + line_gap * (len(lines) - 1)
    return font, lines, total_h, line_gap


def _paste_logo(image: Image.Image) -> None:
    logo = Image.open(config.LOGO_PATH).convert("RGBA")
    aspect = logo.height / logo.width
    logo = logo.resize((config.LOGO_WIDTH, round(config.LOGO_WIDTH * aspect)), Image.LANCZOS)
    x = (config.CARD_WIDTH - logo.width) // 2
    image.paste(logo, (x, config.LOGO_TOP_MARGIN), logo)


def render_card(background: Image.Image, quote: str, author: str) -> Image.Image:
    box = config.TEXT_BOX
    box_w = box["right"] - box["left"]
    box_h = box["bottom"] - box["top"]

    image = _apply_scrim(background, box)
    _paste_logo(image)
    draw = ImageDraw.Draw(image)

    quote_font, lines, quote_h, line_gap = _wrap_and_fit(
        draw, f"“{quote}”", config.QUOTE_FONT,
        config.QUOTE_FONT_MAX_SIZE, config.QUOTE_FONT_MIN_SIZE, box_w, box_h - 90,
    )

    author_font = _font(config.META_FONT, config.AUTHOR_FONT_SIZE, config.META_FONT_AXES)
    author_text = f"— {author}"
    author_bbox = draw.textbbox((0, 0), author_text, font=author_font)
    author_h = author_bbox[3] - author_bbox[1]

    block_h = quote_h + 50 + author_h
    start_y = box["top"] + (box_h - block_h) // 2
    center_x = (box["left"] + box["right"]) // 2

    y = start_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=quote_font)
        line_w = bbox[2] - bbox[0]
        x = center_x - line_w // 2
        # subtle shadow for extra separation from busy backgrounds
        draw.text((x + 2, y + 2), line, font=quote_font, fill=(0, 0, 0, 140))
        draw.text((x, y), line, font=quote_font, fill=(255, 255, 255))
        y += (bbox[3] - bbox[1]) + line_gap

    y += 30
    author_w = author_bbox[2] - author_bbox[0]
    draw.text((center_x - author_w // 2, y), author_text, font=author_font, fill=(230, 230, 230))

    handle_font = _font(config.META_FONT, config.HANDLE_FONT_SIZE, config.META_FONT_BOLD_AXES)
    handle_bbox = draw.textbbox((0, 0), config.HANDLE, font=handle_font)
    handle_w = handle_bbox[2] - handle_bbox[0]
    draw.text(
        (center_x - handle_w // 2, config.CARD_HEIGHT - config.HANDLE_BOTTOM_MARGIN),
        config.HANDLE, font=handle_font, fill=(255, 255, 255),
    )

    return image.convert("RGB")


def save_jpeg(image: Image.Image, path):
    image.save(path, "JPEG", quality=90, optimize=True)
    size_mb = path.stat().st_size / (1024 * 1024)
    assert size_mb < 8, f"Card exceeds Instagram's 8MB limit ({size_mb:.1f}MB)"
