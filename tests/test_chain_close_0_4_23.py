"""Charter 0.4.23 (built as 0.4.21 on branch chain-closes-every-session): a chain session opens in the chain's own tree, and its process is freed at every end.

Measured on 2026-11-01 from a tele-claude session (docs/trials/2026-11-01-chain-close.md): the shim's `create` without
`--workspace` opened the child in the calling session's registered checkout, whatever directory it ran from, so a chain
started in a linked worktree would have worked on the other tree's branch. `close_tab` ran only in `_hand_over`, on
session n-1, so session n stayed alive through all of session n+1, and the last session of a chain was never closed,
each one an idle Claude Code process on a box short of memory. Each test here fails on 2ec340e."""
import json
import os
import stat
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

from helpers import PKG, git
from test_chain_0_4_7 import VERIFIED, ChainCase, cli
from test_chain_wait import WaitCase, charter
from test_review_regressions import commit_all

sys.path.insert(0, str(PKG / ".charter"))
import chain as chainlib  # noqa: E402

SHIM = """#!{py}
import json, os, shutil, sys
argv = sys.argv[1:]
d = {d!r}
with open(os.path.join(d, "calls.jsonl"), "a") as f:
    f.write(json.dumps({{"argv": argv, "cwd": os.getcwd()}}) + "\\n")
if argv[0] == "create":
    goal, brief = argv[argv.index("--goal") + 1], argv[argv.index("--briefing-file") + 1]
    shutil.copy(brief, os.path.join({out!r}, goal + ".md"))
    print(json.dumps({{"backend": "tele-claude", "session_id": "tab-" + str(int(goal[-2:])), "ready": True}}))
elif argv[0] == "delete":
    if os.path.exists(os.path.join(d, "delete-fails")):
        print("tele-claude stalled", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(os.path.join(d, "delete-404")):
        print(json.dumps({{"error": "DELETE -> HTTP 404: Session not found"}}), file=sys.stderr)
        sys.exit(1)
    print(json.dumps({{"deleted": True}}))
"""


class ShimMixin:
    """Sessions launched through a stand-in for the spawn plugin's shim, which records every call."""

    def fake_shim(self):
        self.shimdir = self.root.parent / (self.root.name + "-shim")
        self.shimdir.mkdir()
        shim = self.shimdir / "agent_session.py"
        shim.write_text(SHIM.format(py=sys.executable, d=str(self.shimdir), out=str(self.out)))
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
        patcher = mock.patch.dict(os.environ, {"CHARTER_SPAWN_SHIM": str(shim)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.launcher = "spawn"
        cfg = json.loads((self.root / "charter" / "config.json").read_text())
        cfg.setdefault("chain", {})["close_delay_s"] = 0
        (self.root / "charter" / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
        commit_all(self.root, "chain sessions close at once in these tests")

    def calls(self, verb):
        p = self.shimdir / "calls.jsonl"
        rows = [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
        return [r for r in rows if r["argv"][0] == verb]

    def deleted(self):
        return [next(a for a in c["argv"] if a.startswith("tab-")) for c in self.calls("delete")]

    def wait_until(self, what, ok, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            if ok():
                return
            time.sleep(0.05)
        self.fail(f"{what}: {self.calls('delete')}\n{self.events()}")

    def wait_deleted(self, tab):
        self.wait_until(f"{tab} was not deleted", lambda: tab in self.deleted())

    def wait_event(self, text):
        self.wait_until(f"no event {text!r}", lambda: text in self.events())


class CloseCase(ShimMixin, ChainCase):
    def setUp(self):
        super().setUp()
        self.fake_shim()
        self.start()
        self.cid = self.chain["id"]


class Workspace(ShimMixin, ChainCase):
    def setUp(self):
        super().setUp()
        self.fake_shim()

    def test_session_1_is_told_to_open_in_the_chains_root(self):
        self.start()
        argv = self.calls("create")[0]["argv"]
        self.assertEqual(argv[argv.index("--workspace") + 1], str(self.root))

    def test_a_chain_started_in_a_linked_worktree_opens_there_and_says_so_in_the_dry_run(self):
        tree = self.root.parent / (self.root.name + "-tree")
        git(self.root, "worktree", "add", "-q", "-b", "work", str(tree))
        self.addCleanup(lambda: git(self.root, "worktree", "remove", "--force", str(tree), check=False))
        r = cli(tree, "start", "--unit", "u1", "--launcher", "spawn", "--window", str(self.WINDOW), "--review", "off", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"sessions open in {tree}, on branch work", r.stdout)
        r = cli(tree, "start", "--unit", "u1", "--launcher", "spawn", "--window", str(self.WINDOW), "--review", "off")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        argv = self.calls("create")[0]["argv"]
        self.assertEqual(argv[argv.index("--workspace") + 1], str(tree))

    def test_the_next_session_is_told_too(self):
        self.start()
        self.cid = self.chain["id"]
        self.join(1, "s1")
        self.write_handoff(1)
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        argv = self.calls("create")[1]["argv"]
        self.assertEqual(argv[argv.index("--workspace") + 1], str(self.root))


class Trust(ShimMixin, ChainCase):
    """Claude Code asks per folder, and a briefing pasted before the menu is answered is lost (measured 2026-11-01)."""

    def setUp(self):
        super().setUp()
        self.fake_shim()
        self.home = self.root.parent / (self.root.name + "-home")
        self.home.mkdir()
        patcher = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def dry(self):
        return cli(self.root, "start", "--unit", "u1", "--launcher", "spawn", "--window", str(self.WINDOW), "--review", "off", "--dry-run").stdout

    def record(self, projects):
        (self.home / ".claude.json").write_text(json.dumps({"projects": projects}))

    def test_the_dry_run_warns_of_a_folder_claude_code_has_not_trusted(self):
        self.record({str(self.root.parent): {"hasTrustDialogAccepted": True}})
        out = self.dry()
        self.assertIn(f"warning: Claude Code has not trusted {self.root}", out)
        self.assertIn(f"cd {self.root} && claude", out)

    def test_a_trusted_folder_and_an_unreadable_record_say_nothing(self):
        self.assertNotIn("has not trusted", self.dry())
        self.record({str(self.root): {"hasTrustDialogAccepted": True}})
        self.assertNotIn("has not trusted", self.dry())


    def test_a_linked_worktree_is_trusted_through_its_main_checkout(self):
        tree = self.root.parent / (self.root.name + "-tree")
        git(self.root, "worktree", "add", "-q", "-b", "work", str(tree))
        self.addCleanup(lambda: git(self.root, "worktree", "remove", "--force", str(tree), check=False))
        self.record({str(self.root): {"hasTrustDialogAccepted": True}})
        r = cli(tree, "start", "--unit", "u1", "--launcher", "spawn", "--window", str(self.WINDOW), "--review", "off", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("has not trusted", r.stdout)


class EveryEnd(CloseCase):
    def test_a_session_is_freed_after_its_own_hand_over_not_after_the_next_ones(self):
        self.join(1, "s1")
        self.write_handoff(1)
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.wait_deleted("tab-1")
        self.wait_event("s01 tab-closed")
        self.assertNotIn("tab-2", self.deleted())
        self.assertTrue(chainlib.link(self.root, self.cid, 1).get("tab_closed"))
        self.assertTrue(self.calls("create")[1])

    def test_the_last_session_is_freed_when_the_chain_completes(self):
        self.join(1, "s1")
        self.write_handoff(1, status="complete", next_unit="")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(chainlib.load(self.root)["state"], "complete")
        self.wait_deleted("tab-1")

    def test_a_session_that_halts_is_freed(self):
        self.join(1, "s1")
        self.write_handoff(1, status="halt", next_unit="", halt="the owner must decide")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(chainlib.load(self.root)["state"], "halted")
        self.wait_deleted("tab-1")

    def test_a_session_that_stalls_is_freed_and_the_owner_is_told_its_transcript_stays(self):
        tp, _ = self.join(1, "s1")
        for _ in range(3):
            self.hook("Stop", "s1", tp)
        self.assertTrue(chainlib.link(self.root, self.cid, 1).get("stopped_unclosed"))
        self.wait_deleted("tab-1")
        self.assertIn("claude --resume s1", self.events())

    def test_a_session_stopped_before_it_joined_is_freed(self):
        r = cli(self.root, "stop")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(chainlib.load(self.root)["state"], "stopped")
        self.wait_deleted("tab-1")

    def test_a_session_is_deleted_once_however_many_ends_it_passes(self):
        tp, _ = self.join(1, "s1")
        self.write_handoff(1)
        cli(self.root, "next", sid="s1")
        self.wait_deleted("tab-1")
        self.wait_event("s01 tab-closed")
        self.hook("Stop", "s1", tp)
        self.join(2, "s2")
        self.write_handoff(2, verified=VERIFIED)
        r = cli(self.root, "next", sid="s2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.wait_deleted("tab-2")
        time.sleep(0.3)
        self.assertEqual(self.deleted().count("tab-1"), 1)

    def test_the_delete_names_the_backend_the_session_was_created_on(self):
        self.join(1, "s1")
        self.write_handoff(1)
        cli(self.root, "next", sid="s1")
        self.wait_deleted("tab-1")
        argv = self.calls("delete")[0]["argv"]
        self.assertEqual(argv[argv.index("--backend") + 1], "tele-claude")


class WaitEnd(ShimMixin, WaitCase):
    """WaitCase starts the chain in its own setUp, so the shim goes in first."""

    def start(self, *extra, **kw):
        self.fake_shim()
        return super().start(*extra, **kw)

    def test_a_session_that_waits_is_freed_and_the_owner_is_sent_to_a_session_of_their_own(self):
        self.join(1, "s1")
        self.wait_handoff(1)
        r = self.next("s1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(chainlib.load(self.root)["state"], "waiting")
        self.wait_deleted("tab-1")
        self.assertIn(f"cd {self.root} && claude", r.stdout)
        self.assertNotIn("the chain's tab", r.stdout)


class MenuAtLaunch(ShimMixin, ChainCase):
    def test_a_tab_stopped_at_a_menu_says_how_to_send_its_briefing(self):
        self.fake_shim()
        shim = self.shimdir / "agent_session.py"
        shim.write_text(shim.read_text().replace('"ready": True', '"ready": False, "delivery_error": "stopped at a menu"'))
        self.start()
        self.assertIn(f"send tab-1 --text-file {chainlib.link_dir(self.root, self.chain['id'], 1) / 'briefing.md'}", self.events())


class OwnSession(CloseCase):
    def test_the_owner_is_sent_to_the_chains_tree_from_any_checkout(self):
        self.join(1, "s1")
        self.write_handoff(1, status="halt", next_unit="", halt="the owner must decide")
        cli(self.root, "next", sid="s1")
        c = chainlib.load(self.root)
        c["root"] = "/the/chains/tree"
        chainlib.save(self.root, c)
        self.assertIn("cd /the/chains/tree && claude", charter(self.root, "owner").stdout)


class CloseFailure(CloseCase):
    def hand_over(self):
        self.join(1, "s1")
        self.write_handoff(1)
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_close_that_fails_is_retried_named_and_taken_up_at_the_next_hand_over(self):
        (self.shimdir / "delete-fails").write_text("")
        self.hand_over()
        self.wait_event("s01 tab-not-closed")
        self.assertEqual(self.deleted().count("tab-1"), 3)
        self.assertIn("tele-claude stalled", self.events())
        self.assertFalse(chainlib.link(self.root, self.cid, 1).get("tab_closed"))
        (self.shimdir / "delete-fails").unlink()
        self.join(2, "s2")
        self.write_handoff(2, verified=VERIFIED)
        r = cli(self.root, "next", sid="s2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.wait_until("session 1's tab was not closed at the next hand-over",
                        lambda: chainlib.link(self.root, self.cid, 1).get("tab_closed"))

    def test_a_tab_already_gone_counts_as_closed(self):
        (self.shimdir / "delete-404").write_text("")
        self.hand_over()
        self.wait_event("s01 tab-closed")
        self.assertEqual(self.deleted().count("tab-1"), 1)


if __name__ == "__main__":
    unittest.main()
