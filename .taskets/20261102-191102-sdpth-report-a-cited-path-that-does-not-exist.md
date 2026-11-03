---
id: 20261102-191102-sdpth
title: "Report a cited path that does not exist"
status: done
priority: p2
created: 2026-11-02
updated: 2026-11-03
category: tooling
tags: [charter, spec-step]
origin: spec-step-proposal-20261102
group: spec-step-defects
group_order: 110
order: 3
perimeter: [package/.charter/checks.py, tests/test_spec_step_defects.py, AGENTS.md, docs/gates.md]
decisions: []
kind: work
---

## Context

`charter anchors` flags a `path:line` that does not resolve but passes over a bare path. In a clean clone, a decision citing an absent file reported 0 unresolved. Defect 2 of the spec-step proposal, ruled on Owner Desk `oa-cr4y`, D6. Prose such as `and/or` must not trip it, and the gate result must not change on documents that pass today, so this starts as a report.

## Acceptance

- [x] AC-1: `charter anchors` lists a backticked path with a directory that does not exist, as a warning — probe: `cd tests && python3 -B -m unittest test_spec_step_defects.MissingPath`
- [x] AC-2: (guard) the report does not change the exit code, and a word with a slash in prose is not listed — probe: `cd tests && python3 -B -m unittest test_spec_step_defects.MissingPathGuard`

## Evidence

- commit 6c0fb63 on branch `fix/spec-step-defects`, released as 0.4.22
- $ cd tests && python3 -B -m unittest test_spec_step_defects.MissingPath → OK
- $ cd tests && python3 -B -m unittest test_spec_step_defects.MissingPathGuard → OK

## Log

- 2026-11-03: fixed in its own commit; each commit was checked out alone and passed its own test classes. Listed only when the directory is absent, as AC-1 says; an absent file in an existing directory is still not reported.

## Outside perimeter
