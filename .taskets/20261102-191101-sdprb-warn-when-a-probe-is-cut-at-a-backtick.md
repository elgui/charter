---
id: 20261102-191101-sdprb
title: "Warn when a probe is cut at a backtick"
status: done
priority: p2
created: 2026-11-02
updated: 2026-11-03
category: tooling
tags: [charter, spec-step]
origin: spec-step-proposal-20261102
group: spec-step-defects
group_order: 110
order: 2
perimeter: [package/.charter/checks.py, tests/test_spec_step_defects.py, AGENTS.md, docs/gates.md]
decisions: []
kind: work
---

## Context

`PROBE_RE` stops at the first closing backtick (`package/.charter/checks.py:32`), so a probe that contains one runs as a shorter command, and nothing says so. In the second spec trial this left a unit that could never close. Defect 1 of the spec-step proposal, ruled on Owner Desk `oa-cr4y`, D6.

## Acceptance

- [x] AC-1: `charter check` warns on an acceptance line whose probe is cut at a backtick, and names the line — probe: `cd tests && python3 -B -m unittest test_spec_step_defects.ProbeCut`
- [x] AC-2: (guard) a whole probe gives no warning, and `charter probe` output keeps its form, which tele-claude's checker parses — probe: `cd tests && python3 -B -m unittest test_spec_step_defects.ProbeWhole`

## Evidence

- commit 34dbc83 on branch `fix/spec-step-defects`, released as 0.4.22
- $ cd tests && python3 -B -m unittest test_spec_step_defects.ProbeCut → OK
- $ cd tests && python3 -B -m unittest test_spec_step_defects.ProbeWhole → OK

## Log

- 2026-11-03: fixed in its own commit; each commit was checked out alone and passed its own test classes.

## Outside perimeter
