"""Regression tests for batch 1 of the 2026-09-12 harmonization: changes 6, 7, 10, 11 and 12 of the ranked
table in docs/review/2026-09-12-astra-harmonization.md. One class per change. Every test fails on the
package at 7ece80d and passes once the change is made, except `EnginesSeam.test_a_tasket_without_charter_keys_closes_on_its_body`,
which guards the behaviour the seam note documents and so passes on 7ece80d too."""
import datetime as dt
import re
import sys
import unittest

from helpers import REPO, PKG, UNIT, charter, git
from test_review_regressions import Base, commit_all

sys.path.insert(0, str(PKG / ".charter"))
import checks  # noqa: E402
import lib  # noqa: E402

RULES = ".claude/rules/charter.md"


def decision(did, date, expires):
    return (f"---\nid: {did}\ntitle: {did}\nstatus: active\ndate: {date}\nowner: Test Owner\nkind: design\nexpires: {expires}\n---\n\n"
            "## Decision\n\nKept.\n\n## Because\n\nMeasured.\n")


def section(text, heading):
    """The body of a `## heading` or `### heading` up to the next heading of any level."""
    m = re.search(rf"^#+ {re.escape(heading)}\n(.*?)(?=^#+ |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- change 10

class ExclusiveExpiry(Base):
    """C6: a decision counted as expired only from the day after its `expires:` date; tcv2's `expires_on` is exclusive."""

    def memory(self):
        return charter(self.root, "check", "--all", "--memory").stdout

    def test_a_decision_expiring_today_is_expired_and_one_expiring_tomorrow_is_not(self):
        today = dt.date.today()
        tomorrow = today + dt.timedelta(days=1)
        decs = self.root / "charter" / "decisions"
        (decs / "ends-today.md").write_text(decision("ends-today", "2026-01-01", today.isoformat()))
        (decs / "ends-tomorrow.md").write_text(decision("ends-tomorrow", "2026-01-01", tomorrow.isoformat()))
        out = self.memory()
        self.assertIn(f"`ends-today` expired on {today.isoformat()}", out)
        self.assertNotIn("ends-tomorrow", out)

    def test_an_expiry_not_later_than_the_date_warns(self):
        decs = self.root / "charter" / "decisions"
        (decs / "inverted.md").write_text(decision("inverted", "2099-01-02", "2099-01-01"))
        (decs / "same-day.md").write_text(decision("same-day", "2099-01-01", "2099-01-01"))
        (decs / "in-words.md").write_text(decision("in-words", "2099-01-01", "when the rate limit is lifted"))
        out = self.memory()
        self.assertIn("`inverted` expires on 2099-01-01, not later than its date 2099-01-02", out)
        self.assertIn("`same-day` expires on 2099-01-01, not later than its date 2099-01-01", out)
        self.assertNotIn("in-words", out)
        self.assertNotIn("retry-limit", out)   # the fixture: 2026-09-11 to 2027-03-01

    def test_the_decision_template_says_expiry_is_exclusive(self):
        fm = (PKG / "charter" / "templates" / "decision.md").read_text().split("---")[1]
        comments = [line for line in fm.splitlines() if line.startswith("# expires:")]
        self.assertEqual(len(comments), 1, fm)
        self.assertIn("exclusive", comments[0])
        self.assertIn("later than `date:`", comments[0])


# ---------------------------------------------------------------- change 11

class EvidenceClasses(Base):
    """E-5 L20: tcv2 types sources as measured, operator_report, vendor and inference; charter admitted neither of the last two."""

    def anchors(self, claim):
        (self.root / "docs").mkdir(exist_ok=True)
        f = self.root / "docs" / "report-classes.md"
        f.write_text(f"# Report\n\n{claim}\n")
        return charter(self.root, "anchors", str(f))

    def test_an_operator_report_is_admitted(self):
        for marker in ("(operator report: the owner, 2026-09-12)", "(operator_report: the owner, 2026-09-12)"):
            r = self.anchors(f"The staging box trails production by two Dokku minor versions {marker}.")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("1 admitted", r.stdout)

    def test_an_inference_is_admitted(self):
        r = self.anchors("The subagent share is larger on review units than on build units (inference from two ledgers).")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("1 admitted", r.stdout)

    def test_the_gates_doc_lists_only_markers_the_code_admits(self):
        line = next((l for l in (REPO / "docs" / "gates.md").read_text().splitlines() if l.startswith("- Command: `charter anchors")), "")
        markers = re.findall(r"`(\([^`]*\))`", line)
        self.assertIn("(operator report ...)", markers)
        self.assertIn("(inference ...)", markers)
        for m in markers:
            self.assertIsNotNone(checks.ADMIT_RE.fullmatch(m.replace("...", "x")), m)

    def test_the_method_maps_the_four_classes_to_tcv2(self):
        table = section((REPO / "docs" / "method.md").read_text(), "Evidence classes")
        rows = {r.split("|")[1].strip(): r for r in table.splitlines() if r.startswith("| ") and not r.startswith("| Class")}
        self.assertEqual(set(rows), {"measured", "vendor", "reported", "inference"})
        self.assertIn("`operator_report`", rows["reported"])
        self.assertIn("(operator report ...)", rows["reported"])
        self.assertIn("(inference ...)", rows["inference"])


# ---------------------------------------------------------------- change 6

COMMITMENTS = ["what is sold", "price", "dates", "deployment", "production data or schema", "purchase or budget",
               "public release", "another person's work", "widening a permission", "merging into main"]


class Commitments(Base):
    """E-2 L51-54: R7 named only commercial commitments; a solo developer's riskiest ones are operational."""

    def test_the_installed_rules_file_lists_every_commitment(self):
        line = next((l for l in (self.root / RULES).read_text().splitlines() if "A commitment is" in l), "")
        for c in COMMITMENTS:
            self.assertIn(c, line)

    def test_the_method_states_the_same_list_in_r7(self):
        row = next((l for l in (REPO / "docs" / "method.md").read_text().splitlines() if l.startswith("| R7 |")), "")
        for c in COMMITMENTS:
            self.assertIn(c, row)


# ---------------------------------------------------------------- change 7

class Subagents(Base):
    """R12 promised guidance in the rules file that it did not hold; the reviewer was called read-only while keeping Bash (E-9 L24)."""

    def test_the_installed_rules_file_says_subagents_read_and_the_parent_writes(self):
        body = section((self.root / RULES).read_text(), "Subagents")
        self.assertIn("Subagents read; the parent writes.", body)
        self.assertIn("A subagent that can run Bash is not read-only", body)

    def test_the_reviewer_description_matches_its_tools(self):
        fields, _, _ = lib.split_frontmatter((self.root / ".claude" / "agents" / "charter-reviewer.md").read_text())
        tools = [t.strip() for t in str(fields["tools"]).split(",")]
        self.assertIn("Bash", tools)
        self.assertNotIn("Edit", tools)
        self.assertNotIn("Write", tools)
        desc = str(fields["description"])
        self.assertNotRegex(desc.replace("not read-only", ""), r"(?i)read-only")
        self.assertIn("no Edit or Write", desc)


# ---------------------------------------------------------------- change 12

class EnginesSeam(Base):
    """Trial rows 5 and 6: tcv2's single frontmatter writer cannot set charter's keys; the body sections carry the gate."""

    def test_the_seam_names_the_single_writer_case(self):
        engines = next((p for p in (REPO / "docs" / "method.md").read_text().split("\n\n") if "single frontmatter writer" in p), "")
        for needle in ("tasket_ops", "optional", "`## Acceptance`", "`## Evidence`", "`## Log`", "trial row 5", "trial row 6",
                       "to be implemented in tcv2"):
            self.assertIn(needle, engines)

    def test_a_tasket_without_charter_keys_closes_on_its_body(self):
        head = "---\nid: t2\ntitle: tcv2-shaped unit\nstatus: next\npriority: p2\n---\n"
        body = UNIT.split("---\n", 2)[2]
        (self.root / ".taskets" / "t2.md").write_text(head + body)
        commit_all(self.root, "a unit with no scope, perimeter, decisions or kind")
        (self.root / ".taskets" / "t2.md").write_text(head.replace("status: next", "status: done") + body.replace("- [ ] AC-1", "- [x] AC-1"))
        git(self.root, "add", ".taskets/t2.md")
        refused = git(self.root, "commit", "-q", "-m", "done without evidence", check=False)
        self.assertNotEqual(refused.returncode, 0, refused.stdout + refused.stderr)
        self.assertIn("charter/done block [.taskets/t2.md]", refused.stderr)
        done = head.replace("status: next", "status: done") + body.replace("- [ ] AC-1", "- [x] AC-1").replace(
            "## Evidence\n", f"## Evidence\n\n- {self.sha()} landed the endpoint\n")
        (self.root / ".taskets" / "t2.md").write_text(done)
        git(self.root, "add", ".taskets/t2.md")
        r = git(self.root, "commit", "-q", "-m", "done with evidence", check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
