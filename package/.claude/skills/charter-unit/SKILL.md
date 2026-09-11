---
name: charter-unit
description: Start, resume or finish a unit of work under the charter method. USE WHEN the user names a tasket to work on, says "start this unit", "resume", "pick up", "what is left on this", "mark it done", "finish the unit", OR when you are about to change code and no unit is active.
---

# charter-unit

## Start or resume

1. `python3 .charter/bin/charter unit start <tasket-id>`. If the tasket does not exist, create it from `charter/templates/unit.md` into `.taskets/` (keep the engines' keys: `id`, `title`, `status`, `priority`, `group`, `group_order`, `order` when grouped).
2. Read the unit. Its `## Log` is the state; the transcript is not. Say in one line where it stands.
3. Check the unit cites a scope item (`scope:`) on the client track, and that every `## Acceptance` line names a probe you can run. Fix the unit before touching code.
4. Run the baseline probes and append the results as the first `## Log` line of this session.

## While working

- Stay inside `perimeter:`; note any excursion under `## Outside perimeter` before committing.
- Cite decisions in code with `charter:<id>`; create a decision record when you settle something other code will depend on (`/charter-decision`).
- Append a dated `## Log` line when something lands.

## Finish

1. Run every probe; check each `- [x] AC-n` only after its probe passed.
2. Under `## Evidence`: the commit SHA(s), the `path:line` of the change, each probe as a `$ command` line with its result.
3. Set `status: done`. The gate refuses it if a box is unchecked or the evidence does not resolve; the refusal names what to add.
4. Your final message cites the same evidence. A done claim without anchors is blocked once by the Stop hook.
