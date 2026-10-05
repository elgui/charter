"""Charter 0.4.9: the owner's acts at a chain's wait are the owner's.

In the wait trial (chain 20261004-204830 on the bed, 2026-10-04), session 1 waited on "approve the tone of
farewell('Ada'), then tick AC-2". An agent session that was not the owner then ran one Bash command: `sed -i` ticked
AC-2, `git commit -am "w1 AC-2: tone approved (owner stand-in, trial)"` (b06cd86), and `charter chain resume --note
"Tone approved ... I ticked AC-2."`. Session 2 closed the unit and the chain completed: nothing told the agent's act
from the owner's. Now an `— owner:` line is closed only by the owner (the Edit gate, the commit gate, CI), and a paused
chain resumes only when the owner types `/resume-chain` in an interactive Claude Code session: the prompt hook
performs it and blocks the prompt from the model, and `charter chain resume` refuses everyone
(docs/trials/2026-10-04-owner-gate.md). Every test here fails on 243d84b."""
import json
import shlex
import sys
import unittest
from pathlib import Path

from helpers import PKG, clean_env, git, run_hook
from test_chain_0_4_7 import cli, resume
from test_chain_wait import WaitCase, charter, charter_pkg
from test_review_regressions import commit_all

sys.path.insert(0, str(PKG / ".charter"))
import chain as chainlib  # noqa: E402
import checks  # noqa: E402

NOTE = "Tone approved: 'Goodbye, Ada. Take care!' is fine. I ticked AC-2."


def denied(out: dict) -> str:
    """The reason a PreToolUse hook denied the call, '' when it did not."""
    h = out.get("hookSpecificOutput") or {}
    return h.get("permissionDecisionReason", "") if h.get("permissionDecision") == "deny" else ""


class OwnerGate(WaitCase):
    def setUp(self):
        super().setUp()
        self.u1 = self.root / ".taskets" / "u1.md"

    def waiting(self):
        self.join(1, "s1")
        self.wait_handoff(1)
        self.assertEqual(self.next("s1").returncode, 0)
        self.assertEqual(chainlib.load(self.root)["state"], "waiting")
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def head(self):
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def assert_still_waiting(self, at: str):
        self.assertEqual(chainlib.load(self.root)["state"], "waiting")
        self.assertEqual(self.head(), at)
        self.assertIn("- [ ] AC-2", git(self.root, "show", "HEAD:.taskets/u1.md").stdout)
        self.assertFalse(chainlib.link_dir(self.root, self.cid, 2).exists())

    def test_the_stand_in_of_the_wait_trial_is_refused_at_each_step(self):
        at = self.waiting()
        # the Edit tool of any agent session in the project
        code, out, so, se = run_hook(self.root, "pre_tool_gate", {"tool_name": "Edit", "session_id": "agent-tab", "tool_input": {
            "file_path": str(self.u1), "old_string": "- [ ] AC-2", "new_string": "- [x] AC-2"}}, env={"CLAUDECODE": "1"})
        self.assertIn("only the owner closes such a line", denied(out), so + se)
        # the trial's `sed -i` and commit, from the Bash tool of a Claude Code session
        self.u1.write_text(self.u1.read_text().replace("- [ ] AC-2", "- [x] AC-2"))
        git(self.root, "add", ".taskets/u1.md")
        r = git(self.root, "commit", "-m", "w1 AC-2: tone approved (owner stand-in, trial)", check=False, env=clean_env(CLAUDECODE="1"))
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("it closes AC-2, marked `— owner:`", r.stdout + r.stderr)
        git(self.root, "reset", "-q", "--hard")
        # the resume with a note in the owner's name, from a Claude Code session or a plain shell
        for sid in ("agent-tab", None):
            r = cli(self.root, "resume", "--note", NOTE, sid=sid)
            self.assertEqual(r.returncode, 1)
            self.assertIn("charter chain resume: refused", r.stdout)
            self.assertIn("/resume-chain", r.stdout)
        # the owner switch, which would let the commit through
        code, out, so, se = run_hook(self.root, "chain_gate", {"hook_event_name": "PreToolUse", "session_id": "agent-tab", "tool_name": "Bash",
                                                              "tool_input": {"command": "CHARTER_OWNER=1 git commit -qam 'tone approved'"}})
        self.assertIn("an agent never sets CHARTER_OWNER", denied(out), so + se)
        self.assert_still_waiting(at)
        self.assertNotIn("resumed", self.events())

    def test_the_owner_closes_the_line_and_resumes_by_typing_the_command(self):
        at = self.waiting()
        r = resume(self.root, "AC-2 " + NOTE)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("closed u1 AC-2 as the owner", r.stdout)
        self.assertIn(f"chain {self.cid} resumed: session 2 launched", r.stdout)
        # one commit, made as the owner, of the unit file alone, on top of the wait
        self.assertEqual(git(self.root, "log", "-1", "--format=%P%n%s").stdout.split("\n")[:2],
                         [at, f"owner: closes u1 AC-2 (/resume-chain, chain {self.cid})"])
        self.assertEqual(git(self.root, "show", "--name-only", "--format=", "HEAD").stdout.split(), [".taskets/u1.md"])
        self.assertIn("- [x] AC-2: FileVault is on — owner: do", self.u1.read_text())
        self.assertEqual(git(self.root, "status", "--porcelain", "--untracked-files=no").stdout, "")
        c = chainlib.load(self.root)
        self.assertEqual(c["state"], "running")
        self.assertEqual({k: c["last_resume"][k] for k in ("via", "session", "closed", "next")},
                         {"via": "/resume-chain", "session": "owner-tab", "closed": ["u1 AC-2"], "next": 2})
        b = self.launched(2)
        self.assertIn(f"## Owner's note on resuming (verbatim)\n\n{NOTE}\n", b)
        self.assertIn(f"which closed u1 AC-2 in commit {self.head()[:7]}, as the owner", b)
        self.assertIn(f"resumed: by the owner's /resume-chain in session owner-ta; closed u1 AC-2 in {self.head()[:7]}", self.events())

    def test_the_command_arrives_as_an_expansion_too(self):
        self.waiting()
        r = resume(self.root, "u1:AC-2 done", event="UserPromptExpansion")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("- [x] AC-2", git(self.root, "show", "HEAD:.taskets/u1.md").stdout)

    def test_the_prompt_never_reaches_the_model_even_when_refused(self):
        at = self.waiting()
        for env in ({"CLAUDE_CODE_ENTRYPOINT": "cli", "CLAUDE_CODE_SESSION_ATTENDED": "1"}, {"CLAUDE_CODE_ENTRYPOINT": "sdk-cli"}):
            code, out, raw, err = run_hook(self.root, "chain_gate", {"hook_event_name": "UserPromptSubmit", "session_id": "tab",
                                                                    "prompt": "/resume-chain AC-9 go"}, env=env)
            self.assertEqual(out.get("decision"), "block", raw + err)
            self.assertNotIn("additionalContext", raw)
            self.assertTrue(out["reason"].startswith("charter /resume-chain: refused"), out["reason"])
        self.assert_still_waiting(at)
        # any other prompt passes untouched
        code, out, raw, err = run_hook(self.root, "chain_gate", {"hook_event_name": "UserPromptSubmit", "session_id": "tab",
                                                                "prompt": "resume what you were doing"})
        self.assertEqual(raw, "")

    def test_a_headless_session_cannot_resume(self):
        at = self.waiting()
        for env in ({"CLAUDE_CODE_ENTRYPOINT": "sdk-cli", "CLAUDE_CODE_SESSION_ATTENDED": "0"},
                    {"CLAUDE_CODE_SESSION_ATTENDED": "0"}, {"CLAUDE_CODE_ENTRYPOINT": "sdk-py"}):
            r = resume(self.root, "AC-2 ok", env=env)
            self.assertEqual(r.returncode, 1, env)
            self.assertIn("headless", r.stdout)
        self.assert_still_waiting(at)

    def test_a_chain_session_cannot_resume(self):
        at = self.waiting()
        r = resume(self.root, "AC-2 ok", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"this is session 1 of chain {self.cid}", r.stdout)
        self.assert_still_waiting(at)

    def test_the_chain_tab_refusal_and_the_queue_say_how_to_open_your_own_session(self):
        # the owner typed the command in the chain's tab four times in two trials (docs/trials/2026-10-05-owner-gate-recheck.md)
        self.waiting()
        own = f"cd {shlex.quote(str(self.root.resolve()))} && claude"
        self.assertIn(own, resume(self.root, "ok fine", sid="s1").stdout)
        self.assertIn(f"not in the chain's tab; open your own with `{own}`", charter(self.root, "next").stdout)

    def test_a_closed_session_writes_and_commits_nothing_more(self):
        # session 1 of the re-check committed after `chain next` closed it, unseen (docs/trials/2026-10-05-owner-gate-recheck.md)
        self.waiting()
        for tool, ti, deny in (("Edit", {"file_path": str(self.u1), "old_string": "a", "new_string": "b"}, True),
                               ("Write", {"file_path": str(self.root / "x.txt"), "content": "x"}, True),
                               ("Bash", {"command": "sed -i '' 's/a/b/' .taskets/u1.md; git commit -qam 'tick AC-1'"}, True),
                               ("Bash", {"command": f"git -C {self.root} add -A && git push"}, True),
                               ("Bash", {"command": "git log --oneline -3; git status --short"}, False),
                               ("Bash", {"command": "python3 .charter/bin/charter chain next"}, False),
                               ("Read", {"file_path": str(self.u1)}, False)):
            code, out, so, se = run_hook(self.root, "chain_gate", {"hook_event_name": "PreToolUse", "session_id": "s1",
                                                                  "tool_name": tool, "tool_input": ti})
            self.assertEqual(bool(denied(out)), deny, f"{tool} {ti} {so} {se}")
            if deny:
                self.assertIn(f"session 1 of chain {self.cid} is closed (wait)", denied(out))

    def test_commits_since_the_wait_are_named_and_the_next_session_checks_them(self):
        at = self.waiting()
        (self.root / "notes.txt").write_text("the owner, during the wait\n")
        git(self.root, "add", "notes.txt")
        git(self.root, "commit", "-qm", "owner: a note during the wait")
        extra = self.head()
        r = resume(self.root, "ok all done")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(f"committed since session 1 handed over, and not by your /resume-chain: {extra[:7]} owner: a note during the wait", r.stdout)
        after = chainlib.load(self.root)["last_resume"]["after"]
        self.assertEqual(len(after), 1, after)   # the owner's resume commit is not one of them
        b = self.launched(2)
        self.assertIn("## Commits since session 1 handed over", b)
        self.assertIn(f"{extra[:7]} owner: a note during the wait", b)
        self.assertNotEqual(at, extra)

    def test_a_line_that_is_not_an_open_owner_line_changes_nothing(self):
        at = self.waiting()
        for args, why in (("AC-7 ok", "AC-7 is not an open `— owner:` line"), ("AC-1 ok", "AC-1 is not an open"),
                          ("u9:AC-2 ok", "u9:AC-2 is not an open"), ("--window x AC-2", "--window takes a whole number, not 'x'")):
            r = resume(self.root, args)
            self.assertEqual(r.returncode, 1, args)
            self.assertIn(why, r.stdout)
            if "AC-2 is" in why or "AC-7" in why:
                self.assertIn("open ones: u1:AC-2", r.stdout)
        self.assert_still_waiting(at)

    def test_two_units_with_the_line_need_the_unit_named(self):
        u2 = self.root / ".taskets" / "u2.md"
        u2.write_text(self.u1.read_text().replace("id: u1", "id: u2"))
        commit_all(self.root, "u2, with its own AC-2 for the owner")
        at = self.waiting()
        r = resume(self.root, "AC-2 ok")
        self.assertEqual(r.returncode, 1)
        self.assertIn("AC-2 is an owner line of 2 units; name one: u1:AC-2, u2:AC-2", r.stdout)
        self.assert_still_waiting(at)
        self.assertEqual(resume(self.root, "u2:AC-2 ok").returncode, 0)
        self.assertIn("- [x] AC-2", u2.read_text())
        self.assertIn("- [ ] AC-2", self.u1.read_text())

    def test_a_bare_note_while_lines_are_open_asks_done_or_not(self):
        # the owner should not have to know a line's id (the owner, 2026-10-04)
        at = self.waiting()
        r = resume(self.root, "all good, carry on")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not resumed: the chain waits on u1 AC-2\n  - turn on FileVault", r.stdout)
        self.assertIn("Done? `/resume-chain ok <note>` closes it as yours. Not done: `/resume-chain skip <note>`", r.stdout)
        self.assert_still_waiting(at)

    def test_ok_closes_every_waited_line_and_skip_none(self):
        self.waiting()
        r = resume(self.root, "skip not yet, do the rest")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("still open, and no chain session may close them: u1 AC-2", r.stdout)
        self.assertIn("- [ ] AC-2", self.u1.read_text())
        self.assertIn("not yet, do the rest", self.launched(2))

    def test_ok_closes_the_waited_line_without_its_id(self):
        self.waiting()
        r = resume(self.root, "OK FileVault is on")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("closed u1 AC-2 as the owner", r.stdout)
        self.assertIn("- [x] AC-2", git(self.root, "show", "HEAD:.taskets/u1.md").stdout)
        self.assertIn("FileVault is on", self.launched(2))

    def test_a_box_the_owner_ticked_by_hand_is_closed_by_naming_it(self):
        self.waiting()
        self.u1.write_text(self.u1.read_text().replace("- [ ] AC-2", "- [x] AC-2") + "stray\n")
        r = resume(self.root, "AC-2 done")
        self.assertEqual(r.returncode, 1)
        self.assertIn(".taskets/u1.md has uncommitted changes besides the owner's ticks", r.stdout)
        self.u1.write_text(self.u1.read_text().replace("stray\n", ""))
        r = resume(self.root, "AC-2 done")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("- [x] AC-2", git(self.root, "show", "HEAD:.taskets/u1.md").stdout)
        self.assertEqual(git(self.root, "status", "--porcelain", "--untracked-files=no").stdout, "")

    def test_a_line_closed_outside_the_resume_is_named_and_the_next_session_reopens_it(self):
        self.waiting()
        # a commit outside Claude Code only warns (the owner's own terminal, or an agent past the gates)
        self.u1.write_text(self.u1.read_text().replace("- [ ] AC-2", "- [x] AC-2"))
        git(self.root, "commit", "-qam", "tick by hand")
        sha = self.head()[:7]
        r = resume(self.root, "skip going on")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(f"closed since the wait by a commit that was not your /resume-chain: u1 AC-2 in {sha} ('tick by hand', Test Owner)", r.stdout)
        last = chainlib.load(self.root)["last_resume"]
        self.assertEqual((last["outside"], last["event"]), ([f"u1 AC-2 in {sha} ('tick by hand', Test Owner)"], "UserPromptSubmit"))
        b = self.launched(2)
        self.assertIn("## Owner's lines closed outside the owner's resume", b)
        self.assertIn("Reopen each line the owner's note above does not say is theirs", b)

    def test_a_line_without_an_id_is_closed_by_ok_and_a_same_named_box_elsewhere_is_left(self):
        # cross-review of d54a9dd: `ok` printed a ref the parser refused, and the tick went to the first `AC-2` box in the file
        self.u1.write_text(self.u1.read_text().replace("- [ ] AC-2: FileVault is on — owner: do", "- [ ] FileVault is on — owner: do")
                           .replace("## Context\n", "## Context\n\n- [ ] AC-2 scratch step\n"))
        commit_all(self.root, "u1: an owner line without an id, and a scratch box named AC-2")
        self.join(1, "s1")
        self.wait_handoff(1)
        self.assertEqual(self.next("s1").returncode, 0)
        r = resume(self.root, "ok done")
        self.assertEqual(r.returncode, 0, r.stdout)
        text = self.u1.read_text()
        self.assertIn("- [x] FileVault is on — owner: do", text)
        self.assertIn("- [ ] AC-2 scratch step", text)

    def test_a_prompt_without_a_session_is_refused(self):
        at = self.waiting()
        r = resume(self.root, "ok", sid="")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no Claude Code session named this prompt", r.stdout)
        self.assert_still_waiting(at)

    def test_a_launch_that_fails_after_the_owners_commit_says_so_and_a_retry_keeps_the_lines(self):
        self.waiting()
        c = chainlib.load(self.root)
        good = c["launcher"]
        c["launcher"] = "/nonexistent/launcher {briefing}"
        chainlib.save(self.root, c)
        r = resume(self.root, "ok FileVault is on")
        self.assertEqual(r.returncode, 1)
        self.assertTrue(r.stdout.startswith("charter /resume-chain: partly done"), r.stdout)
        self.assertIn("closed u1 AC-2 as the owner", r.stdout)
        c = chainlib.load(self.root)
        self.assertEqual(c["state"], "halted")
        c["launcher"] = good
        chainlib.save(self.root, c)
        r = resume(self.root, "launcher fixed")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(chainlib.load(self.root)["last_resume"]["closed"], ["u1 AC-2"])
        self.assertNotIn("not your /resume-chain", r.stdout)
        self.assertIn("which closed u1 AC-2 in commit", self.launched(3))

    def test_every_resume_is_the_owners_after_a_stop_too(self):
        self.waiting()
        self.assertEqual(cli(self.root, "stop").returncode, 0)
        self.assertEqual(chainlib.load(self.root)["state"], "stopped")
        self.assertEqual(cli(self.root, "resume").returncode, 1)
        self.assertEqual(resume(self.root, "go on").returncode, 0)
        self.launched(2)


class OwnerLines(unittest.TestCase):
    OLD = ("---\nid: u1\nstatus: now\n---\n\n## Acceptance\n\n- [x] AC-1: works — probe: `true`\n"
           "- [ ] AC-2: the owner approves the tone — owner: check\n- [ ] AC-3: docs\n\n## Log\n\n- 2026-10-04 created\n")

    def changed(self, old, new):
        return checks.owner_line_changes(old, new)

    def test_closing_an_owner_line_is_the_owners_change(self):
        o = self.OLD
        self.assertEqual(self.changed(o, o.replace("- [ ] AC-2", "- [x] AC-2")), ["AC-2"])
        self.assertEqual(self.changed(o, o.replace(" — owner: check", "")), ["AC-2"])                       # unmarked
        self.assertEqual(self.changed(o, o.replace("- [ ] AC-2: the owner approves the tone — owner: check\n", "")), ["AC-2"])   # removed
        self.assertEqual(self.changed(o, o.replace("- [ ] AC-2", "- [x] AC-9")), ["AC-2", "AC-9"])          # renamed and ticked
        self.assertEqual(self.changed(o, o.replace("- [ ] AC-3: docs", "- [x] AC-3: docs — owner: do")), ["AC-3"])   # arrives ticked
        self.assertEqual(self.changed("", o.replace("- [ ] AC-2", "- [x] AC-2")), ["AC-2"])                # a new unit
        dup = o.replace("- [ ] AC-2", "- [x] AC-2").replace("- [ ] AC-3", "- [ ] AC-2 copy — owner: check\n- [ ] AC-3")
        self.assertEqual(self.changed(o, dup), ["AC-2"])                                                    # a duplicate id hides nothing
        noid = o.replace("AC-2: the owner", "the owner")
        self.assertEqual(self.changed(noid, noid.replace("approves the tone", "approves the final tone")), ["the owner approves the tone"])
        self.assertIn("only the owner closes such a line",
                      "; ".join(checks.owner_only_changes(".taskets/u1.md", o, o.replace("- [ ] AC-2", "- [x] AC-2"), "commit")))

    def test_marking_reopening_and_other_lines_stay_free(self):
        o = self.OLD
        self.assertEqual(self.changed(o, o.replace("- [ ] AC-3: docs", "- [ ] AC-3: docs — owner: do")), [])   # a session marks
        self.assertEqual(self.changed(o, o.replace("- [ ] AC-3", "- [x] AC-3")), [])                        # not the owner's
        self.assertEqual(self.changed(o, o.replace("approves the tone", "approves the tone of farewell")), [])
        done = o.replace("- [ ] AC-2", "- [x] AC-2")
        self.assertEqual(self.changed(done, o), [])                                                         # reopened
        self.assertEqual(self.changed(done, done.replace("- [ ] AC-3", "- [x] AC-3")), [])
        self.assertEqual(checks.owner_only_changes(".taskets/u1.md", o, o.replace("- [ ] AC-3", "- [x] AC-3"), "edit"), [])

    def test_the_arguments_of_the_command(self):
        p = chainlib.parse_resume
        opts, refs, note, problem = p("20261004-204830 --window 400000 --more=2 AC-2 w1:ac-3, -- AC-4 is mine")
        self.assertEqual((opts["id"], opts["window"], opts["more"], refs, note, problem),
                         ("20261004-204830", 400000, 2, [(None, "AC-2"), ("w1", "AC-3")], "AC-4 is mine", ""))
        self.assertEqual(p(f"  {NOTE}  ")[1:], ([], NOTE, ""))
        self.assertEqual(p("--skip-review review it by hand later")[0]["skip_review"], True)
        self.assertEqual(p("--skip-review review it by hand later")[2], "review it by hand later")
        self.assertEqual((p("ok  it's fine")[0]["mode"], p("ok  it's fine")[2]), ("ok", "it's fine"))
        self.assertEqual((p("skip")[0]["mode"], p("okay then")[0]["mode"], p("okay then")[2]), ("skip", "", "okay then"))
        self.assertEqual(p("")[1:], ([], "", ""))
        self.assertEqual(p("--more=²")[3], "--more takes a whole number, not '²'")
        self.assertEqual(p("AC-2 --cap 50 is too high")[0]["cap"], None)
        self.assertEqual(p("AC-2 --cap 50 is too high")[1:3], ([(None, "AC-2")], "--cap 50 is too high"))
        self.assertEqual(p("AC-2: tone approved")[1:3], ([(None, "AC-2")], "tone approved"))
        self.assertEqual(p("AC-2,w1:AC-3 ok")[1:3], ([(None, "AC-2"), ("w1", "AC-3")], "ok"))
        self.assertEqual(p("--wrap")[3], "--wrap takes a whole number, not 'nothing'")
        self.assertIsNone(chainlib.RESUME_RE.match("/resume-chainx go"))
        self.assertEqual(chainlib.RESUME_RE.match("/resume-chain\nline two").group(1), "\nline two")


class Installed(unittest.TestCase):
    def test_the_command_is_the_owners_alone_and_the_hook_sees_it(self):
        text = (PKG / ".claude" / "commands" / "resume-chain.md").read_text()
        self.assertIn("\ndisable-model-invocation: true\n", text.split("\n---\n", 1)[0] + "\n")
        hooks = json.loads((PKG / ".claude" / "settings.json").read_text())["hooks"]
        for ev in ("UserPromptSubmit", "UserPromptExpansion"):
            h = hooks[ev][0]["hooks"][0]
            self.assertTrue(h["args"][-1].endswith("/.charter/hooks/chain_gate.py"), ev)
            self.assertGreaterEqual(h["timeout"], 900, ev)   # a resume after a stall re-runs the gates and launches a tab
        self.assertIn(".claude/commands/resume-chain.md", charter_pkg().OWNED)

    def test_any_session_is_denied_the_owner_switch_and_nothing_else(self):
        from helpers import cleanup, make_project
        root = make_project(track="prototype")
        self.addCleanup(lambda: cleanup(root))
        for cmd, deny in (("CHARTER_OWNER=1 git commit -qm x", True), ("export CHARTER_OWNER=1", True), ("git status", False),
                          ("env -u CLAUDECODE git commit -qm x", True), ("unset CLAUDECODE; git commit", True), ("CLAUDECODE= git commit", True),
                          ("echo $CLAUDECODE", False)):
            code, out, so, se = run_hook(root, "chain_gate", {"hook_event_name": "PreToolUse", "session_id": "any",
                                                             "tool_name": "Bash", "tool_input": {"command": cmd}})
            self.assertEqual(bool(denied(out)), deny, cmd + so + se)
        self.assertEqual(charter(root, "owner").returncode, 0)


if __name__ == "__main__":
    unittest.main()
