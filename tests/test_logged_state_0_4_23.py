"""Charter 0.4.23: a unit with Log entries but no `status: in-progress` is `logged`, not `in-progress`. A log is a
description of work, never a start record. `logged` ranks between in-progress and open in `charter next`, shows in
`next --json` as `state`, and has its own heading in the synthesis. Tests that fail on 0.4.22 are the ones that
look for `logged`; the guards pin behaviour that must not change."""
import json
import unittest

from helpers import charter, cleanup, make_project
from test_next_0_4_4 import RAILS, commit_all, put, section, synth_section, unit

LOG = "- 2026-11-05 prepared evidence, not a start"


class LoggedState(unittest.TestCase):
    def setUp(self):
        self.root = make_project()
        self.addCleanup(cleanup, self.root)
        (self.root / ".taskets" / "u1.md").unlink()
        (self.root / "charter" / "rails.md").write_text(RAILS)
        put(self.root, "explicit", unit("explicit", "in-progress", rail="r2"))
        put(self.root, "logged", unit("logged", "next", log=LOG, rail="r2"))
        put(self.root, "plain", unit("plain", "next", rail="r2"))
        put(self.root, "blocked", unit("blocked", "blocked", log=LOG, rail="r2"))
        commit_all(self.root, "units")

    def run_ok(self, *args):
        r = charter(self.root, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_state_by_status_and_log(self):
        data = json.loads(self.run_ok("next", "--json"))
        states = {u["id"]: u["state"] for r in data["rails"] for u in r["units"]}
        self.assertEqual({k: states[k] for k in ("explicit", "logged", "plain", "blocked")},
                         {"explicit": "in-progress", "logged": "logged", "plain": "open", "blocked": "blocked"})

    def test_next_order_is_explicit_logged_open_blocked(self):
        ahead = section(self.run_ok("next", "--limit", "10"), "Next on the road:")
        self.assertEqual([l.split(" ")[1] for l in ahead][:3], ["explicit", "logged", "plain"])

    def test_road_counts_use_the_new_word(self):
        road = section(self.run_ok("next"), "Road (charter/rails.md):")
        line = next(l for l in road if l.startswith("- r2 "))
        for part in ("1 in-progress", "1 logged", "1 open", "1 blocked"):
            self.assertIn(part, line)

    def test_synth_headings(self):
        out = self.run_ok("synth")
        ids = lambda t: [l.split(" ")[1] for l in synth_section(out, t) if l.startswith("- ")]
        self.assertEqual(ids("In progress"), ["explicit"])
        self.assertEqual(ids("Logged (progress not asserted)"), ["logged"])
        self.assertEqual(ids("Open, not started"), ["plain"])

    def test_json_keys_unchanged(self):
        """Guard: only the value of `state` gains a word; no key is added or removed."""
        data = json.loads(self.run_ok("next", "--json"))
        self.assertEqual(data["schema"], 1)
        row = next(u for r in data["rails"] for u in r["units"] if u["id"] == "logged")
        self.assertEqual(set(row), {"id", "title", "status", "path", "group", "order", "state", "boxes"})


if __name__ == "__main__":
    unittest.main()
