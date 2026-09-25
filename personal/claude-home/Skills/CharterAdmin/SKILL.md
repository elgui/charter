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

**Example 3: Upgrade a project already on charter**
```
User: "Upgrade charter on leCRM"
→ Follows "Install or upgrade" below: the dry run, then the upgrade on a branch, staged
→ Returns the diff and the commit command for the owner
```

## Which projects, which version

    for p in ~/Projects/*/; do [ -f "$p/charter/VERSION" ] && echo "$p $(cat $p/charter/VERSION)"; done
    python3 ~/Projects/charter/bin/charter-pkg status <project>

Where one project stands and what comes next: `python3 .charter/bin/charter next` from 0.4.4. On an older install, run this checkout's copy against it; it only reads: `python3 ~/Projects/charter/package/.charter/bin/charter --root <project> next`.

## Install or upgrade

Follow `~/Projects/charter/docs/install.md`: the preconditions, the track (`client` only under a signed devis, otherwise `prototype`), the dry run, the install or upgrade on a branch, then stop with the files staged. The commit touches owner-only paths, so the owner makes it; never set `CHARTER_OWNER` or pass `--no-verify` yourself. A project that already has code, taskets or documents goes through the Migrate workflow, not a bare install.

## Ledger and cost per accepted result

    cd <project> && python3 .charter/bin/charter ledger fold && python3 .charter/bin/charter synth | sed -n '/## Cost/,$p'

Across projects: run the fold in each, then concatenate `charter/ledger.jsonl` files. Every figure is an estimate from each project's `charter/config.json` prices; say so.

## Decisions waiting on Gui

`grep -l "status: proposed" <project>/charter/decisions/*.md <project>/charter/changes/*.md`. Hand the list to Crossroads or Slate; each proposed record already has the shape a decision page needs (title, the case in `## Because`, the options in the body). When the answer comes back, write it into the record (`status: active` or `approved`, with `approved_by`/`approved_on` for changes) and regenerate the index.

## Do not

- Do not edit a project's `.charter/` files by hand; change the package and upgrade.
- Do not write project rules into `~/.claude/projects/*/memory/`; they go in `charter/decisions/` with `kind: lesson`.
