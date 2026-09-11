# The package

Repository `methodo` (working name; see decision `package-name` in the report). Version `package/VERSION`, 0.1.0. Python 3 standard library only; no dependency is installed in a project.

## Layout of this repository

| Path | What |
|---|---|
| `package/` | The committed layer, copied into a project by the installer |
| `package/.charter/` | Tooling: `lib.py`, `checks.py`, `bin/charter`, `hooks/*.py`, `githooks/pre-commit` |
| `package/.claude/` | `settings.json` (hook wiring, merged into the project's), `rules/charter.md`, `skills/charter-*/SKILL.md`, `agents/charter-reviewer.md` |
| `package/.github/workflows/charter.yml` | CI gates |
| `package/charter/` | `README.md`, `config.json` (seeded once), `templates/` (scope, decision, change, unit) |
| `package/AGENTS.md` | The section appended to a project's `AGENTS.md` for Codex and pi |
| `package/.gitignore.fragment` | The line appended to a project's `.gitignore` (`.charter/state/`) |
| `bin/charter-pkg` | Installer: `install`, `upgrade`, `uninstall`, `status`; `--dry-run`, `--force`, `--track` |
| `bin/make-testbed`, `bin/trial-run` | Trial tooling |
| `personal/` | The personal layer, not installed by the installer (`personal/README.md`) |
| `tests/` | `python3 -m unittest -q test_gates test_installer` from `tests/` |
| `docs/` | `method.md`, `gates.md`, `package.md`, `migration.md`, `trials/`, `report-2026-09-11.md`, `session-log.md` |

## What lands in a project

```
<project>/
  .charter/            tooling (owned by the package) + state/ (gitignored, per machine)
  charter/             scope.md, decisions/, changes/, config.json, VERSION, ledger.jsonl, progress.md, templates/
  .claude/settings.json      hook entries added (existing keys kept)
  .claude/rules/charter.md   the rules every Claude Code session loads
  .claude/skills/charter-unit|charter-decision|charter-progress
  .claude/agents/charter-reviewer.md
  .github/workflows/charter.yml
  .taskets/            created if absent
  AGENTS.md            charter section appended between <!-- charter-section:begin/end -->
  .gitignore           `.charter/state/` appended
```

Owned files (22, listed in `bin/charter-pkg` `OWNED`) are recorded with their SHA-256 in `.charter/manifest.json`. Seeded files (`charter/config.json`) are created once and never touched again. Project files (`charter/scope.md`, decisions, changes, ledger, taskets) are never written by the installer.

## Commands

Installer, run from this repository:

```
python3 ~/Projects/methodo/bin/charter-pkg install   <project> --track client|prototype [--dry-run] [--force]
python3 ~/Projects/methodo/bin/charter-pkg upgrade   <project> [--dry-run] [--force]
python3 ~/Projects/methodo/bin/charter-pkg uninstall <project> [--dry-run] [--force] [--purge-state]
python3 ~/Projects/methodo/bin/charter-pkg status    <project>
```

In a project (`python3 .charter/bin/charter ...`):

```
check --staged | --all [--base REF] [--strict] [--ci] [--scope --size --done --decisions --memory --perimeter --changes]
anchors <file>... [--min-len N]
synth [--write] [--out PATH]
ledger fold | add --result <json> [--unit ID] | show
unit start <id> | stop | show
decisions index
log [--days N] [--verbose]
version
```

## Versioning and upgrade

- `package/VERSION` is the package version; `charter/VERSION` in a project records what is installed; `.charter/manifest.json` records the hashes.
- `install` on a project at the same version with all files present does nothing. With a file missing it repairs it.
- `upgrade` prints a unified diff for every owned file that would change, keeps any owned file the project modified locally (unless `--force`), rewrites the manifest and the version, and re-merges the hook entries (entries whose command contains `/.charter/hooks/` are replaced; other hooks are kept).
- `uninstall` removes owned files whose hash matches the manifest, the hook entries, the `AGENTS.md` section, the `.gitignore` line and `core.hooksPath`; keeps project files and `.charter/state/` unless `--purge-state`.
- A new version reaches a project by `upgrade` from a checkout of this repository at the new version, on a branch, committed like any change. Nothing pulls automatically. The personal-layer SessionStart hook says when a project is behind.

## What must stay true

- Nothing in `package/` references a path outside the project. `${CLAUDE_PROJECT_DIR}` in `settings.json` is the only placeholder, and it resolves to the project.
- Everything the gates read is tracked: `.charter/`, `charter/` (except `progress.md` if you choose not to commit it), `.taskets/`, `.claude/`. State is written under `.charter/state/` only.
- Hook scripts run with `python3 -B` and set `sys.dont_write_bytecode`, so they leave no `__pycache__` in the tree.
- Tasket keys the engines read (`status`, `order`, `group`, `group_order`, `priority`, ...) are never renamed or reinterpreted. The package adds `scope`, `perimeter`, `decisions`, `kind`, all optional.
- Skill names `charter-unit`, `charter-decision`, `charter-progress` and agent `charter-reviewer` do not collide with `~/.claude/Skills/` or `~/.claude/commands/` (checked 2026-09-11 against the listing in `docs/session-log.md`).
