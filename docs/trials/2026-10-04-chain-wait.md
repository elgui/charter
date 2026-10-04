# Trial record, 2026-10-04: a chain of 0.4.9 waits on the owner, in cmux tabs

The trusted bed of `docs/trials/2026-10-04-chain-tab-rerun.md` was upgraded to `2f66578` with `bin/charter-pkg upgrade`, which an agent committed (no hook changed since that bed's 0.4.8). On a new branch `wait-trial`, it got two units on rail `r1`. w1 asks for `farewell()` (AC-1, with a probe) and for a person's approval of its tone. That line is AC-2, deliberately left unmarked: `- [ ] AC-2: the owner reads farewell("Ada") and approves its tone`. w2 asks for `shout()` (AC-1, with a probe). The mission was the one of the earlier trials. Chain `20261004-204830` ran with `--launcher spawn --model sonnet --effort low --window 400000 --max-sessions 4 --review off`. Notifications were left at their default (`chain.notify` `auto`). The records are under `docs/trials/2026-10-04-chain-wait/`.

| step | what happened | record |
|---|---|---|
| s01 | Opened as a tab and joined at once. It built `farewell()`, ran AC-1's probe and wrote its evidence, and marked AC-2 `— owner: check`. It committed, then handed over with `status: wait`, `next_unit: w2` and one line under `## Wait` (what to read, the command that prints it, and the line it closes). 18 s, peak 14%. | `docs/trials/2026-10-04-chain-wait/events.log:2-5`; `docs/trials/2026-10-04-chain-wait/s01-handoff.md:28-30`; commit c7bdf21 (in the test bed) |
| the wait | The chain went to `waiting`, and `charter owner` listed it under "Do", with its act and the `chain resume` command, beside the `owner-line:w1:AC-2` item under "Check". | the `charter owner` output in this session; `docs/trials/2026-10-04-chain-wait/events.log:5` |
| the owner's act | This session stood in for the owner of the throwaway bed. It read the message, ticked AC-2 in commit b06cd86 (in the test bed), and ran `charter chain resume --note "Tone approved: ..."`. | `docs/trials/2026-10-04-chain-wait/events.log:6` |
| s02 | Its briefing carried "The chain waited on the owner". Before anything else, it verified the act: it read `git show --stat` of the owner's commit, re-ran the message and re-ran w1's probe, and wrote all three under `## Verified`. It then closed w1, citing the owner's commit as AC-2's evidence, built and closed w2, and handed over `complete`. 22 s, peak 14%. | `docs/trials/2026-10-04-chain-wait/s02-briefing.md:61-63`; `docs/trials/2026-10-04-chain-wait/s02-handoff.md:10-11`; `docs/trials/2026-10-04-chain-wait/w1-after.md:21-22` |

From start to completion the chain took 70 s, including the 25 s the stand-in owner took (`docs/trials/2026-10-04-chain-wait/events.log:1,11`). Start-up was 50,074 and 50,842 tokens (`docs/trials/2026-10-04-chain-wait/s01-link.json:23`, `docs/trials/2026-10-04-chain-wait/s02-link.json:23`), as in the earlier tab trials.

## Found

- The queue's title for a waiting chain repeated the reason ("waits on you after session 1: session 1 waits on the owner: ...") and cut it at 200 characters inside the command. The title is now `chain <id> waits on you: <k> act(s) from session <n>`, with the acts under it, and the notification states the reason once (`owner_items` and `halt` in `package/.charter/chain.py`).
- Whether the macOS notification appeared on the owner's screen was not observed from this session (not verified). `osascript` exists on this machine; the call is fire-and-forget (`notify` in `package/.charter/chain.py`).

## Not tested here

- A wait at a group's end with a real review: `--review off` here. The unit test `test_a_wait_at_the_end_of_a_group_runs_the_review_on_resume` in `tests/test_chain_wait.py` covers it with the fake reviewer.
- A session that waits again because the owner's act is not done (not verified).
