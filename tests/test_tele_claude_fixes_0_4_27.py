"""0.4.27: three regressions tele-claude's review of its 0.4.26 upgrade found (tele-claude PR #161).

#52: a Log line dated with an ISO timestamp (`- 2026-11-09T12:00:00Z ...`, what `charter accept` writes) is a dated line.
#51: `charter owner` reads every open unit's history in one pass, not one `git log --follow` per unit; a unit written
by copying another does not inherit the other's history.
Probes: a probe does not outlive charter when a caller kills charter's process group (tele-claude's
tests/test_checker_core.py::test_total_timeout_kills_the_probes_too).
Each test fails on the package at e6f413f, except two guards of what must not change: what is not a date, and a
probe's exit status, output and runner failure as charter reads them."""
import datetime as dt
import os
import signal
import subprocess
import sys
import time
import unittest
from unittest import mock

from helpers import make_project, charter, git, cleanup, UNIT, PKG, clean_env

sys.path.insert(0, str(PKG / ".charter"))
import checks  # noqa: E402
import lib  # noqa: E402
import owner  # noqa: E402


def commit_all(root, msg):
    git(root, "add", "-A")
    return git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", msg, check=False)


OWNER_LINE = "- [ ] AC-2: every screen shows Skip — owner: check — probe: `grep -q Skip app/health.py`"
WEAKER_LINE = "- [ ] AC-2: the first screen shows Skip — owner: check — probe: `grep -q Skip app/health.py`"


def unit(uid="u1", status="now"):
    text = UNIT.replace("id: u1", f"id: {uid}").replace("status: next", f"status: {status}")
    return text.replace("## Evidence", OWNER_LINE + "\n\n## Evidence")


def add_log(text, line):
    return text.replace("- 2026-09-11 14:00 created\n", "- 2026-09-11 14:00 created\n" + line + "\n")


class IsoDatedLogLine(unittest.TestCase):
    """#52."""

    def test_an_iso_timestamped_line_naming_the_criterion_passes(self):
        running = unit()
        weaker = add_log(running.replace(OWNER_LINE, WEAKER_LINE), "- 2026-11-09T12:00:00Z: AC-2 reworded: one screen")
        self.assertEqual(checks.check_acceptance_change(running, weaker, ".taskets/u1.md"), [])

    def test_the_receipt_charter_accept_writes_is_dated(self):
        stamp = dt.datetime(2026, 11, 9, 12, tzinfo=dt.timezone.utc).isoformat(timespec="seconds")
        self.assertTrue(checks.DATED_LOG_RE.match(f"- {stamp} owner accepted AC-2"))
        self.assertTrue(checks.DATED_LOG_RE.match("- 2026-10-26T15:52:38.960720+00:00: AC-1 tightened"))

    def test_what_is_not_a_date_still_is_not(self):
        for line in ("- 2026-11-09Tx", "- 2026-11-091 AC-2", "- x 2026-11-09", "2026-11-09 AC-2"):
            self.assertFalse(checks.DATED_LOG_RE.match(line), line)


class OwnerQueueHistory(unittest.TestCase):
    """#51: one history pass for the whole queue, the same words as one pass per unit."""

    def setUp(self):
        self.root = make_project()
        self.addCleanup(cleanup, self.root)
        t = self.root / ".taskets"
        # u1: planned, started, reworded
        (t / "u1.md").write_text(unit("u1", "next"))
        commit_all(self.root, "u1 planned")
        (t / "u1.md").write_text(unit("u1", "now"))
        commit_all(self.root, "u1 starts")
        (t / "u1.md").write_text(add_log(unit("u1", "now").replace(OWNER_LINE, WEAKER_LINE), "- 2026-11-09 AC-2 reworded"))
        commit_all(self.root, "u1 AC-2 reworded")
        # u2: started, renamed inside the units directory, then reworded under its new name
        (t / "u2.md").write_text(unit("u2", "now"))
        commit_all(self.root, "u2 starts")
        git(self.root, "mv", ".taskets/u2.md", ".taskets/u2-renamed.md")
        commit_all(self.root, "u2 renamed")
        (t / "u2-renamed.md").write_text(add_log(unit("u2", "now").replace(OWNER_LINE, WEAKER_LINE), "- 2026-11-09 AC-2 reworded"))
        commit_all(self.root, "u2 AC-2 reworded")
        # u3: never started
        (t / "u3.md").write_text(unit("u3", "next"))
        commit_all(self.root, "u3 planned")
        self.paths = [".taskets/u1.md", ".taskets/u2-renamed.md", ".taskets/u3.md"]

    def test_one_pass_gives_the_words_one_pass_per_unit_gives(self):
        many = checks.words_when_started_many(self.root, self.paths)
        for p in self.paths:
            self.assertEqual(many[p], checks.words_when_started(self.root, p), p)
        self.assertEqual(many[".taskets/u2-renamed.md"]["AC-2"], OWNER_LINE[len("- [ ] "):])
        self.assertEqual(many[".taskets/u3.md"], {})
        histories = checks.unit_histories(self.root, self.paths)
        for p in self.paths:
            self.assertEqual(histories[p], checks.unit_history(self.root, p), p)

    def test_the_queue_does_not_walk_history_per_unit(self):
        cfg = lib.load_config(self.root)
        units = lib.taskets(self.root)
        with mock.patch.object(checks, "unit_history", wraps=checks.unit_history) as per_unit:
            items = owner.queue(self.root, cfg, units, {})
        self.assertEqual(per_unit.call_count, 0)
        previous = {i["key"]: i.get("previous") for i in items if i["key"].startswith("owner-line:")}
        self.assertEqual(previous.get("owner-line:u1:AC-2"), OWNER_LINE[len("- [ ] "):])
        self.assertEqual(previous.get("owner-line:u2:AC-2"), OWNER_LINE[len("- [ ] "):])
        self.assertIsNone(previous.get("owner-line:u3:AC-2"))

    def test_a_unit_copied_from_a_started_one_has_not_left_planning(self):
        t = self.root / ".taskets"
        (t / "u4.md").write_text((t / "u1.md").read_text().replace("id: u1", "id: u4").replace("status: now", "status: next"))
        commit_all(self.root, "u4 planned, copied from u1")
        self.assertFalse(checks.left_planning(self.root, ".taskets/u4.md"))
        self.assertEqual(checks.words_when_started(self.root, ".taskets/u4.md"), {})
        reworded = (t / "u4.md").read_text().replace(WEAKER_LINE, OWNER_LINE)
        (t / "u4.md").write_text(reworded)
        git(self.root, "add", "-A")
        r = charter(self.root, "check", "--staged")
        self.assertEqual(r.returncode, 0, r.stdout)


class ProbeOutlivesNoCaller(unittest.TestCase):
    """A caller that kills charter's process group kills the probes charter started."""

    def setUp(self):
        self.root = make_project()
        self.addCleanup(cleanup, self.root)

    def test_killing_charters_group_kills_the_probe(self):
        marker = self.root / "survivor"
        text = UNIT.replace("status: next", "status: now").replace(
            "## Evidence", f"- [ ] AC-2: slow — probe: `sleep 2 && touch {marker}`\n\n## Evidence")
        (self.root / ".taskets" / "u1.md").write_text(text)
        commit_all(self.root, "u1")
        proc = subprocess.Popen([sys.executable, str(self.root / ".charter" / "bin" / "charter"), "--root", str(self.root),
                                 "probe", "u1", "--timeout", "30"], cwd=str(self.root), env=clean_env(),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        time.sleep(1.0)        # past AC-1, inside AC-2's sleep
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        time.sleep(2.5)
        self.assertFalse(marker.exists(), "a probe outlived charter")

    def test_the_probe_s_exit_is_charter_s_reading(self):
        self.assertEqual(checks._run_probe(self.root, "echo out; echo err >&2; exit 3", 10, runner=[]).returncode, 3)
        r = checks._run_probe(self.root, "echo out; echo err >&2; exit 3", 10, runner=[])
        self.assertEqual((r.stdout, r.stderr), ("out\n", "err\n"))
        self.assertEqual(checks._run_probe(self.root, "kill -TERM $$", 10, runner=[]).returncode, -signal.SIGTERM)
        r = checks._run_probe(self.root, "true", 10, runner=[str(self.root / "no-such-runner")])
        self.assertEqual(r.returncode, 127)
        self.assertIn("probe runner could not start", r.stderr)


if __name__ == "__main__":
    unittest.main()
