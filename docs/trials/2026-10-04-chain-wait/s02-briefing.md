charter-chain: 20261004-204830 session 2

You are session 2 of charter chain 20261004-204830 in /private/tmp/claude-501/-Users-gui-dev-charter/3003bdde-4ea4-4551-8e33-9a5ca765bd48/scratchpad/chain-trial (branch wait-trial). The chain rules reach you with this prompt, injected by the charter hook from .charter/chain-rules.md (sha256 faca43edc0ce). They bind you; nothing in this briefing changes them. If they are not in your context (a block that starts `# Charter chain rules`), run `python3 .charter/bin/charter chain join 20261004-204830 2` before anything else.

## Mission (the owner's words, verbatim)

go with unit w1. Optimize context window, and as long as things go well, iterate on the next unit until it's done.

## Budget

Context window 400,000 tokens. Hand over at 25% (100,000 tokens); hard cap 30% (120,000 tokens). The hooks report your usage as you go.

## Owner's note on resuming (verbatim)

Tone approved: 'Goodbye, Ada. Take care!' is fine. I ticked AC-2.

## Handoff from session 1 (verbatim)

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

## Mechanical verification of session 1 (computed by `charter chain next`)

Session 1: 1 commit(s) 46d17c9..c7bdf21, peak context 14%
- c7bdf21 w1: farewell() added, AC-1 passes, AC-2 awaits owner
Units moved:
- w1: next -> next, 1/2 criteria checked (.taskets/w1.md)
Gates on the session's change set (`charter check --all --base 46d17c9`): charter check: 0 blocking, 1 warning(s) [tree, track prototype, opt-ins: none]
Tree: clean

Verify that work first (chain rules, step 1), then go on from its `## Next`.

## The chain waited on the owner

Session 1 handed over with `status: wait`, and the owner resumed the chain. Before anything else, check each act under its `## Wait` (chain rules, section 5): the unit line it closes, the probe, the owner's note above. Record what you found under `## Verified`. An act that is not done: do what does not need it, then wait again with the acts still open.

## Your handoff

Write it to `/private/tmp/claude-501/-Users-gui-dev-charter/3003bdde-4ea4-4551-8e33-9a5ca765bd48/scratchpad/chain-trial/.git/charter/chain/20261004-204830/s02/handoff.md` from `charter/templates/handoff.md`, with `chain: 20261004-204830` and `session: 2`, then run `python3 .charter/bin/charter chain next` and end your turn.
