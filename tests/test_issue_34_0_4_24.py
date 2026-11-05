"""Regression for issue #34, reproduced on cfa1071."""
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

class DeletedOwnerFiles(unittest.TestCase):
    def test_deletions_and_both_sides_of_renames_are_gated(self):
        for rename in (False, True):
            with self.subTest(rename=rename):
                root = make_project()
                self.addCleanup(cleanup, root)
                base = git(root, "rev-parse", "HEAD").stdout.strip()
                if rename:
                    git(root, "mv", "charter/scope.md", "scope-backup.md")
                else:
                    git(root, "rm", "charter/scope.md")
                self.assertIn("charter/scope.md", checks.staged_paths(root))
                result = charter(root, "check", "--staged", "--no-probe", env={"CLAUDECODE": "1"})
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("decides what the gates enforce", result.stdout)
                commit_all(root, "remove scope for CI test")
                self.assertIn("charter/scope.md", checks.changed_paths(root, base))

