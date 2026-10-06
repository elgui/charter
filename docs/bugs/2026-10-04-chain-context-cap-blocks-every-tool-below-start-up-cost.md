# Chain context cap refuses every tool when start-up alone exceeds it

- Seen: 2026-10-04, chain-trial at f733cc5 (session 3), charter 0.4.7
- Status: open

## What happened

Chain 20261004-011522, budget 150,000 tokens, hand-over 25%, cap 30%. Sessions 1, 2 and 3 each started at 33% (session 3 read 35-38% after a few calls). The hook then refused the first edit:

`charter chain: context is at 33% of the window, past the 30% cap. Only the handoff goes through now: ...`

Three sessions in a row handed over without writing `app/greet.py`. Expected: the chain works; a context limit should steer sessions, not block them.

## Reproduce

Run `/charter-chain` on a project whose injected context (rules, skill and agent listings, deferred tool lists, MCP instructions) is above 30% of the window. Every session halts before its first edit.

## Where

The hard-cap refusal and the 25% / 30% shares are in the chain hook and `.charter/chain-rules.md` section 3 (not read in this session; inference).

## Workaround

None from the project. Owner raised the budget by hand.

## Suggested fix

Owner decision (Gui, 2026-10-04): context share must never block a tool.

- Remove the hard-cap refusal. The hook only warns.
- Hand-over line at 20% of the total window (total, not growth since start-up). Past it: finish the step, commit, log, write the handoff, `chain next`.
- 20% is below today's observed start-up (33%), so the line is unreachable unless start-up is trimmed. Fix both: report start-up size in the first hook message, and trim injected context (skill and agent listings, deferred tool lists, MCP instructions) until start-up is under about 15%.
- Until then, if start-up already exceeds the line, the hook should say so once and let the session work the unit rather than hand over empty.
- Update the `charter-chain` skill text ("25% / 30%") and `.charter/chain-rules.md` to match.
