---
id: 20261102-191103-sdprp
title: "Warn on a unit relying on a proposed decision"
status: done
priority: p2
created: 2026-11-02
updated: 2026-11-03
category: tooling
tags: [charter, spec-step]
origin: spec-step-proposal-20261102
group: spec-step-defects
group_order: 110
order: 4
perimeter: [package/.charter/checks.py, tests/test_spec_step_defects.py, AGENTS.md, docs/gates.md]
decisions: []
kind: work
---

## Context

`check_unit_decisions` warns on a missing or retired decision only (`package/.charter/checks.py:665`), and `charter unit start` calls it (`package/.charter/bin/charter:820`), so a unit can start on a decision nobody has ruled. Defect 3 of the spec-step proposal, ruled on Owner Desk `oa-cr4y`, D6. A warning, not a hold: a checkpoint holds.

## Acceptance

- [x] AC-1: `charter unit start` and `charter check` warn when a unit past planning names a `proposed` decision — probe: `cd tests && python3 -B -m unittest test_spec_step_defects.ProposedDecision`
- [x] AC-2: (guard) a unit still at `next` or `later` is not warned, and an active decision is not — probe: `cd tests && python3 -B -m unittest test_spec_step_defects.ProposedDecisionGuard`

## Evidence

- commit 33464e5 (review answer) and d71bc66 on branch `fix/spec-step-defects`, released as 0.4.22
- $ cd tests && python3 -B -m unittest test_spec_step_defects.ProposedDecision → OK
- $ cd tests && python3 -B -m unittest test_spec_step_defects.ProposedDecisionGuard → OK

## Log

- 2026-11-03: fixed in its own commit; each commit was checked out alone and passed its own test classes.
- 2026-11-03: a codex review found defects in this fix; answered in 33464e5: unit start no longer warns on a closed unit.

## Outside perimeter
