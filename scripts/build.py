"""Render docs/index.html from src/index.template.html and write the files
search engines read: robots.txt, sitemap.xml and CNAME.

The page fills itself from docs/data/*.json in the browser. This script also
writes the latest figures straight into the HTML, so search engines and
link previews see real content without running any JavaScript.

Set "siteUrl" (e.g. "https://tirumalaplanner.in") in site.config.json.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = os.path.join(ROOT, "docs")
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
DOW = "Mon Tue Wed Thu Fri Sat Sun".split()


def load(p):
    with open(os.path.join(ROOT, p)) as f:
        return json.load(f)


def nice(iso: str, year=True) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {MON[d.month-1]}" + (f" {d.year}" if year else "")


def fint(v):
    return "—" if v is None else f"{v:,}"


def f2(v):
    return "—" if v is None else f"{v:.2f}"


def sev(h):
    if h is None:
        return None
    return 0 if h <= 6 else 1 if h <= 12 else 2 if h <= 18 else 3 if h <= 24 else 4


def main():
    try:  # tithi table for the page; needs the ephem package
        import panchang
        panchang.main()
    except ImportError:
        print("ephem not installed; keeping existing panchang.json")
    cfg = load("site.config.json")
    url = (cfg.get("siteUrl") or "").rstrip("/")
    name = cfg.get("siteName") or "Tirumala Darshan Planner"
    rows = load("docs/data/bulletins.json")["days"]
    plan = load("docs/data/plan.json")
    tpl = open(os.path.join(ROOT, "src", "index.template.html")).read()
    last = rows[-1] if rows else None
    today = dt.date.today().isoformat()

    pre = {}
    if last:
        wait = "Direct" if last.get("waitHours") == 0 else (last.get("waitText") or "—")
        where = (f"{last['compartments']} of 31 compartments in use" if last.get("compartments") is not None
                 else (last.get("queueNote") or "Queue position not given"))
        pre["queue"] = (f'<div class="big">{html.escape(wait)}</div>\n      <div class="where">'
                        f'{html.escape(where)} · morning of {nice(last["situationDate"])}</div>')
        pre["status"] = (f'<span class="chip fresh"><span class="dot"></span>Latest bulletin covers {nice(last["date"])}</span>'
                         f'<span class="chip">{len(rows):,} days of history</span>')
        trs = []
        for r in reversed(rows[-60:]):
            d = dt.date.fromisoformat(r["date"])
            q = f"{r['compartments']} compartments" if r.get("compartments") is not None else (r.get("queueNote") or "—")
            w = "Direct" if r.get("waitHours") == 0 else (r.get("waitText") or "—")
            trs.append(f"<tr><td>{nice(r['date'])}</td><td class=\"l\">{DOW[d.weekday()]}</td><td>{fint(r.get('pilgrims'))}</td>"
                       f"<td>{fint(r.get('tonsures'))}</td><td>{f2(r.get('hundiCr'))}</td><td>{f2(r.get('ladduLakh'))}</td>"
                       f"<td>{f2(r.get('annaLakh'))}</td><td>{fint(r.get('hospital'))}</td><td class=\"l\">{html.escape(q)}</td>"
                       f"<td>{html.escape(w)}</td></tr>")
        pre["rows"] = "".join(trs)
    try:
        pan = load("docs/data/panchang.json")
        i = (dt.date.fromisoformat(today) - dt.date.fromisoformat(pan["start"])).days
        m, t, a = pan["days"][i]
        names = "Pratipada Dvitiya Tritiya Chaturthi Panchami Shashthi Saptami Ashtami Navami Dashami Ekadashi Dvadashi Trayodashi Chaturdashi Purnima".split()
        n = "Amavasya" if t == 30 else names[(t - 1) % 15]
        pk = "Shukla paksha" if t <= 15 else "Krishna paksha"
        pre["tithi"] = f'{n}<small>{pk} · {"Adhika " if a else ""}{pan["masa"][m]} masam</small>'
    except (OSError, KeyError, IndexError, ValueError):
        pass
    occ = [o for o in plan.get("occasions", []) if (o.get("end") or o["start"]) >= today]
    if occ:
        pre["occ"] = "".join(
            f'<li class="o"><span class="dt"><b>{nice(o["start"], False)}</b></span><span class="nm"><strong>{html.escape(o["name"])}</strong>'
            f'<small>{html.escape(o.get("note", ""))}</small></span><span class="hist"></span></li>' for o in occ)

    for k, v in pre.items():
        tpl = re.sub(rf"<!--PRE:{k}-->.*?<!--/PRE-->", lambda m, v=v, k=k: f"<!--PRE:{k}-->{v}<!--/PRE-->", tpl, flags=re.S)

    jsonld = [
        {"@context": "https://schema.org", "@type": "WebSite", "name": name, "url": (url or "") + "/", "inLanguage": "en-IN"},
        {"@context": "https://schema.org", "@type": "WebApplication", "name": name, "url": (url or "") + "/",
         "applicationCategory": "TravelApplication", "operatingSystem": "Any",
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"},
         "description": "Crowd calendar, Sarva Darshan wait history and TTD ticket release dates for planning a visit to Sri Venkateswara Swamy Temple, Tirumala."},
        {"@context": "https://schema.org", "@type": "Dataset", "name": "Tirumala daily darshan bulletins",
         "description": "Daily pilgrims, tonsures, hundi collection, laddu sales, Annaprasadam and Sarva Darshan queue status at Tirumala, compiled from TTD's public daily bulletins on news.tirumala.org. May contain gaps or errors.",
         "url": (url or "") + "/", "isAccessibleForFree": True,
         "temporalCoverage": f"{rows[0]['date']}/{rows[-1]['date']}" if rows else None,
         "spatialCoverage": {"@type": "Place", "name": "Tirumala, Andhra Pradesh, India",
                             "geo": {"@type": "GeoCoordinates", "latitude": 13.6833, "longitude": 79.3474}},
         "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": (url or "") + "/data/bulletins.json"}],
         "dateModified": (last or {}).get("date")},
    ]
    verify = cfg.get("googleSiteVerification") or ""
    tpl = (tpl.replace("{{SITE_URL}}", url)
              .replace("{{SITE_NAME}}", html.escape(name))
              .replace("{{JSONLD}}", json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/"))
              .replace("{{GOOGLE_VERIFY}}", f'<meta name="google-site-verification" content="{html.escape(verify)}">' if verify else ""))
    if not url:  # no domain yet: drop absolute-URL tags rather than publish broken ones
        tpl = re.sub(r'\n<link rel="canonical" href="/">', "", tpl)
        tpl = re.sub(r'\n<meta (?:property|name)="(?:og:url|og:image|twitter:image)" content="/[^"]*">', "", tpl)
    with open(os.path.join(DOCS, "index.html"), "w") as f:
        f.write(tpl)

    with open(os.path.join(DOCS, "robots.txt"), "w") as f:
        f.write("User-agent: *\nAllow: /\n" + (f"Sitemap: {url}/sitemap.xml\n" if url else ""))
    if url:
        lastmod = (last or {}).get("date", today)
        with open(os.path.join(DOCS, "sitemap.xml"), "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                    f"  <url><loc>{url}/</loc><lastmod>{lastmod}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>\n</urlset>\n")
        host = re.sub(r"^https?://", "", url)
        with open(os.path.join(DOCS, "CNAME"), "w") as f:
            f.write(host + "\n")
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    print(f"built docs/index.html ({len(rows)} days, site {url or 'no domain set'})")


if __name__ == "__main__":
    main()
