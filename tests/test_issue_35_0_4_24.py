"""Regression for issue #35, reproduced on cfa1071."""
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

class ProbeChildren(unittest.TestCase):
    def test_timeout_kills_the_child_before_it_can_write(self):
        import shlex
        root = make_project()
        self.addCleanup(cleanup, root)
        script = "import time; from pathlib import Path; time.sleep(2); Path('escaped').write_text('alive')"
        cmd = shlex.quote(sys.executable) + " -c " + shlex.quote(script) + " & wait"
        rec, _ = checks.probe_record(root, "AC-1", cmd, 0.2)
        self.assertEqual(rec["outcome"], "timeout")
        time.sleep(2.2)
        self.assertFalse((root / "escaped").exists(), "probe child survived timeout")
