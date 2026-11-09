---
id: <YYYYMMDD-HHMMSS-xxxxx>
title: <one deliverable, in one line>
# status: now | next | later | blocked | done (the engines read these values; keep comments on their own lines)
status: next
priority: p1
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
# scope: an in-scope item or an approved change id (client track)
scope: S1
perimeter: [app/<area>/**, tests/unit/**]
# decisions: ids of the decisions this unit relies on; `charter check --decisions` warns when one is retired
decisions: []
# waives: ids of decisions whose evidence gate (`gate_paths:`) this unit is excused from; say why in ## Log; done warns; optional
# kind: work | split (a split unit is opened by the owner)
kind: work
---

## Context

<Why this unit exists, with anchors (path:line, commit, URL).>

## Acceptance

- [ ] AC-1: <binary, observable state> — probe: `<command>`
- [ ] AC-2: <...> — probe: `<command>`
<!-- A criterion a person must close (taste, risk, a device or account only they have, a human review the unit keeps) says why a person is needed, what they will observe or judge, who prepares it and what package they get: not "the owner reviews the result". Do not invent a probe to avoid it. -->
<!-- A probe must fail before the work. A criterion that protects behaviour which already exists says `(guard)`.
     A criterion only the owner can close carries an `— owner: check` (or `— owner: do`) segment before its probe:
     `- [ ] AC-3: rows arrive after the restart — owner: check — probe: `<command>``. `charter owner` lists it. -->
<!-- A unit that changes a state machine (a poller, a session, a relay, a run) lists what the world does without the
     user: a timer or tick, a process dying, a restart, a second device or hook answering, a late completion. Give an AC
     for each one that can fire between two steps. An AC that says "never stuck" or "eventually"
     names what must keep running, and its probe stops that. -->

## Evidence

<Filled as work lands: commit SHAs and each probe as a `$ command` line with its result (`charter probe <id>` prints them).>

## Log

- <YYYY-MM-DD HH:MM> started; baseline: `<command>` → <result>

## Outside perimeter

<- path: why (only if you touched a file outside `perimeter:`)>
