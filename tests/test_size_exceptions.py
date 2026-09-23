"""Change 4 (size rule): named exceptions, a governance byte budget, a configurable governance set.
Each test fails if the corresponding piece is removed."""
import json
import unittest

from helpers import clean_env, make_project, run_hook, charter, git, cleanup


def write_call(root, rel, content):
    return {"tool_name": "Write", "tool_input": {"file_path": str(root / rel), "content": content}}


def lines(n, prefix="x"):
    return "".join(f"{prefix}{i} = {i}\n" for i in range(n))


def health(n):
    """app/health.py at n lines, keeping the fixture decision's invariant."""
    return '"""Health. charter:retry-limit"""\nMAX_RETRIES = 3\n' + lines(n - 2)


def denied(out):
    return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


class SizeExceptions(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        self.set_cfg(lambda c: c["limits"].update(file_lines=20))

    def tearDown(self):
        cleanup(self.root)

    def set_cfg(self, fn):
        p = self.root / "charter" / "config.json"
        cfg = json.loads(p.read_text())
        fn(cfg)
        p.write_text(json.dumps(cfg))

    def exception(self, **kw):
        e = {"path": "app/health.py", "lines": 40, "because": "open work grows it; split planned", "expires": "2099-01-01"}
        e.update(kw)
        self.set_cfg(lambda c: c.__setitem__("size_exceptions", [{k: v for k, v in e.items() if v is not None}]))
        git(self.root, "add", "charter/config.json")   # the owner's commit; the staged checks read it from the index
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "size exception")

    def test_exception_lets_a_file_grow_within_its_budget(self):
        self.exception()
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", lines(30)))
        self.assertFalse(denied(out), so + se)

    def test_growth_beyond_the_exception_budget_is_refused(self):
        self.exception()
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", lines(45)))
        self.assertTrue(denied(out), so + se)
        self.assertIn("40-line", out["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertIn("exception", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_expired_exception_no_longer_applies_and_warns(self):
        self.exception(expires="2020-01-01")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", lines(30)))
        self.assertTrue(denied(out), so + se)
        self.assertIn("expired", out["hookSpecificOutput"]["permissionDecisionReason"])
        r = charter(self.root, "check", "--all")
        self.assertIn("expired on 2020-01-01", r.stdout)

    def test_exception_expiring_today_is_expired(self):
        import datetime
        self.exception(expires=datetime.date.today().isoformat())
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", lines(30)))
        self.assertTrue(denied(out), so + se)

    def test_exception_without_because_or_expires_is_ignored_and_warned(self):
        for missing in ("because", "expires"):
            self.exception(**{missing: None})
            rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", lines(30)))
            self.assertTrue(denied(out), missing + so + se)
            r = charter(self.root, "check", "--all")
            self.assertIn("size_exceptions", r.stdout, missing)
            self.assertIn(missing, r.stdout)

    def test_precommit_honours_the_exception(self):
        self.exception()
        (self.root / "app" / "health.py").write_text(health(30))
        git(self.root, "add", "app/health.py")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 0, r.stdout)
        (self.root / "app" / "health.py").write_text(health(45))
        git(self.root, "add", "app/health.py")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("charter/size block", r.stdout)

    def test_strict_report_names_the_exception(self):
        self.exception()
        (self.root / "app" / "health.py").write_text(lines(30))
        git(self.root, "add", "app/health.py")
        git(self.root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "grow")
        r = charter(self.root, "check", "--all", "--strict", "--size")
        self.assertNotIn("charter/size block [app/health.py]", r.stdout)

    def test_a_boolean_budget_is_not_a_budget(self):
        """JSON `true` is a Python int; an exception whose budget is `true` must be ignored, not read as 1."""
        self.exception(lines=True)
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/health.py", lines(30)))
        self.assertTrue(denied(out), so + se)
        self.assertIn("20-line", out["hookSpecificOutput"]["permissionDecisionReason"])
        r = charter(self.root, "check", "--all")
        self.assertIn("no positive `lines` or `bytes` budget", r.stdout)

    def test_agent_edit_of_size_exceptions_is_refused(self):
        p = self.root / "charter" / "config.json"
        cfg = json.loads(p.read_text())
        cfg["size_exceptions"] = [{"path": "app/health.py", "lines": 4000, "because": "x", "expires": "2099-01-01"}]
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "charter/config.json", json.dumps(cfg)))
        self.assertTrue(denied(out), so + se)


class GovernanceBytes(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")

    def tearDown(self):
        cleanup(self.root)

    def set_cfg(self, fn):
        p = self.root / "charter" / "config.json"
        cfg = json.loads(p.read_text())
        fn(cfg)
        p.write_text(json.dumps(cfg))

    def test_default_budget_is_32_kib(self):
        cfg = json.loads((self.root / "charter" / "config.json").read_text())
        self.assertEqual(cfg["limits"]["governance_bytes"], 32768)

    def test_byte_budget_freezes_a_governance_file_under_the_line_limit(self):
        # tcv2's roadmap carries a 40,869-character line; 3 lines, 41 KB
        text = "# Rules\n" + "x" * 40869 + "\nend\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "CLAUDE.md", text))
        self.assertTrue(denied(out), so + se)
        self.assertIn("32768-byte", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_byte_budget_does_not_apply_to_code(self):
        text = "x = '" + "y" * 40000 + "'\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "app/big.py", text))
        self.assertFalse(denied(out), so + se)

    def test_byte_budget_counts_in_commit_checks(self):
        (self.root / "AGENTS.md").write_text("# Agents\n" + "z" * 40000 + "\n")
        git(self.root, "add", "AGENTS.md")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("byte", r.stdout)

    def test_exception_can_raise_the_byte_budget(self):
        self.set_cfg(lambda c: c.__setitem__("size_exceptions", [
            {"path": "CLAUDE.md", "bytes": 65536, "because": "decisions move out in F.5", "expires": "2099-01-01"}]))
        text = "# Rules\n" + "x" * 40869 + "\nend\n"
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "CLAUDE.md", text))
        self.assertFalse(denied(out), so + se)


class GovernanceSet(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")

    def tearDown(self):
        cleanup(self.root)

    def set_cfg(self, fn):
        p = self.root / "charter" / "config.json"
        cfg = json.loads(p.read_text())
        fn(cfg)
        p.write_text(json.dumps(cfg))

    def test_default_set_is_todays_list(self):
        cfg = json.loads((self.root / "charter" / "config.json").read_text())
        self.assertEqual(cfg["governance_files"], ["CLAUDE.md", "AGENTS.md", "charter/scope.md", ".claude/rules/*.md"])

    def test_a_configured_file_gets_the_governance_limit(self):
        text = lines(500, "line ")
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "docs/roadmap.md", text))
        self.assertFalse(denied(out), so + se)   # 500 < 800: not governance by default
        self.set_cfg(lambda c: c.__setitem__("governance_files", ["CLAUDE.md", "AGENTS.md", "docs/roadmap.md"]))
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "docs/roadmap.md", text))
        self.assertTrue(denied(out), so + se)
        self.assertIn("400-line", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_a_file_dropped_from_the_set_gets_the_file_limit(self):
        self.set_cfg(lambda c: c.__setitem__("governance_files", ["AGENTS.md"]))
        rc, out, so, se = run_hook(self.root, "pre_tool_gate", write_call(self.root, "CLAUDE.md", lines(500, "line ")))
        self.assertFalse(denied(out), so + se)


class SurveyAndPlan(unittest.TestCase):
    """The survey measures bytes, lists the exceptions open work would need, and the plan offers them."""

    def setUp(self):
        self.root = make_project(with_charter=False)
        (self.root / "CLAUDE.md").write_text("# Rules\n" + "x" * 40869 + "\nend\n")
        (self.root / "app" / "big.py").write_text(lines(900))
        (self.root / ".taskets").mkdir()
        (self.root / ".taskets" / "a.md").write_text("---\nid: a\ntitle: grow it\nstatus: next\n---\n\nTouch app/big.py and CLAUDE.md.\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "big")

    def tearDown(self):
        cleanup(self.root)

    def test_survey_and_plan(self):
        import sys
        from helpers import PKG, REPO
        sys.path.insert(0, str(PKG / ".charter"))
        sys.path.insert(0, str(REPO / "bin"))
        import importlib.machinery, importlib.util
        import charter_survey, charter_plan
        loader = importlib.machinery.SourceFileLoader("charter_pkg", str(REPO / "bin" / "charter-pkg"))
        spec = importlib.util.spec_from_loader("charter_pkg", loader)
        pkg = importlib.util.module_from_spec(spec)
        loader.exec_module(pkg)
        s = charter_survey.survey(self.root, pkg, rehearsal=False, offline=True)
        frozen = {f["path"]: f for f in s["size"]["frozen"]}
        self.assertIn("CLAUDE.md", frozen)            # 3 lines, frozen by bytes
        self.assertEqual(frozen["CLAUDE.md"]["byte_limit"], 32768)
        needed = {e["path"]: e for e in s["exceptions_needed"]}
        self.assertEqual(set(needed), {"CLAUDE.md", "app/big.py"})
        self.assertGreater(needed["CLAUDE.md"]["bytes"], 40869)
        self.assertGreater(needed["app/big.py"]["lines"], 900)
        self.assertTrue(all(e["because"] and e["expires"] for e in needed.values()))
        text = charter_plan.plan(s, "prototype")
        self.assertIn("name exceptions", text)
        self.assertIn("size_exceptions", text)


class SurveyRecentlyChanged(unittest.TestCase):
    """A frozen file no open tasket names but that recent commits keep changing is live code: the survey
    suggests an exception for it too, so the install does not freeze the file everyone is working in."""

    def setUp(self):
        self.root = make_project(with_charter=False)
        (self.root / "app" / "hot.py").write_text(lines(900))
        (self.root / "app" / "cold.py").write_text(lines(900))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "both")
        (self.root / "app" / "hot.py").write_text(lines(901))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "hot again")

    def tearDown(self):
        cleanup(self.root)

    def test_recent_activity_suggests_an_exception(self):
        import sys
        from helpers import PKG, REPO
        sys.path.insert(0, str(PKG / ".charter"))
        sys.path.insert(0, str(REPO / "bin"))
        import importlib.machinery, importlib.util
        import charter_survey
        loader = importlib.machinery.SourceFileLoader("charter_pkg", str(REPO / "bin" / "charter-pkg"))
        spec = importlib.util.spec_from_loader("charter_pkg", loader)
        pkg = importlib.util.module_from_spec(spec)
        loader.exec_module(pkg)
        s = charter_survey.survey(self.root, pkg, rehearsal=False, offline=True)
        needed = {e["path"]: e for e in s["exceptions_needed"]}
        self.assertIn("app/hot.py", needed)
        self.assertNotIn("app/cold.py", needed)          # one commit: an import, not activity
        self.assertIn("2 commits in the last 30 days", needed["app/hot.py"]["because"])
        self.assertEqual([f["path"] for f in s["frozen_recently_changed"]], ["app/hot.py"])

    def survey(self):
        import sys
        from helpers import PKG, REPO
        sys.path.insert(0, str(PKG / ".charter"))
        sys.path.insert(0, str(REPO / "bin"))
        import importlib.machinery, importlib.util
        import charter_survey
        loader = importlib.machinery.SourceFileLoader("charter_pkg", str(REPO / "bin" / "charter-pkg"))
        spec = importlib.util.spec_from_loader("charter_pkg", loader)
        pkg = importlib.util.module_from_spec(spec)
        loader.exec_module(pkg)
        return charter_survey.survey(self.root, pkg, rehearsal=False, offline=True)

    def test_a_backdated_commit_does_not_hide_the_ones_behind_it(self):
        """`git log --since` stops walking at the first commit older than the window; a backdated commit in
        the middle of recent history must not hide the recent commits behind it."""
        import os
        env = dict(clean_env(), GIT_COMMITTER_DATE="2001-01-01T00:00:00", GIT_AUTHOR_DATE="2001-01-01T00:00:00")
        (self.root / "app" / "cold.py").write_text(lines(902))
        git(self.root, "commit", "-q", "-am", "backdated", env=env)
        (self.root / "app" / "cold.py").write_text(lines(903))
        git(self.root, "commit", "-q", "-am", "cold again")
        rc = {f["path"]: f["commits"] for f in self.survey()["frozen_recently_changed"]}
        self.assertEqual(rc.get("app/hot.py"), 2)   # both behind the backdated commit
        self.assertEqual(rc.get("app/cold.py"), 2)   # "both" and "cold again"; the backdated one is outside

    def test_scope_file_stays_in_the_governance_table(self):
        (self.root / "charter").mkdir()
        (self.root / "charter" / "scope.md").write_text("# Scope\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "scope")
        self.assertIn("charter/scope.md", [f["path"] for f in self.survey()["size"]["governance"]])


if __name__ == "__main__":
    unittest.main()
