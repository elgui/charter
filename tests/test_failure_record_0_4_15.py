"""Charter 0.4.15: three picks from the technology watch on HERMES (docs/briefs/2026-10-13-hermes-failure-record-and-perimeter-fit.md).

K11. A probe failure leaves a record, not a line: each probe's acceptance id, command, outcome, exit code, duration
and its stdout and stderr tails kept apart; the paths changed since the unit's base, inside and outside its
perimeter; `charter probe <id> --json`; the gate log names the failing ids; the done gate names the unchecked boxes;
the chain briefing carries the tails. The text line `- `$ cmd` → result` is unchanged, because tele-claude's checker
parses it (services/checker/core.py:98 there).
K12. How well a unit's perimeter fit its work: the paths its commits touched outside the perimeter, and the
perimeter entries none touched, in `charter unit show <id>` and in `charter synth`. A report, never a gate.
K13. A session is not charged to a unit another session chose: the checkout's `active` file is inherited only when
no session chose it, and a path another session edited is not charged to the committing session's unit.
Every test here fails on 0.4.14 except the ones marked (guard)."""
import json
import re
import sys
import unittest
from pathlib import Path

from helpers import PKG, charter, cleanup, git, make_project, run_hook
from test_chain_0_4_7 import ChainCase, cli as chain_cli
from test_next_0_4_4 import put, synth_section, unit
from test_review_regressions import commit_all

sys.path.insert(0, str(PKG / ".charter"))
import chain as chainlib  # noqa: E402

# tele-claude's checker, services/checker/core.py:98 at 8ebdd3a: the line format this release keeps
PROBE_LINE = re.compile(r"^- `\$ (?P<cmd>.*)` → (?P<result>.*)$")
RECORD_KEYS = {"ac", "command", "outcome", "exit", "duration_s", "stdout_tail", "stderr_tail", "stdout_lines", "stderr_lines"}
PROBE_KEYS = {"schema", "charter", "unit", "path", "probes", "failed", "changed", "findings"}
VERSION = (PKG / "VERSION").read_text().strip()

# AC-1 passes; AC-2 prints to both streams and fails; its stdout ends with a line that looks like a probe line
# (a probe command cannot hold a backtick, so the output comes from a script)
LOUD = "python3 tests/loud.py"
LOUD_PY = "import sys\nprint('collected 3')\nprint('- `$ fake` → exit 0')\nprint('E   boom', file=sys.stderr)\nsys.exit(1)\n"


def probe_unit(uid, probes, perimeter="[app/health.py, tests/**]", status="in-progress", extra=""):
    boxes = "\n".join(f"- [ ] AC-{i}: criterion {i} — probe: `{cmd}`" for i, cmd in enumerate(probes, 1))
    return (f"---\nid: {uid}\ntitle: {uid} title\nstatus: {status}\nperimeter: {perimeter}\n---\n\n## Acceptance\n\n{boxes}\n\n"
            f"## Evidence\n\n## Log\n\n- 2026-10-13 10:00 created\n{extra}")


def log_rows(root):
    p = root / ".git" / "charter" / "log.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


class Project(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")

    def tearDown(self):
        cleanup(self.root)


# ---------------------------------------------------------------- K11: the probe record

class ProbeRecord(Project):
    def setUp(self):
        super().setUp()
        (self.root / "tests" / "loud.py").write_text(LOUD_PY)
        put(self.root, "pr", probe_unit("pr", ["true", LOUD]))
        commit_all(self.root, "the unit")

    def test_the_text_lines_are_unchanged(self):
        """(guard) one `- `$ cmd` → result` line per probe, as 0.4.14 printed it, and no other line parses as one."""
        r = charter(self.root, "probe", "pr")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[:2], ["- `$ true` → exit 0", f"- `$ {LOUD}` → exit 1 (E   boom)"])
        parsed = [l for l in lines if PROBE_LINE.match(l.strip())]   # the checker strips each line before matching
        self.assertEqual(len(parsed), 2, r.stdout)

    def test_a_failure_prints_its_tails_apart(self):
        out = charter(self.root, "probe", "pr").stdout
        self.assertIn(f"AC-2 failed: `{LOUD}` exited 1 after ", out)
        block = out.split("AC-2 failed:", 1)[1]
        self.assertIn("stdout, last 2 of 2 line(s):", block)
        self.assertIn("  | collected 3", block)
        self.assertIn("stderr, last 1 of 1 line(s):", block)
        self.assertIn("  | E   boom", block)
        self.assertNotIn("AC-1 failed", out)

    def test_the_json_record(self):
        r = charter(self.root, "probe", "pr", "--json")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(set(d), PROBE_KEYS)
        self.assertEqual((d["schema"], d["charter"], d["unit"], d["path"], d["failed"]), (1, VERSION, "pr", ".taskets/pr.md", ["AC-2"]))
        ok, bad = d["probes"]
        self.assertEqual(set(ok), RECORD_KEYS)
        self.assertEqual((ok["ac"], ok["command"], ok["outcome"], ok["exit"]), ("AC-1", "true", "passed", 0))
        self.assertEqual((bad["ac"], bad["outcome"], bad["exit"]), ("AC-2", "failed", 1))
        self.assertEqual(bad["stdout_tail"], "collected 3\n- `$ fake` → exit 0")
        self.assertEqual(bad["stderr_tail"], "E   boom")
        self.assertEqual((bad["stdout_lines"], bad["stderr_lines"]), (2, 1))
        self.assertIsInstance(bad["duration_s"], float)
        self.assertEqual(len(d["findings"]), 1)
        self.assertTrue(d["findings"][0].startswith("AC-2 probe failed"), d["findings"])

    def test_an_unknown_unit_in_json(self):
        r = charter(self.root, "probe", "nope", "--json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no tasket with id nope", json.loads(r.stdout)["error"])

    def test_the_tails_are_capped(self):
        many = "python3 -c \"[print('x' * 99 + str(i % 10)) for i in range(500)]; raise SystemExit(3)\""
        put(self.root, "big", probe_unit("big", [many]))
        d = json.loads(charter(self.root, "probe", "big", "--json").stdout)
        rec = d["probes"][0]
        self.assertEqual((rec["exit"], rec["stdout_lines"]), (3, 500))
        self.assertLessEqual(len(rec["stdout_tail"].encode()), 2048)
        self.assertLessEqual(len(rec["stdout_tail"].splitlines()), 20)
        self.assertTrue(rec["stdout_tail"].endswith("x" * 99 + "9"), rec["stdout_tail"][-120:])
        self.assertTrue(all(len(l) == 100 for l in rec["stdout_tail"].splitlines()))   # cut at a line, never inside one

    def test_a_timeout_is_its_own_outcome(self):
        put(self.root, "slow", probe_unit("slow", ["echo started; sleep 5"]))
        r = charter(self.root, "probe", "slow", "--timeout", "1")
        self.assertIn("timed out after 1 s", r.stdout.splitlines()[0])   # (guard) the text line tele-claude reads
        rec = json.loads(charter(self.root, "probe", "slow", "--timeout", "1", "--json").stdout)["probes"][0]
        self.assertEqual((rec["outcome"], rec["exit"]), ("timeout", None))
        self.assertEqual(rec["stdout_tail"], "started")

    def test_the_log_names_the_failing_ids(self):
        charter(self.root, "probe", "pr")
        row = [r for r in log_rows(self.root) if r["gate"] == "probe"][-1]
        self.assertEqual(row["detail"], "2 probe(s) of pr; failed: AC-2")
        self.assertEqual(row["failed"], ["AC-2"])
        charter(self.root, "probe", "pr", "--json")   # a run, so it is logged too
        self.assertEqual(len([r for r in log_rows(self.root) if r["gate"] == "probe"]), 2)

    def test_a_pass_logs_as_before(self):
        """(guard)"""
        put(self.root, "fine", probe_unit("fine", ["true"]))
        self.assertEqual(charter(self.root, "probe", "fine").returncode, 0)
        row = [r for r in log_rows(self.root) if r["gate"] == "probe"][-1]
        self.assertEqual((row["decision"], row["detail"]), ("passed", "1 probe(s) of fine"))


class ChangedSinceBase(Project):
    def test_paths_changed_since_the_base_inside_and_outside(self):
        put(self.root, "cb", probe_unit("cb", ["false"]))
        commit_all(self.root, "the unit")
        base = git(self.root, "rev-parse", "HEAD~1").stdout.strip()
        (self.root / "app" / "health.py").write_text("MAX_RETRIES = 3\n")
        commit_all(self.root, "work inside")
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return 0\n")   # outside, uncommitted
        (self.root / "app" / "new.py").write_text("x = 1\n")                              # outside, untracked
        d = json.loads(charter(self.root, "probe", "cb", "--json").stdout)
        self.assertEqual(d["changed"], {"base": base, "inside": ["app/health.py"], "outside": ["app/billing.py", "app/new.py"]})
        out = charter(self.root, "probe", "cb").stdout
        self.assertIn(f"changed since {base[:10]}, the unit's base: 1 path(s) inside the perimeter, 2 outside: app/billing.py, app/new.py", out)

    def test_no_perimeter_puts_every_path_inside(self):
        put(self.root, "np", probe_unit("np", ["false"]).replace("perimeter: [app/health.py, tests/**]\n", ""))
        commit_all(self.root, "the unit")
        (self.root / "app" / "billing.py").write_text("x = 2\n")
        d = json.loads(charter(self.root, "probe", "np", "--json").stdout)
        self.assertEqual((d["changed"]["inside"], d["changed"]["outside"]), (["app/billing.py"], []))


class DoneGateNamesBoxes(Project):
    def test_the_unchecked_boxes_are_named(self):
        sha = git(self.root, "rev-parse", "--short=12", "HEAD").stdout.strip()
        boxes = "- [x] AC-1: one — probe: `true`\n- [ ] AC-2: two — probe: `true`\n- [ ] the page is reviewed by the owner"
        put(self.root, "dn", unit("dn", "done", boxes=boxes, evidence=f"- {sha}"))
        git(self.root, "add", "-A")
        r = charter(self.root, "check", "--staged")
        self.assertIn("2 acceptance box(es) are unchecked: AC-2, the page is reviewed by the owner", r.stdout)
        blockers = json.loads(charter(self.root, "unit", "show", "dn", "--json").stdout)["done_blockers"]
        self.assertEqual(blockers[0], "status is done but 2 acceptance box(es) are unchecked: AC-2, the page is reviewed by the owner")


class ChainBriefingTails(ChainCase):
    def test_the_rerun_probe_carries_its_tails(self):
        self.start()
        self.join(1, "s1")
        u = self.root / ".taskets" / "u1.md"
        u.write_text(u.read_text().replace("status: next", "status: done").replace("- [ ] AC-1", "- [x] AC-1")
                     .replace("## Evidence\n", "## Evidence\n\n- `$ python3 -c ...` → exit 0\n"))
        commit_all(self.root, "u1 done")
        (self.root / "app" / "health.py").write_text("MAX_RETRIES = 4\n\n\ndef health():\n    return {'ok': True, 'retries': MAX_RETRIES}\n")
        commit_all(self.root, "a later change breaks u1")
        self.write_handoff(1, status="complete", next_unit="none", done="- u1 closed")
        chain_cli(self.root, "next", sid="s1")
        facts = (chainlib.link_dir(self.root, self.chain["id"], 1) / "facts.md").read_text()
        self.assertIn("Probes of u1, closed this session, re-run now: FAILED", facts)   # (guard)
        self.assertIn("AC-1 failed: ", facts)
        self.assertIn("| AssertionError", facts)


# ---------------------------------------------------------------- K12: perimeter fit

FA, FB, FC = "20261013-1200-fit-alpha", "20261013-1300-beta", "20261013-1300-gamma"


class PerimeterFit(Project):
    def setUp(self):
        super().setUp()
        r = self.root
        (r / "docs").mkdir()
        put(r, FA, probe_unit(FA, ["true"], perimeter="[app/health.py, tests/**, docs/**]",
                              extra="\n## Outside perimeter\n\n- app/billing.py: the invoice rounds the same way\n"))
        put(r, FB, probe_unit(FB, ["true"], perimeter="[app/health.py]"))
        put(r, FC, probe_unit(FC, ["true"], perimeter="[app/health.py]"))
        commit_all(r, "taskets: three units")
        (r / "app" / "health.py").write_text("MAX_RETRIES = 3\n# a\n")
        (r / "app" / "billing.py").write_text("def invoice(a):\n    return a  # b\n")
        commit_all(r, f"health and billing (unit {FA})")
        (r / "tests" / "test_health.py").write_text("def test_ok():\n    pass\n")
        (r / "app" / "extra.py").write_text("y = 1\n")
        commit_all(r, "a test and a helper (#4, unit 20261013-1200)")   # a short tag, unique
        (r / "README.md").write_text("ambiguous\n")
        commit_all(r, "readme (unit 20261013-1300)")                      # a short tag two units share
        (r / "app" / "extra.py").write_text("y = 2\n")
        commit_all(r, "untagged change")
        (r / "app" / "squash.py").write_text("z = 1\n")
        commit_all(r, f"squash of a group\n\n- one (unit {FA})\n- two (unit {FB})")   # the body is not read: untagged
        (r / "app" / "both.py").write_text("z = 1\n")
        commit_all(r, f"shared (unit {FA}, unit {FB})")                     # two units in a subject: counted for neither
        put(r, FC, probe_unit(FC, ["true"], perimeter="[app/health.py, .taskets/**]") + "- 2026-10-13 11:00 a log line\n")
        commit_all(r, f"log (unit {FC})")                                    # only its tasket: an exempt path

    def test_unit_show_json_has_the_fit(self):
        d = json.loads(charter(self.root, "unit", "show", FA, "--json").stdout)
        self.assertEqual(d["perimeter_fit"], {
            "commits": 2, "touched": ["app/billing.py", "app/extra.py", "app/health.py", "tests/test_health.py"],
            "outside": ["app/billing.py", "app/extra.py"], "outside_noted": ["app/billing.py"],
            "entries": ["app/health.py", "tests/**", "docs/**"], "untouched_entries": ["docs/**"]})
        nothing = json.loads(charter(self.root, "unit", "show", FB, "--json").stdout)["perimeter_fit"]
        self.assertEqual((nothing["commits"], nothing["touched"]), (0, []))   # the shared short tag is charged to neither
        tasket_only = json.loads(charter(self.root, "unit", "show", FC, "--json").stdout)["perimeter_fit"]
        # its tasket is not counted as work, but it does touch the `.taskets/**` entry
        self.assertEqual((tasket_only["commits"], tasket_only["touched"], tasket_only["untouched_entries"]), (1, [], ["app/health.py"]))

    def test_unit_show_text_has_the_fit(self):
        r = charter(self.root, "unit", "show", FA)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"{FA} — {FA} title [in-progress]", r.stdout)
        self.assertIn("perimeter fit: 2 commit(s) name this unit, 4 path(s) touched; 2 outside the perimeter "
                      "(1 noted under `## Outside perimeter`): app/billing.py, app/extra.py; 2 of 3 perimeter entries touched; "
                      "untouched: docs/**", r.stdout)

    def test_synth_has_one_line_per_unit(self):
        r = charter(self.root, "synth")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = synth_section(r.stdout, "Perimeter fit")
        self.assertTrue(rows[0].startswith("- Read from commit subjects that say `unit <id>`: 10 commit(s), 5 name no unit, 1 names an id "
                                           "two or more units share, 1 names two or more units; work under no tag or another unit's tag "
                                           "is not seen"), rows[0])
        mine = [l for l in rows if l.startswith(f"- {FA}:")]
        self.assertEqual(len(mine), 1, rows)
        self.assertIn("2 outside the perimeter (1 noted)", mine[0])
        self.assertIn("untouched: docs/**", mine[0])
        self.assertTrue(mine[0].endswith(f"(.taskets/{FA}.md)"), mine[0])
        self.assertFalse([l for l in rows if l.startswith(f"- {FB}:")])   # no commit names it: no line

    def test_the_fit_is_not_a_gate(self):
        """(guard) a unit far outside its perimeter does not change what `charter check` decides."""
        r = charter(self.root, "check", "--all", "--base", "HEAD~4")
        self.assertNotIn("perimeter fit", r.stdout)


# ---------------------------------------------------------------- K13: the session's own unit

class SessionUnit(Project):
    def show(self, sid=None, *extra):
        return charter(self.root, "unit", "show", *extra, env={"CLAUDE_CODE_SESSION_ID": sid} if sid else None)

    def test_a_session_does_not_inherit_another_sessions_choice(self):
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        self.assertEqual(self.show("sess-a").stdout.strip(), "u1")
        self.assertEqual(self.show("sess-b").stdout.strip(),
                         "no active unit (the checkout's last choice, u1, is another session's; `charter unit start <id>` to choose)")
        d = json.loads(self.show("sess-b", "--json").stdout)
        self.assertEqual((d["active"], d["source"]), (None, None))
        self.assertEqual(self.show().stdout.strip(), "u1")   # (guard) no session: the owner's terminal, CI, a plain git hook

    def test_a_choice_made_outside_any_session_is_inherited(self):
        """(guard) the owner starts a unit in a terminal; a session in the checkout works on it."""
        charter(self.root, "unit", "start", "u1")
        d = json.loads(self.show("sess-b", "--json").stdout)
        self.assertEqual((d["active"], d["source"]), ("u1", "checkout"))

    def test_a_choice_from_before_0_4_15_is_not_inherited_by_a_session(self):
        """An `active` file with no record of who chose it was written before this release; in tele-claude most were sessions'."""
        st = self.root / ".git" / "charter"
        st.mkdir(parents=True, exist_ok=True)
        (st / "active").write_text("u1\n")
        self.assertIn("another session's", self.show("sess-b").stdout)
        self.assertEqual(self.show().stdout.strip(), "u1")   # (guard)

    def test_the_hook_does_not_charge_another_sessions_unit(self):
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        p = self.root / "app" / "billing.py"
        p.write_text(p.read_text() + "# b\n")
        code, out, raw, err = run_hook(self.root, "post_tool_gate", {"session_id": "sess-b", "tool_name": "Edit",
                                                                     "tool_input": {"file_path": str(p)}})
        self.assertNotIn("perimeter of unit u1", raw)
        self.assertIn("no active unit", raw)

    def test_a_commit_from_a_session_without_a_unit(self):
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        p = self.root / "app" / "billing.py"
        p.write_text(p.read_text() + "# b\n")
        git(self.root, "add", "app/billing.py")
        r = charter(self.root, "check", "--staged", env={"CLAUDE_CODE_SESSION_ID": "sess-b"})
        self.assertNotIn("perimeter of unit u1", r.stdout)
        row = [x for x in log_rows(self.root) if x["gate"] == "perimeter"][-1]
        self.assertEqual(row.get("session"), "sess-b")   # a commit's rows say which session made them

    def test_a_path_another_session_edited_is_named_not_charged(self):
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "sess-b"})
        st = self.root / ".git" / "charter"
        (st / "session-sess-a.json").write_text(json.dumps({"edited": ["app/billing.py"], "turn_edited": []}))
        (st / "session-sess-b.json").write_text(json.dumps({"edited": ["app/health.py"], "turn_edited": []}))
        for name in ("billing.py", "health.py"):
            p = self.root / "app" / name
            p.write_text(p.read_text() + "# edit\n")
        git(self.root, "add", "app")
        r = charter(self.root, "check", "--staged", env={"CLAUDE_CODE_SESSION_ID": "sess-b"})
        self.assertNotIn("app/billing.py is outside the perimeter", r.stdout)
        self.assertIn("app/billing.py is staged, but session sess-a edited it and this session did not; "
                      "a plain `git commit` charges it to unit u1", r.stdout)
        self.assertIn("git commit -m <message> -- <your paths>", r.stdout)

    def test_unit_stop_clears_the_record_of_who_chose(self):
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        self.assertEqual((self.root / ".git" / "charter" / "active.by").read_text().strip(), "sess-a")
        charter(self.root, "unit", "stop", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        self.assertFalse((self.root / ".git" / "charter" / "active.by").exists())


if __name__ == "__main__":
    unittest.main()
