---
id: 20261024-135241-factory-verification-guide
title: Explain what each verification path actually proves
status: done
priority: p2
created: 2026-10-24
updated: 2026-10-24
category: tooling
tags: [charter, documentation, verification]
origin: ai-native-sdlc-review-20261024
group: factory-quick-wins
group_order: 100
order: 2
plan: true
perimeter: [docs/verification.md, docs/daily-use.md]
decisions: []
kind: work
---

## Context

Read this source repository's `AGENTS.md` and the research findings at `docs/review/2026-10-24-ai-native-sdlc-factory-review.md:65`. A checked tasket, a probe run, an anchored review line, a chain review and tele-claude's checker are different assurances. Package defaults leave probe execution and required review off (`package/charter/config.json:11`); unexpected gate errors deliberately fail open (`package/.charter/bin/charter:1295`). The relevant behavior is documented across `docs/gates.md:161`, `docs/gates.md:174` and `docs/daily-use.md:35`, but there is no compact comparison for a reader deciding what a completion claim establishes.

Implementation evidence: structural done/review checks at `package/.charter/checks.py:389` and `package/.charter/checks.py:429`; chain review responses at `package/.charter/chain_groups.py:164`; tele-claude probe execution at `/home/gui/Projects/tele-claude/services/checker/core.py:537` and revision freshness at `/home/gui/Projects/tele-claude/services/step_close.py:671`.

<!-- charter: opinion -->
## Approach

Autonomy: routine documentation work; the deliverable describes existing behavior and changes no policy.

1. Add `docs/verification.md`, at most 120 lines. Compare ordinary done checks, enabled commit/CI probes, required-review lines, chain reviews, and the tele-claude checker. Each row states how it is enabled, what it checks, and what it cannot establish, with source citations.
2. Explain that gate errors, unknown results, and missing checks must be disclosed when reporting evidence even though existing exit behavior remains unchanged. Distinguish work recorded as done, a specific check passed at a revision, a change delivered, and an outcome observed; these are reporting distinctions, not new tasket statuses.
3. Include a short example completion statement naming the revision, commands, results, configuration and unverified limits. Link the guide once from `docs/daily-use.md`. Instructions for checking a project's effective config must target that installed project, not pretend this source checkout runs Charter.

## Acceptance

- [x] AC-1: The concise guide covers all five verification paths, their activation, guarantees and limits; every factual paragraph or table row has resolving evidence — probe: `test -f docs/verification.md && python3 -B package/.charter/bin/charter anchors docs/verification.md`
- [x] AC-2: The guide remains at most 120 lines and the daily guide links it — probe: `python3 -B -c "from pathlib import Path; p=Path('docs/verification.md'); assert 0 < len(p.read_text().splitlines()) <= 120; assert '(verification.md)' in Path('docs/daily-use.md').read_text()"`
- [x] AC-3: (guard) The documentation edits have no whitespace errors — probe: `git diff --check -- docs/verification.md docs/daily-use.md`

Passing anchors proves reference structure only. Record the five-row source review in Evidence; do not claim this unit strengthened the actual gates. No package change, new test suite, automatic opt-in, rollout, or new approval step belongs here.
<!-- charter: /opinion -->

## Evidence

- Deliverables: the five-path comparison and reporting example in `docs/verification.md:1` (40 lines), linked from `docs/daily-use.md:100`.
- Source review, ordinary done: `package/.charter/checks.py:389` checks boxes and resolving commit/run evidence, not truth; `package/.charter/bin/charter:152` selects closing units (or all with strict). Defaults disable probe/review opt-ins (`package/charter/config.json:11`).
- Source review, probes: the flag/config choice and unstaged-tree refusal are in `package/.charter/bin/charter:122` and `package/.charter/bin/charter:169`. `package/.charter/checks.py:592` runs non-guards at base and chooses warning versus block with `base_must_fail`; direct probe calls only the current-tree runner (`package/.charter/bin/charter:995`).
- Source review, required review: `package/.charter/checks.py:429` matches a review line with a resolving anchor; it does not authenticate a reviewer or execute review. The guide distinguishes that mechanism from the independent review described at `docs/daily-use.md:110`.
- Source review, chain review: `package/.charter/chain_groups.py:86` resolves auto/codex/off/custom modes; `package/.charter/chain_groups.py:340` reads a detached committed range; `package/.charter/chain_groups.py:164` checks answer form and descendant commit ancestry. Resume can skip review (`package/.charter/chain_groups.py:538`); `docs/gates.md:174` records the truth and repeat-review limits.
- Source review, tele-claude checker: `/home/gui/Projects/tele-claude/services/step_close.py:344` invokes the separate checker for project tasks and rejects dirty work. `/home/gui/Projects/tele-claude/services/checker/core.py:451` checks authors/files, and `/home/gui/Projects/tele-claude/services/checker/core.py:537` compares acceptance to base before running probes; `/home/gui/Projects/tele-claude/services/step_close.py:671` checks HEAD/tree freshness before closure. Person credit is labeled separately at `/home/gui/Projects/tele-claude/services/step_close.py:637`. These are inspected implementation paths, not a live automation run.
- Error/config review: `package/.charter/bin/charter:1295` catches unexpected gate errors with exit 0; `package/.charter/bin/charter:1024` reports effective config. Installed-project instructions and the explicitly hypothetical completion statement do not claim settings were changed or a deployment occurred.
- `$ python3 -B package/.charter/bin/charter probe 20261024-135241-factory-verification-guide --json` → exit 0, AC-1–AC-3 passed. Actual per-probe results:
- `$ test -f docs/verification.md && python3 -B package/.charter/bin/charter anchors docs/verification.md` → exit 0
- `$ python3 -B -c "from pathlib import Path; p=Path('docs/verification.md'); assert 0 < len(p.read_text().splitlines()) <= 120; assert '(verification.md)' in Path('docs/daily-use.md').read_text()"` → exit 0
- `$ git diff --check -- docs/verification.md docs/daily-use.md` → exit 0
- `$ python3 -B package/.charter/bin/charter anchors docs/verification.md docs/daily-use.md .taskets/20261024-135240-factory-engine-docs.md` → exit 0 for each; guide: 8 claims all anchored, no unanchored or unresolved references.
- Changes are uncommitted on baseline a2067b4; no gate was strengthened and no package file was edited by this unit (`docs/verification.md:40`).

## Log

- 2026-10-24 13:52 UTC: Created as a small documentation deliverable from the research. No implementation or execution launched (`docs/review/2026-10-24-ai-native-sdlc-factory-review.md`).
- 2026-10-24: Baseline commands executed: AC-1 and AC-2 exit 1 because the guide is absent; AC-3 guard exits 0. Tasket schema, group ordering and tele-claude reader round-trip passed (reported in the authoring-session validation output).
- 2026-10-24 14:04 UTC: Started after unit 1's probes passed. `$ python3 -B package/.charter/bin/charter probe 20261024-135241-factory-verification-guide` reproduced AC-1 exit 1 (missing guide), AC-2 exit 1 (FileNotFoundError), AC-3 exit 0. Implementation is limited to the guide and its daily-use link.
- 2026-10-24 14:06 UTC: Completed after the five-row semantic review; `$ python3 -B package/.charter/bin/charter probe 20261024-135241-factory-verification-guide --json` reports AC-1–AC-3 passed. Guide and daily-use anchors pass; marked done without enabling any checks or claiming delivery/outcomes.
- 2026-10-24 14:10 UTC: Final group pass after both daily-guide links landed: `$ python3 -B package/.charter/bin/charter probe 20261024-135241-factory-verification-guide --json` reports AC-1, AC-2 and AC-3 exit 0 (record retained in `/tmp/charter-quick-wins-WaBWpL/20261024-135241-factory-verification-guide.json`). `$ git diff --check` exits 0. Final anchors, reader metadata, group rank/order and structural done-evidence checks passed; prose was reviewed against the sources listed in Evidence. Shared release work and dated research remain outside this deliverable; no commit or publication.
