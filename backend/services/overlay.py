"""Helpers for the Option B overlay package (HTML/JSON overlay, no image
typesetting).

- `clean_bubbles()` produces a "cleaned" page image with each detected speech
  bubble filled white, removing the original Japanese text. This is a minimal
  approach (solid white rectangle per bubble) -- good enough for a browser to
  render Arabic on top.
- `sha256_file()` hashes the output image for the delivery manifest.

Only Pillow is used (already a project dependency).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Tuple, Union

from PIL import Image, ImageDraw

PathLike = Union[str, Path]


def sha256_file(path: PathLike, *, chunk_size: int = 8192) -> str:
    """Return the hex SHA-256 digest of a file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_bubbles(
    src_image_path: PathLike,
    bubbles: Iterable[dict],
    out_path: PathLike,
    *,
    fill: Tuple[int, int, int] = (255, 255, 255),
) -> Tuple[Path, int, int]:
    """Fill each detected bubble with a solid color (white by default) to
    remove the original Japanese text, and save the cleaned page.

    Args:
        src_image_path: Original manga page image.
        bubbles: Iterable of bubble dicts, each with a "coordinates" mapping
            of {x1, y1, x2, y2} in original-image pixels.
        out_path: Where to write the cleaned PNG.
        fill: RGB fill color for the bubble interiors.

    Returns:
        (out_path, image_width, image_height)
    """
    img = Image.open(src_image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    for b in bubbles:
        c = b["coordinates"]
        x1 = int(round(float(c["x1"])))
        y1 = int(round(float(c["y1"])))
        x2 = int(round(float(c["x2"])))
        y2 = int(round(float(c["y2"])))
        draw.rectangle([x1, y1, x2, y2], fill=fill)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path, img.width, img.height
