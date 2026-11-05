"""Regression for issue #40, reproduced on cfa1071."""
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

class OwnerSeparators(unittest.TestCase):
    def test_plain_terminal_segments_are_owner_acts_in_queue_and_gate(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        for sep in ("-", ";", ":", "—", "–"):
            text = UNIT.replace("## Evidence", f"- [ ] AC-2: check delivery {sep} owner: do\n\n## Evidence")
            (root / ".taskets/u1.md").write_text(text)
            items = json.loads(charter(root, "owner", "--json").stdout)
            # Owner JSON is an envelope in schema 1.
            if isinstance(items, dict): items = items["items"]
            self.assertTrue(any(x["key"] == "owner-line:u1:AC-2" and x["kind"] == "do" for x in items), sep)
            self.assertEqual(checks.owner_line_changes(text, text.replace("[ ] AC-2", "[x] AC-2")), ["AC-2"])
        for line in ("- [ ] AC-2: ask owner: do the work", "Ordinary prose; owner: do", "- [ ] AC-2: ask; owner: does the work"):
            self.assertFalse(owner.OWNER_SEG_RE.search(line), line)
    def test_bare_terminal_owner_marker_is_a_check(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        for sep in ("-", ";", ":", "—", "–"):
            text = UNIT.replace("## Evidence", f"- [ ] AC-2: check delivery {sep} owner:\n\n## Evidence")
            (root / ".taskets/u1.md").write_text(text)
            u = lib.taskets(root)["u1"]
            items = owner.owner_lines(root, "u1", u, owner.legacy_re(root, lib.load_config(root)))
            self.assertTrue(any(x["key"] == "owner-line:u1:AC-2" and x["kind"] == "check" for x in items), sep)
            self.assertEqual(checks.owner_line_changes(text, text.replace("[ ] AC-2", "[x] AC-2")), ["AC-2"])
