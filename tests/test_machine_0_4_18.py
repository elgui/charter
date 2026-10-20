"""Charter 0.4.18: the machine layer (`machine/`, `bin/charter_machine.py`) replaces the personal layer, and the project's own
SessionStart hook takes over the two facts that only needed the project (the ledger backlog, what waits on the owner).
Every test installs into a throwaway home, so the real ~/.claude is never read or written."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import INSTALLER, REPO, cleanup, clean_env, git, make_project, run_hook
from test_delegate_0_4_14 import PROPOSED

LAYER = REPO / "machine"


def pkg(home, *args):
    r = subprocess.run([sys.executable, str(INSTALLER), "machine", *args, "--home", str(home)],
                       capture_output=True, text=True, env=clean_env())
    return r.returncode, r.stdout + r.stderr


def hook(hook_path, cwd, home, **env):
    """Run the machine hook the way Claude Code runs a user-level SessionStart hook."""
    e = {k: v for k, v in clean_env(HOME=str(home)).items() if k != "CHARTER_PKG_DIR"}
    e.update(env)
    r = subprocess.run([sys.executable, "-B", str(hook_path)], input=json.dumps({"cwd": str(cwd), "session_id": "s"}),
                       capture_output=True, text=True, env=e)
    out = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    return r.returncode, out, r.stdout


def ctx(out):
    return out.get("hookSpecificOutput", {}).get("additionalContext", "")


def set_version(root, v):
    (root / "charter" / "VERSION").write_text(v + "\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="charter-home-")).resolve()
        self.claude = self.home / ".claude"
        self.root = make_project()

    def tearDown(self):
        cleanup(self.home)
        cleanup(self.root)


class CopyInstall(Base):
    def test_copies_records_the_checkout_and_wires_settings_once(self):
        self.claude.mkdir()
        (self.claude / "settings.json").write_text(json.dumps({"model": "x", "hooks": {"SessionStart": [
            {"hooks": [{"type": "command", "command": "echo other"}]}]}}))
        rc, so = pkg(self.home, "install")
        self.assertEqual(rc, 0, so)
        hook_p = self.claude / "hooks" / "charter-machine.py"
        self.assertFalse(hook_p.is_symlink())
        self.assertTrue(os.access(hook_p, os.X_OK))
        self.assertEqual((self.claude / "skills" / "CharterAdmin" / "SKILL.md").read_text(),
                         (LAYER / "skills" / "CharterAdmin" / "SKILL.md").read_text())
        side = json.loads((self.claude / "hooks" / "charter-machine.json").read_text())
        # the checkout the files came from, so the hook's version and freshness checks read the tree it was copied from
        # (/reviewPR #27: it recorded the main worktree when run from a linked one)
        self.assertEqual(Path(side["source"]), REPO, side)
        rc, so = pkg(self.home, "install")
        self.assertEqual(rc, 0, so)
        self.assertIn("already wired", so)
        s = json.loads((self.claude / "settings.json").read_text())
        cmds = [h["command"] for g in s["hooks"]["SessionStart"] for h in g["hooks"]]
        self.assertEqual(cmds.count('python3 -B "$HOME/.claude/hooks/charter-machine.py"'), 1, cmds)
        self.assertIn("echo other", cmds)
        self.assertEqual(s["model"], "x")

    def test_dry_run_writes_nothing(self):
        rc, so = pkg(self.home, "install", "--dry-run")
        self.assertEqual(rc, 0, so)
        self.assertIn("would copy", so)
        self.assertFalse(self.claude.exists())

    def test_a_skill_it_did_not_write_is_refused_unless_forced(self):
        foreign = self.claude / "skills" / "CharterAdmin"
        foreign.mkdir(parents=True)
        (foreign / "SKILL.md").write_text("mine\n")
        rc, so = pkg(self.home, "install")
        self.assertEqual(rc, 1, so)
        self.assertIn("is not this layer's", so)
        self.assertEqual((foreign / "SKILL.md").read_text(), "mine\n")
        self.assertFalse((self.claude / "settings.json").exists())
        rc, so = pkg(self.home, "install", "--force")
        self.assertEqual(rc, 0, so)
        self.assertNotEqual((foreign / "SKILL.md").read_text(), "mine\n")

    def test_settings_that_are_not_json_are_left_alone(self):
        self.claude.mkdir()
        (self.claude / "settings.json").write_text("{ not json")
        rc, so = pkg(self.home, "install")
        self.assertEqual(rc, 1, so)
        self.assertIn("charter-machine.py", so)   # the entry to add by hand
        self.assertEqual((self.claude / "settings.json").read_text(), "{ not json")
        rc, so = pkg(self.home, "install", "--no-settings")
        self.assertEqual(rc, 0, so)
        self.assertEqual((self.claude / "settings.json").read_text(), "{ not json")

    def test_uninstall_removes_only_what_install_wrote(self):
        self.claude.mkdir()
        (self.claude / "settings.json").write_text(json.dumps({"hooks": {"SessionStart": [
            {"hooks": [{"type": "command", "command": "echo other"}]}]}}))
        (self.claude / "charter-local.md").write_text("## Session\n\nmine\n")
        pkg(self.home, "install")
        rc, so = pkg(self.home, "uninstall")
        self.assertEqual(rc, 0, so)
        self.assertFalse((self.claude / "hooks" / "charter-machine.py").exists())
        self.assertFalse((self.claude / "hooks" / "charter-machine.json").exists())
        self.assertFalse((self.claude / "skills" / "CharterAdmin").exists())
        s = json.loads((self.claude / "settings.json").read_text())
        self.assertEqual([h["command"] for g in s["hooks"]["SessionStart"] for h in g["hooks"]], ["echo other"])
        self.assertTrue((self.claude / "charter-local.md").exists())

    def test_a_copy_the_user_changed_is_neither_replaced_nor_removed(self):
        # /reviewPR #27 (codex, both passes): ownership was "the sidecar exists", so a user's edit was deleted
        pkg(self.home, "install")
        notes = self.claude / "skills" / "CharterAdmin" / "MY-NOTES.md"
        notes.write_text("mine\n")
        rc, so = pkg(self.home, "install")
        self.assertEqual(rc, 1, so)
        self.assertIn("changed since it was installed", so)
        rc, so = pkg(self.home, "uninstall")
        self.assertIn("kept", so)
        self.assertEqual(notes.read_text(), "mine\n")
        self.assertFalse((self.claude / "hooks" / "charter-machine.py").exists(), so)   # the untouched hook still goes


class LinkInstall(Base):
    def test_links_and_the_linked_hook_finds_its_checkout(self):
        rc, so = pkg(self.home, "install", "--link")
        self.assertEqual(rc, 0, so)
        hook_p = self.claude / "hooks" / "charter-machine.py"
        self.assertTrue(hook_p.is_symlink())
        self.assertEqual(hook_p.resolve(), (LAYER / "hooks" / "charter-machine.py").resolve())
        self.assertEqual((self.claude / "skills" / "CharterAdmin").resolve(), (LAYER / "skills" / "CharterAdmin").resolve())
        self.assertFalse((self.claude / "hooks" / "charter-machine.json").exists())
        rc, out, so = hook(hook_p, self.root, self.home)
        self.assertIn(f"package repository: {REPO}", ctx(out), so)
        rc, so = pkg(self.home, "uninstall")
        self.assertFalse(hook_p.is_symlink() or hook_p.exists(), so)

    def test_a_link_under_another_name_works_too(self):
        # a user's own link manager may keep its own name for the hook (the personal layer's was charter-personal.py)
        (self.claude / "hooks").mkdir(parents=True)
        other = self.claude / "hooks" / "charter-personal.py"
        other.symlink_to(LAYER / "hooks" / "charter-machine.py")
        rc, out, so = hook(other, self.root, self.home)
        self.assertEqual(rc, 0, so)
        self.assertIn(f"package repository: {REPO}", ctx(out), so)


class MachineHook(Base):
    def setUp(self):
        super().setUp()
        pkg(self.home, "install")
        self.hook_p = self.claude / "hooks" / "charter-machine.py"
        git(self.root, "add", "-A")

    def test_silent_outside_a_charter_project(self):
        plain = Path(tempfile.mkdtemp(prefix="plain-")).resolve()
        self.addCleanup(cleanup, plain)
        rc, out, so = hook(self.hook_p, plain, self.home)
        self.assertEqual((rc, so.strip()), (0, ""))

    def test_says_when_the_checkout_is_ahead(self):
        set_version(self.root, "0.4.18")
        latest = (REPO / "package" / "VERSION").read_text().strip()
        rc, out, so = hook(self.hook_p, self.root, self.home, CHARTER_PKG_DIR=str(REPO))
        self.assertIn(f"package {latest} is current", ctx(out), so)
        self.assertNotIn("systemMessage", out)
        set_version(self.root, "0.4.0")
        rc, out, so = hook(self.hook_p, self.root, self.home, CHARTER_PKG_DIR=str(REPO))
        self.assertIn(f"package {latest} available, 0.4.0 installed", out.get("systemMessage", ""), so)

    def test_a_copy_older_than_the_checkout_is_named(self):
        side = self.claude / "hooks" / "charter-machine.json"
        d = json.loads(side.read_text())
        d.update(source=str(REPO), hash="0" * 64)
        side.write_text(json.dumps(d))
        rc, out, so = hook(self.hook_p, self.root, self.home)
        self.assertIn(f"machine layer changed in {REPO}", out.get("systemMessage", ""), so)
        d["hash"] = __import__("charter_machine").layer_hash(REPO)
        side.write_text(json.dumps(d))
        rc, out, so = hook(self.hook_p, self.root, self.home)
        self.assertNotIn("machine layer changed", so)

    def test_local_session_section_only(self):
        (self.claude / "charter-local.md").write_text("# Mine\n\n## Session\n\n- say hello\n\n## Admin\n\n- secret admin rule\n")
        rc, out, so = hook(self.hook_p, self.root, self.home)
        self.assertIn("- say hello", ctx(out), so)
        self.assertNotIn("secret admin rule", ctx(out))

    def test_older_installs_still_get_the_backlog_and_the_waiting_records(self):
        (self.root / "charter" / "decisions" / "cache-ttl.md").write_text(PROPOSED)
        common = Path(git(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
        (common / "charter").mkdir(exist_ok=True)
        (common / "charter" / "sessions.jsonl").write_text(json.dumps({"session": "a", "ts": "2026-10-20T00:00:00+00:00"}) + "\n")
        set_version(self.root, "0.4.17")
        rc, out, so = hook(self.hook_p, self.root, self.home, CHARTER_PKG_DIR=str(REPO))
        self.assertIn("1 ended session(s) not yet in the ledger", ctx(out), so)
        self.assertIn("waiting on you: decisions/cache-ttl", out.get("systemMessage", ""), so)
        set_version(self.root, "0.4.18")
        rc, out, so = hook(self.hook_p, self.root, self.home, CHARTER_PKG_DIR=str(REPO))
        self.assertNotIn("not yet in the ledger", so)
        self.assertNotIn("waiting on you", so)


class ProjectHookTakesOver(unittest.TestCase):
    """From 0.4.18 the project's own SessionStart hook reports what the personal layer used to."""

    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def test_unfolded_sessions_and_waiting_records_reach_the_person(self):
        (self.root / "charter" / "decisions" / "cache-ttl.md").write_text(PROPOSED)
        common = Path(git(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
        (common / "charter").mkdir(exist_ok=True)
        rec = lambda s: json.dumps({"session": s, "ts": "2026-10-20T00:00:00+00:00"}) + "\n"
        (common / "charter" / "sessions.jsonl").write_text(rec("a") + rec("b"))
        (self.root / "charter" / "ledger.jsonl").write_text(rec("a") + json.dumps({"session": "", "source": "human"}) + "\n")
        rc, out, so, se = run_hook(self.root, "session_start", {})
        self.assertEqual(rc, 0, se)
        seen = out.get("systemMessage", "")
        self.assertIn("1 ended session(s) not yet in the ledger", seen, so)
        self.assertIn("Proposed decisions waiting on the owner: cache-ttl", seen, so)

    def test_nothing_to_fold_says_nothing(self):
        rc, out, so, se = run_hook(self.root, "session_start", {})
        self.assertNotIn("not yet in the ledger", so)


class NothingPersonal(unittest.TestCase):
    def test_the_layer_names_no_one_and_no_machine(self):
        for p in LAYER.rglob("*"):
            if p.is_file():
                t = p.read_text()
                for word in (r"/home/", r"\bGui\b", r"\bPAI", r"\bSlate\b", r"\bCrossroads\b", r"AI_tooling", r"devis"):
                    self.assertIsNone(re.search(word, t), f"{p.relative_to(REPO)} names {word}")


sys.path.insert(0, str(REPO / "bin"))

if __name__ == "__main__":
    unittest.main()
