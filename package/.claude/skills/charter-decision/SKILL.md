---
name: charter-decision
description: Record a design decision, a lesson, or a change request under the charter method. USE WHEN a choice is made that other code will depend on, when the user says "record the decision", "write that down", "this is out of scope", "the client wants something else", "change request", "lesson learned", OR when a gate refused an edit for a retired decision or an out-of-scope path.
---

# charter-decision

## A design decision

1. Copy `charter/templates/decision.md` to `charter/decisions/<slug>.md`. The slug is the id.
2. Fill `## Decision` (current state, one paragraph), `## Because` (the case: incident, measurement or constraint, with anchors) and `## Stops applying when`. Set `expires:` to a date or a condition.
3. If files must cite it, set `binds:` to their globs and add `charter:<slug>` in a comment in each. If it can be checked by a command, set `check:`.
4. Status `proposed` when the owner must settle it (commitments, anything touching the scope, price or dates); `active` otherwise. Never edit an active decision: write a new file with `supersedes: <old-id>` and tell the owner, who sets the old one's `status: superseded` and `superseded_by:`. Changing the `status`, `check:` or `binds:` of an existing decision is refused to an agent. Each decision needs its own id; a file that takes another's id is refused.
5. `python3 .charter/bin/charter decisions index`.

## A lesson

Same file, `kind: lesson`, `owner:` set. A lesson without the case that justified it is a warning in `charter check --memory`. Do not write project lessons into personal auto-memory.

## A change request

1. Copy `charter/templates/change.md` to `charter/changes/<slug>.md`, status `proposed`, `paths:` naming what it would touch.
2. Say so to the owner in your final message. Only the owner sets `approved`, `approved_by` and `approved_on`; an agent's edit of those fields is refused. Until all three are set the paths stay refused by the scope gate.
