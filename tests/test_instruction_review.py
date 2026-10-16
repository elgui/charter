"""The instruction-file review (bin/charter_instructions.py), asked for by the owner on 2026-10-16: a session in
tele-claude handed him a `sudo` line to paste because his global `~/.claude/CLAUDE.md` says to ask before any sudo,
and no step of a migration had read that file against charter's rules. Claude Code concatenates every instruction
file it loads and does not rank them (https://code.claude.com/docs/en/memory), so the survey, `charter-pkg
instructions` and the install now list the lines that overlap a charter rule. Every test fails before the change
(the module, the survey section, the plan decision, the verb and the install note did not exist), except
`InstallNote.test_a_project_with_no_overlap_gets_no_note`, which guards the quiet install and so passes before it too."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import INSTALLER, PKG, REPO, cleanup, git, make_project

sys.path.insert(0, str(REPO / "bin"))
import charter_instructions as ci  # noqa: E402

RULES = PKG / ".claude" / "rules" / "charter.md"

CLAUDE_MD = """# Project

Some description of a production service that mentions sudo in passing.

## Sudo Policy

**ALWAYS ask user for confirmation before running any `sudo` command.**

## Handing over

Never paste blocks; hand over ONE line that runs a script.

```
git push origin main   # inside a fence: Claude Code reads it, but it is an example, not a rule
```

See @docs/extra.md for the release rules.
"""
EXTRA = "# Release\n\nAlways push to main after every commit.\n"
NESTED = "# Sub\n\nNever create ADRs here; write decisions in this file.\n"
RULE = "---\npaths: ['app/**']\n---\n\nYou must run `git commit --no-verify` when the hook is slow.\n"
AGENTS = ("# Agents\n\n<!-- charter-section:begin -->\n## Charter method\n\nNever set CHARTER_OWNER.\n"
          "<!-- charter-section:end -->\n")
GLOBAL = "# Me\n\n## Sudo\n\nAlways ask before any sudo command.\n\n@rules-extra.md\n"
GLOBAL_IMPORT = "# More\n\nNever merge to main without asking me.\n"


def pkg(*args, env=None):
    return subprocess.run([sys.executable, "-B", str(INSTALLER), *args], capture_output=True, text=True, env=env)


def project() -> Path:
    root = make_project(with_charter=False)
    (root / "CLAUDE.md").write_text(CLAUDE_MD)
    (root / "docs").mkdir()
    (root / "docs" / "extra.md").write_text(EXTRA)
    (root / "sub").mkdir()
    (root / "sub" / "CLAUDE.md").write_text(NESTED)
    (root / ".claude" / "rules").mkdir(parents=True)
    (root / ".claude" / "rules" / "local.md").write_text(RULE)
    (root / "AGENTS.md").write_text(AGENTS)
    git(root, "add", "-A")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "instructions")
    return root


def tracked(root: Path) -> list[str]:
    return git(root, "ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines()


class TopicsFollowTheRules(unittest.TestCase):
    def test_every_topic_finds_its_charter_rule(self):
        """A topic whose phrase left the rules file would silently stop reporting."""
        found = ci.rule_lines(RULES)
        self.assertEqual(sorted(found), sorted(t[0] for t in ci.TOPICS))
        lines = RULES.read_text().splitlines()
        for tid, (n, text) in found.items():
            self.assertIn(text[:40], lines[n - 1], tid)


class ProjectFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = project()
        cls.res = ci.review(cls.root, "HEAD", tracked(cls.root), RULES)
        cls.by = {(h["path"], h["topic"]): h for h in cls.res["overlaps"]}

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.root)

    def test_reads_every_kind_of_instruction_file_and_imports(self):
        paths = {f["path"] for f in self.res["files"]}
        self.assertEqual(paths, {"CLAUDE.md", "docs/extra.md", "sub/CLAUDE.md", ".claude/rules/local.md", "AGENTS.md"})

    def test_the_sudo_rule_overlaps_twice_at_its_line(self):
        h = self.by[("CLAUDE.md", "root")]
        self.assertEqual((h["line"], h["section"]), (7, "Sudo Policy"))
        self.assertEqual(self.by[("CLAUDE.md", "ask-first")]["line"], 7)

    def test_a_description_that_names_sudo_is_not_a_rule(self):
        self.assertTrue(all(h["line"] != 3 for h in self.res["overlaps"] if h["path"] == "CLAUDE.md"))

    def test_hand_over_import_nested_and_rules_files(self):
        self.assertEqual(self.by[("CLAUDE.md", "hand-over")]["line"], 11)
        self.assertEqual(self.by[("docs/extra.md", "git-mainline")]["line"], 3)
        self.assertIn(("sub/CLAUDE.md", "decisions"), self.by)
        self.assertIn((".claude/rules/local.md", "owner-switch"), self.by)

    def test_fences_and_charters_own_section_are_skipped(self):
        self.assertTrue(all(h["line"] != 15 for h in self.res["overlaps"] if h["path"] == "CLAUDE.md"))
        self.assertFalse([h for h in self.res["overlaps"] if h["path"] == "AGENTS.md"])

    def test_each_overlap_cites_the_charter_rule_line(self):
        lines = RULES.read_text().splitlines()
        for h in self.res["overlaps"]:
            self.assertIn(h["rule"][:40], lines[h["rule_line"] - 1])


class FilesOutsideTheProject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = project()
        cls.home = Path(tempfile.mkdtemp(prefix="charter-home-")).resolve()
        (cls.home / ".claude").mkdir()
        (cls.home / ".claude" / "CLAUDE.md").write_text(GLOBAL)
        (cls.home / ".claude" / "rules-extra.md").write_text(GLOBAL_IMPORT)
        cls.env = dict(os.environ, HOME=str(cls.home))

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.root)
        cleanup(cls.home)

    def test_a_named_file_and_its_relative_import_are_read(self):
        g = str(self.home / ".claude" / "CLAUDE.md")
        res = ci.review(self.root, "HEAD", tracked(self.root), RULES, [g])
        mine = {(h["path"], h["topic"]) for h in res["overlaps"] if h["where"] == "machine"}
        self.assertIn((g, "root"), mine)
        self.assertIn((str(self.home / ".claude" / "rules-extra.md"), "git-mainline"), mine)

    def test_nothing_outside_the_project_is_read_unless_named(self):
        r = pkg("instructions", str(self.root), "--json", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        res = json.loads(r.stdout)
        self.assertFalse([f for f in res["files"] if f["where"] == "machine"])

    def test_the_survey_reports_them_and_passes_its_anchoring_check(self):
        g = str(self.home / ".claude" / "CLAUDE.md")
        rep = pkg("survey", str(self.root), "--offline", "--track", "prototype", "--no-rehearse", "--instructions", g, env=self.env)
        plan = pkg("survey", str(self.root), "--offline", "--track", "prototype", "--no-rehearse", "--plan", "--instructions", g, env=self.env)
        self.assertEqual(rep.returncode, 0, rep.stderr)
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertIn("## Instructions the sessions read", rep.stdout)
        self.assertIn(f"{g}:5", rep.stdout)
        self.assertIn("Where an instruction file and charter's rules overlap, which holds?", plan.stdout)
        self.assertIn("Resolve the instruction overlaps as D", plan.stdout)

    def test_without_them_the_report_says_what_it_did_not_read(self):
        rep = pkg("survey", str(self.root), "--offline", "--track", "prototype", "--no-rehearse", env=self.env)
        self.assertEqual(rep.returncode, 0, rep.stderr)
        self.assertIn("Files outside the project were not read", rep.stdout)
        self.assertNotIn(str(self.home), rep.stdout)


class CheckoutAheadOfTheRef(unittest.TestCase):
    """The survey reads the main line; a `path:line` would point into the checkout, which may say something else."""

    def test_a_changed_file_is_cited_through_git_show(self):
        root = project()
        try:
            (root / "CLAUDE.md").write_text("# Short\n")
            r = pkg("instructions", str(root), "--ref", "main")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("`CLAUDE.md` line 7 (`$ git show main:CLAUDE.md`)", r.stdout)
            self.assertNotIn("CLAUDE.md:7", r.stdout)
        finally:
            cleanup(root)


class InstallNote(unittest.TestCase):
    def test_install_names_the_overlaps_and_how_to_read_them(self):
        root = project()
        try:
            r = pkg("install", str(root), "--track", "prototype")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertRegex(r.stdout, r"instructions: \d+ line\(s\) in \d+ instruction file\(s\) overlap a charter rule")
            self.assertIn("--instructions ~/.claude/CLAUDE.md", r.stdout)
        finally:
            cleanup(root)

    def test_a_project_with_no_overlap_gets_no_note(self):
        root = make_project(with_charter=False)
        try:
            r = pkg("install", str(root), "--track", "prototype")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("instructions:", r.stdout)
        finally:
            cleanup(root)


if __name__ == "__main__":
    unittest.main()
