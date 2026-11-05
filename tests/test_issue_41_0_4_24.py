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
