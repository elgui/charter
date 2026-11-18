"""Calculate a paired score for an explicitly enumerated outcome cohort."""

import argparse
import csv
from fractions import Fraction
from pathlib import Path


FAMILIES = {"Spec": "S", "Road": "D", "Rail": "R", "Units": "U"}
CRITERIA = {f"{prefix}{n}" for prefix in FAMILIES.values() for n in (1, 2, 3)}
HEADER = ["outcome", "criterion", "before", "after", "evidence"]


def read_pair(path, outcomes):
    if any(not outcome.strip() for outcome in outcomes) or len(set(outcomes)) != len(outcomes):
        raise ValueError("Declared outcome IDs must be nonempty and unique.")
    expected = {(outcome, criterion) for outcome in outcomes for criterion in CRITERIA}
    cells = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames != HEADER:
            raise ValueError(f"Expected columns {','.join(HEADER)}.")
        for row in reader:
            if None in row or None in row.values():
                raise ValueError(f"Malformed CSV row ending on line {reader.line_num}.")
            key = (row["outcome"], row["criterion"])
            if key not in expected or key in cells:
                raise ValueError(f"Duplicate or undeclared cell {key}.")
            ratings = (row["before"], row["after"])
            if any(v not in {"0", "1", "2", "?"} for v in ratings):
                raise ValueError(f"Invalid rating for {key}.")
            if not row["evidence"].strip():
                raise ValueError(f"Supply evidence or explain the unknown for {key}.")
            cells[key] = tuple(None if v == "?" else int(v) for v in ratings)
    missing = expected.difference(cells)
    if missing:
        raise ValueError(f"Missing {len(missing)} cells, including {min(missing)}. Use ? for unknown.")
    return cells


def score(values):
    known = [v for v in values if v is not None]
    scale = Fraction(100, 2 * len(values))
    lower = scale * sum(known)
    coverage = 2 * scale * len(known)
    return lower, lower + 100 - coverage, coverage


def display(label, pairs):
    sides = [score(values) for values in zip(*pairs)]
    intervals = [f"{float(lo):.1f}–{float(hi):.1f} ({float(coverage):.1f}% coverage)"
                 for lo, hi, coverage in sides]
    delta = sides[1][0] - sides[0][0]
    print(f"{label:<9} {intervals[0]} → {intervals[1]}   {float(delta):+.1f} demonstrated points")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worksheet", type=Path)
    parser.add_argument("--outcome", action="append", required=True,
                        help="One promised outcome in the frozen cohort. Repeat for each outcome.")
    args = parser.parse_args()
    try:
        cells = read_pair(args.worksheet, args.outcome)
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        parser.exit(2, f"{error}\n")
    print(f"Declared cohort: {', '.join(args.outcome)}")
    for name, prefix in FAMILIES.items():
        display(name, [pair for (_, criterion), pair in cells.items() if criterion.startswith(prefix)])
    display("Overall", list(cells.values()))
    print("Read with the snapshot dates, holds, cell evidence and outcome observations in the worksheet.")


if __name__ == "__main__":
    main()
