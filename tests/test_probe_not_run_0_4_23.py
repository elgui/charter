"""0.4.23: a probe that could not run is `not-run`, not `failed`. Exit 126/127, and pytest's 4/5 when the command runs
pytest, prove nothing about the change: at the unit's base they used to count as "fails before the work". Now they,
and a timeout there, are reported "could not run" (a warning, a block under `probes.base_must_fail`); the probe record
says `not-run`; the gate log rows carry the exit code. Motivation: docs/package.md § Versioning and upgrade, 0.4.23."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import make_project, charter, cleanup, UNIT
from test_probe_at_base import closed
from test_review_regressions import commit_all, set_config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "package" / ".charter"))
import checks  # noqa: E402


def log_rows(root):
    return [json.loads(l) for l in (root / ".git" / "charter" / "log.jsonl").read_text().splitlines()]


class NotRunAtBase(unittest.TestCase):
    def setUp(self):
        self.root = make_project()   # u1 is added by the install commit

    def tearDown(self):
        cleanup(self.root)

    def close(self, probe, env=None, **probes):
        set_config(self.root, probes=dict({"in_ci": True}, **probes))
        commit_all(self.root, "probes in ci")
        (self.root / ".taskets" / "u1.md").write_text(closed(UNIT, probe))
        commit_all(self.root, "u1 done")
        return charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1", env=env)

    def add_script(self):
        """A probe script the unit adds: absent at the base, so running it there exits 127."""
        f = self.root / "check.sh"
        f.write_text("#!/bin/sh\nexit 0\n")
        f.chmod(0o755)
        return "./check.sh"

    def stub_bin(self):
        """A directory put first on PATH, with a pytest that exits 4 when a named .py file is missing, as the real one
        does; no pytest is installed here."""
        d = Path(tempfile.mkdtemp(prefix="stub-pytest-"))
        self.addCleanup(shutil.rmtree, d, True)
        f = d / "pytest"
        f.write_text('#!/bin/sh\nfor a; do case "$a" in *.py) [ -f "$a" ] || exit 4;; esac; done\nexit 0\n')
        f.chmod(0o755)
        return d, {"PATH": f"{d}:{os.environ['PATH']}"}

    def add_test_file(self):
        (self.root / "tests" / "test_new.py").write_text("def test_it():\n    assert True\n")

    def test_a_script_missing_at_the_base_could_not_run_there(self):
        r = self.close(self.add_script())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("could not run", r.stdout)
        self.assertIn("exit 127", r.stdout)
        self.assertIn("probe warn", r.stdout)
        self.assertNotIn("already passes", r.stdout)

    def test_not_run_is_a_block_under_base_must_fail(self):
        r = self.close(self.add_script(), base_must_fail=True)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("probe block", r.stdout)
        self.assertIn("could not run", r.stdout)

    def test_a_pytest_file_added_in_the_unit_could_not_run_at_the_base(self):
        _, env = self.stub_bin()
        self.add_test_file()
        r = self.close("pytest -q tests/test_new.py", env=env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("could not run", r.stdout)
        self.assertIn("exit 4", r.stdout)

    def test_the_same_with_python_dash_m_pytest(self):
        d, env = self.stub_bin()
        (d / "python3").write_text('#!/bin/sh\nshift 2\nexec pytest "$@"\n')
        (d / "python3").chmod(0o755)
        self.add_test_file()
        r = self.close("python3 -m pytest -q tests/test_new.py", env=env)
        self.assertIn("could not run", r.stdout)

    def test_a_timeout_at_the_base_could_not_run_there(self):
        """It used to be skipped in silence; a probe that never finished shows no failure either."""
        (self.root / "fast").write_text("x")
        r = self.close("test -f fast || sleep 5", base_must_fail=True, timeout_s=1)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("could not run", r.stdout)
        self.assertIn("timed out after 1 s", r.stdout)

    def test_an_ordinary_failure_at_the_base_is_still_accepted(self):
        (self.root / "flag").write_text("x")
        r = self.close("test -f flag", base_must_fail=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("could not run", r.stdout)

    def test_the_check_log_row_carries_the_exit_code(self):
        self.close(self.add_script())
        self.assertIn(127, [r.get("exit") for r in log_rows(self.root) if r["gate"] == "probe"])


class NotRunRecord(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def test_the_probe_record_says_not_run(self):
        """`charter probe --json` (0.4.15) names the third outcome; the gate log row lists the exit codes."""
        (self.root / ".taskets" / "u1.md").write_text(closed(UNIT, "exit 127"))
        r = charter(self.root, "probe", "u1", "--json")
        self.assertEqual(r.returncode, 1, r.stdout)
        rec = json.loads(r.stdout)
        self.assertEqual([p["outcome"] for p in rec["probes"]], ["not-run"], r.stdout)
        self.assertEqual(rec["failed"], ["AC-1"])
        self.assertTrue(rec["findings"][0].startswith("AC-1 probe could not run"), rec["findings"])
        row = [x for x in log_rows(self.root) if x["gate"] == "probe"][-1]
        self.assertEqual((row["exits"], row["not_run"]), ({"AC-1": 127}, ["AC-1"]), row)
        self.assertIn("; not-run: AC-1", row["detail"])

    def test_the_text_form_names_it_and_keeps_the_evidence_line(self):
        """The `- `$ cmd` → exit N` line tele-claude's checker parses is unchanged; the block below it says why."""
        (self.root / ".taskets" / "u1.md").write_text(closed(UNIT, "exit 127"))
        r = charter(self.root, "probe", "u1")
        self.assertIn("- `$ exit 127` → exit 127", r.stdout)
        self.assertIn("AC-1 could not run: `exit 127` exited 127 after ", r.stdout)
        self.assertNotIn("timed out", r.stdout)

    def test_an_ordinary_failure_is_still_failed(self):
        (self.root / ".taskets" / "u1.md").write_text(closed(UNIT, "exit 1"))
        rec = json.loads(charter(self.root, "probe", "u1", "--json").stdout)
        self.assertEqual([p["outcome"] for p in rec["probes"]], ["failed"])
        row = [x for x in log_rows(self.root) if x["gate"] == "probe"][-1]
        self.assertEqual(row["exits"], {"AC-1": 1})
        self.assertNotIn("not_run", row)


class ProbeOutcome(unittest.TestCase):
    """`probe_outcome` reads the exit code and the command's words, nothing else."""

    def test_the_rule(self):
        o = checks.probe_outcome
        self.assertEqual(o("true", 0), "passed")
        self.assertEqual(o("sh -c nosuchcmd", 127), "not-run")
        self.assertEqual(o("./run.sh", 126), "not-run")
        for cmd in ("pytest -q tests/a.py", "python3 -m pytest tests/a.py", "uv run pytest -k x", ".venv/bin/pytest x",
                    "cd t && pytest", "py.test x"):
            self.assertEqual(o(cmd, 5), "not-run", cmd)
            self.assertEqual(o(cmd, 4), "not-run", cmd)
            self.assertEqual(o(cmd, 1), "failed", cmd)
        for cmd in ("make test", "python3 check.py", "grep -c pytestx f"):
            self.assertEqual(o(cmd, 5), "failed", cmd)
            self.assertEqual(o(cmd, 4), "failed", cmd)


if __name__ == "__main__":
    unittest.main()
