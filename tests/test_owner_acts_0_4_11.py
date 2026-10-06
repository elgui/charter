"""Charter 0.4.11: the owner's side of a wait.

In chain 20261005-183724 of hermes-custom (2026-10-05), two waits listed 16 acts in prose. Ten were commands under sudo
or Touch ID that the owner pasted one at a time while an agent read each output; three pastes broke; the resume named
7 lines by hand, because `ok` would also have closed one that failed and two not done; the owner typed `/resume-chain`
in the chain's tab twice and was refused. The owner chose (decision page, 2026-10-05): one owner script per wait, run as
the owner; Codex triage and risk notes, never closing or running anything; `ok` closes what passed; the resume allowed
in a closed chain tab; a session keeps going before it waits.

Now the session writes owner.md next to its handoff; `chain next` has it reviewed (a fake reviewer here) and sends an
act an agent could do back; `charter owner run` runs the acts in the owner's shell and records what passed; and
`/resume-chain ok` closes exactly those lines."""
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import PKG, git, run_hook
from test_chain_0_4_7 import ChainCase, cli, env_for, resume
from test_chain_wait import WaitCase, charter
from test_review_regressions import commit_all

sys.path.insert(0, str(PKG / ".charter"))
import chain as chainlib  # noqa: E402
import owner_acts  # noqa: E402

FAKE_REVIEWER = r'''
import json, sys, pathlib
prompt, out, verdicts, calls = sys.argv[1:5]
pathlib.Path(calls).open("a").write(open(prompt).read().split("owner.md, verbatim:")[1][:40].replace("\n", " ") + "\n")
pathlib.Path(out).write_text(pathlib.Path(verdicts).read_text())
'''


def verdict(n, cls="owner_credential", risk="medium", **kw):
    return dict({"n": n, "class": cls, "why": f"act {n} needs sudo", "risk": risk, "reversible": True,
                 "touches": "a file in /tmp", "read": "", "beyond_title": False}, **kw)


class OwnerActsCase(WaitCase):
    """A chain whose unit u1 has three owner lines (AC-2 do, AC-3 check, AC-4 do), and a fake reviewer at hand."""

    def setUp(self):
        super().setUp()
        self.u1 = self.root / ".taskets" / "u1.md"
        self.u1.write_text(self.u1.read_text().replace(
            "- [ ] AC-2: FileVault is on — owner: do\n",
            "- [ ] AC-2: FileVault is on — owner: do\n- [ ] AC-3: the drop box takes a file in — owner: check\n"
            "- [ ] AC-4: an R2 bucket exists — owner: do\n"))
        commit_all(self.root, "u1: three owner lines")
        tmp = self.root.parent / (self.root.name + "-review")
        tmp.mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        self.script, self.verdicts, self.calls = tmp / "reviewer.py", tmp / "verdicts.json", tmp / "calls.txt"
        self.script.write_text(FAKE_REVIEWER)
        self.reviewer = f"{sys.executable} {self.script} {{prompt}} {{out}} {self.verdicts} {self.calls}"
        self.join(1, "s1")

    def owner_md(self, text):
        p = chainlib.link_dir(self.root, self.cid, 1) / "owner.md"
        p.write_text(text)
        return p

    def hand_over(self, owner, verdicts=None, expect=0):
        self.wait_handoff(1, owner=owner)
        env = {"CHARTER_NOTIFY": ""}
        if verdicts is not None:
            self.verdicts.write_text(json.dumps({"steps": verdicts}))
            env["CHARTER_OWNER_REVIEW"] = self.reviewer
        r = charter(self.root, "chain", "next", sid="s1", env=env)
        self.assertEqual(r.returncode, expect, r.stdout + r.stderr)
        return r

    def run_acts(self, *args, inp=None):
        """`charter owner run` as the owner types it: in-process when a terminal is faked, else the CLI with no terminal."""
        if inp is not None:
            out = io.StringIO()
            code = owner_acts.run(self.root, chainlib.load(self.root), inp=inp, out=out, **dict(args))
            return code, out.getvalue()
        # a new session has no controlling terminal, so /dev/tty cannot be opened: the owner's run without one
        r = subprocess.run([sys.executable, "-B", str(self.root / ".charter" / "bin" / "charter"), "--root", str(self.root), "owner", "run", *args],
                           capture_output=True, text=True, cwd=str(self.root), env=env_for(None), start_new_session=True)
        return r.returncode, r.stdout + r.stderr

    def ticked(self):
        text = git(self.root, "show", "HEAD:.taskets/u1.md").stdout
        return {k for k in ("AC-2", "AC-3", "AC-4") if f"- [x] {k}" in text}


class TTY(io.StringIO):
    def isatty(self):
        return True


THREE = """# Owner's acts

## 1. Turn on FileVault (u1)
closes: u1 AC-2
do: System Settings > Privacy & Security > FileVault
check: true

## 2. The drop box takes a file in
closes: u1 AC-3
expect-output: inbox: add

```sh
echo "inbox: add inbox/conf-fixture.ab12"
```

## 3. An R2 bucket and a token
later: yes
closes: u1 AC-4
do: an EU bucket, a token scoped to it
"""


class Parse(unittest.TestCase):
    def test_a_quoted_line_text_may_hold_a_comma(self):
        self.assertEqual(owner_acts.refs('u1 "Approve scope, budget", AC-3'), ([("u1", "approve scope, budget"), ("u1", "AC-3")], []))
        self.assertIn("step 1: `timeout:` is a number of seconds", owner_acts.parse("## 1. a\ncloses: -\ndo: u1\ntimeout: ²\n")[1])

    def test_a_heredoc_body_is_not_a_placeholder(self):
        # a launchd plist written with `tee <<'EOF'` was refused for its `<dict>` (cross-review of 2026-10-05)
        plist = "## 1. Install the plist (u1)\ncloses: -\n\n```sh\nsudo tee /tmp/x.plist <<'EOF'\n<dict><key>a</key></dict>\nEOF\n```\n"
        self.assertEqual(owner_acts.parse(plist)[1], [])
        self.assertIn("holds `<bucket>`", " ".join(owner_acts.parse(plist.replace("sudo tee", "echo <bucket> | sudo tee"))[1]))

    def test_fields_kinds_and_refs(self):
        steps, problems = owner_acts.parse(THREE)
        self.assertEqual(problems, [])
        self.assertEqual([(s["n"], s["kind"], s["closes"]) for s in steps],
                         [(1, "manual", [("u1", "AC-2")]), (2, "command", [("u1", "AC-3")]), (3, "later", [("u1", "AC-4")])])
        self.assertEqual(steps[1]["command"], 'echo "inbox: add inbox/conf-fixture.ab12"')
        self.assertEqual(owner_acts.refs('w1 AC-2, AC-3, w2:ac-1, w3 "FileVault is on — owner: do"')[0],
                         [("w1", "AC-2"), ("w1", "AC-3"), ("w2", "AC-1"), ("w3", "filevault is on")])

    def test_each_defect_is_named(self):
        bad = ("## 1. a\ncloses: u1\nexpect-exit: maybe\nexpect_output: x\n\n```sh\ntrue\n```\n```sh\nfalse\n```\n"
               "## 3. b\ncheck: true\nexpect-output: (\n\n```\ntrue\n```\n## 4. c\ncloses: -\n")
        problems = " | ".join(owner_acts.parse(bad)[1])
        for want in ("step 1: more than one fenced block", "step 1: unknown field `expect_output:`", "step 1: `closes:` 'u1' is not",
                     "step 1: `expect-exit:` is `0`, `nonzero`", "step 3: `check:` belongs to an act that is not a command",
                     "step 3: `expect-output:` is not a regular expression", "step 4: an act that is not a command says how it is done under `do:`",
                     "acts are numbered 1, 3, 4; number them 1 to 3"):
            self.assertIn(want, problems)

    def test_the_template_has_no_act_and_its_example_parses(self):
        text = (PKG / "charter" / "templates" / "owner.md").read_text()
        self.assertEqual(owner_acts.parse(text)[1], ["no act: one `## 1. <title>` per act (template: charter/templates/owner.md)"])
        example = text.split("Example, from a real wait:\n", 1)[1].rsplit("-->", 1)[0]
        steps, problems = owner_acts.parse(example)
        self.assertEqual((problems, [s["kind"] for s in steps]), ([], ["command", "command", "manual", "later"]))


class Review(OwnerActsCase):
    def test_an_act_an_agent_could_do_goes_back_until_done_or_kept_with_a_reason(self):
        two = THREE.replace("## 3. An R2", "## 4. An R2").replace("## 2. The drop", "## 3. The drop").replace(
            "## 1. Turn on FileVault (u1)\n", "## 1. Install restic for u1\ncloses: -\n\n```sh\ntrue\n```\n\n## 2. Turn on FileVault (u1)\n")
        r = self.hand_over(two, [verdict(1, "agent_can_do", "low", why="brew needs no sudo"), verdict(2), verdict(3), verdict(4, "owner_outward")],
                           expect=1)
        self.assertIn("the review of owner.md (Codex, read-only) says you can do these acts yourself: step 1 (Install restic for u1): "
                      "brew needs no sudo", r.stdout)
        self.assertEqual(chainlib.load(self.root)["state"], "running")
        # kept, with the session's reason: the review runs again on the new owner.md, and the wait goes through
        kept = two.replace("closes: -\n", "closes: -\nowner-because: the owner keeps Homebrew by hand\n", 1)
        r = self.hand_over(kept, [verdict(1, "agent_can_do", "low"), verdict(2), verdict(3), verdict(4, "owner_outward")])
        self.assertEqual(len(self.calls.read_text().splitlines()), 2)
        self.assertEqual(chainlib.load(self.root)["state"], "waiting")
        self.assertIn("Codex: medium risk, can be undone; touches a file in /tmp. act 2 needs sudo", r.stdout)
        rec = json.loads((chainlib.link_dir(self.root, self.cid, 1) / "owner-review.json").read_text())
        self.assertEqual((rec["reviewed"], rec["sha"]), (True, owner_acts.sha(kept)))
        self.assertEqual(chainlib.link(self.root, self.cid, 1)["owner_sha"], owner_acts.sha(kept))

    def test_a_review_is_reused_for_the_same_owner_md_and_a_failed_one_lets_the_wait_go_on(self):
        self.wait_handoff(1, owner=THREE)
        self.verdicts.write_text(json.dumps({"steps": [verdict(1)]}))   # judges one act of three
        env = {"CHARTER_OWNER_REVIEW": self.reviewer}
        r = charter(self.root, "chain", "next", "--check", sid="s1", env=env)
        self.assertEqual((r.returncode, self.calls.exists()), (0, False), r.stdout)   # --check reviews nothing
        r = charter(self.root, "chain", "next", sid="s1", env=env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("(not reviewed by a second model: the reviewer judged acts [1], and owner.md has [1, 2, 3])", r.stdout)
        p = chainlib.link_dir(self.root, self.cid, 1)
        self.assertEqual(owner_acts.review(self.root, chainlib.load(self.root), 1, {})["why"],
                         "the reviewer judged acts [1], and owner.md has [1, 2, 3]")
        self.assertEqual(len(self.calls.read_text().splitlines()), 1)   # reused: same owner.md
        self.assertIn("A rule that lets a command run as root without a password (sudoers NOPASSWD) is high risk",
                      (p / "owner-review.prompt.md").read_text())
        self.assertIn("- u1 AC-3: - [ ] AC-3: the drop box takes a file in — owner: check", (p / "owner-review.prompt.md").read_text())

    def test_a_reviewer_that_fails_or_is_absent_never_holds_the_wait(self):
        r = self.hand_over(THREE, verdicts=[])
        self.verdicts.unlink()
        self.assertIn("(not reviewed by a second model:", r.stdout)
        self.assertEqual(chainlib.load(self.root)["state"], "waiting")
        mode = owner_acts.review_mode({"owner_review": "nonsense"}, {})
        self.assertEqual(mode[0], "off")


class Run(OwnerActsCase):
    def test_the_owner_runs_every_act_with_one_command_and_ok_closes_what_passed(self):
        self.hand_over(THREE)
        code, out = self.run_acts()
        self.assertEqual(code, 0, out)
        for want in ("── 1/3 Turn on FileVault (u1)  (closes u1 AC-2)", "check: true", "✓ passed: exit 0",
                     "$ echo \"inbox: add inbox/conf-fixture.ab12\"", "inbox: add inbox/conf-fixture.ab12",
                     "✓ passed: exit 0, output matches `inbox: add`", "later: not run now; its lines stay open",
                     "`/resume-chain ok` closes: u1 AC-2, u1 AC-3", "and leaves open: u1 AC-4 (act 3 later)"):
            self.assertIn(want, out)
        run = json.loads((chainlib.link_dir(self.root, self.cid, 1) / "owner-run.json").read_text())
        self.assertEqual({k: v["status"] for k, v in run["steps"].items()}, {"1": "passed", "2": "passed", "3": "later"})
        self.assertIn("inbox: add inbox/conf-fixture.ab12", (chainlib.link_dir(self.root, self.cid, 1) / "owner-run.log").read_text())
        r = resume(self.root, "ok")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.ticked(), {"AC-2", "AC-3"})
        self.assertIn("still open, and no chain session may close them: u1 AC-4 (act 3 later)", r.stdout)
        b = self.launched(2)
        self.assertIn("## The owner's run of owner.md", b)
        self.assertIn("- act 3 (An R2 bucket and a token): later, for later: not run, stays open", b)
        self.assertIn("## Owner's lines the resume left open\n\nThese lines stay open, and why: u1 AC-4 (act 3 later)", b)

    def test_a_failed_act_keeps_its_line_open_and_its_output_reaches_the_next_session(self):
        failing = THREE.replace('echo "inbox: add inbox/conf-fixture.ab12"', "echo 'cat: conf-fixture.n6pj: Permission denied'; exit 1")
        self.hand_over(failing)
        code, out = self.run_acts()
        self.assertEqual(code, 1, out)
        self.assertIn("✗ failed: exit 1, expected 0", out)
        self.assertIn("and leaves open: u1 AC-3 (act 2 failed); u1 AC-4 (act 3 later)", out)
        r = resume(self.root, "ok")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.ticked(), {"AC-2"})
        b = self.launched(2)
        self.assertIn("- act 2 (The drop box takes a file in): failed, exit 1, expected 0", b)
        self.assertIn("  cat: conf-fixture.n6pj: Permission denied", b)

    def test_ok_before_any_run_is_refused_with_the_command_and_names_still_work(self):
        at = self.hand_over(THREE) and git(self.root, "rev-parse", "HEAD").stdout.strip()
        r = resume(self.root, "ok")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not resumed, and no line closed: you have not run the acts yet: `python3 .charter/bin/charter owner run`", r.stdout)
        self.assertEqual(git(self.root, "rev-parse", "HEAD").stdout.strip(), at)
        r = resume(self.root, "u1:AC-2 did it by hand")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.ticked(), {"AC-2"})

    def test_a_line_two_acts_close_needs_both_and_stop_on_fail_skips_the_rest(self):
        acts = ("## 1. Reinstall for u1\ncloses: u1 AC-3\nstop-on-fail: yes\n\n```sh\nexit 3\n```\n\n"
                "## 2. The drop box takes a file in\ncloses: u1 AC-3, AC-2\n\n```sh\ntrue\n```\n")
        self.hand_over(acts)
        code, out = self.run_acts()
        self.assertEqual(code, 1)
        self.assertIn("✗ skipped: act 1 failed and says stop-on-fail", out)
        self.assertIn("`/resume-chain ok` closes: nothing", out)
        self.assertIn("u1 AC-3 (act 1 failed; act 2 skipped); u1 AC-2 (act 2 skipped)", out)
        # the owner fixes it and runs act 1 and 2 again: the run merges
        p = chainlib.link_dir(self.root, self.cid, 1) / "owner.md"
        code, out = self.run_acts("--only", "2")
        self.assertIn("`/resume-chain ok` closes: u1 AC-2", out)
        self.assertIn("u1 AC-3 (act 1 failed)", out)
        self.assertTrue(p.exists())

    def test_a_changed_owner_md_is_not_run_and_ok_refuses_it(self):
        self.hand_over(THREE)
        self.owner_md(THREE.replace("echo", "rm -rf /tmp/nothing; echo"))
        code, out = self.run_acts()
        self.assertEqual(code, 1)
        self.assertIn("changed after session 1 handed it over and Codex reviewed it. Nothing ran", out)
        r = resume(self.root, "ok")
        self.assertIn("changed after session 1 handed it over; `ok` cannot say which acts passed", r.stdout)

    def test_at_a_terminal_a_high_risk_act_and_a_manual_act_are_asked(self):
        acts = ("## 1. Write the sudoers rule for u1\ncloses: u1 AC-3\n\n```sh\ntrue\n```\n\n"
                "## 2. Turn on FileVault\ncloses: u1 AC-2\ndo: System Settings\n")
        self.hand_over(acts, [verdict(1, risk="high", reversible=False, touches="/etc/sudoers.d"), verdict(2)])
        code, out = self.run_acts(inp=TTY("n\ny\n"))
        self.assertIn("Codex: high risk, cannot be undone; touches /etc/sudoers.d", out)
        self.assertIn("Codex rates this high risk. Run it? [y/N]", out)
        self.assertIn("✗ declined: the owner declined it at the prompt", out)
        self.assertIn("Done? [y/N]", out)
        self.assertIn("`/resume-chain ok` closes: u1 AC-2", out)
        # without a terminal nothing is asked: the manual act is the owner's `ok`, the command runs
        code, out = self.run_acts()
        self.assertIn("(no terminal: nothing is asked)", out)
        self.assertIn("`/resume-chain ok` closes: u1 AC-3, u1 AC-2", out)

    def test_a_timeout_kills_the_whole_act_and_never_passes(self):
        # cross-review of 2026-10-05: the timer killed only /bin/sh, and a killed act passed `expect-exit: nonzero`
        acts = ("## 1. The gateway refuses outside calls (u1)\ncloses: u1 AC-3\nexpect-exit: nonzero\ntimeout: 1\n\n```sh\nsleep 30 && false\n```\n")
        self.hand_over(acts)
        t0 = __import__("time").monotonic()
        code, out = self.run_acts()
        self.assertLess(__import__("time").monotonic() - t0, 15)
        self.assertIn("✗ failed: killed by signal 9 (its timeout)", out)
        self.assertIn("`/resume-chain ok` closes: nothing", out)

    def test_ctrl_c_at_a_prompt_keeps_what_ran(self):
        class Interrupt(TTY):
            def readline(self, *a):
                raise KeyboardInterrupt
        acts = ("## 1. The drop box takes a file in (u1)\ncloses: u1 AC-3\n\n```sh\ntrue\n```\n\n"
                "## 2. Turn on FileVault\ncloses: u1 AC-2\ndo: System Settings\n")
        self.hand_over(acts)
        code, out = self.run_acts(inp=Interrupt())
        self.assertEqual(code, 130)
        run = json.loads((chainlib.link_dir(self.root, self.cid, 1) / "owner-run.json").read_text())["steps"]
        self.assertEqual({k: v["status"] for k, v in run.items()}, {"1": "passed", "2": "failed"})
        r = resume(self.root, "ok")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.ticked(), {"AC-3"})

    def test_an_empty_only_runs_nothing_and_a_bare_note_does_not_skip_unrun_acts(self):
        acts = "## 1. Install restic for u1\ncloses: -\n\n```sh\ntrue\n```\n"
        self.hand_over(acts)
        code, out = self.run_acts("--only", ",")
        self.assertEqual(code, 2)
        self.assertIn("--only names no act", out)
        r = resume(self.root, "carry on")
        self.assertEqual(r.returncode, 1)
        self.assertIn("you have not run the acts yet", r.stdout)
        self.assertIn("Going on without them: `/resume-chain skip <note>`", r.stdout)
        self.assertEqual(resume(self.root, "skip later").returncode, 0)

    def test_every_act_is_listed_and_a_command_act_shows_its_answers(self):
        acts = "".join(f"## {k}. Act {k} for u1\ncloses: -\ndo: step {k}\n\n" for k in range(1, 15))
        acts = acts.replace("## 14. Act 14 for u1\ncloses: -\ndo: step 14\n", "## 14. Configure the remote, interactive (u1)\ncloses: -\ndo: answer n, r2, s3\n\n```sh\ntrue\n```\n")
        self.hand_over(acts)
        out = charter(self.root, "owner").stdout
        self.assertIn("- 13. [you] Act 13 for u1", out)
        self.assertIn("- 14. [run] Configure the remote, interactive (u1)", out)
        self.assertIn("do: answer n, r2, s3", out)
        code, run = self.run_acts("--only", "14")
        self.assertIn("   do: answer n, r2, s3\n   $ true", run)

    def test_a_declined_stop_on_fail_act_stops_the_rest(self):
        acts = ("## 1. Reinstall for u1\ncloses: u1 AC-3\nstop-on-fail: yes\n\n```sh\ntrue\n```\n\n"
                "## 2. The drop box (u1)\ncloses: u1 AC-2\n\n```sh\ntrue\n```\n")
        self.hand_over(acts, [verdict(1, risk="high"), verdict(2)])
        code, out = self.run_acts(inp=TTY("n\n"))
        self.assertIn("✗ skipped: act 1 declined and says stop-on-fail", out)

    def test_an_owner_md_that_was_never_handed_over_is_not_run(self):
        self.hand_over(THREE)
        with chainlib.editing_link(self.root, self.cid, 1) as rec:
            rec.pop("owner_sha")
        code, out = self.run_acts()
        self.assertEqual(code, 1)
        self.assertIn("Nothing ran", out)
        self.assertIn("`ok` cannot say which acts passed", resume(self.root, "ok").stdout)

    def test_past_the_cap_owner_md_can_still_be_written(self):
        d = chainlib.link_dir(self.root, self.cid, 1)
        self.assertTrue(chainlib.allowed_at_cap(self.root, self.chain, 1, "Write", {"file_path": str(d / "owner.md")}))
        self.assertFalse(chainlib.allowed_at_cap(self.root, self.chain, 1, "Write", {"file_path": str(self.root / "app" / "x.py")}))

    def test_the_acts_run_in_zsh(self):
        self.hand_over("## 1. A zsh expansion (u1)\ncloses: u1 AC-3\nexpect-output: OK\n\n```sh\necho ${(U):-ok}\n```\n")
        code, out = self.run_acts()
        self.assertIn("✓ passed", out)

    def test_nothing_runs_unless_the_chain_waits(self):
        code, out = self.run_acts()
        self.assertEqual(code, 1)
        self.assertIn("is running, not waiting on you; nothing to run", out)


class Gates(OwnerActsCase):
    def test_an_agent_never_runs_the_owners_acts(self):
        self.hand_over(THREE)
        # the cross-review of 2026-10-05 found `owner --yes run`, `owner --only 2 run` and a run from .charter/bin got past
        for cmd in ("python3 .charter/bin/charter owner run", "python3 -B .charter/bin/charter --root . owner run --only 2",
                    "cd /x && charter owner run", "python3 .charter/bin/charter owner --yes run", "python3 .charter/bin/charter owner --only 2 run",
                    "cd .charter/bin && python3 charter owner run", "./charter owner --id x run", 'echo hi\npython3 ".charter/bin/charter" owner run'):
            code, out, raw, err = run_hook(self.root, "chain_gate", {"hook_event_name": "PreToolUse", "session_id": "any-agent",
                                                                    "tool_name": "Bash", "tool_input": {"command": cmd}})
            self.assertIn("`charter owner run` is the owner's command", out["hookSpecificOutput"]["permissionDecisionReason"], cmd)
        for cmd in ("python3 .charter/bin/charter owner", "python3 .charter/bin/charter owner --json", "grep -rn owner docs/"):
            code, out, raw, err = run_hook(self.root, "chain_gate", {"hook_event_name": "PreToolUse", "session_id": "any-agent",
                                                                    "tool_name": "Bash", "tool_input": {"command": cmd}})
            self.assertEqual(raw, "", cmd)

    def test_where_sudo_asks(self):
        # the cross-review of 2026-10-05 ran 30 shapes past the first pattern; these are they
        asks = ("sudo ops/install.sh", "cd x && sudo -u _c true", "FOO=1 sudo ls", "echo hi\nsudo ls", "if sudo true; then :; fi",
                "while sudo true; do :; done", "! sudo true", "{ sudo ls; }", "bash -c 'sudo ls'", 'sh -c "sudo ls"', "/usr/bin/sudo ls",
                "env sudo ls", "command sudo ls", "xargs sudo rm", "nohup sudo x", "timeout 5 sudo ls", "x=$(sudo whoami)", "sudo -v",
                "case x in x) sudo true;; esac")
        never = ("sudo -n /opt/x/t", "sudo -nu _c true", "sudo -E -n true", "sudo -u root -n true", "sudo -H -n ls", "sudo --non-interactive true",
                 "sudo -k", "sudo -V", "grep -rn sudo ops/", "echo pseudo", "visudo -c", "man sudo", "git log --grep=sudo")
        self.assertEqual([c for c in asks if not chainlib.sudo_asks(c)], [])
        self.assertEqual([c for c in never if chainlib.sudo_asks(c)], [])

    def test_a_working_chain_session_never_makes_sudo_ask(self):
        tp = self.root.parent / f"{self.root.name}-s1.jsonl"
        for cmd, deny in (("sudo ops/confidential/install.sh", True), ("cd ops && sudo -u _confidential true", True),
                          ("x=$(sudo whoami)", True), ("sudo -n /opt/confidential/bin/conf-restore-test", False),
                          ("grep -rn sudo ops/", False)):
            out = self.hook("PreToolUse", "s1", tp, tool_name="Bash", tool_input={"command": cmd})
            reason = (out.get("hookSpecificOutput") or {}).get("permissionDecisionReason", "")
            self.assertEqual("makes sudo ask the owner" in reason, deny, cmd)
        # the owner's own session is not a chain session: nothing is denied there
        out = self.hook("PreToolUse", "owner-tab", tp, tool_name="Bash", tool_input={"command": "sudo true"})
        self.assertNotIn("hookSpecificOutput", out)

    def test_a_working_chain_session_cannot_run_them_from_the_cli(self):
        r = charter(self.root, "owner", "run", sid="s1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("a chain session never performs the owner's acts", r.stderr)

    def test_a_working_chain_session_cannot_commit_a_handover(self):   # 0.4.12, with the owner switch even
        r = charter(self.root, "owner", "commit", sid="s1", env={"CHARTER_OWNER": "1"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("a chain session never commits the owner's change", r.stderr)



class Config(ChainCase):
    def test_the_start_says_how_the_acts_are_reviewed_and_the_config_knows_the_keys(self):
        cfg = json.loads((self.root / "charter" / "config.json").read_text())
        cfg["chain"] = {"owner_review": "codex", "owner_review_effort": "low", "owner_review_timeout_s": 60}
        (self.root / "charter" / "config.json").write_text(json.dumps(cfg))
        commit_all(self.root, "config: the owner review")
        self.assertNotIn("unknown key", charter(self.root, "config").stdout)
        r = cli(self.root, "start", "--unit", "u1", "--launcher", self.launcher, "--review", "off", "--dry-run")
        self.assertIn("owner's acts at a wait: review off", r.stdout)   # the tests' environment turns it off
        self.start()
        self.assertEqual(chainlib.load(self.root)["owner_review"], "codex")

if __name__ == "__main__":
    unittest.main()
