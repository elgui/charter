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
# kind: work | split (a split unit is opened by the owner)
kind: work
---

## Context

<Why this unit exists, with anchors (path:line, commit, URL).>

## Acceptance

- [ ] AC-1: <binary, observable state> — probe: `<command>`
- [ ] AC-2: <...> — probe: `<command>`

## Evidence

<Filled as work lands: commit SHAs and each probe as a `$ command` line with its result (`charter probe <id>` prints them).>

## Log

- <YYYY-MM-DD HH:MM> started; baseline: `<command>` → <result>

## Outside perimeter

<- path: why (only if you touched a file outside `perimeter:`)>
