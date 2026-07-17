"""
Free Walmart scraper - no API, no key, no cost.

Walmart server-renders its search results into a __NEXT_DATA__ JSON blob, so when a
request gets through you can pull structured products out without a headless browser.

    pip install requests
    python free_scraper/walmart_free_scraper.py "laptop"

Fetches the search page with plain requests and parses what comes back. Run against
walmart.com on 2026-07-14 it was blocked on 4 of 4 attempts from a clean residential IP:
HTTP 200, 15,190 bytes, <title>Robot or human?</title>, no __NEXT_DATA__ at all. See
"Avoid getting blocked when scraping Walmart" in the README.

It parses first and only reports a block when __NEXT_DATA__ is genuinely absent, so it
does not false-positive, and when it is blocked it reports why instead of silently
returning an empty list.
"""
import json
import re
import sys

import requests

SEARCH = "https://www.walmart.com/search"

# A plain requests UA is blocked instantly, and a real one only helps sometimes:
# Walmart fingerprints the connection itself, not just the header.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Substring-matching "captcha" against the whole body false-positives: Walmart ships
# anti-bot JS on good pages too. Only treat it as a block if __NEXT_DATA__ is absent,
# and only match these precise markers near the top of the document.
BLOCK_MARKERS = ("Robot or human?", "px-captcha", "Access Denied", "/_px/", "perimeterx")


def parse_next_data(html: str) -> dict | None:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def extract_products(next_data: dict) -> list[dict]:
    """Walk to the itemStacks that hold the search results."""
    out = []
    try:
        stacks = (
            next_data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"]
        )
    except (KeyError, TypeError):
        return out

    for stack in stacks:
        for it in stack.get("items", []):
            if not it.get("usItemId"):
                continue
            price = (it.get("priceInfo") or {}).get("currentPrice") or {}
            out.append(
                {
                    "id": it.get("usItemId"),
                    "title": it.get("name"),
                    "price": price.get("price"),
                    "currency": price.get("currencyUnit"),
                    "rating": (it.get("averageRating")),
                    "reviews_count": it.get("numberOfReviews"),
                    "url": "https://www.walmart.com" + (it.get("canonicalUrl") or ""),
                    "seller": it.get("sellerName"),
                }
            )
    return out


def scrape(query: str) -> list[dict]:
    r = requests.get(SEARCH, params={"q": query}, headers=HEADERS, timeout=30)

    if r.status_code != 200:
        raise SystemExit(
            f"BLOCKED: HTTP {r.status_code}. Walmart refused the request.\n"
            f"This is the normal outcome from a datacenter/cloud IP. See the README:\n"
            f"  https://github.com/ChocoData-com/walmart-scraper#avoid-getting-blocked-when-scraping-walmart"
        )

    # Try to parse FIRST. If the blob is there and yields items, it is not a block,
    # no matter what anti-bot strings appear elsewhere in the minified JS.
    nd = parse_next_data(r.text)
    if nd:
        products = extract_products(nd)
        if products:
            return products
        raise SystemExit(
            "Parsed __NEXT_DATA__ but found no itemStacks. Walmart renamed the JSON path\n"
            "(this happens a few times a year), or this query genuinely has no results.\n"
            "Update extract_products()."
        )

    # No blob. NOW decide whether that is a bot-check or a markup change. Scope the
    # marker check to the <title> plus the first 4KB so page JS cannot false-positive.
    head = r.text[:4096].lower()
    title = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.S | re.I)
    hay = head + (title.group(1).lower() if title else "")
    if any(m.lower() in hay for m in BLOCK_MARKERS):
        raise SystemExit(
            "BLOCKED: got a bot-check interstitial instead of results (HTTP 200).\n"
            "A 200 does not mean success. Check for the challenge page before parsing.\n"
            "  https://github.com/ChocoData-com/walmart-scraper#avoid-getting-blocked-when-scraping-walmart"
        )

    raise SystemExit(
        "No __NEXT_DATA__ blob and no bot-check marker. Walmart changed the shell, or you\n"
        f"got a JS-only variant (got {len(r.text)} bytes, title: "
        f"{title.group(1).strip()[:60] if title else 'n/a'}).\n"
        "This is the maintenance tax the README quantifies."
    )


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "laptop"
    items = scrape(q)
    print(json.dumps(items[:3], indent=2))
    print(f"\n{len(items)} products for '{q}' (showing 3)")
