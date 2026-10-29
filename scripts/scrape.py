"""Fetch TTD's daily darshan bulletins from news.tirumala.org and merge them
into docs/data/bulletins.json.

Usage:
    python scripts/scrape.py                 # newest bulletins; also backfills until 3 years are covered
    python scripts/scrape.py --min-years 5   # keep going back until 5 years are covered

It tries the site's WordPress JSON feed first and falls back to the HTML
category pages if the feed is unavailable. Only standard library modules
are used, so no installs are needed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from parse import parse_bulletin  # noqa: E402

BASE = "https://news.tirumala.org"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "docs", "data")
UA = "TirumalaDarshanPlanner/1.0 (+independent crowd planner; contact via GitHub)"


def get(url: str, retries: int = 3) -> str:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def from_feed(pages: int, known: set, target: str | None) -> list[dict]:
    """Read the feed newest-first. Stop after `pages` pages, or earlier once a
    page brings nothing new and history already reaches back to `target`."""
    cats = json.loads(get(f"{BASE}/wp-json/wp/v2/categories?slug=darshan"))
    if not cats:
        raise RuntimeError("darshan category not found in feed")
    cid = cats[0]["id"]
    out = []
    earliest = min(known) if known else None
    for page in range(1, pages + 1):
        url = f"{BASE}/wp-json/wp/v2/posts?categories={cid}&per_page=50&page={page}&_fields=title,content"
        try:
            posts = json.loads(get(url))
        except RuntimeError as e:
            if page > 1 and "400" in str(e):
                break  # past the last page
            raise
        if not posts:
            break
        fresh = 0
        for p in posts:
            text = p.get("title", {}).get("rendered", "") + "\n" + p.get("content", {}).get("rendered", "")
            rec = parse_bulletin(text)
            if rec:
                out.append(rec)
                if rec["date"] not in known:
                    fresh += 1
                if earliest is None or rec["date"] < earliest:
                    earliest = rec["date"]
        reached = target is None or (earliest is not None and earliest <= target)
        if fresh == 0 and reached:
            break
        time.sleep(1)
    return out


def from_html(pages: int) -> list[dict]:
    out = []
    for page in range(1, pages + 1):
        url = f"{BASE}/category/darshan/" + (f"page/{page}/" if page > 1 else "")
        html = get(url)
        links = sorted(set(re.findall(r'href="(https://news\.tirumala\.org/total-pilgrims-who-had-darshan-on-[^"#?]+)"', html)))
        if not links:
            break
        for link in links:
            rec = parse_bulletin(get(link))
            if rec:
                out.append(rec)
            time.sleep(0.5)
    return out


def merge(new: list[dict]) -> tuple[int, int]:
    path = os.path.join(DATA, "bulletins.json")
    data = json.load(open(path)) if os.path.exists(path) else {"days": []}
    by = {r["date"]: r for r in data["days"]}
    added = changed = 0
    for r in new:
        old = by.get(r["date"])
        if old is None:
            added += 1
        elif {k: v for k, v in old.items()} != r:
            # keep older non-null values the new parse could not read
            for k, v in old.items():
                if r.get(k) is None and v is not None:
                    r[k] = v
            if r != old:
                changed += 1
        by[r["date"]] = r
    data["days"] = sorted(by.values(), key=lambda r: r["date"])
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    status = {
        "lastChecked": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "latestBulletin": data["days"][-1]["date"] if data["days"] else None,
        "days": len(data["days"]),
    }
    with open(os.path.join(DATA, "status.json"), "w") as f:
        json.dump(status, f, indent=1)
    return added, changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=40, help="most feed pages to read in one run (50 bulletins each)")
    ap.add_argument("--min-years", type=float, default=3, help="keep reading older pages until history covers this many years")
    args = ap.parse_args()
    path = os.path.join(DATA, "bulletins.json")
    known = {r["date"] for r in json.load(open(path))["days"]} if os.path.exists(path) else set()
    target = (dt.date.today() - dt.timedelta(days=int(365.25 * args.min_years))).isoformat() if args.min_years else None
    try:
        recs = from_feed(args.pages, known, target)
        src = "feed"
    except Exception as e:  # feed blocked or changed: fall back to HTML
        print(f"feed unavailable ({e}); using HTML pages", file=sys.stderr)
        recs = from_html(1)
        src = "html"
    added, changed = merge(recs)
    days = json.load(open(path))["days"]
    print(f"{src}: parsed {len(recs)} bulletins, {added} new, {changed} updated; history {days[0]['date']} to {days[-1]['date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
