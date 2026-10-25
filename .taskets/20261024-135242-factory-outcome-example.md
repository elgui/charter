---
id: 20261024-135242-factory-outcome-example
title: Show an outcome check inside an ordinary tasket
status: done
priority: p2
created: 2026-10-24
updated: 2026-10-24
category: tooling
tags: [charter, documentation, outcomes]
origin: ai-native-sdlc-review-20261024
group: factory-quick-wins
group_order: 100
order: 3
plan: true
perimeter: [docs/examples/outcome-review.md, docs/daily-use.md]
decisions: []
kind: work
---

## Context

The research proposes checking whether delivered work helped, but a new platform is unnecessary for trying the idea (`docs/review/2026-10-24-ai-native-sdlc-factory-review.md:124`). The existing unit already has Context, Acceptance, Evidence and Log (`package/charter/templates/unit.md:18`). This unit delivers only a short worked example; it does not conduct the three-change pilot, change the schema, or require every task to carry product metrics.

Charter distinguishes evidence from its truth (`README.md:7`), and cost/optional human time are already supported (`docs/method.md:222`). Owner Desk asks are for present needs, separate from future project work (`/home/gui/Projects/tele-claude/docs/OWNER_DESK.md:49`).

<!-- charter: opinion -->
## Approach

Autonomy: routine example and guide work. Real outcome acceptance is outside this unit.

1. Add `docs/examples/outcome-review.md`, at most 100 lines, containing one explicitly hypothetical tasket example using only existing fields and body sections.
2. In Context show the affected user or operation, baseline with denominator, expected improvement, who observes it, and an observation window. In Acceptance keep technical criteria. In Evidence and dated Log show how a delivered revision and later observation would be recorded, including an honest "not observed yet" case.
3. Explain how the observer chooses continue, adjust, stop or revert. Failure of the product hypothesis does not silently reopen a technically completed unit or authorize deployment/revert. Future observation dates do not create premature Owner Desk asks. Link the example from `docs/daily-use.md`.

## Acceptance

- [x] AC-1: The short example has the existing four sections, labels all sample results hypothetical, and covers both an observed result and an inconclusive observation; factual guidance has resolving sources — probe: `test -f docs/examples/outcome-review.md && python3 -B package/.charter/bin/charter anchors docs/examples/outcome-review.md`
- [x] AC-2: The example stays at most 100 lines and is linked from the daily guide — probe: `python3 -B -c "from pathlib import Path; p=Path('docs/examples/outcome-review.md'); s=p.read_text(); assert 0 < len(s.splitlines()) <= 100; assert all(h in s for h in ('## Context','## Acceptance','## Evidence','## Log')); assert '(examples/outcome-review.md)' in Path('docs/daily-use.md').read_text()"`
- [x] AC-3: (guard) The documentation edits have no whitespace errors — probe: `git diff --check -- docs/examples/outcome-review.md docs/daily-use.md`

Mark hypothetical example text as illustrative/opinion so anchors validation does not treat invented observations as facts. Review the example against the source template and record that comparison in Evidence. These probes check structure and references, not whether any real outcome improved. Keep the exercise optional; do not add a gate, package template field, dashboard, scheduled job, or pilot execution.
<!-- charter: /opinion -->

## Evidence

- Deliverables: `docs/examples/outcome-review.md:1` (56 lines), linked at `docs/daily-use.md:104`. All sample revisions, commands, receipts, dates, observers and measurements are explicitly hypothetical; the sample block is marked illustrative/opinion.
- Template review: sample frontmatter uses only id, title, status, priority, created, updated, perimeter, decisions and kind, all in `package/charter/templates/unit.md:1`; its body uses Context, Acceptance, Evidence and Log from `package/charter/templates/unit.md:18`. Observation details stay in those body sections, with technical criteria in Acceptance. No new schema fields/statuses or actual gate changes were introduced.
- Content review: `docs/examples/outcome-review.md:24` names the operator, 18/120 baseline, at-most-5% expectation, observer and dated window with minimum denominator 120. `docs/examples/outcome-review.md:34` separates revision/test evidence, a delivery receipt, not-observed-yet, an inconclusive 1/8 early observation and a completed 5/125 observation. Sample arithmetic is consistent: 18/120 = 15%, 1/8 = 12.5%, 5/125 = 4%.
- Decision review: `docs/examples/outcome-review.md:51` covers continue/adjust/stop/revert, inconclusive usage, no silent reopening and no authority to deploy/revert. The real owner boundary is cited to `package/.claude/rules/charter.md:57`; the present-need-only ask guidance is grounded in `/home/gui/Projects/tele-claude/docs/OWNER_DESK.md:54`. No real customer result, outcome acceptance, pilot or Owner Desk ask is claimed.
- `$ python3 -B package/.charter/bin/charter probe 20261024-135242-factory-outcome-example --json` → exit 0, AC-1–AC-3 passed. Actual per-probe results:
- `$ test -f docs/examples/outcome-review.md && python3 -B package/.charter/bin/charter anchors docs/examples/outcome-review.md` → exit 0
- `$ python3 -B -c "from pathlib import Path; p=Path('docs/examples/outcome-review.md'); s=p.read_text(); assert 0 < len(s.splitlines()) <= 100; assert all(h in s for h in ('## Context','## Acceptance','## Evidence','## Log')); assert '(examples/outcome-review.md)' in Path('docs/daily-use.md').read_text()"` → exit 0
- `$ git diff --check -- docs/examples/outcome-review.md docs/daily-use.md` → exit 0
- `$ python3 -B package/.charter/bin/charter anchors docs/examples/outcome-review.md docs/daily-use.md` → exit 0 for both: example has 2 factual claims, both anchored, no unanchored or unresolved references; illustrative observations are excluded, not validated as facts.
- Changes remain uncommitted on baseline a2067b4; the documentation deliverable is complete without a real deployment or observation (`docs/examples/outcome-review.md:8`).

## Log

- 2026-10-24 13:52 UTC: Created as a documentation example from the owner's request. No actual observations, acceptance, or pilot results are claimed (`docs/review/2026-10-24-ai-native-sdlc-factory-review.md`).
- 2026-10-24: Baseline commands executed: AC-1 and AC-2 exit 1 because the example is absent; AC-3 guard exits 0. Tasket schema, group ordering and tele-claude reader round-trip passed (reported in the authoring-session validation output).
- 2026-10-24 14:06 UTC: Started after unit 2's probes and semantic review passed. `$ python3 -B package/.charter/bin/charter probe 20261024-135242-factory-outcome-example` reproduced AC-1 exit 1 (missing example), AC-2 exit 1 (FileNotFoundError), AC-3 exit 0. No real observation or pilot is authorized by this example.
- 2026-10-24 14:08 UTC: Completed source-template and content review; `$ python3 -B package/.charter/bin/charter probe 20261024-135242-factory-outcome-example --json` reports AC-1–AC-3 passed. Example and daily-use anchors pass; marked done for the documentation example only.
- 2026-10-24 14:10 UTC: Final group pass after both daily-guide links landed: `$ python3 -B package/.charter/bin/charter probe 20261024-135242-factory-outcome-example --json` reports AC-1, AC-2 and AC-3 exit 0 (record retained in `/tmp/charter-quick-wins-WaBWpL/20261024-135242-factory-outcome-example.json`). `$ git diff --check` exits 0. Final anchors, reader metadata, group rank/order and structural done-evidence checks passed; prose was reviewed against the sources listed in Evidence. Shared release work and dated research remain outside this deliverable; no commit or publication.
