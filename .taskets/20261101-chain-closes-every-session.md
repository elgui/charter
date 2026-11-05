---
id: 20261101-chain-closes-every-session
title: A chain session opens in the chain's own tree and its process is freed at every end
status: done
priority: p1
created: 2026-11-01
updated: 2026-11-05
category: bug
perimeter:
  - package/.charter/chain.py
  - package/.charter/chain_groups.py
  - package/.charter/owner_acts.py
  - package/.charter/lib.py
  - package/.claude/skills/charter-chain/SKILL.md
  - tests/test_chain_close_0_4_23.py
  - tests/test_chain_wait.py
  - tests/test_owner_gate.py
  - package/VERSION
  - package/charter/config.json
  - AGENTS.md
  - docs/
---

# A chain session opens in the chain's own tree and its process is freed at every end

## Why

The coordination engine's core conformance unit runs as a chain from a linked worktree, on a VPS whose swap is nearly
full. Two defects, both measured on 2026-11-01 from a tele-claude session (operator report, 2026-11-01):

- `launch` passes no `--workspace`, and the shim defaults to the calling session's registered `working_dir`. A
  throwaway `create` run from a scratch repository registered and ran in the caller's checkout, on `main`.
- `close_tab` runs in one place, `_hand_over`, on session n-1. Session n stays alive for the whole of session n+1; the
  last session of a chain, and a session that halts, waits or stalls, are never closed.

## Acceptance

- [x] AC-1: `launch` passes the chain's root as `--workspace`, in the main tree and in a linked worktree, and `chain start --dry-run` names where sessions open: `python3 -B -m unittest test_chain_close_0_4_23.Workspace` from `tests/`
- [x] AC-2: a spawned session is deleted after hand-over, wait, halt, complete and stall, and after a stop before it joined: `python3 -B -m unittest test_chain_close_0_4_23.EveryEnd test_chain_close_0_4_23.WaitEnd` from `tests/`
- [x] AC-3: a close that fails is retried, reported as an event, and picked up at the next hand-over; a tab already gone counts as closed: `python3 -B -m unittest test_chain_close_0_4_23.CloseFailure` from `tests/`
- [x] AC-4: a real chain on tele-claude, in a throwaway repository: sessions open in that repository, and a session's process is gone after it ends (recorded in `docs/trials/2026-11-01-chain-close.md`)

## Evidence

- 929ef40, 4ecb010: the fix, its tests and the trial record (`package/.charter/chain.py`, `tests/test_chain_close_0_4_23.py`, `docs/trials/2026-11-01-chain-close.md`)
- $ python3 -B -m unittest test_chain_close_0_4_23: on 2ec340e 15 of the then 16 tests failed; on this branch all pass
- $ python3 -B -m unittest <the AGENTS.md list>: Ran 728 tests, OK (skipped=1), at 4ecb010

## Log

- 2026-11-05: ported onto main (578b282) as e33523d, d4eb108, 956714b, 662708a on branch `port/chain-close`, for release 0.4.23; the commits named above (4ecb010 and the rest) are on branch `chain-closes-every-session`. The 0.4.21 version stamps were left out, since main shipped other work as 0.4.21, and the test module became `tests/test_chain_close_0_4_23.py`, so the probes above name it.
- 2026-11-01: review after closing: the closer started before the next session's launch, which runs in the pane it kills. Moved to the end of `_hand_over`, with a test that fails before it.
- 2026-11-01: full suite green at 4ecb010; closed. Merging is the owner's.
- 2026-11-01: fix and trial landed; AC-4 evidence is docs/trials/2026-11-01-chain-close.md. Added beyond the first list: the trust warning and the honest menu message, both found by the trial.
- 2026-11-01: opened. Tests before the fix. This repository runs no `.charter/` of its own (`AGENTS.md`), so this tasket is the record and its probes run from `tests/`.
