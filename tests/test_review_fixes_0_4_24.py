"""Regressions verified by independent review of the 0.4.24 release."""
import importlib.machinery
import importlib.util
import json
import os
import shlex
import signal
import subprocess
import sys
import time
import unittest
from unittest import mock

from helpers import PKG, REPO, UNIT, charter, cleanup, git, make_project
from test_review_regressions import commit_all, set_config

sys.path.insert(0, str(PKG / '.charter'))
import checks
import lib
import owner


class ProjectCase(unittest.TestCase):
    def setUp(self):
        self.root = make_project()
        self.addCleanup(cleanup, self.root)


class OwnerReviewRegressions(ProjectCase):
    def test_legacy_dash_free_text_remains_an_owner_check(self):
        for separator in ('—', '–'):
            for words in ('confirm it is live', 'checks rows', 'doing the deployment'):
                with self.subTest(separator=separator, words=words):
                    line = f'- [ ] AC-2: delivery {separator} owner: {words}'
                    text = UNIT.replace('## Evidence', line + '\n\n## Evidence')
                    path = self.root / '.taskets/u1.md'
                    path.write_text(text)
                    items = owner.owner_lines(self.root, 'u1', lib.taskets(self.root)['u1'], owner.legacy_re(self.root, lib.load_config(self.root)))
                    self.assertTrue(any(i['key'] == 'owner-line:u1:AC-2' and i['kind'] == 'check' for i in items))
                    self.assertEqual(checks.owner_line_changes(text, text.replace('[ ] AC-2', '[x] AC-2')), ['AC-2'])

    def test_physical_owner_confirmation_ticks_only_the_confirmed_row(self):
        for char in ('\u2028', '\u2029', '\x85', '\x0b', '\x0c', '\x1c', '\x1d', '\x1e'):
            with self.subTest(char=repr(char)):
                text = UNIT.replace('Client wants retries in /health.', 'Pasted ' + char + ' context.')
                text = text.replace('## Evidence', '- [ ] AC-2: delivery — owner: do\n\n## Evidence')
                path = self.root / '.taskets/u1.md'
                path.write_text(text)
                commit_all(self.root, 'fixture: pasted context')
                cfg = lib.load_config(self.root)
                item = owner.owner_lines(self.root, 'u1', lib.taskets(self.root)['u1'], owner.legacy_re(self.root, cfg))[0]
                # Capture the proposed edit; no owner action or commit is performed.
                with mock.patch.object(owner, '_commit', return_value=0) as proposed:
                    owner._accept(self.root, cfg, 'u1', 'AC-2', item['acceptance']['expected'], None, None, True)
                result = proposed.call_args.args[1]['.taskets/u1.md']
                self.assertIn('[x] AC-2:', result)
                self.assertNotIn('[x] AC-1:', result)
                self.assertIn('owner accepted AC-2', result)
                self.assertIn('Pasted ' + char + ' context.', result)

    def test_unicode_inside_a_checkbox_agrees_with_owner_and_edit_gates(self):
        for char in ('\u2028', '\u2029', '\x85', '\x0b', '\x0c', '\x1c', '\x1d', '\x1e'):
            with self.subTest(char=repr(char)):
                text = UNIT.replace('status: next', 'status: in-progress')
                text = text.replace('## Evidence', '- [ ] AC-2: pasted' + char + ' delivery — owner: do\n\n## Evidence')
                ticked = text.replace('[ ] AC-2', '[x] AC-2')
                self.assertEqual(checks.owner_line_changes(text, ticked), ['AC-2'])
                self.assertEqual(checks.owner_line_kinds(text, ticked), {'AC-2': 'structural'})
                edited = text.replace('delivery — owner:', 'different delivery — owner:')
                self.assertTrue(checks.check_acceptance_change(text, edited, '.taskets/u1.md'))


class DeletedPathRegressions(ProjectCase):
    def test_imported_done_documents_are_new_closures_in_commit_and_ci(self):
        for source in ('notes/imported.md', '.taskets/imported.txt'):
            with self.subTest(source=source):
                root = make_project()
                self.addCleanup(cleanup, root)
                old = root / source
                old.parent.mkdir(exist_ok=True)
                old.write_text('---\nid: imported\nstatus: done\n---\n\n## Context\n\nOld notes, not a validated tasket.\n')
                commit_all(root, 'fixture: non-tasket done document')
                base = git(root, 'rev-parse', 'HEAD').stdout.strip()
                git(root, 'mv', source, '.taskets/imported.md')
                self.assertEqual(checks.rename_sources(root).get('.taskets/imported.md'), source)
                result = charter(root, 'check', '--staged', '--done', '--no-probe')
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('Acceptance', result.stdout)
                commit_all(root, 'fixture: imported document')
                result = charter(root, 'check', '--all', '--done', '--base', base, '--no-probe')
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('Acceptance', result.stdout)

    def test_heuristic_rename_of_a_different_id_cannot_inherit_done_status(self):
        path = self.root / '.taskets/u1.md'
        before = UNIT.replace('id: u1', 'id: previous').replace('status: next', 'status: done')
        before = before.replace('[ ] AC-1', '[x] AC-1').replace('## Evidence', '## Evidence\n\n- $ echo done')
        path.write_text(before)
        commit_all(self.root, 'fixture: valid prior done unit')
        base = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        git(self.root, 'rm', '.taskets/u1.md')
        after = before.replace('id: previous', 'id: different').replace('[x] AC-1', '[ ] AC-1').replace('- $ echo done', '')
        (self.root / '.taskets/different.md').write_text(after)
        git(self.root, 'add', '.taskets/different.md')
        self.assertEqual(checks.rename_sources(self.root).get('.taskets/different.md'), '.taskets/u1.md')
        result = charter(self.root, 'check', '--staged', '--done', '--no-probe')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('unchecked', result.stdout)
        commit_all(self.root, 'fixture: different new done unit')
        result = charter(self.root, 'check', '--all', '--done', '--base', base, '--no-probe')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('unchecked', result.stdout)

    def test_renamed_started_criterion_changes_still_need_a_log_in_commit_and_ci(self):
        for logged in (False, True):
            with self.subTest(logged=logged):
                root = make_project()
                self.addCleanup(cleanup, root)
                path = root / '.taskets/u1.md'
                path.write_text(UNIT.replace('status: next', 'status: in-progress'))
                commit_all(root, 'fixture: started unit')
                base = git(root, 'rev-parse', 'HEAD').stdout.strip()
                git(root, 'mv', '.taskets/u1.md', '.taskets/renamed.md')
                renamed = root / '.taskets/renamed.md'
                text = renamed.read_text().replace('retries == 3', 'retries == 4')
                if logged:
                    text += '\n- 2026-11-05 AC-1 revised with the implementation\n'   # 0.4.26: the dated line names the criterion
                renamed.write_text(text)
                git(root, 'add', '.taskets/renamed.md')
                result = charter(root, 'check', '--staged', '--done', '--no-probe')
                self.assertEqual(result.returncode, 0 if logged else 1, result.stdout + result.stderr)
                commit_all(root, 'fixture: renamed criterion')
                result = charter(root, 'check', '--all', '--done', '--base', base, '--no-probe')
                self.assertEqual(result.returncode, 0 if logged else 1, result.stdout + result.stderr)

    def test_deleted_and_renamed_ordinary_units_need_no_impossible_log(self):
        for status in ('in-progress', 'done', 'deleted'):
            for rename in (False, True):
                with self.subTest(status=status, rename=rename):
                    root = make_project()
                    self.addCleanup(cleanup, root)
                    path = root / '.taskets/u1.md'
                    text = UNIT.replace('status: next', 'status: ' + status)
                    if status == 'done':
                        text = text.replace('[ ] AC-1', '[x] AC-1').replace('## Evidence', '## Evidence\n\n- $ echo done')
                    path.write_text(text)
                    commit_all(root, 'fixture: ordinary unit')
                    if rename:
                        git(root, 'mv', '.taskets/u1.md', '.taskets/renamed.md')
                    else:
                        git(root, 'rm', '.taskets/u1.md')
                    result = charter(root, 'check', '--staged', '--done', '--no-probe')
                    self.assertNotIn('no new `## Log`', result.stdout, result.stdout)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_tracked_unit_still_requires_acceptance_change_log(self):
        path = self.root / '.taskets/u1.md'
        path.write_text(UNIT.replace('status: next', 'status: in-progress'))
        commit_all(self.root, 'fixture: started unit')
        path.write_text('')
        git(self.root, 'add', '.taskets/u1.md')
        result = charter(self.root, 'check', '--staged', '--done', '--no-probe')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('no new `## Log`', result.stdout)

    def test_deleting_owner_criteria_stays_owner_only(self):
        path = self.root / '.taskets/u1.md'
        path.write_text(UNIT.replace('## Evidence', '- [ ] AC-2: delivery — owner: do\n\n## Evidence'))
        commit_all(self.root, 'fixture: owner criterion')
        git(self.root, 'rm', '.taskets/u1.md')
        result = charter(self.root, 'check', '--staged', '--protected', '--no-probe', env={'CLAUDECODE': '1'})
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('AC-2', result.stdout)

    def test_owner_only_type_change_reaches_the_gate(self):
        base = git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        path = self.root / 'charter/scope.md'
        (self.root / 'scope-copy.md').write_text(path.read_text())
        path.unlink()
        path.symlink_to('../scope-copy.md')
        git(self.root, 'add', 'charter/scope.md')
        self.assertIn('charter/scope.md', checks.staged_paths(self.root))
        result = charter(self.root, 'check', '--staged', '--protected', '--no-probe', env={'CLAUDECODE': '1'})
        self.assertNotEqual(result.returncode, 0, result.stdout)
        commit_all(self.root, 'fixture: type change for CI')
        self.assertIn('charter/scope.md', checks.changed_paths(self.root, base))


class ProbeCleanupRegressions(ProjectCase):
    def test_escaped_pipe_holder_cannot_make_timeout_cleanup_wait_forever(self):
        child = "import os,time; from pathlib import Path; Path('escaped.pid').write_text(str(os.getpid())); time.sleep(4)"
        parent = 'import subprocess,sys; subprocess.Popen([sys.executable,"-c",' + repr(child) + '],start_new_session=True).wait()'
        started = time.monotonic()
        try:
            record, _ = checks.probe_record(self.root, 'AC-1', shlex.join([sys.executable, '-c', parent]), 1)
            self.assertEqual(record['outcome'], 'timeout')
            self.assertTrue((self.root / 'escaped.pid').exists(), 'the escaping descendant must start to exercise cleanup')
            self.assertLess(time.monotonic() - started, 3)
        finally:
            pid = self.root / 'escaped.pid'
            if pid.exists():
                try:
                    os.kill(int(pid.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_keyboard_interrupt_reaps_the_isolated_probe(self):
        real_popen = subprocess.Popen
        processes = []
        def start(*args, **kwargs):
            proc = real_popen(*args, **kwargs)
            processes.append(proc)
            proc.communicate = mock.Mock(side_effect=KeyboardInterrupt)
            return proc
        try:
            with mock.patch.object(checks.subprocess, 'Popen', side_effect=start):
                with self.assertRaises(KeyboardInterrupt):
                    checks._run_probe(self.root, 'sleep 20', 5, runner=[])
            # the probe is the process whose output charter reads; from 0.4.27 a watcher starts beside it
            probes = [proc for proc in processes if proc.stdout is not None]
            self.assertEqual(len(probes), 1)
            self.assertIsNotNone(probes[0].poll())
        finally:
            for proc in processes:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
                for stream in (proc.stdin, proc.stdout, proc.stderr):
                    if stream is not None:
                        stream.close()


class BoundedAndAnchorRegressions(ProjectCase):
    def test_interrupted_bounded_capture_reaps_its_isolated_producer(self):
        real_popen = subprocess.Popen
        processes = []
        selector = lib.selectors.DefaultSelector()
        def start(*args, **kwargs):
            proc = real_popen(*args, **kwargs)
            processes.append(proc)
            return proc
        try:
            with mock.patch.object(lib.subprocess, 'Popen', side_effect=start), \
                 mock.patch.object(lib.selectors, 'DefaultSelector', return_value=selector), \
                 mock.patch.object(selector, 'select', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    lib.run_bounded([sys.executable, '-c', 'import time; time.sleep(20)'], 100)
            self.assertIsNotNone(processes[0].poll())
        finally:
            selector.close()
            for proc in processes:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
                proc.stdout.close()
                proc.stderr.close()

    def test_deadline_still_applies_after_both_pipes_close(self):
        marker = self.root / 'late-producer'
        ready = self.root / 'producer-ready'
        script = f'import os,time; from pathlib import Path; Path({str(ready)!r}).write_text("ready"); os.close(1); os.close(2); time.sleep(2); Path({str(marker)!r}).write_text("late")'
        result = lib.run_bounded([sys.executable, '-c', script], 100, timeout=1)
        self.assertTrue(ready.exists(), 'the producer must start to exercise pipe EOF')
        self.assertEqual(result.returncode, 124)
        self.assertFalse(marker.exists())
        self.assertFalse(result.truncated)

    def test_ref_line_anchors_use_physical_newlines(self):
        for contents in ('a\u2028b\n', 'a\x0cb', 'a\rb\n', 'a\rb', 'a\r\nb\r\n'):
            with self.subTest(contents=repr(contents)):
                (self.root / 'physical.txt').write_text(contents)
                commit_all(self.root, 'fixture: physical line')
                self.assertTrue(checks._resolves(self.root, 'fileline', 'physical.txt', '1', ref='HEAD'))
                expected = contents.count('\n') > 1
                self.assertEqual(checks._resolves(self.root, 'fileline', 'physical.txt', '2', ref='HEAD'), expected)


loader = importlib.machinery.SourceFileLoader('review_probe_watcher', str(REPO / 'bin/charter-delegate'))
spec = importlib.util.spec_from_loader(loader.name, loader)
watcher = importlib.util.module_from_spec(spec)
loader.exec_module(watcher)


class WatcherProbeRegressions(ProjectCase):
    def item(self, command):
        return {'probes': [{'path': '.taskets/u1.md', 'key': 'AC-2', 'probe': command}]}

    def test_reruns_use_the_configured_runner_and_mask_failure_reasons(self):
        runner = self.root / 'probe-env'
        runner.write_text('#!/bin/sh\nexport REVIEW_PROBE_ENV=selected\nexec "$@"\n')
        runner.chmod(0o755)
        set_config(self.root, probes={'runner': ['./probe-env']})
        self.assertEqual(watcher.run_probes(self.root, self.item('test "$REVIEW_PROBE_ENV" = selected'), 3), '')
        secret = 'gh' + 'p_' + 'A' * 36
        reason = watcher.run_probes(self.root, self.item('printf %s ' + secret + '; exit 1'), 3)
        self.assertTrue(reason)
        self.assertNotIn(secret, reason)
        self.assertIn('REDACTED', reason)

    def test_invalid_runner_refuses_to_run_under_default_environment(self):
        set_config(self.root, probes={'runner': ['']})
        reason = watcher.run_probes(self.root, self.item('touch should-not-run'), 3)
        self.assertTrue(reason)
        self.assertFalse((self.root / 'should-not-run').exists())

    def test_timeout_reason_masks_the_command(self):
        secret = 'gh' + 'p_' + 'A' * 36
        reason = watcher.run_probes(self.root, self.item('sleep 3; printf %s ' + secret), 0.1)
        self.assertIn('did not finish', reason)
        self.assertNotIn(secret, reason)
        self.assertIn('REDACTED', reason)


if __name__ == '__main__':
    unittest.main()
