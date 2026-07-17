"""Generate the repo's hero + evidence graphics with Pillow.

Every value rendered here is REAL: the JSON card fields come from
walmart_scraper_api_data/search.json, and the block evidence comes from the
measured free-scraper run (HTTP 200, 15,190 bytes, title "Robot or human?").
Nothing here is a mocked-up screenshot of a page we could not reach.
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(OUT, "..", "walmart_scraper_api_data")
F = "C:/Windows/Fonts/"


def font(name, size):
    for cand in (name, "segoeui.ttf"):
        try:
            return ImageFont.truetype(F + cand, size)
        except OSError:
            continue
    return ImageFont.load_default()


BOLD, SEMI, REG, MONO = "segoeuib.ttf", "seguisb.ttf", "segoeui.ttf", "consola.ttf"
INK = (245, 243, 240)
MUTE = (169, 162, 154)
DIM = (111, 106, 100)
ACC = (255, 143, 90)
ACC2 = (255, 196, 138)


def vgrad(w, h, top, bot):
    """Vertical gradient base."""
    img = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.point((0, y), tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return img.resize((w, h))


def glow(img, cx, cy, rx, ry, color, strength):
    """Soft radial glow, composited additively."""
    layer = Image.new("RGB", img.size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 44
    for i in range(steps, 0, -1):
        t = i / steps
        a = int(strength * (1 - t) ** 2.2)
        d.ellipse([cx - rx * t, cy - ry * t, cx + rx * t, cy + ry * t],
                  fill=tuple(int(c * a / 255) for c in color))
    return Image.blend(img, Image.blend(img, layer, 0), 0) if False else \
        Image.fromarray(__import__("numpy").clip(
            __import__("numpy").asarray(img, dtype=int) + __import__("numpy").asarray(layer, dtype=int),
            0, 255).astype("uint8"))


def pill(d, x, y, text, f, hot=False):
    w = d.textlength(text, font=f)
    h = 30
    d.rounded_rectangle([x, y, x + w + 28, y + h], radius=15,
                        fill=(28, 20, 17) if hot else (25, 26, 30),
                        outline=(120, 66, 44) if hot else (52, 54, 60))
    d.text((x + 14, y + 6), text, font=f, fill=ACC2 if hot else (221, 214, 207))
    return w + 28 + 9


def hero():
    W, H = 1280, 540
    img = vgrad(W, H, (15, 17, 21), (26, 18, 16))
    img = glow(img, 1000, 100, 520, 300, (255, 143, 90), 46)
    img = glow(img, 150, 470, 420, 260, (120, 84, 60), 40)
    d = ImageDraw.Draw(img)

    # faint grid
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(24, 26, 31))
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=(24, 26, 31))

    # brand
    d.ellipse([64, 60, 75, 71], fill=ACC)
    d.text((88, 57), "C H O C O D A T A", font=font(SEMI, 15), fill=(185, 178, 170))

    # headline
    d.text((64, 108), "Walmart", font=font(BOLD, 76), fill=INK)
    d.text((64, 192), "Scraper", font=font(BOLD, 76), fill=ACC)

    d.text((64, 300), "Extract product prices, ratings, reviews, specifications", font=font(REG, 23), fill=MUTE)
    d.text((64, 334), "and bestsellers from Walmart.com as structured JSON.", font=font(REG, 23), fill=MUTE)

    # element pills
    els = [("prices", 1), ("titles", 1), ("descriptions", 0), ("specifications", 1), ("ratings", 1),
           ("reviews", 1), ("search results", 0), ("bestsellers", 0), ("sellers", 0), ("UPC / GTIN", 0),
           ("inventory", 0), ("category filters", 0)]
    f = font(REG, 15)
    x, y = 64, 410
    for t, hot in els:
        w = d.textlength(t, font=f) + 37
        if x + w > 700:
            x, y = 64, y + 39
        x += pill(d, x, y, t, f, hot=bool(hot))

    # real JSON card
    cx, cy, cw = 828, 150, 388
    d.rounded_rectangle([cx, cy, cx + cw, cy + 268], radius=14, fill=(11, 13, 17), outline=(45, 47, 53))
    d.rounded_rectangle([cx, cy, cx + cw, cy + 38], radius=14, fill=(21, 23, 28))
    d.rectangle([cx, cy + 24, cx + cw, cy + 38], fill=(21, 23, 28))
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse([cx + 14 + i * 18, cy + 14, cx + 24 + i * 18, cy + 24], fill=c)
    d.line([(cx, cy + 38), (cx + cw, cy + 38)], fill=(38, 40, 46))

    s = json.load(open(os.path.join(DATA, "search.json"), encoding="utf-8"))["results"][0]
    rows = [("{", None, None), ('  "title"', f'"{s["title"][:22]}..."', "s"),
            ('  "price"', str(s["price"]), "n"), ('  "currency"', f'"{s["currency"]}"', "s"),
            ('  "rating"', str(s["rating"]), "n"), ('  "reviews_count"', str(s["reviews_count"]), "n"),
            ('  "seller"', f'"{s["seller"]}"', "s"),
            ('  "out_of_stock"', str(s["out_of_stock"]).lower(), "n"), ("}", None, None)]
    fm = font(MONO, 13)
    yy = cy + 54
    for k, v, kind in rows:
        if v is None:
            d.text((cx + 18, yy), k, font=fm, fill=DIM)
        else:
            d.text((cx + 18, yy), k, font=fm, fill=(127, 178, 255))
            kw = d.textlength(k, font=fm)
            d.text((cx + 18 + kw, yy), ": ", font=fm, fill=DIM)
            d.text((cx + 18 + kw + d.textlength(": ", font=fm), yy), v, font=fm,
                   fill=(154, 230, 160) if kind == "s" else ACC2)
        yy += 24

    d.text((828, 468), "6 endpoints  ·  real JSON  ·  no headless browser", font=font(REG, 14), fill=DIM)
    img.save(os.path.join(OUT, "hero.png"))
    print("wrote assets/hero.png", img.size)


def evidence():
    """Side by side: what the free script returns vs the API."""
    W, H = 1280, 420
    img = vgrad(W, H, (15, 17, 21), (22, 16, 15))
    d = ImageDraw.Draw(img)
    d.text((64, 44), "Same page. Same day. Two different outcomes.", font=font(BOLD, 27), fill=INK)
    d.text((64, 84), "Measured 2026-07-14 from a clean residential IP. Reproduce both with the scripts in this repo.",
           font=font(REG, 15), fill=DIM)

    # left: blocked
    d.rounded_rectangle([64, 128, 624, 372], radius=13, fill=(20, 13, 13), outline=(96, 44, 44))
    d.text((88, 148), "free_scraper/walmart_free_scraper.py", font=font(MONO, 13), fill=(214, 128, 128))
    fm = font(MONO, 13)
    for i, ln in enumerate([
        "HTTP status ........ 200      (not 403, not 429)",
        "Response size ...... 15,190 bytes  (~1 MB expected)",
        '<title> ............ "Robot or human?"',
        "__NEXT_DATA__ ...... absent",
        "itemStacks ......... absent",
        "products ........... 0",
    ]):
        d.text((88, 186 + i * 24), ln, font=fm, fill=(178, 168, 162))
    d.text((88, 336), "BLOCKED on 4 of 4 attempts", font=font(BOLD, 16), fill=(230, 110, 110))

    # right: parsed
    d.rounded_rectangle([656, 128, 1216, 372], radius=13, fill=(12, 20, 14), outline=(46, 96, 54))
    d.text((680, 148), "walmart_scraper_api_codes/search.py", font=font(MONO, 13), fill=(130, 210, 140))
    s = json.load(open(os.path.join(DATA, "search.json"), encoding="utf-8"))
    for i, ln in enumerate([
        "HTTP status ........ 200",
        f"results ............ {len(s['results'])} products",
        f"first title ........ {s['results'][0]['title'][:26]}...",
        f"price .............. {s['results'][0]['price']} {s['results'][0]['currency']}",
        f"rating ............. {s['results'][0]['rating']}  ({s['results'][0]['reviews_count']} reviews)",
        "fields per product . 22",
    ]):
        d.text((680, 186 + i * 24), ln, font=fm, fill=(178, 168, 162))
    d.text((680, 336), "Parsed JSON, 22 fields per product", font=font(BOLD, 16), fill=(110, 210, 130))

    img.save(os.path.join(OUT, "free-vs-api.png"))
    print("wrote assets/free-vs-api.png", img.size)


if __name__ == "__main__":
    hero()
    evidence()
