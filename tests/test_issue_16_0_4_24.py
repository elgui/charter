"""Regression for issue #16, reproduced on cfa1071."""
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

class DuplicateOwnerFields(unittest.TestCase):
    def test_ruling_updates_every_top_level_duplicate(self):
        text = "---\nid: x\nstatus: proposed\nstatus: draft\n---\n\nstatus: body stays\n"
        changed = owner.set_field(text, "status", "active")
        self.assertEqual(lib.split_frontmatter(changed)[0]["status"], "active")
        self.assertEqual(changed.count("status: active"), 2)
        self.assertIn("status: body stays", changed)
