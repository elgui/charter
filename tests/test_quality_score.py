"""The quality score's first tooling (bin/charter_quality.py), stage 1 of docs/proposals/assess-charter-quality.md.

The proposal's throwaway calculator becomes a tested command: a frozen declaration (JSON) and one worksheet (CSV) give
the four family intervals and the overall one, per outcome and averaged over the declared outcomes with equal weight;
movement is attributed cell by cell with a reason; two raters' worksheets on one declaration are compared cell by
cell; the result is also emitted as JSON. The worked examples are the proposal's own (section "The score and its
denominator" and the programme paragraph); the interview-trial fixture carries cx-1's ratings of 2026-11-18 only,
with placeholder evidence, and must reproduce the figures reported then: 62.5–70.8 → 70.8–79.2 at 91.7% coverage."""
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from fractions import Fraction
from pathlib import Path

from helpers import REPO

sys.path.insert(0, str(REPO / "bin"))
import charter_quality as cq  # noqa: E402

TOOL = REPO / "bin" / "charter_quality.py"
BLANK = REPO / "docs" / "proposals" / "charter-quality-worksheet.csv"
BLANK_DECLARATION = REPO / "docs" / "proposals" / "charter-quality-declaration.json"

# cx-1's ratings of the interview-trial outcome, before and after the repair (no evidence text: it is private).
INTERVIEW = {"S1": ("2", "2"), "S2": ("2", "2"), "S3": ("1", "1"), "D1": ("2", "2"), "D2": ("1", "1"),
             "D3": ("?", "?"), "R1": ("2", "2"), "R2": ("2", "2"), "R3": ("2", "2"), "U1": ("0", "1"),
             "U2": ("0", "1"), "U3": ("1", "1")}


def declaration(outcomes=("x",), assessors=("first",), holds=(), **extra):
    decl = {"rubric": "assess-charter-quality@test", "project": "demo", "horizon": "the test horizon",
            "scope": "complete", "outcomes": [{"id": o, "home": f"rails.md#{o}"} for o in outcomes],
            "snapshots": {"before": {"sources": [{"ref": "unit.md", "sha256": "aa" * 32}]},
                          "after": {"sources": [{"ref": "unit.md", "sha256": "bb" * 32}]},
                          "control": {"sources": [{"ref": "unit.md", "revision": "c0ffee"}]}},
            "assessors": list(assessors), "evidence_cutoff": "2026-11-18T19:05:15Z", "holds": list(holds)}
    decl.update(extra)
    return decl


def rows_for(outcome, ratings, default=("2", "2")):
    """Twelve rows for one outcome; `ratings` maps a criterion to (before, after[, reason])."""
    rows = []
    for c in cq.CRITERIA:
        r = ratings.get(c, default)
        before, after = r[0], r[1]
        reason = r[2] if len(r) > 2 else ("repaired-artifact" if before != after else "")
        rows.append([outcome, c, before, after, f"placeholder evidence for {c}", reason])
    return rows


class Bed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_decl(self, decl, name="decl.json"):
        path = self.dir / name
        path.write_text(json.dumps(decl), encoding="utf-8")
        return path

    def write_sheet(self, rows, name="sheet.csv", header=None):
        path = self.dir / name
        with path.open("w", encoding="utf-8", newline="") as stream:
            w = csv.writer(stream)
            w.writerow(header or cq.HEADER + ["reason"])
            w.writerows(rows)
        return path

    def assess(self, decl, rows, rater=None, pair=None):
        return cq.assess(cq.read_declaration(self.write_decl(decl)), self.write_sheet(rows), rater, pair)

    def refused(self, decl, rows, fragment, header=None):
        with self.assertRaises(cq.Refusal) as ctx:
            cq.assess(cq.read_declaration(self.write_decl(decl)), self.write_sheet(rows, header=header))
        self.assertIn(fragment, str(ctx.exception))

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True)


def project(res, side, name="Overall"):
    return res["scores"][side]["project"][name]


class WorkedExamples(Bed):
    """The proposal's examples, rule by rule."""

    def test_unit_ratings_2_0_1_give_50_at_full_coverage(self):
        lower, upper, coverage = cq.interval([2, 0, 1])
        self.assertEqual((lower, upper, coverage), (50, 50, 100))
        res = self.assess(declaration(), rows_for("x", {"U1": ("2", "2"), "U2": ("0", "0"), "U3": ("1", "1")}))
        self.assertEqual(project(res, "before", "Units"), (50, 50, 100))

    def test_an_unknown_in_place_of_the_zero_gives_50_to_83_3_at_two_thirds(self):
        lower, upper, coverage = cq.interval([2, None, 1])
        self.assertEqual((lower, upper, coverage), (50, Fraction(250, 3), Fraction(200, 3)))
        self.assertEqual(f"{float(upper):.1f}", "83.3")

    def test_one_supported_and_one_uninspected_outcome_read_50_to_100_at_half_coverage(self):
        rows = rows_for("done", {}) + rows_for("unseen", {c: ("?", "?") for c in cq.CRITERIA})
        res = self.assess(declaration(outcomes=("done", "unseen")), rows)
        self.assertEqual(project(res, "after"), (50, 100, 50))
        self.assertEqual(res["scores"]["after"]["inspected"], 1)
        self.assertEqual(res["scores"]["after"]["outcomes"]["unseen"]["Overall"], (0, 100, 0))

    def test_two_paths_to_one_verified_and_one_failed_result_count_two_outcomes_and_give_50(self):
        rows = rows_for("verified", {}) + rows_for("failed", {c: ("0", "0") for c in cq.CRITERIA})
        res = self.assess(declaration(outcomes=("verified", "failed")), rows)
        self.assertEqual(project(res, "after"), (50, 50, 100))
        # Averaging the branch averages (X) and (X, Y) would give 75; listing X twice is refused, not weighted.
        with self.assertRaises(cq.Refusal) as ctx:
            cq.read_declaration(self.write_decl(declaration(outcomes=("verified", "verified", "failed"))))
        self.assertIn("unique", str(ctx.exception))

    def test_deleting_a_failed_result_cannot_raise_demonstrated_points(self):
        ratings = {"U1": ("2", "2"), "U2": ("0", "0"), "U3": ("1", "1")}
        base = self.assess(declaration(), rows_for("x", ratings))
        deleted = [r for r in rows_for("x", ratings) if r[1] != "U2"]
        self.refused(declaration(), deleted, "Missing 1 cells")
        unknown = self.assess(declaration(), rows_for("x", {**ratings, "U2": ("?", "?")}))
        self.assertEqual(project(unknown, "after", "Units")[0], project(base, "after", "Units")[0])
        self.assertEqual(project(unknown, "after")[0], project(base, "after")[0])
        self.assertLess(project(unknown, "after")[2], 100)
        # Deleting a whole outcome is the same error: every declared outcome needs its twelve cells.
        self.refused(declaration(outcomes=("x", "y")), rows_for("x", ratings), "Missing 12 cells")

    def test_outcomes_are_averaged_with_equal_weight_not_pooled(self):
        rows = rows_for("a", {"S1": ("?", "?")}) + rows_for("b", {c: ("0", "0") for c in cq.CRITERIA})
        res = self.assess(declaration(outcomes=("a", "b")), rows)
        a = res["scores"]["after"]["outcomes"]["a"]["Spec"]
        self.assertEqual(a, (Fraction(200, 3), 100, Fraction(200, 3)))
        self.assertEqual(project(res, "after", "Spec"), (Fraction(100, 3), 50, Fraction(500, 6)))


class InterviewTrial(Bed):
    """cx-1's interview-trial pair, ratings only, reproduces the figures of 2026-11-18."""

    def setUp(self):
        super().setUp()
        rows = rows_for("interview-trial", INTERVIEW)
        self.decl = declaration(outcomes=("interview-trial",), assessors=("cx-1",))
        self.res = self.assess(self.decl, rows)

    def test_overall_before_and_after(self):
        fmt = lambda t: f"{float(t[0]):.1f}–{float(t[1]):.1f} {float(t[2]):.1f}%"
        self.assertEqual(fmt(project(self.res, "before")), "62.5–70.8 91.7%")
        self.assertEqual(fmt(project(self.res, "after")), "70.8–79.2 91.7%")

    def test_units_go_from_16_7_to_50(self):
        self.assertEqual(f"{float(project(self.res, 'before', 'Units')[0]):.1f}", "16.7")
        self.assertEqual(project(self.res, "after", "Units"), (50, 50, 100))
        self.assertEqual(project(self.res, "after", "Rail"), (100, 100, 100))
        self.assertEqual(f"{float(project(self.res, 'after', 'Spec')[0]):.1f}", "83.3")
        self.assertEqual(project(self.res, "after", "Road"), (50, Fraction(250, 3), Fraction(200, 3)))

    def test_movement_is_attributed_cell_by_cell(self):
        self.assertEqual([(c["criterion"], c["before"], c["after"], c["reason"]) for c in self.res["changes"]],
                         [("U1", 0, 1, "repaired-artifact"), ("U2", 0, 1, "repaired-artifact")])

    def test_text_output_keeps_the_calculator_lines(self):
        decl = self.write_decl(self.decl, "interview.json")
        sheet = self.write_sheet(rows_for("interview-trial", INTERVIEW), "interview.csv")
        out = self.run_tool("score", decl, sheet)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Overall   62.5–70.8 (91.7% coverage) → 70.8–79.2 (91.7% coverage)   +8.3 demonstrated points",
                      out.stdout)
        self.assertIn("Units     16.7–16.7 (100.0% coverage) → 50.0–50.0 (100.0% coverage)   +33.3", out.stdout)
        self.assertIn("interview-trial U1  0 → 1  repaired-artifact", out.stdout)
        self.assertIn("Unresolved cells: interview-trial D3", out.stdout)


class Refusals(Bed):
    def test_missing_cell(self):
        self.refused(declaration(), rows_for("x", {})[1:], "Missing 1 cells")

    def test_duplicate_cell(self):
        rows = rows_for("x", {})
        self.refused(declaration(), rows + rows[:1], "Duplicate cell")

    def test_undeclared_outcome(self):
        self.refused(declaration(), rows_for("x", {}) + rows_for("y", {}), "Undeclared outcome 'y'")

    def test_invalid_rating(self):
        self.refused(declaration(), rows_for("x", {"S1": ("3", "3")}), "Invalid rating")
        self.refused(declaration(), rows_for("x", {"S1": ("", "")}), "Invalid rating")

    def test_empty_evidence(self):
        rows = rows_for("x", {})
        rows[4][4] = "  "
        self.refused(declaration(), rows, "Supply evidence")

    def test_empty_outcome_list(self):
        with self.assertRaises(cq.Refusal) as ctx:
            cq.read_declaration(self.write_decl(declaration(outcomes=())))
        self.assertIn("empty inventory has no score", str(ctx.exception))
        with self.assertRaises(cq.Refusal):
            cq.read_worksheet(self.write_sheet(rows_for("x", {})), [])

    def test_a_changed_cell_needs_one_of_the_five_reasons(self):
        self.refused(declaration(), rows_for("x", {"U1": ("0", "1", "")}), "give a reason")
        self.refused(declaration(), rows_for("x", {"U1": ("0", "1", "looks better")}), "give a reason")
        self.refused(declaration(), rows_for("x", {"U1": ("1", "1", "regression")}), "leave its reason empty")
        for reason in cq.REASONS:
            self.assess(declaration(), rows_for("x", {"U1": ("2", "?", reason)}))

    def test_the_five_column_worksheet_still_reads_when_nothing_moves(self):
        rows = [r[:5] for r in rows_for("x", {})]
        cq.assess(cq.read_declaration(self.write_decl(declaration())), self.write_sheet(rows, header=cq.HEADER))
        self.refused(declaration(), [r[:5] for r in rows_for("x", {"U1": ("0", "1")})], "give a reason",
                     header=cq.HEADER)

    def test_unknown_criterion_and_wrong_header(self):
        rows = rows_for("x", {})
        rows[0][1] = "S4"
        self.refused(declaration(), rows, "Unknown criterion")
        self.refused(declaration(), rows_for("x", {}), "Expected columns", header=["outcome", "criterion", "x"])

    def test_declaration_fields(self):
        for key in ("rubric", "horizon", "scope", "snapshots", "assessors", "evidence_cutoff", "holds"):
            decl = declaration()
            del decl[key]
            with self.assertRaises(cq.Refusal, msg=key):
                cq.read_declaration(self.write_decl(decl))
        bad = [declaration(scope="most"), declaration(evidence_cutoff="yesterday"), declaration(extra=1),
               declaration(outcomes=()) | {"outcomes": ["x"]},
               declaration(snapshots={"before": {"sources": [{"ref": "a"}]}, "after": {"sources": [{"ref": "a",
                                                                                                  "sha256": "b"}]}}),
               declaration(holds=[{"id": "h", "reason": "r", "critical": "yes"}]),
               declaration(holds=[{"id": "h", "reason": "r", "critical": True, "outcome": "nope"}])]
        for decl in bad:
            with self.assertRaises(cq.Refusal, msg=json.dumps(decl)[:200]):
                cq.read_declaration(self.write_decl(decl))

    def test_rater_and_pair_must_be_declared(self):
        decl = declaration(assessors=("first", "second"))
        with self.assertRaises(cq.Refusal):
            self.assess(decl, rows_for("x", {}))  # two assessors: name one
        with self.assertRaises(cq.Refusal):
            self.assess(decl, rows_for("x", {}), rater="third")
        with self.assertRaises(cq.Refusal):
            self.assess(decl, rows_for("x", {}), rater="first", pair=["before", "later"])
        res = self.assess(decl, rows_for("x", {}), rater="second", pair=["before", "control"])
        self.assertEqual(res["pair"], ("before", "control"))

    def test_the_command_exits_2_with_the_reason(self):
        out = self.run_tool("score", self.write_decl(declaration()), self.write_sheet(rows_for("x", {})[1:]))
        self.assertEqual(out.returncode, 2)
        self.assertIn("Missing 1 cells", out.stderr)
        self.assertEqual(out.stdout, "")


class Agreement(Bed):
    def setUp(self):
        super().setUp()
        holds = [{"id": "trial-token", "reason": "a reserved owner act", "critical": True, "criteria": ["U2"]}]
        self.decl = self.write_decl(declaration(outcomes=("interview-trial",), assessors=("cx-1", "second"),
                                                holds=holds))
        self.a = self.write_sheet(rows_for("interview-trial", INTERVIEW), "a.csv")

    def agree(self, rows_b):
        decl = cq.read_declaration(self.decl)
        a = cq.assess(decl, self.a, "cx-1")
        b = cq.assess(decl, self.write_sheet(rows_b, "b.csv"), "second")
        return cq.agreement(a, b)

    def test_identical_worksheets_agree_on_every_cell(self):
        agr = self.agree(rows_for("interview-trial", INTERVIEW))
        self.assertEqual(agr["totals"]["agree"], 24)
        self.assertEqual(agr["totals"]["cells"], 24)
        self.assertEqual(agr["totals"]["both_known"], 22)
        self.assertEqual(agr["totals"]["movement_agree"], 11)
        self.assertEqual(agr["disagreements"], [])

    def test_a_disagreement_is_reported_by_cell_and_criterion_with_its_hold(self):
        other = dict(INTERVIEW, U2=("0", "2"), D3=("1", "1"), S3=("2", "2"))
        agr = self.agree(rows_for("interview-trial", other))
        t = agr["totals"]
        self.assertEqual((t["agree"], t["cells"]), (19, 24))
        self.assertEqual((t["known_agree"], t["both_known"], t["known_within_one"]), (19, 22, 22))
        self.assertEqual(t["one_unknown"], 2)
        self.assertEqual((t["movement_agree"], t["movement_compared"]), (11, 11))
        self.assertEqual(agr["by_criterion"]["S3"], {"cells": 2, "agree": 0})
        self.assertEqual(agr["by_criterion"]["U2"], {"cells": 2, "agree": 1})
        u2 = [r for r in agr["disagreements"] if r["criterion"] == "U2"]
        self.assertEqual(u2, [{"outcome": "interview-trial", "criterion": "U2", "side": "after", "cx-1": 1,
                               "second": 2, "holds": ["trial-token"]}])
        out = self.run_tool("agree", self.decl, self.a, self.write_sheet(rows_for("interview-trial", other), "b.csv"))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Cells agreeing: 19/24", out.stdout)
        self.assertIn("interview-trial U2 after: cx-1 1, second 2  affects hold trial-token", out.stdout)
        self.assertIn("interview-trial D3 before: cx-1 ?, second 1", out.stdout)

    def test_movement_in_opposite_directions_is_counted(self):
        agr = self.agree(rows_for("interview-trial", dict(INTERVIEW, U1=("1", "0", "regression"))))
        self.assertEqual((agr["totals"]["movement_agree"], agr["totals"]["movement_compared"]), (10, 11))

    def test_same_rater_or_different_declaration_is_refused(self):
        decl = cq.read_declaration(self.decl)
        a = cq.assess(decl, self.a, "cx-1")
        with self.assertRaises(cq.Refusal):
            cq.agreement(a, cq.assess(decl, self.a, "cx-1"))
        other = cq.read_declaration(self.write_decl(declaration(outcomes=("interview-trial",),
                                                                assessors=("cx-1", "second")), "other.json"))
        with self.assertRaises(cq.Refusal):
            cq.agreement(a, cq.assess(other, self.a, "second"))
        with self.assertRaises(cq.Refusal):
            cq.agreement(a, cq.assess(decl, self.a, "second", ["before", "control"]))


class JsonOutput(Bed):
    def test_the_serialized_assessment_carries_the_proposal_fields(self):
        holds = [{"id": "trial-token", "reason": "a reserved owner act", "critical": True, "criteria": ["U2"]},
                 {"id": "participants", "reason": "availability unknown", "critical": False}]
        decl = self.write_decl(declaration(outcomes=("interview-trial",), assessors=("cx-1",), holds=holds,
                                           settings={"delegate_level": "none"}))
        sheet = self.write_sheet(rows_for("interview-trial", INTERVIEW))
        out = self.run_tool("score", decl, sheet, "--json")
        self.assertEqual(out.returncode, 0, out.stderr)
        data = json.loads(out.stdout)
        for key in ("schema", "rubric", "project", "horizon", "scope", "outcomes", "criteria", "evidence_cutoff",
                    "rater", "settings", "snapshots", "inputs", "holds", "critical_holds", "scores",
                    "demonstrated_delta", "changes", "cells"):
            self.assertIn(key, data)
        self.assertEqual(data["schema"], "charter-quality/1")
        self.assertEqual(data["outcomes"], [{"id": "interview-trial", "home": "rails.md#interview-trial"}])
        self.assertEqual(data["snapshots"]["after"]["sources"][0]["sha256"], "bb" * 32)
        self.assertEqual(data["critical_holds"], 1)
        self.assertEqual(len(data["cells"]), 12)
        d3 = next(c for c in data["cells"] if c["criterion"] == "D3")
        self.assertEqual(d3["state"], {"before": "unknown", "after": "unknown"})
        self.assertEqual(d3["evidence"], "placeholder evidence for D3")  # the reason for the unknown
        u2 = next(c for c in data["cells"] if c["criterion"] == "U2")
        self.assertEqual((u2["before"], u2["after"], u2["reason"], u2["holds"]), ("0", "1", "repaired-artifact",
                                                                                  ["trial-token"]))
        self.assertAlmostEqual(data["scores"]["before"]["overall"]["lower"], 62.5)
        self.assertAlmostEqual(data["scores"]["after"]["overall"]["upper"], 79.1666666, places=5)
        self.assertAlmostEqual(data["scores"]["after"]["overall"]["coverage"], 91.6666666, places=5)
        self.assertAlmostEqual(data["demonstrated_delta"], 8.3333333, places=5)
        self.assertEqual(data["scores"]["after"]["outcomes_inspected"], 1)
        self.assertEqual(len(data["inputs"]["declaration_sha256"]), 64)
        self.assertEqual(len(data["inputs"]["worksheet_sha256"]), 64)
        # Same inputs, same output: nothing time-dependent is serialized.
        self.assertEqual(self.run_tool("score", decl, sheet, "--json").stdout, out.stdout)

    def test_redacted_evidence_keeps_a_digest(self):
        decl = self.write_decl(declaration())
        out = self.run_tool("score", decl, self.write_sheet(rows_for("x", {})), "--json", "--redact-evidence")
        data = json.loads(out.stdout)
        self.assertTrue(all(c["evidence"].startswith("sha256:") for c in data["cells"]))
        self.assertTrue(data["inputs"]["evidence_redacted"])

    def test_agreement_json(self):
        decl = self.write_decl(declaration(assessors=("one", "two")))
        a = self.write_sheet(rows_for("x", {}), "a.csv")
        b = self.write_sheet(rows_for("x", {"R1": ("1", "1")}), "b.csv")
        data = json.loads(self.run_tool("agree", decl, a, b, "--json").stdout)
        self.assertEqual(data["raters"], ["one", "two"])
        self.assertEqual(data["disagreements"][0] | {}, {"outcome": "x", "criterion": "R1", "side": "before",
                                                         "one": "2", "two": "1", "holds": []})
        self.assertEqual(data["totals"]["agree"], 22)
        self.assertEqual(data["assessments"]["two"]["after"]["families"]["Rail"]["lower"], 250 / 3)


class Surfaces(Bed):
    def test_help_exits_0(self):
        for args in (["--help"], ["score", "--help"], ["agree", "--help"]):
            self.assertEqual(self.run_tool(*args).returncode, 0, args)

    def test_the_blank_declaration_and_worksheet_are_valid_input(self):
        res = cq.assess(cq.read_declaration(BLANK_DECLARATION), BLANK)
        self.assertEqual(project(res, "before"), (0, 100, 0))
        out = self.run_tool("score", BLANK_DECLARATION, BLANK)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Overall   0.0–100.0 (0.0% coverage) → 0.0–100.0 (0.0% coverage)   +0.0", out.stdout)

    def test_the_proposal_names_the_tool_and_not_the_old_script(self):
        text = (REPO / "docs" / "proposals" / "assess-charter-quality.md").read_text(encoding="utf-8")
        self.assertTrue("bin/charter_quality.py" in text)
        self.assertFalse("score-charter-pair" in text)
        self.assertFalse((REPO / "docs" / "proposals" / "score-charter-pair.py").exists())


if __name__ == "__main__":
    unittest.main()
