---
id: <slug-same-as-filename>
title: <one line>
# status: proposed | active | rejected | superseded | retired (changing it on an existing decision is the owner's act: `charter rule <id> <status>`)
status: active
date: <YYYY-MM-DD>
owner: <who settles it>
# kind: design | lesson
kind: design
# binds: files that must carry `charter:<id>`; optional
binds: [<glob>, <glob>]
# check: a shell command that exits 0 while the decision holds; optional; it runs at every commit that stages a bound file and in CI.
# Write it only once the code it guards exists. A check never seen failing proves nothing: before the decision goes active, break the
# guarded code on scratch, run the check, see it fail, and record that under ## Because as `$ <break>; <check>` → exit <n>
check: <shell command that exits 0 while the decision holds>
# expires: a date or a condition in words; a date is exclusive (the decision counts as expired from the start of that day) and must be later than `date:`
expires: <YYYY-MM-DD or a condition in words>
# supersedes: the id of the decision this one replaces, if any
supersedes:
# superseded_by: set by the owner when this decision is superseded
superseded_by:
# ask: while proposed, the question the owner answers, in plain words; optional, `charter owner` shows it
ask:
# recommend: while proposed, active | rejected, with the reason under ## Recommendation; optional
recommend:
# read: docs that say how to follow this decision; while it is active every session start names them, and each must exist; optional
read: []
# gate_paths + gate_evidence: while active, a unit whose `perimeter:` touches these globs closes only when its `## Evidence`
# matches the regular expression gate_evidence, or the unit lists this decision under `waives:` (a warning); set both or neither; optional
gate_paths: []
gate_evidence:
---

## Decision

<What was decided, in one paragraph. State the current state, not the history.>

## Because

<The case that justified it: the incident, the measurement, the constraint. This is what a reader needs to know whether it still applies.>

<With a `check:`, the check seen failing: `$ <the scratch break>; <the check>` → exit <non-zero>, then the break undone.>

## Stops applying when

<The condition under which this decision should be retired.>

## Recommendation

<Optional, while proposed: one line on why `recommend:` says what it says.>

<!-- `charter rule` appends a dated line under `## Ruling` at the end of this file when the owner rules. -->
