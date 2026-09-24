"""Charter 0.4.4: `charter next`, a read-only answer to "where does the work stand, and what comes next", from the
project's own files; the synthesis lists the units done before charter apart; the perimeter gate leaves files git
ignores alone. Motivated by NowWhat runs of 2026-09-24: the skill guessed the rail-to-unit mapping that `rails_of`
computes, read 17 pre-charter units in skill-delivery as "done but not accepted", and its brief, written into the
gitignored `.nowwhat/`, landed in leCRM's gate log as a perimeter warning (2026-09-14T16:38:43).
Every test here fails on 0.4.3 except the ones marked (guard), which pin behaviour that must not change."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import PKG, charter, cleanup, clean_env, git, make_project, run_hook
from test_migration import pkg
from test_review_regressions import commit_all, set_config

sys.path.insert(0, str(PKG / ".charter"))
import lib  # noqa: E402

RAILS = """# Rails

| id | title | status | order |
|---|---|---|---|
| r0 | The old road | done | 5 |
| r1 | First | in-progress | 10 |
| r2 | Second | next | 20 |
| r3 | Third | next | 30 |
| r4 | Later | todo | 40 |
"""


def unit(uid, status="next", boxes="- [ ] AC-1: it works — probe: `true`", evidence="", log="", heading="Acceptance", **keys):
    fm = "".join(f"{k}: {v}\n" for k, v in keys.items())
    return (f"---\nid: {uid}\ntitle: {uid} title\nstatus: {status}\n{fm}---\n\n## {heading}\n\n{boxes}\n\n"
            f"## Evidence\n\n{evidence}\n\n## Log\n\n{log}\n")


def put(root, uid, text):
    (root / ".taskets" / f"{uid}.md").write_text(text)


def section(out, title):
    """The lines of `charter next` under a heading line that starts with `title`, up to the next blank line."""
    lines = out.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(title))
    rest = lines[start + 1:]
    return rest[:rest.index("")] if "" in rest else rest


def synth_section(out, title):
    lines = out.splitlines()
    start = lines.index(f"## {title}")
    rest = lines[start + 1:]
    return rest[:rest.index("")]


def state_files(root):
    """What a read-only command must leave as it found it: the gate log, the charter state and the worktree."""
    d = root / ".git" / "charter"
    files = {p.name: p.read_bytes() for p in d.iterdir()} if d.is_dir() else {}
    return files, git(root, "status", "--porcelain").stdout


class Next(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        (self.root / ".taskets" / "u1.md").unlink()
        commit_all(self.root, "no u1")
        self.sha = git(self.root, "rev-parse", "--short=12", "HEAD").stdout.strip()

    def tearDown(self):
        cleanup(self.root)

    def road(self):
        (self.root / "charter" / "rails.md").write_text(RAILS)
        put(self.root, "a1", unit("a1", "done", boxes="- [x] AC-1: it works — probe: `true`", evidence=f"- {self.sha}", rail="r1"))
        put(self.root, "b1", unit("b1", rail="r2", log="- 2026-09-24 10:00 started; baseline fails"))
        put(self.root, "b2", unit("b2", rail="r2"))
        put(self.root, "c1", unit("c1"))
        put(self.root, "d1", unit("d1", rail="r0"))
        commit_all(self.root, "the road")

    def next(self, *args):
        r = charter(self.root, "next", *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_it_writes_nothing(self):
        self.road()
        charter(self.root, "unit", "start", "b1")
        before = state_files(self.root)
        self.next()
        self.assertEqual(state_files(self.root), before)

    def test_the_road_its_units_and_what_comes_next(self):
        self.road()
        out = self.next()
        road = section(out, "Road (charter/rails.md):")
        self.assertIn("- r1 [in-progress]: 1 accepted", road)
        self.assertIn("- r2 [next]: 1 in-progress, 1 open", road)
        self.assertIn("- r3 [next]: no unit cites it, so none can start", road)
        self.assertIn("- later (1 todo): r4", road)
        self.assertFalse(any(l.startswith("- r0") for l in road))   # a closed rail is not on the road ahead
        ahead = section(out, "Next on the road:")
        self.assertEqual([l.split(" ")[1] for l in ahead], ["b1", "b2"])   # the unit already started comes first

    def test_units_off_the_road(self):
        self.road()
        off = "\n".join(section(self.next(), "Off the road:"))
        self.assertIn("unit c1 names no rail from charter/rails.md", off)
        self.assertIn("unit d1 is open, and its rail r0 is done", off)

    def test_what_waits_on_the_owner(self):
        self.road()
        (self.root / "charter" / "decisions" / "pick-db.md").write_text(
            "---\nid: pick-db\ntitle: Postgres for records\nstatus: proposed\n---\n\n## Decision\n\nPostgres.\n\n## Because\n\nTested.\n")
        (self.root / "charter" / "changes").mkdir(exist_ok=True)
        (self.root / "charter" / "changes" / "extra.md").write_text("---\nid: extra\ntitle: An export\nstatus: proposed\n---\n\nWhy.\n")
        commit_all(self.root, "proposals")
        set_config(self.root, limits={"file_lines": 900})
        git(self.root, "add", "charter/config.json")
        owner = "\n".join(section(self.next(), "Waiting on the owner:"))
        self.assertIn("rail r1 is in-progress and every unit on it is finished", owner)
        self.assertIn("charter/rails.md:6", owner)   # r1's line in the file
        self.assertIn("decision pick-db — Postgres for records is proposed", owner)
        self.assertIn("change request extra — An export is proposed", owner)
        self.assertIn("staged, for the owner to commit: charter/config.json", owner)

    def test_nothing_waits_on_the_owner(self):
        """An empty section says so."""
        self.assertEqual(section(self.next(), "Waiting on the owner:"), ["- nothing"])

    def test_a_config_problem_is_on_top(self):
        set_config(self.root, rails={"requird": True})
        out = self.next()
        self.assertTrue(out.splitlines()[0].startswith("charter "), out)
        self.assertIn("problem: charter/config.json: unknown key `rails.requird`", out.splitlines()[1])

    def test_without_rails_the_open_units_are_listed(self):
        put(self.root, "p2", unit("p2", priority="p2"))
        put(self.root, "p0", unit("p0", priority="p0"))
        commit_all(self.root, "units")
        out = self.next()
        self.assertNotIn("Road (", out)
        self.assertEqual([l.split(" ")[1] for l in section(out, "Open units (no charter/rails.md")], ["p0", "p2"])

    def test_an_active_unit_with_every_box_checked_is_ready_to_finish(self):
        put(self.root, "f1", unit("f1", "now", boxes="- [x] AC-1: it works — probe: `true`"))
        commit_all(self.root, "f1")
        charter(self.root, "unit", "start", "f1")
        line = next(l for l in self.next().splitlines() if l.startswith("Active unit:"))
        self.assertIn("1/1 criteria closed; every box is checked: finish it", line)

    def test_the_git_hook_state_is_named(self):
        git(self.root, "config", "--unset", "core.hooksPath", check=False)
        self.assertIn("The charter git hook is not active in this clone: run `python3 .charter/bin/charter setup` once", self.next())

    def test_gate_log_counts(self):
        (self.root / "README.md").write_text("changed\n")
        git(self.root, "add", "README.md")
        put(self.root, "g1", unit("g1", "done"))
        git(self.root, "add", ".taskets/g1.md")
        charter(self.root, "check", "--staged")      # a done unit without evidence: one done block
        last = self.next().splitlines()[-1]
        self.assertTrue(last.startswith("Gate log, last 7 days: "), last)
        self.assertRegex(last, r"\d+ block\(s\) \(.*done \d+")


class DoneBeforeCharter(unittest.TestCase):
    """A unit the done gate never judged is not "done but not accepted": it predates the install, or it is on the
    legacy list without `## Acceptance` (the done gate only warns on those, checks.check_unit_done)."""

    def setUp(self):
        self.root = make_project(with_charter=False)
        body = dict(boxes="- [ ] AC-1: it works — probe: `true`")
        self.commit_at("2026-01-01T10:00:00+00:00", "pre", unit("pre", "done", **body), "pre2", unit("pre2", "done", **body),
                       "pre3", unit("pre3", "done", **body))
        self.commit_at("2026-01-02T10:00:00+00:00", "pre3", unit("pre3", "next", **body))
        r = pkg("install", str(self.root), "--track", "prototype")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.commit_at("2026-02-01T10:00:00+00:00")                               # the install commit
        self.commit_at("2026-02-15T10:00:00+00:00", "pre2", unit("pre2", "next", **body))   # reopened after the install ...
        self.commit_at("2026-02-20T10:00:00+00:00", "pre2", unit("pre2", "done", **body))   # ... and closed again, unjudged
        self.commit_at("2026-03-01T10:00:00+00:00", "post", unit("post", "done", **body))
        put(self.root, "pre3", unit("pre3", "done", **body))                      # done in the worktree only

    def tearDown(self):
        cleanup(self.root)

    def commit_at(self, when, *pairs):
        (self.root / ".taskets").mkdir(exist_ok=True)
        for uid, text in zip(pairs[::2], pairs[1::2]):
            put(self.root, uid, text)
        git(self.root, "add", "-A")
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", f"at {when}",
            env=clean_env(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when))

    def synth(self):
        r = charter(self.root, "synth")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)   # and its own anchoring check passes
        return r.stdout

    def ids(self, lines):
        return sorted(l.split(" ")[1] for l in lines if not l.startswith("- none"))

    def test_done_before_the_install_is_listed_apart(self):
        out = self.synth()
        self.assertEqual(self.ids(synth_section(out, "Done before charter (never judged by the done gate)")), ["pre"])
        self.assertEqual(self.ids(synth_section(out, "Done but not accepted (evidence or criteria missing)")), ["post", "pre2", "pre3"])

    def test_charter_next_counts_them_apart(self):
        out = charter(self.root, "next").stdout
        self.assertEqual(self.ids(section(out, "Done without acceptance")[:-1]), ["post", "pre2", "pre3"])
        self.assertIn("- not counted: 1 unit(s) done before charter", out)

    def test_a_legacy_unit_without_acceptance_is_listed_apart(self):
        put(self.root, "old1", unit("old1", "done", heading="Done When"))
        with (self.root / "charter" / "legacy-taskets.txt").open("a") as f:
            f.write("old1\n")
        commit_all(self.root, "old1")
        self.assertIn("old1", self.ids(synth_section(self.synth(), "Done before charter (never judged by the done gate)")))

    def test_a_legacy_unit_that_took_up_acceptance_is_judged(self):
        """(guard) A legacy id with `## Acceptance` is gated like any unit (checks.check_unit_done), and reported so."""
        put(self.root, "old2", unit("old2", "done"))
        with (self.root / "charter" / "legacy-taskets.txt").open("a") as f:
            f.write("old2\n")
        commit_all(self.root, "old2")
        self.assertIn("old2", self.ids(synth_section(self.synth(), "Done but not accepted (evidence or criteria missing)")))


class UnreadableEvidencePath(unittest.TestCase):
    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root reads every directory")
    def test_a_path_this_user_cannot_read_does_not_crash_the_synthesis(self):
        """leCRM's synthesis died on `/root/dryrun-0034/seedprobe/seedprobe.sh` in a unit's evidence (PermissionError)."""
        root = make_project(track="prototype")
        locked = Path(tempfile.mkdtemp(prefix="charter-locked-"))
        try:
            (locked / "inside").mkdir()
            (locked / "inside" / "probe.sh").write_text("true\n")
            sha = git(root, "rev-parse", "--short=12", "HEAD").stdout.strip()
            put(root, "u1", unit("u1", "done", boxes="- [x] AC-1: it works — probe: `true`",
                                 evidence=f"- {sha}\n- ran {locked}/inside/probe.sh"))
            commit_all(root, "u1 done")
            locked.chmod(0)
            r = charter(root, "synth")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("PermissionError", r.stderr)
        finally:
            locked.chmod(0o755)
            cleanup(locked)
            cleanup(root)


class PerimeterIgnoresScratch(unittest.TestCase):
    def setUp(self):
        self.root = make_project()
        (self.root / ".gitignore").write_text((self.root / ".gitignore").read_text() + ".nowwhat/\n"
                                              if (self.root / ".gitignore").exists() else ".nowwhat/\n")
        commit_all(self.root, "ignore a tool's journal")
        charter(self.root, "unit", "start", "u1")

    def tearDown(self):
        cleanup(self.root)

    def edit(self, rel):
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text("x\n")
        rc, out, so, se = run_hook(self.root, "post_tool_gate", {"tool_name": "Write", "tool_input": {"file_path": str(self.root / rel), "content": "x\n"}})
        self.assertEqual(rc, 0, se)
        return out.get("hookSpecificOutput", {}).get("additionalContext", "")

    def logged(self, rel):
        p = self.root / ".git" / "charter" / "log.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines() if rel in l] if p.exists() else []

    def test_a_file_git_ignores_is_not_the_units_work(self):
        self.assertNotIn("outside the perimeter", self.edit(".nowwhat/briefs/b.md"))
        self.assertEqual(self.logged(".nowwhat/briefs/b.md"), [])

    def test_a_tracked_file_outside_the_perimeter_still_warns(self):
        """(guard)"""
        self.assertIn("outside the perimeter", self.edit("README.md"))

    def test_a_tracked_file_under_an_ignore_rule_still_warns(self):
        """(guard) Ignore rules do not apply to a file git tracks, so the unit's work there is still its work."""
        (self.root / ".nowwhat").mkdir()
        (self.root / ".nowwhat" / "kept.md").write_text("kept\n")
        git(self.root, "add", "-f", ".nowwhat/kept.md")
        commit_all(self.root, "force-add")
        self.assertIn("outside the perimeter", self.edit(".nowwhat/kept.md"))

    def test_ignored_lists_only_the_ignored_paths(self):
        self.assertEqual(lib.ignored(self.root, [".nowwhat/a.md", "README.md", "app/x.py"]), {".nowwhat/a.md"})
        self.assertEqual(lib.ignored(self.root, []), set())


if __name__ == "__main__":
    unittest.main()
