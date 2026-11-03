---
id: 20261103-213700-next-readiness-explanations
title: Explain what can start and why in charter next
status: later
priority: p2
created: 2026-11-03
updated: 2026-11-03
category: tooling
tags: [charter, readiness, next, idea]
origin: readiness-investigation-20261103
plan: false
kind: work
perimeter: [package/.charter/**, tests/test_next_readiness.py, AGENTS.md, docs/daily-use.md, docs/verification.md, docs/method.md, docs/package.md, docs/method-visual.html, docs/assets/maps/**, docs/maps.md, docs/maps.html, package/VERSION, package/charter/config.json]
decisions: []
---

## Context

Filed at the user's request on 2026-11-03: improve `charter next` so a person or agent can see which existing units can start, which cannot, and the evidence behind each condition. This is an independent backlog idea, not a scheduled implementation or a prerequisite for the readiness visual.

The current command exports rails, unit states and owner work, but a nonempty Log can produce an `in-progress` display state without establishing eligibility. Read `package/.charter/bin/charter` (`_unit_state`, `_next_json`, `cmd_next`), `package/.charter/rails.py`, `package/.charter/owner.py` and `docs/verification.md` before designing the output.

The originating private investigation and prototype are retained at `/home/gui/.local/share/readiness-lab/lecrm/study/REPORT.html`. Treat client examples as private and turn them into synthetic fixtures; do not copy their records into this repository.

## Proposed outcome

A short text brief and a compatible JSON representation explain recorded start conditions, explicit dependencies, missing links, rail coverage gaps and owner conditions, with source paths/lines and revision provenance. Show unknowns explicitly. Keep eligibility separate from design adequacy, live-run admission and delivery verification. Owner acceptance can hold closure without holding a worker's start.

Compare this CLI-first result with the existing visual prototype on representative questions before deciding whether a dashboard integration adds value. Execution-path differences matter: manual start does not enforce unit dependencies; Run All ignores dependencies outside its group; optional sequence edges are not authored dependencies. The command must not imply it simulates every engine.

## Acceptance

- [ ] AC-1: synthetic cases cover an eligible unit, an explicit dependency hold, a human checkpoint, a missing prerequisite, an empty rail, a closure-only owner criterion and branch provenance — probe: `cd tests && python3 -B -m unittest test_next_readiness`
- [ ] AC-2: text and JSON give matching evidence-backed explanations and preserve existing read-only behavior and JSON compatibility — probe: `cd tests && python3 -B -m unittest test_json_verbs_0_4_13 test_next_readiness`
- [ ] AC-3: documentation explains computed conditions, unknowns, design judgment and execution limits with resolving sources — probe: `python3 -B package/.charter/bin/charter anchors docs/daily-use.md docs/verification.md`

## Boundaries

Autonomy: an agent can design and implement the read-only output when this idea is selected. Filing it does not authorize launch, release, publishing or any owner action. A package change is a release: follow AGENTS.md for versions, upgrade notes, generated maps and the full documented background test suite. Do not change statuses, approvals, runtime behavior or the unreleased spec recipe's hold merely to make the brief actionable.

## Log

- 2026-11-03: Filed as a standalone idea. No implementation or release started. Acceptance commands describe future verification; they have not been reported as passing.
