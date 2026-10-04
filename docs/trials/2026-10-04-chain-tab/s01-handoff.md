---
chain: 20261004-011522
session: 1
status: continue
next_unit: t1
---

## Verified

first session

## Done

nothing landed

## State

Unit t1 is active (started). app/greet.py does not exist yet. AC-1 is open. The only change is a dated `## Log` line in .taskets/t1*.md, committed.

## Next

Write app/greet.py with greet(name) returning 'Hello, <name>!'. Run `python3 .charter/bin/charter probe t1`, check AC-1, put the commit SHA under `## Evidence`, set done, commit. Then take the next unit from `charter next`.

## Watch out

Session 1 was at 33% context after reading the briefing and the tasket, before any code. The injected rules and hooks are probably most of that. Read little in the next session.

## Halt

none
