---
chain: 20261004-204830
session: 1
status: wait
next_unit: w2
---

## Verified

first session

## Done

- w1: app/farewell.py, AC-1 checked with probe evidence (commit below in git log, "w1: farewell() added"). AC-2 open, owner-only.

## State

w1 stays `next`/active with AC-2 marked `— owner: check`. Tree clean.

## Next

Check the owner did AC-2 (tone approved); then close w1 with `charter probe w1`, and work w2.

## Watch out

none

## Wait

- read farewell("Ada") -> "Goodbye, Ada. Take care!" (python3 -c "from app.farewell import farewell; print(farewell('Ada'))") and approve or change the tone, then tick AC-2 — closes w1 AC-2
