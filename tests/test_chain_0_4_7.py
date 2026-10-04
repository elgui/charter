"""Charter 0.4.7: the continuous chain. A run of sessions works the road one unit after another; each session is
joined to the chain by the hook from a marker in its first prompt and receives the rules verbatim from
`.charter/chain-rules.md`, works under a context budget the hook measures from its transcript (told to hand over
at the wrap line, refused all but the handoff past the cap), and hands over through `charter chain next`, which
validates the handoff, verifies the session's work mechanically and launches the next one. Asked for on
2026-10-04: "No session should go over 30% of context usage", "each session should eventually verify what has
done the previous one", "fix those rules ... to prevent deterioration" (docs/design/continuous-chain.md).
Every test here fails on 0.4.6, which has no chain."""
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

from helpers import PKG, cleanup, git, make_project, run_hook
from test_migration import pkg
from test_review_regressions import commit_all

sys.path.insert(0, str(PKG / ".charter"))
import chain as chainlib  # noqa: E402


def env_for(sid=None):
    """The environment of a Bash command in a Claude Code session (sid), or of a plain shell (None)."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CHARTER_OWNER", "CHARTER_UNIT") and not k.startswith("CLAUDE_CODE_")}
    if sid:
        env["CLAUDE_CODE_SESSION_ID"] = sid
    return env


def cli(root, *args, sid=None):
    return subprocess.run([sys.executable, "-B", str(root / ".charter" / "bin" / "charter"), "--root", str(root), "chain", *args],
                          capture_output=True, text=True, cwd=str(root), env=env_for(sid))


def transcript(path, tokens, sidechain_tokens=None):
    """A transcript whose last main-chain response puts `tokens` in the context."""
    rows = [{"type": "user", "message": {"content": "hi"}},
            {"type": "assistant", "message": {"usage": {"input_tokens": 3, "cache_read_input_tokens": tokens - 13,
                                                        "cache_creation_input_tokens": 0, "output_tokens": 10}}}]
    if sidechain_tokens:
        rows.append({"type": "assistant", "isSidechain": True, "message": {"usage": {"input_tokens": sidechain_tokens, "output_tokens": 1}}})
    Path(path).write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def handoff(cid, n, status="continue", next_unit="u1", verified="first session", done="- nothing landed",
            state="u1 is active, AC-1 open", nxt="run the u1 probe", halt=""):
    return (f"---\nchain: {cid}\nsession: {n}\nstatus: {status}\nnext_unit: {next_unit}\n---\n\n"
            f"## Verified\n\n{verified}\n\n## Done\n\n{done}\n\n## State\n\n{state}\n\n## Next\n\n{nxt}\n\n## Watch out\n\nnone\n"
            + (f"\n## Halt\n\n{halt}\n" if halt else ""))


VERIFIED = "- `$ python3 .charter/bin/charter probe u1` → exit 0"


class ChainCase(unittest.TestCase):
    """A charter project on main with a chain started on u1; sessions are 'launched' by a command that copies the
    briefing to <out>/<goal>.md, and joined by feeding that briefing to the hook as the session's first prompt."""

    WINDOW = 100_000

    def setUp(self):
        self.root = make_project(track="prototype")
        self.out = Path(self.root.parent / (self.root.name + "-launched"))
        self.out.mkdir()
        self.launcher = f"{sys.executable} -c \"import shutil,sys; shutil.copy(sys.argv[1], sys.argv[2])\" {{briefing}} {self.out}/{{goal}}.md"

    def tearDown(self):
        cleanup(self.root)
        cleanup(self.out)

    def start(self, *extra, mission="go with unit 1, keep going while things go well"):
        # the group review of 0.4.8 is off here: `auto` is Codex wherever it is on PATH (tests/test_groups_0_4_8.py has it)
        r = cli(self.root, "start", "--unit", "u1", "--mission", mission, "--window", str(self.WINDOW), "--launcher", self.launcher,
                "--review", "off", *extra)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.chain = chainlib.load(self.root)
        return r

    def launched(self, n):
        """The briefing session n was launched with, once the detached launcher has copied it."""
        p = self.out / f"chain {self.chain['id']} s{n:02d}.md"
        for _ in range(100):
            if p.exists() and p.stat().st_size:
                return p.read_text()
            time.sleep(0.05)
        self.fail(f"session {n} was not launched: {sorted(x.name for x in self.out.iterdir())}")

    def join(self, n, sid, tokens=27_000):
        tp = self.root.parent / f"{self.root.name}-{sid}.jsonl"
        transcript(tp, tokens)
        self.addCleanup(lambda: tp.unlink(missing_ok=True))
        code, out, raw, err = run_hook(self.root, "chain_gate", {"hook_event_name": "UserPromptSubmit", "session_id": sid,
                                                                 "prompt": self.launched(n), "transcript_path": str(tp)})
        self.assertEqual(code, 0, err)
        return tp, out

    def hook(self, event, sid, tp, **payload):
        code, out, raw, err = run_hook(self.root, "chain_gate", dict({"hook_event_name": event, "session_id": sid,
                                                                      "transcript_path": str(tp)}, **payload))
        self.assertEqual(code, 0, err)
        return out

    def write_handoff(self, n, **kw):
        p = chainlib.link_dir(self.root, self.chain["id"], n) / "handoff.md"
        p.write_text(handoff(self.chain["id"], n, **kw))
        return p

    def events(self):
        return (chainlib.chain_dir(self.root, self.chain["id"]) / "events.log").read_text()


class Start(ChainCase):
    def test_start_on_main_branches_records_and_launches_session_1_with_the_mission_verbatim(self):
        r = self.start()
        cid = self.chain["id"]
        self.assertEqual(git(self.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), f"chain/{cid}")
        self.assertEqual(self.chain["state"], "running")
        self.assertEqual(self.chain["rules_sha"], chainlib.rules_sha(self.root))
        self.assertEqual((self.chain["wrap_pct"], self.chain["cap_pct"], self.chain["window"]), (25, 30, self.WINDOW))
        b = self.launched(1)
        self.assertTrue(b.startswith(f"charter-chain: {cid} session 1\n"), b[:80])
        self.assertIn("go with unit 1, keep going while things go well", b)
        self.assertIn("charter unit start u1", b)
        self.assertIn(str(chainlib.link_dir(self.root, cid, 1) / "handoff.md"), b)
        ev = self.events()
        self.assertIn("chain started:", ev)
        self.assertIn("s01 launched:", ev)
        self.assertIn(f"chain watch {cid}", r.stdout)

    def test_a_small_window_is_named_at_the_start(self):
        r = cli(self.root, "start", "--unit", "u1", "--launcher", self.launcher, "--model", "sonnet", "--dry-run")
        self.assertIn("warning: a 200,000-token window leaves little room", r.stdout)
        r = cli(self.root, "start", "--unit", "u1", "--launcher", self.launcher, "--model", "opus[1m]", "--dry-run")
        self.assertNotIn("warning", r.stdout)

    def test_here_stays_on_main(self):
        self.start("--here")
        self.assertEqual(git(self.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "main")

    def test_dry_run_writes_nothing_and_refusals_name_their_reason(self):
        r = cli(self.root, "start", "--unit", "u1", "--launcher", self.launcher, "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("nothing written", r.stdout)
        self.assertEqual(chainlib.load(self.root), {})
        self.assertEqual(git(self.root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), "main")
        (self.root / "app" / "billing.py").write_text("x = 1\n")
        r = cli(self.root, "start", "--unit", "nope", "--launcher", "headless-typo", "--wrap", "30", "--cap", "25")
        self.assertEqual(r.returncode, 1)
        for why in ("uncommitted change", "no tasket 'nope'", "launcher 'headless-typo'", "0 < wrap (30) < cap (25)"):
            self.assertIn(why, r.stdout)

    def test_a_second_chain_is_refused_while_one_runs(self):
        self.start("--here")
        r = cli(self.root, "start", "--unit", "u1", "--launcher", self.launcher)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"chain {self.chain['id']} is running", r.stdout)

    def test_a_launch_that_fails_halts_the_chain(self):
        r = cli(self.root, "start", "--unit", "u1", "--launcher", "/nonexistent/launcher {briefing}", "--here")
        self.assertEqual(r.returncode, 1)
        c = chainlib.load(self.root)
        self.assertEqual(c["state"], "halted")
        self.assertIn("launching session 1 failed", c["reason"])


class JoinAndRules(ChainCase):
    def test_the_marker_joins_the_session_and_the_rules_arrive_verbatim(self):
        self.start()
        tp, out = self.join(1, "sess-a")
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(ctx.startswith((self.root / ".charter" / "chain-rules.md").read_text().rstrip()), ctx[:200])
        self.assertIn("hand over at 25%, cap 30% of 100,000 tokens", ctx)
        rec = chainlib.link(self.root, self.chain["id"], 1)
        self.assertEqual((rec["session_id"], rec["start_head"]), ("sess-a", chainlib.head(self.root)))
        self.assertTrue((chainlib.base_dir(self.root) / "sessions" / "sess-a").exists())
        self.assertIn("s01 joined:", self.events())

    def test_a_second_session_cannot_take_a_joined_link(self):
        self.start()
        self.join(1, "sess-a")
        _, out = self.join(1, "sess-b")
        self.assertIn("already joined by another Claude Code session", out["hookSpecificOutput"]["additionalContext"])
        self.assertFalse((chainlib.base_dir(self.root) / "sessions" / "sess-b").exists())

    def test_rules_changed_after_the_start_halt_the_chain_at_the_next_join(self):
        self.start()
        (self.root / ".charter" / "chain-rules.md").write_text("# Charter chain rules\n\nDo whatever.\n")
        _, out = self.join(1, "sess-a")
        self.assertIn("halted: its rules changed", out["hookSpecificOutput"]["additionalContext"])
        self.assertNotIn("Do whatever", out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(chainlib.load(self.root)["state"], "halted")

    def test_a_prompt_without_the_marker_and_a_session_outside_the_chain_get_nothing(self):
        self.start()
        tp = self.root.parent / f"{self.root.name}-plain.jsonl"
        transcript(tp, 99_000)
        self.addCleanup(lambda: tp.unlink(missing_ok=True))
        for ev, extra in (("UserPromptSubmit", {"prompt": "fix the bug"}), ("PreToolUse", {"tool_name": "Read", "tool_input": {}}),
                          ("PostToolUse", {"tool_name": "Read", "tool_input": {}, "tool_response": "x"}), ("Stop", {})):
            code, out, raw, err = run_hook(self.root, "chain_gate", dict({"hook_event_name": ev, "session_id": "outsider",
                                                                          "transcript_path": str(tp)}, **extra))
            self.assertEqual((code, raw.strip(), err.strip()), (0, "", ""), ev)

    def test_the_rules_file_is_the_owners(self):
        code, out, raw, err = run_hook(self.root, "pre_tool_gate", {"tool_name": "Edit", "tool_input": {
            "file_path": str(self.root / ".charter" / "chain-rules.md"), "old_string": "# Charter chain rules", "new_string": "# Rules"}})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")


class Budget(ChainCase):
    def setUp(self):
        super().setUp()
        self.start()
        self.hp = str(chainlib.link_dir(self.root, self.chain["id"], 1) / "handoff.md")

    def test_context_is_read_from_the_main_chain_only(self):
        tp = self.root.parent / f"{self.root.name}-t.jsonl"
        transcript(tp, 12_345, sidechain_tokens=500_000)
        self.addCleanup(lambda: tp.unlink(missing_ok=True))
        self.assertEqual(chainlib.context_tokens(tp), 12_345)
        self.assertIsNone(chainlib.context_tokens(self.root / "missing.jsonl"))
        self.assertEqual(chainlib.window_for("opus[1m]"), 1_000_000)
        self.assertEqual(chainlib.window_for("sonnet"), 200_000)
        self.assertEqual(chainlib.window_for("opus[1m]", 400_000), 400_000)

    def test_usage_is_reported_every_5_points_and_the_wrap_line_says_hand_over(self):
        tp, _ = self.join(1, "s1", tokens=11_000)
        out = self.hook("PostToolUse", "s1", tp, tool_name="Read", tool_input={}, tool_response="")
        self.assertIn("context 11% of the window (hand over at 25%)", out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.hook("PostToolUse", "s1", tp, tool_name="Read", tool_input={}, tool_response=""), {})
        transcript(tp, 25_500)
        out = self.hook("PostToolUse", "s1", tp, tool_name="Read", tool_input={}, tool_response="")
        msg = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("past the 25% hand-over line", msg)
        self.assertIn(self.hp, msg)
        self.assertIn("s01 wrap: context 26%", self.events())
        self.assertGreaterEqual(chainlib.link(self.root, self.chain["id"], 1)["peak_pct"], 25.5)

    def test_a_large_tool_result_counts_before_the_next_response_does(self):
        tp, _ = self.join(1, "s1", tokens=20_000)
        out = self.hook("PostToolUse", "s1", tp, tool_name="Read", tool_input={}, tool_response="x" * 24_000)
        self.assertIn("past the 25% hand-over line", out["hookSpecificOutput"]["additionalContext"])

    def test_past_the_cap_only_the_handoff_goes_through(self):
        tp, _ = self.join(1, "s1", tokens=31_000)
        allowed = [("Write", {"file_path": self.hp, "content": "x"}),
                   ("Edit", {"file_path": str(self.root / ".taskets" / "u1.md"), "old_string": "a", "new_string": "b"}),
                   ("Bash", {"command": "git add -A && git commit -m 'u1: retries'"}),
                   ("Bash", {"command": "python3 .charter/bin/charter chain next"}),
                   ("Bash", {"command": "python3 -B .charter/bin/charter probe u1"})]
        for tool, ti in allowed:
            self.assertEqual(self.hook("PreToolUse", "s1", tp, tool_name=tool, tool_input=ti), {}, (tool, ti))
        refused = [("Read", {"file_path": str(self.root / "app" / "health.py")}),
                   ("Write", {"file_path": str(self.root / "app" / "health.py"), "content": "x"}),
                   ("Bash", {"command": "git status && pytest -q"}), ("Agent", {"prompt": "search"}),
                   ("Bash", {"command": "git show HEAD:app/health.py > app/billing.py"}),
                   ("Bash", {"command": "git log | tee app/billing.py"}),
                   ("Bash", {"command": "git status & rm -rf app"}),
                   ("Bash", {"command": "git log $(rm -rf app)"}), ("Bash", {"command": "git log `rm -rf app`"})]
        for tool, ti in refused:
            out = self.hook("PreToolUse", "s1", tp, tool_name=tool, tool_input=ti)
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny", (tool, ti))
            self.assertIn("past the 30% cap", out["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertEqual(self.events().count("s01 cap:"), 1)

    def test_under_the_cap_tools_pass_and_a_question_to_the_owner_never_does(self):
        tp, _ = self.join(1, "s1", tokens=10_000)
        self.assertEqual(self.hook("PreToolUse", "s1", tp, tool_name="Read", tool_input={"file_path": "x"}), {})
        out = self.hook("PreToolUse", "s1", tp, tool_name="AskUserQuestion", tool_input={})
        self.assertIn("status: halt", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_a_session_cannot_end_its_turn_before_handing_over_and_a_third_stop_is_let_go_as_stalled(self):
        tp, _ = self.join(1, "s1", tokens=10_000)
        out = self.hook("Stop", "s1", tp)
        self.assertEqual(out["decision"], "block")
        self.assertIn("has budget left (10% of the window", out["reason"])
        self.hook("PostToolUse", "s1", tp, tool_name="Read", tool_input={}, tool_response="")   # it worked: the count restarts
        transcript(tp, 26_000)
        self.assertIn("write " + self.hp, self.hook("Stop", "s1", tp)["reason"])
        self.assertEqual(self.hook("Stop", "s1", tp)["decision"], "block")
        self.assertEqual(self.hook("Stop", "s1", tp), {})
        self.assertIn("s01 stalled:", self.events())
        self.assertIn("ended its turn three times", self.events())


class HandoffCheck(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        self.chain = {"id": "c1"}

    def tearDown(self):
        cleanup(self.root)

    def test_the_template_as_written_is_refused(self):
        text = (PKG / "charter" / "templates" / "handoff.md").read_text().replace("<chain id>", "c1").replace("<n>", "1")
        problems = chainlib.check_handoff(self.root, self.chain, 1, text)
        for s in chainlib.SECTIONS:
            self.assertIn(f"`## {s}` is missing or empty", problems)
        self.assertTrue(any("next_unit" in p for p in problems))

    def test_a_filled_handoff_passes_and_each_defect_is_named(self):
        sha = git(self.root, "rev-parse", "--short", "HEAD").stdout.strip()
        ok = handoff("c1", 2, verified=VERIFIED, done=f"- u1: retries in health(), {sha}", state="u1 active; session 3003bdde ran it")
        self.assertEqual(chainlib.check_handoff(self.root, self.chain, 2, ok), [])
        cases = [(handoff("c2", 2, verified=VERIFIED), "`chain:` is 'c2', not c1"),
                 (handoff("c1", 3, verified=VERIFIED), "`session:` is 3, not 2"),
                 (handoff("c1", 2, status="paused", verified=VERIFIED), "`status:` is 'paused'"),
                 (handoff("c1", 2, verified="looked at it, fine"), "`## Verified` cites no `$ command`"),
                 (handoff("c1", 2, verified=VERIFIED, done="- u1: landed in deadbeefcafe"), "do not resolve: deadbeefcafe"),
                 (handoff("c1", 2, status="halt", next_unit="none", verified=VERIFIED), "`status: halt` needs `## Halt`"),
                 (handoff("c1", 2, verified=VERIFIED, state="x\n" * 90), "a handoff holds at most 80 lines")]
        for text, why in cases:
            problems = chainlib.check_handoff(self.root, self.chain, 2, text)
            self.assertTrue(any(why in p for p in problems), (why, problems))

    def test_config_takes_a_chain_section_and_names_a_wrong_type(self):
        import lib
        cfg = lib.config_from({"chain": {"wrap_pct": 20, "effort": "medium"}})
        self.assertEqual((cfg["chain"]["wrap_pct"], cfg["chain"]["cap_pct"], cfg["chain"]["effort"]), (20, 30, "medium"))
        self.assertEqual(cfg[lib.PROBLEMS], [])
        cfg = lib.config_from({"chain": {"cap_pct": "30%"}})
        self.assertTrue(any("chain.cap_pct" in p for p in cfg[lib.PROBLEMS]), cfg[lib.PROBLEMS])


class Next(ChainCase):
    def setUp(self):
        super().setUp()
        self.start()
        self.cid = self.chain["id"]

    def test_only_a_chain_session_hands_over_for_itself(self):
        self.join(1, "s1")
        self.write_handoff(1)
        r = cli(self.root, "next", sid="the-monitor")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not a session of the chain", r.stdout)
        self.assertEqual(cli(self.root, "next", "--check", "--session", "1", sid="the-monitor").returncode, 0)

    def test_no_handoff_or_a_bad_one_is_refused_and_nothing_is_recorded(self):
        self.join(1, "s1")
        r = cli(self.root, "next", sid="s1")
        self.assertIn("no handoff at", r.stdout)
        self.write_handoff(1, state="")
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a * 2\n")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("`## State` is missing or empty", r.stdout)
        self.assertIn("uncommitted change(s) the handoff's `## State` does not name: app/billing.py", r.stdout)
        self.assertNotIn("closed_at", chainlib.link(self.root, self.cid, 1))
        self.write_handoff(1, state="app/billing.py is half-done: the doubling has no test yet")
        self.assertEqual(cli(self.root, "next", sid="s1").returncode, 0)

    def test_a_new_file_left_out_of_every_commit_is_uncommitted_work(self):
        self.join(1, "s1")
        (self.root / "app" / "slug.py").write_text("def slugify(s):\n    return s\n")
        self.write_handoff(1)
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not name: app/slug.py", r.stdout)
        # a file that was already untracked when the session was launched is not the session's
        self.assertEqual(chainlib.uncommitted(self.root, {"untracked_at_launch": ["app/slug.py"]}), [])

    def test_a_session_on_another_branch_cannot_hand_over(self):
        self.join(1, "s1")
        git(self.root, "checkout", "-q", "-b", "elsewhere")
        self.write_handoff(1)
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"HEAD is on elsewhere, and the chain works on chain/{self.cid}", r.stdout)

    def test_a_session_that_joins_while_it_is_launched_stays_joined(self):
        real = chainlib.launch

        def launch_and_join(root, chain, n, brief):
            chainlib.join(root, chain, n, "fast-session", "")   # the hook, before the shim has returned
            return {"ok": True, "ready": True, "id": "local-1", "note": "", "where": "test"}
        chainlib.launch = launch_and_join
        try:
            chainlib.start_link(self.root, chainlib.load(self.root), 2, ("handoff", "facts"))
        finally:
            chainlib.launch = real
        rec = chainlib.link(self.root, self.cid, 2)
        self.assertEqual((rec.get("session_id"), rec.get("backend_id")), ("fast-session", "local-1"))

    def test_handing_over_early_needs_a_reason(self):
        self.join(1, "s1", tokens=5_000)
        self.write_handoff(1)
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("context is at 5%, under the 25% hand-over line", r.stdout)
        r = cli(self.root, "next", "--early", "u1 is done and u2 needs the owner's design", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("s01 early: u1 is done and u2 needs the owner's design", self.events())

    def test_a_session_that_landed_nothing_works_on_up_to_the_hand_over_line(self):
        tp, _ = self.join(1, "s1", tokens=24_000)
        self.write_handoff(1)
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("context is at 24%, under the 25% hand-over line, nothing is committed yet", r.stdout)
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a\n\n\n# u1 groundwork\n")
        commit_all(self.root, "groundwork")
        self.assertEqual(cli(self.root, "next", sid="s1").returncode, 0)

    def test_a_handover_records_verifies_and_launches_the_next_session_with_the_handoff_verbatim(self):
        self.join(1, "s1")
        u = self.root / ".taskets" / "u1.md"
        u.write_text(u.read_text().replace("status: next", "status: now").replace("- [ ] AC-1", "- [x] AC-1"))
        (self.root / "app" / "health.py").write_text((self.root / "app" / "health.py").read_text() + "\n# checked\n")
        commit_all(self.root, "u1: health reports retries")
        sha = git(self.root, "rev-parse", "--short", "HEAD").stdout.strip()
        self.write_handoff(1, done=f"- u1: AC-1 checked, {sha}", nxt="close u1: evidence and status done")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("session 1 closed (continue)", r.stdout)
        rec = chainlib.link(self.root, self.cid, 1)
        self.assertEqual((rec["status"], rec["nums"]["commits"], rec["nums"]["box_delta"]), ("continue", 1, 1))
        facts = (chainlib.link_dir(self.root, self.cid, 1) / "facts.md").read_text()
        self.assertIn(f"{sha} u1: health reports retries", facts)
        self.assertIn("- u1: next -> now, 1/1 criteria checked", facts)
        self.assertIn("Gates on the session's change set", facts)
        b = self.launched(2)
        self.assertTrue(b.startswith(f"charter-chain: {self.cid} session 2\n"))
        self.assertIn(handoff(self.cid, 1, done=f"- u1: AC-1 checked, {sha}", nxt="close u1: evidence and status done").strip(), b)
        self.assertIn(facts.strip(), b)
        self.assertIn("go with unit 1, keep going while things go well", b)
        self.assertEqual(self.hook("Stop", "s1", self.root / "none.jsonl"), {})   # closed: it may end its turn
        self.assertIn("s01 closed: continue; 1 commit(s)", self.events())
        self.assertIn("s02 launched:", self.events())

    def test_a_unit_closed_in_the_session_has_its_probes_rerun(self):
        self.join(1, "s1")
        u = self.root / ".taskets" / "u1.md"
        u.write_text(u.read_text().replace("status: next", "status: done").replace("- [ ] AC-1", "- [x] AC-1")
                     .replace("## Evidence\n", "## Evidence\n\n- `$ python3 -c ...` → exit 0\n"))
        commit_all(self.root, "u1 done")
        (self.root / "app" / "health.py").write_text("MAX_RETRIES = 4\n\n\ndef health():\n    return {'ok': True, 'retries': MAX_RETRIES}\n")
        commit_all(self.root, "a later change breaks u1")
        self.write_handoff(1, status="complete", next_unit="none", done="- u1 closed")
        r = cli(self.root, "next", sid="s1")
        self.assertEqual(r.returncode, 0, r.stdout)
        facts = (chainlib.link_dir(self.root, self.cid, 1) / "facts.md").read_text()
        self.assertIn("Probes of u1, closed this session, re-run now: FAILED", facts)
        self.assertIn("probes FAILED", self.events())
        c = chainlib.load(self.root)   # no session follows to repair it, so the chain does not end as complete
        self.assertEqual(c["state"], "halted")
        self.assertIn("says the road is finished, but probes of a unit it closed fail now", c["reason"])

    def test_halt_complete_stop_and_the_session_limit_end_the_chain(self):
        for kw, state, why in ((dict(status="halt", next_unit="none", halt="- u2 needs a decision on the cache"), "halted", "u2 needs a decision on the cache"),
                               (dict(status="complete", next_unit="none"), "complete", "found the road finished")):
            self.setUp()
            self.join(1, "s1")
            self.write_handoff(1, **kw)
            self.assertEqual(cli(self.root, "next", sid="s1").returncode, 0)
            c = chainlib.load(self.root)
            self.assertEqual(c["state"], state)
            self.assertIn(why, c["reason"])
            self.assertFalse((chainlib.link_dir(self.root, c["id"], 2)).exists())
            self.tearDown()
        self.setUp()
        self.join(1, "s1")
        self.assertIn("stop requested", cli(self.root, "stop").stdout)
        tp = self.root.parent / f"{self.root.name}-s1.jsonl"
        out = self.hook("PostToolUse", "s1", tp, tool_name="Read", tool_input={}, tool_response="")
        self.assertIn("the chain is stopping", out["hookSpecificOutput"]["additionalContext"])
        self.write_handoff(1)
        cli(self.root, "next", sid="s1")
        self.assertEqual(chainlib.load(self.root)["state"], "stopped")

    def test_two_sessions_that_land_nothing_halt_the_chain_as_stalled(self):
        self.join(1, "s1")
        self.write_handoff(1)
        cli(self.root, "next", sid="s1")
        self.join(2, "s2")
        self.write_handoff(2, verified=VERIFIED)
        r = cli(self.root, "next", sid="s2")
        self.assertEqual(r.returncode, 0, r.stdout)
        c = chainlib.load(self.root)
        self.assertEqual(c["state"], "halted")
        self.assertIn("changed nothing outside .taskets/ and checked no criterion", c["reason"])

    def test_resume_after_a_halt_carries_the_owners_note_and_watch_prints_every_event(self):
        self.join(1, "s1")
        self.write_handoff(1, status="halt", next_unit="none", halt="- which cache: redis or memory?")
        cli(self.root, "next", sid="s1")
        r = cli(self.root, "resume", "--note", "memory cache; record it as a decision")
        self.assertEqual(r.returncode, 0, r.stdout)
        b = self.launched(2)
        self.assertIn("## Owner's note on resuming (verbatim)\n\nmemory cache; record it as a decision", b)
        self.assertIn("which cache: redis or memory?", b)
        self.assertEqual(chainlib.load(self.root)["state"], "running")
        cli(self.root, "stop")
        w = cli(self.root, "watch", "--interval", "0.1")
        lines = w.stdout.splitlines()
        self.assertTrue(lines[0].startswith("#1 ") and "chain started:" in lines[0], lines[:2])
        self.assertIn("chain resumed:", w.stdout)
        self.assertTrue(lines[-1].endswith("watch ends"))
        w = cli(self.root, "watch", "--from", "3", "--interval", "0.1")
        self.assertTrue(w.stdout.startswith("#3 "))


class ChildEnv(unittest.TestCase):
    def test_a_launched_session_drops_this_sessions_markers_and_keeps_auth_and_config(self):
        keep = {"CLAUDE_CONFIG_DIR": "/c", "CLAUDE_CODE_OAUTH_TOKEN": "t", "CLAUDE_CODE_USE_BEDROCK": "1", "PATH": "/bin"}
        drop = {"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "s", "CLAUDE_CODE_ENTRYPOINT": "cli", "CHARTER_OWNER": "1", "CHARTER_UNIT": "u1"}
        old = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(keep, **drop)
            self.assertEqual(chainlib.child_env(), keep)
        finally:
            os.environ.clear()
            os.environ.update(old)


class Installed(unittest.TestCase):
    def test_install_brings_the_chain_and_wires_its_hook_on_every_tool(self):
        root = make_project(track="prototype")
        try:
            for rel in (".charter/chain.py", ".charter/chain-rules.md", "charter/templates/handoff.md", ".claude/skills/charter-chain/SKILL.md"):
                self.assertEqual((root / rel).read_bytes(), (PKG / rel).read_bytes(), rel)
            self.assertTrue(os.access(root / ".charter" / "hooks" / "chain_gate.py", os.X_OK))
            s = json.loads((root / ".claude" / "settings.json").read_text())
            for ev in ("UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"):
                groups = [g for g in s["hooks"][ev] if any("chain_gate.py" in " ".join(h.get("args", [])) for h in g["hooks"])]
                self.assertEqual(len(groups), 1, ev)
                self.assertNotIn("matcher", groups[0], ev)
            r = pkg("upgrade", str(root))
            self.assertIn("nothing to do", r.stdout)
        finally:
            cleanup(root)


if __name__ == "__main__":
    unittest.main()
