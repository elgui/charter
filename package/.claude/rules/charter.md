# Charter rules

This project runs under the charter method (`charter/`, `.charter/`). Full text: `charter/README.md`.

## Before you change code

- Start the unit you are working on: `python3 .charter/bin/charter unit start <tasket-id>`. Edits without an active unit are logged as unattributed. An engine sets `CHARTER_UNIT=<id>` instead; the environment wins over the file.
- Read the unit's `## Acceptance` list (`## Done When` in a tasket the Tasket skill wrote). Each line is a probe you will run. If a probe cannot be named, write it before coding.
- On the client track, the unit's `scope:` must name an item in `charter/scope.md`. Work outside the scope is a change request in `charter/changes/`, not a commit.
- Where `charter/rails.md` exists, the unit's `rail:` (or its `roadmap:` anchor) must name an open item of it. Work the road does not name is not started: ask the owner to add a rail item first, because that is the re-plan.
- If the session banner says the git hook is not active, run `python3 .charter/bin/charter setup` once. If it says the clone runs other git hooks, tell the owner instead; `setup` would stop them.

## While you work

- Code that depends on a decision carries `charter:<decision-id>` in a comment. A decision with `check:` is verified in CI and by `charter check --all`, and at commit when a staged path matches its `binds:`; a `check:` with no `binds:` does not run at commit.
- Stay inside the unit's `perimeter:`. If you must touch a file outside it, add `- <path>: <why>` under `## Outside perimeter` in the unit before committing.
- A file over the size limit is frozen. Move code out of it into a new file (shrinking is always allowed); a `kind: split` unit that lets it grow is opened by the owner.
- Once a unit has left `next` or `later`, changing or removing an acceptance line needs a dated `## Log` line in the same edit.
- Append a dated line to the unit's `## Log` when something lands or when you stop. A resumed session reads the unit, not the transcript.
- Keep comments in frontmatter on their own lines: an engine reads `status: done  # x` as the status `done  # x`.

## Before you say done

- `done` is refused without: every acceptance box checked, and `## Evidence` naming a commit SHA that resolves or a `$ command` run. A path or a URL alone is not evidence. `python3 .charter/bin/charter probe <id>` runs the probes and prints the `$ command` lines.
- A final message after a turn that edited files or committed, and that claims completion, cites a commit, a `path:line` or a `$ command` run, or says plainly what is not done. The Stop hook blocks such a message once.
- Reports and syntheses are checked by `python3 .charter/bin/charter anchors <file>`: every claim line needs an anchor, or a marker that admits it as reported or inference: `(reported in ...)`, `(operator report ...)`, `(inference ...)`, `(unverified)`, `(estimate ...)`. A pull-request description is checked with `--pr`, as a warning.

## What only the owner changes

These are refused to an agent's Edit and Write, and CI checks that the owner authored them. Propose instead: a change request, a new decision that supersedes, a note in your final message.

- `charter/scope.md`, `charter/rails.md`, `charter/config.json`, `.charter/**`, `.claude/settings.json`, `.claude/settings.local.json`, `.github/workflows/charter.yml`, and adding an id to `charter/legacy-taskets.txt`. An upgrade is the exception: package files exactly as the installer wrote them, matching `.charter/manifest.json`, are yours to commit.
- In a change request: `status:` other than `proposed`, `approved_by:`, `approved_on:`, and the `paths:` of an approved one.
- In an existing decision: `status:`, `superseded_by:`, and the `check:` and `binds:` of an active one.
- Opening or widening a `kind: split` unit.
- Closing an acceptance line marked `— owner:` (ticking, unmarking or removing it): the owner closes it, with `/resume-chain ok` when a chain waits on it.
- Running a waiting chain's acts: `charter owner run` is the owner's command (the hook denies it to an agent). Give the owner the command, never run it.
- Committing an owner-only change. Leave it staged and run `python3 .charter/bin/charter handover`: it records the handover and prints the owner's one line, `CHARTER_OWNER=1 python3 <root>/.charter/bin/charter owner commit`. Give the owner that line verbatim (as `! <line>` for a Claude Code prompt); never run it (the hook denies it to an agent).
- Setting `CHARTER_OWNER` anywhere (the hook denies a Bash command that names it).
- Resuming a chain: `charter chain resume` refuses; the owner types `/resume-chain`.

The owner edits these by hand or in a Claude Code session started with `CHARTER_OWNER=1`. A ruling is one owner command: `charter rule <decision> active|rejected|superseded`, `charter approve <change> [--reject]` or `charter rail <id> <status>` writes it and commits it as the owner. An agent never runs these; it proposes, and `charter owner` shows the owner what waits.

## Decisions and memory

- A design decision that other code depends on goes in `charter/decisions/<slug>.md` (template in `charter/templates/decision.md`), with the case that justified it and when it stops applying. Do not put it in `CLAUDE.md`.
- A lesson that should bind this project is a decision with `kind: lesson`. Personal auto-memory is for your own habits, never for project rules.
- Commitments are the owner's alone. A commitment is anything that changes an external obligation: what is sold, price, dates, deployment, production data or schema, purchase or budget, public release, another person's work, widening a permission, merging into main. Propose it and wait for the owner's word; an instruction from the owner in this session is that word. For what is sold, price or dates, the proposal is a change request in `charter/changes/`.

## Subagents

- Staff a subagent where a real wait disappears, such as independent reads in parallel; do not staff a step whose inputs still move.
- Subagents read; the parent writes. A subagent that can run Bash is not read-only, so give it no task that edits, commits or deploys, and make every change in the parent session.
- Say in the unit's `## Log` why a subagent was used. `charter synth` shows the subagents' share of each unit's cost.

## Commands

    python3 .charter/bin/charter check --all      # run every gate on the change set since HEAD~1 (--base REF, --strict)
    python3 .charter/bin/charter probe <id>       # run a unit's acceptance probes, print evidence lines
    python3 .charter/bin/charter synth            # progress synthesis, anchored
    python3 .charter/bin/charter anchors <file>   # anchoring check on a deliverable
    python3 .charter/bin/charter decisions index  # regenerate the decision index
    python3 .charter/bin/charter log              # what the gates did lately
    python3 .charter/bin/charter setup            # activate the git hook in this clone
    python3 .charter/bin/charter config           # the track and opt-ins the gates read; problems in charter/config.json
    python3 .charter/bin/charter next             # the road, the next units, what waits on the owner; writes nothing
    python3 .charter/bin/charter chain status     # a continuous chain of sessions (`/charter-chain`); in a chain session, .charter/chain-rules.md also binds
    python3 .charter/bin/charter owner [--json]   # what waits on the owner, with the command for each; writes nothing
