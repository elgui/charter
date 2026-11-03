"""Owner acceptance is a bound, one-criterion commit, never an agent tick or probe run."""
import json
import unittest

from helpers import charter, cleanup, clean_env, git, run_hook
from test_owner_0_4_8 import project, put, head_message


class OwnerAcceptance(unittest.TestCase):
    def setUp(self):
        self.root = project()
        self.addCleanup(cleanup, self.root)

    def item(self, ac='AC-2'):
        data = json.loads(charter(self.root, 'owner', '--json').stdout)
        return next(i for i in data['items'] if i['key'] == f'owner-line:b1:{ac}')

    def accept(self, item=None, *extra, env=None):
        item = item or self.item()
        return charter(self.root, 'accept', 'b1', item['key'].split(':')[-1],
                       '--expected', item['acceptance']['expected'], *extra, env=env)

    def test_one_owner_confirmation_closes_exact_box_and_records_provenance(self):
        item = self.item()
        self.assertEqual(item['acceptance']['perform'][-4:], ['b1', 'AC-2', '--expected', item['acceptance']['expected']])
        r = self.accept(item, '--note', 'Rows observed', '--trailer', 'Owner-Action: oa-test (dashboard)')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = (self.root / '.taskets/b1.md').read_text()
        self.assertIn('[x] AC-2:', text)
        self.assertIn('[ ] AC-3:', text)
        self.assertIn('owner accepted AC-2: Rows observed', text)
        self.assertIn('Owner-Action: oa-test (dashboard)', head_message(self.root))
        self.assertEqual(git(self.root, 'show', '--format=', '--name-only', 'HEAD').stdout.strip(), '.taskets/b1.md')
        self.assertFalse((self.root / 'rows.txt').exists(), 'accept must not execute probes')

    def test_other_staged_work_is_not_committed(self):
        put(self.root, 'other', 'unrelated\n')
        git(self.root, 'add', 'other')
        r = self.accept()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(git(self.root, 'diff', '--cached', '--name-only').stdout.strip(), 'other')

    def test_changed_criterion_or_branch_refuses_old_confirmation(self):
        for branch in (False, True):
            with self.subTest(branch=branch):
                item = self.item()
                if branch:
                    git(self.root, 'switch', '-c', 'other-branch')
                else:
                    path = self.root / '.taskets/b1.md'
                    path.write_text(path.read_text().replace('rows arrive', 'different rows arrive'))
                    git(self.root, 'add', '.taskets/b1.md')
                    git(self.root, 'commit', '-m', 'change criterion')
                before = git(self.root, 'rev-parse', 'HEAD').stdout
                r = self.accept(item)
                self.assertNotEqual(r.returncode, 0, r.stdout)
                self.assertEqual(git(self.root, 'rev-parse', 'HEAD').stdout, before)
                self.assertIn('criterion or branch changed', r.stderr)

    def test_dirty_target_and_agent_session_refuse(self):
        item = self.item()
        path = self.root / '.taskets/b1.md'
        path.write_text(path.read_text() + '\nlocal work\n')
        r = self.accept(item)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('uncommitted changes', r.stderr)
        git(self.root, 'restore', '.taskets/b1.md')
        env = clean_env()
        env['CLAUDECODE'] = '1'
        r = self.accept(item, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("owner's act", r.stderr)

    def test_separate_boxes_can_be_confirmed_from_same_queue_snapshot(self):
        first, second = self.item(), self.item('AC-3')
        for item in (first, second):
            r = self.accept(item)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = self.accept(first)
        self.assertNotEqual(r.returncode, 0, 'a completed criterion must not commit twice')

    def test_ambiguous_or_nonowner_box_refuses(self):
        item = self.item()
        path = self.root / '.taskets/b1.md'
        text = path.read_text()
        line = next(row for row in text.splitlines() if '[ ] AC-2' in row)
        path.write_text(text.replace(line, line + '\n' + line))
        git(self.root, 'add', '.taskets/b1.md')
        git(self.root, 'commit', '-m', 'duplicate label')
        r = self.accept(item)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('found 2', r.stderr)
        r = charter(self.root, 'accept', 'b1', 'AC-5', '--expected', 'anything')
        self.assertNotEqual(r.returncode, 0)

    def test_dry_run_and_rejected_commit_preserve_target(self):
        item = self.item()
        path = self.root / '.taskets/b1.md'
        before = path.read_bytes(), git(self.root, 'rev-parse', 'HEAD').stdout
        r = self.accept(item, '--dry-run')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((path.read_bytes(), git(self.root, 'rev-parse', 'HEAD').stdout), before)
        hook = self.root / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        git(self.root, 'config', 'core.hooksPath', '.git/hooks')
        r = self.accept(item)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((path.read_bytes(), git(self.root, 'rev-parse', 'HEAD').stdout), before)
        self.assertEqual(git(self.root, 'status', '--porcelain').stdout, '')

    def test_hook_denies_acceptance_from_any_agent_tool_call(self):
        for command in ('python3 .charter/bin/charter accept b1 AC-2 --expected abc',
                        "python3 '.charter/bin/charter' --root . accept b1 AC-2 --expected abc",
                        "sh -c 'python3 .charter/bin/charter accept b1 AC-2 --expected abc'"):
            code, out, stdout, stderr = run_hook(self.root, 'chain_gate', {
                'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': command}})
            self.assertEqual(out.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny', stdout + stderr)

    def test_duplicate_unit_identity_and_terminal_unit_refuse(self):
        item = self.item()
        original = self.root / '.taskets/b1.md'
        copy = self.root / '.taskets/duplicate.md'
        copy.write_bytes(original.read_bytes())
        r = self.accept(item)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('ambiguous', r.stderr)
        copy.unlink()
        original.write_text(original.read_text().replace('status: next', 'status: parked'))
        git(self.root, 'add', '.taskets/b1.md')
        git(self.root, 'commit', '-m', 'park unit')
        r = self.accept(item)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('already parked', r.stderr)

    def test_quoted_mentions_of_acceptance_do_not_block_documentation(self):
        for command in ("git commit -m 'Document charter accept'", "rg 'charter accept' docs"):
            code, out, stdout, stderr = run_hook(self.root, 'chain_gate', {
                'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': command}})
            self.assertNotEqual(out.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny', stdout + stderr)
