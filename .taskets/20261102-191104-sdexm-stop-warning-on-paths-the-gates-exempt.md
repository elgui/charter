---
id: 20261102-191104-sdexm
title: "Stop the scope warning on paths the gates exempt"
status: done
priority: p2
created: 2026-11-02
updated: 2026-11-03
category: tooling
tags: [charter, spec-step]
origin: spec-step-proposal-20261102
group: spec-step-defects
group_order: 110
order: 5
perimeter: [package/.charter/checks.py, tests/test_spec_step_defects.py, AGENTS.md, docs/gates.md]
decisions: []
kind: work
---

## Context

`check_unit_scope` warns on `charter/` and `.taskets/` perimeter entries (`package/.charter/checks.py:136`) that `PERIMETER_EXEMPT` excludes elsewhere (`package/.charter/lib.py:26`). Every spec unit on the client track raised them, and they fell only when the unit closed, so they stopped being looked at. Defect 4 of the spec-step proposal, ruled on Owner Desk `oa-cr4y`, D6.

## Acceptance

- [x] AC-1: a perimeter entry under an exempt path raises no coverage warning — probe: `cd tests && python3 -B -m unittest test_spec_step_defects.ExemptPerimeter`
- [x] AC-2: (guard) an uncovered ordinary path still warns, and an out-of-scope path still warns — probe: `cd tests && python3 -B -m unittest test_spec_step_defects.ExemptPerimeterGuard`

## Evidence

- commit 8d39e3e on branch `fix/spec-step-defects`, released as 0.4.22
- $ cd tests && python3 -B -m unittest test_spec_step_defects.ExemptPerimeter → OK
- $ cd tests && python3 -B -m unittest test_spec_step_defects.ExemptPerimeterGuard → OK

## Log

- 2026-11-03: fixed in its own commit; each commit was checked out alone and passed its own test classes.

## Outside perimeter
