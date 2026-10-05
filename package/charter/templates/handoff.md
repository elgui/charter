---
chain: <chain id>
session: <n>
# status: continue | wait | halt | complete
status: continue
# next_unit: the tasket the next session works on (after the owner's acts, with wait); `none` when the chain halts or is complete
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

## Wait

<Only with `status: wait`: one line per act of the owner's, paste-ready (.charter/chain-rules.md section 5): ``- <what> — run: `<command>` — expect: <what success prints> — closes <unit-id> AC-n``, or the exact path of a setting instead of `run:`. The command runs as pasted in zsh: no `<placeholder>` in it (`chain next` refuses one), a value is read with `read "x?…"`.>
<!-- e.g.
- store the R2 bucket name — run: `read "b?R2 bucket name: " && echo "$b" | sudo tee /opt/app/etc/r2-bucket` — expect: the name echoed back, one Touch ID prompt — closes 20261004-0010 AC-7
- turn on FileVault (System Settings > Privacy & Security > FileVault > Turn On) — expect: "FileVault is turned on" — closes 20261004-0010 AC-8
-->

## Halt

<Only with `status: halt`: what went wrong, and what the owner must judge before the chain can go on.>
