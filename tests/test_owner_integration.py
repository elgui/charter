"""Owner integration uses committed objects and preserves other sessions' local work."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "docs/proposals/integrate-reviewed-branch.py"
SPEC = importlib.util.spec_from_file_location("owner_integration_payload", SCRIPT)
payload = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(payload)


class Integration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="owner-merge-test-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        for name in ("feature", "other", "third"):
            (self.repo / name).write_text("base\n")
        self.git("add", "feature", "other", "third")
        self.git("commit", "-q", "-m", "base")
        self.git("switch", "-q", "-c", "reviewed")
        (self.repo / "feature").write_text("reviewed\n")
        self.git("add", "feature")
        self.git("commit", "-q", "-m", "reviewed feature")
        self.reviewed = self.git("rev-parse", "HEAD")
        self.git("switch", "-q", "main")

    def git(self, *args):
        return payload.git(self.repo, *args)

    def dirty_work(self):
        (self.repo / "other").write_text("staged work\n")
        self.git("add", "other")
        (self.repo / "other").write_text("staged plus unstaged work\n")
        (self.repo / "draft").write_text("untracked draft\n")

    def fingerprint(self):
        return (self.git("status", "--porcelain"), self.git("diff"), self.git("diff", "--cached"),
                (self.repo / "other").read_bytes(), (self.repo / "draft").read_bytes())

    def test_dirty_default_checkout_preserves_index_worktree_and_untracked_files(self):
        self.dirty_work()
        before = self.fingerprint()
        merged = payload.integrate(self.repo, self.reviewed)
        self.assertEqual(self.fingerprint(), before)
        self.assertEqual((self.repo / "feature").read_text(), "reviewed\n")
        self.assertEqual(self.git("show", f"{merged}:other"), "base")

    def test_dirty_feature_checkout_stays_on_its_branch_and_main_updates_elsewhere(self):
        self.git("switch", "-q", "-c", "concurrent-docs")
        self.dirty_work()
        before = self.fingerprint()
        payload.integrate(self.repo, self.reviewed)
        self.assertEqual(self.git("branch", "--show-current"), "concurrent-docs")
        self.assertEqual(self.fingerprint(), before)
        self.assertEqual(self.git("show", "main:feature"), "reviewed")
        self.assertEqual((self.repo / "feature").read_text(), "base\n")

    def test_target_can_advance_with_unrelated_committed_work(self):
        (self.repo / "third").write_text("new committed work\n")
        self.git("add", "third")
        self.git("commit", "-q", "-m", "concurrent commit")
        self.dirty_work()
        before = self.fingerprint()
        payload.integrate(self.repo, self.reviewed)
        self.assertEqual(self.fingerprint(), before)
        self.assertEqual(self.git("show", "HEAD:third"), "new committed work")

    def test_overlapping_local_edit_refuses_without_losing_it(self):
        (self.repo / "feature").write_text("local conflicting work\n")
        before = self.git("rev-parse", "HEAD")
        with self.assertRaises(RuntimeError):
            payload.integrate(self.repo, self.reviewed)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual((self.repo / "feature").read_text(), "local conflicting work\n")

    def test_check_does_not_update_refs_or_local_work(self):
        self.dirty_work()
        before = self.fingerprint(), self.git("rev-parse", "main"), self.git("worktree", "list", "--porcelain")
        subprocess.run(["python3", str(SCRIPT), "--repo", str(self.repo), "--candidate", self.reviewed, "--check"],
                       capture_output=True, check=True)
        self.assertEqual((self.fingerprint(), self.git("rev-parse", "main"),
                          self.git("worktree", "list", "--porcelain")), before)
