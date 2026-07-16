"""Render developer-journey screenshots from REAL captured session output.

Follows the pattern oxylabs/amazon-scraper uses: a terminal shot of the command
actually running, then a table shot of the data it retrieved.

The text rendered here is the verbatim stdout of a real run (captured to
%TEMP%/qa/*.out) and the real committed JSON. The shell prompt is deliberately
generic (~/walmart-scraper $) so no local username or path is exposed.
"""
import json
import os
import re

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..")
DATA = os.path.join(OUT, "..", "walmart_scraper_api_data")
QA = os.path.expandvars(r"%TEMP%\qa")
F = "C:/Windows/Fonts/"

MONO = ImageFont.truetype(F + "consola.ttf", 15)
MONOB = ImageFont.truetype(F + "consolab.ttf", 15)
UI = ImageFont.truetype(F + "segoeui.ttf", 14)
UIB = ImageFont.truetype(F + "seguisb.ttf", 14)

BG, FG, DIM = (13, 15, 19), (208, 205, 200), (110, 106, 100)
GREEN, BLUE, AMBER, RED, CYAN = (126, 209, 138), (127, 178, 255), (255, 196, 138), (232, 118, 118), (120, 205, 210)

SECRET = re.compile(r"asa_live_[A-Za-z0-9_\-]+")


def sanitize(s: str) -> str:
    """Never leak a key, a local path, or a username into an image."""
    s = SECRET.sub("$CHOCODATA_API_KEY", s)
    s = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+", "~", s)
    s = re.sub(r"/c/Users/[^/\s]+", "~", s)
    s = s.replace(os.environ.get("USERNAME", "\0"), "dev")
    return s


def terminal(lines, path, width=1180, title="bash"):
    pad, lh = 18, 23
    h = 46 + pad * 2 + lh * len(lines)
    img = Image.new("RGB", (width, h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 38], fill=(24, 26, 31))
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse([16 + i * 20, 14, 26 + i * 20, 24], fill=c)
    d.text((width // 2 - 18, 11), title, font=UI, fill=DIM)
    y = 38 + pad
    for text, color, bold in lines:
        d.text((pad, y), text, font=MONOB if bold else MONO, fill=color)
        y += lh
    img.save(os.path.join(OUT, path))
    print("wrote assets/" + path, img.size)


def read_out(name):
    p = os.path.join(QA, name)
    return sanitize(open(p, encoding="utf-8", errors="replace").read()) if os.path.exists(p) else ""


def shot_run():
    """The API call actually running: what a developer sees."""
    out = read_out("search.out").strip().splitlines()
    body = [l for l in out if l.strip()]
    head, tail = body[:14], body[-1]
    lines = [("$ export CHOCODATA_API_KEY=\"your_key\"", GREEN, True),
             ("$ python walmart_scraper_api_codes/search.py", GREEN, True), ("", FG, False)]
    for l in head:
        c = FG
        if re.search(r'"\w+":', l):
            c = BLUE
        if re.search(r": \d", l):
            c = AMBER
        lines.append((l[:110], c, False))
    lines += [("  ...", DIM, False), ("", FG, False), (tail[:110], CYAN, True)]
    terminal(lines, "run-search.png", title="walmart-scraper")


def shot_blocked():
    """The free scraper hitting the wall, verbatim."""
    out = read_out("free.out").strip().splitlines()
    lines = [("$ python free_scraper/walmart_free_scraper.py \"laptop\"", GREEN, True), ("", FG, False)]
    for l in out[:6]:
        lines.append((l[:105], RED if "BLOCKED" in l else FG, "BLOCKED" in l))
    terminal(lines, "run-blocked.png", title="walmart-scraper")


def shot_table():
    """Retrieved data as a table, the way oxylabs shows it."""
    s = json.load(open(os.path.join(DATA, "search.json"), encoding="utf-8"))["results"][:8]
    cols = [("#", 34), ("title", 330), ("id", 108), ("price", 66), ("rating", 60), ("reviews", 70), ("seller", 128)]
    W = sum(c[1] for c in cols) + 40
    rh, hh = 30, 34
    H = 52 + hh + rh * len(s)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 14), "walmart_search_results", font=UIB, fill=(30, 30, 30))
    x0, y0 = 20, 46
    d.rectangle([x0, y0, W - 20, y0 + hh], fill=(238, 238, 238))
    x = x0
    for name, w in cols:
        d.text((x + 9, y0 + 9), name, font=UIB, fill=(20, 20, 20))
        x += w
    y = y0 + hh
    for i, r in enumerate(s):
        if i % 2:
            d.rectangle([x0, y, W - 20, y + rh], fill=(250, 250, 250))
        vals = [str(i), r["title"][:44] + ("..." if len(r["title"]) > 44 else ""), r["id"],
                f'{r["price"]}' if r["price"] is not None else "-",
                str(r["rating"] or "-"), str(r["reviews_count"] or "-"), (r["seller"] or "-")[:15]]
        x = x0
        for (name, w), v in zip(cols, vals):
            d.text((x + 9, y + 7), v, font=MONO if name in ("id", "price", "rating", "reviews") else UI,
                   fill=(60, 60, 60) if name != "#" else (150, 150, 150))
            x += w
        d.line([(x0, y), (W - 20, y)], fill=(226, 226, 226))
        y += rh
    d.line([(x0, y), (W - 20, y)], fill=(226, 226, 226))
    for i in range(len(cols) + 1):
        xx = x0 + sum(c[1] for c in cols[:i])
        d.line([(xx, y0), (xx, y)], fill=(226, 226, 226))
    img.save(os.path.join(OUT, "retrieved-data.png"))
    print("wrote assets/retrieved-data.png", img.size)


def shot_generic(src, out, cmd, tail_color=CYAN, keep=13):
    """Terminal shot of any script's real captured stdout."""
    body = [l for l in read_out(src).strip().splitlines() if l.strip()]
    lines = [(f"$ python {cmd}", GREEN, True), ("", FG, False)]
    for l in body[:keep]:
        c = FG
        if re.search(r'"\w+":', l):
            c = BLUE
        if re.search(r':\s+\d', l):
            c = AMBER
        lines.append((l[:110], c, False))
    if len(body) > keep + 1:
        lines.append(("  ...", DIM, False))
    lines += [("", FG, False), (body[-1][:110], tail_color, True)]
    terminal(lines, out, title="walmart-scraper")


def shot_error():
    """The error UX: what a bad key actually gives you. Trust-building."""
    out = read_out("badkey.out").strip().splitlines()
    lines = [("$ export CHOCODATA_API_KEY=\"wrong_key\"", GREEN, True),
             ("$ python walmart_scraper_api_codes/search.py", GREEN, True), ("", FG, False)]
    for l in out[:4]:
        lines.append((l[:105], RED, True))
    lines += [("", FG, False),
              ("# no traceback, no silent empty list: every documented error", DIM, False),
              ("# maps to a message that tells you what to do next.", DIM, False)]
    terminal(lines, "run-error.png", title="walmart-scraper")


if __name__ == "__main__":
    shot_run()
    shot_blocked()
    shot_table()
    shot_generic("product.out", "run-product.png", "walmart_scraper_api_codes/product.py")
    shot_generic("reviews.out", "run-reviews.png", "walmart_scraper_api_codes/reviews.py")
    shot_error()
