---
id: 20261024-135240-factory-engine-docs
title: Correct the stale tele-claude integration description
status: done
priority: p2
created: 2026-10-24
updated: 2026-10-24
category: tooling
tags: [charter, documentation, factory]
origin: ai-native-sdlc-review-20261024
group: factory-quick-wins
group_order: 100
order: 1
plan: true
perimeter: [docs/method.md]
decisions: []
kind: work
---

## Context

This is the Charter source repository, not a project with Charter installed. Read `AGENTS.md`; do not run setup or install Charter to execute this unit. The research report identified a concrete documentation defect: `docs/method.md:234` says tele-claude still needs Charter metadata added to its tasket reader and does not export the active unit. The reader already passes the fields, and worker attribution constructs `CHARTER_UNIT` (`/home/gui/Projects/tele-claude/services/project_tasket_reader.py:229`, `/home/gui/Projects/tele-claude/services/step_close.py:138`; `docs/review/2026-10-24-ai-native-sdlc-factory-review.md:63`).

The surrounding heading, "Seams designed, not built", also includes implemented behavior. Its external-contributor proposal remains a proposal. Recheck the current source when executing: tele-claude's launch wiring was being refactored into `services/harness_adapter.py` during the investigation. Do not infer tcv2's current implementation from tele-claude's (`docs/method.md:230`; `/home/gui/Projects/tele-claude/services/harness_adapter.py:184`).

<!-- charter: opinion -->
## Approach

Autonomy: routine documentation work; no owner action needed to prepare and verify it.

1. Re-read the current method paragraph and trace the tasket reader plus worker launch call into `worker_env_exports`. Identify committed behavior separately from concurrent edits.
2. Correct only the engine paragraph and its containing heading. Separate implemented integration from the still-proposed contributor brief. Cite current path:line evidence or a stable repository URL. Leave historical tcv2 statements qualified unless independently verified.
3. Record a short claim-to-source review in Evidence. Preserve other cards' release/version edits in the same document. Do not change either product or rewrite the dated research report.

## Acceptance

- [x] AC-1: The obsolete claims that tele-claude needs the fields added and neither engine exports the unit are removed, and the heading no longer labels every seam unbuilt — probe: `python3 -B -c "from pathlib import Path; s=Path('docs/method.md').read_text(); p=s.split('**Engines.**',1)[1].split('\n\n',1)[0]; assert 'needs four names added' not in p and 'neither engine does yet' not in p; assert '## Seams designed, not built' not in s"`
- [x] AC-2: The revised Engines paragraph cites the metadata reader and unit-attribution implementation, and its anchors resolve — probe: `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'package/.charter'); import checks; p=Path('docs/method.md').read_text().split('**Engines.**',1)[1].split('\n\n',1)[0]; assert 'project_tasket_reader.py' in p and 'step_close.py' in p; report=checks.check_anchors(Path.cwd(),p); print(report); assert report.ok"`
- [x] AC-3: (guard) The method edit has no whitespace errors — probe: `git diff --check -- docs/method.md`

These probes establish removal and reference structure, not the truth of prose. Evidence must also explain how the reader and actual launch caller support the replacement claims. No product test or package release is required for this documentation-only unit.
<!-- charter: /opinion -->

## Evidence

- Replacement: `docs/method.md:230` separates integration from proposals; `docs/method.md:234` describes the reader and worker attribution. The contributor proposal remains unchanged.
- Claim review: the reader's optional-key loop copies all four metadata fields (`/home/gui/Projects/tele-claude/services/project_tasket_reader.py:229`). `worker_env_exports` calls `_worker_env`, which includes `CHARTER_UNIT` only when given a unit id; `judged_tasket_id` walks injected fix-step parents (`/home/gui/Projects/tele-claude/services/step_close.py:138`, `/home/gui/Projects/tele-claude/services/step_close.py:183`).
- Launch review: `$ git -C /home/gui/Projects/tele-claude show f13e407f46ecf5964ef8d2985022eb597edc069b:services/group_automator.py` shows committed `worker_command` passing project task ids into that export and prefixing the worker command. The current caller does the same in `/home/gui/Projects/tele-claude/services/harness_adapter.py:184`; `$ git -C /home/gui/Projects/tele-claude status --short -- services/harness_adapter.py services/group_automator.py services/step_close.py services/project_tasket_reader.py` shows the adapter added and automator modified in the index, with the reader and attribution helper unchanged. No runtime launch or current tcv2 behavior was verified.
- `$ python3 -B package/.charter/bin/charter probe 20261024-135240-factory-engine-docs` → exit 0: AC-1 removal/heading, AC-2 paragraph anchors and AC-3 whitespace each exit 0.
- `$ python3 -B package/.charter/bin/charter anchors docs/method.md` → exit 0: 66 claims, 64 anchored, 2 admitted, no unanchored claims or unresolved references.
- Actual per-probe results from `$ python3 -B package/.charter/bin/charter probe 20261024-135240-factory-engine-docs --json`:
- `$ python3 -B -c "from pathlib import Path; s=Path('docs/method.md').read_text(); p=s.split('**Engines.**',1)[1].split('\n\n',1)[0]; assert 'needs four names added' not in p and 'neither engine does yet' not in p; assert '## Seams designed, not built' not in s"` → exit 0
- `$ python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0,'package/.charter'); import checks; p=Path('docs/method.md').read_text().split('**Engines.**',1)[1].split('\n\n',1)[0]; assert 'project_tasket_reader.py' in p and 'step_close.py' in p; report=checks.check_anchors(Path.cwd(),p); print(report); assert report.ok"` → exit 0
- `$ git diff --check -- docs/method.md` → exit 0
- Changes remain uncommitted on baseline a2067b4; no new implementation SHA is claimed. The other card's version-line edit is preserved (`$ git diff -- docs/method.md`).

## Log

- 2026-10-24 13:52 UTC: Created from the owner's request for simple units. Status is later; no implementation or execution launched. The old paragraph was still present when authored (`docs/method.md:234`).
- 2026-10-24: Baseline commands executed: AC-1 and AC-2 exit 1 as expected before the correction; AC-3 guard exits 0. Tasket schema, group ordering and tele-claude reader round-trip passed (reported in the authoring-session validation output).
- 2026-10-24 14:02 UTC: Started attended documentation work. `$ python3 -B package/.charter/bin/charter probe 20261024-135240-factory-engine-docs` reproduced AC-1 and AC-2 exit 1 (AssertionError), AC-3 exit 0. `$ python3 -B package/.charter/bin/charter anchors docs/method.md docs/daily-use.md .taskets/20261024-135240-factory-engine-docs.md .taskets/20261024-135241-factory-verification-guide.md .taskets/20261024-135242-factory-outcome-example.md` passed all five files before edits; no pre-existing anchor failure to exclude.
- 2026-10-24 14:04 UTC: Completed AC-1–AC-3 after source and launch-caller review; `$ python3 -B package/.charter/bin/charter probe 20261024-135240-factory-engine-docs` gives all three probes exit 0 and method anchors pass (commands in Evidence). Marked done for this documentation deliverable; no product behavior, installation, commit or publication performed.
- 2026-10-24 14:10 UTC: Final group pass after both daily-guide links landed: `$ python3 -B package/.charter/bin/charter probe 20261024-135240-factory-engine-docs --json` reports AC-1, AC-2 and AC-3 exit 0 (record retained in `/tmp/charter-quick-wins-WaBWpL/20261024-135240-factory-engine-docs.json`). `$ git diff --check` exits 0. Final anchors, reader metadata, group rank/order and structural done-evidence checks passed; prose was reviewed against the sources listed in Evidence. Shared release work and dated research remain outside this deliverable; no commit or publication.
