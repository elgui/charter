---
chain: 20261004-224239
session: 1
status: wait
next_unit: w3
---

## Verified

first session

## Done

- w3 AC-1: app/welcome.py, welcome("Ada") -> "Welcome, Ada!" (a799d7c, tick in next commit)
- w4: whisper() done, probe passes, evidence recorded (824f537)

## State

w3 has AC-1 closed; AC-2 (tone) is owner: check and open. Everything committed.

## Next

After the owner closes w3 AC-2, run `charter next`; r1 should then have nothing left (r2 close is owner's).

## Watch out

w4 says "After w3"; I did it first since w3's only open line is the owner's.

## Wait

- read welcome("Ada") ("Welcome, Ada!") and approve its tone — closes w3 AC-2 (`/resume-chain AC-2 <note>`)
