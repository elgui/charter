"""Regression for issue #19, reproduced on cfa1071."""
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

class HistoryAvailability(unittest.TestCase):
    def test_failed_history_is_not_reported_as_zero_commits(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        units = lib.taskets(root)
        real = lib.git
        def run(root, *args):
            if "log" in args:
                import subprocess
                return subprocess.CompletedProcess(args, 128, "", "unreadable")
            return real(root, *args)
        with mock.patch.object(lib, "git", side_effect=run):
            fits, seen = checks.perimeter_fits(root, units)
        self.assertIn("unavailable", checks.fit_text(fits["u1"]))
    def test_shallow_history_is_labelled(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        units = lib.taskets(root)
        real = lib.git
        def run(root, *args):
            if "--is-shallow-repository" in args:
                import subprocess
                return subprocess.CompletedProcess(args, 0, "true\n", "")
            return real(root, *args)
        with mock.patch.object(lib, "git", side_effect=run):
            fits, seen = checks.perimeter_fits(root, units)
        self.assertIn("shallow", checks.fit_text(fits["u1"]))
