# A `path:line` anchor to `.charter/bin/charter` is read as a decision marker

- Seen: 2026-09-27, hermes-custom at `4a4526a`, charter 0.4.6
- Status: open

## What happened

Writing a tasket whose `## Context` cited the CI base handling as `` `.charter/bin/charter:131` `` was refused by the PreToolUse gate:

```
charter gate refused this edit.
- charter/decisions block [.taskets/20260927-1800-decision-markers.md]: .taskets/20260927-1800-decision-markers.md cites decision `131` which does not exist Override: create charter/decisions/131.md or fix the marker
```

Expected: `.charter/bin/charter:131` is a `path:line` anchor, the form `.claude/rules/charter.md` asks for in reports. It names no decision.

## Reproduce

In any charter project, Write a `.taskets/<id>.md` (or any gated file) containing the text `.charter/bin/charter:131`.

## Where

The marker scan matches `charter:<id>` wherever it appears, so the tail of the path `.charter/bin/charter` followed by `:131` qualifies (inference: the regex was not read; the refusal message names decision `131`).

## Workaround

Write the anchor as "line 131 of `.charter/bin/charter`". The tasket in hermes-custom does that.

## Suggested fix

Only count `charter:<id>` when not preceded by a path character (`/`, `.`, word character), and/or require the id to match an existing decision's slug shape (digits alone are never a slug the template produces).
