"""Regression for issue #39, reproduced on cfa1071."""
import json
import os
import signal
import sys
import time
import unittest
from pathlib import Path
from unittest import mock
from helpers import PKG, REPO, make_project, cleanup, charter, git, UNIT
from test_review_regressions import commit_all, set_config
sys.path.insert(0, str(PKG / ".charter"))
import checks
import lib
import owner

class ProbeCredentials(unittest.TestCase):
    def test_secrets_are_masked_before_tails_and_evidence_are_built(self):
        import shlex
        root = make_project()
        self.addCleanup(cleanup, root)
        # Synthetic shapes only; never a real credential.
        secret = "gh" + "p_" + "A" * 36
        script = "import sys; print(sys.argv[1]); print(sys.argv[1], file=sys.stderr); sys.exit(1)"
        cmd = " ".join(map(shlex.quote, [sys.executable, "-c", script, secret]))
        rec, tail = checks.probe_record(root, "AC-1", cmd, 2)
        for value in (rec["stdout_tail"], rec["stderr_tail"], tail, rec["command"]):
            self.assertNotIn(secret, value)
        self.assertIn("REDACTED", rec["stdout_tail"])
        import re
        text = re.sub(r"probe: `[^`]*`", lambda _: "probe: `" + cmd + "`", UNIT)
        findings, lines, records = checks.run_probes_recorded(root, text, "u1.md", 2)
        self.assertNotIn(secret, str((findings, lines, records)))

