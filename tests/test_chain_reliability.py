"""Charter 0.4.8, the chain's failure modes found on 2026-10-04. A chain in a cmux tab (chain 20261004-011522,
docs/trials/2026-10-04-chain-tab.md) ran three sessions that each started at 33% of a 150,000-token window, past the
25% hand-over line, and each committed one `## Log` line: the engine relaunched them because a commit counted as
progress, the cap refused the commit the session was told to make (its `Co-Authored-By: ... <address>` trailer read as
a redirection), and the halt told the owner to raise a budget that `chain resume` could not change. The review runner's
gaps come from the 0.4.8 cross-review: a killed runner's worktree stayed, `review.out` stayed beside `review.md`, and
`chain stop` could write back a stale copy of chain.json over the runner's. Each test here fails on 38f0e56."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from helpers import PKG, git
from test_chain_0_4_7 import VERIFIED, ChainCase, cli, env_for, transcript
from test_groups_0_4_8 import CODEX_SAMPLE, GroupCase
from test_review_regressions import commit_all

sys.path.insert(0, str(PKG / ".charter"))
import chain as chainlib  # noqa: E402
import chain_groups as groups  # noqa: E402

TRAILER = "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"


class StartUp(ChainCase):
    def setUp(self):
        super().setUp()
        self.start()
        self.cid = self.chain["id"]

    def log_line(self, n):
        u = self.root / ".taskets" / "u1.md"
        u.write_text(u.read_text().replace("## Log\n", f"## Log\n\n- session {n}: handed over at the line\n", 1))
        commit_all(self.root, f"u1: log session {n}")

    def test_a_session_that_starts_past_the_hand_over_line_halts_the_chain_and_resume_takes_a_new_budget(self):
        tp, _ = self.join(1, "s1", tokens=33_000)
        out = self.hook("PreToolUse", "s1", tp, tool_name="Bash", tool_input={"command": "printf x > app/greet.py"})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        rec = chainlib.link(self.root, self.cid, 1)
        self.assertEqual((rec["start_pct"], rec["start_tokens"]), (33.0, 33_000))
        transcript(tp, 36_000)   # later tools do not move the start-up
        self.hook("PreToolUse", "s1", tp, tool_name="Read", tool_input={"file_path": "x"})
        self.assertEqual(chainlib.link(self.root, self.cid, 1)["start_pct"], 33.0)
        self.log_line(1)
        self.write_handoff(1)
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout)
        c = chainlib.load(self.root)
        self.assertEqual(c["state"], "halted")
        self.assertIn("session 1 was at 33% of the window (33,000 tokens) at its first tool, past the 25% hand-over line", c["reason"])
        self.assertIn("charter chain resume --window", c["reason"])
        self.assertFalse(chainlib.link_dir(self.root, self.cid, 2).exists())
        r = cli(self.root, "resume", "--wrap", "50", "--cap", "45")
        self.assertEqual(r.returncode, 1)
        self.assertIn("0 < wrap (50) < cap (45) <= 100", r.stdout)
        self.assertEqual(chainlib.load(self.root)["state"], "halted")   # nothing recorded
        r = cli(self.root, "resume", "--window", "200000", "--wrap", "40", "--cap", "45")
        self.assertEqual(r.returncode, 0, r.stdout)
        c = chainlib.load(self.root)
        self.assertEqual((c["state"], c["window"], c["wrap_pct"], c["cap_pct"]), ("running", 200_000, 40, 45))
        self.assertIn("Context window 200,000 tokens. Hand over at 40%", self.launched(2))
        self.assertIn("chain budget: hand over at 40%, cap 45% of 200,000 tokens (was 25%, 30% of 100,000)", self.events())

    def test_the_start_up_is_compared_in_tokens_not_in_its_rounded_share(self):
        c = dict(self.chain, window=200_000, wrap_pct=25)
        self.assertEqual(chainlib.started_past_line(c, {"n": 1, "start_pct": 25.0, "start_tokens": 49_999}), "")
        self.assertIn("past the 25% hand-over line", chainlib.started_past_line(c, {"n": 1, "start_pct": 25.0, "start_tokens": 50_000}))

    def test_a_session_whose_start_up_is_under_the_line_goes_on(self):
        tp, _ = self.join(1, "s1", tokens=20_000)
        self.hook("PreToolUse", "s1", tp, tool_name="Read", tool_input={"file_path": "x"})
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a\n\n\n# u1 groundwork\n")
        commit_all(self.root, "groundwork")
        transcript(tp, 26_000)
        self.write_handoff(1)
        self.assertEqual(cli(self.root, "next", sid="s1").returncode, 0)
        self.assertEqual(chainlib.load(self.root)["state"], "running")
        self.launched(2)

    def test_sessions_that_commit_only_unit_files_are_stalled(self):
        for n, sid in ((1, "s1"), (2, "s2")):
            self.join(n, sid)
            self.log_line(n)
            self.write_handoff(n, verified=VERIFIED if n > 1 else "first session")
            r = cli(self.root, "next", sid=sid)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertEqual(chainlib.link(self.root, self.cid, n)["nums"]["work"], 0)
        c = chainlib.load(self.root)
        self.assertEqual(c["state"], "halted")
        self.assertIn("sessions 1 and 2 changed nothing outside .taskets/ and checked no criterion", c["reason"])

    def test_the_start_names_a_hand_over_line_under_the_measured_start_up(self):
        prior = chainlib.link_dir(self.root, "20261004-011522", 1)
        prior.mkdir(parents=True)
        (prior / "link.json").write_text(json.dumps({"n": 1, "start_pct": 33.0, "start_tokens": 49_500}))
        cli(self.root, "stop")
        r = cli(self.root, "start", "--unit", "u1", "--launcher", self.launcher, "--window", "150000", "--dry-run")
        self.assertIn("warning: the hand-over line (37,500 tokens) is at or under a session's start-up "
                      "(49,500 tokens, measured in chain 20261004-011522)", r.stdout)
        r = cli(self.root, "start", "--unit", "u1", "--launcher", self.launcher, "--window", "400000", "--dry-run")
        self.assertIn("warning: a 400,000-token window leaves little room: start-up alone takes about 49,500 tokens", r.stdout)

    def test_the_start_estimates_the_start_up_by_launcher_when_none_was_measured(self):
        cli(self.root, "stop")
        r = cli(self.root, "start", "--unit", "u1", "--launcher", "headless", "--model", "sonnet", "--dry-run")
        self.assertIn("start-up alone takes about 33,000 tokens (16% of it, estimated for the headless launcher", r.stdout)


class CapCommands(ChainCase):
    def setUp(self):
        super().setUp()
        self.start()
        self.tp, _ = self.join(1, "s1", tokens=31_000)

    def decide(self, command):
        out = self.hook("PreToolUse", "s1", self.tp, tool_name="Bash", tool_input={"command": command})
        return out.get("hookSpecificOutput", {}).get("permissionDecision", "allow"), out

    def test_a_commit_with_a_trailer_or_a_heredoc_message_goes_through_at_the_cap(self):
        allowed = [f'git add .taskets/u1.md && git commit -qm "u1: log session 3 halt\n\n{TRAILER}"',
                   f'git commit -q -m "u1: log" -m "{TRAILER}"',
                   f"git commit -q -m \"$(cat <<'EOF'\nu1: log session 3 halt\n\n{TRAILER}\nEOF\n)\"",
                   "git status;\ngit log -1 --format='%h <%ae>'",
                   "git add .taskets/u1.md\ngit commit -m 'u1: a > b'", "git -C . commit -c HEAD", "git log --format=%H -1"]
        for c in allowed:
            self.assertEqual(self.decide(c)[0], "allow", c)
        refused = ["echo '- session 3: halted' >> .taskets/u1.md", 'git commit -m "$(rm -rf app)"', "git log 2>&1",
                   "cd app && git status", 'git commit -m "unterminated', "git log | tee x", "(git status)",
                   "git commit -m \"$(cat <<EOF\n$(rm -rf app)\nEOF\n)\"", "git log ';' rm -rf app",
                   "git -c alias.x='!touch app/x' x", "git -C . -c core.pager='sh -c id' log", "git --config-env=core.pager=X log",
                   "git config alias.x '!touch app/x'", "git --exec-path=/tmp log"]
        for c in refused:
            d, out = self.decide(c)
            self.assertEqual(d, "deny", c)
        self.assertIn("What passes: Edit or Write on the handoff and on .taskets/ files", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_plain_commands_reads_quotes_operators_and_newlines(self):
        pc = chainlib.plain_commands
        self.assertEqual(pc(f'git add x && git commit -m "a\n\nb <c@d>"'), [["git", "add", "x"], ["git", "commit", "-m", "a\n\nb <c@d>"]])
        self.assertEqual(pc("git status\n\ngit log;\n"), [["git", "status"], ["git", "log"]])
        msg = "git commit -m \"$(cat <<'EOF'\nfix\nEOF\n)\""
        self.assertEqual(pc(msg), [["git", "commit", "-m", "MESSAGE"]])
        # as in bash, an indented EOF does not end the message, so what follows it is message text, not a command
        self.assertEqual(pc("git commit -m \"$(cat <<'EOF'\n  EOF\n)\"\nrm -rf app\nEOF\n)\""), [["git", "commit", "-m", "MESSAGE"]])
        self.assertIsNone(pc("git commit -m \"$(cat <<EOF\n$(rm -rf app)\nEOF\n)\""))   # an unquoted delimiter expands its body
        for bad in ("git log > x", "git log &", "git log `x`", "git log $(x)", "git log <(x)", "a 'b"):
            self.assertIsNone(pc(bad), bad)


class Runner(GroupCase):
    def test_a_review_drops_what_a_killed_runner_left_and_keeps_no_output_beside_its_record(self):
        self.answer(CODEX_SAMPLE)
        self.start()
        left = groups.review_tmp(self.root, self.state())
        self.assertTrue(str(left).startswith(tempfile.gettempdir()))
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(left)]))
        r = git(self.root, "worktree", "add", "--detach", str(left / "tree"), "HEAD")   # a runner killed with SIGKILL
        self.assertEqual(r.returncode, 0, r.stderr)
        self.join(1, "s1")
        sha = self.work()
        self.assertEqual(self.hand_over(1, "s1", next_unit="u3", done=f"- u1: retries, {sha[:7]}").returncode, 0)
        self.launched(2)
        self.assertFalse(left.exists())
        self.assertEqual(len(git(self.root, "worktree", "list").stdout.splitlines()), 1)
        d = groups.group_dir(self.root, self.cid, 1)
        self.assertTrue((d / "review.md").exists())
        self.assertFalse((d / "review.out").exists())


class GroupFindings(GroupCase):
    """The Codex review of 0.4.8 (2026-10-04, `codex exec review --base chain-0.4.7`)."""

    def test_a_complete_road_halted_as_broken_resumes_with_a_repair_session_not_a_review(self):
        self.start()
        self.join(1, "s1")
        u = self.root / ".taskets" / "u1.md"
        u.write_text(u.read_text().replace("status: next", "status: done").replace("- [ ] AC-1", "- [x] AC-1")
                     .replace("## Evidence\n", "## Evidence\n\n- `$ python3 -c ...` → exit 0\n"))
        commit_all(self.root, "u1 done")
        (self.root / "app" / "health.py").write_text("MAX_RETRIES = 4\n\n\ndef health():\n    return {'ok': True, 'retries': MAX_RETRIES}\n")
        commit_all(self.root, "a later change breaks u1")
        self.assertEqual(self.hand_over(1, "s1", status="complete", next_unit="none", done="- u1 closed").returncode, 0)
        self.assertIn("probes of a unit it closed fail now", self.state()["reason"])
        r = cli(self.root, "resume", "--note", "repair u1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("repair u1", self.launched(2))
        self.assertEqual((self.calls(), self.state()["state"]), ([], "running"))

    def test_a_fix_off_the_chains_branch_does_not_answer_a_finding(self):
        end = git(self.root, "rev-parse", "HEAD").stdout.strip()
        here = git(self.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        git(self.root, "checkout", "-q", "-b", "side")
        side = self.work(line="# fixed on a side branch")
        git(self.root, "checkout", "-q", here)
        self.assertFalse(groups._after(self.root, end, side))
        self.assertTrue(groups._after(self.root, end, self.work(line="# fixed here")))

    def test_the_report_keeps_the_reviewed_rounds_of_a_group_whose_later_review_was_skipped(self):
        self.start()
        ch = self.state()
        g = ch["groups"][0]
        g.update(state="cleared", cleared="c" * 40, skipped=True, base="b" * 40, end="c" * 40,
                 rounds=[{"base": "a" * 40, "end": "b" * 40, "findings": [{"id": "R1"}], "fix_session": 2, "review_file": "review.md"}])
        chainlib.save(self.root, ch)
        d = groups.group_dir(self.root, self.cid, 1)
        d.mkdir(parents=True, exist_ok=True)
        (d / "review.md").write_text("- [P1] Average the middle pair — app/health.py:2\n")
        rep = cli(self.root, "report").stdout
        self.assertIn("- [P1] Average the middle pair — app/health.py:2", rep)
        self.assertIn("Review of this range skipped by the owner.", rep)


class StopAndRunner(ChainCase):
    def test_a_hand_over_records_under_the_chain_lock(self):
        self.start()
        self.join(1, "s1")
        self.write_handoff(1)
        with chainlib.chain_lock(self.root, self.chain["id"]):
            p = subprocess.Popen([sys.executable, "-B", str(self.root / ".charter" / "bin" / "charter"), "--root", str(self.root),
                                  "chain", "next"], cwd=str(self.root), stdout=subprocess.PIPE, text=True,
                                 env=env_for("s1"))
            time.sleep(1.5)
            self.assertIsNone(p.poll(), "chain next recorded while a stop or the runner held the chain state")
            self.assertNotIn("closed_at", chainlib.link(self.root, self.chain["id"], 1))
        out, _ = p.communicate(timeout=60)
        self.assertEqual(p.returncode, 0, out)
        self.assertIn("session 1 closed (continue)", out)

    def test_stop_waits_for_the_runner_to_finish_writing_the_chain_state(self):
        self.start()
        cid = self.chain["id"]
        self.join(1, "s1")
        with chainlib.chain_lock(self.root, cid):
            p = subprocess.Popen([sys.executable, "-B", str(self.root / ".charter" / "bin" / "charter"), "--root", str(self.root),
                                  "chain", "stop"], cwd=str(self.root), stdout=subprocess.PIPE, text=True)
            time.sleep(1.0)
            self.assertIsNone(p.poll(), "stop ran while the runner held the chain state")
        out, _ = p.communicate(timeout=30)
        self.assertEqual(p.returncode, 0)
        self.assertIn("stop requested", out)


if __name__ == "__main__":
    unittest.main()
