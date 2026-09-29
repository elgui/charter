"""0.4.7: four gates that made noise in tele-claude's first days on charter, each kept to what it
catches. Each test fails if its change is removed.

- the Stop gate warns about an anchor that does not resolve, and still blocks a claim with none;
- the size gate warns when a file crosses 80% of its limit, not on every change above it; an opt-in
  `limits.growth_slack_lines` lets a change grow a frozen file by that much; a `git mv` is not a new file;
- a `charter:<id>` marker followed by a period cites <id>;
- the active unit is the session's own; the checkout's shared choice counts only while its unit is open.
"""
import json
import unittest

from helpers import make_project, run_hook, charter, git, cleanup


def write_call(root, rel, content):
    return {"tool_name": "Write", "tool_input": {"file_path": str(root / rel), "content": content}}


def lines(n, prefix="x"):
    return "".join(f"{prefix}{i} = {i}\n" for i in range(n))


def denied(out):
    return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def commit_all(root, msg="setup"):
    git(root, "add", "-A")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", msg)


class Project(unittest.TestCase):
    track = "prototype"

    def setUp(self):
        self.root = make_project(track=self.track)

    def tearDown(self):
        cleanup(self.root)

    def set_cfg(self, fn):
        p = self.root / "charter" / "config.json"
        cfg = json.loads(p.read_text())
        fn(cfg)
        p.write_text(json.dumps(cfg))
        commit_all(self.root, "config")


class StopGateAnchors(Project):
    def stop_after_edit(self, msg):
        (self.root / "README.md").write_text("edited\n")
        run_hook(self.root, "post_tool_gate", write_call(self.root, "README.md", "edited\n"))
        return run_hook(self.root, "stop_gate", {"last_assistant_message": msg, "stop_hook_active": False})

    def test_an_anchor_in_another_repository_warns_and_does_not_block(self):
        rc, out, so, se = self.stop_after_edit("Done: the fix is in Keeper.py:253 and commit 9f8e7d6c.")
        self.assertNotEqual(out.get("decision"), "block", so + se)
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("do not resolve", ctx)
        self.assertIn("Keeper.py:253", ctx)

    def test_a_claim_with_no_anchor_at_all_still_blocks(self):
        rc, out, so, se = self.stop_after_edit("All done, it works.")
        self.assertEqual(out.get("decision"), "block", so + se)


class SizeCrossing(Project):
    def setUp(self):
        super().setUp()
        self.set_cfg(lambda c: c["limits"].update(file_lines=20))   # 80% is 16 lines
        (self.root / "app" / "big.py").write_text(lines(17))
        commit_all(self.root)

    def test_growth_above_80_percent_does_not_warn_again(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/big.py", lines(18)))
        self.assertNotIn("plan a split", so + se)

    def test_crossing_80_percent_warns(self):
        (self.root / "app" / "small.py").write_text(lines(15))
        commit_all(self.root)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/small.py", lines(17)))
        self.assertFalse(denied(out), so + se)
        self.assertIn("plan a split", so + se)


class SizeSlack(Project):
    def setUp(self):
        super().setUp()
        self.set_cfg(lambda c: c["limits"].update(file_lines=20, growth_slack_lines=5, governance_lines=5))
        (self.root / "app" / "big.py").write_text(lines(30))
        commit_all(self.root)

    def test_growth_within_the_slack_warns(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/big.py", lines(33)))
        self.assertFalse(denied(out), so + se)
        (self.root / "app" / "big.py").write_text(lines(33))
        git(self.root, "add", "app/big.py")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("growth slack", r.stdout)

    def test_growth_beyond_the_slack_blocks(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/big.py", lines(40)))
        self.assertTrue(denied(out), so + se)

    def test_without_the_key_there_is_no_slack(self):
        self.set_cfg(lambda c: c["limits"].pop("growth_slack_lines"))
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/big.py", lines(31)))
        self.assertTrue(denied(out), so + se)

    def test_a_governance_file_gets_no_slack(self):
        (self.root / "CLAUDE.md").write_text("# Rules\n" + "".join(f"- rule {i}\n" for i in range(8)))
        commit_all(self.root)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "CLAUDE.md", (self.root / "CLAUDE.md").read_text() + "- one more\n"))
        self.assertTrue(denied(out), so + se)


class SizeRename(Project):
    def setUp(self):
        super().setUp()
        self.set_cfg(lambda c: c["limits"].update(file_lines=20))
        (self.root / "app" / "old.py").write_text(lines(30))
        commit_all(self.root)

    def test_a_git_mv_is_measured_against_the_old_name(self):
        (self.root / "docs").mkdir(exist_ok=True)
        git(self.root, "mv", "app/old.py", "docs/old.py")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("frozen", r.stdout)

    def test_a_moved_file_that_grows_is_still_refused(self):
        (self.root / "docs").mkdir(exist_ok=True)
        git(self.root, "mv", "app/old.py", "docs/old.py")
        (self.root / "docs" / "old.py").write_text(lines(34))
        git(self.root, "add", "docs/old.py")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("frozen", r.stdout)


class MarkerPunctuation(Project):
    def test_a_trailing_period_is_not_part_of_the_id(self):
        p = self.root / "app" / "health.py"
        p.write_text(p.read_text() + "# The cap is decided, see charter:retry-limit.\n")
        git(self.root, "add", "app/health.py")
        r = charter(self.root, "check", "--staged")
        self.assertNotIn("retry-limit.", r.stdout)
        self.assertEqual(r.returncode, 0, r.stdout)


class ActiveUnitPerSession(Project):
    def unit_for(self, sid):
        return charter(self.root, "unit", "show", env={"CLAUDE_CODE_SESSION_ID": sid}).stdout.strip()

    def mark_done(self):
        p = self.root / ".taskets" / "u1.md"
        p.write_text(p.read_text().replace("status: next", "status: done"))

    def test_the_session_that_started_a_unit_keeps_it(self):
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        self.assertEqual(self.unit_for("sess-a"), "u1")
        self.assertEqual(self.unit_for("sess-b"), "u1")   # the checkout's choice, while u1 is open
        self.mark_done()
        self.assertEqual(self.unit_for("sess-a"), "u1")
        self.assertIn("no active unit", self.unit_for("sess-b"))

    def test_a_session_is_not_charged_to_a_closed_unit(self):
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        self.mark_done()
        run_hook(self.root, "session_end", {"session_id": "sess-b", "reason": "exit"})
        run_hook(self.root, "session_end", {"session_id": "sess-a", "reason": "exit"})
        st = git(self.root, "rev-parse", "--git-common-dir").stdout.strip()
        path = (self.root / st / "charter" / "sessions.jsonl") if not st.startswith("/") else None
        recs = {}
        for f in ([path] if path and path.exists() else list(self.root.rglob("sessions.jsonl"))):
            for line in f.read_text().splitlines():
                r = json.loads(line)
                recs[r["session"]] = r["unit"]
        self.assertEqual(recs.get("sess-b"), "", recs)
        self.assertEqual(recs.get("sess-a"), "u1", recs)
        self.assertEqual(self.unit_for("sess-a"), "no active unit (the checkout's last choice, u1, is closed)")

    def test_charter_unit_in_the_environment_still_wins(self):
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        r = charter(self.root, "unit", "show", env={"CLAUDE_CODE_SESSION_ID": "sess-a", "CHARTER_UNIT": "other"})
        self.assertEqual(r.stdout.strip(), "other")

    def test_unit_stop_clears_the_sessions_choice(self):
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        charter(self.root, "unit", "stop", env={"CLAUDE_CODE_SESSION_ID": "sess-a"})
        self.assertEqual(self.unit_for("sess-a"), "no active unit")


if __name__ == "__main__":
    unittest.main()
