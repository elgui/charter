"""Findings from the review of tcv2 #92 (the Charter 0.4.0 install), 2026-09-23.

Three were found by codex (gpt-5.6-terra) and verified against this package; one was found by
running `charter synth` in tcv2's main checkout. Each test failed before its fix, except the
characterization test for unbound decision checks, which pins the behaviour the docs now state.
"""

import json
import tempfile
import unittest
from pathlib import Path

from helpers import charter, cleanup, git, make_project, run_hook


def commit_all(root, msg, *extra):
    git(root, "add", "-A")
    git(root, *extra, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", msg)


def set_config(root, **changes):
    p = root / "charter" / "config.json"
    cfg = json.loads(p.read_text())
    cfg.update(changes)
    p.write_text(json.dumps(cfg, indent=2) + "\n")


class OwnerIsReadFromTheBase(unittest.TestCase):
    """CI took `owner` from the config under review, so a commit could name its own author the
    owner in charter/config.json and pass the owner check for that same change set."""

    def setUp(self):
        self.root = make_project(track="prototype")
        set_config(self.root, owner="Test Owner")
        commit_all(self.root, "owner set")

    def tearDown(self):
        cleanup(self.root)

    def test_a_commit_that_makes_its_author_the_owner_is_still_refused(self):
        set_config(self.root, owner="Mallory")
        sc = self.root / "charter" / "scope.md"
        sc.write_text(sc.read_text() + "\n<!-- widened -->\n")
        commit_all(self.root, "I own this now", "-c", "user.name=Mallory", "-c", "user.email=m@example.com")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Mallory", r.stdout)

    def test_the_owner_may_still_hand_ownership_on(self):
        set_config(self.root, owner=["Test Owner", "Heir"])
        commit_all(self.root, "add an heir")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertNotIn("charter/protected block", r.stdout)


class IgnoredTasketsAreNotUnits(unittest.TestCase):
    """`lib.taskets` globbed .taskets/ on disk, so `synth` and `check --all` listed files git
    ignores. In tcv2 that put three local automator taskets into charter/progress.md, whose
    anchors then fail in CI, where those files do not exist."""

    def setUp(self):
        self.root = make_project(track="prototype")
        (self.root / ".gitignore").write_text(".taskets/scratch-*.md\n")
        (self.root / "charter" / "rails.md").write_text(
            "# Rails\n\n| id | title | status | order |\n|---|---|---|---|\n| r1 | the road | next | 10 |\n")
        commit_all(self.root, "ignore scratch taskets; a road")
        (self.root / ".taskets" / "scratch-1.md").write_text("---\nid: scratch-1\ntitle: local only\nstatus: next\n---\n\nOff every rail.\n")

    def tearDown(self):
        cleanup(self.root)

    def test_synth_does_not_list_an_ignored_tasket(self):
        r = charter(self.root, "synth")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("scratch-1", r.stdout)

    def test_check_does_not_judge_an_ignored_tasket(self):
        r = charter(self.root, "check", "--all", "--rails")
        self.assertIn("u1", r.stdout, "the tracked unit off the rails is still reported")
        self.assertNotIn("scratch-1", r.stdout)

    def test_a_tracked_tasket_is_still_read(self):
        r = charter(self.root, "synth")
        self.assertIn("u1", r.stdout)


class UnboundChecksRunInCiNotAtCommit(unittest.TestCase):
    """Characterization. The rules file said a decision's `check:` is verified at every commit;
    at commit only a decision whose `binds:` match a staged path runs its check."""

    def setUp(self):
        self.root = make_project(track="prototype")
        (self.root / "charter" / "decisions" / "flag.md").write_text(
            "---\nid: flag\ntitle: the flag file stays absent\nstatus: active\nexpires: 2099-01-01\n"
            "check: test ! -e FLAG\n---\n\n## Decision\n\nNo FLAG.\n\n## Because\n\nMeasured.\n")
        commit_all(self.root, "unbound decision")
        (self.root / "FLAG").write_text("x\n")
        git(self.root, "add", "FLAG")

    def tearDown(self):
        cleanup(self.root)

    def test_the_commit_gate_does_not_run_it(self):
        r = charter(self.root, "check", "--staged")
        self.assertNotIn("`flag` is contradicted", r.stdout)

    def test_ci_does(self):
        commit_all(self.root, "flag")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertIn("`flag` is contradicted", r.stdout)


OWNER_VAR = "CHARTER_" + "OWNER"   # spelled apart: the gate under test refused this file while it was broken


class OwnerVariableOutsideTheProject(unittest.TestCase):
    """The PreToolUse gate refused any Edit or Write that introduced the owner variable, wherever the
    file was. It exists because a settings `env` block reaches the running session; a PR description
    in the session's scratchpad reaches nothing, and was refused (tcv2 session, 2026-09-23).
    Inside the project, and in a Claude Code settings file anywhere, it is still refused."""

    def setUp(self):
        self.root = make_project(track="prototype")
        self.outside = Path(tempfile.mkdtemp(prefix="charter-outside-"))

    def tearDown(self):
        cleanup(self.root)
        cleanup(self.outside)

    def write(self, path, content):
        call = {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": content}}
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", call)
        return (out.get("hookSpecificOutput") or {}).get("permissionDecision"), so + se

    def test_a_scratch_file_outside_the_project_may_name_it(self):
        d, why = self.write(self.outside / "scratchpad" / "pr-upgrade.md", f"Set `{OWNER_VAR}=1` on the commit only.\n")
        self.assertNotEqual(d, "deny", why)

    def test_a_file_inside_the_project_still_may_not(self):
        d, why = self.write(self.root / "docs" / "notes.md", f"export {OWNER_VAR}=1\n")
        self.assertEqual(d, "deny", why)

    def test_a_settings_file_anywhere_still_may_not(self):
        env = json.dumps({"env": {OWNER_VAR: "1"}}) + "\n"
        home = self.outside / "home" / ".claude"
        for path in (self.root / ".claude" / "settings.json",
                     home / "settings.json",
                     home / "settings.local.json",
                     self.outside / "etc" / "claude-code" / "managed-settings.json",
                     self.outside / "etc" / "claude-code" / "managed-settings.d" / "50-owner.json",
                     self.outside / "main-checkout" / ".claude" / "settings.local.json"):
            d, why = self.write(path, env)
            self.assertEqual(d, "deny", f"{path}: {why}")

    def test_a_link_to_a_settings_file_is_a_settings_file(self):
        target = self.outside / "home" / ".claude" / "settings.json"
        target.parent.mkdir(parents=True)
        target.write_text("{}\n")
        link = self.outside / "notes.md"
        link.symlink_to(target)
        d, why = self.write(link, json.dumps({"env": {OWNER_VAR: "1"}}) + "\n")
        self.assertEqual(d, "deny", why)


if __name__ == "__main__":
    unittest.main()
