#!/usr/bin/env python3
"""Make the small copies of item pictures that the page's lists use.

The poster (and so printing and image downloads) uses the full-size lossless
pictures in images/. The item picker and bell list only show pictures at about
60 px, so they load these instead: images/thumbs/<name>.webp, at most THUMB_SIZE
pixels across (twice the display size, for sharp phone screens), lossy.

  uv run --python 3.12 --with pillow tools/make_thumbs.py          # all missing or out of date
  uv run --python 3.12 --with pillow tools/make_thumbs.py --all    # redo every one
tools/fetch_images.py makes the thumbnail itself for each picture it fetches.
"""
import glob
import os
import sys

from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
THUMB_SIZE = 160


def thumb_path(image_path):
    name = os.path.splitext(os.path.basename(image_path))[0] + ".webp"
    return os.path.join(os.path.dirname(image_path), "thumbs", name)


def make_thumb(image_path):
    out = thumb_path(image_path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img = Image.open(image_path).convert("RGBA")
    img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
    img.save(out, "WEBP", quality=82, method=6)
    return out


def main():
    redo = "--all" in sys.argv
    made = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "images", "*.webp")) + glob.glob(os.path.join(ROOT, "images", "*.png"))):
        out = thumb_path(path)
        if redo or not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(path):
            make_thumb(path)
            made += 1
    total = sum(os.path.getsize(p) for p in glob.glob(os.path.join(ROOT, "images", "thumbs", "*.webp")))
    print(f"Made {made} thumbnails; images/thumbs is {total / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
