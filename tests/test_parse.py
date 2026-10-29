"""Run with: python -m pytest tests  (or: python tests/test_parse.py)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from parse import parse_bulletin  # noqa: E402

CASES = [
    (
        """<p>Total pilgrims who had darshan on 22.10.2026: 65,113</p><p>Tonsures: 26,391</p>
        <p>Hundi kanukalu: 3.82 CR</p><p>Laddu sale&#8230; 3.71 Lac</p><p>Annaprasadam.. 1.71 Lac</p>
        <p>Ashwini hospital..2,677</p><p>Present Situation on 23-10-2026:</p><p>Waiting Compartments..26</p>
        <p>Approx. Darshan Time for Sarvadarshanam (without SSD Tokens)&#8230;10 H.</p>""",
        dict(date="2026-10-22", pilgrims=65113, tonsures=26391, hundiCr=3.82, ladduLakh=3.71,
             annaLakh=1.71, hospital=2677, compartments=26, queueFull=False, waitHours=10.0),
    ),
    (
        """Total pilgrims who had darshan on 23.10.2026: 70,496
        Tonsures: 29,327
        Hundi kanukalu: 3.95 CR
        Laddu sale… 3.77 Lac
        Annaprasadam.. 2.28Lac
        Present Situation on 24-10-2026:
        Waiting Compartments..Outside line at ATGH
        Approx. Darshan Time for Sarvadarshanam (without SSD Tokens)…12-15H.""",
        dict(date="2026-10-23", pilgrims=70496, annaLakh=2.28, hospital=None, compartments=None,
             queueNote="Outside line at ATGH", queueFull=True, waitHours=15.0, waitText="12-15 h"),
    ),
    (
        """Total pilgrims who had darshan on 19.10.2026: 85,431
        Tonsures : 22,966  Hundi kanukalu : 3.20 CR  Laddu sale… 4.44 Lac  Annaprasadam.. 2.37Lac
        Ashwini hospital..9,269  Present Situation on 20-10-2026:  Waiting Compartments..06
        Approx. Darsan Time for Sarvadarshanam (without SSD Tokens)…6 – 8 H.""",
        dict(date="2026-10-19", tonsures=22966, compartments=6, waitHours=8.0, waitText="6-8 h"),
    ),
    (
        """Total pilgrims who had darshan on 11.10.2026: 71,759 Tonsures: 20,867 Hundi kanukalu: 3.37 CR
        Present Situation on 12-10-2026: Waiting Compartments..Present Direct Line
        Approx. Darshan Time for Sarvadarshanam (without SSD Tokens)…00 H.""",
        dict(date="2026-10-11", queueNote="Direct line", waitHours=0.0, waitText="0 h"),
    ),
    (
        """Total pilgrims who had darshan on 16.10.2026: 77,759 Tonsures: 28,977 Hundi kanukalu: 2.96 CR
        Annaprasadam.. 6.54 Lac Aswini hospital…13,540 Waiting Compartments..31
        Approx. Darshan Time for Sarvadarshanam (with out SSD Tokens)...12 H.""",
        dict(annaLakh=None, hospital=13540, compartments=31, queueFull=True, waitHours=12.0),
    ),
    ("TTD board meeting held today; donations of Rs 10 lakh received.", None),
]


def test_cases():
    for raw, want in CASES:
        got = parse_bulletin(raw)
        if want is None:
            assert got is None, got
            continue
        assert got is not None, raw[:60]
        for k, v in want.items():
            assert got.get(k) == v, (k, got.get(k), v, got)


if __name__ == "__main__":
    test_cases()
    print("all parser cases pass")
