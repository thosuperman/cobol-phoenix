"""Build the Phoenix Mutual sample fixtures from one declarative list.

Writes:
  backend/phoenix/samples/phoenix-mutual/fixtures/policies.txt   (PREMCALC input)
  backend/phoenix/samples/phoenix-mutual/phoenix-fixtures.json   (fixtures for RATEENG and PREMCALC)

Expected outputs are NOT written here: they are captured from GnuCOBOL with
`make sample-expected` so they are real execution results.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend" / "phoenix" / "samples" / "phoenix-mutual"

LAYOUT = [  # (field, width, kind, scale)
    ("PR-POLICY-ID", 10, "x", 0), ("PR-STATE", 2, "x", 0), ("PR-DRIVER-AGE", 3, "9", 0),
    ("PR-YEARS-LICENSED", 2, "9", 0), ("PR-VEHICLE-CLASS", 1, "x", 0), ("PR-VEHICLE-VALUE", 9, "9", 2),
    ("PR-COVERAGE", 1, "x", 0), ("PR-DEDUCTIBLE", 5, "9", 0), ("PR-CLAIMS-3YR", 2, "9", 0),
    ("PR-VIOLATIONS-3YR", 2, "9", 0), ("PR-MULTI-POLICY", 1, "x", 0), ("PR-ANNUAL-MILEAGE", 6, "9", 0),
    ("PR-PAY-PLAN", 1, "x", 0),
]  # fmt: skip

POLICIES = [
    ("standard-ca-full", "Experienced CA sedan driver, full coverage, multi-policy discount", ["PM00000001", "CA", 42, 20, "S", "28500.00", "F", 500, 0, 0, "Y", 12000, "A"]),
    ("young-sports-monthly", "19-year-old sports car, full coverage, monthly plan", ["PM00000002", "NY", 19, 1, "P", "45000.00", "F", 250, 1, 1, "N", 15000, "M"]),
    ("senior-truck-liability", "Senior truck driver, liability only, low mileage", ["PM00000003", "TX", 67, 45, "T", "18000.00", "L", 0, 0, 0, "Y", 5000, "A"]),
    ("suv-surcharge-high-mileage", "SUV with claims, violations and high mileage", ["PM00000004", "FL", 33, 12, "U", "39999.99", "S", 1000, 2, 3, "N", 25000, "M"]),
    ("declined-risk-points", "Five claims in three years: declined", ["PM00000005", "WA", 25, 7, "S", "15000.00", "S", 249, 5, 0, "N", 10000, "A"]),
    ("state-not-served", "State without a rate table entry", ["PM00000006", "ZZ", 40, 20, "S", "20000.00", "S", 500, 0, 0, "N", 10000, "A"]),
    ("age-out-of-range", "15-year-old driver", ["PM00000007", "OH", 15, 0, "S", "8000.00", "L", 0, 0, 0, "N", 5000, "A"]),
    ("years-licensed-inconsistent", "Licensed longer than possible for the age", ["PM00000008", "IL", 30, 20, "S", "21000.00", "S", 500, 0, 0, "N", 9000, "A"]),
    ("unknown-vehicle-class", "Vehicle class X is not rated", ["PM00000009", "AZ", 55, 30, "X", "30000.00", "S", 500, 0, 0, "N", 9000, "A"]),
    ("missing-policy-id", "Blank policy identifier", ["", "CA", 40, 20, "S", "20000.00", "S", 500, 0, 0, "N", 10000, "A"]),
    ("minimum-premium", "Cheap liability risk hits the 450.00 minimum premium", ["PM00000012", "OH", 45, 25, "S", "1000.00", "L", 0, 0, 0, "Y", 3000, "A"]),
    ("max-vehicle-value", "Maximum vehicle value, 18-year-old, sports, full", ["PM00000013", "CA", 18, 2, "P", "9999999.99", "F", 0, 0, 0, "N", 30000, "M"]),
]


def record(values: list) -> str:
    out = []
    for (name, width, kind, scale), v in zip(LAYOUT, values, strict=True):
        if kind == "x":
            out.append(str(v).ljust(width)[:width])
        else:
            digits = str(v).replace(".", "") if scale else str(v)
            out.append(digits.rjust(width, "0")[-width:])
    return "".join(out)


def main() -> None:
    lines = [record(v) for _, _, v in POLICIES]
    # one malformed record (non-numeric age) exercises the NUMERIC class test
    bad = record(["PM00000011", "CA", 40, 20, "S", "20000.00", "S", 500, 0, 0, "N", 10000, "A"])
    bad = bad[:12] + "4A0" + bad[15:]
    lines.insert(10, bad)
    (ROOT / "fixtures").mkdir(exist_ok=True)
    (ROOT / "fixtures" / "policies.txt").write_text("\n".join(lines) + "\nEND\n")
    rate_fixtures = []
    for fid, desc, values in POLICIES:
        inputs = {}
        for (name, _w, kind, _s), v in zip(LAYOUT, values, strict=True):
            inputs[name] = str(v)
        rate_fixtures.append({"id": fid, "description": desc, "inputs": {"POLICY-REC": inputs}})
    rate_fixtures.append({"id": "non-numeric-age", "description": "Driver age contains a letter (raw bytes '4A0')", "inputs": {"POLICY-REC": {**{n: str(v) for (n, *_), v in zip(LAYOUT, POLICIES[0][2], strict=True)}, "PR-POLICY-ID": "PM00000011", "PR-DRIVER-AGE": "raw:4A0"}}})
    fixtures = {
        "RATEENG": rate_fixtures,
        "PREMCALC": [{"id": "nightly-batch", "description": "fixtures/policies.txt (13 policies + END)", "stdin": (ROOT / "fixtures" / "policies.txt").read_text()}],
    }
    (ROOT / "phoenix-fixtures.json").write_text(json.dumps(fixtures, indent=2) + "\n")
    print(f"wrote {len(lines)} policy records and {len(rate_fixtures)} RATEENG fixtures")


if __name__ == "__main__":
    main()
