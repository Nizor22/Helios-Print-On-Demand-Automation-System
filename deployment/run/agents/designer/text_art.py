from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont


DEFAULT_CANVAS = (4500, 5400)  # width, height


def load_font(fonts_dir: Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Try some common fonts if available in assets; otherwise fallback to default
    preferred = [
        "Inter-Bold.ttf",
        "Montserrat-Bold.ttf",
        "OpenSans-Bold.ttf",
        "Poppins-Bold.ttf",
    ]
    for name in preferred:
        candidate = fonts_dir / name
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def create_text_design(
    text: str,
    out_dir: Path,
    fonts_dir: Path,
    canvas_size: Tuple[int, int] = DEFAULT_CANVAS,
    padding_ratio: float = 0.08,
    bg_rgba: Tuple[int, int, int, int] = (0, 0, 0, 0),
    text_rgb: Tuple[int, int, int] = (0, 0, 0),
) -> Path:
    """
    Create a large transparent PNG with centered multiline text.
    Returns the saved file path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    width, height = canvas_size
    image = Image.new("RGBA", (width, height), bg_rgba)
    draw = ImageDraw.Draw(image)

    # Adaptive font sizing based on text length
    max_text_width = width * (1 - padding_ratio * 2)
    max_text_height = height * (1 - padding_ratio * 2)

    # Binary search font size
    min_size, max_size = 40, 480
    best_font = None
    best_lines: list[str] = []

    def wrap_text(draw_obj: ImageDraw.ImageDraw, font_obj: ImageFont.ImageFont, raw_text: str, max_w: int) -> list[str]:
        words = raw_text.split()
        lines: list[str] = []
        line: list[str] = []
        for word in words:
            test_line = " ".join(line + [word])
            # Pillow 10+ removed textsize; use textbbox for accurate measurement
            bbox = draw_obj.textbbox((0, 0), test_line, font=font_obj)
            w = bbox[2] - bbox[0]
            if w <= max_w:
                line.append(word)
            else:
                if line:
                    lines.append(" ".join(line))
                line = [word]
        if line:
            lines.append(" ".join(line))
        return lines

    while min_size <= max_size:
        mid = (min_size + max_size) // 2
        font = load_font(fonts_dir, size=mid)
        lines = wrap_text(draw, font, text, int(max_text_width))
        line_heights = []
        total_h = 0
        for l in lines:
            bbox = draw.textbbox((0, 0), l, font=font)
            h = bbox[3] - bbox[1]
            line_heights.append(h)
            total_h += int(h * 1.15)
        if total_h <= max_text_height and lines:
            best_font = font
            best_lines = lines
            min_size = mid + 10
        else:
            max_size = mid - 10

    if best_font is None:
        best_font = load_font(fonts_dir, size=80)
        best_lines = [text]

    # Compute top-left for centered text
    total_h = 0
    for l in best_lines:
        bbox = draw.textbbox((0, 0), l, font=best_font)
        h = bbox[3] - bbox[1]
        total_h += int(h * 1.15)
    y = (height - total_h) // 2
    for l in best_lines:
        bbox = draw.textbbox((0, 0), l, font=best_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (width - w) // 2
        draw.text((x, y), l, fill=text_rgb, font=best_font)
        y += int(h * 1.15)

    # Save
    filename = f"{text.lower().replace(' ', '_')[:60]}".strip("_") or "design"
    out_path = out_dir / f"{filename}.png"
    # Ensure unique
    i = 2
    while out_path.exists():
        out_path = out_dir / f"{filename}_{i}.png"
        i += 1

    image.save(out_path, format="PNG")
    return out_path
