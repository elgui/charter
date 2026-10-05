---
id: w1
title: farewell() says goodbye, and its tone is approved
status: done
order: 4
perimeter: [app/farewell.py]
kind: work
rail: r1
---

## Context

app/farewell.py: farewell(name), the counterpart of greet(). A person must approve the tone.

## Acceptance

- [x] AC-1: farewell("Ada") says goodbye to Ada — probe: `python3 -c "from app.farewell import farewell; m = farewell('Ada'); assert 'Ada' in m and m != 'Hello, Ada!'"`
- [x] AC-2: the owner reads farewell("Ada") and approves its tone — owner: check

## Evidence

- AC-1: `$ python3 -c "from app.farewell import farewell; m = farewell('Ada'); assert 'Ada' in m and m != 'Hello, Ada!'"` → exit 0
- AC-2: owner approved tone, commit b06cd86; `$ python3 -c "from app.farewell import farewell; print(farewell('Ada'))"` → Goodbye, Ada. Take care!

## Log
- 2026-10-04: app/farewell.py added, AC-1 probe passes. AC-2 (tone approval) waits on the owner.
- 2026-10-04: session 2 verified AC-1 probe and owner's AC-2 tick (b06cd86); w1 closed.
