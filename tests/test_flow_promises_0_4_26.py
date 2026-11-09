"""0.4.26, from the flow-promises watch (docs/briefs/2026-11-09-flow-promises-checks-world-actions-owner-lines.md).

K7: a decision's `check:` is seen failing before it goes active, and a decision whose `binds:` matches no file is reported.
K2: a unit that changes a state machine lists what the world does without the user.
K6: only the owner weakens an owner line: an acceptance change needs a dated Log line naming the criterion, a move back
into planning does not lift that, and the owner and the delegate see the old wording beside the new.
Each test fails on the package at cfa1071."""
import hashlib
import json
import re
import sys
import unittest
from unittest import mock

from helpers import make_project, run_hook, charter, git, cleanup, UNIT, PKG
from test_gates import write_call

sys.path.insert(0, str(PKG / ".charter"))
import checks  # noqa: E402
import lib  # noqa: E402
import owner  # noqa: E402


def decision(out):
    return out.get("hookSpecificOutput", {}).get("permissionDecision") or "allow"


def commit_all(root, msg):
    git(root, "add", "-A")
    return git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", msg, check=False)


OWNER_LINE = "- [ ] AC-2: every screen shows Skip — owner: check — probe: `grep -q Skip app/health.py`"
WEAKER_LINE = "- [ ] AC-2: the first screen shows Skip — owner: check — probe: `grep -q Skip app/health.py`"


def with_owner_line(status="now"):
    text = UNIT.replace("status: next", f"status: {status}")
    return text.replace("## Evidence", OWNER_LINE + "\n\n## Evidence")


def add_log(text, line):
    return text.replace("- 2026-09-11 14:00 created\n", "- 2026-09-11 14:00 created\n" + line + "\n")


VACUOUS = """---
id: agent-runtime-layering-without-herdr
title: The agent runtime layers reach tmux through one module
status: active
date: 2026-10-20
owner: Test Owner
kind: design
binds: [services/agent_io.py, services/agent_state.py, services/detect/**, services/runtime_contract.py]
check: ! grep -rlsE '"(/usr/bin/)?tmux"' services/agent_io.py services/agent_state.py services/detect services/runtime_contract.py
expires: 2027-06-01
---

## Decision

Only the runtime contract names tmux.

## Because

A layering review.

## Stops applying when

The runtime is replaced.
"""


class DecisionCheckSeenFailing(unittest.TestCase):
    """K7."""

    def test_template_and_skill_ask_for_a_check_seen_failing(self):
        for rel in ("charter/templates/decision.md", ".claude/skills/charter-decision/SKILL.md"):
            text = (PKG / rel).read_text()
            self.assertIn("seen fail", text, rel)

    def test_a_decision_whose_binds_match_no_file_is_reported(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        (root / "services").mkdir()
        (root / "services" / "relay.py").write_text("RELAY = 1\n")
        (root / "charter" / "decisions" / "agent-runtime-layering-without-herdr.md").write_text(VACUOUS)
        commit_all(root, "a decision over files that were never built")
        r = charter(root, "check", "--all")
        lines = [l for l in r.stdout.splitlines() if "matches no file" in l]
        self.assertEqual(len(lines), 1, r.stdout)
        self.assertIn("charter/decisions warn", lines[0])
        self.assertIn("agent-runtime-layering-without-herdr", lines[0])
        # the fixture's own decision binds app/health.py, which exists: nothing about it
        self.assertNotIn("retry-limit", lines[0])
        # the check passes over the missing files: the warning is the only sign
        self.assertNotIn("is contradicted", r.stdout)

    def test_staged_commits_are_not_told_about_it(self):
        root = make_project()
        self.addCleanup(cleanup, root)
        (root / "charter" / "decisions" / "agent-runtime-layering-without-herdr.md").write_text(VACUOUS)
        git(root, "add", "-A")
        r = charter(root, "check", "--staged")
        self.assertNotIn("matches no file", r.stdout)


class WhatTheWorldDoes(unittest.TestCase):
    """K2."""

    def test_unit_template_asks_for_the_world_actions(self):
        text = (PKG / "charter" / "templates" / "unit.md").read_text()
        self.assertIn("what the world does", text)
        self.assertIn("names what must keep running", text)


class OwnerLineRewording(unittest.TestCase):
    """K6, parts 1 and 2."""

    def setUp(self):
        self.root = make_project()
        self.addCleanup(cleanup, self.root)

    def test_rewording_an_owner_line_with_a_bare_log_line_is_denied(self):
        running = with_owner_line()
        (self.root / ".taskets" / "u1.md").write_text(running)
        weaker = add_log(running.replace(OWNER_LINE, WEAKER_LINE), "- x")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", weaker))
        self.assertEqual(decision(out), "deny", so + se)
        self.assertTrue(checks.check_acceptance_change(running, weaker, ".taskets/u1.md"))

    def test_a_dated_line_that_names_another_criterion_is_not_enough(self):
        running = with_owner_line()
        weaker = add_log(running.replace(OWNER_LINE, WEAKER_LINE), "- 2026-11-09 10:00 AC-1 probe tightened")
        found = checks.check_acceptance_change(running, weaker, ".taskets/u1.md")
        self.assertEqual(len(found), 1)
        self.assertIn("AC-2", found[0].message)
        # AC-2 is not AC-20
        also = add_log(running.replace(OWNER_LINE, WEAKER_LINE), "- 2026-11-09 10:00 AC-20 reworded")
        self.assertTrue(checks.check_acceptance_change(running, also, ".taskets/u1.md"))

    def test_a_dated_line_naming_the_criterion_passes(self):
        running = with_owner_line()
        (self.root / ".taskets" / "u1.md").write_text(running)
        weaker = add_log(running.replace(OWNER_LINE, WEAKER_LINE), "- 2026-11-09 10:00 AC-2 reworded: only the first screen has Skip")
        self.assertEqual(checks.check_acceptance_change(running, weaker, ".taskets/u1.md"), [])
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", weaker))
        self.assertNotEqual(decision(out), "deny", so + se)

    def test_a_line_without_an_id_is_named_by_its_text(self):
        running = UNIT.replace("status: next", "status: now").replace("## Evidence", "- [ ] retries are logged — probe: `true`\n\n## Evidence")
        changed = running.replace("retries are logged", "retries are counted")
        found = checks.check_acceptance_change(running, add_log(changed, "- 2026-11-09 10:00 changed the logging line"), ".taskets/u1.md")
        self.assertTrue(found)
        ok = add_log(changed, "- 2026-11-09 10:00 retries are logged: now counted instead")
        self.assertEqual(checks.check_acceptance_change(running, ok, ".taskets/u1.md"), [])

    def test_moving_back_to_planning_does_not_lift_the_rule(self):
        unit = self.root / ".taskets" / "u1.md"
        running = with_owner_line("now")
        unit.write_text(running)
        commit_all(self.root, "u1 starts")
        parked = running.replace("status: now", "status: next")
        unit.write_text(parked)
        git(self.root, "add", "-A")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 0, r.stdout)
        commit_all(self.root, "u1 back to next")
        reworded = parked.replace(OWNER_LINE, WEAKER_LINE)
        unit.write_text(reworded)
        git(self.root, "add", "-A")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("acceptance changed after work started", r.stdout)
        unit.write_text(parked)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", reworded))
        self.assertEqual(decision(out), "deny", so + se)

    def test_ci_reads_the_history_up_to_its_base(self):
        unit = self.root / ".taskets" / "u1.md"
        running = with_owner_line("now")
        unit.write_text(running)
        commit_all(self.root, "u1 starts")
        parked = running.replace("status: now", "status: next")
        unit.write_text(parked)
        commit_all(self.root, "u1 back to next")
        base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        unit.write_text(parked.replace(OWNER_LINE, WEAKER_LINE))
        commit_all(self.root, "u1 reworded, hooks skipped")
        r = charter(self.root, "check", "--all", "--done", "--base", base, "--no-probe")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("acceptance changed after work started", r.stdout)

    def test_a_unit_never_started_is_replanned_freely(self):
        unit = self.root / ".taskets" / "u1.md"
        planned = with_owner_line("next")
        unit.write_text(planned)
        commit_all(self.root, "u1 planned")
        unit.write_text(planned.replace(OWNER_LINE, WEAKER_LINE))
        git(self.root, "add", "-A")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 0, r.stdout)


class OldBesideNew(unittest.TestCase):
    """K6, part 3."""

    def setUp(self):
        self.root = make_project()
        self.addCleanup(cleanup, self.root)
        self.unit = self.root / ".taskets" / "u1.md"
        self.unit.write_text(with_owner_line("next"))
        commit_all(self.root, "u1 planned")
        self.started = with_owner_line("now")
        self.unit.write_text(self.started)
        commit_all(self.root, "u1 starts")

    def reword(self):
        self.unit.write_text(add_log(self.started.replace(OWNER_LINE, WEAKER_LINE), "- 2026-11-09 10:00 AC-2 reworded: one screen"))
        commit_all(self.root, "u1 AC-2 reworded")

    def owner_item(self):
        r = charter(self.root, "owner", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        items = [i for i in json.loads(r.stdout)["items"] if i["key"] == "owner-line:u1:AC-2"]
        self.assertEqual(len(items), 1, r.stdout)
        return items[0]

    def test_owner_json_shows_the_previous_wording(self):
        self.reword()
        item = self.owner_item()
        self.assertEqual(item.get("previous"), OWNER_LINE[len("- [ ] "):])
        r = charter(self.root, "owner")
        self.assertIn("was, when work started: " + OWNER_LINE[len("- [ ] "):], r.stdout)

    def test_an_unchanged_line_carries_no_previous(self):
        item = self.owner_item()
        self.assertNotIn("previous", item)

    def test_the_delegate_request_carries_the_previous_wording(self):
        self.reword()
        ticked = self.unit.read_text().replace("- [ ] AC-2", "- [x] AC-2")
        self.unit.write_text(ticked)
        git(self.root, "add", "-A")
        probes = checks.owner_line_kinds(checks.head_text(self.root, ".taskets/u1.md"), checks.staged_text(self.root, ".taskets/u1.md"))
        import delegate
        found = delegate._closed_probes(self.root, ".taskets/u1.md", probes)
        self.assertEqual(found[0].get("previous"), OWNER_LINE[len("- [ ] "):])

    def test_the_receipt_stores_the_accepted_words(self):
        cfg = lib.load_config(self.root)
        item = owner.owner_lines(self.root, "u1", lib.taskets(self.root)["u1"], owner.legacy_re(self.root, cfg))[0]
        with mock.patch.object(owner, "_commit", return_value=0) as proposed:
            owner._accept(self.root, cfg, "u1", "AC-2", item["acceptance"]["expected"], None, None, True)
        result = proposed.call_args.args[1][".taskets/u1.md"]
        digest = hashlib.sha256(OWNER_LINE.encode()).hexdigest()[:16]
        receipt = [l for l in result.splitlines() if "owner accepted AC-2" in l]
        self.assertEqual(len(receipt), 1, result)
        self.assertTrue(receipt[0].endswith(f"[words sha256:{digest}]"), receipt[0])
        # a later reword of the accepted line, even logged, is reported
        accepted = result
        reworded = add_log(accepted.replace("every screen", "the first screen"), "- 2026-11-10 10:00 AC-2 reworded")
        found = checks.check_acceptance_change(accepted, reworded, ".taskets/u1.md")
        self.assertTrue([f for f in found if "accepted" in f.message and f.level == "warn"], found)
        self.assertFalse([f for f in found if f.level == "block"], found)


if __name__ == "__main__":
    unittest.main()
