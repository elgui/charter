"""0.4.22: the four Charter defects the spec-step trials found (docs/proposals/2026-11-spec-step.md,
§ Defects that stand on their own). Each class is named by its unit's acceptance line.

- a probe cut short at a backtick runs as a shorter command, and nothing said so;
- `charter anchors` passed over a backticked path whose directory does not exist;
- a unit past planning could rely on a decision nobody has ruled, in silence;
- the scope gate warned on perimeter entries under paths every other gate exempts.
"""
import re
import unittest

from helpers import make_project, charter, git, cleanup

PROPOSED = """---
id: open-choice
title: An open choice
status: proposed
date: 2026-11-02
owner: Test Owner
kind: design
ask: Pick one?
recommend: active
---

## Decision

One of two.

## Because

Two units could choose differently.
"""


def unit(uid, status="next", perimeter="[app/health.py]", decisions="[]", acceptance=None):
    acc = acceptance or "- [ ] AC-1: the endpoint exists — probe: `test -f app/health.py`"
    return f"""---
id: {uid}
title: Unit {uid}
status: {status}
priority: p2
scope: S1
perimeter: {perimeter}
decisions: {decisions}
kind: work
---

## Context

Test unit.

## Acceptance

{acc}

## Evidence

## Log
"""


class Project(unittest.TestCase):
    track = "client"

    def setUp(self):
        self.root = make_project(track=self.track)

    def tearDown(self):
        cleanup(self.root)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def check_staged(self, *rels):
        git(self.root, "add", *rels)
        r = charter(self.root, "check", "--staged")
        return r.stdout + r.stderr

    def check_all(self):
        r = charter(self.root, "check", "--all")
        return r.stdout + r.stderr


# ------------------------------------------------------------------ 1. a probe cut at a backtick

CUT = "- [ ] AC-2: the year is recent — probe: `test \"`date +%Y`\" -gt 2000`"


class ProbeCut(Project):
    def test_check_warns_on_a_probe_cut_at_a_backtick_and_names_the_line(self):
        self.write(".taskets/u2.md", unit("u2", acceptance="- [ ] AC-1: exists — probe: `test -f app/health.py`\n" + CUT))
        out = self.check_staged(".taskets/u2.md")
        line = next((l for l in out.splitlines() if "cut at a backtick" in l), "")
        self.assertTrue(line, out)
        self.assertIn("AC-2", line)
        self.assertIn(".taskets/u2.md", line)
        self.assertIn("warn", line.lower())

    def test_a_probe_whose_command_ends_in_a_space_before_more_code_is_cut(self):
        self.write(".taskets/u2.md", unit("u2", acceptance="- [ ] AC-1: it greps — probe: `grep -q ` app/health.py`"))
        self.assertIn("cut at a backtick", self.check_staged(".taskets/u2.md"))

    def test_a_hash_inside_a_word_does_not_hide_an_open_quote(self):
        self.write(".taskets/u2.md", unit("u2", acceptance="- [ ] AC-1: set — probe: `test -n value#\"` printf bad`\"`"))
        self.assertIn("cut at a backtick", self.check_staged(".taskets/u2.md"))

    def test_a_cut_command_substitution_is_cut(self):
        self.write(".taskets/u2.md", unit("u2", acceptance="- [ ] AC-1: empty — probe: `test -z ` printf bad``"))
        self.assertIn("cut at a backtick", self.check_staged(".taskets/u2.md"))

    def test_a_cut_that_leaves_an_open_quote_and_a_space_is_cut(self):
        self.write(".taskets/u2.md", unit("u2", acceptance="- [ ] AC-1: recent — probe: `test \"` date +%Y`\" -gt 2000`"))
        self.assertIn("cut at a backtick", self.check_staged(".taskets/u2.md"))


class ProbeWhole(Project):
    ACC = ("- [ ] AC-1: exists — probe: `test -f app/health.py`\n"
           "- [ ] AC-2: still there — probe: `test -f app/health.py` (see `app/health.py`).\n"
           "- [ ] AC-3: a stray space — probe: `test -f app/health.py ` (see `app/health.py`).\n"
           "- [ ] AC-4: a comment — probe: `test -f app/health.py # don't remove` (see `app/health.py`).\n"
           "- [ ] AC-5: a literal backtick after it — probe: `test -f app/health.py` (the delimiter is `` ` ``).\n"
           "- [ ] AC-6: a lone run in prose — probe: `test -f app/health.py` (write `` to start a span).")

    def test_a_whole_probe_gives_no_warning(self):
        self.write(".taskets/u2.md", unit("u2", acceptance=self.ACC))
        self.assertNotIn("cut at a backtick", self.check_staged(".taskets/u2.md"))

    def test_probe_output_keeps_its_form(self):
        self.write(".taskets/u2.md", unit("u2", acceptance=self.ACC))
        git(self.root, "add", ".taskets/u2.md")
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "unit")
        r = charter(self.root, "probe", "u2")
        lines = [l for l in r.stdout.splitlines() if l.startswith("- `$ ")]
        self.assertEqual(lines, ["- `$ test -f app/health.py` → exit 0"] * 3 + ["- `$ test -f app/health.py # don't remove` → exit 0"]
                         + ["- `$ test -f app/health.py` → exit 0"] * 2, r.stdout + r.stderr)


# ------------------------------------------------------------------ 2. a cited path that does not exist

DOC = "The handler is at app/health.py:5, and the study it follows is in {ref}.\n"


class MissingPath(Project):
    def test_anchors_lists_a_backticked_path_whose_directory_does_not_exist(self):
        self.write("notes.md", DOC.format(ref="`analysis/2026-11/study.md`"))
        r = charter(self.root, "anchors", "notes.md")
        line = next((l for l in r.stdout.splitlines() if "analysis/2026-11/study.md" in l), "")
        self.assertTrue(line, r.stdout + r.stderr)
        self.assertIn("L1", line)

    def test_a_missing_directory_written_with_a_trailing_slash_is_listed(self):
        self.write("notes.md", DOC.format(ref="`analysis/2026-11/`"))
        self.assertIn("analysis/2026-11/", charter(self.root, "anchors", "notes.md").stdout)

    def test_a_file_where_a_directory_should_be_is_listed(self):
        self.write("notes.md", DOC.format(ref="`README.md/child.py`"))
        self.assertIn("README.md/child.py", charter(self.root, "anchors", "notes.md").stdout)

    def test_a_missing_directory_before_dot_dot_is_listed(self):
        self.write("notes.md", DOC.format(ref="`no-such-dir/../app/health.py`"))
        self.assertIn("no-such-dir/../app/health.py", charter(self.root, "anchors", "notes.md").stdout)

    def test_a_numeric_or_dot_directory_is_still_checked(self):
        for ref in ("`no-such-dir/2026/`", "`no-such-dir/./`"):
            with self.subTest(ref=ref):
                self.write("notes.md", DOC.format(ref=ref))
                self.assertIn("missing path", charter(self.root, "anchors", "notes.md").stdout)

    def test_a_file_with_a_numeric_extension_is_a_path(self):
        self.write("notes.md", DOC.format(ref="`no-such-dir/man1/charter.1`"))
        self.assertIn("no-such-dir/man1/charter.1", charter(self.root, "anchors", "notes.md").stdout)

    def test_one_absent_tree_is_one_line_however_it_is_written(self):
        self.write("notes.md", DOC.format(ref="`analysis/a.md`") + DOC.format(ref="`./analysis/b.md`"))
        out = [l for l in charter(self.root, "anchors", "notes.md").stdout.splitlines() if "missing path" in l]
        self.assertEqual(len(out), 1, out)
        self.assertIn("1 more", out[0])


class MissingPathGuard(Project):
    def test_the_report_does_not_change_the_exit_code(self):
        self.write("ok.md", DOC.format(ref="README.md"))
        self.write("missing.md", DOC.format(ref="`analysis/2026-11/study.md`"))
        ok, missing = charter(self.root, "anchors", "ok.md"), charter(self.root, "anchors", "missing.md")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertEqual(missing.returncode, ok.returncode, missing.stdout)
        self.assertIn(": ok", missing.stdout.splitlines()[0])

    def test_prose_refs_and_existing_paths_are_not_listed(self):
        text = (DOC.format(ref="`app/health.py`") + "Use one and/or the other, from `origin/main` or `owner/repo`, by `app/*.py`.\n"
                "A new file `app/new_module.py` and a home file `~/.no-such-file-here` are not missing directories.\n"
                "Neither is a ratio, `1/2.0`, nor a branch, `release/0.4.22`.\n")
        self.write("notes.md", text)
        out = charter(self.root, "anchors", "notes.md").stdout
        self.assertNotIn("missing path", out)

    def test_a_path_inside_a_code_block_is_not_listed(self):
        self.write("notes.md", DOC.format(ref="README.md") + "\n```\ncat `analysis/2026-11/study.md`\n```\n")
        self.assertNotIn("missing path", charter(self.root, "anchors", "notes.md").stdout)


# ------------------------------------------------------------------ 3. a unit relying on a proposed decision

class ProposedDecision(Project):
    def setUp(self):
        super().setUp()
        self.write("charter/decisions/open-choice.md", PROPOSED)

    def test_check_warns_when_a_started_unit_names_a_proposed_decision(self):
        self.write(".taskets/u2.md", unit("u2", status="in-progress", decisions="[open-choice]"))
        out = self.check_all()
        line = next((l for l in out.splitlines() if "open-choice" in l and "proposed" in l), "")
        self.assertTrue(line, out)
        self.assertIn("u2", line)

    def test_unit_start_warns_when_the_unit_names_a_proposed_decision(self):
        self.write(".taskets/u2.md", unit("u2", status="now", decisions="[open-choice]"))
        r = charter(self.root, "unit", "start", "u2")
        self.assertIn("still proposed", r.stdout + r.stderr)


class ProposedDecisionGuard(Project):
    def setUp(self):
        super().setUp()
        self.write("charter/decisions/open-choice.md", PROPOSED)

    def test_a_unit_still_in_planning_is_not_warned(self):
        for status in ("next", "later"):
            with self.subTest(status=status):
                self.write(".taskets/u2.md", unit("u2", status=status, decisions="[open-choice]"))
                self.assertNotIn("still proposed", self.check_all())

    def test_a_closed_unit_is_not_warned_at_unit_start(self):
        for status in ("done", "deleted"):
            with self.subTest(status=status):
                self.write(".taskets/u2.md", unit("u2", status=status, decisions="[open-choice]"))
                r = charter(self.root, "unit", "start", "u2")
                self.assertNotIn("still proposed", r.stdout + r.stderr)

    def test_an_active_decision_is_not_warned(self):
        self.write(".taskets/u2.md", unit("u2", status="in-progress", decisions="[retry-limit]"))
        out = self.check_all()
        self.assertNotIn("still proposed", out)
        self.assertNotIn("relies on decision retry-limit", out)


# ------------------------------------------------------------------ 4. exempt paths in a perimeter

def uncovered(out, entry):
    return [l for l in out.splitlines() if f"perimeter entry {entry} is not covered" in l]


class ExemptPerimeter(Project):
    def test_an_entry_under_an_exempt_path_raises_no_coverage_warning(self):
        self.write(".taskets/u2.md", unit("u2", perimeter="[app/health.py, charter/specs/**, .taskets/**, .claude/notes.md]"))
        out = self.check_all()
        for entry in ("charter/specs/**", ".taskets/**", ".claude/notes.md"):
            with self.subTest(entry=entry):
                self.assertEqual(uncovered(out, entry), [], out)


class ExemptPerimeterGuard(Project):
    def test_an_uncovered_ordinary_path_still_warns(self):
        self.write(".taskets/u2.md", unit("u2", perimeter="[app/health.py, app/other.py]"))
        self.assertTrue(uncovered(self.check_all(), "app/other.py"))

    def test_an_out_of_scope_path_still_warns(self):
        self.write(".taskets/u2.md", unit("u2", perimeter="[app/billing.py]"))
        out = self.check_all()
        self.assertTrue(re.search(r"perimeter entry app/billing\.py falls under out-of-scope item X1", out), out)



if __name__ == "__main__":
    unittest.main()
