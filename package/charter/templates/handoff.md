---
chain: <chain id>
session: <n>
# status: continue | halt | complete
status: continue
# next_unit: the tasket the next session works on; `none` when the chain halts or is complete
next_unit: <tasket id>
---

## Verified

<What you checked of the previous session's work, how, and the result: each `$ command` you ran and what it returned, with the commits you read. Session 1 writes `first session`.>

## Done

<One line per unit moved this session: id, what landed, commit SHA(s). "nothing landed" is an answer.>

## State

<Where the next session starts: the active unit and its open criteria, anything half-done, any uncommitted file and why it is not committed.>

## Next

<The first concrete action for the next session.>

## Watch out

<What failed, what was ruled out and why, traps in the code or the environment. "none" is an answer.>

## Review

<Only when your briefing carries a group's review: one line per finding, starting with its id, `R1 fixed <commit>` or `R2 dismissed <path:line> <why>`. With `status: halt`, answer what you could; the session after the owner's answer gets the whole review again.>

## Halt

<Only with `status: halt`: what the owner must decide or do before the chain can go on.>
