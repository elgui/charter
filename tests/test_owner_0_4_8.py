"""Charter 0.4.8: `charter owner [--json]` reports what waits on the owner, and `charter rule`, `approve` and `rail` record
a ruling in one command. Motivated by tele-claude's owner desk (its docs/OWNER_DESK.md §9.6, unit 20260930-103400-88c5):
a ruling cost the owner four steps (edit `status:`, regenerate the index, commit with the owner switch set), and he forgot
the switch twice in 37 real `!` runs (reported in the 2026-09-30 catalog of that spec, §1). `next` and `owner` print one
queue from one function, so the two cannot drift.
Every test here fails on 0.4.7 except the ones marked (guard), which pin behaviour that must not change."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # `python3 -m unittest tests.test_owner_0_4_8` from the repo root

from helpers import charter, cleanup, clean_env, git, make_project  # noqa: E402
from test_review_regressions import commit_all, set_config  # noqa: E402

RAILS = """# Rails

| id | title | status | order | groups |
|---|---|---|---|---|
| r1 | First | in-progress | 10 | |
| r2 | Second | next | 20 | |
"""

PROPOSED = """---
id: pick-db
title: Postgres for records
status: proposed
date: 2026-09-30
owner: Test Owner
kind: design
ask: Do records live in Postgres?
recommend: active
binds: [app/health.py]
check: {check}
expires: 2027-01-01
supersedes:
superseded_by:
---

## Decision

Postgres.

## Because

Tested.

## Recommendation

It is what production runs.
"""

CHANGE = """---
id: extra
title: An export
status: proposed
date: 2026-09-30
paths: [app/export.py]
approved_by:
approved_on:
---

## What is asked

An export.
"""


def unit(uid, status="next", boxes="- [ ] AC-1: it works — probe: `true`", **keys):
    fm = "".join(f"{k}: {v}\n" for k, v in keys.items())
    return f"---\nid: {uid}\ntitle: {uid} title\nstatus: {status}\n{fm}---\n\n## Acceptance\n\n{boxes}\n\n## Evidence\n\n## Log\n\n"


def put(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def head_files(root):
    return sorted(git(root, "show", "--name-only", "--format=", "HEAD").stdout.split())


def head_message(root):
    return git(root, "log", "-1", "--format=%B").stdout.strip()


def project(check="true"):
    root = make_project(track="prototype")
    set_config(root, owner="Test Owner")
    put(root, "charter/decisions/pick-db.md", PROPOSED.format(check=check))
    put(root, "charter/changes/extra.md", CHANGE)
    put(root, "charter/rails.md", RAILS)
    (root / ".taskets" / "u1.md").unlink()
    put(root, ".taskets/a1.md", unit("a1", "deleted", rail="r1"))
    put(root, ".taskets/b1.md", unit("b1", rail="r2", boxes=(
        "- [x] AC-1: done already — owner: check — probe: `true`\n"
        "- [ ] AC-2: rows arrive after the restart — owner: check — probe: `test -f rows.txt`\n"
        "- [ ] AC-3: the installer ran — owner: do\n"
        "- [ ] AC-4: after Test Owner restarts, the card wakes — human: watch the grid\n"
        "- [ ] AC-5: an agent's own work — probe: `true`")))
    put(root, ".taskets/h1.md", unit("h1", rail="r2", gate_reason='"HUMAN-ONLY: the owner runs the installer"'))
    commit_all(root, "a project with a queue")
    charter(root, "decisions", "index")
    commit_all(root, "index")
    return root


class OwnerJsonQueue(unittest.TestCase):
    def setUp(self):
        self.root = project(check="touch check-ran && true")

    def tearDown(self):
        cleanup(self.root)

    def queue(self):
        r = charter(self.root, "owner", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout)

    def test_owner_json_shape(self):
        rep = self.queue()
        self.assertEqual(set(rep), {"project", "charter", "owner", "items"})
        self.assertEqual(rep["project"], str(self.root))
        self.assertEqual(rep["owner"], "Test Owner")
        fields = {"key", "kind", "title", "file", "line", "ask", "recommend", "options", "check", "probe", "marked", "perform", "run"}
        for it in rep["items"]:
            self.assertEqual(set(it), fields, it)
            self.assertIn(it["kind"], ("decide", "do", "check"))
            self.assertTrue(it["perform"] is None or isinstance(it["perform"], list))

    def test_owner_json_proposed_decision(self):
        it = {i["key"]: i for i in self.queue()["items"]}["decision:pick-db"]
        self.assertEqual(it["kind"], "decide")
        self.assertEqual(it["ask"], "Do records live in Postgres?")
        self.assertEqual(it["recommend"], "active")
        self.assertEqual(it["check"], "touch check-ran && true")
        self.assertEqual(it["file"], "charter/decisions/pick-db.md")
        self.assertEqual(it["line"], 4)   # the status: line
        self.assertEqual(it["perform"][-3:], ["rule", "pick-db", "{answer}"])
        self.assertEqual([o["value"] for o in it["options"]], ["active", "rejected"])
        self.assertEqual(it["options"][0]["perform"][-3:], ["rule", "pick-db", "active"])

    def test_owner_json_reports_never_runs(self):
        self.queue()
        charter(self.root, "owner")
        self.assertFalse((self.root / "check-ran").exists())
        self.assertFalse((self.root / "rows.txt").exists())

    def test_owner_json_change_rail_staged(self):
        set_config(self.root, limits={"file_lines": 900})
        git(self.root, "add", "charter/config.json")
        items = {i["key"]: i for i in self.queue()["items"]}
        self.assertEqual(items["change:extra"]["perform"][-3:], ["approve", "extra", "{answer}"])
        self.assertEqual([o["value"] for o in items["change:extra"]["options"]], ["approved", "rejected"])
        rail = items["rail:r1"]
        self.assertEqual((rail["kind"], rail["line"], rail["recommend"]), ("decide", 5, "done"))
        self.assertEqual(rail["perform"][-3:], ["rail", "r1", "{answer}"])
        self.assertNotIn("rail:r2", items)   # units on it are still open
        staged = items["staged"]
        self.assertEqual(staged["kind"], "do")
        self.assertIn("charter/config.json", staged["title"])
        self.assertEqual(staged["perform"][:2], ["env", "CHARTER_OWNER=1"])
        self.assertEqual(staged["perform"][-2:], ["--", "charter/config.json"])

    def test_owner_json_human_only_and_owner_lines(self):
        items = {i["key"]: i for i in self.queue()["items"]}
        self.assertEqual(items["human:h1"]["kind"], "do")
        self.assertIn("HUMAN-ONLY", items["human:h1"]["ask"])
        ac2 = items["owner-line:b1:AC-2"]
        self.assertEqual((ac2["kind"], ac2["probe"], ac2["marked"]), ("check", "test -f rows.txt", True))
        self.assertIn("rows arrive after the restart", ac2["title"])
        self.assertEqual(items["owner-line:b1:AC-3"]["kind"], "do")
        self.assertFalse(items["owner-line:b1:AC-4"]["marked"])   # legacy: names the owner, no segment
        self.assertNotIn("owner-line:b1:AC-1", items)   # checked
        self.assertNotIn("owner-line:b1:AC-5", items)   # the agent's own
        self.assertEqual(items["owner-line:b1:AC-2"]["line"],
                         (self.root / ".taskets" / "b1.md").read_text().splitlines().index(
                             "- [ ] AC-2: rows arrive after the restart — owner: check — probe: `test -f rows.txt`") + 1)

    def test_owner_json_and_next_print_one_queue(self):
        rep = self.queue()
        out = charter(self.root, "next").stdout.splitlines()
        start = out.index("Waiting on the owner:")
        owner = out[start + 1:out.index("", start)]
        self.assertEqual(len(owner), len(rep["items"]))
        self.assertIn("- decision pick-db — Postgres for records is proposed (charter/decisions/pick-db.md)", owner)   # (guard) 0.4.4 wording

    def test_owner_json_human_form(self):
        out = charter(self.root, "owner").stdout
        self.assertIn("Decide:", out)
        self.assertIn("check (not run): touch check-ran && true", out)
        self.assertIn("active: python3 ", out)

    def test_owner_json_segment_keeps_probe_parsing(self):
        """(guard) The `— owner:` segment leaves the probe and done gates reading the line as before."""
        r = charter(self.root, "probe", "b1")
        self.assertIn("test -f rows.txt", r.stdout)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)   # rows.txt does not exist


class RuleVerb(unittest.TestCase):
    def setUp(self):
        self.root = project()
        put(self.root, "notes.md", "an agent's, staged\n")
        git(self.root, "add", "notes.md")
        put(self.root, "scratch.md", "untracked\n")

    def tearDown(self):
        cleanup(self.root)

    def rule(self, *args, env=None):
        return charter(self.root, "rule", *args, env=env)

    def test_rule_active_writes_status_ruling_index_and_commits_only_those(self):
        before = git(self.root, "rev-parse", "HEAD").stdout
        r = self.rule("pick-db", "active", "--note", "as recommended", "--trailer", "Owner-Action: oa-7k2f (terminal)",
                      env={"CLAUDECODE": "1"})   # a `!` command: inside Claude Code, where the gate blocks an agent
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("owner's act", r.stderr)
        self.assertEqual(git(self.root, "rev-parse", "HEAD~1").stdout, before)
        self.assertEqual(head_files(self.root), ["charter/decisions/INDEX.md", "charter/decisions/pick-db.md"])
        msg = head_message(self.root)
        self.assertTrue(msg.startswith("decision pick-db: active"), msg)
        self.assertTrue(msg.endswith("Owner-Action: oa-7k2f (terminal)"), msg)
        text = (self.root / "charter" / "decisions" / "pick-db.md").read_text()
        self.assertIn("\nstatus: active\n", text)
        self.assertRegex(text, r"## Ruling\n\n- \d{4}-\d{2}-\d{2} active by Test Owner: as recommended\n$")
        self.assertIn("| pick-db | Postgres for records | active |", (self.root / "charter" / "decisions" / "INDEX.md").read_text())
        self.assertEqual(git(self.root, "diff", "--cached", "--name-only").stdout.split(), ["notes.md"])   # other work stays staged
        self.assertTrue((self.root / "scratch.md").exists())
        self.assertEqual(git(self.root, "status", "--porcelain", "--", "charter").stdout, "")

    def test_rule_refuses_a_failing_check(self):
        put(self.root, "charter/decisions/pick-db.md", PROPOSED.format(check="echo not yet >&2; false"))
        commit_all(self.root, "a check that fails")
        head = git(self.root, "rev-parse", "HEAD").stdout
        r = self.rule("pick-db", "active")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not yet", r.stderr)
        self.assertEqual(git(self.root, "rev-parse", "HEAD").stdout, head)
        self.assertIn("status: proposed", (self.root / "charter" / "decisions" / "pick-db.md").read_text())

    def test_rule_rejected_skips_the_check(self):
        put(self.root, "charter/decisions/pick-db.md", PROPOSED.format(check="false"))
        commit_all(self.root, "a check that fails")
        r = self.rule("pick-db", "rejected")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("\nstatus: rejected\n", (self.root / "charter" / "decisions" / "pick-db.md").read_text())

    def test_rule_refuses_a_decision_that_is_not_proposed(self):
        r = self.rule("retry-limit", "rejected")
        self.assertEqual(r.returncode, 1)
        self.assertIn("is active", r.stderr)

    def test_rule_refuses_a_bare_superseded(self):
        self.assertIn("--by", self.rule("pick-db", "superseded").stderr)
        self.assertIn("no other decision", self.rule("pick-db", "superseded", "--by", "nope").stderr)

    def test_rule_supersedes_an_active_decision(self):
        self.assertEqual(self.rule("pick-db", "active").returncode, 0)
        r = self.rule("retry-limit", "superseded", "--by", "pick-db")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = (self.root / "charter" / "decisions" / "retry-limit.md").read_text()
        self.assertIn("\nstatus: superseded\n", text)
        self.assertIn("\nsuperseded_by: pick-db\n", text)

    def test_rule_dry_run_changes_nothing(self):
        head = git(self.root, "rev-parse", "HEAD").stdout
        r = self.rule("pick-db", "active", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("+status: active", r.stdout)
        self.assertIn("would commit", r.stdout)
        self.assertEqual(git(self.root, "rev-parse", "HEAD").stdout, head)
        self.assertEqual(git(self.root, "status", "--porcelain", "--", "charter").stdout, "")

    def test_rule_dry_run_does_not_run_the_check(self):
        """A check may write files; a dry run names it and leaves it unrun."""
        put(self.root, "charter/decisions/pick-db.md", PROPOSED.format(check="touch check-ran && true"))
        commit_all(self.root, "a check that writes a file")
        r = self.rule("pick-db", "active", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("would run the check first: touch check-ran && true", r.stdout)
        self.assertFalse((self.root / "check-ran").exists())

    def test_rule_refuses_an_uncommitted_proposal(self):
        p = self.root / "charter" / "decisions" / "pick-db.md"
        p.write_text(p.read_text().replace("Postgres.", "MySQL."))
        r = self.rule("pick-db", "active")
        self.assertEqual(r.returncode, 1)
        self.assertIn("uncommitted", r.stderr)

    def test_rule_index_leaves_out_another_sessions_uncommitted_decision(self):
        put(self.root, "charter/decisions/draft.md", "---\nid: draft\ntitle: A draft\nstatus: proposed\n---\n\nx\n")
        self.assertEqual(self.rule("pick-db", "active").returncode, 0)
        committed = git(self.root, "show", "HEAD:charter/decisions/INDEX.md").stdout
        self.assertNotIn("draft", committed)
        self.assertIn("draft", (self.root / "charter" / "decisions" / "INDEX.md").read_text())   # back in the working copy

    def test_rule_refused_commit_rolls_back(self):
        """A commit the gate refuses leaves nothing half-done."""
        hook = self.root / ".charter" / "githooks" / "pre-commit"
        saved = hook.read_text()
        hook.write_text("#!/bin/sh\necho refused by a test >&2\nexit 1\n")
        try:
            r = self.rule("pick-db", "active")
        finally:
            hook.write_text(saved)
        self.assertEqual(r.returncode, 1)
        self.assertIn("refused by a test", r.stderr)
        self.assertEqual(git(self.root, "status", "--porcelain", "--", "charter").stdout, "")
        self.assertEqual(git(self.root, "diff", "--cached", "--name-only").stdout.split(), ["notes.md"])

    def test_rule_refused_commit_keeps_a_staged_index(self):
        """An index another session staged is staged again, as it was, when the commit is refused."""
        ip = self.root / "charter" / "decisions" / "INDEX.md"
        staged = ip.read_text() + "\nstaged by another session\n"
        ip.write_text(staged)
        git(self.root, "add", "charter/decisions/INDEX.md")
        hook = self.root / ".charter" / "githooks" / "pre-commit"
        saved = hook.read_text()
        hook.write_text("#!/bin/sh\necho refused by a test >&2\nexit 1\n")
        try:
            r = self.rule("pick-db", "active")
        finally:
            hook.write_text(saved)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(git(self.root, "show", ":charter/decisions/INDEX.md").stdout, staged)
        self.assertEqual(ip.read_text(), staged)


class ApproveAndRailVerbs(unittest.TestCase):
    def setUp(self):
        self.root = project()

    def tearDown(self):
        cleanup(self.root)

    def test_approve_sets_status_who_and_when(self):
        r = charter(self.root, "approve", "extra", "--trailer", "Owner-Action: oa-1 (dashboard)")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        fields = (self.root / "charter" / "changes" / "extra.md").read_text()
        self.assertIn("\nstatus: approved\n", fields)
        self.assertIn("\napproved_by: Test Owner\n", fields)
        self.assertRegex(fields, r"\napproved_on: \d{4}-\d{2}-\d{2}\n")
        self.assertEqual(head_files(self.root), ["charter/changes/extra.md"])
        self.assertTrue(head_message(self.root).endswith("Owner-Action: oa-1 (dashboard)"))

    def test_approve_reject(self):
        r = charter(self.root, "approve", "extra", "--reject", "--note", "not now")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("\nstatus: rejected\n", (self.root / "charter" / "changes" / "extra.md").read_text())
        self.assertEqual(head_message(self.root), "change extra: rejected")

    def test_approve_refuses_one_already_ruled(self):
        charter(self.root, "approve", "extra")
        r = charter(self.root, "approve", "extra", "--reject")
        self.assertEqual(r.returncode, 1)
        self.assertIn("is approved", r.stderr)

    def test_rail_sets_the_status_cell(self):
        r = charter(self.root, "rail", "r1", "done", "--trailer", "Owner-Action: oa-2 (terminal)")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("| r1 | First | done | 10 | |", (self.root / "charter" / "rails.md").read_text())
        self.assertEqual(head_files(self.root), ["charter/rails.md"])
        self.assertTrue(head_message(self.root).startswith("rail r1: done"))

    def test_rail_refuses_an_unknown_id_or_status(self):
        self.assertIn("no rail", charter(self.root, "rail", "r9", "done").stderr)
        r = charter(self.root, "rail", "r1", "finished")
        self.assertEqual(r.returncode, 1)
        self.assertIn("todo, next, in-progress, done, parked, dropped", r.stderr)

    def test_no_push_from_any_verb(self):
        remote = self.root.parent / (self.root.name + "-remote.git")
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, env=clean_env())
        git(self.root, "remote", "add", "origin", str(remote))
        git(self.root, "push", "-q", "-u", "origin", "main")
        pushed = git(self.root, "rev-parse", "origin/main").stdout
        for args in (("rule", "pick-db", "active"), ("approve", "extra"), ("rail", "r1", "done")):
            r = charter(self.root, *args)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("not pushed", r.stdout)
        self.assertEqual(subprocess.run(["git", "-C", str(remote), "rev-parse", "main"], capture_output=True, text=True).stdout, pushed)
        self.assertEqual(git(self.root, "rev-list", "--count", "origin/main..main").stdout.strip(), "3")
        cleanup(remote)


if __name__ == "__main__":
    unittest.main()
