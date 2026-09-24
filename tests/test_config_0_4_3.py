"""Charter 0.4.3, from the outside review of 2026-09-24: a misspelled key, a value of the wrong type or an
unknown track in charter/config.json switched a gate off in silence (`config_from` merged any key), the
installer's default track contradicted the survey's, and the in-session hooks did not see NotebookEdit.
Every test here fails on 0.4.2 except `test_a_notebook_in_scope_is_allowed`, which guards the behaviour kept."""
import json
import sys
import unittest

from helpers import PKG, charter, cleanup, git, make_project, run_hook
from test_migration import pkg
from test_review_regressions import commit_all, decision, set_config

sys.path.insert(0, str(PKG / ".charter"))
import lib  # noqa: E402


class ConfigFrom(unittest.TestCase):
    def problems(self, user):
        return lib.config_from(user)[lib.PROBLEMS]

    def test_the_shipped_config_has_no_problem(self):
        self.assertEqual(self.problems(json.loads((PKG / "charter" / "config.json").read_text())), [])

    def test_a_misspelled_section_key_is_a_problem_with_a_suggestion(self):
        cfg = lib.config_from({"rails": {"requird": True}})
        self.assertFalse(cfg["rails"]["required"])
        self.assertIn("unknown key `rails.requird` (did you mean `required`?); ignored", cfg[lib.PROBLEMS])

    def test_a_misspelled_top_level_key_is_a_problem(self):
        self.assertIn("unknown key `reveiw` (did you mean `review`?); ignored", self.problems({"reveiw": {"required": True}}))

    def test_an_unknown_track_is_read_as_client(self):
        cfg = lib.config_from({"track": "prototpe"})
        self.assertEqual(cfg["track"], "client")   # the stricter track: the scope gate stays on
        self.assertTrue(any("`track` is \"prototpe\"" in p and "did you mean `prototype`" in p for p in cfg[lib.PROBLEMS]))

    def test_a_string_where_a_boolean_goes_is_a_problem(self):
        cfg = lib.config_from({"review": {"required": "true"}})
        self.assertFalse(cfg["review"]["required"])
        self.assertEqual(len(cfg[lib.PROBLEMS]), 1)

    def test_a_boolean_is_not_a_limit(self):
        self.assertEqual(len(self.problems({"limits": {"file_lines": True}})), 1)

    def test_price_rows_and_the_flat_0_1_0_form_are_accepted(self):
        self.assertEqual(self.problems({"prices_usd_per_mtok": {"claude-x": {"input": 1, "output": 2.5}}}), [])
        self.assertEqual(self.problems({"prices_usd_per_mtok": {"input": 1, "output": 2}}), [])
        self.assertEqual(len(self.problems({"prices_usd_per_mtok": {"claude-x": {"inptu": 1}}})), 1)

    def test_opt_ins_are_listed(self):
        self.assertEqual(lib.config_line(lib.config_from({})), "track client, opt-ins: none")
        cfg = lib.config_from({"track": "prototype", "review": {"required": True}, "probes": {"at_commit": True}})
        self.assertEqual(lib.config_line(cfg), "track prototype, opt-ins: probes.at_commit, review.required")


class ConfigAtCommit(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def test_a_staged_typo_refuses_the_commit(self):
        set_config(self.root, rails={"requird": True})
        git(self.root, "add", "charter/config.json")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("charter/config block [charter/config.json]", r.stdout)
        self.assertIn("rails.requird", r.stdout)

    def test_the_check_line_names_the_track_and_the_opt_ins(self):
        set_config(self.root, review={"required": True})
        commit_all(self.root, "review required")
        r = charter(self.root, "check", "--all")
        self.assertIn("track client, opt-ins: review.required]", r.stdout)

    def test_charter_config_prints_what_is_read(self):
        r = charter(self.root, "config")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "track client, opt-ins: none"))
        set_config(self.root, track="clinet")
        r = charter(self.root, "config")
        self.assertEqual(r.returncode, 1)
        self.assertIn("problem: charter/config.json: `track` is \"clinet\"", r.stdout)

    def test_the_session_banner_shows_opt_ins_and_problems(self):
        set_config(self.root, reveiw={"required": True})
        rc, _, so, se = run_hook(self.root, "session_start", {})
        self.assertEqual(rc, 0, se)
        self.assertIn("track client, opt-ins: none", so)
        self.assertIn("unknown key `reveiw`", so)
        self.assertIn("Commits and CI are refused", so)


class TrackIsExplicit(unittest.TestCase):
    def setUp(self):
        self.root = make_project(with_charter=False)

    def tearDown(self):
        cleanup(self.root)

    def test_a_first_install_without_track_is_refused(self):
        r = pkg("install", str(self.root))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("--track", r.stdout)
        self.assertFalse((self.root / "charter").exists())
        self.assertFalse((self.root / ".charter").exists())
        self.assertEqual(git(self.root, "status", "--porcelain").stdout, "")

    def test_a_survey_without_track_is_refused(self):
        r = pkg("survey", str(self.root), "--offline", "--no-rehearse")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--track", r.stderr)

    def test_a_reinstall_with_another_track_says_it_is_not_applied(self):
        self.assertEqual(pkg("install", str(self.root), "--track", "prototype").returncode, 0)
        r = pkg("install", str(self.root), "--track", "client")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("NOTE --track client not applied", r.stdout)
        self.assertEqual(json.loads((self.root / "charter" / "config.json").read_text())["track"], "prototype")
        self.assertEqual(pkg("install", str(self.root)).returncode, 0)   # a reinstall needs no --track


class NotebookEdit(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def call(self, rel):
        return {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": str(self.root / rel), "new_source": "x = 1", "cell_id": "a"}}

    def test_the_matcher_includes_it(self):
        s = json.loads((PKG / ".claude" / "settings.json").read_text())
        for event in ("PreToolUse", "PostToolUse"):
            self.assertIn("NotebookEdit", s["hooks"][event][0]["matcher"].split("|"))

    def test_a_notebook_under_an_owner_only_path_is_refused(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", self.call(".charter/scratch.ipynb"))
        self.assertEqual(decision(out), "deny", so + se)

    def test_a_notebook_out_of_scope_is_refused(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", self.call("app/billing/model.ipynb"))
        self.assertEqual(decision(out), "deny", so + se)
        self.assertIn("charter/scope", so)

    def test_a_notebook_in_scope_is_allowed(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", self.call("tests/explore.ipynb"))
        self.assertNotEqual(decision(out), "deny", so + se)


if __name__ == "__main__":
    unittest.main()
