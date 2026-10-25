# An optional outcome check in an ordinary tasket

The unit template already supplies Context, Acceptance, Evidence and Log; its existing fields suffice for this example (`package/charter/templates/unit.md:1`, `package/charter/templates/unit.md:18`). A done record makes evidence reviewable without judging its truth (`README.md:7`).

<!-- charter: opinion -->
Use this example when a later observation would help decide whether a change was useful. It is optional guidance, with no new fields, statuses or gates. Keep technical acceptance separate from the product hypothesis: a technically correct change can fail to help.

**Everything in the sample below is hypothetical**, including dates, commands, revisions, deployment receipts, observers and measurements. No customer result, deployment or pilot has occurred as part of writing it. Replace placeholders with real evidence only when it exists.

```yaml
---
id: 20261102-090000-import-preview
title: Explain empty-row errors before CSV import
status: done
priority: p2
created: 2026-11-02
updated: 2026-11-09
perimeter: [app/import_preview.py, tests/test_import_preview.py]
decisions: []
kind: work
---
```

## Context

Hypothetical operation: a support operator imports customer CSV files. Empty-row errors appear only after submission, causing manual correction and retries. In the baseline week, 18 of 120 submitted imports needed operator correction (15%); count each submitted import once, even if it contains several invalid rows.

Hypothesis: explaining empty rows in the preview reduces imports needing correction to at most 5%, with at least 120 submitted imports in the observation window. The support lead observes the same counter and definition from 2026-11-03 through 2026-11-09 UTC, after delivery. They record the denominator, changed traffic mix and other releases before interpreting the comparison; this is a hypothesis, not technical acceptance.

## Acceptance

- [x] AC-1: Preview identifies empty rows before submission — probe: `python3 -m unittest tests.test_import_preview.EmptyRows`
- [x] AC-2: (guard) Valid CSV imports retain their preview and submission behavior — probe: `python3 -m unittest tests.test_import_preview.ValidRows`

## Evidence

- Hypothetical technical evidence: implementation revision `<implementation-revision>`; `app/import_preview.py:<line>`; `$ python3 -m unittest tests.test_import_preview.EmptyRows` → exit 0, failed at the baseline; `$ python3 -m unittest tests.test_import_preview.ValidRows` → exit 0, guard passed at baseline. These placeholders are not resolving anchors or actual test runs.
- Hypothetical delivery evidence: `<release-receipt>` identifies the target environment, running revision `<implementation-revision>` and changed-path smoke result. A code commit alone is not this receipt.
- Hypothetical delivery-day observation, 2026-11-02: **not observed yet**; no post-delivery imports. Technical acceptance is complete; usefulness is unknown.
- Hypothetical early observation, 2026-11-04: 1 of 8 submitted imports needed correction (12.5%). Inconclusive: the minimum denominator is unmet and the window is still open. Keep observing; do not call this success or failure.
- Hypothetical completed observation, 2026-11-09: 5 of 125 needed correction (4%) during the declared window, versus 18 of 120 (15%) at baseline. The minimum denominator and target were met. The support lead records similar traffic mix and no known concurrent import change, but the comparison does not prove causation. Decision: continue using the preview; no further implementation is implied.

## Log

- 2026-11-02 09:00 UTC (hypothetical): Started; EmptyRows fails at baseline, ValidRows passes as a guard.
- 2026-11-02 11:00 UTC (hypothetical): Both technical probes pass at `<implementation-revision>`; checked acceptance and recorded done.
- 2026-11-02 14:00 UTC (hypothetical): Authorized delivery recorded in `<release-receipt>`; outcome not observed yet.
- 2026-11-04 17:00 UTC (hypothetical): 1/8 correction rate; observation inconclusive, continue to the agreed window.
- 2026-11-09 17:00 UTC (hypothetical): 5/125 correction rate; support lead chooses continue, with attribution uncertainty retained in Evidence.

After the window, the observer compares the observation with the declared expectation and chooses **continue**, **adjust**, **stop** or **revert**. With insufficient usage, record “inconclusive” and agree whether a longer window is useful. Adjust can become a new tasket; stop can mean dropping the hypothesis or further investment. Revert is a proposed action needing the project's usual authorization and checks, not an instruction to execute it.

A failed hypothesis does not silently reopen a technically completed unit or authorize deployment/revert. Put the observation and decision in Evidence and Log; create future work only if someone chooses it. The sample's future observation date is a planning note, not a scheduled job or a present request for the owner.
<!-- charter: /opinion -->

Owner Desk is for a present owner need that state cannot derive: agents file/read, and the owner acts. File an ask only when an actual decision or owner-only action is needed now; a future observation window alone is not such an ask (`/home/gui/Projects/tele-claude/docs/OWNER_DESK.md:54`). Deployment and public release remain owner commitments (`package/.claude/rules/charter.md:57`).
