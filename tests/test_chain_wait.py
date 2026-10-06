"""Charter 0.4.9: a chain that waits on the owner, and the fixes from the cross-review of the merged 0.4.9
(2026-10-04, `codex exec review --base origin/main`).

A road whose units need the owner (sudo, a password, a purchase, a decision) halted the chain at the first such step,
and the owner learned of it only by watching. A session now does what it can, marks the owner's lines, and hands over
with `status: wait`: the chain waits at a commit, tells the owner (a notification, the owner's queue), and the session
after `chain resume` checks the owner's acts first. The review's findings: a second `chain next` could launch a second
successor, a late tab could join a closed session, an edit to a file untracked at launch went unseen, a chain session
could run an owner verb, a complete chain could leave work uncommitted, a resume from another branch launched there,
the size gate skipped any file named like the installer's, and an upgrade dropped a project hook that shared a group
with one of charter's."""
import argparse
import contextlib
import io
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from helpers import PKG, REPO, git
from test_chain_0_4_7 import VERIFIED, ChainCase, cli, env_for, handoff, resume
from test_groups_0_4_8 import GroupCase
from test_review_regressions import commit_all

sys.path.insert(0, str(PKG / ".charter"))
import chain as chainlib  # noqa: E402
import checks  # noqa: E402
import lib  # noqa: E402

WAIT = "- turn on FileVault (System Settings > Privacy & Security) — closes u1 AC-2"
# from 0.4.11 the acts are in owner.md; the handoff's `## Wait` says what the owner should know beyond them
OWNER = ("# Owner's acts\n\n## 1. turn on FileVault (System Settings > Privacy & Security)\ncloses: u1 AC-2\n"
         "do: System Settings > Privacy & Security > FileVault\n")


def charter(root, *args, sid=None, env=None):
    e = env_for(sid)
    e.update(env or {})
    return subprocess.run([sys.executable, "-B", str(root / ".charter" / "bin" / "charter"), "--root", str(root), *args],
                          capture_output=True, text=True, cwd=str(root), env=e)


def charter_pkg():
    loader = importlib.machinery.SourceFileLoader("charter_pkg", str(REPO / "bin" / "charter-pkg"))
    spec = importlib.util.spec_from_loader("charter_pkg", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class WaitCase(ChainCase):
    def setUp(self):
        super().setUp()
        self.notified = self.out.parent / (self.out.name + "-notified.txt")
        self.addCleanup(lambda: self.notified.unlink(missing_ok=True))
        cfg = json.loads((self.root / "charter" / "config.json").read_text())
        cfg["chain"] = {"notify": "off", "notify_command":
                        f"{sys.executable} -c \"import sys; open(sys.argv[1], 'a').write(sys.argv[2] + ' | ' + sys.argv[3] + chr(10))\" "
                        f"{self.notified} {{chain}} {{text}}"}
        (self.root / "charter" / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
        u1 = self.root / ".taskets" / "u1.md"
        u1.write_text(u1.read_text().replace("\n## Evidence", "- [ ] AC-2: FileVault is on — owner: do\n\n## Evidence"))
        commit_all(self.root, "u1: an owner line; notifications to a file")
        self.start()
        self.cid = self.chain["id"]

    def next(self, sid):
        """`chain next` with notifications on, as on the owner's machine (the tests turn them off elsewhere)."""
        return charter(self.root, "chain", "next", sid=sid, env={"CHARTER_NOTIFY": ""})

    def wait_handoff(self, n, wait=WAIT, owner=OWNER, **kw):
        p = self.write_handoff(n, status="wait", **kw)
        if wait:
            p.write_text(p.read_text() + f"\n## Wait\n\n{wait}\n")
        if owner is not None:
            (p.parent / "owner.md").write_text(owner)
        return p

    def notes(self):
        for _ in range(100):
            if self.notified.exists() and self.notified.read_text():
                return self.notified.read_text()
            import time
            time.sleep(0.05)
        return ""


class Wait(WaitCase):
    def test_a_session_that_waits_pauses_the_chain_tells_the_owner_and_the_next_session_checks_the_acts(self):
        self.join(1, "s1")
        self.wait_handoff(1)
        r = self.next("s1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("waits on the owner, who is told", r.stdout)
        c = chainlib.load(self.root)
        self.assertEqual(c["state"], "waiting")
        self.assertIn("session 1 waits on the owner: 1 act(s) in owner.md (0 to run with `charter owner run`): turn on FileVault", c["reason"])
        self.assertIn("chain wait: session 1 waits on the owner", self.events())
        self.assertIn(f"{self.cid} | 1 act waits: run `python3 .charter/bin/charter owner` in {self.root}, "
                      "`python3 .charter/bin/charter owner run` to run them, then type /resume-chain ok", self.notes())
        # the session's last message to the owner: the acts verbatim and the command to paste, in a fenced block (0.4.10, 0.4.11)
        self.assertIn("End your turn with a closing message that gives the owner what follows, verbatim", r.stdout)
        self.assertIn("- 1. [you] turn on FileVault (System Settings > Privacy & Security) (closes u1 AC-2)", r.stdout)
        self.assertIn("```sh\npython3 .charter/bin/charter owner run\n```", r.stdout)
        self.assertFalse(chainlib.link_dir(self.root, self.cid, 2).exists())

        q = json.loads(charter(self.root, "owner", "--json").stdout)
        it = {i["key"]: i for i in q["items"]}
        self.assertEqual(it[f"chain:{self.cid}"]["kind"], "do")
        self.assertIn("turn on FileVault", it[f"chain:{self.cid}"]["ask"])
        # no command of the queue resumes a chain: the owner types `/resume-chain`, with the owner lines to close (0.4.9)
        self.assertIsNone(it[f"chain:{self.cid}"]["perform"])
        self.assertIn("owner-line:u1:AC-2", it)
        nxt = charter(self.root, "next").stdout
        self.assertIn(f"chain {self.cid} waits on you: 1 act(s) from session 1", nxt)
        self.assertEqual(it[f"chain:{self.cid}"]["title"], f"chain {self.cid} waits on you: 1 act(s) from session 1")
        self.assertIn("then type `/resume-chain ok` in Claude Code, in the chain's tab once its session has handed over, or a session of your own", nxt)
        self.assertNotIn("chain resume", nxt)

        r = cli(self.root, "start", "--unit", "u1", "--launcher", self.launcher, "--review", "off")
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"chain {self.cid} waits on the owner", r.stdout)

        r = resume(self.root, "ok FileVault is on")
        self.assertEqual(r.returncode, 0, r.stdout)
        b = self.launched(2)
        self.assertIn("## The chain waited on the owner", b)
        self.assertIn("FileVault is on", b)
        self.assertIn(WAIT, b)
        self.assertEqual(chainlib.load(self.root)["state"], "running")
        self.assertNotIn(f"chain:{self.cid}", charter(self.root, "owner", "--json").stdout)

    def test_a_wait_needs_its_acts_and_a_clean_tree(self):
        self.join(1, "s1")
        self.wait_handoff(1, wait="")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("`status: wait` needs `## Wait`", r.stdout)
        self.wait_handoff(1, owner=None)
        (chainlib.link_dir(self.root, self.cid, 1) / "owner.md").unlink()
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("`status: wait` needs the owner's acts in", r.stdout)
        self.wait_handoff(1, state="app/billing.py: a draft, not committed")
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a * 2\n")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("uncommitted change(s) with `status: wait`: app/billing.py", r.stdout)
        self.assertEqual(chainlib.load(self.root)["state"], "running")

    def test_a_complete_chain_leaves_nothing_uncommitted_even_without_groups(self):
        self.join(1, "s1")
        self.write_handoff(1, status="complete", next_unit="none", state="app/billing.py: a draft, not committed")
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a * 2\n")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("uncommitted change(s) with `status: complete`: app/billing.py", r.stdout)

    def test_a_waiting_chain_can_be_stopped(self):
        self.join(1, "s1")
        self.wait_handoff(1)
        self.assertEqual(self.next("s1").returncode, 0)
        r = cli(self.root, "stop", "--reason", "not this week")
        self.assertEqual(r.returncode, 0, r.stdout)
        c = chainlib.load(self.root)
        self.assertEqual((c["state"], c["reason"]), ("stopped", "not this week"))

    def test_a_question_to_the_owner_points_to_wait(self):
        tp, _ = self.join(1, "s1")
        out = self.hook("PreToolUse", "s1", tp, tool_name="AskUserQuestion", tool_input={})
        self.assertIn("`status: wait`", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_a_chain_session_cannot_perform_an_owner_verb(self):
        self.join(1, "s1")
        r = charter(self.root, "rule", "retry-limit", "rejected", sid="s1")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("a chain session never performs the owner's act", r.stderr)
        self.assertNotIn("charter rule", git(self.root, "log", "-1", "--format=%s").stdout)
        r = charter(self.root, "rule", "retry-limit", "rejected", "--dry-run", sid="other")
        self.assertNotIn("a chain session never performs", r.stderr)


class WaitSecondReview(WaitCase):
    """The cross-review of the wait itself (2026-10-04, 409ad60..6b104af)."""

    def waiting(self):
        self.join(1, "s1")
        self.wait_handoff(1)
        self.assertEqual(self.next("s1").returncode, 0)
        self.assertEqual(chainlib.load(self.root)["state"], "waiting")

    def test_an_owner_act_is_denied_to_a_chain_session_whatever_its_environment(self):
        tp, _ = self.join(1, "s1")
        for cmd in ("env -u CLAUDE_CODE_SESSION_ID python3 .charter/bin/charter rule retry-limit rejected",
                    "CHARTER_OWNER=1 git commit -m x"):
            out = self.hook("PreToolUse", "s1", tp, tool_name="Bash", tool_input={"command": cmd})
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny", cmd)
        self.assertNotIn("hookSpecificOutput", self.hook("PreToolUse", "s1", tp, tool_name="Bash", tool_input={"command": "python3 .charter/bin/charter next"}))

    def test_an_act_names_what_it_closes(self):
        self.join(1, "s1")
        self.wait_handoff(1, owner="## 1. later\ncloses: -\ndo: something\n")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("step 1 (later) closes no line and names no unit, decision or change request", r.stdout)

    def test_the_template_as_written_is_not_an_act(self):
        self.join(1, "s1")
        self.wait_handoff(1, owner=(self.root / "charter" / "templates" / "owner.md").read_text())
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("owner.md: no act: one `## 1. <title>` per act", r.stdout)
        self.wait_handoff(1)
        self.assertEqual(self.next("s1").returncode, 0)
        it = {i["key"]: i for i in json.loads(charter(self.root, "owner", "--json").stdout)["items"]}[f"chain:{self.cid}"]
        self.assertEqual(it["title"], f"chain {self.cid} waits on you: 1 act(s) from session 1")
        self.assertTrue(it["ask"].startswith("- 1. [you] turn on FileVault (System Settings > Privacy & Security) (closes u1 AC-2)\n"
                                             "   do: System Settings > Privacy & Security > FileVault\n"
                                             "(not reviewed by a second model: review off)\n"), it["ask"])
        self.assertIn(chainlib.own_session(self.root), it["ask"])

    def test_a_stop_requested_before_the_wait_wins(self):
        self.join(1, "s1")
        self.assertEqual(cli(self.root, "stop").returncode, 0)   # the live session is told to hand over
        self.wait_handoff(1)
        self.assertEqual(self.next("s1").returncode, 0)
        c = chainlib.load(self.root)
        self.assertEqual(c["state"], "stopped")
        self.assertIn("stopped by the owner; session 1 was waiting on: 1 act(s) in owner.md (0 to run with `charter owner run`): turn on FileVault", c["reason"])

    def test_resume_of_a_waiting_chain_wants_the_owners_changes_committed(self):
        self.waiting()
        u1 = self.root / ".taskets" / "u1.md"
        u1.write_text(u1.read_text().replace("- [ ] AC-2", "- [x] AC-2"))
        r = resume(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("1 uncommitted change(s): .taskets/u1.md", r.stdout)
        self.assertIn("git commit -m \"owner: done during the chain's wait\" -- .taskets/u1.md", r.stdout)
        self.assertEqual(chainlib.load(self.root)["state"], "waiting")
        commit_all(self.root, "owner: AC-2 done")
        self.assertEqual(resume(self.root).returncode, 0)
        self.launched(2)

    def test_resume_refuses_a_branch_that_lost_the_chains_last_commit(self):
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a\n\n\n# s1 work\n")
        commit_all(self.root, "s1 work")
        self.waiting()
        git(self.root, "reset", "-q", "--hard", "HEAD~1")
        r = resume(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no longer holds", r.stdout)

    def test_a_manual_join_of_a_chain_that_is_not_running_is_refused(self):
        self.waiting()
        r = cli(self.root, "join", self.cid, "1", sid="late")
        self.assertIn(f"charter chain {self.cid} is waiting", r.stdout)
        self.assertIsNone(chainlib.joined(self.root, "late"))

    def test_a_deleted_untracked_file_counts_as_uncommitted(self):
        rec = {"untracked_at_launch": ["notes.md"], "untracked_stat_at_launch": {"notes.md": [6, 1]}}
        self.assertEqual(chainlib.uncommitted(self.root, rec), ["notes.md"])

    def test_notifications_survive_a_bad_template_and_a_typo(self):
        cfg = json.loads((self.root / "charter" / "config.json").read_text())
        cfg["chain"] = {"notify": "atuo", "notify_command": "echo 'unbalanced"}
        (self.root / "charter" / "config.json").write_text(json.dumps(cfg))
        with mock.patch.dict(os.environ, {"CHARTER_NOTIFY": ""}), mock.patch.object(chainlib.sys, "platform", "darwin"), \
                mock.patch.object(chainlib.shutil, "which", return_value="/usr/bin/osascript"), \
                mock.patch.object(chainlib.subprocess, "Popen") as popen:
            chainlib.notify(self.root, self.chain, "waits on you")
        self.assertEqual([c.args[0][0] for c in popen.call_args_list], ["osascript"])

    def test_a_dry_run_reserves_no_id(self):
        cli(self.root, "stop")
        before = sorted(x.name for x in chainlib.base_dir(self.root).iterdir())
        self.assertEqual(cli(self.root, "start", "--unit", "u1", "--launcher", self.launcher, "--dry-run").returncode, 0)
        self.assertEqual(sorted(x.name for x in chainlib.base_dir(self.root).iterdir()), before)


class WaitAtABoundary(GroupCase):
    def test_a_wait_at_the_end_of_a_group_runs_the_review_on_resume(self):
        self.start()
        self.join(1, "s1")
        self.work()
        p = self.write_handoff(1, status="wait", next_unit="u3")
        p.write_text(p.read_text() + f"\n## Wait\n\n{WAIT}\n")
        (p.parent / "owner.md").write_text("## 1. approve the copy of u3\ncloses: -\ndo: read it and say yes\n")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual((self.state()["state"], self.calls()), ("waiting", []))
        self.assertEqual(resume(self.root).returncode, 0)
        b = self.launched(2)
        self.assertEqual((len(self.calls()), self.group(0)["state"], self.group()["key"]), (1, "cleared", "r2"))
        self.assertIn("## The chain waited on the owner", b)


class ReviewFixes(ChainCase):
    def setUp(self):
        super().setUp()
        self.start()
        self.cid = self.chain["id"]

    def test_a_second_next_that_waited_on_the_lock_launches_nothing(self):
        self.join(1, "s1")
        self.write_handoff(1)
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a\n\n\n# groundwork\n")
        commit_all(self.root, "groundwork")
        real = chainlib.chain_lock

        @contextlib.contextmanager
        def first_one_won(root, cid):
            with real(root, cid):
                with chainlib.editing_link(root, cid, 1) as rec:
                    rec["closed_at"] = chainlib.now()   # what the first `chain next` did while this one waited
                yield
        a = argparse.Namespace(id=None, session=1, early="test", check=False)
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_SESSION_ID"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(chainlib, "chain_lock", first_one_won):
            self.assertEqual(chainlib.cmd_next(self.root, a), 0)
        self.assertFalse(chainlib.link_dir(self.root, self.cid, 2).exists())
        self.assertNotIn("s01 closed", self.events())

    def test_a_late_tab_cannot_join_a_session_resume_closed(self):
        self.assertEqual(cli(self.root, "stop").returncode, 0)   # session 1 never joined: stopped at once
        self.assertEqual(resume(self.root).returncode, 0)
        self.launched(2)
        _, out = self.join(1, "late")   # the tab of session 1 starts now, say after its folder-trust menu
        self.assertIn("is already closed", out["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(chainlib.joined(self.root, "late"))

    def test_an_edit_to_a_file_untracked_at_launch_counts_as_uncommitted(self):
        cli(self.root, "stop")
        (self.root / "notes.md").write_text("draft\n")
        self.assertEqual(resume(self.root).returncode, 0)
        rec = chainlib.link(self.root, self.cid, 2)
        self.assertEqual(chainlib.uncommitted(self.root, rec), [])
        (self.root / "notes.md").write_text("draft, and the session's work\n")
        self.assertEqual(chainlib.uncommitted(self.root, rec), ["notes.md"])
        self.assertEqual(chainlib.uncommitted(self.root, {"untracked_at_launch": ["notes.md"]}), [])   # a record from before

    def test_resume_from_another_branch_is_refused(self):
        cli(self.root, "stop")
        git(self.root, "checkout", "-q", "main")
        r = resume(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"HEAD is on main, and the chain works on chain/{self.cid}", r.stdout)
        self.assertFalse(chainlib.link_dir(self.root, self.cid, 2).exists())

    def test_two_starts_in_one_second_get_two_ids(self):
        with mock.patch.object(chainlib.dt, "datetime") as fake, mock.patch.object(chainlib.time, "sleep") as slept:
            fake.now.return_value.strftime.side_effect = [self.cid, "20991231-235959"]
            self.assertEqual(chainlib.new_id(self.root), "20991231-235959")
        self.assertEqual(slept.call_count, 1)


class Package(unittest.TestCase):
    def test_the_size_gate_skips_exactly_the_installer_files(self):
        pkg = charter_pkg()
        self.assertEqual(checks.PACKAGE_FILES, {o for o in pkg.OWNED if not o.startswith(".charter/")})
        cfg = lib.config_from({})
        self.assertIsNone(checks.size_budget_for(REPO, cfg, "charter/templates/unit.md"))
        self.assertIsNotNone(checks.size_budget_for(REPO, cfg, "charter/templates/project.md"))
        self.assertIsNotNone(checks.size_budget_for(REPO, cfg, ".claude/skills/charter-local/SKILL.md"))

    def test_an_upgrade_keeps_a_project_hook_that_shares_a_group_with_charter(self):
        pkg = charter_pkg()
        mine = {"type": "command", "command": "echo mine"}
        old = {"type": "command", "command": "python3 -B ${CLAUDE_PROJECT_DIR}/.charter/hooks/stop_gate.py"}
        existing = {"hooks": {"Stop": [{"hooks": [old, mine]}, {"matcher": "x", "hooks": [{"command": "echo other"}]}]}}
        fragment = {"hooks": {"Stop": [{"hooks": [old]}]}}
        merged = pkg.merge_settings(existing, fragment, REPO)["hooks"]["Stop"]
        self.assertEqual(merged, [{"hooks": [mine]}, {"matcher": "x", "hooks": [{"command": "echo other"}]}, {"hooks": [old]}])
        self.assertEqual(pkg.strip_settings({"hooks": {"Stop": merged}})["hooks"]["Stop"],
                         [{"hooks": [mine]}, {"matcher": "x", "hooks": [{"command": "echo other"}]}])

    def test_notify_settings_are_known_config(self):
        cfg = lib.config_from({"chain": {"notify": "off", "notify_command": "echo {text}"}})
        self.assertEqual((cfg["chain"]["notify"], cfg[lib.PROBLEMS]), ("off", []))
        self.assertEqual(lib.config_from({})["chain"]["notify"], "auto")


PASTE = ("- write the bucket name — run: `read \"b?R2 bucket name: \" && echo \"$b\" | sudo tee /opt/x/r2-bucket` "
         "— expect: the name echoed, one Touch ID — closes u1 AC-2\n"
         "- turn on FileVault (System Settings > Privacy & Security) — closes u1 AC-2\n"
         "- configure the remote — run: `sudo rclone config` — expect: `rclone config` lists r2 — closes u1 AC-2")
CMDS = ['read "b?R2 bucket name: " && echo "$b" | sudo tee /opt/x/r2-bucket', "sudo rclone config"]
# the same three acts in owner.md (0.4.11)
OWNER3 = ("## 1. Write the R2 bucket name, one Touch ID (u1)\ncloses: -\nexpect-output: .\n\n```sh\n" + CMDS[0] + "\n```\n\n"
          "## 2. Turn on FileVault\ncloses: u1 AC-2\ndo: System Settings > Privacy & Security > FileVault\n\n"
          "## 3. Configure the remote, interactive (u1)\ncloses: -\ndo: answer n, r2, s3, Cloudflare\n\n```sh\n" + CMDS[1] + "\n```\n")
RUN = "python3 .charter/bin/charter owner run"


class PasteReady(WaitCase):
    """Charter 0.4.10 (docs/bugs/2026-10-05-owner-acts-not-paste-ready.md): an owner act reaches the owner as commands
    that run as pasted in zsh, in the terminal, not as labels in a file the owner does not read. From 0.4.11 the acts
    are in owner.md and the owner pastes one command, `charter owner run`; the standard holds for owner.md, and a wait
    handed over before 0.4.11 is shown as 0.4.10 showed it."""

    def test_a_placeholder_in_a_command_is_refused_and_a_redirection_passes(self):
        self.join(1, "s1")
        self.wait_handoff(1, owner="## 1. Write the bucket (u1)\ncloses: u1 AC-2\n\n```sh\necho <bucket> | sudo tee x\n```\n")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("`<bucket>`", r.stdout)
        self.assertIn("is a redirection", r.stdout)
        # in `## Wait`, a backticked placeholder is refused too, and a `run:` command belongs in owner.md
        self.wait_handoff(1, wait="- see owner.md; the bucket is `<bucket>` — closes u1 AC-2")
        self.assertIn("`## Wait` commands hold `<bucket>`", cli(self.root, "next", sid="s1").stdout)
        self.wait_handoff(1, wait="- sort the list — run: `sort < in.txt` — closes u1 AC-2")
        self.assertIn("`## Wait` gives commands (`sort < in.txt`): an act with a command goes in owner.md", cli(self.root, "next", sid="s1").stdout)
        self.assertEqual(chainlib.load(self.root)["state"], "running")
        self.wait_handoff(1, owner="## 1. Sort the list (u1)\ncloses: u1 AC-2\n\n```sh\nsort < in.txt\n```\n")
        r = self.next("s1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(chainlib.load(self.root)["state"], "waiting")

    def test_what_counts_as_a_placeholder(self):
        for act in ("run: `echo <bucket> | sudo tee x`", "run: `set <R2_bucket-name>`", "`a` then `cp <src> /x`"):
            self.assertTrue(chainlib.placeholders(act), act)
        for act in ("run: `sort < in.txt`", "run: `cat <<EOF`", "run: `cat <<'EOF'`", "run: `a <in >out`",
                    "closes <unit-id> AC-1, not in backticks", "run: `read \"b?name: \"`"):
            self.assertEqual(chainlib.placeholders(act), [], act)

    def test_a_double_backtick_span_is_read_whole(self):
        # markdown's form for a command that holds a backtick (cross-review of f8d72ef)
        act = "- tag it — run: `` git log -1 --format=`%h` `` — closes u1 AC-2"
        self.assertEqual(chainlib.run_commands(act), ["git log -1 --format=`%h`"])
        self.assertEqual(chainlib.placeholders("run: `` echo `x` <bucket> ``"), ["<bucket>"])
        self.assertEqual(chainlib.run_commands("run: `sudo rclone config`, then `x`"), ["sudo rclone config"])

    def test_on_wait_chain_next_prints_each_act_and_the_command(self):
        self.join(1, "s1")
        self.wait_handoff(1, owner=OWNER3)
        r = self.next("s1")
        self.assertEqual(r.returncode, 0, r.stdout)
        for want in ("- 1. [run] Write the R2 bucket name, one Touch ID (u1) (closes nothing)", f"   $ {CMDS[0]}",
                     "- 2. [you] Turn on FileVault (closes u1 AC-2)", "- 3. [run] Configure the remote, interactive (u1) (closes nothing)",
                     f"```sh\n{RUN}\n```", "/resume-chain ok", "listed again by `python3 .charter/bin/charter owner`", "never a summary"):
            self.assertIn(want, r.stdout)

    def test_charter_owner_prints_the_command_on_a_line_of_its_own(self):
        self.join(1, "s1")
        self.wait_handoff(1, owner=OWNER3)
        self.assertEqual(self.next("s1").returncode, 0)
        self.assertIn(RUN, charter(self.root, "owner").stdout.splitlines())
        self.assertIn(RUN, charter(self.root, "next").stdout.splitlines())
        it = {i["key"]: i for i in json.loads(charter(self.root, "owner", "--json").stdout)["items"]}[f"chain:{self.cid}"]
        self.assertEqual(it["run"], [RUN])
        self.assertIn(f"$ {CMDS[1]}", it["ask"])

    def test_the_wait_notification_points_to_charter_owner(self):
        self.join(1, "s1")
        self.wait_handoff(1, owner=OWNER3)
        self.assertEqual(self.next("s1").returncode, 0)
        self.assertIn(f"{self.cid} | 3 acts wait: run `python3 .charter/bin/charter owner` in {self.root}, `{RUN}` to run them", self.notes())

    def test_a_wait_handed_over_before_0_4_11_is_shown_as_0_4_10_showed_it(self):
        # a chain that waited before the project upgraded: its session wrote no owner.md, only `## Wait` acts
        self.join(1, "s1")
        self.wait_handoff(1, wait=PASTE, owner=None)
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"CHARTER_NOTIFY": ""}), contextlib.redirect_stdout(out):
            self.assertEqual(chainlib._hand_over(self.root, self.cid, 1, "wait", "u1", "three acts", None), 0)
        for line in PASTE.splitlines():
            self.assertIn(line + "\n", out.getvalue())
        for c in CMDS:
            self.assertIn(f"```sh\n{c}\n```", out.getvalue())
        printed = charter(self.root, "owner").stdout.splitlines()
        for c in CMDS:
            self.assertIn(c, printed)
        it = {i["key"]: i for i in json.loads(charter(self.root, "owner", "--json").stdout)["items"]}[f"chain:{self.cid}"]
        self.assertEqual(it["run"], CMDS)
        self.assertIn(f"{self.cid} | 3 acts wait: run `python3 .charter/bin/charter owner` in {self.root}, then type /resume-chain in", self.notes())
        r = resume(self.root, "ok all three done")   # 0.4.9's `ok`: every waited line
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("closed u1 AC-2 as the owner", r.stdout)

    def test_the_rules_and_the_templates_carry_the_standard(self):
        for f in (".charter/chain-rules.md", "charter/templates/handoff.md", "charter/templates/owner.md"):
            self.assertIn("paste-ready", (PKG / f).read_text(), f)


if __name__ == "__main__":
    unittest.main()
