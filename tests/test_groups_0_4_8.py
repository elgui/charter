"""Charter 0.4.8: a chain's groups and their review. A chain works one group of units at a time (a rail item of
`charter/rails.md`, else a tasket `group:`) on one branch. When the road goes on to another group, or ends, the group's
commits are reviewed by another model family (`codex exec review --base <start>`) in a worktree of its own at the
group's last commit; the next session answers every finding under `## Review` before the next group starts, and the
group is cleared at its last commit: a point the owner can merge up to. Asked for on 2026-10-04: "each new group starts
with what has been done before (even if it later needs fixes)", no drift, no merge conflicts, and a Codex review at
each group boundary (docs/design/continuous-chain.md § Groups and their review). Every test here fails on 0.4.7,
which has no groups.

The reviewer is a fake command (the `{base}`/`{out}` template the setting accepts) that records where it ran and
answers with what the test wrote; the parser is checked against Codex's real output, measured on 2026-10-04."""
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

from helpers import PKG, cleanup, git, make_project
from test_chain_0_4_7 import VERIFIED, ChainCase, cli, env_for, handoff
from test_review_regressions import commit_all

sys.path.insert(0, str(PKG / ".charter"))
import chain as chainlib  # noqa: E402
import chain_groups as groups  # noqa: E402

RAILS = """# Rails

| id | title | status | order |
|---|---|---|---|
| r1 | Health reports retries | in-progress | 10 |
| r2 | Billing doubles | next | 20 |
"""


def unit(uid, rail, perimeter, extra=""):
    return (f"---\nid: {uid}\ntitle: {uid} work\nstatus: next\nscope: S1\nrail: {rail}\nperimeter: [{perimeter}, tests/**]\nkind: work\n{extra}---\n\n"
            f"## Acceptance\n\n- [ ] AC-1: {uid} — probe: `python3 -c \"pass\"`\n\n## Evidence\n\n## Log\n")


# what codex exec review wrote with -o on 2026-10-04 (codex-cli 0.147.0), its worktree path replaced by {cwd}
CODEX_SAMPLE = """The new median function produces incorrect results for all even-length sequences, a common and valid input category.

Review comment:

- [P1] Average the middle pair for even-length inputs — {cwd}/app/health.py:2-2
  For every even-length input, this returns the upper middle element rather than the median; for example, `median([1, 3])` returns `3` instead of `2`. Handle even lengths by averaging the two central sorted values."""

FAKE = r'''import json, os, subprocess, sys, time
base, out, ctl = sys.argv[1], sys.argv[2], sys.argv[3]
head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
with open(os.path.join(ctl, "calls.jsonl"), "a") as f:
    f.write(json.dumps({"base": base, "head": head, "cwd": os.getcwd(), "dirty": dirty}) + "\n")
sleep = os.path.join(ctl, "sleep")
if os.path.exists(sleep):
    time.sleep(float(open(sleep).read()))
code = int(open(os.path.join(ctl, "exit")).read()) if os.path.exists(os.path.join(ctl, "exit")) else 0
if code == 0:
    open(out, "w").write(open(os.path.join(ctl, "answer.txt")).read().replace("{cwd}", os.getcwd()))
else:
    print("fake reviewer: not logged in", file=sys.stderr)
sys.exit(code)
'''


class GroupCase(ChainCase):
    """The chain project of 0.4.7 with a road: u1 and u2 on rail r1, u3 on rail r2; the review is the fake."""

    def setUp(self):
        super().setUp()
        (self.root / "charter" / "rails.md").write_text(RAILS)
        u1 = self.root / ".taskets" / "u1.md"
        u1.write_text(u1.read_text().replace("kind: work\n", "kind: work\nrail: r1\n"))
        (self.root / ".taskets" / "u2.md").write_text(unit("u2", "r1", "app/health.py"))
        (self.root / ".taskets" / "u3.md").write_text(unit("u3", "r2", "app/billing.py"))
        commit_all(self.root, "the road: r1 then r2")
        self.ctl = Path(str(self.out) + "-review")
        self.ctl.mkdir()
        self.addCleanup(cleanup, self.ctl)
        (self.ctl / "fake.py").write_text(FAKE)
        self.answer("No issues found.")
        self.review = f"{sys.executable} {self.ctl / 'fake.py'} {{base}} {{out}} {self.ctl}"

    def start(self, *extra, **kw):
        r = super().start("--review", self.review, *extra, **kw)
        self.cid = self.chain["id"]
        return r

    def answer(self, text, code=0):
        (self.ctl / "answer.txt").write_text(text)
        (self.ctl / "exit").write_text(str(code))

    def calls(self):
        p = self.ctl / "calls.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def launched(self, n):
        """Session n's briefing: after a review, the runner launches it, so wait longer than 0.4.7's harness does."""
        p = self.out / f"chain {self.cid} s{n:02d}.md"
        self.wait(lambda: p.exists() and p.stat().st_size, f"session {n} launched")
        return p.read_text()

    def wait(self, cond, what, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            if cond():
                return
            time.sleep(0.1)
        self.fail(f"timed out waiting for: {what}\n{self.events()}")

    def state(self):
        return chainlib.load(self.root, self.cid)

    def group(self, k=-1):
        return self.state()["groups"][k]

    def unit_start(self, uid, sid):
        return subprocess.run([sys.executable, "-B", str(self.root / ".charter" / "bin" / "charter"), "--root", str(self.root), "unit", "start", uid],
                              capture_output=True, text=True, cwd=str(self.root), env=env_for(sid))

    def work(self, path="app/health.py", line="# retries checked"):
        p = self.root / path
        p.write_text(p.read_text() + f"\n{line}\n")
        commit_all(self.root, f"work on {path}")
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def hand_over(self, n, sid, **kw):
        kw.setdefault("verified", VERIFIED if n > 1 else "first session")
        self.write_handoff(n, **kw)
        return cli(self.root, "next", sid=sid)

    def end_group_one(self, findings=None):
        """Session 1 works r1 and hands over to u3, on r2: the review of r1 runs, and session 2 is launched."""
        if findings is not None:
            self.answer(findings)
        self.start()
        self.join(1, "s1")
        self.sha1 = self.work()
        r = self.hand_over(1, "s1", next_unit="u3", done=f"- u1: retries, {self.sha1[:7]}")
        self.assertEqual(r.returncode, 0, r.stdout)
        return r


class GroupOf(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")

    def tearDown(self):
        cleanup(self.root)

    def test_a_unit_is_in_the_group_of_its_first_open_rail_else_its_tasket_group(self):
        import lib
        cfg = lib.load_config(self.root)
        self.assertEqual(groups.group_of(self.root, cfg, {"group": "board-home"}), "board-home")
        self.assertEqual(groups.group_of(self.root, cfg, {}), "")
        (self.root / "charter" / "rails.md").write_text(RAILS.replace("| r1 | Health reports retries | in-progress | 10 |",
                                                                      "| r1 | Health reports retries | done | 10 |"))
        self.assertEqual(groups.group_of(self.root, cfg, {"rail": "r2", "group": "board-home"}), "r2")
        self.assertEqual(groups.group_of(self.root, cfg, {"rail": ["r1", "r2"]}), "r2")   # r1 is closed: the road's order skips it
        self.assertEqual(groups.group_of(self.root, cfg, {"rail": "r1"}), "r1")
        self.assertEqual(groups.group_of(self.root, cfg, {"group": "board-home"}), "")   # a road, and the unit is not on it


class Parse(unittest.TestCase):
    def test_codex_output_splits_into_numbered_findings_with_their_location(self):
        f = groups.parse(CODEX_SAMPLE.replace("{cwd}/", "") + "\n\n- [P2] Name the constant — app/health.py:5\n  It is a magic number.")
        self.assertEqual([(x["id"], x["sev"], x["where"]) for x in f], [("R1", "P1", "app/health.py:2-2"), ("R2", "P2", "app/health.py:5")])
        self.assertEqual(f[0]["title"], "Average the middle pair for even-length inputs")
        self.assertIn("`median([1, 3])` returns `3`", f[0]["text"])
        self.assertEqual(groups.counts(f), "P1 1, P2 1")

    def test_no_finding_line_is_no_finding_unless_a_severity_is_named(self):
        self.assertEqual(groups.parse("No issues found. The change looks correct."), [])
        f = groups.parse("Findings: [P1] the cache is never invalidated (app/cache.py)")
        self.assertEqual(len(f), 1)
        self.assertIn("could not split into findings", f[0]["title"])

    def test_codex_reviews_the_range_from_the_base_with_the_effort_and_no_prompt(self):
        cmd = groups.review_command({"review": "codex", "review_effort": "high"}, "abc1234", "def5678", Path("/t"), Path("/o/review.out"))
        self.assertEqual(cmd[1:], ["exec", "review", "--base", "abc1234", "-c", "model_reasoning_effort=high", "-o", "/o/review.out"])
        self.assertEqual(groups.resolve_review("off"), ("off", "off"))
        self.assertEqual(groups.resolve_review("x {out}")[0], "command")
        self.assertEqual(groups.resolve_review("sometimes")[0], "")


class Start(GroupCase):
    def test_the_chain_records_its_first_group_and_says_which_reviewer(self):
        r = self.start()
        self.assertIn("review: the configured review command, at the end of each group", r.stdout)
        self.assertIn("the chain starts on group `r1`", r.stdout)
        g = self.group()
        self.assertEqual((g["k"], g["key"], g["state"], g["first_session"], g["start"]),
                         (1, "r1", "working", 1, git(self.root, "rev-parse", "HEAD").stdout.strip()))
        self.assertIn("You work group `r1`", self.launched(1))

    def test_review_off_keeps_the_chain_of_0_4_7(self):
        super(GroupCase, self).start("--review", "off")
        self.cid = self.chain["id"]
        self.assertNotIn("groups", self.state())
        self.join(1, "s1")
        self.assertEqual(self.unit_start("u3", "s1").returncode, 0)
        self.work()
        self.assertEqual(self.hand_over(1, "s1", next_unit="u3").returncode, 0)
        self.assertNotIn("## Group", self.launched(2))
        self.assertEqual(self.calls(), [])


class Boundary(GroupCase):
    def test_a_chain_session_cannot_start_a_unit_of_a_group_that_has_not_started(self):
        self.start()
        self.join(1, "s1")
        r = self.unit_start("u3", "s1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unit u3 is on group `r2`, and this session works group `r1`", r.stdout)
        self.assertIn("`next_unit: u3`", r.stdout)
        self.assertEqual(self.unit_start("u2", "s1").returncode, 0)
        self.assertEqual(self.unit_start("u3", "the-owner").returncode, 0)   # outside the chain, nothing changes

    def test_ending_a_group_is_not_an_early_hand_over(self):
        self.start()
        self.join(1, "s1", tokens=5_000)
        self.work()
        r = self.hand_over(1, "s1", next_unit="u2")
        self.assertIn("under the 25% hand-over line", r.stdout)
        r = self.hand_over(1, "s1", next_unit="u3")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_the_group_is_reviewed_in_its_own_worktree_before_the_next_session_starts(self):
        r = self.end_group_one(CODEX_SAMPLE)
        self.assertIn("the review of group `r1` is running and the next session starts when it ends", r.stdout)
        b = self.launched(2)
        call = self.calls()[0]
        g = self.group()
        self.assertEqual((call["base"], call["head"], call["dirty"]), (g["start"], self.sha1, ""))
        self.assertNotEqual(os.path.realpath(call["cwd"]), os.path.realpath(self.root))
        self.assertFalse(Path(call["cwd"]).exists())   # the worktree is gone
        self.assertNotIn(call["cwd"], git(self.root, "worktree", "list").stdout)
        self.assertEqual((g["state"], g["fix_session"], g["end"], len(g["findings"])), ("fixing", 2, self.sha1, 1))
        self.assertIn("## Review of group `r1`", b)
        self.assertIn("R1. - [P1] Average the middle pair for even-length inputs — app/health.py:2-2", b)
        self.assertNotIn(call["cwd"], b)
        self.assertIn("hand over with `next_unit: u3`", b)
        rv = (groups.group_dir(self.root, self.cid, 1) / "review.md").read_text()
        self.assertIn("app/health.py:2-2", rv)
        ev = self.events()
        for line in ("chain review: group `r1`, sessions 1-1", "chain reviewed: group `r1`: 1 finding(s) (P1 1); session 2 answers them", "s02 launched"):
            self.assertIn(line, ev)

    def test_the_answering_session_answers_every_finding_then_the_next_group_starts_from_its_last_commit(self):
        self.end_group_one(CODEX_SAMPLE + "\n\n- [P2] Name the constant — {cwd}/app/health.py:2\n  A magic number.")
        self.launched(2)
        self.join(2, "s2")
        r = self.unit_start("u3", "s2")
        self.assertIn("this session answers the review of group `r1`", r.stdout)
        self.assertEqual(self.unit_start("u1", "s2").returncode, 0)
        r = self.hand_over(2, "s2", next_unit="u3")
        self.assertIn("`## Review` answers R1 ([P1] Average the middle pair for even-length inputs) 0 times", r.stdout)
        self.assertIn("answers R2 ([P2] Name the constant) 0 times", r.stdout)
        review = f"- R1 fixed {self.sha1[:7]}\n- R2 dismissed, it reads fine"
        self.write_handoff(2, verified=VERIFIED, next_unit="u3")
        hp = chainlib.link_dir(self.root, self.cid, 2) / "handoff.md"
        hp.write_text(hp.read_text() + f"\n## Review\n\n{review}\n")
        r = cli(self.root, "next", sid="s2")
        self.assertIn(f"`## Review`, R1: answer with `R1 fixed <commit after {self.sha1[:7]}>`", r.stdout)   # the reviewed commit is no fix
        self.assertIn("`## Review`, R2: answer with", r.stdout)                                                  # a dismissal needs evidence
        fix = self.work(line="# even lengths averaged")
        hp.write_text(hp.read_text().replace(review, f"- R1 fixed {fix[:7]}\n- R2 dismissed: app/health.py:2 names it MAX_RETRIES"))
        r = cli(self.root, "next", sid="s2")
        self.assertEqual(r.returncode, 0, r.stdout)
        b = self.launched(3)
        g1, g2 = self.group(0), self.group(1)
        self.assertEqual((g1["state"], g1["cleared"]), ("cleared", fix))
        self.assertEqual((g2["k"], g2["key"], g2["start"], g2["first_session"], g2["state"]), (2, "r2", fix, 3, "working"))
        self.assertIn(f"Group `r1` is cleared at {fix[:7]} (2 review finding(s) answered by session 2). You work group `r2`", b)
        self.assertIn(f"chain cleared: group `r1` is cleared at {fix[:7]}", self.events())
        self.assertEqual(len(self.calls()), 1)   # the answers are not reviewed again: the next session verifies them
        self.join(3, "s3")
        self.assertEqual(self.unit_start("u3", "s3").returncode, 0)
        self.assertEqual(self.unit_start("u1", "s3").returncode, 0)   # an earlier group: a fix carried forward
        st = cli(self.root, "status").stdout
        self.assertIn(f"g01 `r1`  s01-s01  {g1['start'][:7]}..{self.sha1[:7]}  cleared at {fix[:7]}, 2 finding(s) (P1 1, P2 1), answered by s02", st)
        self.assertIn(f"g02 `r2`  s03-  {fix[:7]}..  working", st)
        rep = cli(self.root, "report").stdout
        self.assertIn(f"### Group `r1`: {g1['start'][:7]}..{self.sha1[:7]}, cleared at {fix[:7]}", rep)
        self.assertIn("[P1] Average the middle pair", rep)
        self.assertIn(f"Answers, session 2 (verbatim):\n\n- R1 fixed {fix[:7]}", rep)
        self.assertIn("### Group `r2`", rep)

    def test_a_clean_review_clears_the_group_at_its_last_commit(self):
        self.end_group_one("No issues found.")
        b = self.launched(2)
        g1, g2 = self.group(0), self.group(1)
        self.assertEqual((g1["state"], g1["cleared"], g1["findings"]), ("cleared", self.sha1, []))
        self.assertEqual((g2["key"], g2["start"], g2["first_session"]), ("r2", self.sha1, 2))
        self.assertIn(f"Group `r1` is cleared at {self.sha1[:7]} (its review found nothing). You work group `r2`", b)
        self.assertIn("chain reviewed: group `r1`: no findings", self.events())

    def test_a_finding_that_needs_the_owner_halts_the_chain(self):
        self.end_group_one(CODEX_SAMPLE)
        self.launched(2)
        self.join(2, "s2")
        self.write_handoff(2, verified=VERIFIED, status="halt", next_unit="none", halt="- R1: the median contract is the client's call")
        hp = chainlib.link_dir(self.root, self.cid, 2) / "handoff.md"
        hp.write_text(hp.read_text() + "\n## Review\n\n- R1 halt: the contract is the client's\n")
        self.assertEqual(cli(self.root, "next", sid="s2").returncode, 0)
        self.assertEqual(self.state()["state"], "halted")
        self.assertEqual(self.group()["state"], "fixing")

    def test_a_unit_of_the_next_group_moved_without_unit_start_is_named_in_the_facts(self):
        self.start()
        self.join(1, "s1")
        u3 = self.root / ".taskets" / "u3.md"
        u3.write_text(u3.read_text().replace("status: next", "status: now"))
        self.work()
        self.hand_over(1, "s1", next_unit="u3")
        facts = (chainlib.link_dir(self.root, self.cid, 1) / "facts.md").read_text()
        self.assertIn("Group boundary crossed in a session of group `r1`, so the review of `r1` covers it:", facts)
        self.assertIn("- u3 is on group `r2`, which has not started", facts)


class AfterTheCrossReview(GroupCase):
    """What the Codex cross-review of this change found (2026-10-04), each pinned."""

    def answering(self, findings=CODEX_SAMPLE + "\n\n- [P2] Name the constant — {cwd}/app/health.py:2\n  A magic number.", tokens=27_000):
        self.end_group_one(findings)
        self.launched(2)
        self.join(2, "s2", tokens=tokens)
        return self.work(line="# even lengths averaged")

    def review_handoff(self, review, **kw):
        kw.setdefault("next_unit", "u3")
        return handoff(self.cid, 2, verified=VERIFIED, **kw) + f"\n## Review\n\n{review}\n"

    def test_each_finding_has_one_line_that_starts_with_its_id_and_its_answer(self):
        fix = self.answering()
        ch = self.state()
        for review, why in ((f"- R1 R2 fixed {fix[:7]}", "answers R2 ([P2] Name the constant) 0 times"),
                            (f"- R1 not fixed {fix[:7]}\n- R2 fixed {fix[:7]}", "answers R1 ([P1] Average"),
                            (f"- R1 fixed {fix[:7]}\n- R1 fixed {fix[:7]}\n- R2 fixed {fix[:7]}", "answers R1 ([P1] Average the middle pair for even-length inputs) 2 times"),
                            (f"- R1 fixed {fix[:7]}\n- R2 halt: the client decides", "`halt` needs the handoff's `status: halt`")):
            problems = chainlib.check_handoff(self.root, ch, 2, self.review_handoff(review))
            self.assertTrue(any(why in x for x in problems), (review, problems))
        ok = self.review_handoff(f"- R1 fixed {fix[:7]}\n- R2: dismissed, `$ grep -n MAX app/health.py` shows the name")
        self.assertEqual(chainlib.check_handoff(self.root, ch, 2, ok), [])

    def test_a_halt_leaves_the_whole_review_to_the_session_after_the_owners_answer(self):
        self.answering()
        hp = chainlib.link_dir(self.root, self.cid, 2) / "handoff.md"
        hp.write_text(handoff(self.cid, 2, verified=VERIFIED, status="halt", next_unit="none", halt="- R2: is the constant the client's?"))
        self.assertEqual(cli(self.root, "next", sid="s2").returncode, 0)
        self.assertEqual(self.state()["state"], "halted")
        self.assertEqual(cli(self.root, "resume", "--note", "the constant is ours").returncode, 0)
        b = self.launched(3)
        self.assertIn("## Review of group `r1`", b)
        self.assertEqual(self.group()["fix_session"], 3)

    def test_nothing_uncommitted_crosses_the_end_of_a_group(self):
        self.start()
        self.join(1, "s1")
        self.work()
        (self.root / "app" / "health.py").write_text((self.root / "app" / "health.py").read_text() + "\n# half done\n")
        r = self.hand_over(1, "s1", next_unit="u3", state="app/health.py is half done: the comment is a draft")
        self.assertEqual(r.returncode, 1)
        self.assertIn("uncommitted change(s) where a group ends: app/health.py", r.stdout)
        self.assertEqual(self.calls(), [])
        r = self.hand_over(1, "s1", next_unit="u2", state="app/health.py is half done: the comment is a draft")
        self.assertEqual(r.returncode, 0, r.stdout)   # inside the group, a named change still crosses sessions

    def test_an_answering_session_that_stays_in_its_group_is_held_to_the_early_rule(self):
        fix = self.answering(tokens=5_000)
        hp = chainlib.link_dir(self.root, self.cid, 2) / "handoff.md"
        hp.write_text(self.review_handoff(f"- R1 fixed {fix[:7]}\n- R2 dismissed app/health.py:2 it has a name", next_unit="u2"))
        self.assertIn("under the 25% hand-over line", cli(self.root, "next", sid="s2").stdout)
        hp.write_text(self.review_handoff(f"- R1 fixed {fix[:7]}\n- R2 dismissed app/health.py:2 it has a name", next_unit="u3"))
        self.assertEqual(cli(self.root, "next", sid="s2").returncode, 0)

    def test_a_group_back_at_work_keeps_its_first_review_and_answers(self):
        fix = self.answering(CODEX_SAMPLE)
        hp = chainlib.link_dir(self.root, self.cid, 2) / "handoff.md"
        hp.write_text(self.review_handoff(f"- R1 fixed {fix[:7]}", next_unit="u2"))
        self.assertEqual(cli(self.root, "next", sid="s2").returncode, 0)
        self.assertEqual(self.group()["state"], "working")
        self.launched(3)
        self.join(3, "s3")
        self.answer("No issues found in the new work.")
        end2 = self.work(line="# u2 done")
        self.assertEqual(self.hand_over(3, "s3", next_unit="u3").returncode, 0)
        self.launched(4)
        self.assertEqual([c["base"] for c in self.calls()], [self.group(0)["start"], self.sha1])   # the second review starts where the first ended, so it covers the fix
        rep = cli(self.root, "report").stdout
        self.assertIn(f"### Group `r1`, review 1: {self.group(0)['start'][:7]}..{self.sha1[:7]}, cleared at {end2[:7]}", rep)
        self.assertIn(f"Answers, session 2 (verbatim):\n\n- R1 fixed {fix[:7]}", rep)
        self.assertIn(f"### Group `r1`, review 2: {self.sha1[:7]}..{end2[:7]}", rep)
        self.assertIn("No issues found in the new work.", rep)
        self.assertIn(f"cleared at {end2[:7]}, 1 finding(s) (P1 1), answered by s02; no findings", cli(self.root, "status").stdout)

    def test_a_retagged_unit_and_a_change_only_a_later_unit_covers_are_named(self):
        self.start()
        self.join(1, "s1")
        u3 = self.root / ".taskets" / "u3.md"
        u3.write_text(u3.read_text().replace("rail: r2", "rail: r1"))
        self.work()
        self.hand_over(1, "s1", next_unit="u2")
        facts = (chainlib.link_dir(self.root, self.cid, 1) / "facts.md").read_text()
        self.assertIn("- u3 moved from group `r2` to group `r1` in this session", facts)
        u3.write_text(u3.read_text().replace("rail: r1", "rail: r2"))
        commit_all(self.root, "u3 back on r2")
        self.launched(2)
        self.join(2, "s2")
        self.work("app/billing.py", "# u3 groundwork")
        self.hand_over(2, "s2", next_unit="u2", verified=VERIFIED)
        facts = (chainlib.link_dir(self.root, self.cid, 2) / "facts.md").read_text()
        self.assertIn("- app/billing.py is only in the perimeter of u3, on a group that has not started", facts)

    def test_a_stop_during_the_last_review_stays_a_stop_and_resume_completes_the_chain(self):
        (self.ctl / "sleep").write_text("2")
        self.start()
        self.join(1, "s1")
        self.work()
        self.hand_over(1, "s1", status="complete", next_unit="none")
        cli(self.root, "stop")
        self.wait(lambda: self.group()["state"] == "cleared", "the review is recorded")
        self.assertEqual(self.state()["state"], "stopped")
        r = cli(self.root, "resume")
        self.assertEqual((r.returncode, self.state()["state"]), (0, "complete"), r.stdout)

    def test_skipping_the_last_groups_review_completes_the_chain_and_says_so(self):
        self.answer("", code=3)
        self.start()
        self.join(1, "s1")
        self.work()
        self.hand_over(1, "s1", status="complete", next_unit="none")
        self.wait(lambda: self.state()["state"] == "halted", "the chain halts")
        r = cli(self.root, "resume", "--skip-review")
        self.assertEqual((r.returncode, self.state()["state"]), (0, "complete"), r.stdout)

    def test_status_names_a_review_whose_runner_is_gone(self):
        self.start()
        ch = self.state()
        ch["groups"][0].update(state="reviewing", end=ch["groups"][0]["start"], last_session=1, review_started="2026-01-01T00:00:00")
        chainlib.save(self.root, ch)
        self.assertIn("review interrupted: `charter chain resume` runs it again", cli(self.root, "status").stdout)


class EndAndFailure(GroupCase):
    def test_the_road_finished_reviews_the_last_group_before_the_chain_completes(self):
        self.answer(CODEX_SAMPLE)
        self.start()
        self.join(1, "s1")
        self.work()
        self.assertEqual(self.hand_over(1, "s1", status="complete", next_unit="none").returncode, 0)
        b = self.launched(2)
        self.assertIn("hand over with `status: complete`", b)
        self.assertEqual(self.state()["state"], "running")
        self.join(2, "s2")
        fix = self.work(line="# fixed")
        self.write_handoff(2, verified=VERIFIED, status="complete", next_unit="none")
        hp = chainlib.link_dir(self.root, self.cid, 2) / "handoff.md"
        hp.write_text(hp.read_text() + f"\n## Review\n\n- R1 fixed {fix[:7]}\n")
        self.assertEqual(cli(self.root, "next", sid="s2").returncode, 0)
        c = self.state()
        self.assertEqual((c["state"], c["groups"][0]["cleared"]), ("complete", fix))
        self.assertIn("every group is reviewed", c["reason"])

    def test_a_clean_last_group_completes_the_chain_after_its_review(self):
        self.start()
        self.join(1, "s1")
        self.work()
        self.hand_over(1, "s1", status="complete", next_unit="none")
        self.wait(lambda: self.state()["state"] != "running", "the chain ends")
        self.assertEqual(self.state()["state"], "complete")
        self.assertEqual(len(self.calls()), 1)

    def test_a_review_that_cannot_run_halts_the_chain_and_resume_runs_it_again(self):
        self.answer("", code=3)
        self.end_group_one()
        self.wait(lambda: self.state()["state"] != "running", "the chain halts")
        c = self.state()
        self.assertEqual((c["state"], c["groups"][0]["state"]), ("halted", "review-failed"))
        self.assertIn("the review of group `r1` could not run: the reviewer exited 3", c["reason"])
        self.assertIn("not logged in", c["reason"])
        self.answer("No issues found.")
        r = cli(self.root, "resume", "--note", "codex is logged in again")
        self.assertEqual(r.returncode, 0, r.stdout)
        b = self.launched(2)
        self.assertIn("codex is logged in again", b)
        self.assertEqual((len(self.calls()), self.group(0)["state"]), (2, "cleared"))

    def test_the_owner_can_skip_a_review_that_cannot_run(self):
        self.answer("", code=3)
        self.end_group_one()
        self.wait(lambda: self.state()["state"] != "running", "the chain halts")
        r = cli(self.root, "resume", "--skip-review", "--note", "review it by hand later")
        self.assertEqual(r.returncode, 0, r.stdout)
        b = self.launched(2)
        self.assertIn("the owner skipped its review", b)
        self.assertIn("review it by hand later", b)
        g = self.group(0)
        self.assertEqual((g["state"], g.get("skipped"), g["cleared"]), ("cleared", True, self.sha1))

    def test_a_stop_during_the_review_keeps_the_findings_and_resume_launches_the_answering_session(self):
        (self.ctl / "sleep").write_text("2")
        self.end_group_one(CODEX_SAMPLE)
        r = cli(self.root, "resume")
        self.assertEqual(r.returncode, 1)
        self.assertIn("the review of group `r1` is still running", r.stdout)
        cli(self.root, "stop")
        self.assertEqual(self.state()["state"], "stopped")
        self.wait(lambda: self.group()["state"] == "fixing", "the review is recorded")
        time.sleep(0.5)
        self.assertFalse((self.out / f"chain {self.cid} s02.md").exists())
        self.assertEqual(cli(self.root, "resume").returncode, 0)
        self.assertIn("## Review of group `r1`", self.launched(2))

    def test_a_chain_stopped_at_a_boundary_resumes_with_the_review(self):
        self.start()
        self.join(1, "s1")
        self.work()
        cli(self.root, "stop")
        self.assertEqual(self.hand_over(1, "s1", next_unit="u3").returncode, 0)
        self.assertEqual((self.state()["state"], self.calls()), ("stopped", []))
        self.assertEqual(cli(self.root, "resume").returncode, 0)
        self.launched(2)
        self.assertEqual((len(self.calls()), self.group(0)["state"], self.group()["key"]), (1, "cleared", "r2"))


class Installed(unittest.TestCase):
    def test_install_brings_the_groups_module_and_the_review_rules(self):
        root = make_project(track="prototype")
        try:
            self.assertEqual((root / ".charter" / "chain_groups.py").read_bytes(), (PKG / ".charter" / "chain_groups.py").read_bytes())
            self.assertIn("## 6. A group ends with its review", (root / ".charter" / "chain-rules.md").read_text())
            self.assertIn("## Review", (root / "charter" / "templates" / "handoff.md").read_text())
            import lib
            cfg = lib.config_from({"chain": {"review": "off", "review_effort": "medium", "review_timeout_s": 600}})
            self.assertEqual((cfg["chain"]["review"], cfg["chain"]["review_timeout_s"], cfg[lib.PROBLEMS]), ("off", 600, []))
        finally:
            cleanup(root)


if __name__ == "__main__":
    unittest.main()
