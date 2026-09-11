---
id: <YYYYMMDD-HHMMSS-xxxxx>
title: <one deliverable, in one line>
status: next              # now | next | later | blocked | done (engines: keep these values)
priority: p1
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
scope: S1                 # scope item or approved change id (client track)
perimeter: [app/<area>/**, tests/unit/**]
decisions: []             # decision ids this unit relies on
kind: work                # work | split
---

## Context

<Why this unit exists, with anchors (path:line, commit, URL).>

## Acceptance

- [ ] AC-1: <binary, observable state> — probe: `<command>`
- [ ] AC-2: <...> — probe: `<command>`

## Evidence

<Filled as work lands: commit SHAs, path:line of the change, `$ command` runs with their result.>

## Log

- <YYYY-MM-DD HH:MM> started; baseline: `<command>` → <result>

## Outside perimeter

<- path: why (only if you touched a file outside `perimeter:`)>
