# Charter rules

This project runs under the charter method (`charter/`, `.charter/`). Full text: `charter/README.md`.

## Before you change code

- Start the unit you are working on: `python3 .charter/bin/charter unit start <tasket-id>`. Edits without an active unit are logged as unattributed.
- Read the unit's `## Acceptance` list. Each line is a probe you will run. If a probe cannot be named, write it before coding.
- On the client track, the unit's `scope:` must name an item in `charter/scope.md`. Work outside the scope is a change request in `charter/changes/`, not a commit.

## While you work

- Code that depends on a decision carries `charter:<decision-id>` in a comment. A decision with `check:` is verified at every commit.
- Stay inside the unit's `perimeter:`. If you must touch a file outside it, add `- <path>: <why>` under `## Outside perimeter` in the unit before committing.
- A file over the size limit is frozen. Create a unit with `kind: split` to split it; do not grow it.
- Append a dated line to the unit's `## Log` when something lands or when you stop. A resumed session reads the unit, not the transcript.

## Before you say done

- `done` is refused without: every acceptance box checked, and `## Evidence` holding a commit SHA, a `path:line`, or a `$ command` run that resolves.
- A final message that claims completion cites its evidence or says plainly what is not done. The Stop hook blocks such a message once.
- Reports, PR descriptions and syntheses are checked by `python3 .charter/bin/charter anchors <file>`: every claim line needs an anchor or an explicit `(unverified)`.

## Decisions and memory

- A design decision that other code depends on goes in `charter/decisions/<slug>.md` (template in `charter/templates/decision.md`), with the case that justified it and when it stops applying. Do not put it in `CLAUDE.md`.
- A lesson that should bind this project is a decision with `kind: lesson`. Personal auto-memory is for your own habits, never for project rules.
- Commitments to the client (scope, price, dates) are the owner's alone: propose a change request, do not decide.

## Commands

    python3 .charter/bin/charter check --all      # run every gate on the tree
    python3 .charter/bin/charter synth            # progress synthesis, anchored
    python3 .charter/bin/charter anchors <file>   # anchoring check on a deliverable
    python3 .charter/bin/charter decisions index  # regenerate the decision index
    python3 .charter/bin/charter log              # what the gates did lately
