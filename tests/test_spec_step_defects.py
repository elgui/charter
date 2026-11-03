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


class ProbeWhole(Project):
    ACC = ("- [ ] AC-1: exists — probe: `test -f app/health.py`\n"
           "- [ ] AC-2: still there — probe: `test -f app/health.py` (see `app/health.py`).")

    def test_a_whole_probe_gives_no_warning(self):
        self.write(".taskets/u2.md", unit("u2", acceptance=self.ACC))
        self.assertNotIn("cut at a backtick", self.check_staged(".taskets/u2.md"))

    def test_probe_output_keeps_its_form(self):
        self.write(".taskets/u2.md", unit("u2", acceptance=self.ACC))
        git(self.root, "add", ".taskets/u2.md")
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "unit")
        r = charter(self.root, "probe", "u2")
        lines = [l for l in r.stdout.splitlines() if l.startswith("- `$ ")]
        self.assertEqual(lines, ["- `$ test -f app/health.py` → exit 0"] * 2, r.stdout + r.stderr)




if __name__ == "__main__":
    unittest.main()
