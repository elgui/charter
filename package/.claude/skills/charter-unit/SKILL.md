---
name: charter-unit
description: Start, resume or finish a unit of work under the charter method. USE WHEN the user names a tasket to work on, says "start this unit", "resume", "pick up", "what is left on this", "mark it done", "finish the unit", OR when you are about to change code and no unit is active.
---

# charter-unit

## Start or resume

1. `python3 .charter/bin/charter unit start <tasket-id>`. If the user named no unit, `python3 .charter/bin/charter next` lists the open units in the road's order; take one from there. If the tasket does not exist, create it from `charter/templates/unit.md` into `.taskets/` (keep the engines' keys: `id`, `title`, `status`, `priority`, `group`, `group_order`, `order` when grouped).
2. Read the unit. Its `## Log` is the state; the transcript is not. Say in one line where it stands.
3. Check the unit cites a scope item (`scope:`) on the client track, and that every `## Acceptance` line names a probe you can run. Fix the unit before touching code; once it leaves `next` or `later`, a changed criterion needs a `## Log` line saying why. Sort each criterion: mechanical proof (a probe decides it) or an owner observation or judgment (taste, risk, a device or account only the owner has, a human review the unit keeps). For the second kind, write now why a person is needed, the observable result or judgment, who prepares it and what package they hand over; "the owner reviews the result" is not a criterion, and no probe is invented to avoid the owner.
4. Run the baseline probes (`python3 .charter/bin/charter probe <id>`) and append the results as the first `## Log` line of this session.

## While working

- Stay inside `perimeter:`; note any excursion under `## Outside perimeter` before committing.
- End each commit subject with `(unit <id>)`, and commit only your own paths (`git commit -m <message> -- <paths>`): `charter unit show <id>` and `charter synth` read the tag to report how the perimeter fit the work, and the checkout's index may hold another session's files.
- Cite decisions in code with `charter:<id>`; create a decision record when you settle something other code will depend on (`/charter-decision`).
- Append a dated `## Log` line when something lands. After a turn that committed, the Stop hook reminds you if the unit's log did not move.

## Finish

1. `python3 .charter/bin/charter probe <id>`; check each agent-owned `- [x] AC-n` only after its probe passed. Leave owner lines open. Before you surface one, finish every part of it an agent can finish, then prepare the human task through the configured owner interface: one specific question, an entry the owner can open (or the material inline, or the device), a finite path of actions with the result to expect, the technical evidence already completed, and what you could not verify (access you did not exercise, judgment that remains). Rehearse that path on the final candidate. Surface the `charter owner --json` acceptance contract with the exact project, source and criterion; never hand the owner raw logs, a bare path or a checkbox to hunt for or edit. Technical review, where `review.required` or the unit asks for it, happens before this and never stands in for the owner's closure. Only the owner confirms acceptance; agents never run `charter accept`.
2. Under `## Evidence`: the commit SHA(s), the `path:line` of the change, and the `$ command` lines `charter probe` printed. A path or a URL alone is refused. If `charter/config.json` sets `review.required`, add `- review: <reviewer and model> — <verdict> — <anchor>` pointing at the independent review.
3. Set `status: done`. The gate refuses it if a box is unchecked, no commit or run is cited, or an anchor does not resolve; the refusal names what to add. A project with `probes.at_commit` or `probes.in_ci` set re-runs the probes when the unit closes.
4. Your final message cites the same evidence. A done claim without a commit, a `path:line` or a run is blocked once by the Stop hook.
