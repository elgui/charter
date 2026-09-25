"""Charter 0.4.6: an upgrade of package files is the agent's to commit; a hand edit of the engine stays the owner's.
Until 0.4.5 every change under .charter/ was owner-only at commit, so each upgrade (the installer's own output,
byte for byte) waited on the owner, and on 2026-09-25 four projects waited at once. The engine's owner-only rule
is kept for what it guards: a gate edited by an agent (say by `sed` from Bash, which no Edit hook sees). The
installer records each file's hash in .charter/manifest.json, so the gate can tell the two apart.
Every test here fails on 0.4.5 except the ones marked (guard), which pin behaviour that must not change."""
import hashlib
import json
import unittest

from helpers import charter, cleanup, clean_env, git, make_project
from test_handover_0_4_5 import behind, staged
from test_migration import commit, pkg
from test_review_regressions import commit_all, set_config

IN_CLAUDE = clean_env(CLAUDECODE="1")


def agent_commit(root, msg="x"):
    r = git(root, "commit", "-q", "-m", msg, check=False, env=IN_CLAUDE)
    r.out = r.stdout + r.stderr
    return r


class UpgradeIsTheAgents(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        behind(self.root, settings=False)

    def tearDown(self):
        cleanup(self.root)

    def test_the_installer_says_an_agent_commits_it(self):
        r = pkg("upgrade", str(self.root))
        self.assertIn("none is an owner-only change, so an agent commits them", r.stdout)
        self.assertNotIn("CHARTER_OWNER", r.stdout)

    def test_the_gate_lets_an_agent_commit_it(self):
        pkg("upgrade", str(self.root))
        r = agent_commit(self.root, "charter upgrade")
        self.assertEqual(r.returncode, 0, r.out)
        self.assertEqual(staged(self.root), [])

    def test_next_does_not_list_it_as_waiting_on_the_owner(self):
        pkg("upgrade", str(self.root))
        self.assertNotIn("staged, for the owner to commit", charter(self.root, "next").stdout)

    def test_handover_says_an_agent_commits_it(self):
        pkg("upgrade", str(self.root))
        out = charter(self.root, "handover").stdout
        self.assertIn("so an agent commits them", out)
        self.assertNotIn("Waiting on the owner", out)


class HandEditStaysTheOwners(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")

    def tearDown(self):
        cleanup(self.root)

    def test_an_edited_engine_file_is_refused(self):  # (guard)
        p = self.root / ".charter" / "checks.py"
        p.write_text(p.read_text() + "\n# loosened\n")
        git(self.root, "add", ".charter/checks.py")
        r = agent_commit(self.root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("charter/protected block [.charter/checks.py]", r.out)

    def test_an_edited_engine_file_inside_an_upgrade_is_refused(self):
        behind(self.root, settings=False)
        pkg("upgrade", str(self.root))
        p = self.root / ".charter" / "checks.py"
        p.write_text(p.read_text() + "\n# loosened\n")
        git(self.root, "add", ".charter/checks.py")
        out = agent_commit(self.root).out
        self.assertIn("charter/protected block [.charter/checks.py]", out)
        self.assertIn("charter/protected block [.charter/manifest.json]", out)   # it lists a file that no longer matches

    def test_a_manifest_that_does_not_match_the_files_is_refused(self):
        mp = self.root / ".charter" / "manifest.json"
        man = json.loads(mp.read_text())
        man["files"][".charter/checks.py"] = hashlib.sha256(b"something else").hexdigest()
        mp.write_text(json.dumps(man, indent=2) + "\n")
        git(self.root, "add", ".charter/manifest.json")
        self.assertIn("charter/protected block [.charter/manifest.json]", agent_commit(self.root).out)

    def test_settings_stay_the_owners(self):  # (guard)
        behind(self.root, settings=True)
        pkg("upgrade", str(self.root))
        out = agent_commit(self.root).out
        self.assertIn("charter/protected block [.claude/settings.json]", out)
        self.assertNotIn("protected block [.charter/", out)


class CiAgrees(unittest.TestCase):
    """CI checks the author of every owner-only change; a release commit by anyone is not one."""
    def setUp(self):
        self.root = make_project(track="prototype")
        set_config(self.root, owner="Test Owner")
        commit_all(self.root, "owner set")

    def tearDown(self):
        cleanup(self.root)

    def test_an_upgrade_by_another_author_passes(self):
        behind(self.root, settings=False)
        pkg("upgrade", str(self.root))
        commit(self.root, "charter upgrade", name="Agent", email="a@example.com")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertNotIn("charter/protected block", r.stdout)

    def test_an_engine_edit_by_another_author_is_refused(self):  # (guard)
        p = self.root / ".charter" / "checks.py"
        p.write_text(p.read_text() + "\n# loosened\n")
        commit(self.root, "loosen", name="Agent", email="a@example.com")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertIn("by Agent <a@example.com> changes .charter/checks.py", r.stdout)


class FleetCommitsUpgrades(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.dir = Path(tempfile.mkdtemp(prefix="charter-fleet-"))
        self.plain, self.owned = self.dir / "plain", self.dir / "owned"
        for dest, settings in ((self.plain, False), (self.owned, True)):
            make_project(track="prototype").rename(dest)
            behind(dest, settings=settings)

    def tearDown(self):
        cleanup(self.dir)

    def test_the_agent_commits_what_it_may_and_hands_over_the_rest(self):
        r = pkg("fleet", "--root", str(self.dir), "--upgrade")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = {l.split()[0]: l for l in r.stdout.splitlines()[1:3]}
        self.assertIn("committed", rows["plain"])
        self.assertEqual(git(self.plain, "show", "-s", "--format=%s", "HEAD").stdout.strip(),
                         "charter " + (self.plain / "charter" / "VERSION").read_text().strip())
        self.assertIn("wait on the owner (.claude/settings.json)", rows["owned"])
        self.assertIn("Waiting on the owner: 1 project(s), one command.", r.stdout)
        self.assertNotIn(str(self.plain), r.stdout.split("Waiting on the owner")[1])


if __name__ == "__main__":
    unittest.main()
