# Two sessions in one clone share one active unit: the later `unit start` re-attributes the other session's edits

- Seen: 2026-10-02, hermes-custom at 1bed62e, charter 0.4.6
- Status: open

## What happened

Session A ran `python3 .charter/bin/charter unit start 20261002-1450-bonito-model-ab` at 14:50 and printed
`active unit: 20261002-1450-bonito-model-ab — …`. Within the same minute another Claude Code session in the same clone
(merging `builder-lane`, commit 1bed62e) made `20260928-1935-builder-lane` active. From then on every Write in
session A, to files inside its own unit's `perimeter:`, drew:

```
charter: charter/perimeter warn [ops/model-ab/run.ts]: ops/model-ab/run.ts is outside the perimeter of unit
20260928-1935-builder-lane and has no note Override: add `- ops/model-ab/run.ts: <why>` under `## Outside perimeter`
in .taskets/20260928-1935-builder-lane.md, or widen `perimeter:`
```

`cat .git/charter/active` → `20260928-1935-builder-lane`. The edits are logged against the wrong unit, and the
suggested override would write a false note into a unit the session never worked on. Expected: each session keeps
the unit it started; a second session's `unit start` does not change what the first session's edits are
attributed to. The per-session files (`.git/charter/session-<id>.json`) already exist but do not carry the unit.

## Reproduce

1. In one clone, open two Claude Code sessions A and B.
2. A: `python3 .charter/bin/charter unit start <unit-a>`.
3. B: `python3 .charter/bin/charter unit start <unit-b>`.
4. A: Write a file inside `<unit-a>`'s perimeter → the perimeter hook warns that it is outside `<unit-b>`.

## Where

`package/.charter/lib.py:574-582` (`active_unit`): `CHARTER_UNIT` from the environment, else the single file
`local_state_dir(root) / "active"`, shared by every session in the clone. A Claude Code session cannot set
`CHARTER_UNIT` for its own hook processes. The session files are written by the hooks (inference: not read).

## Workaround

Session A did not re-run `unit start` (that would flip session B's attribution in turn). It logged the mis-attribution
in its own unit's `## Log` and kept its files inside its own perimeter.

## Suggested fix

Record the started unit in the session's own state file (`session-<session_id>.json`, keyed by the hook's
`session_id`) and have `active_unit` prefer it over the clone-wide `active` file; keep the file as the fallback for
git hooks and engines.

## Addition 2026-10-13: the residual, measured in tele-claude, and the fix in 0.4.15

- Status from this date: fixed in 0.4.15 for a session that names its id; open for a commit made outside any session, which still reads the checkout's choice (`docs/gates.md` § What a gate cannot see).
- What was left: 0.4.7 gave each session its own choice (`<git dir>/charter/active-<session id>`) but kept the checkout's `active` file as the fallback for every caller, sessions included, while the unit is open, so a session that never ran `unit start` was charged to the unit another session chose last (`active_unit_source` in `package/.charter/lib.py`, as of 0.4.13).

Measured on 2026-10-13 in tele-claude's gate log and session records, rows of 2026-10-06 to 2026-10-13, read only; each group of perimeter rows was matched to the commit that next touched its paths (`$ git -C /home/gui/Projects/tele-claude log --all --reflog --since=2026-10-04 --format='%H %aI %s' --name-only`):

- The perimeter gate wrote 72 "outside the perimeter" rows, 16 from the hook and 56 from `charter check --staged`; the CLI rows carry no `session` field, so the committing session had to be inferred (/home/gui/Projects/tele-claude/.git/charter/log.jsonl).
- 23 of the 56 CLI rows charged the unit the commit itself names (`unit <id>` in its message): real warnings, mostly tests and shared fixtures outside a perimeter (/home/gui/Projects/tele-claude/.git/charter/log.jsonl).
- 22 came from two commits with no tag, https://github.com/elgui/tele-claude/commit/081c5505 and https://github.com/elgui/tele-claude/commit/6266aa01; the second says it carries an earlier session's r6 work.
- The brief's reading that most rows charge another session's unit did not hold: 44 of its 58 (unit, path) pairs fall in another unit's perimeter because perimeters overlap, not because the unit was wrong (`docs/briefs/2026-10-13-hermes-failure-record-and-perimeter-fit.md` § K13).
- 5 rows were the fallback: https://github.com/elgui/tele-claude/commit/818348d3 (2026-10-08 19:10) and https://github.com/elgui/tele-claude/commit/671b2db8 (2026-10-09 08:27) say `unit 20261008-1730` and were judged against `20261008-1731-park-a-session-on-someone-from-its-card` (/home/gui/Projects/tele-claude/.git/charter/log.jsonl).
- Four sessions, caeac0da/6dded105/e10b87d9/2ebf52f4, ended charged to that unit, and the second of them had logged "no active unit" from 17:10 to 17:14 that day (/home/gui/Projects/tele-claude/.git/charter/sessions.jsonl).
- Over the week, 10 units were each recorded at the end of more than one session (37 sessions), `20260930-0831-staging-smoke-before-restart` at the end of 9 (/home/gui/Projects/tele-claude/.git/charter/sessions.jsonl).
- 6 rows had a second cause, the shared index: at 2026-10-11 17:43 and 2026-10-12 13:28, sessions charged to `20260930-0831` and `20261012-1320` were warned about `services/atomic_json.py`, `services/group_automator.py` and `tests/test_group_automator_persistence.py`, which another session had staged and committed at 2026-10-12 17:02 as https://github.com/elgui/tele-claude/commit/0354cd9 (`unit 20260929-2005`).
- A plain `git commit` hands the pre-commit hook everything staged in the checkout's index; with a pathspec (`git commit -- <paths>`) the hook sees only those paths. Checked in a scratch repository on 2026-10-13, where a hook running `git diff --cached --name-only` printed the one path given (`docs/session-log.md` § 2026-10-13).
- `CLAUDE_CODE_SESSION_ID` reaches the git hook: the same scratch hook, run by `git commit` from a Claude Code session's Bash tool, printed the session's id, so `charter check --staged` sees the committing session whenever a session commits (`docs/session-log.md` § 2026-10-13).

The fix, 0.4.15 (`docs/gates.md` § Perimeter; tests in `tests/test_failure_record_0_4_15.py`, class `SessionUnit`):

- `charter unit start` records which session made the checkout's choice in `<git dir>/charter/active.by`, empty when none did; a session with an id and no unit of its own inherits the checkout's choice only when no session made it, and a choice recorded before 0.4.15 is not inherited by a session (`inherits_checkout` in `package/.charter/lib.py`).
- At commit, a staged path outside the perimeter that another live session's record lists as edited, and the committing session's does not, is named as that session's, with `git commit -- <your paths>` as the way past (`edited_by_other_sessions` in `package/.charter/checks.py`).
- The rows `charter check` writes carry `session`, so the next measurement needs no inference (`cmd_check` in `package/.charter/bin/charter`).
