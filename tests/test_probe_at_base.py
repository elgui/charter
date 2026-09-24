"""A probe must fail before the unit's work (method.md § Real tests, point 2). When probes run, each
probe of a unit that closes is also run at the parent of the commit that added the unit."""
import re
import unittest

from helpers import make_project, charter, git, cleanup, UNIT
from test_review_regressions import commit_all, set_config

NEW_PROBE = 'python3 -c "from app.ping import ping; assert ping()==1"'


def closed(text, probe):
    text = text.replace("status: next", "status: done").replace("- [ ] AC-1", "- [x] AC-1")
    text = re.sub(r"probe: `[^`]*`", lambda _: f"probe: `{probe}`", text)
    return text.replace("## Evidence\n", "## Evidence\n\n- `$ make test` → exit 0\n")


class ProbeAtBase(unittest.TestCase):
    def setUp(self):
        self.root = make_project()   # u1 is added by the install commit, after app/health.py exists

    def tearDown(self):
        cleanup(self.root)

    def close(self, probe, unit=UNIT, **probes):
        set_config(self.root, probes=dict({"in_ci": True}, **probes))
        commit_all(self.root, "probes in ci")
        (self.root / ".taskets" / "u1.md").write_text(closed(unit, probe))
        commit_all(self.root, "u1 done")
        return charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")

    def test_a_probe_that_already_passed_is_reported(self):
        r = self.close("true")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("already passes", r.stdout)

    def test_base_must_fail_refuses_it(self):
        r = self.close("true", base_must_fail=True)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("already passes", r.stdout)

    def test_a_guard_criterion_is_expected_to_pass_before(self):
        r = self.close("true", unit=UNIT.replace("- [ ] AC-1:", "- [ ] AC-1: (guard)"), base_must_fail=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("already passes", r.stdout)

    def test_a_probe_of_new_behaviour_is_not_reported(self):
        (self.root / "app" / "ping.py").write_text("def ping():\n    return 1\n")
        r = self.close(NEW_PROBE, base_must_fail=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("already passes", r.stdout)

    def test_the_base_is_before_the_unit_not_before_the_closing_commit(self):
        (self.root / "app" / "ping.py").write_text("def ping():\n    return 1\n")
        commit_all(self.root, "the work, before the unit closes")
        r = self.close(NEW_PROBE, base_must_fail=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_no_worktree_is_left_behind(self):
        self.close("true")
        self.assertEqual(len(git(self.root, "worktree", "list").stdout.splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
