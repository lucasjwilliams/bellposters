#!/usr/bin/env python3
"""Fetch a cut-out picture for every item in data/items.js that lacks one.

For each item with a "wiki" article and no image file yet, this takes the
article's lead photo from Wikimedia Commons, removes the background with
rembg, crops it to the subject and saves it as a lossless WebP at the item's
"image" path, plus a thumbnail. The photographer and licence go into
images/credits.json, since most Commons licences require a credit.

Run with uv, which fetches the dependencies:
  uv run --python 3.12 --with rembg --with onnxruntime --with pillow --with requests --with scipy tools/fetch_images.py
Pass item ids to redo just those, e.g. `... fetch_images.py sheep cat`.
To use a different photo, set "wiki" to another article, or put "File:Name.jpg"
to use a specific Commons file.
"""
import io
import json
import os
import re
import sys
import time

import numpy as np
import requests
from PIL import Image, ImageEnhance
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_thumbs import make_thumb  # noqa: E402
from rembg import new_session, remove

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
UA = {"User-Agent": "BellWeightPosters/1.0 (bell poster generator; python-requests)"}
MAX_SIZE = 480


def get(url, **kwargs):
    for attempt in range(5):
        r = requests.get(url, headers=UA, timeout=60, **kwargs)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()


def load_items():
    with open(os.path.join(ROOT, "data", "items.js"), encoding="utf-8") as f:
        src = f.read()
    body = re.search(r"window\.ITEMS\s*=\s*(\[.*\])\s*;", src, re.S).group(1)
    return json.loads(body)


def lead_image_file(article):
    if article.startswith("File:"):
        return article
    r = get("https://en.wikipedia.org/w/api.php", params={
        "action": "query", "prop": "pageimages", "piprop": "name",
        "titles": article, "redirects": 1, "format": "json",
    }).json()
    page = next(iter(r["query"]["pages"].values()))
    name = page.get("pageimage")
    return f"File:{name}" if name else None


def commons_info(file_title):
    r = get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "prop": "imageinfo", "iiprop": "url|extmetadata",
        "iiurlwidth": 1000, "titles": file_title, "format": "json",
    }).json()
    page = next(iter(r["query"]["pages"].values()))
    if "imageinfo" not in page:
        return None  # not on Commons, e.g. a non-free English Wikipedia file
    info = page["imageinfo"][0]
    meta = info.get("extmetadata", {})
    strip = lambda s: re.sub(r"<[^>]+>", "", s or "").strip()
    return {
        "url": info.get("thumburl") or info["url"],
        "source": info["descriptionurl"],
        "artist": strip(meta.get("Artist", {}).get("value")) or "Unknown",
        "licence": strip(meta.get("LicenseShortName", {}).get("value")) or "See source",
    }


def tidy(img, opts=None):
    """Drop the faint haze and stray scraps background removal leaves behind,
    then crop to the subject. opts is an item's optional "cutout" settings:
      fillHoles: true   put back anything removed from inside the outline
                        (e.g. a laptop's shiny screen)
      rotate: 35        degrees anticlockwise
      brightness / contrast: 1.3   lighten or add contrast to a dull photo
    """
    opts = opts or {}
    alpha = np.array(img.getchannel("A"))
    if opts.get("fillHoles"):
        inside = ndimage.binary_fill_holes(alpha > 128)
        alpha[inside] = np.maximum(alpha[inside], 255)
    alpha[alpha < 60] = 0
    # Keep the biggest solid shape, plus any other shape at least a fifth its size
    labels, n = ndimage.label(alpha > 128)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
        keep = np.isin(labels, 1 + np.flatnonzero(sizes >= sizes.max() / 5))
        near = ndimage.binary_dilation(keep, iterations=3)  # keep soft edges
        alpha[~near] = 0
    alpha = Image.fromarray(alpha)
    img.putalpha(alpha)
    if opts.get("brightness") or opts.get("contrast"):
        rgb = img.convert("RGB")
        rgb = ImageEnhance.Brightness(rgb).enhance(opts.get("brightness", 1))
        rgb = ImageEnhance.Contrast(rgb).enhance(opts.get("contrast", 1))
        rgb.putalpha(alpha)
        img = rgb
    if opts.get("rotate"):
        img = img.rotate(opts["rotate"], resample=Image.BICUBIC, expand=True)
    bbox = img.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
    img.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
    return img


def cut_out(data, session, opts=None):
    return tidy(remove(Image.open(io.BytesIO(data)).convert("RGB"), session=session), opts)


def main():
    only = set(sys.argv[1:])
    credits_path = os.path.join(ROOT, "images", "credits.json")
    credits = {}
    if os.path.exists(credits_path):
        with open(credits_path, encoding="utf-8") as f:
            credits = json.load(f)

    session = new_session("isnet-general-use")
    for item in load_items():
        if not item.get("wiki") or not item.get("image"):
            continue
        out = os.path.join(ROOT, item["image"])
        if only and item["id"] not in only:
            continue
        if not only and os.path.exists(out):
            continue
        try:
            file_title = lead_image_file(item["wiki"])
            info = commons_info(file_title) if file_title else None
            if not info:
                print(f"SKIP {item['id']}: no free lead image for {item['wiki']!r}")
                continue
            data = get(info["url"]).content
        except requests.RequestException as err:
            # One slow download shouldn't lose the credits for everything else
            print(f"FAIL {item['id']}: {err} (run again to retry)")
            continue
        cut_out(data, session, item.get("cutout")).save(out, "WEBP", lossless=True, quality=100, method=6)
        make_thumb(out)
        credits[item["id"]] = {"name": item["name"], "file": file_title, **info}
        print(f"OK   {item['id']}: {file_title} ({info['licence']})")
        time.sleep(1)

    # Forget credits for items that have since been removed
    ids = {i["id"] for i in load_items()}
    credits = {k: v for k, v in credits.items() if k in ids}
    with open(credits_path, "w", encoding="utf-8") as f:
        json.dump(credits, f, ensure_ascii=False, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
