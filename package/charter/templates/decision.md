---
id: <slug-same-as-filename>
title: <one line>
status: active            # proposed | active | superseded | retired
date: <YYYY-MM-DD>
owner: <who settles it>
kind: design              # design | lesson
binds: [<glob>, <glob>]   # files that must carry `charter:<id>`; optional
check: <shell command that exits 0 while the decision holds>   # optional
expires: <YYYY-MM-DD or a condition in words>
supersedes:               # id of the decision this replaces, if any
superseded_by:            # set when status becomes superseded
---

## Decision

<What was decided, in one paragraph. State the current state, not the history.>

## Because

<The case that justified it: the incident, the measurement, the constraint. This is what a reader needs to know whether it still applies.>

## Stops applying when

<The condition under which this decision should be retired.>
