#!/usr/bin/env python3
"""charter_quality: score the preparation of a frozen outcome cohort, attribute its movement, compare two assessors.

    charter_quality.py score DECLARATION WORKSHEET [--rater NAME] [--pair BEFORE AFTER] [--json [--redact-evidence]]
    charter_quality.py agree DECLARATION WORKSHEET_A WORKSHEET_B [--raters A B] [--pair BEFORE AFTER] [--json]

Stage 1 of docs/proposals/assess-charter-quality.md, section "The score and its denominator". The declaration is a
JSON file that freezes the question before any rating: rubric version, project, horizon, scope (complete or sample),
the promised outcomes with their canonical homes, the snapshots with their source revisions or digests, the
assessors, the evidence cutoff and the holds. The worksheet is a CSV with one row per outcome and criterion and the
columns outcome,criterion,before,after,evidence and an optional reason. Ratings are 0, 1, 2 or ? (unknown). A cell
whose rating changes between the two snapshots needs one of the five reasons of rule 4.

Arithmetic only: the tool cannot discover an omitted outcome, judge evidence or authorize work. Outcome IDs are
declared by hand. Python 3 standard library only; the same inputs give the same output.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

SCHEMA = "charter-quality/1"
FAMILIES = {"Spec": "S", "Road": "D", "Rail": "R", "Units": "U"}
CRITERIA = tuple(f"{prefix}{n}" for prefix in FAMILIES.values() for n in (1, 2, 3))
RATINGS = {"0": 0, "1": 1, "2": 2, "?": None}
HEADER = ["outcome", "criterion", "before", "after", "evidence"]
REASONS = ("repaired-artifact", "changed-external-fact", "new-evidence", "regression", "assessor-disagreement")
DECLARATION_KEYS = {"rubric", "project", "horizon", "scope", "outcomes", "snapshots", "settings", "assessors",
                    "evidence_cutoff", "holds", "notes"}
REQUIRED_KEYS = DECLARATION_KEYS - {"settings", "notes"}
RESERVED_RATERS = {"outcome", "criterion", "side", "holds"}  # the fixed keys of a disagreement row


class Refusal(ValueError):
    """An input the tool will not score: the message names what to fix."""


def family_of(criterion: str) -> str:
    return next(name for name, prefix in FAMILIES.items() if criterion.startswith(prefix))


def _text(value, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Refusal(f"{what} must be a nonempty string.")
    return value


# --- the declaration -------------------------------------------------------------------------------------------

def read_declaration(path: Path) -> dict:
    raw = path.read_bytes()
    try:
        decl = json.loads(raw.decode("utf-8-sig"))
    except json.JSONDecodeError as error:
        raise Refusal(f"The declaration is not JSON: {error}.") from None
    if not isinstance(decl, dict):
        raise Refusal("The declaration must be a JSON object.")
    unknown = set(decl) - DECLARATION_KEYS
    if unknown:
        raise Refusal(f"Unknown declaration fields: {', '.join(sorted(unknown))}.")
    missing = REQUIRED_KEYS - set(decl)
    if missing:
        raise Refusal(f"The declaration lacks {', '.join(sorted(missing))}. Freeze the question before rating.")
    for key in ("rubric", "project", "horizon"):
        _text(decl[key], key)
    if decl["scope"] not in ("complete", "sample"):
        raise Refusal('scope must be "complete" or "sample".')
    try:
        dt.datetime.fromisoformat(_text(decl["evidence_cutoff"], "evidence_cutoff").replace("Z", "+00:00"))
    except ValueError:
        raise Refusal("evidence_cutoff must be an ISO 8601 date or time.") from None

    outcomes = decl["outcomes"]
    if not isinstance(outcomes, list) or not outcomes:
        raise Refusal("The declaration names no outcome. An empty inventory has no score.")
    ids = []
    for outcome in outcomes:
        if not isinstance(outcome, dict) or set(outcome) != {"id", "home"}:
            raise Refusal('Each outcome is an object with exactly "id" and "home" (its canonical home).')
        oid = _text(outcome["id"], "outcome id")
        if oid != oid.strip():
            raise Refusal(f"Outcome id {oid!r} has surrounding spaces: the worksheet must match it exactly.")
        ids.append(oid)
        _text(outcome["home"], f"home of outcome {outcome['id']}")
    if len(set(ids)) != len(ids):
        raise Refusal("Declared outcome IDs must be unique: a second path to one result is not a second outcome.")

    snapshots = decl["snapshots"]
    if not isinstance(snapshots, dict) or len(snapshots) < 2:
        raise Refusal("Declare at least two snapshots, each with its sources.")
    for name, snap in snapshots.items():
        if not isinstance(snap, dict) or not isinstance(snap.get("sources"), list) or not snap["sources"]:
            raise Refusal(f'Snapshot "{name}" needs a nonempty "sources" list.')
        for source in snap["sources"]:
            if not isinstance(source, dict) or not isinstance(source.get("ref"), str) or not source["ref"].strip():
                raise Refusal(f'Each source of snapshot "{name}" needs a "ref".')
            if not any(isinstance(source.get(k), str) and source[k].strip() for k in ("revision", "sha256")):
                raise Refusal(f'Source {source["ref"]} of snapshot "{name}" needs a "revision" or a "sha256".')

    assessors = decl["assessors"]
    if not isinstance(assessors, list) or not assessors:
        raise Refusal("assessors must be a nonempty list of distinct names.")
    for name in assessors:
        _text(name, "assessor")
        if name in RESERVED_RATERS:
            raise Refusal(f"Assessor name {name!r} is reserved ({', '.join(sorted(RESERVED_RATERS))}).")
    if len(set(assessors)) != len(assessors):
        raise Refusal("assessors must be a nonempty list of distinct names.")
    if "settings" in decl and not isinstance(decl["settings"], dict):
        raise Refusal("settings must be an object.")

    if not isinstance(decl["holds"], list):
        raise Refusal("holds must be a list (empty when there is none).")
    for hold in decl["holds"]:
        if not isinstance(hold, dict):
            raise Refusal("Each hold is an object.")
        _text(hold.get("id"), "hold id")
        _text(hold.get("reason"), f"reason of hold {hold.get('id')}")
        if not isinstance(hold.get("critical"), bool):
            raise Refusal(f"Hold {hold['id']} needs critical: true or false.")
        if "outcome" in hold and hold["outcome"] not in ids:
            raise Refusal(f"Hold {hold['id']} names undeclared outcome {hold['outcome']}.")
        criteria = hold.get("criteria", [])
        if not isinstance(criteria, list):
            raise Refusal(f"criteria of hold {hold['id']} must be a list of criterion IDs.")
        bad = [c for c in criteria if c not in CRITERIA]
        if bad:
            raise Refusal(f"Hold {hold['id']} names unknown criteria {', '.join(map(str, bad))}.")
    decl["_ids"] = ids
    decl["_sha256"] = hashlib.sha256(raw).hexdigest()
    return decl


# --- the worksheet ---------------------------------------------------------------------------------------------

def read_worksheet(path: Path, outcomes: list[str]) -> dict:
    """Every declared (outcome, criterion) cell once: {(outcome, criterion): {before, after, evidence, reason}}."""
    if not outcomes:
        raise Refusal("The declaration names no outcome. An empty inventory has no score.")
    if any(not o.strip() for o in outcomes) or len(set(outcomes)) != len(outcomes):
        raise Refusal("Declared outcome IDs must be nonempty and unique.")
    expected = {(o, c) for o in outcomes for c in CRITERIA}
    cells = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames not in (HEADER, HEADER + ["reason"]):
            raise Refusal(f"Expected columns {','.join(HEADER)} and optionally reason.")
        for row in reader:
            if None in row or None in row.values():
                raise Refusal(f"Malformed CSV row ending on line {reader.line_num}.")
            key = (row["outcome"], row["criterion"])
            if row["criterion"] not in CRITERIA:
                raise Refusal(f"Unknown criterion {row['criterion']!r} on line {reader.line_num}.")
            if key not in expected:
                raise Refusal(f"Undeclared outcome {row['outcome']!r} on line {reader.line_num}. "
                              "Declare it in the frozen inventory first.")
            if key in cells:
                raise Refusal(f"Duplicate cell {key} on line {reader.line_num}.")
            if row["before"] not in RATINGS or row["after"] not in RATINGS:
                raise Refusal(f"Invalid rating for {key}: use 0, 1, 2 or ?.")
            if not row["evidence"].strip():
                raise Refusal(f"Supply evidence or explain the unknown for {key}.")
            before, after = RATINGS[row["before"]], RATINGS[row["after"]]
            reason = row.get("reason", "").strip()
            if row["before"] != row["after"] and reason not in REASONS:
                raise Refusal(f"The rating of {key} changes: give a reason, one of {', '.join(REASONS)}.")
            if row["before"] == row["after"] and reason:
                raise Refusal(f"The rating of {key} does not change: leave its reason empty.")
            cells[key] = {"before": before, "after": after, "evidence": row["evidence"], "reason": reason}
    missing = sorted(expected.difference(cells))
    if missing:
        raise Refusal(f"Missing {len(missing)} cells, including {missing[0]}. Use ? for unknown; "
                      "deleting a cell never removes it from the denominator.")
    return cells


# --- the arithmetic --------------------------------------------------------------------------------------------

def interval(values: list) -> tuple[Fraction, Fraction, Fraction]:
    """(lower, upper, coverage) in points out of 100 for equally weighted cells rated 0-2 or None (unknown)."""
    if not values:
        raise Refusal("No cell to score.")
    known = [v for v in values if v is not None]
    scale = Fraction(100, 2 * len(values))
    lower = scale * sum(known)
    coverage = 2 * scale * len(known)
    return lower, lower + 100 - coverage, coverage


def mean(triples: list[tuple]) -> tuple[Fraction, Fraction, Fraction]:
    n = len(triples)
    return tuple(sum((t[i] for t in triples), Fraction(0)) / n for i in range(3))


def side_scores(cells: dict, outcomes: list[str], side: str) -> dict:
    """Family and overall intervals per outcome, then each averaged over the declared outcomes with equal weight."""
    per_outcome = {}
    for o in outcomes:
        fams = {name: interval([cells[(o, c)][side] for c in CRITERIA if c.startswith(prefix)])
                for name, prefix in FAMILIES.items()}
        fams["Overall"] = mean([fams[name] for name in FAMILIES])
        per_outcome[o] = fams
    project = {name: mean([per_outcome[o][name] for o in outcomes]) for name in [*FAMILIES, "Overall"]}
    inspected = sum(1 for o in outcomes if any(cells[(o, c)][side] is not None for c in CRITERIA))
    return {"project": project, "outcomes": per_outcome, "inspected": inspected}


def changes(cells: dict, outcomes: list[str]) -> list[dict]:
    out = []
    for o in outcomes:
        for c in CRITERIA:
            cell = cells[(o, c)]
            if cell["before"] != cell["after"]:
                out.append({"outcome": o, "criterion": c, "family": family_of(c), "before": cell["before"],
                            "after": cell["after"], "reason": cell["reason"],
                            "lost_evidence": cell["before"] is not None and cell["after"] is None})
    return out


def holds_on(decl: dict, outcome: str, criterion: str) -> list[str]:
    return [h["id"] for h in decl["holds"]
            if h.get("outcome", outcome) == outcome and criterion in h.get("criteria", [])]


# --- assessment and agreement ----------------------------------------------------------------------------------

def pick_pair(decl: dict, pair: list[str] | None) -> tuple[str, str]:
    before, after = pair or ("before", "after")
    for name in (before, after):
        if name not in decl["snapshots"]:
            raise Refusal(f'Snapshot "{name}" is not declared. Declared: {", ".join(decl["snapshots"])}.')
    if before == after:
        raise Refusal("A pair needs two different snapshots.")
    return before, after


def pick_rater(decl: dict, rater: str | None) -> str:
    if rater is None:
        if len(decl["assessors"]) != 1:
            raise Refusal(f"Name the rater with --rater: one of {', '.join(decl['assessors'])}.")
        return decl["assessors"][0]
    if rater not in decl["assessors"]:
        raise Refusal(f"Rater {rater!r} is not a declared assessor ({', '.join(decl['assessors'])}).")
    return rater


def assess(decl: dict, worksheet: Path, rater: str | None = None, pair: list[str] | None = None) -> dict:
    """One rater's worksheet on a declaration: the serialized assessment (exact Fractions inside)."""
    before, after = pick_pair(decl, pair)
    rater = pick_rater(decl, rater)
    ids = decl["_ids"]
    cells = read_worksheet(worksheet, ids)
    return {"decl": decl, "rater": rater, "pair": (before, after), "cells": cells, "ids": ids,
            "worksheet_sha256": hashlib.sha256(worksheet.read_bytes()).hexdigest(),
            "scores": {"before": side_scores(cells, ids, "before"), "after": side_scores(cells, ids, "after")},
            "changes": changes(cells, ids)}


def agreement(a: dict, b: dict) -> dict:
    """Cell-by-cell agreement of two raters' worksheets on the same declaration and pair."""
    if a["decl"]["_sha256"] != b["decl"]["_sha256"] or a["pair"] != b["pair"]:
        raise Refusal("Agreement compares two worksheets on the same declaration and the same pair.")
    if a["rater"] == b["rater"]:
        raise Refusal("Agreement compares two different raters.")
    rows, by_criterion = [], {c: {"cells": 0, "agree": 0} for c in CRITERIA}
    totals = {"cells": 0, "agree": 0, "both_known": 0, "known_agree": 0, "known_within_one": 0, "one_unknown": 0,
              "movement_compared": 0, "movement_agree": 0}
    for o in a["ids"]:
        for c in CRITERIA:
            ca, cb = a["cells"][(o, c)], b["cells"][(o, c)]
            for side in ("before", "after"):
                va, vb = ca[side], cb[side]
                same = va == vb
                totals["cells"] += 1
                totals["agree"] += same
                by_criterion[c]["cells"] += 1
                by_criterion[c]["agree"] += same
                if va is not None and vb is not None:
                    totals["both_known"] += 1
                    totals["known_agree"] += same
                    totals["known_within_one"] += abs(va - vb) <= 1
                elif (va is None) != (vb is None):
                    totals["one_unknown"] += 1
                if not same:
                    rows.append({"outcome": o, "criterion": c, "side": side, a["rater"]: va, b["rater"]: vb,
                                 "holds": holds_on(a["decl"], o, c)})
            if None not in (ca["before"], ca["after"], cb["before"], cb["after"]):
                totals["movement_compared"] += 1
                sign = lambda cell: (cell["after"] > cell["before"]) - (cell["after"] < cell["before"])
                totals["movement_agree"] += sign(ca) == sign(cb)
    return {"raters": [a["rater"], b["rater"]], "totals": totals, "by_criterion": by_criterion,
            "disagreements": rows}


# --- output ----------------------------------------------------------------------------------------------------

def f(x: Fraction) -> float:
    return float(x)


def score_json(triple) -> dict:
    lower, upper, coverage = triple
    return {"lower": f(lower), "upper": f(upper), "coverage": f(coverage)}


def rating(v) -> str:
    return "?" if v is None else str(v)


def assessment_json(res: dict, redact: bool = False) -> dict:
    decl, (before, after) = res["decl"], res["pair"]
    cells = []
    for o in res["ids"]:
        for c in CRITERIA:
            cell = res["cells"][(o, c)]
            evidence = cell["evidence"]
            if redact:
                evidence = "sha256:" + hashlib.sha256(evidence.encode("utf-8")).hexdigest()
            cells.append({"outcome": o, "criterion": c, "family": family_of(c),
                          "before": rating(cell["before"]), "after": rating(cell["after"]),
                          "state": {side: "unknown" if cell[side] is None else "rated" for side in ("before", "after")},
                          "evidence": evidence, "reason": cell["reason"] or None, "holds": holds_on(decl, o, c)})
    scores = {}
    for side in ("before", "after"):
        s = res["scores"][side]
        scores[side] = {"snapshot": before if side == "before" else after,
                        "families": {k: score_json(v) for k, v in s["project"].items() if k != "Overall"},
                        "overall": score_json(s["project"]["Overall"]),
                        "demonstrated_points": f(s["project"]["Overall"][0]),
                        "outcomes": {o: {k: score_json(v) for k, v in fam.items()} for o, fam in s["outcomes"].items()},
                        "outcomes_inspected": s["inspected"]}
    return {
        "schema": SCHEMA, "rubric": decl["rubric"], "project": decl["project"], "horizon": decl["horizon"],
        "scope": decl["scope"], "outcomes": decl["outcomes"], "outcomes_total": len(res["ids"]),
        "criteria": list(CRITERIA), "evidence_cutoff": decl["evidence_cutoff"], "rater": res["rater"],
        "settings": decl.get("settings", {}),
        "snapshots": {name: decl["snapshots"][name] for name in res["pair"]},
        "inputs": {"declaration_sha256": decl["_sha256"], "worksheet_sha256": res["worksheet_sha256"],
                   "evidence_redacted": redact},
        "holds": decl["holds"], "critical_holds": sum(h["critical"] for h in decl["holds"]),
        "scores": scores,
        "demonstrated_delta": f(res["scores"]["after"]["project"]["Overall"][0]
                                - res["scores"]["before"]["project"]["Overall"][0]),
        "changes": [{**ch, "before": rating(ch["before"]), "after": rating(ch["after"])} for ch in res["changes"]],
        "cells": cells,
    }


def line(label: str, sides: list) -> str:
    parts = [f"{f(lo):.1f}–{f(hi):.1f} ({f(cov):.1f}% coverage)" for lo, hi, cov in sides]
    delta = sides[1][0] - sides[0][0]
    return f"{label:<9} {parts[0]} → {parts[1]}   {f(delta):+.1f} demonstrated points"


def assessment_text(res: dict) -> str:
    decl, (before, after) = res["decl"], res["pair"]
    sb, sa = res["scores"]["before"], res["scores"]["after"]
    n = len(res["ids"])
    out = [f"Declared cohort ({decl['scope']}): {', '.join(res['ids'])}",
           f"Rubric {decl['rubric']}; rater {res['rater']}; evidence cutoff {decl['evidence_cutoff']}; "
           f"{before} → {after}"]
    for name in [*FAMILIES, "Overall"]:
        out.append(line(name, [sb["project"][name], sa["project"][name]]))
    if n > 1:
        for o in res["ids"]:
            out.append(line(f"  {o}", [sb["outcomes"][o]["Overall"], sa["outcomes"][o]["Overall"]]))
    critical = [h["id"] for h in decl["holds"] if h["critical"]]
    out.append(f"Outcomes inspected {sb['inspected']}/{n} → {sa['inspected']}/{n}; "
               f"unresolved critical holds {len(critical)}" + (f" ({', '.join(critical)})" if critical else ""))
    if res["changes"]:
        out.append("Changed cells:")
        for ch in res["changes"]:
            lost = "  lost evidence" if ch["lost_evidence"] else ""
            out.append(f"  {ch['outcome']} {ch['criterion']}  {rating(ch['before'])} → {rating(ch['after'])}  "
                       f"{ch['reason']}{lost}")
    else:
        out.append("Changed cells: none")
    unknown = [f"{o} {c}" for o in res["ids"] for c in CRITERIA if res["cells"][(o, c)]["after"] is None]
    out.append("Unresolved cells: " + (", ".join(unknown) if unknown else "none"))
    out.append("Read with the snapshot sources, holds, cell evidence and outcome observations in the inputs.")
    return "\n".join(out)


def agreement_json(a: dict, b: dict, agr: dict) -> dict:
    decl = a["decl"]
    return {"schema": SCHEMA, "rubric": decl["rubric"], "project": decl["project"], "horizon": decl["horizon"],
            "scope": decl["scope"], "outcomes": decl["outcomes"], "outcomes_total": len(a["ids"]),
            "declaration_sha256": a["decl"]["_sha256"], "pair": list(a["pair"]), "raters": agr["raters"],
            "totals": agr["totals"], "by_criterion": agr["by_criterion"], "disagreements": [
                {k: (rating(v) if k in agr["raters"] else v) for k, v in row.items()} for row in agr["disagreements"]],
            "assessments": {r["rater"]: {side: {"snapshot": r["pair"][i],
                                                "overall": score_json(r["scores"][side]["project"]["Overall"]),
                                                "families": {k: score_json(v) for k, v in
                                                             r["scores"][side]["project"].items() if k != "Overall"}}
                                         for i, side in enumerate(("before", "after"))} for r in (a, b)}}


def agreement_text(a: dict, b: dict, agr: dict) -> str:
    ra, rb = agr["raters"]
    t = agr["totals"]
    out = [f"Agreement of {ra} and {rb} on {a['decl']['project']}, {' → '.join(a['pair'])}, rubric {a['decl']['rubric']}",
           f"Cells agreeing: {t['agree']}/{t['cells']} (both snapshots); both rated: {t['known_agree']}/{t['both_known']} "
           f"exact, {t['known_within_one']}/{t['both_known']} within one; rated by one only: {t['one_unknown']}; "
           f"same direction of movement: {t['movement_agree']}/{t['movement_compared']}",
           f"Declared cohort ({a['decl']['scope']}): {', '.join(a['ids'])}; horizon {a['decl']['horizon']}",
           "By criterion: " + "  ".join(f"{c} {v['agree']}/{v['cells']}" for c, v in agr["by_criterion"].items())]
    if agr["disagreements"]:
        out.append("Disagreements:")
        for row in agr["disagreements"]:
            hold = f"  affects hold {', '.join(row['holds'])}" if row["holds"] else ""
            out.append(f"  {row['outcome']} {row['criterion']} {row['side']}: {ra} {rating(row[ra])}, "
                       f"{rb} {rating(row[rb])}{hold}")
    else:
        out.append("Disagreements: none")
    for r in (a, b):
        out.append(f"{r['rater']}:")
        for name in [*FAMILIES, "Overall"]:
            out.append("  " + line(name, [r["scores"]["before"]["project"][name], r["scores"]["after"]["project"][name]]))
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="charter_quality.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="verb", required=True)
    sc = sub.add_parser("score", help="one rater's intervals, coverage and cell-by-cell movement")
    sc.add_argument("declaration", type=Path)
    sc.add_argument("worksheet", type=Path)
    sc.add_argument("--rater", help="a declared assessor; required when several are declared")
    sc.add_argument("--redact-evidence", action="store_true", help="with --json, replace evidence text by its digest")
    ag = sub.add_parser("agree", help="two raters' worksheets on the same declaration, compared cell by cell")
    ag.add_argument("declaration", type=Path)
    ag.add_argument("worksheet_a", type=Path)
    ag.add_argument("worksheet_b", type=Path)
    ag.add_argument("--raters", nargs=2, metavar=("A", "B"), help="the declared assessors of the two worksheets")
    for p in (sc, ag):
        p.add_argument("--pair", nargs=2, metavar=("BEFORE", "AFTER"),
                       help="declared snapshots the before and after columns rate (default: before after)")
        p.add_argument("--json", action="store_true", help="emit the serialized result as JSON")
    args = parser.parse_args(argv)
    try:
        decl = read_declaration(args.declaration)
        if args.verb == "score":
            res = assess(decl, args.worksheet, args.rater, args.pair)
            print(json.dumps(assessment_json(res, args.redact_evidence), indent=2, ensure_ascii=False)
                  if args.json else assessment_text(res))
        else:
            if args.raters is None and len(decl["assessors"]) != 2:
                raise Refusal("Name the two raters with --raters A B.")
            ra, rb = args.raters or decl["assessors"]
            a = assess(decl, args.worksheet_a, ra, args.pair)
            b = assess(decl, args.worksheet_b, rb, args.pair)
            agr = agreement(a, b)
            print(json.dumps(agreement_json(a, b, agr), indent=2, ensure_ascii=False)
                  if args.json else agreement_text(a, b, agr))
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
