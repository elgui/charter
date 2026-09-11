"""Gate behaviour: given this hook input, expect this decision.
Each test fails if the corresponding gate is removed."""
import json
import unittest
from pathlib import Path

from helpers import make_project, run_hook, charter, git, cleanup, UNIT


def write_call(root, rel, content):
    return {"tool_name": "Write", "tool_input": {"file_path": str(root / rel), "content": content}}


def edit_call(root, rel, old, new):
    return {"tool_name": "Edit", "tool_input": {"file_path": str(root / rel), "old_string": old, "new_string": new}}


class ScopeGate(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def test_out_of_scope_write_is_denied(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/billing.py", "def invoice(a):\n    return a * 2\n"))
        self.assertEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)
        self.assertIn("X1", out["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIn("charter/changes", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_in_scope_write_is_allowed(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", '"""Health. charter:retry-limit"""\nMAX_RETRIES = 3\n'))
        self.assertNotEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)

    def test_approved_change_request_unlocks_the_path(self):
        (self.root / "charter" / "changes" / "invoicing-lite.md").write_text(
            "---\nid: invoicing-lite\ntitle: Light invoicing\nstatus: approved\npaths: [app/billing.py]\napproved_by: Test Owner\napproved_on: 2026-09-11\n---\n\n## What is asked\n\nA stub.\n")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/billing.py", "def invoice(a):\n    return a * 2\n"))
        self.assertNotEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)

    def test_prototype_track_has_no_scope_gate(self):
        cfg = json.loads((self.root / "charter" / "config.json").read_text())
        cfg["track"] = "prototype"
        (self.root / "charter" / "config.json").write_text(json.dumps(cfg))
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/billing.py", "x = 1\n"))
        self.assertNotEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)

    def test_precommit_refuses_out_of_scope_staged_file(self):
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a * 3\n")
        git(self.root, "add", "app/billing.py")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("charter/scope block", r.stdout)


class SizeGate(unittest.TestCase):
    def setUp(self):
        self.root = make_project()
        cfg = json.loads((self.root / "charter" / "config.json").read_text())
        cfg["limits"]["file_lines"] = 20
        (self.root / "charter" / "config.json").write_text(json.dumps(cfg))

    def tearDown(self):
        cleanup(self.root)

    def test_growing_past_limit_is_denied(self):
        big = "\n".join(f"x{i} = {i}" for i in range(25)) + "\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", big))
        self.assertEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)
        self.assertIn("frozen", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_shrinking_an_oversized_file_is_allowed(self):
        big = "\n".join(f"x{i} = {i}" for i in range(30)) + "\n"
        (self.root / "app" / "health.py").write_text(big)
        smaller = "\n".join(f"x{i} = {i}" for i in range(25)) + "\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", smaller))
        self.assertNotEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)

    def test_open_split_unit_unfreezes(self):
        (self.root / ".taskets" / "split1.md").write_text("---\nid: split1\ntitle: split health\nstatus: now\nkind: split\nperimeter: [app/health.py]\n---\n")
        big = "\n".join(f"x{i} = {i}" for i in range(25)) + "\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", big))
        self.assertNotEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)

    def test_json_files_are_exempt(self):
        big = "[\n" + ",\n".join("1" for _ in range(40)) + "\n]\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "data.json", big))
        self.assertNotEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)


class DoneGate(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def test_done_without_checked_boxes_is_denied(self):
        text = UNIT.replace("status: next", "status: done")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", text))
        self.assertEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)
        self.assertIn("unchecked", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_done_with_boxes_but_no_evidence_is_denied(self):
        text = UNIT.replace("status: next", "status: done").replace("- [ ] AC-1", "- [x] AC-1")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", edit_call(self.root, ".taskets/u1.md", "status: next", "status: done"))
        # Edit path: only the status changes, boxes stay unchecked -> denied
        self.assertEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", text))
        self.assertEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)
        self.assertIn("Evidence", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_done_with_resolving_evidence_is_allowed(self):
        sha = git(self.root, "rev-parse", "--short", "HEAD").stdout.strip()
        text = (UNIT.replace("status: next", "status: done").replace("- [ ] AC-1", "- [x] AC-1")
                .replace("## Evidence\n", f"## Evidence\n\n- {sha} app/health.py:2\n- `$ python3 -c ...` → ok\n"))
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", text))
        self.assertNotEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)

    def test_done_with_bogus_sha_is_denied(self):
        text = (UNIT.replace("status: next", "status: done").replace("- [ ] AC-1", "- [x] AC-1")
                .replace("## Evidence\n", "## Evidence\n\n- deadbeef1234 did it\n"))
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", text))
        self.assertEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)
        self.assertIn("do not resolve", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_precommit_refuses_done_flip_without_evidence(self):
        (self.root / ".taskets" / "u1.md").write_text(UNIT.replace("status: next", "status: done"))
        git(self.root, "add", ".taskets/u1.md")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("charter/done block", r.stdout)


class DecisionGate(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def test_citing_a_retired_decision_is_denied(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", '"""charter:old-cache"""\nMAX_RETRIES = 3\n'))
        self.assertEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)
        self.assertIn("retired", out["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIn("retry-limit", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_bound_file_without_marker_warns_but_allows(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", "MAX_RETRIES = 3\n"))
        self.assertNotEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", so + se)
        self.assertIn("charter:retry-limit", out.get("hookSpecificOutput", {}).get("additionalContext", ""))

    def test_contradicting_a_decision_check_fails_precommit(self):
        (self.root / "app" / "health.py").write_text('"""charter:retry-limit"""\nMAX_RETRIES = 10\n')
        git(self.root, "add", "app/health.py")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("contradicted", r.stdout)

    def test_contradiction_is_reported_after_the_edit(self):
        (self.root / "app" / "health.py").write_text('"""charter:retry-limit"""\nMAX_RETRIES = 10\n')
        rc, out, so, se = run_hook(self.root, "post_tool_gate", write_call(self.root, "app/health.py", "irrelevant"))
        self.assertEqual(rc, 2, so + se)
        self.assertIn("contradicted", se)


class PerimeterGate(unittest.TestCase):
    def setUp(self):
        self.root = make_project()
        charter(self.root, "unit", "start", "u1")

    def tearDown(self):
        cleanup(self.root)

    def test_edit_outside_perimeter_warns_in_session(self):
        rc, out, so, se = run_hook(self.root, "post_tool_gate", write_call(self.root, "README.md", "x"))
        self.assertEqual(rc, 0, se)
        self.assertIn("outside the perimeter", out.get("hookSpecificOutput", {}).get("additionalContext", ""))

    def test_commit_outside_perimeter_without_note_is_refused(self):
        (self.root / "README.md").write_text("changed\n")
        git(self.root, "add", "README.md")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("charter/perimeter block", r.stdout)

    def test_commit_outside_perimeter_with_note_passes(self):
        (self.root / "README.md").write_text("changed\n")
        (self.root / ".taskets" / "u1.md").write_text(UNIT + "\n## Outside perimeter\n\n- README.md: documented the retry count\n")
        git(self.root, "add", "README.md", ".taskets/u1.md")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 0, r.stdout)


class StopGate(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def test_done_claim_without_evidence_is_blocked_once(self):
        rc, out, so, se = run_hook(self.root, "stop_gate", {"last_assistant_message": "All done, the feature is implemented and tests pass.", "stop_hook_active": False})
        self.assertEqual(out.get("decision"), "block", so + se)
        rc, out, so, se = run_hook(self.root, "stop_gate", {"last_assistant_message": "All done, the feature is implemented and tests pass.", "stop_hook_active": True})
        self.assertNotEqual(out.get("decision"), "block", "second attempt must pass through")

    def test_done_claim_with_evidence_passes(self):
        sha = git(self.root, "rev-parse", "--short", "HEAD").stdout.strip()
        rc, out, so, se = run_hook(self.root, "stop_gate", {"last_assistant_message": f"Done: {sha} adds it, see app/health.py:2; `$ python3 -m pytest -q` → 1 passed", "stop_hook_active": False})
        self.assertNotEqual(out.get("decision"), "block", so + se)

    def test_admitting_not_done_passes(self):
        rc, out, so, se = run_hook(self.root, "stop_gate", {"last_assistant_message": "Not done: the probe did not run because pytest is missing.", "stop_hook_active": False})
        self.assertNotEqual(out.get("decision"), "block", so + se)


class Anchors(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def test_unanchored_claim_fails_and_anchored_passes(self):
        sha = git(self.root, "rev-parse", "--short", "HEAD").stdout.strip()
        bad = self.root / "bad.md"
        bad.write_text("# Report\n\nThe health endpoint was rewritten and now handles 3 retries per call.\n")
        good = self.root / "good.md"
        good.write_text(f"# Report\n\nThe health endpoint returns the retry count (app/health.py:2, commit {sha}).\n\nThe client asked for 5 retries (unverified).\n")
        r = charter(self.root, "anchors", str(bad))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("1 unanchored", r.stdout)
        r = charter(self.root, "anchors", str(good))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("1 admitted", r.stdout)

    def test_unresolved_anchor_fails(self):
        doc = self.root / "doc.md"
        doc.write_text("# R\n\nThe endpoint lives at app/health.py:999 and was added in commit abcdef1234.\n")
        r = charter(self.root, "anchors", str(doc))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("unresolved", r.stdout)

    def test_opinion_section_is_exempt(self):
        doc = self.root / "doc.md"
        doc.write_text("# R\n\n<!-- charter: opinion -->\nI recommend rewriting the endpoint because it would be nicer and faster.\n<!-- charter: /opinion -->\n")
        r = charter(self.root, "anchors", str(doc))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_synth_passes_its_own_check(self):
        r = charter(self.root, "synth", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.root / "charter" / "progress.md").exists())
        r2 = charter(self.root, "anchors", str(self.root / "charter" / "progress.md"))
        self.assertEqual(r2.returncode, 0, r2.stdout)


class SessionHooks(unittest.TestCase):
    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def test_session_start_prints_index(self):
        charter(self.root, "unit", "start", "u1")
        rc, out, so, se = run_hook(self.root, "session_start", {"source": "startup"})
        self.assertIn("Active unit u1", so)
        self.assertIn("retry-limit", so)
        self.assertIn("1/1 acceptance criteria open", so)

    def test_session_end_records_usage(self):
        tr = self.root / "transcript.jsonl"
        lines = [json.dumps({"type": "assistant", "requestId": "r1", "message": {"id": "m1", "model": "sonnet", "usage": {"input_tokens": 10, "output_tokens": 20, "cache_read_input_tokens": 5, "cache_creation_input_tokens": 1}}}),
                 json.dumps({"type": "assistant", "requestId": "r1", "message": {"id": "m1", "model": "sonnet", "usage": {"input_tokens": 10, "output_tokens": 20, "cache_read_input_tokens": 5, "cache_creation_input_tokens": 1}}}),
                 json.dumps({"type": "user", "message": {}})]
        tr.write_text("\n".join(lines) + "\n")
        rc, out, so, se = run_hook(self.root, "session_end", {"transcript_path": str(tr), "reason": "exit"})
        rec = json.loads((self.root / ".charter" / "state" / "sessions.jsonl").read_text().splitlines()[-1])
        self.assertEqual(rec["usage"]["output"], 20, "duplicate message ids must be counted once")
        self.assertEqual(rec["usage"]["turns"], 1)
        r = charter(self.root, "ledger", "fold")
        self.assertIn("folded 1", r.stdout)
        led = json.loads((self.root / "charter" / "ledger.jsonl").read_text().splitlines()[-1])
        self.assertIsNotNone(led["est_usd"])


if __name__ == "__main__":
    unittest.main()
