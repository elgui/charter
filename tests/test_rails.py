"""Rails: a prototype project's roadmap as its scope set (R6's counterpart when no devis exists).

`charter/rails.md` lists the road's items. Every open unit cites one with `rail:` (or with a
`roadmap:` link whose anchor names it). An unlinked open unit warns; with `rails.required` a unit
in the change set that is unlinked is refused. Adding a rail item is the recorded re-plan, and it
is the owner's act. Motivated by tcv2, where ten PRs merged in five days without the road knowing.
"""

import json
import unittest

from helpers import charter, cleanup, git, make_project, run_hook


def write_call(root, rel, content):
    return {"tool_name": "Write", "tool_input": {"file_path": str(root / rel), "content": content}}


def denied(out):
    return (out.get("hookSpecificOutput") or {}).get("permissionDecision") == "deny"

RAILS = """# Rails

The road, in order. Owner-only: adding an item is a re-plan.

| id | title | status | order |
|---|---|---|---|
| ogp-f5 | Portable decisions | next | 10 |
| gate-triage | Cut the master's per-gate cost | next | 20 |
| ogp-f4 | Durable cost | done | 5 |
"""


def unit(uid, status="next", **keys):
    fm = "".join(f"{k}: {v}\n" for k, v in keys.items())
    return (f"---\nid: {uid}\ntitle: {uid} title\nstatus: {status}\n{fm}---\n\n## Acceptance\n\n"
            f"- [ ] AC-1: it works — probe: `true`\n\n## Evidence\n\n## Log\n")


class Rails(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        (self.root / ".taskets" / "u1.md").unlink()
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-am", "no u1")

    def tearDown(self):
        cleanup(self.root)

    def owner_commit(self, msg="owner"):
        git(self.root, "add", "-A")
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", msg)

    def rails(self, text=RAILS, required=False):
        (self.root / "charter" / "rails.md").write_text(text)
        if required:
            p = self.root / "charter" / "config.json"
            cfg = json.loads(p.read_text())
            cfg["rails"] = dict(cfg.get("rails") or {}, required=True)
            p.write_text(json.dumps(cfg))
        self.owner_commit("rails")

    def write_unit(self, uid, **kw):
        (self.root / ".taskets" / f"{uid}.md").write_text(unit(uid, **kw))

    def check(self, *args):
        r = charter(self.root, "check", *args)
        return r.returncode, r.stdout

    def test_no_rails_file_means_no_rails_findings(self):
        self.write_unit("a")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("charter/rails", out)

    def test_an_unlinked_open_unit_warns(self):
        self.rails()
        self.write_unit("a")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertEqual(rc, 0, out)
        self.assertIn("charter/rails warn [.taskets/a.md]", out)
        self.assertIn("names no rail", out)

    def test_a_rail_key_links_the_unit(self):
        self.rails()
        self.write_unit("a", rail="ogp-f5")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertNotIn("[.taskets/a.md]", out)

    def test_a_roadmap_anchor_links_the_unit(self):
        """tcv2 already writes `roadmap: <doc>#<anchor>`; the anchor is read as the rail id."""
        self.rails()
        self.write_unit("a", roadmap="docs/omnigent-pivot-roadmap-2026-07-06.md#OGP-F5")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertNotIn("[.taskets/a.md]", out)

    def test_a_groups_column_puts_a_whole_group_on_a_rail(self):
        """tcv2 plans by `group:` and edits frontmatter only through its own writer, so linking a backlog
        one key at a time is not possible there. The owner can claim groups for a rail instead."""
        self.rails("| id | title | status | order | groups |\n|---|---|---|---|---|\n"
                   "| triage | Gate triage | next | 10 | tcv2-gate-triage |\n"
                   "| findings | Findings | next | 20 | tcv2-atlas-*, supervised-retro-* |\n")
        self.write_unit("a", group="tcv2-gate-triage")
        self.write_unit("b", group="supervised-retro-aug")
        self.write_unit("c", group="elsewhere")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertNotIn("[.taskets/a.md]", out)
        self.assertNotIn("[.taskets/b.md]", out)
        self.assertIn("[.taskets/c.md]", out)
        synth = charter(self.root, "synth").stdout
        self.assertIn("a (open)", synth[synth.index("- triage"):synth.index("- findings")])

    def test_an_explicit_rail_wins_over_the_group(self):
        self.rails("| id | title | status | order | groups |\n|---|---|---|---|---|\n"
                   "| triage | Gate triage | next | 10 | g1 |\n| other | Other | done | 20 | |\n")
        self.write_unit("a", group="g1", rail="other")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertIn("rail other is done", out)

    def test_an_unknown_rail_warns(self):
        self.rails()
        self.write_unit("a", rail="off-road")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertIn("unknown rail off-road", out)

    def test_a_closed_rail_warns(self):
        self.rails()
        self.write_unit("a", rail="ogp-f4")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertIn("rail ogp-f4 is done", out)

    def test_done_and_parked_units_are_not_judged(self):
        self.rails()
        self.write_unit("a", status="parked")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertNotIn("[.taskets/a.md]", out)

    def test_required_refuses_an_unlinked_unit_at_commit(self):
        self.rails(required=True)
        self.write_unit("a")
        git(self.root, "add", ".taskets/a.md")
        rc, out = self.check("--staged")
        self.assertEqual(rc, 1, out)
        self.assertIn("charter/rails block [.taskets/a.md]", out)
        self.assertIn("the owner adds a rail item first", out)

    def test_required_does_not_refuse_a_commit_that_leaves_old_units_alone(self):
        self.write_unit("old")
        self.owner_commit("an unlinked unit from before the rails")
        self.rails(required=True)
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a + 0\n")
        git(self.root, "add", "app/billing.py")
        rc, out = self.check("--staged")
        self.assertEqual(rc, 0, out)

    def test_required_accepts_a_linked_unit(self):
        self.rails(required=True)
        self.write_unit("a", rail="gate-triage")
        git(self.root, "add", ".taskets/a.md")
        rc, out = self.check("--staged")
        self.assertEqual(rc, 0, out)

    def test_a_duplicate_rail_id_warns(self):
        self.rails(RAILS + "| ogp-f5 | again | next | 30 |\n")
        rc, out = self.check("--all", "--rails")
        self.assertIn("charter/rails.md", out)
        self.assertIn("ogp-f5 twice", out)

    def test_the_rails_file_cannot_be_moved_out_of_the_owner_only_path(self):
        """A configurable path escaped both the staged view (which copies charter/ and .taskets/) and the
        owner-only list (review finding). The file is charter/rails.md, and a `rails.file` key is ignored."""
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs" / "road.md").write_text(RAILS)
        p = self.root / "charter" / "config.json"
        cfg = json.loads(p.read_text())
        cfg["rails"] = {"file": "docs/road.md", "required": True}
        p.write_text(json.dumps(cfg))
        self.owner_commit("a rails file outside charter/")
        self.write_unit("a")
        self.owner_commit()
        rc, out = self.check("--all", "--rails")
        self.assertEqual(rc, 0, out)            # no charter/rails.md: the gate is off, not moved
        self.assertNotIn("docs/road.md", out)
        self.assertNotIn("charter/rails", out)

    def test_an_agent_edit_of_the_rails_file_is_refused(self):
        self.rails()
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/rails.md", RAILS + "| mine | x | next | 1 |\n"))
        self.assertTrue(denied(out), so + se)

    def test_synth_renders_the_rails_in_order_with_their_units(self):
        self.rails()
        self.write_unit("a", rail="gate-triage")
        self.write_unit("b", rail="ogp-f5")
        self.write_unit("c")
        self.owner_commit()
        r = charter(self.root, "synth")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = r.stdout
        self.assertIn("## Rails", out)
        i5, i4, it = out.index("- ogp-f4"), out.index("- ogp-f5"), out.index("- gate-triage")
        self.assertLess(i5, i4)
        self.assertLess(i4, it)
        self.assertIn("b (open)", out[i4:it])
        self.assertIn("## Off the rails", out)
        self.assertIn("- c —", out[out.index("## Off the rails"):])


if __name__ == "__main__":
    unittest.main()
