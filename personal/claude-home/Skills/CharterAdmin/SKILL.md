---
name: CharterAdmin
description: Administer the charter method across Gui's projects from the personal layer. USE WHEN the user says "charter status", "upgrade charter", "install charter on", "fold the ledgers", "cost per accepted unit across projects", "which projects run charter", OR wants open charter decisions turned into a Crossroads or Slate page.
---

# CharterAdmin (personal layer)

Package repository: `~/Projects/methodo` (override with `CHARTER_PKG_DIR`). The committed layer in each project never depends on this skill.

## Which projects, which version

    for p in ~/Projects/*/; do [ -f "$p/charter/VERSION" ] && echo "$p $(cat $p/charter/VERSION)"; done
    python3 ~/Projects/methodo/bin/charter-pkg status <project>

## Install or upgrade

    python3 ~/Projects/methodo/bin/charter-pkg install <project> --track client --dry-run   # read it
    python3 ~/Projects/methodo/bin/charter-pkg install <project> --track client
    python3 ~/Projects/methodo/bin/charter-pkg upgrade <project> --dry-run                  # shows the diff
    python3 ~/Projects/methodo/bin/charter-pkg upgrade <project>

Commit the result in the project on a branch. Never upgrade a project with a dirty tree.

## Ledger and cost per accepted result

    cd <project> && python3 .charter/bin/charter ledger fold && python3 .charter/bin/charter synth | sed -n '/## Cost/,$p'

Across projects: run the fold in each, then concatenate `charter/ledger.jsonl` files. Every figure is an estimate from each project's `charter/config.json` prices; say so.

## Decisions waiting on Gui

`grep -l "status: proposed" <project>/charter/decisions/*.md <project>/charter/changes/*.md`. Hand the list to Crossroads or Slate; each proposed record already has the shape a decision page needs (title, the case in `## Because`, the options in the body). When the answer comes back, write it into the record (`status: active` or `approved`, with `approved_by`/`approved_on` for changes) and regenerate the index.

## Do not

- Do not edit a project's `.charter/` files by hand; change the package and upgrade.
- Do not write project rules into `~/.claude/projects/*/memory/`; they go in `charter/decisions/` with `kind: lesson`.
