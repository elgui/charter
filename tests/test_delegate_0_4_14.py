"""Charter 0.4.14: the owner's delegate (docs/design/owner-delegate.md). The owner asked on 2026-10-12 to stop being
handed basic owner commits and merges, and ruled on 2026-10-13 (Crossroads owner-delegate-levels-20261013): strict by
default, three levels below it that only the owner sets, the level read from the config committed on the default
branch, a watcher outside Claude Code that commits what the level delegates. These tests cover the package's half;
test_delegate_watcher covers the watcher."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import INSTALLER, PKG, charter, cleanup, clean_env, git, make_project, run_hook

sys.path.insert(0, str(PKG / ".charter"))
import checks  # noqa: E402
import lib  # noqa: E402

UNIT2 = """---
id: u2
title: Rows arrive
status: in-progress
scope: S1
perimeter: [app/health.py]
kind: work
---

## Acceptance

- [ ] AC-1: rows arrive — owner: check — probe: `true`
- [ ] AC-2: deployed — owner: do
- [ ] AC-3: the name is right — owner: decide

## Evidence

## Log

- 2026-10-13 10:00 created
"""

PROPOSED = """---
id: cache-ttl
title: Cache entries live one hour
status: proposed
date: 2026-10-13
owner: Test Owner
kind: design
---

## Decision

One hour.

## Because

Measured.

## Stops applying when

Never.
"""


def owner_commit(root, msg="owner"):
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", msg)


def set_config(root, **updates):
    """The owner's committed config change, as a test fixture (the hook is bypassed: the owner made it)."""
    p = root / "charter" / "config.json"
    obj = json.loads(p.read_text())
    obj.update(updates)
    p.write_text(json.dumps(obj, indent=2) + "\n")
    git(root, "add", "charter/config.json")
    if git(root, "diff", "--cached", "--quiet", "--", "charter/config.json", check=False).returncode:
        git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", f"config {updates}", "--", "charter/config.json")


def level_of(root):
    r = charter(root, "delegate", "level")
    return r.stdout.split()[1] if r.returncode == 0 else r.stderr


def tick(text, key):
    return text.replace(f"- [ ] {key}:", f"- [x] {key}:", 1)


def denied(out):
    h = out.get("hookSpecificOutput") or {}
    return h.get("permissionDecisionReason", "") if h.get("permissionDecision") == "deny" else ""


class Base(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        (self.root / ".taskets" / "u2.md").write_text(UNIT2)
        (self.root / "charter" / "decisions" / "cache-ttl.md").write_text(PROPOSED)
        git(self.root, "add", "-A")
        owner_commit(self.root, "u2 and a proposal")

    def tearDown(self):
        cleanup(self.root)

    def u2(self):
        return (self.root / ".taskets" / "u2.md").read_text()

    def close_check(self):
        (self.root / ".taskets" / "u2.md").write_text(tick(self.u2(), "AC-1"))
        git(self.root, "add", ".taskets/u2.md")

    def head(self):
        return git(self.root, "rev-parse", "HEAD").stdout.strip()


class Levels(Base):
    def test_no_key_on_main_is_strict(self):
        self.assertEqual(level_of(self.root), "strict")

    def test_the_level_is_read_from_main_never_the_tree(self):
        p = self.root / "charter" / "config.json"
        obj = json.loads(p.read_text())
        obj["delegate"] = {"level": "open"}
        p.write_text(json.dumps(obj))   # uncommitted: an agent's, or anyone's, working tree
        self.assertEqual(level_of(self.root), "strict")
        git(self.root, "add", "charter/config.json")   # staged is not committed either
        self.assertEqual(level_of(self.root), "strict")

    def test_a_branch_without_the_key_inherits_main(self):
        git(self.root, "switch", "-q", "-c", "feature")
        git(self.root, "switch", "-q", "main")
        set_config(self.root, delegate={"level": "open"})
        git(self.root, "switch", "-q", "feature")   # made before the owner set the level
        self.assertEqual(level_of(self.root), "open")

    def test_a_branch_naming_a_stricter_level_narrows_it(self):
        set_config(self.root, delegate={"level": "open"})
        git(self.root, "switch", "-q", "-c", "feature")
        set_config(self.root, delegate={"level": "routine"})
        self.assertEqual(level_of(self.root), "routine")

    def test_a_branch_naming_a_looser_level_cannot_widen_it(self):
        set_config(self.root, delegate={"level": "routine"})
        git(self.root, "switch", "-q", "-c", "feature")
        set_config(self.root, delegate={"level": "open"})
        self.assertEqual(level_of(self.root), "routine")

    def test_an_unknown_level_fails_closed_with_a_problem(self):
        set_config(self.root, delegate={"level": "loose"})
        r = charter(self.root, "delegate", "level")
        self.assertIn("level strict", r.stdout)
        self.assertIn("not one of strict, routine, answers, open", r.stdout)
        self.assertIn("read as strict", " ".join(lib.config_from({"delegate": {"level": "loose"}})[lib.PROBLEMS]))

    def test_the_default_branch_is_master_where_there_is_no_main(self):
        git(self.root, "branch", "-m", "main", "master")
        set_config(self.root, delegate={"level": "answers"})
        self.assertEqual(lib.default_branch(self.root), "master")
        self.assertEqual(level_of(self.root), "answers")

    def test_the_seeded_config_names_no_level(self):
        # an explicit strict on every branch would narrow each of them below the level the owner later sets on main
        self.assertNotIn("delegate", json.loads((PKG / "charter" / "config.json").read_text()))


class Kinds(unittest.TestCase):
    def test_ticking_an_owner_check_line_unchanged_is_owner_check(self):
        self.assertEqual(checks.owner_act_kinds(".taskets/u2.md", UNIT2, tick(UNIT2, "AC-1")), ["owner-check"])

    def test_ticking_a_do_or_decide_line_is_structural(self):
        self.assertEqual(checks.owner_act_kinds(".taskets/u2.md", UNIT2, tick(UNIT2, "AC-2")), ["structural"])
        self.assertEqual(checks.owner_act_kinds(".taskets/u2.md", UNIT2, tick(UNIT2, "AC-3")), ["structural"])

    def test_rewording_or_removing_an_owner_line_is_structural(self):
        reworded = tick(UNIT2, "AC-1").replace("rows arrive", "some rows arrive")
        self.assertEqual(checks.owner_act_kinds(".taskets/u2.md", UNIT2, reworded), ["structural"])
        removed = UNIT2.replace("- [ ] AC-1: rows arrive — owner: check — probe: `true`\n", "")
        self.assertEqual(checks.owner_act_kinds(".taskets/u2.md", UNIT2, removed), ["structural"])
        reprobed = tick(UNIT2, "AC-1").replace("probe: `true`", "probe: `echo ok`")
        self.assertEqual(checks.owner_act_kinds(".taskets/u2.md", UNIT2, reprobed), ["structural"])

    def test_an_installer_exact_settings_change_is_an_upgrade(self):
        frag = json.loads((PKG / ".charter" / "settings-fragment.json").read_text())
        old = json.dumps({"permissions": {"allow": ["Bash(ls)"]}, "hooks": {}})
        new = json.dumps(lib.merge_settings(json.loads(old), frag))
        self.assertEqual(checks.owner_act_kinds(".claude/settings.json", old, new, fragment=frag), ["upgrade"])

    def test_any_other_settings_change_is_structural(self):
        frag = json.loads((PKG / ".charter" / "settings-fragment.json").read_text())
        old = json.dumps({"hooks": {}})
        merged = lib.merge_settings(json.loads(old), frag)
        merged["permissions"] = {"allow": ["Bash"]}
        self.assertEqual(checks.owner_act_kinds(".claude/settings.json", old, json.dumps(merged), fragment=frag), ["structural"])
        self.assertEqual(checks.owner_act_kinds(".claude/settings.json", old, json.dumps(lib.merge_settings({}, frag))), ["structural"])  # no fragment

    def test_rails_scope_and_config(self):
        self.assertEqual(checks.owner_act_kinds("charter/rails.md", "a\n", "b\n"), ["rails"])
        self.assertEqual(checks.owner_act_kinds("charter/scope.md", "a\n", "b\n"), ["scope"])
        self.assertEqual(checks.owner_act_kinds("charter/config.json", "{}", '{"delegate": {"level": "open"}}'), ["structural"])
        self.assertEqual(checks.owner_act_kinds(".charter/lib.py", "a", "b"), ["structural"])

    def test_what_each_level_delegates(self):
        self.assertFalse(lib.delegable({"owner-check"}, "strict"))
        self.assertTrue(lib.delegable({"owner-check", "upgrade"}, "routine"))
        self.assertFalse(lib.delegable({"ruling"}, "routine"))
        self.assertTrue(lib.delegable({"ruling"}, "answers"))
        self.assertFalse(lib.delegable({"rails"}, "answers"))
        self.assertFalse(lib.delegable({"merge"}, "answers"))
        self.assertTrue(lib.delegable({"rails", "scope", "merge", "ruling"}, "open"))
        self.assertFalse(lib.delegable({"owner-check", "structural"}, "open"))


class Handover(Base):
    def test_a_delegable_handover_records_its_kinds_and_keeps_the_owner_line_last(self):
        set_config(self.root, delegate={"level": "routine"})
        self.close_check()
        r = charter(self.root, "handover", "-m", "close u2 AC-1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Handed to the owner's delegate (level routine, from main)", r.stdout)
        self.assertIn("kinds of owner act: owner-check (1)", r.stdout)
        self.assertTrue(r.stdout.strip().splitlines()[-1].startswith("CHARTER_OWNER=1 python3 "))
        rec = lib.load_handover(self.root)
        self.assertEqual((rec["level"], rec["delegable"], rec["kinds"]), ("routine", True, {".taskets/u2.md": ["owner-check"]}))
        self.assertRegex(rec["id"], r"^h[0-9a-f]{12}$")

    def test_at_strict_the_block_is_unchanged(self):
        self.close_check()
        r = charter(self.root, "handover")
        self.assertIn("Waiting on the owner: commit 1 staged file(s)", r.stdout)
        self.assertNotIn("kinds of owner act", r.stdout)
        self.assertFalse(lib.load_handover(self.root)["delegable"])

    def test_a_kind_the_level_keeps_is_named(self):
        set_config(self.root, delegate={"level": "routine"})
        (self.root / ".taskets" / "u2.md").write_text(tick(self.u2(), "AC-2"))
        git(self.root, "add", ".taskets/u2.md")
        r = charter(self.root, "handover")
        self.assertIn("Waiting on the owner", r.stdout)
        self.assertIn("level routine (from main) keeps this for the owner", r.stdout)

    def test_an_ask_records_the_owners_words_and_the_session(self):
        set_config(self.root, delegate={"level": "answers"})
        r = charter(self.root, "handover", "--ask", "rule", "cache-ttl", "active", "--quote", "yes, make cache-ttl active",
                    "--session", "sess-1")
        self.assertEqual(r.returncode, 0, r.stderr)
        asks = list((self.root / ".git" / "charter" / "asks").glob("*.json"))
        rec = json.loads(asks[0].read_text())
        self.assertEqual((rec["verb"], rec["target"], rec["status"], rec["quote"], rec["session"]),
                         ("rule", "cache-ttl", "active", "yes, make cache-ttl active", "sess-1"))

    def test_an_ask_below_answers_is_refused(self):
        set_config(self.root, delegate={"level": "routine"})
        r = charter(self.root, "handover", "--ask", "rule", "cache-ttl", "active", "--quote", "yes, make cache-ttl active")
        self.assertEqual(r.returncode, 1)
        self.assertIn("keeps the owner's rulings for the owner", r.stderr)

    def test_an_ask_without_the_owners_words_is_refused(self):
        set_config(self.root, delegate={"level": "answers"})
        r = charter(self.root, "handover", "--ask", "rule", "cache-ttl", "active", "--quote", "yes")
        self.assertEqual(r.returncode, 1)
        self.assertIn("the owner's own words", r.stderr)

    def test_an_ask_the_verb_would_refuse_is_refused(self):
        set_config(self.root, delegate={"level": "answers"})
        r = charter(self.root, "handover", "--ask", "rule", "retry-limit", "rejected", "--quote", "reject the retry limit please")
        self.assertEqual(r.returncode, 1)
        self.assertIn("refuses it now", r.stderr)

    def test_a_merge_below_open_is_refused(self):
        set_config(self.root, delegate={"level": "answers"})
        r = charter(self.root, "handover", "--merge", "7")
        self.assertEqual(r.returncode, 1)
        self.assertIn("level answers (from main) keeps merges for the owner", r.stderr)
        set_config(self.root, delegate={"level": "open"})
        r = charter(self.root, "handover", "--merge", "7", "--method", "squash")
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads((self.root / ".git" / "charter" / "merges" / "7.json").read_text())
        self.assertEqual((rec["pr"], rec["method"], rec["base"]), (7, "squash", "main"))

    def test_wait_without_a_verdict_times_out_with_the_owner_line(self):
        set_config(self.root, delegate={"level": "routine"})
        self.close_check()
        charter(self.root, "handover")
        r = charter(self.root, "handover", "--wait", "--timeout", "0")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertTrue(r.stdout.strip().splitlines()[-1].startswith("CHARTER_OWNER=1 python3 "))

    def test_wait_reports_an_escalation_and_a_commit(self):
        set_config(self.root, delegate={"level": "routine"})
        self.close_check()
        charter(self.root, "handover")
        hid = lib.load_handover(self.root)["id"]
        charter(self.root, "delegate", "settle", "--id", hid, "--result", "escalated", "--judge", "sonnet", "--reason", "probe failed")
        r = charter(self.root, "handover", "--wait", "--timeout", "0")
        self.assertEqual(r.returncode, 3)
        self.assertIn("handed " + hid + " back to the owner (escalated, judged by sonnet): probe failed", r.stdout)
        self.assertTrue(r.stdout.strip().splitlines()[-1].startswith("CHARTER_OWNER=1 python3 "))

    def test_wait_at_strict_returns_at_once(self):
        self.close_check()
        r = charter(self.root, "handover", "--wait", "--timeout", "60")
        self.assertEqual(r.returncode, 3)
        self.assertIn("level strict keeps this handover for the owner", r.stdout)


class DelegateActs(Base):
    def hand_over(self, level="routine"):
        set_config(self.root, delegate={"level": level})
        self.close_check()
        charter(self.root, "handover", "-m", "close u2 AC-1")
        return lib.load_handover(self.root)["id"]

    def test_commit_is_refused_inside_claude_code(self):
        hid = self.hand_over()
        before = self.head()
        r = charter(self.root, "delegate", "commit", "--id", hid, "--judge", "sonnet", env={"CLAUDECODE": "1"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("runs outside Claude Code", r.stderr)
        self.assertEqual(self.head(), before)

    def test_commit_is_refused_when_the_tree_or_index_moved(self):
        hid = self.hand_over()
        (self.root / ".taskets" / "u2.md").write_text(self.u2() + "\nmore\n")   # the tree, after the handover
        r = charter(self.root, "delegate", "commit", "--id", hid)
        self.assertEqual(r.returncode, 1)
        self.assertIn("changed since the handover", r.stderr)
        git(self.root, "add", ".taskets/u2.md")   # and the index
        r = charter(self.root, "delegate", "commit", "--id", hid)
        self.assertIn("changed since the handover", r.stderr)

    def test_commit_is_refused_when_the_level_does_not_cover_it(self):
        hid = self.hand_over()
        set_config(self.root, delegate={"level": "strict"})   # the owner tightened it since
        r = charter(self.root, "delegate", "commit", "--id", hid)
        self.assertEqual(r.returncode, 1)
        self.assertIn("level strict", r.stderr)

    def test_commit_is_the_delegates_with_the_owner_as_author(self):
        hid = self.hand_over()
        r = charter(self.root, "delegate", "commit", "--id", hid, "--judge", "sonnet", "--reason", "probe passes")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        v = json.loads(r.stdout)
        self.assertEqual(v["result"], "committed")
        fmt = git(self.root, "show", "-s", "--format=%an|%ae|%cn|%ce|%B", "HEAD").stdout
        an, ae, cn, ce, body = fmt.split("|", 4)
        self.assertEqual((an, ae), ("Test Owner", "t@example.com"))
        self.assertEqual((cn, ce), lib.DELEGATE_COMMITTER)
        self.assertIn(f"Charter-Delegate: level routine; judged by sonnet; {hid}", body)
        self.assertIsNone(lib.load_handover(self.root))
        self.assertEqual(json.loads((self.root / ".git" / "charter" / "delegate" / f"{hid}.json").read_text())["sha"], self.head())

    def test_perform_rules_without_the_owner_switch(self):
        set_config(self.root, delegate={"level": "answers"})
        charter(self.root, "handover", "--ask", "rule", "cache-ttl", "active", "--quote", "yes, make cache-ttl active")
        aid = json.loads(next((self.root / ".git" / "charter" / "asks").glob("*.json")).read_text())["id"]
        r = charter(self.root, "delegate", "perform", "--id", aid, "--judge", "sonnet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = (self.root / "charter" / "decisions" / "cache-ttl.md").read_text()
        self.assertIn("status: active", text)
        self.assertIn('the owner\'s words: "yes, make cache-ttl active"', text)
        cn = git(self.root, "show", "-s", "--format=%cn", "HEAD").stdout.strip()
        self.assertEqual(cn, lib.DELEGATE_COMMITTER[0])

    def test_perform_is_refused_below_answers(self):
        set_config(self.root, delegate={"level": "answers"})
        charter(self.root, "handover", "--ask", "rule", "cache-ttl", "active", "--quote", "yes, make cache-ttl active")
        aid = json.loads(next((self.root / ".git" / "charter" / "asks").glob("*.json")).read_text())["id"]
        set_config(self.root, delegate={"level": "routine"})
        r = charter(self.root, "delegate", "perform", "--id", aid)
        self.assertEqual(r.returncode, 1)
        self.assertIn("keeps the owner's rulings for the owner", r.stderr)

    def test_the_level_is_set_only_by_the_owner(self):
        r = charter(self.root, "delegate", "level", "open", env={"CLAUDECODE": "1"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("refused to an agent", r.stderr)
        r = charter(self.root, "delegate", "level", "open", env={"CLAUDECODE": "1", "CHARTER_OWNER": "1"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(level_of(self.root), "open")

    def test_the_owner_queue_carries_the_level(self):
        set_config(self.root, delegate={"level": "answers"})
        rep = json.loads(charter(self.root, "owner", "--json").stdout)
        self.assertEqual(rep["delegate"]["level"], "answers")
        self.assertEqual(rep["delegate"]["levels"], ["strict", "routine", "answers", "open"])


class EditGate(Base):
    def write(self, text, rel=".taskets/u2.md"):
        return run_hook(self.root, "pre_tool_gate", {"tool_name": "Write", "tool_input": {"file_path": str(self.root / rel), "content": text}})

    def test_closing_an_owner_check_line_passes_at_routine_with_a_note(self):
        set_config(self.root, delegate={"level": "routine"})
        _, out, so, se = self.write(tick(self.u2(), "AC-1"))
        self.assertEqual(denied(out), "", so + se)
        self.assertIn("delegate takes at level routine", json.dumps(out))

    def test_the_same_edit_is_denied_at_strict(self):
        _, out, so, se = self.write(tick(self.u2(), "AC-1"))
        self.assertIn("only the owner closes such a line", denied(out))

    def test_an_edit_whose_result_cannot_be_computed_stays_denied(self):
        set_config(self.root, delegate={"level": "open"})
        _, out, _, _ = run_hook(self.root, "pre_tool_gate", {"tool_name": "Edit", "tool_input": {
            "file_path": str(self.root / "charter" / "scope.md"), "old_string": "not in the file", "new_string": "x"}})
        self.assertIn("decides what the gates enforce", denied(out))

    def test_rails_and_scope_edits_pass_at_open(self):
        set_config(self.root, delegate={"level": "open"})
        scope = (self.root / "charter" / "scope.md").read_text()
        _, out, _, _ = self.write(scope + "\n- one more assumption\n", "charter/scope.md")
        self.assertEqual(denied(out), "")

    def test_a_config_edit_is_denied_at_open(self):
        set_config(self.root, delegate={"level": "open"})
        _, out, _, _ = self.write('{"track": "prototype"}\n', "charter/config.json")
        self.assertIn("decides what the gates enforce", denied(out))


class ChainGate(Base):
    def bash(self, command):
        _, out, _, _ = run_hook(self.root, "chain_gate", {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                                                           "tool_input": {"command": command}})
        return denied(out)

    def test_the_delegates_acts_and_the_watcher_are_denied(self):
        for cmd in ("python3 .charter/bin/charter delegate commit --id h0123456789ab",
                    "python3 .charter/bin/charter delegate perform --id a0123456789ab",
                    "python3 .charter/bin/charter delegate settle --id h0123456789ab --result committed",
                    "python3 .charter/bin/charter delegate level open",
                    "python3 ~/Projects/charter/bin/charter-delegate run"):
            self.assertIn("never run the delegate's acts", self.bash(cmd), cmd)

    def test_reading_the_plan_and_the_level_is_allowed(self):
        for cmd in ("python3 .charter/bin/charter delegate plan --json", "python3 .charter/bin/charter delegate level",
                    "python3 .charter/bin/charter handover --wait"):
            self.assertEqual(self.bash(cmd), "", cmd)


class UpgradeKind(Base):
    def test_an_installer_settings_merge_is_an_upgrade_the_delegate_takes_at_routine(self):
        set_config(self.root, delegate={"level": "routine"})
        sp = self.root / ".claude" / "settings.json"
        s = json.loads(sp.read_text())
        s["hooks"].pop("SessionEnd")   # a project whose settings lost one of charter's hooks
        sp.write_text(json.dumps(s, indent=2) + "\n")
        git(self.root, "add", ".claude/settings.json")
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "owner: drop a hook", "--", ".claude/settings.json")
        r = subprocess.run([sys.executable, str(INSTALLER), "install", str(self.root)], capture_output=True, text=True, env=clean_env())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Handed to the owner's delegate (level routine", r.stdout)
        rec = lib.load_handover(self.root)
        self.assertEqual(rec["kinds"], {".claude/settings.json": ["upgrade"]})
        self.assertTrue(rec["delegable"])

    def test_a_hand_edit_of_settings_beside_it_is_structural(self):
        set_config(self.root, delegate={"level": "open"})
        sp = self.root / ".claude" / "settings.json"
        s = json.loads(sp.read_text())
        s["permissions"] = {"allow": ["Bash"]}
        sp.write_text(json.dumps(s, indent=2) + "\n")
        git(self.root, "add", ".claude/settings.json")
        r = charter(self.root, "handover")
        self.assertIn("Waiting on the owner", r.stdout)
        self.assertEqual(lib.load_handover(self.root)["kinds"], {".claude/settings.json": ["structural"]})


class FleetLevels(unittest.TestCase):
    def setUp(self):
        self.fleet = Path(tempfile.mkdtemp(prefix="charter-fleet-")).resolve()
        self.a = make_project(track="prototype")
        self.b = make_project(track="prototype")
        self.pa, self.pb = self.fleet / "alpha", self.fleet / "beta"
        self.a.rename(self.pa)
        self.b.rename(self.pb)
        git(self.pa, "worktree", "add", "-q", "-b", "wt", str(self.fleet / "alpha-wt"))

    def tearDown(self):
        cleanup(self.fleet)

    def fleet_levels(self, *args, **env):
        return subprocess.run([sys.executable, str(INSTALLER), "fleet", "--root", str(self.fleet), "--levels", *args],
                              capture_output=True, text=True, env=clean_env(**env))

    def test_an_agent_is_refused_and_a_dry_run_is_not(self):
        r = self.fleet_levels("alpha=open", CLAUDECODE="1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("an agent never runs it", r.stderr)
        r = self.fleet_levels("alpha=open", "--dry-run", CLAUDECODE="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("alpha: would commit on main: delegate level strict (no key) -> open", r.stdout)
        self.assertEqual(lib.committed_level(self.pa, "refs/heads/main")[0], None)

    def test_one_commit_per_repository_on_its_default_branch(self):
        r = self.fleet_levels("alpha=open,beta=routine", "--owner", "beta=Test Owner, t@example.com", CLAUDECODE="1", CHARTER_OWNER="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(lib.committed_level(self.pa, "refs/heads/main")[0], "open")
        self.assertEqual(lib.delegate_level(self.fleet / "alpha-wt")["level"], "open")   # the worktree inherits it
        self.assertEqual(r.stdout.count("alpha:"), 1)
        cfg = json.loads(git(self.pb, "show", "main:charter/config.json").stdout)
        self.assertEqual((cfg["delegate"]["level"], cfg["owner"]), ("routine", "Test Owner, t@example.com"))

    def test_a_repository_with_its_main_line_checked_out_nowhere(self):
        git(self.pb, "switch", "-q", "-c", "feature")
        r = self.fleet_levels("beta=answers", CHARTER_OWNER="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(lib.committed_level(self.pb, "refs/heads/main")[0], "answers")
        self.assertEqual(git(self.pb, "branch", "--show-current").stdout.strip(), "feature")
        self.assertEqual(git(self.pb, "status", "--porcelain").stdout.strip(), "")

    def test_a_main_line_not_on_0_4_14_is_refused(self):
        (self.pb / "charter" / "VERSION").write_text("0.4.13\n")
        git(self.pb, "add", "charter/VERSION")
        owner_commit(self.pb)
        r = self.fleet_levels("beta=open", CHARTER_OWNER="1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("main is on charter 0.4.13; upgrade it to 0.4.14 there first", r.stdout)

    def test_an_unknown_name_writes_nothing(self):
        r = self.fleet_levels("alpha=open,gamma=open", CHARTER_OWNER="1")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no charter project named gamma", r.stderr)
        self.assertIsNone(lib.committed_level(self.pa, "refs/heads/main")[0])


if __name__ == "__main__":
    unittest.main()
