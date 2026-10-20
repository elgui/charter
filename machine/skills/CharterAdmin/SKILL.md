---
name: CharterAdmin
description: Administer the charter method across this machine's projects, and migrate existing projects onto it. USE WHEN the user says "charter status", "upgrade charter", "install charter on", "fold the ledgers", "cost per accepted unit across projects", "which projects run charter", OR wants to migrate, move or onboard an existing project onto charter, survey a project before a charter install, or plan a charter migration, OR wants the open charter decisions put to them.
---

# CharterAdmin (machine layer)

The committed layer in each project never depends on this skill. It is installed once per user, from a charter checkout, by `python3 <checkout>/bin/charter-pkg machine install` (`machine/README.md` in the checkout).

## The checkout

`<checkout>` below is the charter repository this machine installs from. The machine layer's SessionStart hook names it in every charter project (`package repository: <path>`); outside one, use `$CHARTER_PKG_DIR`, or `source` in `~/.claude/hooks/charter-machine.json` when the layer was copied. Do not guess a path.

## This machine's additions

If `~/.claude/charter-local.md` exists, read its `## Admin` section before any procedure below. It is the user's: where their contracts live, which tool puts decisions to them, which notifications to send. It adds to these procedures and never relaxes a rule of `docs/install.md` or of a project's `.claude/rules/charter.md`.

## Workflow Routing

| Workflow | Trigger | File |
|----------|---------|------|
| **Migrate** | "migrate <project> to charter", "put charter on <project>", "survey <project> for charter", any install on a project that already has code, taskets or documents | `workflows/Migrate.md` |

The sections after the examples are short procedures for projects already on charter.

## Examples

**Example 1: Migrate an existing project**
```
User: "Put charter on my-app"
→ Invokes Migrate workflow
→ Runs `charter-pkg survey`, which reads the project and rehearses the install in a throwaway clone
→ Settles what the facts settle, puts the rest to the owner, rehearses the whole plan in a clone
→ Executes on a branch, one checked commit per step, only after the owner's go-ahead
→ Returns the survey, the plan with each check's output, and the decisions still open
```

**Example 2: Survey only**
```
User: "What would it take to put charter on my-app?"
→ Invokes Migrate workflow, phases 1 and 2
→ Returns the survey report and the generated plan; writes nothing to the project
```

**Example 3: Upgrade every project ("upgrade charter", "upgrade the projects")**
```
User: "Upgrade charter everywhere"
→ `python3 <checkout>/bin/charter-pkg fleet` to show the table, then `fleet --upgrade`
→ An upgrade of package files alone is committed by fleet itself (0.4.6); the table says `committed <sha>`
→ Returns the fleet's owner's line first, verbatim, as one line, if any project waits on the owner (a settings.json merge, a kept file): `CHARTER_OWNER=1 python3 <checkout>/bin/charter-pkg fleet --commit` from 0.4.12
→ Then one line per project: the version change, and any KEEP, IGNORED or NOTE line
```

**Example 4: Upgrade one project already on charter**
```
User: "Upgrade charter on my-app"
→ Follows "Install or upgrade" below: the dry run, then the upgrade on a branch, staged
→ Returns the owner's line the installer printed, verbatim, as one line (`CHARTER_OWNER=1 python3 <root>/.charter/bin/charter owner commit` from 0.4.12), then the diff
```

## Which projects, which version

    python3 <checkout>/bin/charter-pkg fleet            # read-only: version, branch, what waits on the owner
    python3 <checkout>/bin/charter-pkg status <project>

`fleet` looks for projects under `~/Projects`; `--root <dir>` names another directory.

Where one project stands and what comes next: `python3 .charter/bin/charter next` from 0.4.4. On an older install, run the checkout's copy against it; it only reads: `python3 <checkout>/package/.charter/bin/charter --root <project> next`.

## Install or upgrade

Follow `<checkout>/docs/install.md`: the preconditions, the track (`client` only when a signed contract covers the project, otherwise `prototype`), the dry run, the install or upgrade on a branch, then read the block the installer prints. `so an agent commits them`: run the command yourself (from 0.4.6, package files matching the manifest are not an owner-only change). `Waiting on the owner`: stop and open the report with the owner's line, the block's last line, copied verbatim as one line (`docs/install.md` step 8). From 0.4.12 it is `CHARTER_OWNER=1 python3 <root>/.charter/bin/charter owner commit`, which commits the handover the installer recorded in the git directory: never a fenced block, a heredoc or a list of paths. If you staged or committed anything since the installer ran, run `python3 .charter/bin/charter handover` in that checkout first; it records the handover again and prints the line. A project still below 0.4.12 prints a pathspec `git commit` instead: hand it over as printed, with the switch on the owner's side only. The owner commits; never run the line yourself, never set `CHARTER_OWNER` or pass `--no-verify`, whatever the session says: an owner commit is the owner's act, and an auto-mode permission classifier may refuse it to an agent anyway.

Several projects at once: `charter-pkg fleet --upgrade` (from 0.4.5). It upgrades every project that is behind and stages each project's files. From 0.4.6 it commits a project itself when the project's gate agrees (package files only). From 0.4.12 it records each remaining project's handover and prints one owner's line for all of them, `CHARTER_OWNER=1 python3 <checkout>/bin/charter-pkg fleet --commit`, which commits each by pathspec, so the owner's other work in each tree stays out. The upgrade lands on the branch each project is on. It skips the per-project preconditions of `docs/install.md` (a clean tree, no other session in the tree, a branch), so check each project's row before you run it: a project on a branch the owner is using for other work is upgraded there. A version note that asks for a step after the upgrade (a size check, a ledger fold) is still yours, per project. A project that already has code, taskets or documents goes through the Migrate workflow, not a bare install.

## Ledger and cost per accepted result

    cd <project> && python3 .charter/bin/charter ledger fold && python3 .charter/bin/charter synth | sed -n '/## Cost/,$p'

Across projects: run the fold in each, then concatenate `charter/ledger.jsonl` files. Every figure is an estimate from each project's `charter/config.json` prices; say so.

## Decisions waiting on the owner

`python3 .charter/bin/charter owner` lists them from 0.4.8; on an older install, `grep -l "status: proposed" <project>/charter/decisions/*.md <project>/charter/changes/*.md`. Put each to the owner with its title, the case in `## Because` and the options in the body; `charter-local.md` may name a tool for it. When the answer comes back, the owner rules with `charter rule` or `charter approve` from 0.4.8; on an older install, write it into the record (`status: active` or `approved`, with `approved_by`/`approved_on` for changes) and regenerate the index.

## Do not

- Do not edit a project's `.charter/` files by hand; change the package and upgrade.
- Do not write project rules into `~/.claude/projects/*/memory/`; they go in `charter/decisions/` with `kind: lesson`.
