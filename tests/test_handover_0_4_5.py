"""Charter 0.4.5: the owner's commit of an install, upgrade or uninstall is handed over as one command the tools
print, not as prose each agent writes. Motivated by upgrade reports of 2026-09-25 (0.4.0 -> 0.4.4 in several
projects): the agent said "commit these 13 files" (13 was the count of changes, not a list), gave no command, did
not say whether anything was staged, and offered "start a session with CHARTER_OWNER=1", which it had read in the
gate's own refusal. The installer now stages what it wrote and prints a pathspec commit; `charter handover` prints
the same block from the index; the refusal at commit points at it.
Every test here fails on 0.4.4 except the ones marked (guard), which pin behaviour that must not change."""
import json
import os
import shlex
import subprocess
import unittest

from helpers import charter, cleanup, clean_env, git, make_project
from test_migration import pkg
from test_review_regressions import commit_all

IN_SESSION = "  in a Claude Code prompt:  ! "


def owner_command(out):
    """The command the owner pastes after `!` in a Claude Code prompt, as the tool printed it."""
    return next(l[len(IN_SESSION):] for l in out.splitlines() if l.startswith(IN_SESSION))


def run_as_owner_in_session(cmd):
    """What `!` shell mode does with it: a shell inside Claude Code (CLAUDECODE=1), from wherever the session is."""
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, cwd="/", env=clean_env(CLAUDECODE="1"))


def staged(root):
    return sorted(x for x in git(root, "diff", "--cached", "--name-only").stdout.splitlines() if x)


def behind(root, settings=True):
    """An installed project one release back: a file the new release adds is missing, the version is older, and
    (settings) the hook entries the new release merges into .claude/settings.json, an owner-only file, are not
    there yet. From 0.4.6 an upgrade of package files alone is the agent's to commit (test_release_commit_0_4_6)."""
    (root / ".charter" / "rails.py").unlink()
    if settings:
        sp = root / ".claude" / "settings.json"
        cur = json.loads(sp.read_text())
        cur["hooks"].pop("SessionEnd", None)
        sp.write_text(json.dumps(cur, indent=2) + "\n")
    man = json.loads((root / ".charter" / "manifest.json").read_text())
    man["version"] = "0.4.4"
    (root / ".charter" / "manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    (root / "charter" / "VERSION").write_text("0.4.4\n")
    commit_all(root, "an older charter")
    git(root, "switch", "-q", "-c", "charter-upgrade")


class UpgradeHandsOver(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        behind(self.root)
        (self.root / "credentials.md").write_text("the owner's, untracked\n")
        (self.root / "notes.md").write_text("an agent's, staged\n")
        git(self.root, "add", "notes.md")

    def tearDown(self):
        cleanup(self.root)

    def test_upgrade_stages_what_it_wrote_and_prints_one_command(self):
        r = pkg("upgrade", str(self.root))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        wrote = [".charter/manifest.json", ".charter/rails.py", ".claude/settings.json", "charter/VERSION"]
        self.assertEqual(staged(self.root), sorted(wrote + ["notes.md"]))
        self.assertIn("Waiting on the owner: commit 4 staged file(s) on branch charter-upgrade.", r.stdout)
        cmd = owner_command(r.stdout)
        self.assertTrue(cmd.startswith(f"CHARTER_OWNER=1 git -C {shlex.quote(str(self.root))} commit -m "), cmd)
        self.assertEqual(shlex.split(cmd)[-5:], ["--"] + wrote)

    def test_the_printed_command_commits_exactly_those_files_from_any_directory(self):
        cmd = owner_command(pkg("upgrade", str(self.root)).stdout)
        r = run_as_owner_in_session(cmd)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        shown = git(self.root, "show", "--name-only", "--format=%s", "HEAD").stdout.split()
        self.assertEqual(shown[:2], ["charter", (self.root / "charter" / "VERSION").read_text().strip()])
        self.assertEqual(sorted(shown[2:]), [".charter/manifest.json", ".charter/rails.py", ".claude/settings.json", "charter/VERSION"])
        self.assertEqual(staged(self.root), ["notes.md"])       # the agent's staged work stays out
        self.assertIn("?? credentials.md", git(self.root, "status", "--porcelain").stdout)

    def test_an_agent_commit_is_refused_and_the_refusal_names_handover(self):
        pkg("upgrade", str(self.root))
        r = git(self.root, "commit", "-q", "-m", "x", check=False, env=clean_env(CLAUDECODE="1"))
        self.assertNotEqual(r.returncode, 0)
        out = r.stdout + r.stderr
        self.assertIn("charter/protected block", out)
        self.assertIn("charter handover", out)
        self.assertNotIn("start Claude Code with CHARTER_OWNER=1", out)

    def test_dry_run_stages_nothing(self):  # (guard)
        r = pkg("upgrade", str(self.root), "--dry-run")
        self.assertEqual(staged(self.root), ["notes.md"])
        self.assertNotIn("Waiting on the owner", r.stdout)


class HandoverCommand(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        git(self.root, "switch", "-q", "-c", "work")

    def tearDown(self):
        cleanup(self.root)

    def test_nothing_staged(self):
        self.assertEqual(charter(self.root, "handover").stdout.strip(), "nothing staged")

    def test_no_owner_only_change_is_the_agents_to_commit(self):
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a * 2\n")
        git(self.root, "add", "app/billing.py")
        out = charter(self.root, "handover").stdout
        self.assertIn("none is an owner-only change, so an agent commits them", out)
        self.assertNotIn("CHARTER_OWNER", out)

    def test_owner_only_change_gets_the_same_block_and_leaves_the_index(self):
        (self.root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}) + "\n")
        (self.root / "notes.md").write_text("x\n")
        git(self.root, "add", ".claude/settings.json", "notes.md")
        before = git(self.root, "diff", "--cached").stdout
        r = charter(self.root, "handover", "-m", "Settings: drop the hooks")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Waiting on the owner: commit 2 staged file(s) on branch work.", r.stdout)
        self.assertIn("-m 'Settings: drop the hooks' -- .claude/settings.json notes.md", owner_command(r.stdout))
        self.assertIn("owner-only among them (1): .claude/settings.json", r.stdout)   # (0.4.6: the block's last line)
        self.assertEqual(git(self.root, "diff", "--cached").stdout, before)

    def test_main_line_is_flagged(self):
        git(self.root, "switch", "-q", "main")
        (self.root / ".claude" / "settings.json").write_text("{}\n")
        git(self.root, "add", ".claude/settings.json")
        self.assertIn("note: main is the main line", charter(self.root, "handover").stdout)

    def test_next_points_at_handover(self):
        (self.root / ".claude" / "settings.json").write_text("{}\n")
        git(self.root, "add", ".claude/settings.json")
        self.assertIn("`python3 .charter/bin/charter handover` prints the command", charter(self.root, "next").stdout)


class UninstallHandsOver(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")

    def tearDown(self):
        cleanup(self.root)

    def test_uninstall_command_commits_the_removal(self):
        r = pkg("uninstall", str(self.root))
        cmd = owner_command(r.stdout)
        self.assertIn("commit -m 'charter: uninstall'", cmd)
        c = run_as_owner_in_session(cmd)
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
        self.assertEqual(staged(self.root), [])
        self.assertFalse(git(self.root, "ls-files", ".charter").stdout.strip())


class Fleet(unittest.TestCase):
    """`charter-pkg fleet`: every charter project under a directory, and one owner command for all their upgrades."""
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.dir = Path(tempfile.mkdtemp(prefix="charter-fleet-"))
        self.projects = []
        for name in ("alpha", "beta", "gamma"):
            root = make_project(track="prototype")
            dest = self.dir / name
            root.rename(dest)
            behind(dest)
            (dest / "mine.txt").write_text("the owner's, untracked\n")
            self.projects.append(dest)
        (self.dir / "not-charter").mkdir()
        # gamma: upgraded by an earlier run, nothing staged, nothing committed
        pkg("upgrade", str(self.projects[2]))
        git(self.projects[2], "reset", "-q")

    def tearDown(self):
        cleanup(self.dir)

    def test_without_upgrade_it_only_reads(self):
        before = [git(p, "status", "--porcelain").stdout for p in self.projects]
        r = pkg("fleet", "--root", str(self.dir))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([git(p, "status", "--porcelain").stdout for p in self.projects], before)
        lines = {l.split()[0]: l for l in r.stdout.splitlines()[1:4]}
        self.assertEqual(sorted(lines), ["alpha", "beta", "gamma"])
        self.assertIn("behind", lines["alpha"])
        self.assertIn("0.4.4 -> ", lines["gamma"])
        self.assertIn("not committed", lines["gamma"])
        self.assertIn("re-run with --upgrade", r.stdout)
        self.assertNotIn("CHARTER_OWNER", r.stdout)

    def test_upgrade_gives_one_command_that_commits_every_project(self):
        r = pkg("fleet", "--root", str(self.dir), "--upgrade")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Waiting on the owner: 3 project(s), one command.", r.stdout)
        cmd = owner_command(r.stdout)
        self.assertEqual(cmd.count("CHARTER_OWNER=1 git -C "), 3)
        c = run_as_owner_in_session(cmd)
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
        for p in self.projects:
            self.assertEqual(git(p, "show", "-s", "--format=%s", "HEAD").stdout.strip(),
                             "charter " + (p / "charter" / "VERSION").read_text().strip())
            self.assertIn(".charter/rails.py", git(p, "show", "--name-only", "--format=", "HEAD").stdout)
            self.assertEqual(git(p, "status", "--porcelain").stdout, "?? mine.txt\n")
        again = pkg("fleet", "--root", str(self.dir))
        self.assertIn("nothing waits", again.stdout)


if __name__ == "__main__":
    unittest.main()
