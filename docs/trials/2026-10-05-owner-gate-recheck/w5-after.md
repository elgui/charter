---
id: w5
title: thanks() thanks a member, and its tone is approved
status: done
order: 8
perimeter: [app/thanks.py]
kind: work
rail: r1
---

## Context

app/thanks.py: thanks(name), the line a member reads after helping. A person must approve its tone.

## Acceptance

- [x] AC-1: thanks("Ada") thanks Ada — probe: `python3 -c "from app.thanks import thanks; m = thanks('Ada'); assert 'Ada' in m and 'hank' in m"`
- [x] AC-2: the owner reads thanks("Ada") and approves its tone — owner: check

## Evidence

- commit 8c8b9e2 (thanks() written); AC-2 closed by the owner in 87b5bdb
- $ python3 -c "from app.thanks import thanks; m = thanks('Ada'); assert 'Ada' in m and 'hank' in m" → exit 0

## Log

- 2026-10-05: created for the owner-gate re-check at 1b0cddd
- 2026-10-05: app/thanks.py written, AC-1 probe passes. AC-2 (tone) waits on the owner; not guessed.
- 2026-10-05: session 2 verified AC-1 probe, AC-2 closed by owner (87b5bdb); w5 done.
