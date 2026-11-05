"""Regression for issue #20, reproduced on cfa1071."""
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

class SessionAttribution(unittest.TestCase):
    def test_missing_record_does_not_claim_a_session_did_not_edit(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        cfg = lib.load_config(root)
        unit = lib.taskets(root)["u1"]
        f = checks.check_perimeter(root, cfg, unit, ["app/other.py"], True, {"app/other.py": "sibling"})[0]
        self.assertNotIn("this session did not", f.message)
        self.assertIn("record does not list", f.message)
