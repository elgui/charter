---
chain: 20261004-112911
session: 1
status: continue
next_unit: t3
---

## Verified

first session

## Done

- t1: greet(name) in app/greet.py, probe passes, 180df9e (evidence commit follows).
- t2: slugify(text) in app/slug.py, probe passes, e052839 (evidence commit follows).

## State

Group r1 complete, everything committed, no active unit. t3 (group r2) waits for the r1 review.

## Next

`python3 .charter/bin/charter unit start t3`, then work it.

## Watch out

None. `charter unit done` does not exist; I set status/boxes/Evidence by hand, then `unit stop`. Size warning at 25/30 lines on t1.md and t2.md.
