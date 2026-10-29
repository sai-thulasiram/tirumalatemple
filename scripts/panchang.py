"""Compute the tithi and lunar month for every day, as observed at sunrise
in Tirumala, and write docs/data/panchang.json.

Tithi: the Moon's longitude minus the Sun's, in 12-degree steps (1-15 Shukla,
16-30 Krishna/Bahula; 30 = Amavasya). Taken at the moment of sunrise at
Tirumala, as panchangams do (udaya tithi).

Month: amanta (new moon to new moon), as in the Telugu calendar. A month is
named after the sidereal sign the Sun occupies at the new moon that starts
it (Sun in Meena -> Chaitra). When the Sun stays in the same sign through a
whole lunar month, that month is Adhika (extra) and carries the next name.
Sidereal positions use the Lahiri ayanamsa.

Accuracy: within a few minutes of printed panchangams. A day whose tithi
changes within minutes of sunrise can occasionally differ by one tithi.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os

import ephem

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "data", "panchang.json")
IST = dt.timedelta(hours=5, minutes=30)

MASA = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
        "Ashwayuja", "Kartika", "Margashira", "Pushya", "Magha", "Phalguna"]


def lahiri(d: ephem.Date) -> float:
    years = (ephem.Date(d) - ephem.Date("2000/1/1 12:00")) / 365.25
    return 23.853 + 0.0139689 * years  # degrees


def lon(body, d) -> float:
    body.compute(d, epoch=d)
    return math.degrees(float(ephem.Ecliptic(body, epoch=d).lon)) % 360


def tithi_at(d) -> int:
    diff = (lon(ephem.Moon(), d) - lon(ephem.Sun(), d)) % 360
    return int(diff // 12) + 1


def sun_sign(d) -> int:
    return int(((lon(ephem.Sun(), d) - lahiri(d)) % 360) // 30)  # 0 = Mesha


_nm_cache: dict = {}


def masa_at(d):
    prev_nm = ephem.previous_new_moon(d)
    key = round(float(prev_nm), 3)
    if key not in _nm_cache:
        next_nm = ephem.next_new_moon(prev_nm + 1)
        s1, s2 = sun_sign(prev_nm), sun_sign(next_nm)
        _nm_cache[key] = ((s1 + 1) % 12, s1 == s2)
    return _nm_cache[key]


def sunrise(d: dt.date) -> ephem.Date:
    obs = ephem.Observer()
    obs.lat, obs.lon, obs.elevation = "13.6833", "79.3474", 900
    obs.pressure = 0
    obs.horizon = "-0:34"
    obs.date = ephem.Date(dt.datetime(d.year, d.month, d.day, 0, 0) - IST)  # local midnight
    return obs.next_rising(ephem.Sun())


def compute(start: dt.date, end: dt.date) -> dict:
    days = []
    d = start
    while d <= end:
        t = sunrise(d)
        m, adhika = masa_at(t)
        days.append([m, tithi_at(t), 1 if adhika else 0])
        d += dt.timedelta(days=1)
    return {"start": start.isoformat(), "masa": MASA,
            "note": "Each entry: [month index into masa, tithi 1-30 (1-15 Shukla, 16-30 Krishna; 15 Purnima, 30 Amavasya), adhika flag]. At sunrise in Tirumala.",
            "days": days}


def main():
    today = dt.date.today()
    start = dt.date(today.year - 10, 1, 1)
    end = today + dt.timedelta(days=550)
    data = compute(start, end)
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"panchang: {len(data['days'])} days from {start} to {end}")


if __name__ == "__main__":
    main()
