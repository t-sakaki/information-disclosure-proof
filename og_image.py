"""
Generates the og:image / twitter:image for a Case page (/case/{uid}) as a
PNG, so that when the Case link is shared on X/Bluesky/etc, the preview
card shows the actual disclosure request content (target authority,
summary, support raised) -- not just a bare title/description text card.

Rendered with Pillow rather than an HTML->image service, since the content
is short and structured (a handful of fields) and this avoids adding a
headless-browser dependency for a single image. Uses Noto Sans JP
(static/fonts/NotoSansJP.ttf, OFL-licensed, bundled in the repo) since the
request content is Japanese.

The image itself is generated on every request rather than cached/stored,
consistent with the rest of the app reading straight from the chain: there
is no database, so there's nothing to invalidate when a new tip comes in.
"""
from __future__ import annotations

import io
import os
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from ledger import format_amount

WIDTH, HEIGHT = 1200, 630
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "fonts", "NotoSansJP.ttf")

BG_TOP = (11, 13, 18)
BG_BOTTOM = (20, 16, 34)
SURFACE = (27, 31, 42)
BORDER = (38, 43, 56)
TEXT = (238, 240, 244)
TEXT_DIM = (154, 161, 177)
ACCENT = (109, 139, 255)
ACCENT_2 = (126, 240, 192)


def _font(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(FONT_PATH, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    current = ""
    for ch in text:
        trial = current + ch
        if draw.textlength(trial, font=font) > max_width and current:
            lines.append(current)
            current = ch
            if len(lines) == max_lines - 1:
                break
        else:
            current = trial
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if len(lines) == max_lines:
        last = lines[-1]
        while draw.textlength(last + "…", font=font) > max_width and len(last) > 1:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


def _vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (1, h), 0)
    for y in range(h):
        t = y / max(h - 1, 1)
        base.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return base.resize((w, h))


def _rounded_rect(draw: ImageDraw.ImageDraw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def render_case_og_image(uid: str, case: dict[str, Any]) -> bytes:
    req = case["request"]
    img = _vertical_gradient((WIDTH, HEIGHT), BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    pad = 64

    # --- top badge: "Recorded on-chain" ---
    badge_font = _font(24, 600)
    badge_text = "RECORDED ON-CHAIN · BASE SEPOLIA · EAS"
    badge_w = draw.textlength(badge_text, font=badge_font) + 56
    _rounded_rect(draw, (pad, pad, pad + badge_w, pad + 56), radius=28, fill=SURFACE, outline=BORDER, width=1)
    draw.ellipse((pad + 22, pad + 22, pad + 34, pad + 34), fill=ACCENT_2)
    draw.text((pad + 46, pad + 15), badge_text, font=badge_font, fill=TEXT_DIM)

    # --- target authority (headline) ---
    y = pad + 100
    authority_font = _font(60, 800)
    authority_lines = _wrap(draw, req["target_authority"], authority_font, WIDTH - pad * 2, 2)
    for line in authority_lines:
        draw.text((pad, y), line, font=authority_font, fill=TEXT)
        y += 74

    # --- request type pill ---
    y += 6
    type_font = _font(28, 600)
    type_text = req["request_type"]
    type_w = draw.textlength(type_text, font=type_font) + 40
    _rounded_rect(draw, (pad, y, pad + type_w, y + 48), radius=24, fill=None, outline=ACCENT, width=2)
    draw.text((pad + 20, y + 9), type_text, font=type_font, fill=ACCENT)
    y += 74

    # --- summary ---
    summary_font = _font(32, 400)
    summary_text = req["summary"] or "(no summary provided / 要約なし)"
    for line in _wrap(draw, summary_text, summary_font, WIDTH - pad * 2, 3):
        draw.text((pad, y), line, font=summary_font, fill=TEXT_DIM)
        y += 44

    # --- bottom stat bar ---
    bar_h = 130
    bar_top = HEIGHT - bar_h - pad + 20
    _rounded_rect(draw, (pad, bar_top, WIDTH - pad, bar_top + bar_h), radius=18, fill=SURFACE, outline=BORDER, width=1)

    totals_text = ", ".join(f'{format_amount(t["amount"])} {t["currency"]}' for t in case["totals"]) or "0"
    label_font = _font(22, 600)

    col1_x = pad + 40
    col2_x = pad + 40 + (WIDTH - pad * 2 - 80) // 2
    # The raised-amount column must not run into the supporters column, so
    # shrink its font until it fits the space available (a long "0.000001
    # ETH, 2 USDC" would otherwise overlap "SUPPORTERS" at a fixed size).
    max_value_width = col2_x - col1_x - 30
    value_size = 44
    while value_size > 22 and draw.textlength(totals_text, font=_font(value_size, 800)) > max_value_width:
        value_size -= 2
    value_font = _font(value_size, 800)
    if draw.textlength(totals_text, font=value_font) > max_value_width:
        totals_text = _wrap(draw, totals_text, value_font, max_value_width, 1)[0]
    supporters_font = _font(44, 800)

    draw.text((col1_x, bar_top + 20), "RAISED / 集まった応援", font=label_font, fill=TEXT_DIM)
    draw.text((col1_x, bar_top + 52 + (44 - value_size)), totals_text, font=value_font, fill=ACCENT_2)

    draw.text((col2_x, bar_top + 20), "SUPPORTERS / 応援者数", font=label_font, fill=TEXT_DIM)
    draw.text((col2_x, bar_top + 52), str(case["tip_count"]), font=supporters_font, fill=TEXT)

    site_font = _font(24, 600)
    site_text = "Disclosure Proof"
    site_w = draw.textlength(site_text, font=site_font)
    draw.text((WIDTH - pad - 40 - site_w, bar_top + 34), site_text, font=site_font, fill=TEXT)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
