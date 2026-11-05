---
id: 20261105-120000-next-shows-unit-questions
title: charter next shows the question each waiting unit names
status: later
priority: p3
created: 2026-11-05
updated: 2026-11-05
category: tooling
tags: [charter, next, owner, idea]
origin: branch-reconcile-20261105
plan: false
kind: work
perimeter: [package/.charter/**, tests/**, AGENTS.md, docs/daily-use.md, docs/method.md, docs/package.md, docs/method-visual.html, docs/assets/maps/**, docs/maps.md, docs/maps.html, package/VERSION, package/charter/config.json]
decisions: []
---

## Context

A 0.4.7 attempt on the branch `next-lists-the-owner-questions` (`672db7f`, kept as the local tag `archive/next-lists-the-owner-questions`) made `charter next` list, under "Waiting on the owner", each open unit's `question:` frontmatter or the `gate_reason:` of a `gate: human` unit. It never merged; `main` released 0.4.7 for other work (`docs/package.md:109`). The owner queue of 0.4.8 now covers units whose `gate_reason` starts with `HUMAN-ONLY` (`package/.charter/owner.py:314`). Three parts of the attempt are still missing on `main`: a unit's `question:` field shown by `charter next`, a `gate: human` unit whose reason lacks the `HUMAN-ONLY` prefix, and a nudge when a `blocked` unit names no question (`$ git grep -n "question" origin/main -- package/` finds no `question:` field).

The personal road tooling already writes `question:` into units and expects `charter next` to list it (operator report, 2026-09-26).

## Acceptance

- [ ] AC-1: `charter next` and `charter next --json` show the `question:` of an open or blocked unit, and a blocked unit without one gets a one-line nudge (not verified) — probe: `cd tests && python3 -B -m unittest test_next_0_4_4 test_json_verbs_0_4_13`
- [ ] AC-2: a `gate: human` unit without the `HUMAN-ONLY` prefix reaches the owner queue or `next`, without listing a unit twice (not verified) — probe: `cd tests && python3 -B -m unittest test_owner_0_4_8`

## Boundaries

Read the archived attempt before designing; rebuild against current code rather than reapplying it. A package change is a release (AGENTS.md).

## Log

- 2026-11-05: Filed while reconciling unmerged branches; nothing implemented (operator report, 2026-11-05).
