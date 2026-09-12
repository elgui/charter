"""Regression tests for the three defects the 2026-09-12 harmonization trial found in charter 0.2.0
(docs/review/2026-09-12-astra-harmonization.md, changes 1 to 3). One class per defect. Each test fails
on the package at ab0a8b1 and passes once the defect is fixed."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import run_hook, charter, git, PKG
from test_review_regressions import Base, commit_all, set_config, done_unit

sys.path.insert(0, str(PKG / ".charter"))
import lib  # noqa: E402

# A PNG header: 0x89 is not UTF-8 and NUL bytes follow. The 900 newlines make it 901 "lines" to a line
# counter, over the 800-line limit, so a size gate that counted binary content would refuse it.
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00\xff\n" * 900


def passed_cleanly(test, r):
    """The command succeeded because the gates ran, not because a crash failed open."""
    test.assertEqual(r.returncode, 0, r.stdout + r.stderr)
    test.assertNotIn("Traceback", r.stderr)
    test.assertNotIn("internal error", r.stderr)


# ---------------------------------------------------------------- defect 1

class BinaryFiles(Base):
    """Trial row 9: every commit that staged a binary file was refused with a UnicodeDecodeError."""

    def test_a_new_binary_file_commits_through_the_git_hook(self):
        (self.root / "img.png").write_bytes(PNG)
        git(self.root, "add", "img.png")
        r = git(self.root, "commit", "-q", "-m", "add a png", check=False)
        passed_cleanly(self, r)
        self.assertIn("img.png", git(self.root, "show", "--name-only", "--format=", "HEAD").stdout)

    def test_a_modified_binary_file_commits_through_the_git_hook(self):
        (self.root / "img.png").write_bytes(PNG)
        commit_all(self.root, "add a png, hook off")
        (self.root / "img.png").write_bytes(PNG + b"\x89\x00\n" * 50)
        git(self.root, "add", "img.png")
        r = git(self.root, "commit", "-q", "-m", "change the png", check=False)
        passed_cleanly(self, r)

    def test_ci_mode_passes_a_modified_binary_file(self):
        (self.root / "img.png").write_bytes(PNG)
        commit_all(self.root, "add a png")
        (self.root / "img.png").write_bytes(PNG + b"\x89\x00\n" * 50)
        commit_all(self.root, "change the png")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        passed_cleanly(self, r)
        self.assertNotIn("img.png", r.stdout)

    def test_strict_size_check_skips_tracked_binaries(self):
        (self.root / "img.png").write_bytes(PNG)
        commit_all(self.root, "add a png")
        (self.root / "README.md").write_text("scratch, touched\n")
        commit_all(self.root, "a later commit, so the base holds the png too")
        r = charter(self.root, "check", "--size", "--strict")
        passed_cleanly(self, r)
        self.assertNotIn("img.png", r.stdout)

    def test_a_check_command_that_prints_bytes_is_still_judged(self):
        d = (self.root / "charter" / "decisions" / "retry-limit.md").read_text()
        d = d.replace('check: grep -q "MAX_RETRIES = 3" app/health.py', "check: printf '\\211\\n'; exit 1")
        (self.root / "charter" / "decisions" / "retry-limit.md").write_text(d)
        r = charter(self.root, "check", "--all", "--decisions")
        self.assertNotIn("Traceback", r.stderr)
        self.assertNotIn("internal error", r.stderr)
        self.assertIn("retry-limit` is contradicted", r.stdout)

    def test_a_crashing_gate_fails_open_and_logs_an_error(self):
        (self.root / ".taskets" / "stray.md").mkdir()   # read as a tasket, it raises IsADirectoryError
        r = charter(self.root, "check", "--all")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("internal error", r.stderr)
        self.assertIn("error/error: 1", charter(self.root, "log").stdout)
        r = charter(self.root, "check", "--all", "--ci", env={"GITHUB_ACTIONS": "true"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("::warning title=charter gate error::", r.stdout)   # CI passes, so the run's summary shows it

    def test_a_config_that_is_not_json_fails_open(self):
        (self.root / "charter" / "config.json").write_text("{ not json\n")
        r = charter(self.root, "check", "--all")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("not valid JSON", r.stderr)
        self.assertIn("error/error: 1", charter(self.root, "log").stdout)


# ---------------------------------------------------------------- defect 2

def usage_line(i, model, inp, out, sidechain=False):
    o = {"type": "assistant", "requestId": f"r{i}", "message": {"id": f"m{i}", "model": model, "usage": {
        "input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}}
    if sidechain:
        o["isSidechain"] = True
    return json.dumps(o)


class SubagentUsage(Base):
    """E-17: Claude Code writes subagent transcripts to `<session id>/subagents/`, which SessionEnd never read."""

    def end_session(self, sid, main, subagents=None):
        """Claude Code's layout: `<dir>/<sid>.jsonl`, and `<dir>/<sid>/subagents/agent-<n>.jsonl` per subagent."""
        d = Path(tempfile.mkdtemp(prefix="charter-transcripts-"))
        self.extra.append(d)
        tr = d / f"{sid}.jsonl"
        tr.write_text("\n".join(main) + "\n")
        if subagents is not None:
            sub = d / sid / "subagents"
            sub.mkdir(parents=True)
            for n, lines in enumerate(subagents):
                (sub / f"agent-{n}.jsonl").write_text("\n".join(lines) + "\n")
                (sub / f"agent-{n}.meta.json").write_text('{"agentType": "Explore"}\n')
        run_hook(self.root, "session_end", {"session_id": sid, "transcript_path": str(tr), "reason": "exit"})
        return json.loads((lib.shared_state_dir(self.root) / "sessions.jsonl").read_text().splitlines()[-1])

    def test_session_end_counts_subagent_transcripts(self):
        u = self.end_session("s1", [usage_line(0, "model-a", 1000, 100)],
                             [[usage_line(1, "model-b", 500, 3, sidechain=True),    # a first content block, usage streamed so far
                               usage_line(1, "model-b", 500, 50, sidechain=True),   # the same response's last block
                               usage_line(2, "model-a", 10, 5, sidechain=True)]])["usage"]
        self.assertEqual(u["output"], 100 + 50 + 5)
        self.assertEqual(u["subagent_output"], 55)
        self.assertEqual(u["by_model"]["model-a"]["output"], 105)
        self.assertEqual(u["by_model"]["model-b"]["input"], 500)
        self.assertEqual(u["subagents"]["by_model"]["model-b"]["output"], 50)
        self.assertEqual(u["subagents"]["turns"], 2)
        self.assertTrue(u["children_included"])
        self.assertEqual(u["subagent_files"], 1)

    def test_no_subagent_directory_means_no_subagent_ran(self):
        u = self.end_session("s1", [usage_line(0, "model-a", 1000, 100)])["usage"]
        self.assertTrue(u["children_included"])
        self.assertEqual(u["subagent_files"], 0)
        self.assertEqual(u["subagent_output"], 0)

    def test_the_fold_prices_the_subagent_share_per_model(self):
        set_config(self.root, prices_usd_per_mtok={"model-a": {"input": 1, "output": 2, "cache_read": 0, "cache_write": 0},
                                                   "model-b": {"input": 10, "output": 20, "cache_read": 0, "cache_write": 0}})
        self.end_session("s1", [usage_line(0, "model-a", 1_000_000, 0)], [[usage_line(1, "model-b", 0, 1_000_000, sidechain=True)]])
        charter(self.root, "ledger", "fold")
        rec = json.loads((self.root / "charter" / "ledger.jsonl").read_text().splitlines()[-1])
        self.assertAlmostEqual(rec["est_usd"], 1 + 20)
        self.assertAlmostEqual(rec["subagent_est_usd"], 20)
        self.assertTrue(rec["usage"]["children_included"])


# ---------------------------------------------------------------- defect 3

class UnknownCost(Base):
    """package/.charter/bin/charter:345 added a session with no usage as 0 USD, and the synthesis stated no coverage."""

    def end_session(self, sid, with_transcript=True):
        payload = {"session_id": sid, "reason": "exit"}
        if with_transcript:
            tr = self.root / f"transcript-{sid}.jsonl"
            tr.write_text(usage_line(0, "model-a", 1_000_000, 0) + "\n")
            payload["transcript_path"] = str(tr)
        run_hook(self.root, "session_end", payload)
        if with_transcript:
            tr.unlink()

    def synth_cost(self):
        (self.root / ".taskets" / "u1.md").write_text(done_unit(f"- {self.sha()} app/health.py:2"))
        commit_all(self.root, "u1 accepted")
        r = charter(self.root, "synth")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)   # every line still passes the anchoring check
        return r.stdout.split("## Cost per accepted result")[1]

    def test_an_unknown_cost_is_not_added_as_zero(self):
        set_config(self.root, prices_usd_per_mtok={"model-a": {"input": 1, "output": 0, "cache_read": 0, "cache_write": 0}})
        commit_all(self.root, "prices")
        charter(self.root, "unit", "start", "u1")
        self.end_session("known")
        self.end_session("unknown", with_transcript=False)
        charter(self.root, "ledger", "fold")
        cost = self.synth_cost()
        self.assertIn("1 of 2 session(s) have a cost", cost)
        self.assertIn("lower bounds", cost)
        self.assertIn("estimated total at least 1.00 USD", cost)
        self.assertIn("at least 1.00 USD per accepted unit (incomplete)", cost)
        self.assertRegex(cost, r"- u1: 2 session\(s\), 1 without a cost, at least 1\.00 USD estimated")

    def test_a_session_folded_before_subagents_were_counted_is_a_lower_bound(self):
        old = {"ts": "2026-09-11T10:00:00+00:00", "session": "old", "unit": "u1", "source": "interactive",
               "usage": {"input": 1_000_000, "output": 0, "by_model": {"model-a": {"input": 1_000_000, "output": 0}}},
               "est_usd": 3.0, "accepted": False, "note": "folded by charter 0.2.0"}
        (self.root / "charter" / "ledger.jsonl").write_text(json.dumps(old) + "\n")
        cost = self.synth_cost()
        self.assertIn("1 of those do not record subagent usage", cost)
        self.assertIn("estimated total at least 3.00 USD", cost)

    def test_full_coverage_is_stated_and_no_human_time_is_not_zero(self):
        charter(self.root, "unit", "start", "u1")
        self.end_session("known")
        charter(self.root, "ledger", "fold")
        cost = self.synth_cost()
        self.assertIn("all 1 session(s) have a cost, subagents counted", cost)
        self.assertRegex(cost, r"- u1: 1 session\(s\), [0-9.]+ USD estimated, 0\.00 of it by subagents")
        self.assertIn("no human time recorded", cost)
        self.assertNotIn("(incomplete)", cost)
        self.assertNotIn("0 human min,", cost)


if __name__ == "__main__":
    unittest.main()
