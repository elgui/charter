"""Charter 0.4.17: an unusable CI base no longer checks every tracked path.

A push's previous SHA is unusable after a force push (the old tip is fetched by no ref) or on the push that creates a
branch (all zeroes). Up to 0.4.16 `check --all --base <that>` then counted every tracked path as changed, so files that
were out of scope or oversized before the change set blocked it: 266 blocking on tcv2 (docs/review/findings-2026-09-23.md:32),
135 on chatboting after a `staging` prune (elgui/chatboting#131). From 0.4.17 the change set is measured from the merge
base with the main line when that is behind HEAD, else from HEAD~1, with a warning naming which; every tracked path
counts as changed only when neither exists. A change set that breaks a gate is still refused.
Every test here fails on 0.4.16 except the ones marked (guard)."""
import unittest

from helpers import charter, git
from test_review_regressions import Base, clone, commit_all

UNUSABLE = ("0" * 40, "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")


class UnusableBase(Base):
    def test_a_clean_tip_passes_on_the_main_line(self):
        # app/billing.py is out of scope and was committed before; the push itself changes nothing
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "--allow-empty", "-m", "clean push")
        for base in UNUSABLE:
            r = charter(self.root, "check", "--all", "--ci", "--base", base)
            self.assertEqual(r.returncode, 0, f"base {base}: {r.stdout}")
            self.assertIn("HEAD~1", r.stdout)
            self.assertNotIn("every tracked path", r.stdout)

    def test_a_branch_is_measured_from_its_merge_base_with_the_remote_main_line(self):
        # as on a CI runner building `staging`: origin/main is fetched, no local main exists
        c = clone(self.root)
        self.extra.append(c.parent)
        git(c, "checkout", "-q", "-b", "staging")
        git(c, "branch", "-q", "-D", "main")
        (c / "app" / "billing.py").write_text("def invoice(a):\n    return a * 7\n")
        commit_all(c, "out of scope, one commit before the tip")
        git(c, "-c", "core.hooksPath=/dev/null", "commit", "-q", "--allow-empty", "-m", "clean tip")
        for base in UNUSABLE:
            r = charter(c, "check", "--all", "--ci", "--base", base)
            self.assertEqual(r.returncode, 1, f"base {base}: {r.stdout}")   # HEAD~1 alone would miss the billing change
            self.assertIn("origin/main", r.stdout)
            self.assertIn("app/billing.py", r.stdout)

    def test_a_branch_reset_to_the_main_line_passes(self):
        # the chatboting `staging` prune: reset to origin/main, force-pushed
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "--allow-empty", "-m", "main moves on")
        c = clone(self.root)
        self.extra.append(c.parent)
        git(c, "checkout", "-q", "-b", "staging", "origin/main")
        git(c, "branch", "-q", "-D", "main")
        r = charter(c, "check", "--all", "--ci", "--base", UNUSABLE[1])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("every tracked path", r.stdout)

    def test_a_usable_base_reports_no_fallback(self):   # (guard)
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "--allow-empty", "-m", "clean push")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("not usable", r.stdout)


if __name__ == "__main__":
    unittest.main()
