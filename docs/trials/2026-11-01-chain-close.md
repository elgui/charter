# Trial: a chain from a linked worktree on tele-claude, and when its sessions end (2026-11-01)

Claude Code 2.1.316, tele-claude backend, the spawn plugin's shim, sessions on `haiku` at effort `low`. The bed was a scratch repository with a linked worktree on a branch `work`, started from a session registered in another repository, the shape of a real chain started from a shared checkout. All chain ids below are the bed's (operator report, 2026-11-01). The bed was deleted afterwards, so the events are quoted here.

## Where a session opens

Before the fix, a `create` without `--workspace` from the scratch repository, with the shim's result read back (operator report, 2026-11-01):

```text
"workspace": "<the caller's checkout>"
{'working_dir': '<the caller's checkout>', 'status': 'active', 'tmux_session': 'cc-45', ...}
pane_current_path: <the caller's checkout>
```

`cwd` on the subprocess does not move it: the shim takes the caller's registered row (`README.md` § Where the child lands, beside the shim). A chain started in a linked worktree would have worked in the other tree, on its branch. After the fix, chain `20261101-214136` registered `working_dir` as the linked worktree, and every session of the four chains below did too (operator report, 2026-11-01).

## What `delete` frees

`delete` on the tele-claude backend exits Claude Code and kills the tmux session. Measured on one idle `haiku` session of 364 MB RSS (operator report, 2026-11-01):

| | used (MB) | swap used (MB) |
|---|---|---|
| before the launch | 17,019 | 3,791 |
| running | 17,374 | 3,791 |
| just before `delete` | 17,405 | 3,791 |
| 3 s after `delete` | 17,195 | 3,791 |

The tmux session and the process were gone after it. The row goes too, so `agent_session.py status <id>` then fails with `no tele-claude session <id>`, exit 1, not the verdict `dead`, and a second `delete` gets HTTP 404. The box was shared with about 70 other sessions, so `free -m` alone is a noisy reading; the process and the tmux session are the proof (operator report, 2026-11-01).

## Every end

`close_delay_s` was 15 on the bed (operator report, 2026-11-01).

| End | Chain | Session ended | `tab-closed` | Path |
|---|---|---|---|---|
| hand-over | `20261101-214136` | s01 21:43:11 | 21:43:32 | `close_link` from `_hand_over` |
| complete, with a review after it | `20261101-214136` | s02 21:44:03 | 21:44:23 | `close_link` from `_hand_over` |
| complete, the last session | `20261101-214136` | s03 21:44:28 | 21:44:47 | `close_link` from `_hand_over` |
| complete, then a slow review | `20261101-214519` | s01 21:45:58 | 21:46:18 | `close_link` from `_hand_over` |
| halt | `20261101-214519` | s02 21:47:14 | 21:47:33 | `close_link` from `_hand_over` |
| wait | `20261101-214752` | s01 21:48:29 | 21:48:48 | `close_link` from `_hand_over` |
| stall | `20261101-214910` | s01 21:49:17 | 21:49:36 | `close_session` from `on_stop` |

For each one, `status <id>` read `no tele-claude session`. For the stall, the tmux session and the pid were checked as well, a process of 315 MB RSS. The stall was fed: the Stop hook ran three times by hand with the real session's id, on a real tab, because a model that is told to go on does not stall on demand (operator report, 2026-11-01).

The closer survives the delete: it wrote `tab-closed` after its own session was gone, in every row above.

In chain `20261101-214519` the reviewer took 40 s, longer than the close, so the runner launched s02 at 21:46:45, 27 s after s01's pane was gone. That is the normal order with a real review, and the launch needs `--workspace`: with the parent's pane gone there is no registered row to inherit (operator report, 2026-11-01).

## Folder trust

In the bed's first launch, session 1 stopped at Claude Code's trust menu, and `create` returned `ready: false`. Answering the menu did not bring the briefing: the session sat idle, unjoined, until the briefing was sent with the shim's `send`. The old event text, "the session then starts on its own", is true of a terminal tab, which carries its briefing on the command line, and false of a pasted one (operator report, 2026-11-01).

Trust does not come from a parent folder: the home of all the projects was trusted, and the bed still asked. After the answer in the linked worktree, Claude Code recorded it under the **main checkout's** path, not the worktree's. A linked worktree of a trusted repository, with no record of its own, came up `ready: true`, with no menu (operator report, 2026-11-01). So `untrusted` reads both keys, and the warning is for a repository nobody has trusted.

## What it does not show

- `wait` at a real Codex review of owner.md: the bed ran `--owner-review off`.
- A real `opus[1m]` session's memory: the figures here are `haiku` at effort `low`.
- A resume after the tab closed, on this backend. The code path is `tests/test_owner_gate.py`, which has no tab to close.
- A launch through the session server during a stall. One `create` in about ten died on a 5 s read timeout before creating anything: `http_json` in the shim catches `HTTPError` and `URLError`, and a read timeout is neither. In a chain that is a safe halt, `launching session n failed`, and `/resume-chain` retries it (`start_link` in `package/.charter/chain.py`); the fix belongs to the shim's repository (operator report, 2026-11-01).
