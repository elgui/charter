# Trial record, 2026-10-04: a chain of 0.4.8 in cmux tabs, with group reviews

The bed of `docs/trials/2026-10-04-chain-tab.md`, which the owner had trusted, was upgraded to `chain-reliability` with `bin/charter-pkg upgrade` and given a road of two rails: `r1` holds t1 (`greet`) and t2 (`slugify`), and `r2` holds t3 (`mean`). Chain `20261004-192345` ran with `--launcher spawn --model sonnet --effort low --window 400000 --max-sessions 6` and the same mission. The review was Codex at effort `high`. The records are under `docs/trials/2026-10-04-chain-tab/20261004-192345/`.

| step | what happened | record |
|---|---|---|
| s01 | opened as a tab and joined at once, with no trust menu; closed t1 and t2 in 4 commits, peak 14% | `docs/trials/2026-10-04-chain-tab/20261004-192345/events.log:2-4` |
| review of `r1` | started by `chain next` in a detached runner; 68 s, no findings; the group was cleared at its last commit | `docs/trials/2026-10-04-chain-tab/20261004-192345/events.log:5-7`; `docs/trials/2026-10-04-chain-tab/20261004-192345/g01-review.md:1` |
| s02 | **launched as a cmux tab by the detached runner**, 3 s after the review cleared, and joined; closed t3, `complete`; session 1's tab was closed | `docs/trials/2026-10-04-chain-tab/20261004-192345/events.log:8-11`; `docs/trials/2026-10-04-chain-tab/20261004-192345/s02-screen.txt` |
| review of `r2` | 57 s, no findings; the chain completed | `docs/trials/2026-10-04-chain-tab/20261004-192345/events.log:12-15` |

The whole chain took 3 min 10 s (`docs/trials/2026-10-04-chain-tab/20261004-192345/events.log:1,15`). The runner is started detached (`start_new_session=True`, `start_review` in `package/.charter/chain_groups.py`) and outlives the shell that started it. It opened session 2's tab in the workspace the chain was started from: the same workspace id as session 1's tab (`docs/trials/2026-10-04-chain-tab/20261004-192345/s01-link.json:12`, `docs/trials/2026-10-04-chain-tab/20261004-192345/s02-link.json:16`). Before the trial, a process detached the same way printed its parent pid as 1 and got `PONG` from cmux (`$ python3 -c "import subprocess; subprocess.Popen(['sh', '-c', 'sleep 2; ps -o ppid= -p $$; cmux ping'], start_new_session=True)"`, run from this session; output not archived).

The start-up measured at each session's first tool was 49,568 and 50,369 tokens (`docs/trials/2026-10-04-chain-tab/20261004-192345/s01-link.json:22`, `docs/trials/2026-10-04-chain-tab/20261004-192345/s02-link.json:22`). That matches the 49,500 of the run above and the 50,000 that `STARTUP_TOKENS` estimates for the spawn launcher (`package/.charter/chain.py`). Neither review left a `review.out` or a `charter-review-*` directory, and `git worktree list` showed only the bed.

## Found while setting it up

`charter-pkg upgrade` staged 0.4.8 and said an agent commits it. The bed's 30-line `limits.file_lines` (`bin/make-testbed:23`) then refused that commit: the package's own `.claude/skills/charter-chain/SKILL.md` grew to 51 lines and `charter/templates/handoff.md` to 36. The size gate exempted `.charter/` because "an upgrade replaces it", but not the package files outside it. It now exempts the installer's paths outside `.charter/` too, as fixed globs rather than the manifest's entries, which a session could rewrite (`PACKAGE_GLOBS`, `size_budget_for` in `package/.charter/checks.py`; `test_a_file_the_installer_owns_is_not_held_to_the_projects_size_limit` in `tests/test_chain_reliability.py`). With the default 800-line limit, no project meets this today.

`charter/rails.md` is owner-only, so its fixture commit in the bed went through as `bin/make-testbed` commits its own baseline, with `git -c core.hooksPath=/dev/null` (`bin/make-testbed:27`). This was a throwaway bed whose owner is the fixture "Test Owner"; nothing else was committed past the hook.
