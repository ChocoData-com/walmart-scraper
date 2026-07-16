"""
Walmart price monitor - a real, runnable use case on the Chocodata Walmart Scraper API.

Polls a Walmart search, stores every observation in a local SQLite file, and prints
any price change since the previous run. This is the single most common reason people
scrape Walmart (repricing / competitor monitoring), so it is here end to end rather
than as a snippet.

    pip install requests
    export CHOCODATA_API_KEY="your_key"     # free key (1,000 requests, one-time): https://chocodata.com
    python walmart_scraper_api_codes/price_monitor.py "gaming laptop"
    # ... run it again later to see the diffs

Cost: 1 request (5 credits) per run per query.
Docs: https://chocodata.com/docs
"""
import os
import sqlite3
import sys
import time

import requests

API = "https://api.chocodata.com/api/v1/walmart/search"
KEY = os.environ.get("CHOCODATA_API_KEY")
DB = "walmart_prices.db"

if not KEY:
    sys.exit("Set CHOCODATA_API_KEY first. Free key: https://chocodata.com")


def _check(r) -> None:
    """Map the API's documented errors onto actionable messages instead of a traceback."""
    if r.status_code == 401:
        sys.exit("401 INVALID_API_KEY: key missing or not recognised. Get one: https://chocodata.com")
    if r.status_code == 402:
        sys.exit("402 INSUFFICIENT_CREDITS: balance exhausted. Top up or upgrade: https://chocodata.com/pricing")
    if r.status_code == 429:
        sys.exit("429 RATE_LIMITED: over your plan's concurrency. Back off and retry.")
    if r.status_code == 404:
        sys.exit(f"404 item_not_found: {r.json().get('message', 'id does not exist')} (not retryable, not charged)")
    if r.status_code == 502:
        sys.exit("502 target_unreachable: Walmart refused every attempt for this request. Retryable, and you were not charged.")
    r.raise_for_status()


def fetch(query: str) -> list[dict]:
    """One API call -> the current ranked results for this query."""
    r = requests.get(API, params={"api_key": KEY, "query": query}, timeout=90)
    _check(r)
    return r.json().get("results", [])


def setup(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS observations (
               id TEXT, query TEXT, title TEXT, price REAL, currency TEXT,
               seller TEXT, ts INTEGER,
               PRIMARY KEY (id, ts)
           )"""
    )


def previous_price(conn: sqlite3.Connection, item_id: str) -> float | None:
    row = conn.execute(
        "SELECT price FROM observations WHERE id = ? ORDER BY ts DESC LIMIT 1", (item_id,)
    ).fetchone()
    return row[0] if row else None


def main(query: str) -> None:
    conn = sqlite3.connect(DB)
    setup(conn)
    now = int(time.time())
    results = fetch(query)

    changes = 0
    for item in results:
        item_id, price = item.get("id"), item.get("price")
        # Walmart lists some rows without a scalar price (variant/multi-option cards).
        if not item_id or not isinstance(price, (int, float)):
            continue

        before = previous_price(conn, item_id)
        if before is not None and before != price:
            delta = price - before
            arrow = "UP  " if delta > 0 else "DOWN"
            pct = (delta / before) * 100 if before else 0
            print(f"{arrow} {item['title'][:56]:56} {before:>8.2f} -> {price:>8.2f} ({pct:+.1f}%)")
            changes += 1

        conn.execute(
            "INSERT OR REPLACE INTO observations VALUES (?,?,?,?,?,?,?)",
            (item_id, query, item.get("title"), price, item.get("currency"),
             item.get("seller"), now),
        )

    conn.commit()
    tracked = conn.execute("SELECT COUNT(DISTINCT id) FROM observations").fetchone()[0]
    conn.close()

    print(f"\n{len(results)} results this run | {changes} price change(s) | {tracked} products tracked in {DB}")
    if changes == 0:
        print("No changes yet. Run it again in an hour, or schedule it (cron / GitHub Actions).")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gaming laptop")
