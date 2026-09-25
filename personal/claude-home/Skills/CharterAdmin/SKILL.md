---
name: CharterAdmin
description: Administer the charter method across Gui's projects from the personal layer, and migrate existing projects onto it. USE WHEN the user says "charter status", "upgrade charter", "install charter on", "fold the ledgers", "cost per accepted unit across projects", "which projects run charter", OR wants to migrate, move or onboard an existing project onto charter, survey a project before a charter install, or plan a charter migration, OR wants open charter decisions turned into a Crossroads or Slate page.
---

# CharterAdmin (personal layer)

Package repository: `~/Projects/charter` (override with `CHARTER_PKG_DIR`). The committed layer in each project never depends on this skill.

## Workflow Routing

**When executing a workflow, do BOTH of these:**

1. **Call the notification script** (for observability tracking):
   ```bash
   ~/.claude/Tools/SkillWorkflowNotification WORKFLOWNAME CharterAdmin
   ```

2. **Output the text notification** (for user visibility):
   ```
   Running the **WorkflowName** workflow from the **CharterAdmin** skill...
   ```

| Workflow | Trigger | File |
|----------|---------|------|
| **Migrate** | "migrate <project> to charter", "put charter on <project>", "survey <project> for charter", any install on a project that already has code, taskets or documents | `workflows/Migrate.md` |

The sections after the examples are short procedures for projects already on charter.

## Examples

**Example 1: Migrate an existing project**
```
User: "Put charter on leCRM"
→ Invokes Migrate workflow
→ Runs `charter-pkg survey`, which reads the project and rehearses the install in a throwaway clone
→ Settles what the facts settle, puts the rest on a Slate, rehearses the whole plan in a clone
→ Executes on a branch, one checked commit per step, only after the owner's go-ahead
→ Returns the survey, the plan with each check's output, and the Slate link
```

**Example 2: Survey only**
```
User: "What would it take to put charter on orqueveaux?"
→ Invokes Migrate workflow, phases 1 and 2
→ Returns the survey report and the generated plan; writes nothing to the project
```

**Example 3: Upgrade every project ("upgrade charter", "upgrade the projects")**
```
User: "Upgrade charter everywhere"
→ `python3 ~/Projects/charter/bin/charter-pkg fleet` to show the table, then `fleet --upgrade`
→ Returns the fleet's handover block first, verbatim: one command that commits every project
→ Then one line per project: the version change, and any KEEP, IGNORED or NOTE line
```

**Example 4: Upgrade one project already on charter**
```
User: "Upgrade charter on leCRM"
→ Follows "Install or upgrade" below: the dry run, then the upgrade on a branch, staged
→ Returns the handover block the installer printed (the owner's one commit command), then the diff
```

## Which projects, which version

    python3 ~/Projects/charter/bin/charter-pkg fleet            # read-only: version, branch, what waits on the owner
    python3 ~/Projects/charter/bin/charter-pkg status <project>

Where one project stands and what comes next: `python3 .charter/bin/charter next` from 0.4.4. On an older install, run this checkout's copy against it; it only reads: `python3 ~/Projects/charter/package/.charter/bin/charter --root <project> next`.

## Install or upgrade

Follow `~/Projects/charter/docs/install.md`: the preconditions, the track (`client` only under a signed devis, otherwise `prototype`), the dry run, the install or upgrade on a branch, then stop: the installer stages its files and prints the handover block. Open the report with that block, copied verbatim (`docs/install.md` step 8). The commit touches owner-only paths, so the owner makes it; never set `CHARTER_OWNER` or pass `--no-verify` yourself. The auto-mode classifier refuses a `CHARTER_OWNER=1` commit from an agent as a safety bypass unless Gui has explicitly asked, in that conversation, for the agent to make the owner's commit itself: on 2026-09-25 "set them up properly (performing git operations)" was refused, "do them yourself this time" was allowed. Without that word, hand over the command; don't try.

Several projects at once: `charter-pkg fleet --upgrade` (from 0.4.5). It upgrades every project that is behind, stages each project's files, and prints one command that commits all of them, each by pathspec, so the owner's other work in each tree stays out. The upgrade lands on the branch each project is on. It skips the per-project preconditions of `docs/install.md` (a clean tree, no other session in the tree, a branch), so check each project's row before you run it: a project on a branch the owner is using for other work is upgraded there. A version note that asks for a step after the upgrade (a size check, a ledger fold) is still yours, per project. A project that already has code, taskets or documents goes through the Migrate workflow, not a bare install.

## Ledger and cost per accepted result

    cd <project> && python3 .charter/bin/charter ledger fold && python3 .charter/bin/charter synth | sed -n '/## Cost/,$p'

Across projects: run the fold in each, then concatenate `charter/ledger.jsonl` files. Every figure is an estimate from each project's `charter/config.json` prices; say so.

## Decisions waiting on Gui

`grep -l "status: proposed" <project>/charter/decisions/*.md <project>/charter/changes/*.md`. Hand the list to Crossroads or Slate; each proposed record already has the shape a decision page needs (title, the case in `## Because`, the options in the body). When the answer comes back, write it into the record (`status: active` or `approved`, with `approved_by`/`approved_on` for changes) and regenerate the index.

## Do not

- Do not edit a project's `.charter/` files by hand; change the package and upgrade.
- Do not write project rules into `~/.claude/projects/*/memory/`; they go in `charter/decisions/` with `kind: lesson`.
