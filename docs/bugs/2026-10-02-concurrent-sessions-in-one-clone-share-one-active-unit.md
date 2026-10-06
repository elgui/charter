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
