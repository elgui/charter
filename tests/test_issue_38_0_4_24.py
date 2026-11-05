"""Regression for issue #38, reproduced on cfa1071."""
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

class SurveyRefAnchors(unittest.TestCase):
    def test_ref_survives_working_tree_deletion_and_rejects_worktree_only_file(self):
        sys.path.insert(0, str(REPO / "bin"))
        import charter_plan
        root = make_project()
        self.addCleanup(cleanup, root)
        git(root, "branch", "survey-ref")
        git(root, "rm", "app/health.py")
        (root / "only-here.py").write_text("x = 1\n")
        good = "- The surveyed implementation remains available (`app/health.py:6`).\n"
        bad = "- This file exists only in the working tree (`only-here.py:1`).\n"
        self.assertTrue(charter_plan.check(root, good, ref="survey-ref").ok)
        self.assertFalse(charter_plan.check(root, bad, ref="survey-ref").ok)

