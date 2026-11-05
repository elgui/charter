"""Regression for issue #14, reproduced on cfa1071."""
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

class PhysicalLineNumbers(unittest.TestCase):
    def test_pasted_unicode_separators_do_not_shift_acceptance(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        for char in ("\u2028", "\u2029", "\x85", "\x0c", "\x0b", "\x1c", "\x1d", "\x1e"):
            text = UNIT.replace("Client wants retries in /health.", "Pasted " + char + " text.")
            text = text.replace("## Evidence", "- [ ] AC-2: check delivery — owner: do\n\n## Evidence")
            (root / ".taskets/u1.md").write_text(text)
            out = json.loads(charter(root, "unit", "show", "u1", "--json").stdout)
            rows = out["acceptance"]
            for row in rows:
                actual = next(i for i, line in enumerate(text.split("\n"), 1) if row["label"] + ":" in line)
                self.assertEqual(row["line"], actual, repr(char))
            u = lib.taskets(root)["u1"]
            queue = owner.owner_lines(root, "u1", u, owner.legacy_re(root, lib.load_config(root)))
            self.assertEqual(queue[0]["line"], rows[1]["line"])
            self.assertIn(char, lib.section(lib.split_frontmatter(text)[2], "Context"))
