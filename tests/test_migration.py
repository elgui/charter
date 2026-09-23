"""Regression tests for the migration workflow built on the 2026-09-13 leCRM rehearsal: the survey command
(bin/charter_survey.py, bin/charter_plan.py) and the three package defects the rehearsal found. Every test fails
on the package at 99e1a2a and passes once the change is made, except
`ExistingHooks.test_a_clone_without_other_hooks_is_set_as_before`, which guards the behaviour kept and so passes
on 99e1a2a too. `survey` did not exist, the installer and
`charter setup` pointed core.hooksPath at .charter/githooks over the project's own hooks, the installer said
nothing about a path .gitignore keeps out of the commit, and `lib.section` read a tasket titled
`# Log emails ...` as its Log section, which made `charter synth` refuse to write anything. `DoneWhen` covers the owner's
answer L1 of 2026-09-13: the package reads the Tasket skill's `## Done When` as the acceptance checklist; its
`test_a_legacy_done_when_tasket_still_closes_with_a_warning` guards the behaviour kept and so passes on 99e1a2a too."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import INSTALLER, PKG, REPO, charter, cleanup, git, make_project, run_hook

sys.path.insert(0, str(PKG / ".charter"))
sys.path.insert(0, str(REPO / "bin"))
import lib  # noqa: E402

KEY = "sk_" + "test_" + "Q7" * 12   # credential-shaped, built here so no scanner flags this file


def pkg(*args):
    return subprocess.run([sys.executable, "-B", str(INSTALLER), *args], capture_output=True, text=True)


def executable(p: Path, body: str = "#!/bin/sh\nexit 0\n") -> None:
    p.write_text(body)
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def tasket(tid: str, status: str, body: str, title: str = "t") -> str:
    return f"---\nid: {tid}\ntitle: {title}\nstatus: {status}\npriority: p2\n---\n\n# {title}\n\n{body}\n"


def commit(root: Path, msg: str, **author) -> None:
    git(root, "add", "-A")
    extra = [a for k, v in author.items() for a in ("-c", f"user.{k}={v}")]
    git(root, *extra, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", msg)


def legacy_project() -> Path:
    """A bare project shaped like the leCRM main line: every tasket class, lefthook, a deploy workflow that ignores
    only docs, an ignored .claude/settings.json, frozen code, tests and tooling, a credential shape and a binary."""
    root = make_project(with_charter=False)
    (root / "app" / "health.py").write_text("MAX_RETRIES = 3   # runbook: deploy-handoff.md\n")   # no `charter:` marker: nothing here predates the install
    (root / "docs").mkdir()
    (root / "docs" / "deploy-handoff.md").write_text("# Deploy handoff\n\nThe operator guide.\n")
    t = root / ".taskets"
    t.mkdir()
    (t / "a-none.md").write_text(tasket("a-none", "next", "## Context\n\nWork in app/big.py.\n"))
    (t / "b-donewhen.md").write_text(tasket("b-donewhen", "later", "## Done When\n- [ ] endpoint answers\n- [ ] `pytest -q` green\n"))
    (t / "c-donewhen-done.md").write_text(tasket("c-donewhen-done", "done", "## Done When\n- [x] shipped\n- [ ] demo checked\n"))
    (t / "d-ready.md").write_text(tasket("d-ready", "next", "## Acceptance\n\n- [ ] AC-1: ok — probe: `true`\n"))
    (t / "e-prose.md").write_text(tasket("e-prose", "done", "## Acceptance\n\n- works in production\n"))
    (t / "f-pending.md").write_text(tasket("f-pending", "pending", "## Context\n\nold vocabulary\n"))
    (t / "g-dod.md").write_text(tasket("g-dod", "next", "## Definition of Done\n- [ ] shipped\n"))
    (root / "app" / "big.py").write_text("x = 1\n" * 900)
    (root / "tests" / "test_big.py").write_text("y = 1\n" * 850)
    (root / ".claude" / "skills" / "vendor-skill").mkdir(parents=True)
    (root / ".claude" / "skills" / "vendor-skill" / "SKILL.md").write_text("z\n" * 1200)
    (root / "app" / "settings.py").write_text(f'FALLBACK = "{KEY}"\n')
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00binary")
    (root / "lefthook.yml").write_text("pre-commit:\n  commands:\n    fmt:\n      run: true\n")
    (root / ".gitignore").write_text(".claude/settings.json\n")
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "deploy-prod.yml").write_text("name: deploy\non:\n  push:\n    branches: [main]\n    paths-ignore:\n      - '**.md'\n"
                                        "      - 'docs/**'\n      - '.taskets/**'\njobs:\n  d:\n    runs-on: ubuntu-latest\n"
                                        "    steps:\n      - run: ssh deploy@host ./deploy.sh\n")
    (root / "PHASE2_PROGRESS.md").write_text("# Phase 2\n\nstatus\n")
    commit(root, "legacy state (#12)")
    (root / "README.md").write_text("scratch\nmore\n")
    commit(root, "a collaborator's change", name="Other Person", email="o@example.com")
    return root


def survey(root: Path, *args) -> subprocess.CompletedProcess:
    return pkg("survey", str(root), "--offline", *args)


# ---------------------------------------------------------------- lib.section

class SectionHeadings(unittest.TestCase):
    """A tasket titled `# Log emails to the timeline` had its whole body read as `## Log`."""

    def test_a_level_one_title_is_not_a_section(self):
        body = "# Log emails to the timeline\n\n## References\n\n`internal/sync/gmail/gmail.go:46-71`\n"
        self.assertEqual(lib.section(body, "Log"), "")

    def test_a_heading_must_start_with_the_whole_word(self):
        self.assertEqual(lib.section("## Logging design\n\nx\n", "Log"), "")
        self.assertEqual(lib.section("## Log\n\n- 2026-09-13 started\n", "Log"), "- 2026-09-13 started")
        self.assertEqual(lib.section("## Acceptance criteria\n\n- [ ] a\n", "Acceptance"), "- [ ] a")
        self.assertEqual(lib.section("## Evidence (run 42)\n\n- abc\n", "Evidence"), "- abc")

    def test_synth_writes_when_a_tasket_is_titled_log(self):
        root = make_project()
        try:
            (root / ".taskets" / "t9.md").write_text(tasket("t9", "next", "## Context\n\nSee `internal/nowhere/gmail.go:46`.\n",
                                                           title="Log emails to the timeline"))
            commit(root, "a tasket titled Log")
            r = charter(root, "synth")
            self.assertEqual(r.returncode, 0, r.stderr)
            opened = r.stdout.split("## Open, not started", 1)[1].split("\n## ", 1)[0]
            self.assertIn("t9 — Log emails to the timeline", opened)
        finally:
            cleanup(root)


# ---------------------------------------------------------------- git hooks

class ExistingHooks(unittest.TestCase):
    """core.hooksPath replaces the hook directory, so setting it stopped lefthook, pre-commit or husky without a word."""

    def setUp(self):
        self.root = make_project(with_charter=False)

    def tearDown(self):
        cleanup(self.root)

    def hooks_path(self):
        return git(self.root, "config", "--get", "core.hooksPath", check=False).stdout.strip()

    def test_install_keeps_a_hook_the_clone_runs(self):
        executable(self.root / ".git" / "hooks" / "pre-commit")
        r = pkg("install", str(self.root))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.hooks_path(), "")
        self.assertIn("KEEP git hooks", r.stdout)
        self.assertIn(".git/hooks/pre-commit", r.stdout)
        r = pkg("install", str(self.root), "--replace-hooks")
        self.assertEqual(self.hooks_path(), ".charter/githooks")

    def test_a_tracked_framework_counts_even_where_it_is_not_installed(self):
        (self.root / "lefthook.yml").write_text("pre-commit:\n  commands:\n    fmt:\n      run: true\n")
        r = pkg("install", str(self.root))
        self.assertEqual(self.hooks_path(), "")
        self.assertIn("lefthook.yml", r.stdout)

    def test_a_framework_that_runs_the_gate_is_recognised(self):
        (self.root / "lefthook.yml").write_text("pre-commit:\n  commands:\n    charter:\n      run: python3 -B .charter/bin/charter check --staged\n")
        r = pkg("install", str(self.root))
        self.assertEqual(self.hooks_path(), "")
        self.assertIn("lefthook.yml runs the charter gate", r.stdout)
        _, out, stdout, _ = run_hook(self.root, "session_start", {})
        self.assertNotIn("not active", stdout)
        self.assertNotIn("not wired", stdout)

    def test_setup_keeps_other_hooks_and_the_banner_says_why(self):
        pkg("install", str(self.root))
        git(self.root, "config", "--unset", "core.hooksPath")
        executable(self.root / ".git" / "hooks" / "pre-push")
        r = charter(self.root, "setup")
        self.assertIn("KEEP git hooks", r.stdout)
        self.assertEqual(self.hooks_path(), "")
        _, _, stdout, _ = run_hook(self.root, "session_start", {})
        self.assertIn("runs other git hooks", stdout)
        self.assertNotIn("Run `python3 .charter/bin/charter setup` once", stdout)
        charter(self.root, "setup", "--replace-hooks")
        self.assertEqual(self.hooks_path(), ".charter/githooks")

    def test_a_clone_without_other_hooks_is_set_as_before(self):
        r = pkg("install", str(self.root))
        self.assertEqual(self.hooks_path(), ".charter/githooks", r.stdout)


class IgnoredInstallPaths(unittest.TestCase):
    """leCRM ignores .claude/settings.json, so the install commit silently left the session hooks out."""

    def test_install_names_a_path_the_commit_will_not_carry(self):
        root = make_project(with_charter=False)
        try:
            (root / ".gitignore").write_text("node_modules/\n.claude/settings.json\n")
            commit(root, "ignore settings")
            for args in (["--dry-run"], []):
                r = pkg("install", str(root), *args)
                self.assertIn("IGNORED by .gitignore:2 (`.claude/settings.json`), so a commit will not carry it: .claude/settings.json", r.stdout)
            self.assertNotIn("IGNORED", pkg("install", str(root)).stdout)   # nothing written, nothing to warn about
        finally:
            cleanup(root)


# ---------------------------------------------------------------- `## Done When`

DONE_WHEN = "## Done When\n- [ ] AC-1: the endpoint answers — probe: `true`\n\n## Evidence\n\n## Log\n"


class DoneWhen(unittest.TestCase):
    """L1: the Tasket skill writes the checklist under `## Done When`; a tasket made that way after the install could never close."""

    def setUp(self):
        self.root = make_project()

    def tearDown(self):
        cleanup(self.root)

    def close(self, body):
        (self.root / ".taskets" / "t3.md").write_text(tasket("t3", "done", body))
        git(self.root, "add", ".taskets/t3.md")
        return git(self.root, "commit", "-q", "-m", "close t3", check=False)

    def test_a_new_done_when_tasket_is_gated_and_closes_with_evidence(self):
        (self.root / ".taskets" / "t3.md").write_text(tasket("t3", "next", DONE_WHEN))
        commit(self.root, "a tasket written by the Tasket skill")
        refused = self.close(DONE_WHEN)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("1 acceptance box(es) are unchecked", refused.stderr + refused.stdout)
        sha = git(self.root, "rev-parse", "--short", "HEAD").stdout.strip()
        done = DONE_WHEN.replace("- [ ]", "- [x]").replace("## Evidence\n", f"## Evidence\n\n- {sha} landed it\n")
        r = self.close(done)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_probes_and_the_synthesis_read_done_when(self):
        (self.root / ".taskets" / "t3.md").write_text(tasket("t3", "next", DONE_WHEN))
        commit(self.root, "a tasket written by the Tasket skill")
        r = charter(self.root, "probe", "t3")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("`$ true` → exit 0", r.stdout)
        self.assertIn("t3 — t [next]: 0/1 criteria closed", charter(self.root, "synth").stdout)

    def test_a_legacy_done_when_tasket_still_closes_with_a_warning(self):
        root = make_project(with_charter=False)
        try:
            (root / ".taskets").mkdir()
            (root / ".taskets" / "old.md").write_text(tasket("old", "next", DONE_WHEN))
            commit(root, "before charter")
            pkg("install", str(root))
            self.assertIn("old", (root / "charter" / "legacy-taskets.txt").read_text().split())
            commit(root, "install")
            (root / ".taskets" / "old.md").write_text(tasket("old", "done", DONE_WHEN))
            git(root, "add", ".taskets/old.md")
            r = git(root, "commit", "-q", "-m", "close a legacy tasket", check=False)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("legacy tasket old set to done", r.stdout + r.stderr)
        finally:
            cleanup(root)


# ---------------------------------------------------------------- survey

class Survey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = legacy_project()
        cls.before = cls.snapshot(cls.root)
        r = survey(cls.root, "--json", "--test-cmd", "python3 -c 'print(1)'")
        assert r.returncode == 0, r.stdout + r.stderr
        cls.facts = json.loads(r.stdout)
        cls.after = cls.snapshot(cls.root)
        cls.report = survey(cls.root, "--no-rehearse")
        cls.plan = survey(cls.root, "--no-rehearse", "--plan")

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.root)

    @staticmethod
    def snapshot(root: Path):
        files = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        return files, git(root, "config", "--list", "--local").stdout

    def test_the_project_is_not_written(self):
        self.assertEqual(self.before, self.after)
        self.assertFalse((self.root / ".git" / "charter").exists())

    def test_tasket_classes_and_the_legacy_count(self):
        t = self.facts["taskets"]
        self.assertEqual(t["classes"]["none"], {"open": 2})
        self.assertEqual(t["classes"]["done-when"], {"open": 1, "done": 1})
        self.assertEqual(t["classes"]["other:Definition of Done"], {"open": 1})
        self.assertEqual(t["classes"]["ready"], {"open": 1})
        self.assertEqual(t["classes"]["prose"], {"done": 1})
        self.assertEqual([i["id"] for i in t["items"] if i["unknown_status"]], ["f-pending"])
        dry = pkg("install", str(self.root), "--dry-run").stdout
        self.assertIn(f"seed ({t['legacy_at_install']} legacy tasket(s))", dry)
        self.assertEqual(self.facts["rehearsal"]["legacy"], t["legacy_at_install"])

    def test_size_with_each_group_exempt(self):
        sz = self.facts["size"]
        self.assertEqual({f["path"]: f["area"] for f in sz["frozen"]},
                         {".claude/skills/vendor-skill/SKILL.md": "tooling", "app/big.py": "code or docs", "tests/test_big.py": "tests"})
        self.assertEqual(sz["variants"], {"none": 3, "tests": 2, "tooling": 2, "all": 1})
        self.assertEqual(self.facts["frozen_in_open_work"], [{"path": "app/big.py", "lines": 900, "taskets": ["a-none"]}])

    def test_hooks_ignored_paths_and_the_deploy_workflow(self):
        self.assertIn("lefthook.yml", self.facts["hooks"]["other_hooks"])
        self.assertEqual([x["path"] for x in self.facts["claude"]["ignored_install_paths"]], [".claude/settings.json"])
        w = self.facts["ci"]["workflows"][0]
        self.assertTrue(w["deploys"] and w["push_on_mainline"] and w["install_triggers"])
        self.assertEqual(w["changesets"], {"ledger fold": True, "legacy list edit": True, "decision record": False, "tasket edit": False})

    def test_credentials_are_reported_by_shape_only(self):
        self.assertEqual(self.facts["credentials"], [{"path": "app/settings.py", "line": 1, "kind": "stripe secret key", "prefix": "sk_t", "length": len(KEY)}])
        for out in (json.dumps(self.facts), self.report.stdout, self.plan.stdout):
            self.assertNotIn(KEY, out)
            self.assertNotIn(KEY[8:], out)

    def test_history_binaries_documents(self):
        self.assertEqual(self.facts["history"]["authors_90d"], {"Test Owner": 2, "Other Person": 1})
        self.assertEqual(self.facts["history"]["first_parent_50"], {"merge": 0, "squash": 1, "direct": 2})
        self.assertEqual(self.facts["binaries"], ["logo.png"])
        phase = next(m for m in self.facts["markdown"]["root"] if m["path"] == "PHASE2_PROGRESS.md")
        self.assertEqual((phase["archive_candidate"], phase["cited_by"]), (True, []))
        guide = next(m for m in self.facts["markdown"]["docs"] if m["path"] == "docs/deploy-handoff.md")
        self.assertEqual((guide["archive_candidate"], guide["cited_by"]), (True, ["app/health.py"]))
        self.assertIn("docs/deploy-handoff.md stay, because code, CI or other docs cite them", self.plan.stdout)

    def test_the_rehearsal_installs_commits_and_runs_the_gates(self):
        rh = self.facts["rehearsal"]
        self.assertEqual((rh["install_exit"], rh["commit_exit"], rh["synth"]["exit"]), (0, 0, 0), rh)
        self.assertIn("0 blocking", rh["check_all"]["summary"])
        self.assertEqual(rh["strict_size_blocks"], 3)
        self.assertEqual(rh["install_ignored"], [".claude/settings.json"])
        self.assertEqual(rh["left_unstaged"], [])   # the plan's `git add` list stages the whole install
        self.assertNotIn(".claude/settings.json", self.facts["add_paths"])
        self.assertEqual(rh["tests"]["exit"], 0)
        self.assertIsNone(rh["clone"])

    def test_a_branch_can_be_surveyed(self):
        git(self.root, "branch", "charter/install")
        try:
            r = survey(self.root, "--no-rehearse", "--json", "--ref", "charter/install")
            facts = json.loads(r.stdout)
            self.assertEqual(facts["checkout"]["mainline"], "charter/install", r.stdout[-300:])
            w = facts["ci"]["workflows"][0]   # judged for a push to main, where the branch merges
            self.assertTrue(w["push_on_mainline"] and w["install_triggers"])
            self.assertEqual(survey(self.root, "--no-rehearse", "--ref", "no-such-branch").returncode, 2)
        finally:
            git(self.root, "branch", "-D", "charter/install")

    def test_report_and_plan_pass_their_own_anchoring_check(self):
        self.assertEqual(self.report.returncode, 0, self.report.stderr)
        self.assertEqual(self.plan.returncode, 0, self.plan.stderr)
        self.assertIn("# Charter survey:", self.report.stdout)

    def test_the_plan_puts_each_fork_to_the_owner(self):
        p = self.plan.stdout
        for q in ("Which track", "hooks the project already has", "Should charter commits start `.github/workflows/deploy-prod.yml`",
                  "Should `.claude/settings.json` be committed", "checklist sits under `## Definition of Done`", "exempt from the size limit",
                  "Who is told before the install merges", "credential-shaped literals placeholders"):
            self.assertIn(q, p)
        self.assertIn(f"charter-pkg install {self.root} --track prototype", p)
        self.assertIn("merge-commits.md", p)
        self.assertIn("<!-- charter: opinion -->", p)
        self.assertNotIn("checklist sits under `## Done When`", p)   # the package reads it (L1)

    def test_a_branch_is_read_at_its_ref_not_from_the_checkout(self):
        wt = Path(tempfile.mkdtemp(prefix="charter-wt-")) / "wt"
        git(self.root, "worktree", "add", "-q", "-b", "wired", str(wt))
        try:
            (wt / "lefthook.yml").write_text("pre-commit:\n  commands:\n    charter:\n      run: python3 -B .charter/bin/charter check --staged\n")
            (wt / ".gitignore").write_text("node_modules/\n")
            (wt / "charter").mkdir()
            (wt / "charter" / "VERSION").write_text("0.3.0\n")
            (wt / "charter" / "config.json").write_text(json.dumps({"exempt_from_size": ["tests/**"]}))
            commit(wt, "the migration branch, as the checkout never sees it")
            facts = json.loads(survey(self.root, "--no-rehearse", "--json", "--ref", "wired").stdout)
            self.assertEqual(facts["hooks"]["wired_by"], "lefthook.yml")
            self.assertEqual(facts["claude"]["ignored_install_paths"], [])
            self.assertEqual(sorted(f["path"] for f in facts["size"]["frozen"]), [".claude/skills/vendor-skill/SKILL.md", "app/big.py"])
            tree = lambda s: {k: v for k, v in s[0].items() if k.split('/')[0] != '.git'}
            self.assertEqual(tree(self.snapshot(self.root)), tree(self.before))   # the checkout's files are untouched
        finally:
            git(self.root, "worktree", "remove", "--force", str(wt))
            git(self.root, "branch", "-D", "wired")
            cleanup(wt.parent)

    def test_out_must_be_outside_the_project(self):
        r = survey(self.root, "--no-rehearse", "--out", str(self.root / "survey"))
        self.assertEqual(r.returncode, 2)
        self.assertFalse((self.root / "survey").exists())


class NegatedIgnorePattern(unittest.TestCase):
    """`.gitignore` has `.claude/*` then `!.claude/settings.json` (a real migration's project did this):
    `git check-ignore -v --stdin` still prints the negated line, with exit 0, though the file is trackable
    (`git check-ignore -q` on it alone exits 1). The pre-fix code read every printed line as ignored."""

    @classmethod
    def setUpClass(cls):
        cls.root = make_project(with_charter=False)
        (cls.root / ".gitignore").write_text(".claude/*\n!.claude/settings.json\n")
        commit(cls.root, "ignore .claude but keep settings.json")

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.root)

    def test_survey_does_not_list_the_negated_path_as_ignored(self):
        r = survey(self.root, "--no-rehearse", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        facts = json.loads(r.stdout)
        self.assertNotIn(".claude/settings.json", [x["path"] for x in facts["claude"]["ignored_install_paths"]])

    def test_the_installer_does_not_print_ignored_by_for_it(self):
        r = pkg("install", str(self.root), "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(any("IGNORED by" in l and "settings.json" in l for l in r.stdout.splitlines()), r.stdout)


class WorkflowTriggers(unittest.TestCase):
    """GitHub's `paths-ignore` skips a push only when every changed file matches."""

    def test_parse_and_evaluate(self):
        import charter_survey as cs
        ev = cs.parse_triggers("on:\n  push:\n    branches: [main, 'leo/**']\n    paths-ignore:\n      - '**.md'\n      - docs/**\n  pull_request:\n")
        self.assertEqual(ev["push"], {"branches": ["main", "leo/**"], "paths-ignore": ["**.md", "docs/**"]})
        self.assertIn("pull_request", ev)
        self.assertEqual(sorted(cs.parse_triggers('"on": [push, workflow_dispatch]\n')), ["push", "workflow_dispatch"])
        push = ev["push"]
        self.assertFalse(cs.triggers(push, ["a/b/c.md", "docs/x/y.png"]))
        self.assertTrue(cs.triggers(push, ["a.md", "charter/ledger.jsonl"]))
        self.assertTrue(cs.triggers({"paths": ["apps/**"]}, ["apps/api/x.go"]))
        self.assertFalse(cs.triggers({"paths": ["apps/**"]}, ["README.md"]))


if __name__ == "__main__":
    unittest.main()
