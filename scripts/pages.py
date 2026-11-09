"""Static, text-first answer pages for search engines and AI agents.

Most AI agents read a page's raw HTML and do not run JavaScript, so the
interactive planner on the home page is mostly invisible to them. This
module writes plain HTML pages that each answer one question, plus
llms.txt and data/today.json. Called from build.py.

Pages:
  /today/                       today's queue, tithi, next ticket release
  /festivals/<slug>/            one per upcoming occasion, vs last year
  /tickets/<month>-<year>/      ticket release dates for a darshan month
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re

MON = "January February March April May June July August September October November December".split()
MON3 = [m[:3] for m in MON]
DOWF = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
TN = "Pratipada Dvitiya Tritiya Chaturthi Panchami Shashthi Saptami Ashtami Navami Dashami Ekadashi Dvadashi Trayodashi Chaturdashi Purnima".split()
LVL = ["Light", "Moderate", "Busy", "Very busy", "Peak"]
TEMPLE = {"@type": "Place", "name": "Sri Venkateswara Swamy Temple, Tirumala",
          "address": {"@type": "PostalAddress", "addressLocality": "Tirumala", "addressRegion": "Andhra Pradesh",
                      "postalCode": "517504", "addressCountry": "IN"}}


def D(iso: str) -> dt.date:
    return dt.date.fromisoformat(iso)


def nice(iso: str, year=True) -> str:
    d = D(iso)
    return f"{d.day} {MON3[d.month-1]}" + (f" {d.year}" if year else "")


def long(iso: str) -> str:
    d = D(iso)
    return f"{DOWF[d.weekday()]}, {d.day} {MON[d.month-1]} {d.year}"


def span(a: str, b: str | None) -> str:
    return nice(a) if not b or a == b else f"{nice(a, D(a).year != D(b).year)} – {nice(b)}"


def slug(name: str, start: str) -> str:
    # Must match festSlug() in src/index.template.html
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", name.lower())) + "-" + start[:4]


def level(h):
    if h is None:
        return None
    return 0 if h <= 6 else 1 if h <= 12 else 2 if h <= 18 else 3 if h <= 24 else 4


def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def fint(v):
    return "—" if v is None else f"{round(v):,}"


def add(iso: str, n: int) -> str:
    return (D(iso) + dt.timedelta(days=n)).isoformat()


def tithi_name(pan, iso):
    try:
        m, t, a = pan["days"][(D(iso) - D(pan["start"])).days]
    except (IndexError, KeyError, TypeError):
        return None
    n = "Amavasya" if t == 30 else TN[(t - 1) % 15]
    return f'{n}, {"Shukla" if t <= 15 else "Krishna"} paksha, {"Adhika " if a else ""}{pan["masa"][m]} masam'


def compare(rows, start, end):
    """Pilgrims on [start,end] vs the 14 days either side; longest morning queue."""
    end = end or start
    by = {r["date"]: r for r in rows}
    bs = {r["situationDate"]: r for r in rows}
    inr, around, waits, full = [], [], [], 0
    d = start
    while d <= end:
        if by.get(d, {}).get("pilgrims"):
            inr.append(by[d]["pilgrims"])
        d = add(d, 1)
    for i in range(1, 15):
        for x in (add(start, -i), add(end, i)):
            if by.get(x, {}).get("pilgrims"):
                around.append(by[x]["pilgrims"])
    d = start
    while d <= add(end, 1):
        r = bs.get(d)
        if r and r.get("waitHours") is not None:
            waits.append(r["waitHours"])
            full += 1 if r.get("queueFull") else 0
        d = add(d, 1)
    a, b = avg(inr), avg(around)
    return {"days": len(inr), "pilgrims": a, "pct": (a - b) / b * 100 if a and b else None,
            "wmax": max(waits) if waits else None, "full": full, "mornings": len(waits)}


def quota_dates(plan, year, month):
    """Release dates for darshan in (year, month): about three months ahead."""
    rm, ry = month - 3, year
    while rm < 1:
        rm += 12
        ry -= 1
    out = []
    for q in plan.get("quotaPattern", []):
        try:
            out.append({**q, "date": dt.date(ry, rm, q["day"]).isoformat()})
        except ValueError:
            pass
    return out


# ---------------------------------------------------------------- page shell
CSS = """:root{--bg:#FBF6EC;--surface:#FFFDF8;--ink:#3A1F14;--muted:#7A5E4E;--line:#EADCC6;--accent:#8E1B1B;--gold:#A8730C;--gold-soft:#F6E7C1;--crit:#B3261E}
@media (prefers-color-scheme:dark){:root{--bg:#1C100C;--surface:#26170F;--ink:#F6EBDD;--muted:#C2A992;--line:#3D2A1F;--accent:#F0A58F;--gold:#E6B655;--gold-soft:#3D2C12;--crit:#F27A70;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 "Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:760px;margin:0 auto;padding:24px max(16px,env(safe-area-inset-left,0px)) 48px max(16px,env(safe-area-inset-right,0px))}
h1{font-family:"Marcellus",Georgia,serif;font-weight:400;color:var(--accent);font-size:clamp(28px,5vw,38px);line-height:1.15;margin:8px 0 6px;text-wrap:balance}
h2{font-family:"Marcellus",Georgia,serif;font-weight:400;font-size:22px;margin:28px 0 8px}
a{color:var(--accent)}p{margin:8px 0}.muted{color:var(--muted);font-size:14px}
.crumb{font-size:14px}.crumb a{text-decoration:none}
.answer{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--gold);border-radius:10px;padding:14px 16px;margin:14px 0}
.answer p:first-child{margin-top:0}.answer p:last-child{margin-bottom:0}
table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600;font-size:13px}
.tbl{overflow-x:auto}
ul{padding-left:20px}li{margin:4px 0}
.cta{display:inline-block;margin-top:10px;padding:9px 16px;border-radius:999px;background:var(--accent);color:var(--bg);text-decoration:none;font-weight:600}
.warn{border-left-color:var(--crit)}
footer{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);font-size:13px;color:var(--muted)}"""


def shell(url, site, analytics, path, title, desc, body, jsonld, updated):
    canon = f"{url}{path}"
    ld = json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{canon}">
<meta name="robots" content="index,follow,max-snippet:-1">
<meta property="og:type" content="article"><meta property="og:site_name" content="{html.escape(site)}">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{canon}"><meta property="og:image" content="{url}/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Sans+3:wght@400;600&display=swap">
{analytics}
<script type="application/ld+json">{ld}</script>
<style>{CSS}</style>
</head>
<body><main>
<p class="crumb"><a href="/">← Tirumala Darshan Planner</a></p>
{body}
<p><a class="cta" href="/#check">Check your own dates in the planner</a></p>
<footer>Updated {long(updated)}. Independent site, not run by TTD. Figures come from TTD's daily bulletins on news.tirumala.org and may sometimes be incomplete or wrong. Book only on <a href="https://ttdevasthanams.ap.gov.in">ttdevasthanams.ap.gov.in</a>; never pay a broker. Report brokers to TTD Vigilance: 9866898630.</footer>
</main></body></html>
"""


def crumbs(url, items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": url + p}
                                for i, (n, p) in enumerate(items)]}


# ---------------------------------------------------------------- generators
def generate(docs, url, site, analytics, rows, plan, pan, today):
    """Write all pages. Returns [(path, lastmod)] for the sitemap."""
    written = []
    last = rows[-1] if rows else None
    year_rows = [r for r in rows if r["date"] >= add(today, -365)]
    occ_all = [o for o in plan.get("occasions", [])]
    upcoming = [o for o in occ_all if (o.get("end") or o["start"]) >= today]

    def write(path, content):
        p = os.path.join(docs, path.strip("/"), "index.html")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(content)
        written.append((path, (last or {}).get("date", today)))

    # weekday pattern (morning of situationDate)
    by_dow = [[] for _ in range(7)]
    for r in year_rows:
        if r.get("waitHours") is not None:
            by_dow[D(r["situationDate"]).weekday()].append(r["waitHours"])
    dow_avg = [avg(x) for x in by_dow]

    # ticket months: the month whose quota opens next, plus three after
    months = []
    t = D(today)
    for k in range(0, 6):
        y, m = t.year + (t.month - 1 + k) // 12, (t.month - 1 + k) % 12 + 1
        qs = quota_dates(plan, y, m)
        if qs and max(q["date"] for q in qs) >= add(today, -31):
            months.append((y, m, qs))
    months = months[:4]

    def sed(qs):
        return next((q for q in qs if "300" in q["name"]), None)

    # ---------------- /tickets/<month>-<year>/
    ticket_links = []
    for y, m, qs in months:
        path = f"/tickets/{MON[m-1].lower()}-{y}/"
        s = sed(qs)
        gone = s and s["date"] < today
        rows_html = "".join(f"<tr><td>{nice(q['date'])}</td><td>{html.escape(q['time'])}</td><td>{html.escape(q['name'])}</td></tr>" for q in sorted(qs, key=lambda q: (q['date'], q['time'][-2:], q['time'])))
        fests = [o for o in occ_all if o["start"][:7] == f"{y}-{m:02d}" and "holidays" not in o["name"].lower()]
        title = f"TTD ₹300 darshan ticket release date for {MON[m-1]} {y}"
        lead = (f"₹300 Special Entry Darshan tickets for {MON[m-1]} {y} were released on {long(s['date'])} at {s['time']} IST on ttdevasthanams.ap.gov.in and are usually sold out the same day."
                if gone else
                f"₹300 Special Entry Darshan tickets for {MON[m-1]} {y} are expected to be released on {long(s['date'])} at {s['time']} IST on ttdevasthanams.ap.gov.in.") if s else ""
        body = f"""<h1>{html.escape(title)}</h1>
<div class="answer"><p><b>{html.escape(lead)}</b></p>
<p>Rooms in Tirumala and Tirupati for {MON[m-1]} open the same day at 3:00 PM. TTD releases each month's quota about three months ahead; it confirms exact dates a few days before, so check TTD's notice.</p></div>
<h2>All quota releases for {MON[m-1]} {y} darshan</h2>
<div class="tbl"><table><tr><th>Date</th><th>Time (IST)</th><th>What opens</th></tr>{rows_html}</table></div>
{"<h2>Festivals in " + MON[m-1] + "</h2><ul>" + "".join(f'<li><a href="/festivals/{slug(o["name"], o["start"])}/">{html.escape(o["name"])}</a>: {span(o["start"], o.get("end"))}</li>' for o in fests) + "</ul>" if fests else ""}
<h2>If tickets are already sold out</h2>
<ul><li><b>SSD time-slot token (free):</b> collect it in Tirupati the day before at Srinivasam (near the central bus stand), Vishnu Nivasam (opposite the railway station) or the Bhudevi Complex (Alipiri), in person with original Aadhaar.</li>
<li><b>Walk up</b> by Srivari Mettu or Alipiri; walkers get a Divya Darshan token on the way.</li>
<li><b>SRIVANI</b> (₹10,000 donation + ₹500 ticket per person): same-day tickets released online around 9 AM; a small offline quota at Tirupati airport.</li>
<li><b>Free Sarva Darshan:</b> no ticket needed; see <a href="/today/">today's queue</a>.</li></ul>"""
        desc = lead[:155]
        ld = [crumbs(url, [("Planner", "/"), (f"Tickets {MON[m-1]} {y}", path)]),
              {"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": url + path, "dateModified": today, "description": desc}]
        write(path, shell(url, site, analytics, path, title, desc, body, ld, today))
        ticket_links.append((f"Tickets for {MON[m-1]} {y}", path))

    # ---------------- /festivals/<slug>/
    fest_links = []
    for o in upcoming:
        if "holidays" in o["name"].lower():
            continue
        start, end = o["start"], o.get("end") or o["start"]
        path = f"/festivals/{slug(o['name'], start)}/"
        past = (o.get("past") or [None])[0]
        c = compare(rows, past["start"], past.get("end")) if past else None
        lv = level(c["wmax"]) if c else None
        dy, dm = D(start).year, D(start).month
        s = sed(quota_dates(plan, dy, dm))
        tt = tithi_name(pan, start)
        status = "TTD has not confirmed this date yet; it is the expected date from the panchang." if o.get("status") == "expected" else ""
        if c and c["days"]:
            pct = c["pct"]
            busier = ("about the same as usual" if pct is None or abs(pct) < 4 else
                      f"{abs(round(pct))}% {'busier' if pct > 0 else 'quieter'} than the two weeks around it")
            when = span(past["start"], past.get("end"))
            outside = f", and the line ran outside the waiting halls on {c['full']} of {c['mornings']} mornings" if c["full"] else ""
            hist = f"Last time ({when}), about {fint(c['pilgrims'])} devotees a day had darshan, {busier}."
            if c["wmax"] is not None:
                hist = hist[:-1] + f". The free queue was up to {c['wmax']:g} hours{outside}."
        else:
            hist = "There is no bulletin data yet for the last occurrence."
        crowd = f"Expected crowd: <b>{LVL[lv]}</b>." if lv is not None else ""
        tk = ""
        if s:
            tk = (f"₹300 tickets for {MON[dm-1]} were released on {nice(s['date'])} and are usually sold out; use an SSD token, the footpath, SRIVANI or the free queue."
                  if s["date"] < today else
                  f"₹300 tickets for {MON[dm-1]} open on {long(s['date'])} at {s['time']} IST.")
        tpath = f"/tickets/{MON[dm-1].lower()}-{dy}/"
        tlink = f' <a href="{tpath}">All ticket dates for {MON[dm-1]}</a>.' if any(p == tpath for _, p in ticket_links) else ""
        title = f"{o['name']} {D(start).year} at Tirumala: dates, crowd and tickets"
        body = f"""<h1>{html.escape(o['name'])} {D(start).year} at Tirumala</h1>
<div class="answer"><p><b>Date: {span(start, end)}{f" ({DOWF[D(start).weekday()]})" if start == end else ""}.</b> {html.escape(status)}</p>
<p>{crowd} {html.escape(hist)}</p>
<p>{html.escape(tk)}{tlink}</p></div>
<h2>About {html.escape(o['name'])}</h2>
<p>{html.escape(o.get('note', ''))}</p>
{f"<p class='muted'>Tithi on {nice(start)}: {html.escape(tt)} (at sunrise in Tirumala).</p>" if tt else ""}
<h2>Planning tips</h2>
<ul><li>Stay in Tirupati and go up for the day if rooms on the hill are full; free lockers are near the queue complexes.</li>
<li>Expect queues to start building the evening before and to stay long for a day after.</li>
<li>Check <a href="/today/">today's queue</a> on the morning you travel.</li></ul>"""
        desc = f"{o['name']} {D(start).year} at Tirumala on {span(start, end)}. {hist}"[:155]
        ev = {"@context": "https://schema.org", "@type": "Event", "name": f"{o['name']} at Tirumala",
              "startDate": start, "endDate": end, "eventStatus": "https://schema.org/EventScheduled",
              "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "location": TEMPLE,
              "description": o.get("note", ""), "organizer": {"@type": "Organization", "name": "Tirumala Tirupati Devasthanams", "url": "https://ttdevasthanams.ap.gov.in"},
              "isAccessibleForFree": True, "url": url + path}
        ld = [crumbs(url, [("Planner", "/"), (o["name"], path)]), ev]
        write(path, shell(url, site, analytics, path, title, desc, body, ld, today))
        fest_links.append((f"{o['name']} ({span(start, end)})", path))

    # ---------------- /today/
    if last:
        q = "no waiting, direct entry" if last.get("waitHours") == 0 else f"about {last.get('waitText') or '?'}"
        where = (f"{last['compartments']} of 31 waiting compartments in use" if last.get("compartments") is not None
                 else (last.get("queueNote") or "position not reported"))
        lag = (D(today) - D(last["situationDate"])).days
        nxt = None
        for y, m, qs in months:
            s = sed(qs)
            if s and s["date"] >= today:
                nxt = (y, m, s)
                break
        soon = [o for o in upcoming if o["start"] <= add(today, 45) and "holidays" not in o["name"].lower()]
        best = min(range(7), key=lambda i: dow_avg[i] if dow_avg[i] is not None else 99)
        worst = max(range(7), key=lambda i: dow_avg[i] if dow_avg[i] is not None else -1)
        tt = tithi_name(pan, today)
        title = f"Tirumala darshan crowd today, {nice(today)}: free queue waiting time"
        body = f"""<h1>Tirumala crowd today</h1>
<p class="muted">{long(today)}</p>
<div class="answer{' warn' if lag >= 2 else ''}"><p><b>Free Sarva Darshan queue on the morning of {nice(last['situationDate'])}: {html.escape(q)}</b> ({html.escape(where)}), per TTD's latest bulletin.{f' TTD has not published a newer report for {lag} days.' if lag >= 2 else ''}</p>
<p>On {nice(last['date'])}, {fint(last.get('pilgrims'))} devotees had darshan and {fint(last.get('tonsures'))} offered tonsure; the Srivari hundi collected ₹{last.get('hundiCr') or '—'} crore.</p>
<p>With a ₹300 ticket or an SSD time-slot token the wait is much shorter than the free queue.</p></div>
{f"<p>Today's tithi: <b>{html.escape(tt)}</b> (at sunrise in Tirumala).</p>" if tt else ""}
<h2>Next ticket release</h2>
<p>{f"₹300 Special Entry Darshan tickets for {MON[nxt[1]-1]} {nxt[0]} open on <b>{long(nxt[2]['date'])} at {nxt[2]['time']} IST</b> on ttdevasthanams.ap.gov.in. <a href='/tickets/{MON[nxt[1]-1].lower()}-{nxt[0]}/'>All quota dates</a>." if nxt else "See the planner for ticket dates."}</p>
<h2>Festivals in the next six weeks</h2>
{"<ul>" + "".join(f'<li><a href="/festivals/{slug(o["name"], o["start"])}/">{html.escape(o["name"])}</a>: {span(o["start"], o.get("end"))}</li>' for o in soon) + "</ul>" if soon else "<p>No major festivals in the next six weeks.</p>"}
<h2>Quieter days of the week</h2>
<p>Over the last 12 months, {DOWF[best]} mornings had the shortest free queue (about {dow_avg[best]:.0f} hours on average) and {DOWF[worst]} the longest (about {dow_avg[worst]:.0f} hours).</p>"""
        desc = f"Tirumala free darshan queue on {nice(last['situationDate'])}: {q}. Daily figures from TTD, next ticket release dates and upcoming festivals."[:155]
        ld = [crumbs(url, [("Planner", "/"), ("Today", "/today/")]),
              {"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": url + "/today/", "dateModified": today, "description": desc}]
        write("/today/", shell(url, site, analytics, "/today/", title, desc, body, ld, today))

        # data/today.json: small, stable, for agents
        today_json = {
            "site": url + "/", "generated": today, "source": "TTD daily bulletins, news.tirumala.org",
            "latestBulletin": {k: last.get(k) for k in ("date", "pilgrims", "tonsures", "hundiCr", "situationDate", "compartments", "queueNote", "waitText", "waitHours")},
            "freeQueueNote": "waitHours is for the free Sarva Darshan queue only; ₹300 and SSD ticket holders wait far less.",
            "tithiToday": tt,
            "nextRelease300": {"forMonth": f"{nxt[0]}-{nxt[1]:02d}", "date": nxt[2]["date"], "timeIST": nxt[2]["time"]} if nxt else None,
            "upcomingFestivals": [{"name": o["name"], "start": o["start"], "end": o.get("end") or o["start"], "status": o.get("status"),
                                   "page": f"{url}/festivals/{slug(o['name'], o['start'])}/"} for o in upcoming if "holidays" not in o["name"].lower()][:8],
            "weekdayAvgWaitHours": {DOWF[i]: (round(dow_avg[i], 1) if dow_avg[i] is not None else None) for i in range(7)},
        }
        with open(os.path.join(docs, "data", "today.json"), "w") as f:
            json.dump(today_json, f, ensure_ascii=False, indent=1)

    # ---------------- llms.txt
    lines = [f"# {site}", "",
             "> Independent planner for darshan at Sri Venkateswara Swamy Temple, Tirumala (Andhra Pradesh, India). "
             "Built from TTD's public daily bulletins: free Sarva Darshan queue waiting time, pilgrims, tonsures and hundi, "
             "plus festival dates compared with last year and TTD online ticket (quota) release dates. Not affiliated with TTD.", "",
             "Key facts:",
             "- Waiting times are for the free Sarva Darshan queue only. ₹300 Special Entry Darshan and SSD token holders wait far less.",
             "- TTD releases each month's ₹300 tickets online about three months ahead, on the 24th at 10:00 AM IST (rooms 3:00 PM). Book only on ttdevasthanams.ap.gov.in.",
             "- No broker can sell darshan or rooms. Report brokers to TTD Vigilance: 9866898630. TTD call centre: 155257.", "",
             "## Pages",
             f"- [Crowd today]({url}/today/): latest queue, today's tithi, next ticket release",
             *[f"- [{n}]({url}{p})" for n, p in ticket_links],
             *[f"- [{n}]({url}{p})" for n, p in fest_links],
             f"- [Interactive planner]({url}/): date checker, darshan types, local tips", "",
             "## Data (JSON, updated twice daily)",
             f"- [today.json]({url}/data/today.json): latest bulletin, tithi, next release, upcoming festivals, weekday averages",
             f"- [bulletins.json]({url}/data/bulletins.json): every daily bulletin for the last two years",
             f"- [plan.json]({url}/data/plan.json): festival dates and quota release pattern", ""]
    with open(os.path.join(docs, "llms.txt"), "w") as f:
        f.write("\n".join(lines))

    return written, ticket_links, fest_links
