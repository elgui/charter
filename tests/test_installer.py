"""Installer: idempotent install, dry run, upgrade diff, uninstall."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import make_project, git, cleanup, INSTALLER, PKG


def pkg(*args):
    return subprocess.run([sys.executable, str(INSTALLER), *args], capture_output=True, text=True)


class Installer(unittest.TestCase):
    def setUp(self):
        self.root = make_project(with_charter=False)

    def tearDown(self):
        cleanup(self.root)

    def test_dry_run_changes_nothing(self):
        before = set(p.relative_to(self.root) for p in self.root.rglob("*") if ".git" not in p.parts)
        r = pkg("install", str(self.root), "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("dry run", r.stdout)
        after = set(p.relative_to(self.root) for p in self.root.rglob("*") if ".git" not in p.parts)
        self.assertEqual(before, after)

    def test_install_is_idempotent(self):
        r1 = pkg("install", str(self.root))
        self.assertEqual(r1.returncode, 0, r1.stdout)
        snapshot = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts}
        r2 = pkg("install", str(self.root))
        self.assertIn("nothing to do", r2.stdout)
        snapshot2 = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.assertEqual(snapshot, snapshot2)
        self.assertEqual(git(self.root, "config", "--get", "core.hooksPath").stdout.strip(), ".charter/githooks")
        self.assertEqual((self.root / "charter" / "VERSION").read_text().strip(), (PKG / "VERSION").read_text().strip())

    def test_settings_merge_keeps_existing_hooks(self):
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": ["Bash(pytest *)"]}, "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}}))
        pkg("install", str(self.root))
        s = json.loads((self.root / ".claude" / "settings.json").read_text())
        self.assertEqual(s["permissions"]["allow"], ["Bash(pytest *)"])
        self.assertEqual(len(s["hooks"]["Stop"]), 2)
        self.assertTrue(any("stop_gate.py" in " ".join(h.get("args", [])) for g in s["hooks"]["Stop"] for h in g["hooks"]))

    def test_upgrade_shows_diff_and_respects_local_edits(self):
        pkg("install", str(self.root))
        rules = self.root / ".claude" / "rules" / "charter.md"
        rules.write_text(rules.read_text() + "\nLocal addition.\n")
        r = pkg("upgrade", str(self.root))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("KEEP (locally modified", r.stdout)
        self.assertIn("Local addition.", rules.read_text())
        r = pkg("upgrade", str(self.root), "--force")
        self.assertNotIn("Local addition.", rules.read_text())

    def test_uninstall_removes_owned_files_and_keeps_project_files(self):
        pkg("install", str(self.root))
        (self.root / "charter" / "scope.md").write_text("# Scope\n")
        (self.root / "charter" / "decisions" / "x.md").write_text("---\nid: x\n---\n")
        r = pkg("uninstall", str(self.root))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse((self.root / ".charter" / "bin" / "charter").exists())
        self.assertFalse((self.root / ".claude" / "rules" / "charter.md").exists())
        self.assertFalse((self.root / ".github" / "workflows" / "charter.yml").exists())
        self.assertTrue((self.root / "charter" / "scope.md").exists())
        self.assertTrue((self.root / "charter" / "decisions" / "x.md").exists())
        self.assertTrue((self.root / "charter" / "config.json").exists())
        self.assertEqual(git(self.root, "config", "--get", "core.hooksPath", check=False).stdout.strip(), "")
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertNotIn(".charter/state/", (self.root / ".gitignore").read_text())

    def test_status_reports_versions(self):
        pkg("install", str(self.root))
        r = pkg("status", str(self.root))
        self.assertIn("installed: " + (PKG / "VERSION").read_text().strip(), r.stdout)


if __name__ == "__main__":
    unittest.main()
