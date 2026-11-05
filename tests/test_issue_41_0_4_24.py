"""Issue #41: projects choose a probe runner without inheriting a session's PATH."""
import json
import os
import shlex
import sys
import unittest
from helpers import make_project, cleanup, charter, UNIT, PKG
from test_review_regressions import set_config
sys.path.insert(0, str(PKG / ".charter"))
import lib

class ProbeRunner(unittest.TestCase):
    def test_runner_wraps_the_unchanged_shell_command(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        runner = root / "probe runner"
        runner.write_text('#!/bin/sh\nexport CHARTER_TEST_RUNNER=selected\nexec "$@"\n')
        runner.chmod(0o755)
        set_config(root, probes={"runner": ["./probe runner"]})
        import re
        cmd = 'test "$CHARTER_TEST_RUNNER" = selected'
        (root / ".taskets/u1.md").write_text(re.sub(r"probe: `[^`]*`", lambda _: "probe: `" + cmd + "`", UNIT))
        r = charter(root, "probe", "u1", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout)["probes"][0]["command"], cmd)
    def test_bad_runners_fail_closed(self):
        for value in ("python3", [""], [4], ["bad\x00path"]):
            cfg = lib.config_from({"probes": {"runner": value}})
            self.assertTrue(cfg[lib.PROBLEMS], repr(value))
        self.assertFalse(lib.config_from({"probes": {"runner": []}})[lib.PROBLEMS])
    def test_runner_location_is_retained_for_a_base_worktree(self):
        import checks
        root = make_project()
        self.addCleanup(cleanup, root)
        runner = root / "probe-env"
        runner.write_text('#!/bin/sh\nexport CHARTER_TEST_RUNNER=selected\nexec "$@"\n')
        runner.chmod(0o755)
        set_config(root, probes={"runner": ["./probe-env"]})
        import re
        text = re.sub(r"probe: `[^`]*`", 'probe: `test "$CHARTER_TEST_RUNNER" = selected`', UNIT)
        findings = checks.run_probes_at_base(root, lib.load_config(root), text, ".taskets/u1.md", 3)
        self.assertTrue(any("already passes" in f.message for f in findings), findings)
    def test_invalid_config_does_not_run_a_probe_under_the_default_environment(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        set_config(root, probes={"runner": [""]})
        import re
        (root / ".taskets/u1.md").write_text(re.sub(r"probe: `[^`]*`", 'probe: `touch should-not-run`', UNIT))
        r = charter(root, "probe", "u1")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((root / "should-not-run").exists())
