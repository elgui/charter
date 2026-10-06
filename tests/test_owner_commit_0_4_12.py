"""Charter 0.4.12: the owner commits a handover with one short line, `CHARTER_OWNER=1 python3 <root>/.charter/bin/charter
owner commit`, instead of a command an agent assembles (docs/design/owner-handover.md). Motivated by leCRM's upgrade to
0.4.11 on 2026-10-06 (docs/bugs/2026-10-06-owner-commit-not-one-line.md): the handover was a 17-path command, the
agent's heredoc block did not paste, and the classifier refused the agent's own commit even after "do it yourself".
`charter handover` and the installer record the handover in the git directory; the owner's line commits it."""
import json
import shlex
import subprocess
import unittest

from helpers import charter, cleanup, clean_env, git, make_project, run_hook
from test_handover_0_4_5 import behind, engine_line, handover_record, owner_command, staged
from test_migration import pkg

SETTINGS = '{"hooks": {}}\n'


def run_line(line, cwd="/", **env):
    """The owner's line as `!` runs it in a Claude Code prompt (CLAUDECODE=1), or as a terminal does (in_session=False)."""
    in_session = env.pop("in_session", True)
    e = clean_env(**({"CLAUDECODE": "1"} if in_session else {}), **env)
    return subprocess.run(["bash", "-c", line], capture_output=True, text=True, cwd=str(cwd), env=e)


class OwnerCommit(unittest.TestCase):
    def setUp(self):
        self.root = make_project(track="prototype")
        git(self.root, "switch", "-q", "-c", "work")
        (self.root / ".claude" / "settings.json").write_text(SETTINGS)
        (self.root / "notes.md").write_text("the agent's\n")
        git(self.root, "add", ".claude/settings.json", "notes.md")

    def tearDown(self):
        cleanup(self.root)

    def hand_over(self, *args):
        r = charter(self.root, "handover", *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return owner_command(r.stdout)

    def head(self):
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def test_the_line_is_short_and_the_record_is_data_in_the_git_dir(self):
        line = self.hand_over("-m", "Settings: drop the hooks")
        self.assertEqual(line, engine_line(self.root))
        self.assertEqual(shlex.split(line)[0], "CHARTER_OWNER=1")   # the switch is the owner's to type, on the line
        p = self.root / ".git" / "charter" / "handover.json"
        self.assertNotIn("CHARTER_OWNER", p.read_text())            # and in no file
        self.assertNotIn("handover", git(self.root, "status", "--porcelain", "--ignored").stdout)
        rec = handover_record(self.root)
        self.assertEqual((rec["branch"], rec["message"], rec["paths"], rec["by"]),
                         ("work", "Settings: drop the hooks", [".claude/settings.json", "notes.md"], "charter handover"))

    def test_the_line_commits_the_handover_as_the_owner_from_any_directory(self):
        line = self.hand_over("-m", "Settings: drop the hooks")
        (self.root / "later.md").write_text("staged after the handover\n")
        git(self.root, "add", "later.md")
        r = run_line(line)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(git(self.root, "show", "-s", "--format=%s", "HEAD").stdout.strip(), "Settings: drop the hooks")
        self.assertEqual(sorted(git(self.root, "show", "--name-only", "--format=", "HEAD").stdout.split()), [".claude/settings.json", "notes.md"])
        self.assertEqual(staged(self.root), ["later.md"])
        self.assertIn("staged but not handed over, left out (1): later.md", r.stdout)
        self.assertIn("charter check: 0 blocking", r.stdout + r.stderr)   # the gate ran, and the switch lifted the owner-only check
        self.assertIsNone(handover_record(self.root))

    def test_without_the_switch_inside_claude_code_it_is_refused(self):
        line = self.hand_over()
        before = self.head()
        r = run_line(line.replace("CHARTER_OWNER=1 ", ""))
        self.assertEqual(r.returncode, 1)
        self.assertIn("An agent never runs this", r.stderr)
        self.assertEqual(self.head(), before)
        self.assertIsNotNone(handover_record(self.root))

    def test_it_never_sets_the_switch_itself(self):
        # from the owner's own terminal, without the switch, the gate cannot tell them from the owner and only warns:
        # the warning shows the verb left the switch to the line
        line = self.hand_over()
        r = run_line(line.replace("CHARTER_OWNER=1 ", ""), in_session=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("charter/protected warn", r.stdout + r.stderr)

    def test_an_edit_after_the_handover_is_named_and_committed_as_it_is_now(self):
        line = self.hand_over()
        edited = '{"hooks": {}, "env": {}}\n'
        (self.root / ".claude" / "settings.json").write_text(edited)   # the owner's edit, as install step 8 asks of config.json
        r = run_line(line)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("changed since the handover, committed as they are now (1): .claude/settings.json", r.stdout)
        self.assertEqual(git(self.root, "show", "HEAD:.claude/settings.json").stdout, edited)

    def test_another_branch_is_refused_and_the_record_kept(self):
        line = self.hand_over()
        git(self.root, "switch", "-q", "-c", "other")
        r = run_line(line)
        self.assertEqual(r.returncode, 1)
        self.assertIn("handed over on branch work, and this checkout is on other", r.stderr)
        git(self.root, "switch", "-q", "work")
        self.assertEqual(run_line(line).returncode, 0)

    def test_a_handover_committed_another_way_is_stale(self):
        line = self.hand_over()
        git(self.root, "commit", "-qm", "by hand", env=clean_env(CHARTER_OWNER="1"))
        (self.root / ".claude" / "settings.json").write_text('{"hooks": {"x": []}}\n')
        git(self.root, "add", ".claude/settings.json")
        before = self.head()
        r = run_line(line)
        self.assertEqual(r.returncode, 1)
        self.assertIn("changed in a commit since the handover", r.stderr)
        self.assertEqual(self.head(), before)
        self.assertIsNone(handover_record(self.root))
        nxt = charter(self.root, "next").stdout   # the queue does not offer the line for it either
        self.assertIn("`python3 .charter/bin/charter handover` records it", nxt)

    def test_an_unrelated_commit_since_leaves_it_standing(self):
        line = self.hand_over()
        (self.root / "app" / "billing.py").write_text("def invoice(a):\n    return a * 3\n")
        git(self.root, "commit", "-qm", "the agent's own work", "--", "app/billing.py")
        r = run_line(line)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_nothing_handed_over(self):
        git(self.root, "reset", "-q")
        self.assertEqual(charter(self.root, "handover").stdout.strip(), "nothing staged")   # and it drops any record
        r = run_line(engine_line(self.root))
        self.assertEqual(r.returncode, 1)
        self.assertIn("nothing is handed over", r.stderr)

    def test_no_owner_only_change_drops_the_record(self):
        self.hand_over()
        git(self.root, "reset", "-q", ".claude/settings.json")
        out = charter(self.root, "handover").stdout
        self.assertIn("so an agent commits them", out)
        self.assertIsNone(handover_record(self.root))

    def test_the_queue_shows_the_line_once_handed_over(self):
        def item():
            q = json.loads(charter(self.root, "owner", "--json").stdout)
            return next(i for i in q["items"] if i["key"] == "staged")
        self.assertEqual((item()["run"], item()["perform"]), ([], None))
        line = self.hand_over()
        engine = str(self.root / ".charter" / "bin" / "charter")
        self.assertEqual(item()["run"], [line])
        self.assertEqual(item()["perform"], ["env", "CHARTER_OWNER=1", "python3", engine, "owner", "commit"])
        self.assertIn("\n" + line + "\n", charter(self.root, "next").stdout)   # alone on its line

    def test_owner_run_without_a_chain_names_the_line(self):
        line = self.hand_over()
        r = charter(self.root, "owner", "run")
        self.assertEqual(r.returncode, 1)
        self.assertIn(line, r.stderr)

    def test_the_hook_denies_it_to_an_agent(self):
        for cmd in (shlex.split(engine_line(self.root))[1:], ["python3", ".charter/bin/charter", "--root", ".", "owner", "commit"]):
            code, out, so, se = run_hook(self.root, "chain_gate", {"hook_event_name": "PreToolUse", "session_id": "any",
                                                                  "tool_name": "Bash", "tool_input": {"command": shlex.join(cmd)}})
            reason = json.loads(so)["hookSpecificOutput"]["permissionDecisionReason"]
            self.assertIn("`charter owner commit` is the owner's command", reason, cmd)
        code, out, so, se = run_hook(self.root, "chain_gate", {"hook_event_name": "PreToolUse", "session_id": "any",
                                                              "tool_name": "Bash", "tool_input": {"command": "python3 .charter/bin/charter handover"}})
        self.assertEqual(so.strip(), "")


class Worktree(unittest.TestCase):
    """leCRM's case: the upgrade is staged in a worktree while the session, and the owner's `!`, sit in the main checkout."""
    def setUp(self):
        self.root = make_project(track="prototype")
        self.wt = self.root.parent / (self.root.name + "-wt")
        git(self.root, "worktree", "add", "-q", "-b", "charter-up", str(self.wt))
        (self.wt / ".claude" / "settings.json").write_text(SETTINGS)
        git(self.wt, "add", ".claude/settings.json")

    def tearDown(self):
        git(self.root, "worktree", "remove", "--force", str(self.wt), check=False)
        cleanup(self.wt)
        cleanup(self.root)

    def test_the_line_commits_the_worktree_from_the_main_checkout(self):
        line = owner_command(charter(self.wt, "handover").stdout)
        self.assertEqual(line, engine_line(self.wt))
        main_head = git(self.root, "rev-parse", "HEAD").stdout.strip()
        r = run_line(line, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(git(self.root, "rev-parse", "main").stdout.strip(), main_head)
        self.assertEqual(git(self.wt, "show", "--name-only", "--format=", "charter-up").stdout.split(), [".claude/settings.json"])


class FleetCommit(unittest.TestCase):
    """`fleet --commit` commits the handovers `fleet --upgrade` recorded, and names any other one instead."""
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.dir = Path(tempfile.mkdtemp(prefix="charter-fleet-"))
        self.alpha, self.beta = self.dir / "alpha", self.dir / "beta"
        make_project(track="prototype").rename(self.alpha)
        behind(self.alpha)
        make_project(track="prototype").rename(self.beta)
        git(self.beta, "switch", "-q", "-c", "work")
        (self.beta / ".claude" / "settings.json").write_text(SETTINGS)
        git(self.beta, "add", ".claude/settings.json")
        self.beta_line = owner_command(charter(self.beta, "handover").stdout)

    def tearDown(self):
        cleanup(self.dir)

    def test_it_commits_fleets_handovers_and_names_the_others(self):
        r = pkg("fleet", "--root", str(self.dir), "--upgrade")
        self.assertIn("Waiting on the owner: 1 project(s), one line.", r.stdout)
        beta_head = git(self.beta, "rev-parse", "HEAD").stdout
        c = run_line(owner_command(r.stdout))
        self.assertEqual(c.returncode, 0, c.stdout + c.stderr)
        self.assertEqual(git(self.alpha, "show", "-s", "--format=%s", "HEAD").stdout.strip(),
                         "charter " + (self.alpha / "charter" / "VERSION").read_text().strip())
        self.assertEqual(git(self.beta, "rev-parse", "HEAD").stdout, beta_head)
        self.assertIn("beta: a handover from `charter handover` waits too, left alone; its own line:\n" + self.beta_line, c.stdout)
        self.assertIsNotNone(handover_record(self.beta))


if __name__ == "__main__":
    unittest.main()
