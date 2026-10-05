---
id: w3
title: welcome() greets a new member, and its tone is approved
status: done
order: 6
perimeter: [app/welcome.py]
kind: work
rail: r1
---

## Context

app/welcome.py: welcome(name), the line a new member reads first. A person must approve its tone.

## Acceptance

- [x] AC-1: welcome("Ada") welcomes Ada — probe: `python3 -c "from app.welcome import welcome; m = welcome('Ada'); assert 'Ada' in m and 'elcome' in m"`
- [x] AC-2: the owner reads welcome("Ada") and approves its tone — owner: check

## Evidence

- `$ python3 -c "from app.welcome import welcome; m = welcome('Ada'); assert 'Ada' in m and 'elcome' in m"` → exit 0
- AC-2 closed by the owner in 1fca9cd

## Log

- 2026-10-04: created for the owner-gate trial
- 2026-10-04: app/welcome.py added, AC-1 probe passes; AC-2 (tone) waits on the owner
- 2026-10-05: session 3 ran probe w3 (passes); owner closed AC-2 in 1fca9cd; unit done
