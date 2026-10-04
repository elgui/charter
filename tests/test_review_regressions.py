"""Regression tests for the 2026-09-11 weakness review (docs/review/2026-09-11-weakness-evaluation.md).
One class per finding. Each test states the behaviour the review found broken; it fails on the
package at 71ddc0b and passes once the finding is fixed."""
import json
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from helpers import make_project, run_hook, charter, git, cleanup, clean_env, UNIT, INSTALLER, PKG, REPO
from test_gates import write_call, edit_call

sys.path.insert(0, str(PKG / ".charter"))
import lib  # noqa: E402


def decision(out):
    return out.get("hookSpecificOutput", {}).get("permissionDecision") or "allow"


def context(out):
    return out.get("hookSpecificOutput", {}).get("additionalContext", "")


def template(name):
    return (PKG / "charter" / "templates" / name).read_text()


def commit_all(root, msg, **kw):
    git(root, "add", "-A")
    return git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", msg, check=False, **kw)


def set_config(root, **changes):
    cfg = json.loads((root / "charter" / "config.json").read_text())
    for k, v in changes.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k].update(v)
        else:
            cfg[k] = v
    (root / "charter" / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")


def clone(src):
    dst = Path(tempfile.mkdtemp(prefix="charter-clone-")) / "p"
    subprocess.run(["git", "clone", "-q", "file://" + str(src), str(dst)], check=True, capture_output=True, env=clean_env())
    git(dst, "config", "user.name", "Test Owner")
    git(dst, "config", "user.email", "t@example.com")
    return dst


def done_unit(evidence, probe='python3 -c "from app.health import health; assert health()[\'retries\']==3"'):
    text = UNIT.replace("status: next", "status: done").replace("- [ ] AC-1", "- [x] AC-1")
    text = re.sub(r"probe: `[^`]*`", lambda _: f"probe: `{probe}`", text)
    return text.replace("## Evidence\n", f"## Evidence\n\n{evidence}\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.root = make_project()
        self.extra = []

    def tearDown(self):
        cleanup(self.root)
        for d in self.extra:
            cleanup(d)

    def sha(self, ref="HEAD"):
        return git(self.root, "rev-parse", "--short", ref).stdout.strip()


# ---------------------------------------------------------------- finding 1

class TemplateComments(Base):
    """Artifacts written from the shipped templates, comments and all, must be read as meant."""

    def unit_from_template(self, status):
        t = (template("unit.md").replace("<YYYYMMDD-HHMMSS-xxxxx>", "tpl1").replace("<one deliverable, in one line>", "From the template")
             .replace("<YYYY-MM-DD>", "2026-09-11").replace("[app/<area>/**, tests/unit/**]", "[app/health.py, tests/**]"))
        return t.replace("status: next", f"status: {status}")

    def test_done_gate_applies_to_a_unit_from_the_template(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/tpl1.md", self.unit_from_template("done")))
        self.assertEqual(decision(out), "deny", so + se)

    def test_scope_id_from_the_template_is_known(self):
        (self.root / ".taskets" / "tpl1.md").write_text(self.unit_from_template("next"))
        r = charter(self.root, "check", "--all", "--scope")
        self.assertNotIn("unknown scope id", r.stdout)

    def test_decision_retired_from_the_template_cannot_be_cited(self):
        d = (template("decision.md").replace("<slug-same-as-filename>", "tpl-retired").replace("<one line>", "Old way")
             .replace("status: active", "status: retired").replace("<YYYY-MM-DD>", "2026-09-11"))
        (self.root / "charter" / "decisions" / "tpl-retired.md").write_text(d)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", '"""charter:retry-limit charter:tpl-retired"""\nMAX_RETRIES = 3\n'))
        self.assertEqual(decision(out), "deny", so + se)

    def test_decision_active_from_the_template_runs_its_check(self):
        d = (template("decision.md").replace("<slug-same-as-filename>", "tpl-active").replace("<one line>", "Limit is 5")
             .replace("[<glob>, <glob>]", "[app/core.py]").replace("<shell command that exits 0 while the decision holds>", 'grep -q "LIMIT = 5" app/core.py'))
        (self.root / "charter" / "decisions" / "tpl-active.md").write_text(d)
        (self.root / "app" / "core.py").write_text("LIMIT = 9\n")
        rc, out, so, se = run_hook(self.root, "post_tool_gate", write_call(self.root, "app/core.py", "LIMIT = 9\n"))
        self.assertEqual(rc, 2, so + se)
        self.assertIn("contradicted", se)

    def test_change_approved_from_the_template_needs_a_name(self):
        c = (template("change.md").replace("<slug-same-as-filename>", "sneak").replace("<one line>", "Invoicing after all")
             .replace("status: proposed", "status: approved").replace("[<globs this change may touch>]", "[app/billing.py]")
             .replace("<YYYY-MM-DD>", "2026-09-11"))
        (self.root / "charter" / "changes" / "sneak.md").write_text(c)
        r = charter(self.root, "check", "--all", "--changes")
        self.assertEqual(r.returncode, 1, r.stdout)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/billing.py", "def invoice(a):\n    return a * 2\n"))
        self.assertEqual(decision(out), "deny", "an approval without a name must not unlock the path")

    def test_inline_comments_are_read_as_yaml_reads_them(self):
        fields, _, _ = lib.split_frontmatter(
            "---\nstatus: done   # finally\ncheck: grep -q \"#x\" f.txt  # note\nurl: https://x.org/a#frag\n"
            "binds: [a.py, b.py]   # both\nempty:     # nothing\ntag: 'a # b'\n---\n")
        self.assertEqual(fields["status"], "done")
        self.assertEqual(fields["check"], 'grep -q "#x" f.txt')
        self.assertEqual(fields["url"], "https://x.org/a#frag")
        self.assertEqual(fields["binds"], ["a.py", "b.py"])
        self.assertFalse(fields["empty"])
        self.assertEqual(fields["tag"], "a # b")

    def test_a_value_that_is_only_a_comment_is_empty(self):
        fields, _, _ = lib.split_frontmatter("---\nstatus: # not decided\nbinds:\n  - a.py  # the one\ntitle: x\n---\n")
        self.assertEqual(fields["status"], "")
        self.assertEqual(fields["binds"], ["a.py"])

    def test_inline_comment_in_a_tasket_warns_for_the_engines(self):
        t = UNIT.replace("status: next", "status: next   # maybe later")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", t))
        self.assertIn("inline comment", context(out), so + se)

    def test_templates_carry_no_inline_comment_on_a_key(self):
        for name in ("unit.md", "decision.md", "change.md"):
            fm = template(name).split("---")[1]
            for line in fm.splitlines():
                if line.strip() and not line.lstrip().startswith("#"):
                    self.assertNotRegex(line, r"\s#", f"{name}: {line!r}")


# ---------------------------------------------------------------- finding 2

class CiMode(Base):
    def test_ci_refuses_a_file_grown_past_the_limit(self):
        set_config(self.root, limits={"file_lines": 20})
        commit_all(self.root, "limit 20")
        with (self.root / "app" / "health.py").open("a") as f:
            f.write("".join(f"X{i} = {i}\n" for i in range(40)))
        commit_all(self.root, "grow")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("charter/size block", r.stdout)

    def test_ci_leaves_an_untouched_oversized_file_alone(self):
        set_config(self.root, limits={"file_lines": 20})
        (self.root / "app" / "big.py").write_text("".join(f"X{i} = {i}\n" for i in range(40)))
        commit_all(self.root, "big file before the change set")
        (self.root / "app" / "health.py").write_text((self.root / "app" / "health.py").read_text() + "# touched\n")
        commit_all(self.root, "touch another file")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertNotIn("charter/size block", r.stdout)

    def test_ci_passes_a_done_tasket_that_predates_the_change_set(self):
        (self.root / ".taskets" / "legacy.md").write_text("---\nid: legacy\ntitle: Old work\nstatus: done\n---\n\n## Done When\n\nIt works.\n")
        commit_all(self.root, "pre-existing done tasket")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_ci_refuses_a_tasket_flipped_to_done_in_the_change_set(self):
        (self.root / ".taskets" / "u1.md").write_text(UNIT.replace("status: next", "status: done"))
        commit_all(self.root, "u1 done without evidence")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("charter/done block", r.stdout)

    def test_committed_synthesis_passes_the_ci_anchor_step_in_a_clean_clone(self):
        run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", "MAX_RETRIES = 3\n"))   # logs a warning
        r = charter(self.root, "synth", "--write")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        commit_all(self.root, "progress")
        c = clone(self.root)
        self.extra.append(c.parent)
        r = charter(c, "anchors", str(c / "charter" / "progress.md"))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_hex_segment_inside_a_path_is_not_a_commit(self):
        d = self.root / "run-40f77140-d1b7" / "e91f6497d326"
        d.mkdir(parents=True)
        (d / "notes.md").write_text("x\n")
        doc = self.root / "report.md"
        doc.write_text(f"# R\n\nThe reproduction script and its output are kept in {d / 'notes.md'} on this machine.\n")
        r = charter(self.root, "anchors", str(doc))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_the_printed_synthesis_passes_its_own_check_after_gates_logged(self):
        charter(self.root, "check", "--all")   # writes gate events to the log the synthesis summarises
        r = charter(self.root, "synth")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("## Gate activity", r.stdout)

    def test_unusable_base_checks_every_path_and_says_so(self):
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a * 5\n")
        commit_all(self.root, "out of scope")
        for base in ("0" * 40, "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"):
            r = charter(self.root, "check", "--all", "--ci", "--base", base)
            self.assertEqual(r.returncode, 1, f"base {base}: {r.stdout}")
            self.assertIn("base", r.stdout.lower())


# ---------------------------------------------------------------- finding 3

class FreshClone(Base):
    def test_installer_on_a_fresh_clone_activates_the_git_hook(self):
        c = clone(self.root)
        self.extra.append(c.parent)
        subprocess.run([sys.executable, str(INSTALLER), "install", str(c)], capture_output=True, text=True, env=clean_env())
        self.assertEqual(git(c, "config", "--get", "core.hooksPath", check=False).stdout.strip(), ".charter/githooks")
        (c / "app" / "billing.py").write_text("def invoice(a):\n    return a * 9\n")
        git(c, "add", "-A")
        self.assertNotEqual(git(c, "commit", "-q", "-m", "out of scope", check=False).returncode, 0)

    def test_committed_layer_can_activate_the_git_hook_itself(self):
        c = clone(self.root)
        self.extra.append(c.parent)
        r = charter(c, "setup")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(git(c, "config", "--get", "core.hooksPath", check=False).stdout.strip(), ".charter/githooks")

    def test_session_start_tells_claude_when_the_git_hook_is_off(self):
        c = clone(self.root)
        self.extra.append(c.parent)
        rc, out, so, se = run_hook(c, "session_start", {"source": "startup"})
        self.assertIn("charter setup", so)
        rc, out, so, se = run_hook(self.root, "session_start", {"source": "startup"})
        self.assertNotIn("charter setup", so)


# ---------------------------------------------------------------- finding 4

class ProtectedFiles(Base):
    OWNER = {"CHARTER_OWNER": "1"}

    def test_agent_cannot_edit_the_scope(self):
        call = edit_call(self.root, "charter/scope.md", "paths: app/billing.py, app/billing/**\n", "")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", call)
        self.assertEqual(decision(out), "deny", so + se)
        self.assertIn("CHARTER_OWNER", out["hookSpecificOutput"]["permissionDecisionReason"])
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", call, env=self.OWNER)
        self.assertNotEqual(decision(out), "deny", so + se)

    def test_agent_cannot_change_the_config_or_the_gate_code(self):
        cfg = (self.root / "charter" / "config.json").read_text()
        for rel, content in (("charter/config.json", cfg.replace('"done"', '"closed"')),
                             (".charter/checks.py", "def check_scope(*a):\n    return []\n"),
                             (".claude/settings.json", "{}\n"),
                             (".github/workflows/charter.yml", "name: charter\n")):
            rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, rel, content))
            self.assertEqual(decision(out), "deny", f"{rel}: {so + se}")

    def test_agent_cannot_grant_itself_owner_mode_through_settings(self):
        outside = Path(tempfile.mkdtemp(prefix="charter-home-"))
        self.extra.append(outside)
        for path in (self.root / ".claude" / "settings.local.json", outside / "settings.json"):
            call = {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": '{"env": {"CHARTER_OWNER": "1"}}\n'}}
            rc, out, so, se = run_hook(self.root, "pre_tool_gate", call)
            self.assertEqual(decision(out), "deny", f"{path}: {so + se}")

    def test_agent_may_propose_but_not_approve_a_change(self):
        body = "---\nid: inv\ntitle: x\nstatus: {s}\npaths: [app/billing.py]\n{extra}---\n\n## What is asked\n\nA stub.\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/changes/inv.md", body.format(s="proposed", extra="")))
        self.assertNotEqual(decision(out), "deny", so + se)
        approved = body.format(s="approved", extra="approved_by: Test Owner\napproved_on: 2026-09-11\n")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/changes/inv.md", approved))
        self.assertEqual(decision(out), "deny", so + se)
        (self.root / "charter" / "changes" / "inv.md").write_text(body.format(s="proposed", extra=""))
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", edit_call(self.root, "charter/changes/inv.md", "status: proposed", "status: approved"))
        self.assertEqual(decision(out), "deny", so + se)

    def test_agent_may_add_a_decision_but_not_retire_or_weaken_one(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", edit_call(self.root, "charter/decisions/retry-limit.md", "status: active", "status: retired"))
        self.assertEqual(decision(out), "deny", so + se)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", edit_call(self.root, "charter/decisions/retry-limit.md", 'check: grep -q "MAX_RETRIES = 3" app/health.py', "check: true"))
        self.assertEqual(decision(out), "deny", so + se)
        new = "---\nid: timeouts\ntitle: Timeouts are 5 s\nstatus: active\nexpires: 2027-01-01\n---\n\n## Decision\n\n5 s.\n\n## Because\n\nMeasured.\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/decisions/timeouts.md", new))
        self.assertNotEqual(decision(out), "deny", so + se)

    def test_a_second_file_cannot_take_over_a_decision_id(self):
        dup = "---\nid: retry-limit\ntitle: x\nstatus: retired\n---\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/decisions/zzz.md", dup))
        self.assertEqual(decision(out), "deny", so + se)
        (self.root / "charter" / "decisions" / "zzz.md").write_text(dup)
        r = charter(self.root, "check", "--all", "--decisions")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("retry-limit", r.stdout)

    def test_agent_cannot_open_a_split_unit(self):
        split = "---\nid: forever\ntitle: split later\nstatus: later\nkind: split\nperimeter: [app/health.py]\n---\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/forever.md", split))
        self.assertEqual(decision(out), "deny", so + se)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/forever.md", split), env=self.OWNER)
        self.assertNotEqual(decision(out), "deny", so + se)

    def test_a_split_unit_unfreezes_named_files_only(self):
        set_config(self.root, limits={"file_lines": 20})
        big = "\n".join(f"x{i} = {i}" for i in range(25)) + "\n"
        (self.root / ".taskets" / "split1.md").write_text("---\nid: split1\ntitle: split\nstatus: now\nkind: split\nperimeter: [app/**]\n---\n")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", big))
        self.assertEqual(decision(out), "deny", "a glob perimeter must not unfreeze a file: " + so + se)
        (self.root / ".taskets" / "split1.md").write_text("---\nid: split1\ntitle: split\nstatus: now\nkind: split\nperimeter: [app/health.py]\n---\n")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", big))
        self.assertNotEqual(decision(out), "deny", so + se)

    def test_ci_refuses_an_owner_only_change_by_someone_else(self):
        set_config(self.root, owner="Test Owner")
        commit_all(self.root, "owner set")
        sc = self.root / "charter" / "scope.md"
        sc.write_text(sc.read_text().replace("paths: app/billing.py, app/billing/**\n", ""))
        git(self.root, "add", "-A")
        git(self.root, "-c", "user.name=Agent Bot", "-c", "user.email=bot@example.com", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "drop X1 paths")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Agent Bot", r.stdout)
        git(self.root, "reset", "-q", "--hard", "HEAD~1")
        sc.write_text(sc.read_text().replace("paths: app/billing.py, app/billing/**\n", ""))
        commit_all(self.root, "owner drops X1 paths")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertNotIn("Agent Bot", r.stdout)
        self.assertNotIn("charter/protected block", r.stdout)

    def test_ci_sees_an_owner_only_change_made_inside_a_merge_commit(self):
        set_config(self.root, owner="Test Owner")
        commit_all(self.root, "owner set")
        base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        bot = ["-c", "user.name=Agent Bot", "-c", "user.email=bot@example.com", "-c", "core.hooksPath=/dev/null"]
        git(self.root, "checkout", "-q", "-b", "feature")
        (self.root / "notes.txt").write_text("unrelated\n")
        git(self.root, "add", "-A")
        git(self.root, *bot, "commit", "-q", "-m", "feature: unrelated file")
        git(self.root, "checkout", "-q", "main")
        (self.root / "README.md").write_text("main moved on\n")
        commit_all(self.root, "main: readme")
        git(self.root, *bot, "merge", "--no-ff", "--no-commit", "feature", check=False)
        sc = self.root / "charter" / "scope.md"
        sc.write_text(sc.read_text().replace("paths: app/billing.py, app/billing/**\n", ""))
        git(self.root, "add", "-A")
        git(self.root, *bot, "commit", "-q", "-m", "merge feature")
        r = charter(self.root, "check", "--all", "--ci", "--base", base)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("charter/scope.md", r.stdout)
        self.assertIn("Agent Bot", r.stdout)

    def test_ci_does_not_blame_a_merge_for_the_owner_changes_it_brings_in(self):
        set_config(self.root, owner="Test Owner")
        commit_all(self.root, "owner set")
        base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        bot = ["-c", "user.name=Agent Bot", "-c", "user.email=bot@example.com", "-c", "core.hooksPath=/dev/null"]
        git(self.root, "checkout", "-q", "-b", "feature")
        (self.root / "notes.txt").write_text("unrelated\n")
        git(self.root, "add", "-A")
        git(self.root, *bot, "commit", "-q", "-m", "feature: unrelated file")
        git(self.root, "checkout", "-q", "main")
        sc = self.root / "charter" / "scope.md"
        sc.write_text(sc.read_text() + "\n- the owner adds an assumption\n")
        commit_all(self.root, "owner: scope")
        git(self.root, "checkout", "-q", "feature")
        git(self.root, *bot, "merge", "-q", "--no-ff", "-m", "update branch", "main")
        r = charter(self.root, "check", "--all", "--ci", "--base", base)
        self.assertNotIn("charter/protected block", r.stdout)

    def test_ci_sees_a_merge_that_drops_the_owners_later_change(self):
        set_config(self.root, owner="Test Owner")
        commit_all(self.root, "owner set")
        base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        bot = ["-c", "user.name=Agent Bot", "-c", "user.email=bot@example.com", "-c", "core.hooksPath=/dev/null"]
        git(self.root, "checkout", "-q", "-b", "feature")
        (self.root / "notes.txt").write_text("unrelated\n")
        git(self.root, "add", "-A")
        git(self.root, *bot, "commit", "-q", "-m", "feature: unrelated file")
        git(self.root, "checkout", "-q", "main")
        sc = self.root / "charter" / "scope.md"
        sc.write_text(sc.read_text() + "\n- the owner tightens an assumption\n")
        commit_all(self.root, "owner: scope after the base")
        git(self.root, *bot, "merge", "--no-ff", "--no-commit", "feature", check=False)
        git(self.root, "checkout", "feature", "--", "charter/scope.md")   # keep the stale side
        git(self.root, *bot, "commit", "-q", "-m", "merge feature, keeping the old scope")
        r = charter(self.root, "check", "--all", "--ci", "--base", base)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("Agent Bot", r.stdout)

    def test_reopening_a_split_unit_counts_for_any_done_status(self):
        set_config(self.root, done_statuses=["done", "shipped"])
        split = "---\nid: s1\ntitle: split\nstatus: shipped\nkind: split\nperimeter: [app/health.py]\n---\n"
        (self.root / ".taskets" / "s1.md").write_text(split)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/s1.md", split.replace("status: shipped", "status: now")))
        self.assertEqual(decision(out), "deny", so + se)

    def test_an_agent_may_narrow_an_open_split_unit(self):
        split = "---\nid: s1\ntitle: split\nstatus: now\nkind: split\nperimeter: [app/health.py, app/billing.py]\n---\n"
        (self.root / ".taskets" / "s1.md").write_text(split)
        narrower = split.replace("perimeter: [app/health.py, app/billing.py]", "perimeter: [app/health.py]")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/s1.md", narrower))
        self.assertNotEqual(decision(out), "deny", so + se)
        wider = split.replace("perimeter: [app/health.py, app/billing.py]", "perimeter: [app/health.py, app/billing.py, README.md]")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/s1.md", wider))
        self.assertEqual(decision(out), "deny", so + se)
        closed = split.replace("status: now", "status: done")
        (self.root / ".taskets" / "s1.md").write_text(closed)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/s1.md", split))
        self.assertEqual(decision(out), "deny", "reopening a closed split unit unfreezes its files again: " + so + se)

    def test_session_start_says_when_no_owner_is_named(self):
        rc, out, so, se = run_hook(self.root, "session_start", {"source": "startup"})
        self.assertIn("names no owner", so)
        set_config(self.root, owner="Test Owner")
        rc, out, so, se = run_hook(self.root, "session_start", {"source": "startup"})
        self.assertNotIn("names no owner", so)

    def test_ci_refuses_gate_code_that_differs_from_the_manifest(self):
        p = self.root / ".charter" / "checks.py"
        p.write_text(p.read_text().replace("def check_scope(", "def _orig_check_scope(", 1) + "\n\ndef check_scope(*a, **k):\n    return []\n")
        commit_all(self.root, "neuter the scope gate")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("manifest", r.stdout)

    def test_precommit_inside_claude_code_refuses_an_owner_only_change(self):
        sc = self.root / "charter" / "scope.md"
        sc.write_text(sc.read_text().replace("paths: app/billing.py, app/billing/**\n", ""))
        git(self.root, "add", "charter/scope.md")
        self.assertEqual(charter(self.root, "check", "--staged", env={"CLAUDECODE": "1"}).returncode, 1)
        self.assertEqual(charter(self.root, "check", "--staged", env={"CLAUDECODE": "1", "CHARTER_OWNER": "1"}).returncode, 0)
        self.assertEqual(charter(self.root, "check", "--staged").returncode, 0)


# ---------------------------------------------------------------- finding 5

class DoneEvidence(Base):
    def test_a_url_or_a_bare_path_is_not_evidence_of_done(self):
        for ev in ("- https://example.com", "- README.md"):
            rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", done_unit(ev)))
            self.assertEqual(decision(out), "deny", f"{ev}: {so + se}")

    def test_a_recorded_run_is_evidence_of_done(self):
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", done_unit("- `$ python3 -m pytest -q` → 1 passed")))
        self.assertNotEqual(decision(out), "deny", so + se)

    def test_probe_mode_runs_the_probes_of_a_unit_closed_in_the_commit(self):
        ev = f"- {self.sha()} app/health.py:2"
        (self.root / ".taskets" / "u1.md").write_text(done_unit(ev, probe='python3 -c "raise SystemExit(1)"'))
        git(self.root, "add", ".taskets/u1.md")
        r = charter(self.root, "check", "--staged", "--probe")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("probe", r.stdout)
        (self.root / ".taskets" / "u1.md").write_text(done_unit(ev))
        git(self.root, "add", ".taskets/u1.md")
        r = charter(self.root, "check", "--staged", "--probe")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_probes_run_in_ci_when_the_project_asks_for_it(self):
        ev = f"- {self.sha()} app/health.py:2"
        (self.root / ".taskets" / "u1.md").write_text(done_unit(ev, probe='python3 -c "raise SystemExit(1)"'))
        commit_all(self.root, "u1 done, probe fails")
        self.assertEqual(charter(self.root, "check", "--all", "--ci", "--base", "HEAD~1").returncode, 0)
        set_config(self.root, probes={"in_ci": True})
        commit_all(self.root, "probes in ci")
        r = charter(self.root, "check", "--all", "--ci", "--base", "HEAD~2")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("probe", r.stdout)

    def test_probe_command_prints_evidence_lines(self):
        r = charter(self.root, "probe", "u1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"\$ python3 -c .*exit 0")

    def test_weakening_acceptance_mid_flight_needs_a_log_line(self):
        running = UNIT.replace("status: next", "status: now")
        (self.root / ".taskets" / "u1.md").write_text(running)
        probe = re.search(r"probe: `([^`]*)`", running).group(1)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", edit_call(self.root, ".taskets/u1.md", probe, "true"))
        self.assertEqual(decision(out), "deny", so + se)
        weaker = running.replace(probe, "true").replace("- 2026-09-11 14:00 created\n", "- 2026-09-11 14:00 created\n- 2026-09-11 15:00 AC-1 probe replaced: the import path moved\n")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, ".taskets/u1.md", weaker))
        self.assertNotEqual(decision(out), "deny", so + se)


# ---------------------------------------------------------------- finding 6

class SquashedEvidence(Base):
    def squash_merge(self):
        a = self.root
        base = git(a, "rev-parse", "HEAD").stdout.strip()
        git(a, "checkout", "-q", "-b", "feat")
        (a / "app" / "health.py").write_text((a / "app" / "health.py").read_text().replace("MAX_RETRIES}", "MAX_RETRIES}  # reports retries"))
        commit_all(a, "feat: report retries")
        x = self.sha()
        (a / ".taskets" / "u1.md").write_text(done_unit(f"- {x} app/health.py:6"))
        commit_all(a, "u1 done")
        head = git(a, "rev-parse", "HEAD").stdout.strip()
        git(a, "checkout", "-q", "main")
        git(a, "merge", "--squash", "feat", check=False)
        commit_all(a, "Squash feat")
        git(a, "update-ref", "refs/pull/1/head", head)   # what a hosted pull request keeps
        git(a, "branch", "-q", "-D", "feat")
        return base, x

    def test_ci_recipe_fetches_pull_request_heads_so_squashed_evidence_resolves(self):
        base, x = self.squash_merge()
        c = clone(self.root)
        self.extra.append(c.parent)
        wf = (PKG / ".github" / "workflows" / "charter.yml").read_text()
        fetch = [l.strip() for l in wf.splitlines() if "refs/pull/" in l and "git fetch" in l]
        self.assertTrue(fetch, "the workflow must fetch pull-request heads")
        subprocess.run(re.sub(r"^-?\s*run:\s*", "", fetch[0]), shell=True, cwd=str(c), capture_output=True, env=clean_env())
        r = charter(c, "check", "--all", "--ci", "--base", base)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_synthesis_labels_a_squashed_sha_historical(self):
        base, x = self.squash_merge()
        c = clone(self.root)
        self.extra.append(c.parent)
        r = charter(c, "synth")
        line = [l for l in r.stdout.splitlines() if l.startswith("- u1 ")]
        self.assertTrue(line, r.stdout + r.stderr)
        self.assertIn("historical", line[0])
        self.assertIn("## Done and accepted\n- u1", r.stdout)


# ---------------------------------------------------------------- finding 7

class SharedState(Base):
    def test_worktrees_share_the_log_and_it_outlives_them(self):
        wt = Path(tempfile.mkdtemp(prefix="charter-wt-")) / "wt"
        self.extra.append(wt.parent)
        git(self.root, "worktree", "add", "-q", str(wt), "-b", "wt")
        run_hook(wt, "pre_tool_gate", write_call(wt, "app/health.py", "MAX_RETRIES = 3\n"))   # warns: marker missing
        self.assertIn("decisions/warn", charter(self.root, "log").stdout)
        git(self.root, "worktree", "remove", "--force", str(wt))
        self.assertIn("decisions/warn", charter(self.root, "log").stdout)

    def test_state_leaves_the_tree_clean(self):
        charter(self.root, "unit", "start", "u1")
        run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", "MAX_RETRIES = 3\n"))
        self.assertFalse((self.root / ".charter" / "state").exists())

    def test_charter_unit_in_the_environment_wins_over_the_state_file(self):
        (self.root / ".taskets" / "u2.md").write_text(UNIT.replace("id: u1", "id: u2").replace("title: Health endpoint reports retries", "title: Second unit"))
        charter(self.root, "unit", "start", "u1")
        rc, out, so, se = run_hook(self.root, "session_start", {"source": "startup"}, env={"CHARTER_UNIT": "u2"})
        self.assertIn("Active unit u2", so)


# ---------------------------------------------------------------- finding 8

class Ledger(Base):
    def end_session(self, sid, models=(("model-a", 1_000_000, 1_000_000),)):
        tr = self.root / f"transcript-{sid}.jsonl"
        lines = [json.dumps({"type": "assistant", "requestId": f"r{i}", "message": {"id": f"m{i}", "model": m, "usage": {
            "input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}})
            for i, (m, inp, out) in enumerate(models)]
        tr.write_text("\n".join(lines) + "\n")
        run_hook(self.root, "session_end", {"session_id": sid, "transcript_path": str(tr), "reason": "exit"})
        tr.unlink()

    def accept_u1(self):
        (self.root / ".taskets" / "u1.md").write_text(done_unit(f"- {self.sha()} app/health.py:2"))
        commit_all(self.root, "u1 accepted")

    def test_acceptance_is_read_when_the_synthesis_runs(self):
        charter(self.root, "unit", "start", "u1")
        self.end_session("s1")
        charter(self.root, "ledger", "fold")
        self.accept_u1()
        r = charter(self.root, "synth")
        cost = r.stdout.split("## Cost per accepted result")[1]
        self.assertRegex(cost, r"- u1: .*\baccepted\b", cost)
        self.assertNotIn("not accepted", cost)

    def test_prices_are_per_model(self):
        set_config(self.root, prices_usd_per_mtok={"default": {"input": 100, "output": 100, "cache_read": 0, "cache_write": 0},
                                                   "model-a": {"input": 1, "output": 2, "cache_read": 0, "cache_write": 0},
                                                   "model-b": {"input": 10, "output": 20, "cache_read": 0, "cache_write": 0}})
        self.end_session("s1", models=(("model-a-2026", 1_000_000, 1_000_000), ("model-b", 1_000_000, 0)))
        charter(self.root, "ledger", "fold")
        rec = json.loads((self.root / "charter" / "ledger.jsonl").read_text().splitlines()[-1])
        self.assertAlmostEqual(rec["est_usd"], 1 + 2 + 10)

    def test_one_hour_cache_writes_are_priced_as_such(self):
        set_config(self.root, prices_usd_per_mtok={"model-a": {"input": 1, "output": 0, "cache_read": 0, "cache_write": 3, "cache_write_1h": 7}})
        tr = self.root / "transcript.jsonl"
        usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 3_000_000,
                 "cache_creation": {"ephemeral_5m_input_tokens": 1_000_000, "ephemeral_1h_input_tokens": 2_000_000}}
        tr.write_text(json.dumps({"type": "assistant", "requestId": "r1", "message": {"id": "m1", "model": "model-a", "usage": usage}}) + "\n")
        run_hook(self.root, "session_end", {"session_id": "s1", "transcript_path": str(tr), "reason": "exit"})
        charter(self.root, "ledger", "fold")
        rec = json.loads((self.root / "charter" / "ledger.jsonl").read_text().splitlines()[-1])
        self.assertAlmostEqual(rec["est_usd"], 1 * 3 + 2 * 7)

    def test_rework_counts_sessions_after_the_first_done(self):
        charter(self.root, "unit", "start", "u1")
        self.end_session("before")
        time.sleep(1.1)
        self.accept_u1()
        time.sleep(1.1)
        # 0.4.7: a session is charged to a done unit only if it started that unit itself; the
        # checkout's shared choice stops at done (tests/test_gate_noise_0_4_7.py). Rework starts it.
        charter(self.root, "unit", "start", "u1", env={"CLAUDE_CODE_SESSION_ID": "after"})
        self.end_session("after")
        charter(self.root, "ledger", "fold")
        r = charter(self.root, "synth")
        self.assertRegex(r.stdout, r"- u1: 2 session\(s\).*1 after the first done", r.stdout)

    def test_human_minutes_are_recorded_per_unit(self):
        r = charter(self.root, "ledger", "add", "--human-minutes", "30", "--unit", "u1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(charter(self.root, "synth").stdout, r"- u1: .*30 human min")


# ---------------------------------------------------------------- finding 9

class ScopeParser(Base):
    def rewrite_scope(self, old, new):
        sc = self.root / "charter" / "scope.md"
        sc.write_text(sc.read_text().replace(old, new))

    def billing_write(self):
        return run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/billing.py", "def invoice(a):\n    return a * 2\n"))

    def test_hyphenated_out_of_scope_heading_still_gates(self):
        self.rewrite_scope("## Out of scope", "## Out-of-Scope")
        rc, out, so, se = self.billing_write()
        self.assertEqual(decision(out), "deny", so + se)

    def test_item_without_an_id_still_gates_and_is_reported(self):
        self.rewrite_scope("### X1 — Invoicing", "### Invoicing")
        rc, out, so, se = self.billing_write()
        self.assertEqual(decision(out), "deny", so + se)
        r = charter(self.root, "check", "--all", "--scope")
        self.assertIn("no id", r.stdout)

    def test_scope_file_problems_are_reported(self):
        self.rewrite_scope("paths: app/billing.py, app/billing/**\n", "")
        self.rewrite_scope("## Assumptions", "## Exclusions\n\n### Z1 — Reporting\npaths: app/reports/**\n\n## Assumptions")
        r = charter(self.root, "check", "--all", "--scope")
        self.assertIn("X1", r.stdout)
        self.assertIn("no paths", r.stdout)
        self.assertIn("Exclusions", r.stdout)

    def test_unit_perimeter_reaching_out_of_scope_is_reported(self):
        (self.root / ".taskets" / "u1.md").write_text(UNIT.replace("perimeter: [app/health.py, tests/**]", "perimeter: [app/health.py, app/billing.py]"))
        r = charter(self.root, "check", "--all", "--scope")
        self.assertRegex(r.stdout, r"u1.*perimeter.*X1")


# ---------------------------------------------------------------- finding 10

class LegacyTaskets(unittest.TestCase):
    def setUp(self):
        self.root = make_project(with_charter=False)
        (self.root / ".taskets").mkdir()
        (self.root / ".taskets" / "old.md").write_text("---\nid: old\ntitle: Old work\nstatus: next\npriority: p2\n---\n\n## Done When\n\nIt works.\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "a tasket from before charter")
        r = subprocess.run([sys.executable, str(INSTALLER), "install", str(self.root), "--track", "client"], capture_output=True, text=True, env=clean_env())
        assert r.returncode == 0, r.stdout + r.stderr
        commit_all(self.root, "install charter")

    def tearDown(self):
        cleanup(self.root)

    def test_installer_grandfathers_the_taskets_it_finds(self):
        self.assertIn("old", (self.root / "charter" / "legacy-taskets.txt").read_text().split())

    def test_an_engine_can_close_a_legacy_tasket(self):
        p = self.root / ".taskets" / "old.md"
        p.write_text(p.read_text().replace("status: next", "status: done"))
        git(self.root, "add", "-A")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("legacy", r.stdout)

    def test_an_agent_may_shorten_the_legacy_list_but_not_extend_it(self):
        p = self.root / "charter" / "legacy-taskets.txt"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/legacy-taskets.txt", p.read_text() + "new\n"))
        self.assertEqual(decision(out), "deny", so + se)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/legacy-taskets.txt", p.read_text().replace("old\n", "")))
        self.assertNotEqual(decision(out), "deny", so + se)

    def test_a_new_tasket_is_gated(self):
        (self.root / ".taskets" / "new.md").write_text("---\nid: new\ntitle: New work\nstatus: done\n---\n\nDone.\n")
        git(self.root, "add", "-A")
        self.assertEqual(charter(self.root, "check", "--staged").returncode, 1)


# ---------------------------------------------------------------- finding 11

class StopGateTurns(Base):
    def stop(self, msg, active=False):
        return run_hook(self.root, "stop_gate", {"last_assistant_message": msg, "stop_hook_active": active})

    def edit(self, rel="README.md"):
        (self.root / rel).write_text("edited\n")
        run_hook(self.root, "post_tool_gate", write_call(self.root, rel, "edited\n"))

    def test_a_turn_that_changed_nothing_is_not_judged(self):
        rc, out, so, se = self.stop("I finished reading the scope. The billing module is out of scope, so it is not done here.")
        self.assertNotEqual(out.get("decision"), "block", so + se)
        rc, out, so, se = self.stop("All done: the explanation is complete.")
        self.assertNotEqual(out.get("decision"), "block", so + se)

    def test_a_bare_path_does_not_answer_a_claim(self):
        self.edit()
        rc, out, so, se = self.stop("All done, it works. See README.md.")
        self.assertEqual(out.get("decision"), "block", so + se)

    def test_a_commit_answers_a_claim_and_the_marker_resets(self):
        self.edit()
        rc, out, so, se = self.stop(f"Done in {self.sha()}.")
        self.assertNotEqual(out.get("decision"), "block", so + se)
        rc, out, so, se = self.stop("All done.")
        self.assertNotEqual(out.get("decision"), "block", "the next turn changed nothing: " + so + se)

    def test_a_short_sha_made_of_digits_is_still_a_commit(self):
        for _ in range(400):   # about one short SHA in 27 is all digits: (10/16)**7
            git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "--allow-empty", "-m", "empty")
            short = git(self.root, "rev-parse", "--short=7", "HEAD").stdout.strip()
            if short.isdigit():
                break
        self.assertTrue(short.isdigit(), short)
        self.edit()
        rc, out, so, se = self.stop(f"Done in {short}.")
        self.assertNotEqual(out.get("decision"), "block", so + se)

    def test_a_landed_commit_without_a_log_line_is_told_to_claude(self):
        charter(self.root, "unit", "start", "u1")
        run_hook(self.root, "session_start", {"source": "startup"})
        (self.root / "app" / "health.py").write_text((self.root / "app" / "health.py").read_text() + "# more\n")
        commit_all(self.root, "work")
        rc, out, so, se = self.stop(f"Committed {self.sha()} with the change to app/health.py:7.")
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "Stop", so + se)
        self.assertIn("## Log", context(out))
        self.assertNotIn("systemMessage", out)


# ---------------------------------------------------------------- finding 12

class PullRequestBody(Base):
    def anchors_pr(self, body):
        p = self.root / "pr.md"
        p.write_text(body)
        return charter(self.root, "anchors", "--pr", str(p))

    def test_an_ordinary_body_warns_and_passes(self):
        r = self.anchors_pr("Fixes the webhook retry bug the client reported last week.\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("unanchored", r.stdout)

    def test_an_issue_reference_is_an_anchor(self):
        r = self.anchors_pr("Closes #123\n")
        self.assertIn("1 anchored", r.stdout)

    def test_an_empty_body_warns(self):
        r = self.anchors_pr("")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("empty", r.stdout)

    def test_prototype_track_anchors_warn_as_the_method_says(self):
        doc = self.root / "docs-report.md"
        doc.write_text("# R\n\nThe endpoint was rewritten and doubles throughput in production.\n")
        self.assertEqual(charter(self.root, "anchors", str(doc)).returncode, 1)
        set_config(self.root, track="prototype")
        r = charter(self.root, "anchors", str(doc))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("WARN", r.stdout)

    def test_workflow_reruns_when_the_body_is_edited(self):
        wf = (PKG / ".github" / "workflows" / "charter.yml").read_text()
        self.assertRegex(wf, r"pull_request:\s*\n\s*types:\s*\[[^\]]*edited")


# ---------------------------------------------------------------- finding 13

class StagedContent(Base):
    def test_a_partially_staged_violation_is_refused(self):
        good = (self.root / "app" / "health.py").read_text()
        (self.root / "app" / "health.py").write_text(good.replace("MAX_RETRIES = 3", "MAX_RETRIES = 10"))
        git(self.root, "add", "app/health.py")
        (self.root / "app" / "health.py").write_text(good)
        r = git(self.root, "commit", "-q", "-m", "partial staging", check=False)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("MAX_RETRIES = 10", git(self.root, "show", "HEAD:app/health.py").stdout)

    def test_the_commit_is_judged_against_the_staged_scope(self):
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a * 3\n")
        git(self.root, "add", "app/billing.py")
        sc = self.root / "charter" / "scope.md"
        sc.write_text(sc.read_text().replace("paths: app/billing.py, app/billing/**\n", ""))   # unstaged
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("charter/scope block", r.stdout)


# ---------------------------------------------------------------- docs vs code

class UnitDecisionsKey(Base):
    def test_a_unit_relying_on_a_retired_decision_is_reported(self):
        (self.root / ".taskets" / "u1.md").write_text(UNIT.replace("decisions: [retry-limit]", "decisions: [old-cache]"))
        r = charter(self.root, "check", "--all", "--decisions")
        self.assertRegex(r.stdout, r"u1.*old-cache.*retired")


if __name__ == "__main__":
    unittest.main()
