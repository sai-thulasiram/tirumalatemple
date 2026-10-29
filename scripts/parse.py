"""Parse TTD's daily darshan bulletin text into a structured record.

A bulletin on news.tirumala.org reads roughly like:

    Total pilgrims who had darshan on 22.10.2026: 65,113
    Tonsures: 26,391
    Hundi kanukalu: 3.82 CR
    Laddu sale... 3.71 Lac
    Annaprasadam.. 1.71 Lac
    Ashwini hospital..2,677
    Present Situation on 23-10-2026:
    Waiting Compartments..26
    Approx. Darshan Time for Sarvadarshanam (without SSD Tokens)...10 H.

Spelling and punctuation vary from day to day, so every pattern is loose.
"""
from __future__ import annotations

import datetime as dt
import html
import re

NUM = r"([\d,]+(?:\.\d+)?)"

# Values outside these ranges are treated as typos in the source and dropped.
SANE = {
    "pilgrims": (5_000, 200_000),
    "tonsures": (1_000, 120_000),
    "hundiCr": (0.3, 15.0),
    "ladduLakh": (0.5, 8.0),
    "annaLakh": (0.2, 5.0),
    "hospital": (100, 15_000),
}


def clean_text(raw: str) -> str:
    """Strip HTML, unescape entities and normalise punctuation and spacing."""
    t = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", raw, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = t.replace("…", "...").replace(" ", " ").replace("–", "-").replace("—", "-")
    t = re.sub(r"[ \t]+", " ", t)
    return t


def _num(s: str | None, kind=float):
    if s is None:
        return None
    try:
        return kind(float(s.replace(",", "")))
    except ValueError:
        return None


def _find(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.I | re.S)
    return m.group(1) if m else None


def parse_bulletin(raw: str) -> dict | None:
    """Return a record, or None if the text is not a daily darshan bulletin."""
    t = clean_text(raw)
    m = re.search(r"darshan\s+on\s+(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\s*:?\s*" + NUM, t, re.I)
    if not m:
        return None
    d, mo, y = (int(x) for x in m.group(1, 2, 3))
    try:
        day = dt.date(y, mo, d)
    except ValueError:
        return None

    rec = {
        "date": day.isoformat(),
        "pilgrims": _num(m.group(4), int),
        "tonsures": _num(_find(r"Tonsures?\s*[:.\s]+\s*" + NUM, t), int),
        "hundiCr": _num(_find(r"Hundi[^\d]{0,30}?" + NUM + r"\s*(?:CR|Cr|crore)", t)),
        "ladduLakh": _num(_find(r"Laddu[^\d]{0,25}?" + NUM + r"\s*(?:Lac|Lakh|L\b)", t)),
        "annaLakh": _num(_find(r"Anna\s*prasadam[^\d]{0,25}?" + NUM + r"\s*(?:Lac|Lakh|L\b)", t)),
        "hospital": _num(_find(r"A[s]?h?wini\s*hospital[^\d]{0,15}?" + NUM, t), int),
    }

    for key, (lo, hi) in SANE.items():
        v = rec.get(key)
        if v is not None and not (lo <= v <= hi):
            rec[key] = None

    # Queue situation the next morning
    rec["situationDate"] = (day + dt.timedelta(days=1)).isoformat()
    comp_raw = _find(r"Waiting\s*Compartments?[ .:]*([^\n]*?)\s*(?=Approx|Darsh?an\s*Time|\n|$)", t)
    direct = bool(re.search(r"direct\s*line", t, re.I))
    comp_raw = (comp_raw or "").strip(" .:-")
    cnum = int(comp_raw) if re.fullmatch(r"\d{1,2}", comp_raw) else None
    note = None
    if direct:
        note = "Direct line"
    elif cnum is None and comp_raw:
        note = re.sub(r"\s+", " ", comp_raw).rstrip(".")
        note = re.sub(r"(?i)^out\s*side", "Outside", note)
        note = re.sub(r"(?i)silat?horanam|sila thoranam|silatoranam", "Silathoranam", note)
        if not note.lower().startswith("outside") and len(note) < 60:
            note = "Outside line at " + note
        note = note[:80]
    rec["compartments"] = cnum
    rec["queueNote"] = note
    rec["queueFull"] = bool((note and note.lower().startswith("outside")) or (cnum is not None and cnum >= 31))

    wait_raw = _find(r"Sarva\s*darshan\w*[^.]*?(?:Tokens?\)?)?\s*[.:\s]*((?:\d{1,2}(?:\s*[-–to]+\s*\d{1,2})?)\s*(?:H|Hrs?|Hours?)?)", t)
    hours = [float(x) for x in re.findall(r"\d{1,2}", wait_raw or "")]
    if direct:
        rec["waitHours"], rec["waitText"] = 0.0, "0 h"
    elif hours:
        hours = [h for h in hours if h <= 48]
        rec["waitHours"] = max(hours) if hours else None
        rec["waitText"] = "-".join(str(int(h)) for h in hours) + " h" if hours else None
        if rec["waitHours"] == 0:
            rec["waitText"] = "0 h"
    else:
        rec["waitHours"], rec["waitText"] = None, None

    rec["source"] = "news.tirumala.org"
    return rec
