# Bell Weight Posters

Make a printable poster that compares each bell in a tower to something that weighs about the same.

**Live site:** https://lucasjwilliams.github.io/bellposters/

Pick any ring from [Dove's Guide](https://dove.cccbr.org.uk/), untick or rename bells, swap the suggested items, choose a colour and layout, then print it, save it as a PDF or download it as an image. You can also start from scratch with a custom tower.

`?ring=<Dove ring id>` opens a tower directly (e.g. `?ring=825` for Edgbaston). **Copy share link** saves the whole poster, including any pictures people have added themselves, in the link.

## How it works

It's a static site with no build step: `index.html`, `style.css` and `app.js`, plus two data files.

- `data/rings.js` is every full-circle ring in Dove's Guide, with each bell's weight, note and diameter.
- `data/items.js` is the list of things to compare against.

Items are suggested by weight, heaviest bells first, while trying not to repeat the same kind of thing (two bears, two cars) or fill a poster with one category. The chosen items are then re-ordered so heavier bells always get heavier items.

## Adding items

Each entry in `data/items.js` looks like this:

```js
{ "id": "lion", "name": "Adult male lion", "kg": 190, "category": "animal", "kind": "big-cat", "wiki": "Lion", "image": "images/lion.webp" }
```

- `category`: animal, vehicle, home, food, music, sport, street, fun, travel, garden, history, prehistoric, space or building. Used to keep posters varied.
- `kind`: items with the same kind never appear on one poster together.
- `wiki`: the Wikipedia article (or a specific Commons file, `"File:Name.jpg"`) the picture comes from.
- `cutout` (optional): fixes for the automatic cut-out, `fillHoles`, `rotate`, `brightness` or `contrast`.

### Pictures

`tools/fetch_images.py` downloads the picture for each item that doesn't have one, removes the background, and saves a lossless WebP plus a small thumbnail for the item picker. It records each photographer and licence in `images/credits.json`.

```sh
uv run --python 3.12 --with rembg --with onnxruntime --with pillow --with requests --with scipy tools/fetch_images.py            # new items
uv run --python 3.12 --with rembg --with onnxruntime --with pillow --with requests --with scipy tools/fetch_images.py sheep cat   # redo these
```

If you add a picture by hand, put it in `images/` and run `tools/make_thumbs.py` to make its thumbnail.

## Updating the bell data

Download `dove.csv` and `bells.csv` from https://dove.cccbr.org.uk/downloads into the repo root and run:

```sh
python3 tools/build_data.py
```

## Running locally

Opening `index.html` directly works for everything except **Download as image**, which browsers block for local files. Use a local server for that:

```sh
python3 -m http.server
```

## Credits

- Bell data from [Dove's Guide for Church Bell Ringers](https://dove.cccbr.org.uk/), licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- Item photos from [Wikimedia Commons](https://commons.wikimedia.org/), under the licences listed in `images/credits.json`.
- Image export uses [html2canvas](https://html2canvas.hertzen.com/).

The code is released under the [MIT License](LICENSE). The bell data and photos keep their own licences above.
