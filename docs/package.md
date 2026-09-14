# The package

Repository `methodo` (working name; see decision `package-name` in the report). Version `package/VERSION`, 0.3.0. Python 3 standard library only; no dependency is installed in a project.

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
| `bin/charter-pkg` | Installer: `install`, `upgrade`, `uninstall`, `status`; `--dry-run`, `--force`, `--track`, `--replace-hooks`. And `survey`, which measures a project before a migration |
| `bin/charter_survey.py`, `bin/charter_plan.py` | The survey: the facts, read-only on the project, and the report and plan rendered from them (`docs/design/migration-workflow.md`) |
| `bin/make-testbed`, `bin/trial-run` | Trial tooling |
| `personal/` | The personal layer, not installed by the installer (`personal/README.md`) |
| `tests/` | `python3 -B -m unittest -q test_gates test_installer test_review_regressions test_harmonization_regressions test_batch1_regressions test_migration` from `tests/`; `test_review_regressions.py` holds one class per finding of the 2026-09-11 review, `test_harmonization_regressions.py` one class per defect the 2026-09-12 harmonization trial found, `test_migration.py` the survey and the defects the 2026-09-13 leCRM rehearsal found |
| `docs/` | `method.md`, `gates.md`, `package.md`, `migration.md`, `method-visual.html` (the method in diagrams), `design/`, `trials/`, `review/`, `report-2026-09-11.md`, `session-log.md` |

## What lands in a project

```
<project>/
  .charter/            tooling (owned by the package)
  .git/charter/        gate log and session records (per machine, shared by worktrees, never committed)
  charter/             scope.md, decisions/, changes/, config.json, legacy-taskets.txt, VERSION, ledger.jsonl, progress.md, templates/
  .claude/settings.json      hook entries added (existing keys kept)
  .claude/rules/charter.md   the rules every Claude Code session loads
  .claude/skills/charter-unit|charter-decision|charter-progress
  .claude/agents/charter-reviewer.md
  .github/workflows/charter.yml
  .taskets/            created if absent
  AGENTS.md            charter section appended between <!-- charter-section:begin/end -->
  .gitignore           `.charter/state/` appended (where 0.1.0 kept its state; `charter setup` moves it)
```

Owned files (22, listed in `bin/charter-pkg` `OWNED`) are recorded with their SHA-256 in `.charter/manifest.json`; CI refuses a file under `.charter/` that differs from it. Seeded files (`charter/config.json`) are created once and never touched again. `charter/legacy-taskets.txt` is written once, listing the taskets found without an acceptance section. Project files (`charter/scope.md`, decisions, changes, ledger, taskets) are never written by the installer.

## Commands

Installer, run from this repository:

```
python3 ~/Projects/methodo/bin/charter-pkg install   <project> --track client|prototype [--dry-run] [--force] [--replace-hooks]
python3 ~/Projects/methodo/bin/charter-pkg upgrade   <project> [--dry-run] [--force]
python3 ~/Projects/methodo/bin/charter-pkg uninstall <project> [--dry-run] [--force] [--purge-state]
python3 ~/Projects/methodo/bin/charter-pkg status    <project>
python3 ~/Projects/methodo/bin/charter-pkg survey    <project> [--track T] [--out DIR | --plan | --json] [--test-cmd CMD]
                                                     [--ref BRANCH] [--keep-clone] [--no-rehearse] [--offline]
```

In a project (`python3 .charter/bin/charter ...`):

```
check --staged | --all [--base REF] [--strict] [--ci] [--probe | --no-probe]
      [--scope --size --done --decisions --memory --perimeter --changes --protected]
probe <id> [--timeout S]
anchors <file>... [--min-len N] [--pr]
synth [--write] [--out PATH]
ledger fold | add --result <json> [--unit ID] | add --human-minutes N [--unit ID] [--note TEXT] | show
unit start <id> | stop | show
decisions index
log [--days N] [--verbose]
setup [--replace-hooks]
version
```

## Versioning and upgrade

- `package/VERSION` is the package version; `charter/VERSION` in a project records what is installed; `.charter/manifest.json` records the hashes.
- `install` reconciles on every run: missing owned files, the hook entries, the `AGENTS.md` section, the `.gitignore` line and `core.hooksPath`. On a project where all of that already holds it changes nothing. Because `.charter/manifest.json` is tracked, a fresh clone looks installed; running `install` there, or `python3 .charter/bin/charter setup` without this repository, sets the hook path the clone lacks.
- `core.hooksPath` replaces the clone's hook directory, so `install` and `setup` leave it alone when the project already runs git hooks: an executable non-sample file in the hook directory, or a tracked `lefthook.yml`, `.pre-commit-config.yaml`, `.husky/pre-commit` or husky entry in `package.json`. They print what they kept and how to run `charter check --staged` from that framework (`package/.charter/githooks/README.md`); `--replace-hooks` overrides. A framework file that already runs the gate counts as wired, for them and for the SessionStart banner.
- `install` names every path it wrote that the project's `.gitignore` matches, because a commit will not carry it.
- `upgrade` prints a unified diff for every owned file that would change, keeps any owned file the project modified locally (unless `--force`), rewrites the manifest and the version, and re-merges the hook entries (entries whose command contains `/.charter/hooks/` are replaced; other hooks are kept).
- `uninstall` removes owned files whose hash matches the manifest, the hook entries, the `AGENTS.md` section, the `.gitignore` line and `core.hooksPath`; keeps project files, and the state in the git directory and in `.charter/state/` unless `--purge-state`.
- A new version reaches a project by `upgrade` from a checkout of this repository at the new version, on a branch, committed by the owner like any change (the commit touches `.charter/`, which CI checks against `owner`). Nothing pulls automatically. The personal-layer SessionStart hook says when a project is behind. After an upgrade from 0.1.0, `python3 .charter/bin/charter setup` moves the old state out of `.charter/state/`.

## What must stay true

- Nothing in `package/` references a path outside the project. `${CLAUDE_PROJECT_DIR}` in `settings.json` is the only placeholder, and it resolves to the project.
- Everything the gates read is tracked: `.charter/`, `charter/` (except `progress.md` if you choose not to commit it), `.taskets/`, `.claude/`. State is written only in the git directory, never in the tree.
- Hook scripts run with `python3 -B` and set `sys.dont_write_bytecode`, so they leave no `__pycache__` in the tree.
- Tasket keys the engines read (`status`, `order`, `group`, `group_order`, `priority`, ...) are never renamed or reinterpreted. The package adds `scope`, `perimeter`, `decisions`, `kind`, all optional. Templates keep frontmatter comments on their own lines, which every parser skips.
- Skill names `charter-unit`, `charter-decision`, `charter-progress` and agent `charter-reviewer` do not collide with `~/.claude/Skills/` or `~/.claude/commands/` (checked 2026-09-11 against the listing in `docs/session-log.md`).
