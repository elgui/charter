"""Charter 0.4.13: charter answers in JSON for the road and for a unit, so a tool reads units through charter's own
parser instead of one of its own (tele-claude, rail r17-unit-console, 2026-10-10). `charter unit show --json
[--session <sid>]` is a session's active unit and where it came from; `charter unit show <id> --json` is one unit as
the gates read it, with `done_blockers` from the done gate's own function; `charter next --json` is the road, every row.
The text output of both commands is unchanged. Every test here fails on 0.4.12 except the ones marked (guard)."""
import json
import re
import sys
import unittest

from helpers import PKG, charter, cleanup, git, make_project
from test_next_0_4_4 import put, state_files, unit
from test_review_regressions import commit_all

sys.path.insert(0, str(PKG / ".charter"))

RAILS = """# Rails

| id | title | status | order |
|---|---|---|---|
| r0 | The old road | done | 5 |
| r1 | First | in-progress | 10 |
| r2 | Second | next | 20 |
| r3 | Third | todo | 30 |
"""

UNIT_KEYS = {"schema", "charter", "id", "title", "status", "path", "rail", "kind", "perimeter", "decisions", "gate",
             "acceptance_heading", "acceptance", "evidence", "log", "done_blockers"}
ROW_KEYS = {"line", "label", "text", "checked", "probe", "owner"}
NEXT_KEYS = {"schema", "charter", "active", "rails", "off_road", "done_without_acceptance", "owner_waiting"}
RAIL_KEYS = {"id", "title", "status", "order", "units"}
RAIL_UNIT_KEYS = {"id", "title", "status", "path", "group", "order", "boxes", "state"}


def acc_unit():
    """A unit with every field the shape names: probes, a marked owner line, an unmarked one, six log lines."""
    return ("---\nid: acc\ntitle: The console reads units\nstatus: in-progress\nrail: r1\nkind: work\n"
            "perimeter: [app/health.py, tests/**]\ndecisions: [retry-limit]\ngate: human\ngroup: console\norder: 2\n---\n\n"
            "# The console reads units\n\n## Context\n\nWhy.\n\n## Acceptance\n\n"
            "- [x] AC-1: health answers — probe: `python3 -c 'import app.health'`\n"
            "- [ ] AC-2: the owner looks at the page — owner: check\n"
            "- [ ] AC-3: Test Owner runs the deploy\n"
            "- [ ] a line without an id\n\n"
            "## Evidence\n\n- commit {sha}\n- `$ python3 -c 'import app.health'` → exit 0\n\n"
            "## Log\n\n" + "".join(f"- 2026-10-10 0{i}:00 step {i}\n" for i in range(1, 7)))


class JsonVerbs(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        self.sha = git(self.root, "rev-parse", "--short=12", "HEAD").stdout.strip()
        r = self.root
        (r / "charter" / "rails.md").write_text(RAILS)
        put(r, "acc", acc_unit().replace("{sha}", self.sha))
        # a `## Done When` unit with no probes, every box checked, and a commit as evidence: the gate would pass it
        put(r, "dw", unit("dw", boxes="- [x] the page loads\n- [x] the list is sorted", heading="Done When",
                          evidence=f"- {self.sha}", rail="r2", group="console", order="1"))
        put(r, "dn", unit("dn", "done", boxes="- [x] AC-1: it works — probe: `true`", evidence=f"- {self.sha}", rail="r1"))
        put(r, "dnu", unit("dnu", "done", rail="r1"))                          # done, its box open: done without acceptance
        put(r, "noacc", "---\nid: noacc\ntitle: No checklist\nstatus: next\nrail: r2\n---\n\n## Context\n\nNone.\n")
        put(r, "off", unit("off"))                                             # names no rail
        put(r, "unk", unit("unk", rail="r13-model-routing"))                   # names a rail the file does not list
        put(r, "old", unit("old", rail="r0"))                                  # open, on a closed rail
        for i in range(6):                                                     # more than `--limit` on one rail
            put(r, f"m{i}", unit(f"m{i}", rail="r2", order=str(10 + i)))
        commit_all(r, "the testbed")

    def tearDown(self):
        cleanup(self.root)

    def json(self, *args, env=None, code=0):
        r = charter(self.root, *args, "--json", env=env)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return json.loads(r.stdout)

    # ------------------------------------------------------------ unit show --json [--session]

    def test_the_active_unit_and_where_it_came_from(self):
        self.assertEqual(self.json("unit", "show"), {"schema": 1, "charter": "0.4.13", "active": None, "source": None})
        charter(self.root, "unit", "start", "acc", env={"CLAUDE_CODE_SESSION_ID": "s1"})
        charter(self.root, "unit", "start", "dw", env={"CLAUDE_CODE_SESSION_ID": "s2"})   # the checkout's last choice: dw
        self.assertEqual(self.json("unit", "show", "--session", "s1")["active"], "acc")
        self.assertEqual(self.json("unit", "show", "--session", "s1")["source"], "session")
        self.assertEqual(self.json("unit", "show", "--session", "s3"), {"schema": 1, "charter": "0.4.13", "active": "dw", "source": "checkout"})
        self.assertEqual(self.json("unit", "show", env={"CLAUDE_CODE_SESSION_ID": "s1"})["active"], "acc")
        env = self.json("unit", "show", "--session", "s1", env={"CHARTER_UNIT": "off"})
        self.assertEqual((env["active"], env["source"]), ("off", "env"))   # as the gates read it: an engine's export wins

    def test_session_flag_in_text_output(self):
        charter(self.root, "unit", "start", "acc", env={"CLAUDE_CODE_SESSION_ID": "s1"})
        charter(self.root, "unit", "start", "dw", env={"CLAUDE_CODE_SESSION_ID": "s2"})
        self.assertEqual(charter(self.root, "unit", "show", "--session", "s1").stdout.strip(), "acc")
        self.assertEqual(charter(self.root, "unit", "show").stdout.strip(), "dw")   # (guard) the text form is unchanged

    def test_session_flag_on_start_and_stop(self):
        charter(self.root, "unit", "start", "acc", "--session", "s1")
        self.assertEqual((self.root / ".git" / "charter" / "active-s1").read_text().strip(), "acc")
        charter(self.root, "unit", "start", "dw")                              # no session: the checkout's file only
        self.assertEqual(self.json("unit", "show", "--session", "s1")["active"], "acc")
        charter(self.root, "unit", "stop", "--session", "s1")
        self.assertFalse((self.root / ".git" / "charter" / "active-s1").exists())

    def test_show_writes_nothing(self):
        """`unit show` is a read: without `<git dir>/charter`, neither form makes it (review of PR #13, 2026-10-11)."""
        import shutil
        shutil.rmtree(self.root / ".git" / "charter", ignore_errors=True)
        self.assertEqual(self.json("unit", "show")["active"], None)
        self.json("unit", "show", "acc")
        self.assertEqual(charter(self.root, "unit", "show").stdout.strip(), "no active unit")
        self.assertFalse((self.root / ".git" / "charter").exists())
        charter(self.root, "unit", "start", "acc")   # (guard) start still makes it
        self.assertEqual((self.root / ".git" / "charter" / "active").read_text().strip(), "acc")

    def test_json_on_start_and_stop_is_refused(self):
        """`--json` asks for a read; `start` and `stop` write, so they refuse it and change nothing (review of PR #13)."""
        charter(self.root, "unit", "start", "dw")
        for args in (("start", "acc"), ("stop",)):
            r = charter(self.root, "unit", *args, "--json")
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("charter unit: --json works with `show` only", r.stderr)
            self.assertEqual((self.root / ".git" / "charter" / "active").read_text().strip(), "dw")

    # ------------------------------------------------------------ unit show <id> --json

    def test_one_unit_as_the_gates_read_it(self):
        u = self.json("unit", "show", "acc")
        self.assertEqual(set(u), UNIT_KEYS)
        self.assertEqual((u["schema"], u["charter"], u["id"], u["status"], u["path"]), (1, "0.4.13", "acc", "in-progress", ".taskets/acc.md"))
        self.assertEqual((u["rail"], u["kind"], u["gate"], u["acceptance_heading"]), ("r1", "work", "human", "Acceptance"))
        self.assertEqual((u["perimeter"], u["decisions"]), (["app/health.py", "tests/**"], ["retry-limit"]))
        rows = u["acceptance"]
        self.assertTrue(all(set(x) == ROW_KEYS for x in rows))
        self.assertEqual([x["label"] for x in rows], ["AC-1", "AC-2", "AC-3", None])
        self.assertEqual([x["checked"] for x in rows], [True, False, False, False])
        self.assertEqual([x["probe"] for x in rows], ["python3 -c 'import app.health'", None, None, None])
        self.assertEqual([x["owner"] for x in rows], [False, True, True, False])   # marked, and unmarked naming the owner
        self.assertEqual(rows[3]["text"], "a line without an id")
        lines = (self.root / ".taskets" / "acc.md").read_text().splitlines()
        for x in rows:   # `line` is the file's own 1-based line number
            self.assertIn(x["text"], lines[x["line"] - 1])
        self.assertEqual(u["evidence"], [f"commit {self.sha}", "`$ python3 -c 'import app.health'` → exit 0"])
        self.assertEqual(u["log"], [f"2026-10-10 0{i}:00 step {i}" for i in range(2, 7)])   # the last five
        self.assertEqual(u["done_blockers"], ["status is done but 3 acceptance box(es) are unchecked"])

    def test_line_numbers_past_a_nested_acceptance_heading(self):
        """A nested heading that starts with `Acceptance` again is not in the section's text, so `line` cannot count
        on the section's lines being contiguous in the file (review of PR #13, 2026-10-11)."""
        import lib
        body = ("# Nested\n\n## Acceptance\n\n  - [ ] AC-1: the first\n### Acceptance, the owner's part\n"
                "- [ ] AC-2: the second — owner: check\n\n- [x] AC-3: the third\n\n## Log\n")
        put(self.root, "nest", "---\nid: nest\ntitle: Nested\nstatus: next\nrail: r1\n---\n\n" + body)
        rows = self.json("unit", "show", "nest")["acceptance"]
        lines = (self.root / ".taskets" / "nest.md").read_text().splitlines()
        self.assertEqual([(x["label"], x["line"]) for x in rows], [("AC-1", 12), ("AC-2", 14), ("AC-3", 16)])
        for x in rows:
            self.assertIn(f"{x['label']}: {x['text']}", lines[x["line"] - 1])
        # (guard) the text every gate reads is unchanged
        self.assertEqual(lib.acceptance(body), "- [ ] AC-1: the first\n- [ ] AC-2: the second — owner: check\n\n- [x] AC-3: the third")

    def test_owner_flag_follows_the_owner_queue(self):
        """`owner` uses the rule `charter owner` applies, so every open line it marks is in the owner's queue."""
        rows = self.json("unit", "show", "acc")["acceptance"]
        q = self.json("owner")["items"]
        lines = {i["line"] for i in q if i["key"].startswith("owner-line:acc:")}
        self.assertEqual({x["line"] for x in rows if x["owner"] and not x["checked"]}, lines)
        marked = {i["line"]: i["marked"] for i in q if i["key"].startswith("owner-line:acc:")}
        self.assertEqual(sorted(marked.values()), [False, True])   # one marked, one the queue calls an unmarked owner line

    def test_a_done_when_unit_with_no_probes(self):
        u = self.json("unit", "show", "dw")
        self.assertEqual(u["acceptance_heading"], "Done When")
        self.assertEqual([(x["label"], x["text"], x["checked"], x["probe"], x["owner"]) for x in u["acceptance"]],
                         [(None, "the page loads", True, None, False), (None, "the list is sorted", True, None, False)])
        self.assertEqual(u["done_blockers"], [])
        self.assertEqual((u["kind"], u["gate"], u["perimeter"]), (None, None, []))

    def test_a_unit_with_no_checklist_and_an_unknown_id(self):
        u = self.json("unit", "show", "noacc")
        self.assertEqual((u["acceptance_heading"], u["acceptance"], u["evidence"], u["log"]), (None, [], [], []))
        self.assertEqual(len(u["done_blockers"]), 2)
        self.assertEqual(self.json("unit", "show", "nope", code=1)["error"], "no tasket with id nope in .taskets/")

    def test_done_blockers_match_the_gate(self):
        """For every unit of the testbed, `done_blockers` is what the done gate refuses when the unit says done: at
        commit (the flips staged) and over the tree (`--all --strict`, which judges a unit already done)."""
        ids = sorted(p.stem for p in (self.root / ".taskets").glob("*.md"))
        said = {uid: self.json("unit", "show", uid)["done_blockers"] for uid in ids}
        self.assertTrue(any(said.values()) and not all(said.values()), said)   # some pass, some do not
        flipped = []
        for uid in ids:
            p = self.root / ".taskets" / f"{uid}.md"
            text = p.read_text()
            if not re.search(r"^status: done$", text, re.M):
                p.write_text(re.sub(r"^status: .*$", "status: done", text, count=1, flags=re.M))
                flipped.append(uid)
        git(self.root, "add", "-A")
        for args, judged in ((("--staged",), flipped), (("--all", "--strict"), ids)):
            out = charter(self.root, "check", *args, "--done").stdout
            gate: dict[str, list[str]] = {}
            for m in re.finditer(r"^charter/done block \[\.taskets/([^\]]+)\.md\]: (.*?)(?: Override: .*)?$", out, re.M):
                gate.setdefault(m.group(1), []).append(m.group(2))
            for uid in judged:
                self.assertEqual(gate.get(uid, []), said[uid], f"{uid} with {args}:\n{out}")

    def test_done_blockers_with_two_status_lines(self):
        """The parser reads the last of two `status:` lines; `done_blockers` judges the unit as done all the same
        (review of PR #13, 2026-10-11)."""
        put(self.root, "dup", unit("dup", "next\nstatus: open", rail="r1"))   # an open box, no evidence
        u = self.json("unit", "show", "dup")
        self.assertEqual(u["status"], "open")
        self.assertEqual(len(u["done_blockers"]), 2, u["done_blockers"])

    # ------------------------------------------------------------ next --json

    def test_the_road_every_row(self):
        charter(self.root, "unit", "start", "acc", env={"CLAUDE_CODE_SESSION_ID": "s1"})
        n = self.json("next")
        self.assertEqual(set(n), NEXT_KEYS)
        self.assertEqual((n["schema"], n["charter"], n["active"]), (1, "0.4.13", "acc"))
        self.assertEqual([(r["id"], r["status"], r["order"]) for r in n["rails"]],
                         [("r0", "done", 5), ("r1", "in-progress", 10), ("r2", "next", 20), ("r3", "todo", 30)])
        self.assertTrue(all(set(r) == RAIL_KEYS for r in n["rails"]))
        r1, r2 = n["rails"][1], n["rails"][2]
        self.assertEqual(r1["title"], "First")
        self.assertEqual(sorted(u["id"] for u in r1["units"]), ["acc", "dn", "dnu"])
        self.assertEqual([u["id"] for u in r2["units"]], ["dw", "m0", "m1", "m2", "m3", "m4", "m5", "noacc"])   # no --limit cut
        acc = next(u for u in r1["units"] if u["id"] == "acc")
        self.assertEqual(set(acc), RAIL_UNIT_KEYS)
        self.assertEqual((acc["group"], acc["order"], acc["boxes"], acc["path"]), ("console", 2, {"checked": 1, "total": 4}, ".taskets/acc.md"))
        self.assertEqual({o["id"]: o["reason"] for o in n["off_road"]},
                         {"off": "names no rail", "u1": "names no rail", "unk": "names unknown rail r13-model-routing",
                          "old": "is open, and its rail r0 is done"})
        self.assertEqual([d["id"] for d in n["done_without_acceptance"]], ["dnu"])
        self.assertEqual(n["owner_waiting"], len(self.json("owner")["items"]))
        self.assertGreaterEqual(n["owner_waiting"], 2)
        self.assertEqual(self.json("next", "--session", "s9")["active"], "acc")   # the checkout's choice, still open

    def test_no_rails_file(self):
        (self.root / "charter" / "rails.md").unlink()
        n = self.json("next")
        self.assertEqual((n["rails"], n["off_road"]), (None, []))

    def test_json_writes_nothing(self):   # (guard) next stays read-only, its JSON form too
        charter(self.root, "unit", "start", "acc")
        before = state_files(self.root)
        self.json("next")
        self.assertEqual(state_files(self.root), before)

    def test_text_output_is_unchanged(self):   # (guard)
        out = charter(self.root, "next").stdout
        self.assertFalse(out.lstrip().startswith("{"))
        self.assertIn("unit off names no rail from charter/rails.md", out)
        self.assertIn("unit unk names unknown rail r13-model-routing", out)
        self.assertIn("- +4 more (`--limit`)", out)


if __name__ == "__main__":
    unittest.main()
