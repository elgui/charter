"""Charter 0.4.23 (built as 0.4.9 on the unreleased branch decision-read-and-gated-evidence, ported onto main): a decision names the doc that says how to follow it (`read:`), and can require evidence from any unit whose
perimeter touches given paths (`gate_paths:` + `gate_evidence:`); a unit that cannot meet it says so with `waives:`.
`charter anchors` no longer passes a missing file. Motivated by tele-claude's dev-sandbox review (its
docs/DEV_SANDBOX_REVIEW_20261001.md): nothing pointed sessions at the sandbox's doc, a unit that touched runtime code closed
with no proof unless its author remembered to add the probe by hand, and `charter anchors <missing>` read an empty stdin,
found 0 claims and passed. Every test here fails on 0.4.22 except the ones marked (guard).
A half-set or invalid gate fails closed: the done gate refuses the units it would have judged."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from helpers import PKG, charter, cleanup, make_project, run_hook  # noqa: E402
from test_gates import write_call  # noqa: E402
from test_review_regressions import commit_all, decision, done_unit  # noqa: E402

sys.path.insert(0, str(PKG / ".charter"))
import lib  # noqa: E402

GATED = """---
id: prove-first
title: Changes under app/ are proven before they ship
status: active
date: 2026-10-01
owner: Test Owner
kind: design
read: [docs/PROVE.md]
gate_paths: [app/**]
gate_evidence: "prove\\.sh --unit .*exit 0"
expires: 2027-03-01
---

## Decision

Prove first.

## Because

A change shipped unproven.

## Stops applying when

Never.
"""


def gated_done(evidence, waives=""):
    text = done_unit(evidence)
    if waives:
        text = text.replace("kind: work\n", f"kind: work\nwaives: [{waives}]\n", 1)
    return text


class GlobsOverlap(unittest.TestCase):
    def test_literal_inside_glob(self):
        self.assertTrue(lib.globs_overlap("services/main.py", "services/**"))
        self.assertTrue(lib.globs_overlap("services/**", "services/main.py"))

    def test_nested_globs(self):
        self.assertTrue(lib.globs_overlap("services/detect/**", "services/**"))
        self.assertTrue(lib.globs_overlap("**", "services/**"))

    def test_disjoint(self):
        self.assertFalse(lib.globs_overlap("docs/**", "services/**"))
        self.assertFalse(lib.globs_overlap("tests/test_x.py", "services/**"))
        self.assertFalse(lib.globs_overlap("requirements.txt", "requirements-dev.txt"))


class Base(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def add_gate(self, with_doc=True):
        (self.root / "charter" / "decisions" / "prove-first.md").write_text(GATED)
        if with_doc:
            (self.root / "docs").mkdir(exist_ok=True)
            (self.root / "docs" / "PROVE.md").write_text("# Prove\n\nRun prove.sh.\n")
        commit_all(self.root, "gate")

    def gate(self, text):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", text))
        return decision(out), so + se


class EvidenceGate(Base):
    def test_gated_unit_without_the_evidence_is_refused(self):
        self.add_gate()
        d, out = self.gate(gated_done("- `$ make test` → exit 0"))
        self.assertEqual(d, "deny", out)
        self.assertIn("prove-first", out)
        self.assertIn("docs/PROVE.md", out)

    def test_gated_unit_with_the_evidence_passes(self):
        self.add_gate()
        d, out = self.gate(gated_done("- `$ make test` → exit 0\n- `$ prove.sh --unit u1` → exit 0"))
        self.assertNotEqual(d, "deny", out)

    def test_waiver_passes_with_a_warning(self):
        self.add_gate()
        text = gated_done("- `$ make test` → exit 0", waives="prove-first")
        d, out = self.gate(text)
        self.assertNotEqual(d, "deny", out)
        (self.root / ".taskets" / "u1.md").write_text(text.replace("status: done", "status: next"))
        r = charter(self.root, "unit", "start", "u1")
        self.assertIn("waived", r.stdout)

    def test_unit_outside_the_paths_is_not_gated(self):
        """(guard) a unit whose perimeter misses gate_paths closes as before"""
        self.add_gate()
        text = gated_done("- `$ make test` → exit 0").replace("perimeter: [app/health.py, tests/**]", "perimeter: [tests/**]")
        self.assertNotEqual(self.gate(text)[0], "deny")

    def test_no_gate_fields_no_change(self):
        """(guard) a project without gate fields behaves as before"""
        self.assertNotEqual(self.gate(gated_done("- `$ make test` → exit 0"))[0], "deny")

    def test_unit_start_names_the_gate(self):
        self.add_gate()
        r = charter(self.root, "unit", "start", "u1")
        self.assertIn("gated by decision `prove-first`", r.stdout)
        self.assertIn("docs/PROVE.md", r.stdout)


class FailsClosed(Base):
    def write_gate(self, text):
        (self.root / "charter" / "decisions" / "prove-first.md").write_text(text)
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs" / "PROVE.md").write_text("# Prove\n")
        commit_all(self.root, "gate")

    def test_gate_paths_without_evidence_refuses_done(self):
        self.write_gate(GATED.replace('gate_evidence: "prove\\.sh --unit .*exit 0"\n', ""))
        d, out = self.gate(gated_done("- `$ make test` → exit 0\n- `$ prove.sh --unit u1` → exit 0"))
        self.assertEqual(d, "deny", out)
        self.assertIn("no `gate_evidence:`", out)
        r = charter(self.root, "check", "--all")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("decision `prove-first` has `gate_paths:` but no `gate_evidence:`", r.stdout)

    def test_invalid_regex_refuses_done(self):
        self.write_gate(GATED.replace('"prove\\.sh --unit .*exit 0"', '"prove(.sh"'))
        d, out = self.gate(gated_done("- `$ make test` → exit 0\n- `$ prove(.sh --unit u1` → exit 0"))
        self.assertEqual(d, "deny", out)
        self.assertIn("not a valid regular expression", out)

    def test_waiver_still_passes_a_broken_gate(self):
        """(guard) a waiver excuses the unit whatever the gate's state"""
        self.write_gate(GATED.replace('gate_evidence: "prove\\.sh --unit .*exit 0"\n', ""))
        self.assertNotEqual(self.gate(gated_done("- `$ make test` → exit 0", waives="prove-first"))[0], "deny")


class TeleClaudeShape(Base):
    """The fields as tele-claude's dev-sandbox-before-production-20261001 writes them, and its planned
    docs/owner-patches/20261001-decision-gate-on.patch."""
    DEC = GATED.replace("gate_paths: [app/**]", "gate_paths: [services/**, config/**, requirements.txt, dashboard/src/**, mini-app/src/**]").replace(
        '"prove\\.sh --unit .*exit 0"', '"scripts/sandbox.sh verdict --unit .*exit 0"').replace(
        "read: [docs/PROVE.md]", "read: [docs/PROVE.md]  # a trailing comment, as tele-claude carries on its comment lines")

    def setUp(self):
        super().setUp()
        (self.root / "charter" / "decisions" / "prove-first.md").write_text(self.DEC)
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs" / "PROVE.md").write_text("# Prove\n")
        commit_all(self.root, "gate")

    def unit(self, perimeter, evidence):
        return gated_done(evidence).replace("perimeter: [app/health.py, tests/**]", f"perimeter: [{perimeter}]")

    def test_literal_gate_path(self):
        self.assertEqual(self.gate(self.unit("requirements.txt", "- `$ make test` → exit 0"))[0], "deny")

    def test_sandbox_verdict_passes(self):
        ok = "- `$ make test` → exit 0\n- `$ scripts/sandbox.sh verdict --unit u1` → exit 0"
        self.assertNotEqual(self.gate(self.unit("services/main.py", ok))[0], "deny")

    def test_docs_only_unit_is_not_gated(self):
        """(guard)"""
        self.assertNotEqual(self.gate(self.unit("docs/**", "- `$ make test` → exit 0"))[0], "deny")


class GateFieldsAreTheOwners(Base):
    def test_agent_cannot_drop_the_gate_of_an_active_decision(self):
        self.add_gate()
        text = GATED.replace("gate_paths: [app/**]\n", "")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/decisions/prove-first.md", text))
        self.assertEqual(decision(out), "deny", so + se)
        self.assertIn("gate_paths", so + se)

    def test_agent_cannot_loosen_the_evidence(self):
        self.add_gate()
        text = GATED.replace('"prove\\.sh --unit .*exit 0"', '".*"')
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/decisions/prove-first.md", text))
        self.assertEqual(decision(out), "deny", so + se)
        self.assertIn("gate_evidence", so + se)

    def test_agent_may_edit_a_proposed_decision_gate(self):
        """(guard) only an active decision's gate is the owner's"""
        self.add_gate()
        prop = GATED.replace("status: active", "status: proposed")
        (self.root / "charter" / "decisions" / "prove-first.md").write_text(prop)
        commit_all(self.root, "proposed")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/decisions/prove-first.md",
                                                                          prop.replace("gate_paths: [app/**]\n", "")))
        self.assertNotEqual(decision(out), "deny", so + se)


class ReadPointer(Base):
    def test_banner_points_at_the_doc(self):
        self.add_gate()
        rc, out, so, se = run_hook(self.root, "session_start", {})
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("Read before working here", ctx)
        self.assertIn("docs/PROVE.md (prove-first)", ctx)
        self.assertIn("docs/PROVE.md", out.get("systemMessage", ""))

    def test_missing_doc_is_refused_by_check(self):
        self.add_gate(with_doc=False)
        r = charter(self.root, "check", "--all")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("points sessions at docs/PROVE.md, which does not exist", r.stdout)

    def test_present_doc_passes_check(self):
        """(guard)"""
        self.add_gate()
        r = charter(self.root, "check", "--all")
        self.assertNotIn("points sessions at", r.stdout)


class AnchorsMissingFile(Base):
    def test_missing_file_fails(self):
        r = charter(self.root, "anchors", "docs/NO_SUCH_FILE.md")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("no such file", r.stdout)

    def test_dash_reads_stdin(self):
        """(guard) `-` still reads stdin"""
        import subprocess
        from helpers import clean_env
        r = subprocess.run([sys.executable, str(self.root / ".charter" / "bin" / "charter"), "anchors", "-"], cwd=self.root,
                           input="# Notes\n", capture_output=True, text=True, env=clean_env())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_strict_fails_on_prototype(self):
        cfg = json.loads((self.root / "charter" / "config.json").read_text())
        cfg["track"] = "prototype"
        (self.root / "charter" / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs" / "report.md").write_text("# Report\n\nThe service answers in 40 ms on every route we measured.\n")
        self.assertEqual(charter(self.root, "anchors", "docs/report.md").returncode, 0)
        self.assertEqual(charter(self.root, "anchors", "--strict", "docs/report.md").returncode, 1)



class ReviewOf43(Base):
    """/reviewPR #43, pass B and pass A (gpt-6.1-sol)."""

    def test_a_regex_that_overflows_refuses_done(self):
        (self.root / "charter" / "decisions" / "prove-first.md").write_text(
            GATED.replace('"prove\\.sh --unit .*exit 0"', '"x{4294967295}"'))
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs" / "PROVE.md").write_text("# Prove\n")
        commit_all(self.root, "gate")
        d, out = self.gate(gated_done("- `$ make test` → exit 0"))
        self.assertEqual(d, "deny", out)
        self.assertIn("not a valid regular expression", out)

    def test_a_directory_is_not_a_doc_to_read(self):
        self.add_gate(with_doc=False)
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs" / "PROVE.md").mkdir()
        (self.root / "docs" / "PROVE.md" / "x.txt").write_text("x\n")
        commit_all(self.root, "a directory where the doc should be")
        r = charter(self.root, "check", "--all")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("points sessions at docs/PROVE.md, which does not exist", r.stdout)

    def test_at_commit_the_index_decides_not_the_working_tree(self):
        import subprocess
        self.add_gate()
        subprocess.run(["git", "rm", "-q", "--cached", "docs/PROVE.md"], cwd=self.root, check=True)
        self.assertTrue((self.root / "docs" / "PROVE.md").is_file())
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("points sessions at docs/PROVE.md, which does not exist", r.stdout)


if __name__ == "__main__":
    unittest.main()
