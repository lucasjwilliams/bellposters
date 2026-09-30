#!/usr/bin/env python3
"""Build data/rings.json from Dove's Guide exports.

Inputs (repo root, from https://dove.cccbr.org.uk/downloads):
  dove.csv   - one row per ring (tower details, tenor weight)
  bells.csv  - one row per bell (weight, diameter, note)

Output: data/rings.json, a compact array the site loads:
  towers: [ringId, place, dedication, county, country, bellCount, tenorLbs, bells]
  bells:  [role, lbs, approx(0/1), note, diameterInches]
Dove data is CC BY-SA 4.0 - keep the attribution in the site footer.
"""
import csv
import json
import os
import re
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def compact(n):
    """Drop trailing .0 so the JSON stays small."""
    if n is None:
        return None
    return int(n) if n == int(n) else round(n, 2)


def main():
    bells_by_ring = defaultdict(list)
    with open(os.path.join(ROOT, "bells.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["Collection Type"] not in ("full-circle ring", "lightweight ring"):
                continue
            role = row["Bell Role"].strip()
            if not role:
                continue
            bells_by_ring[row["Ring ID"]].append([
                role,
                compact(num(row["Weight (lbs)"])),
                1 if row["Weight (approx)"].strip() else 0,
                row["Note"].strip(),
                compact(num(row["Diameter (in)"])),
            ])

    def role_key(b):
        # "1", "2", "6b", "2#" ... sort by number, extras just after their number
        m = re.match(r"(\d+)(.*)", b[0])
        return (int(m.group(1)), m.group(2)) if m else (9999, b[0])

    towers = []
    with open(os.path.join(ROOT, "dove.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            bells = sorted(bells_by_ring.get(row["RingID"], []), key=role_key)
            place = row["Place"]
            if row["Place2"]:
                place += ", " + row["Place2"]
            towers.append([
                int(row["RingID"]),
                place,
                row["Dedicn"],
                row["County"] or row["Region"],
                row["Country"],
                int(row["Bells"] or 0),
                compact(num(row["Wt"])),
                bells,
            ])

    towers.sort(key=lambda t: (t[1].lower(), t[2].lower()))
    # A script rather than JSON so the site also works opened straight from disk
    out = os.path.join(ROOT, "data", "rings.js")
    with open(out, "w", encoding="utf-8") as f:
        f.write("window.RINGS=")
        json.dump(towers, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    with_bells = sum(1 for t in towers if t[7])
    print(f"Wrote {len(towers)} rings ({with_bells} with per-bell data) to {out}")


if __name__ == "__main__":
    main()
