# The package

Repository `charter` (named `methodo` until 2026-09-24; decision `package-name` in the report). Version `package/VERSION`, 0.4.3. Python 3 standard library only; no dependency is installed in a project.

## Layout of this repository

| Path | What |
|---|---|
| `package/` | The committed layer, copied into a project by the installer |
| `package/.charter/` | Tooling: `lib.py`, `checks.py`, `rails.py`, `bin/charter`, `hooks/*.py`, `githooks/pre-commit` |
| `package/.claude/` | `settings.json` (hook wiring, merged into the project's), `rules/charter.md`, `skills/charter-*/SKILL.md`, `agents/charter-reviewer.md` |
| `package/.github/workflows/charter.yml` | CI gates |
| `package/charter/` | `README.md`, `config.json` (seeded once), `templates/` (scope, decision, change, unit) |
| `package/AGENTS.md` | The section appended to a project's `AGENTS.md` for Codex and pi |
| `package/.gitignore.fragment` | The line appended to a project's `.gitignore` (`.charter/state/`) |
| `bin/charter-pkg` | Installer: `install`, `upgrade`, `uninstall`, `status`, and `survey`, which measures a project before a migration. Flags under [Commands](#commands); the procedure is `docs/install.md` |
| `bin/charter_survey.py`, `bin/charter_plan.py` | The survey: the facts, read-only on the project, and the report and plan rendered from them (`docs/design/migration-workflow.md`) |
| `bin/make-testbed`, `bin/trial-run` | Trial tooling |
| `personal/` | The personal layer, not installed by the installer (`personal/README.md`) |
| `tests/` | The command is in `AGENTS.md` at the repository root. `test_review_regressions.py` holds one class per finding of the 2026-09-11 review, `test_harmonization_regressions.py` one class per defect the 2026-09-12 harmonization trial found, `test_migration.py` the survey and the defects the 2026-09-13 leCRM rehearsal found; the others are named after the feature or review they test |
| `docs/` | Reference: `install.md`, `method.md`, `gates.md`, `package.md`, `migration.md`, `method-visual.html` (the method in diagrams), `design/`. History: `trials/`, `review/`, `briefs/`, `report-2026-09-11.md`, `session-log.md` |

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

Owned files (24, listed in `bin/charter-pkg` `OWNED`) are recorded with their SHA-256 in `.charter/manifest.json`; CI refuses a file under `.charter/` that differs from it. Seeded files (`charter/config.json`) are created once and never touched again. `charter/legacy-taskets.txt` is written once, listing the taskets found without an acceptance section. Project files (`charter/scope.md`, decisions, changes, ledger, taskets) are never written by the installer.

## Commands

Installer, run from a checkout of this repository, wherever it sits (the step-by-step procedure, with expected output, is `docs/install.md`):

```
python3 <checkout>/bin/charter-pkg install   <project> --track client|prototype [--dry-run] [--force] [--show-diff] [--replace-hooks]
python3 <checkout>/bin/charter-pkg upgrade   <project> [--dry-run] [--force] [--replace-hooks]
python3 <checkout>/bin/charter-pkg uninstall <project> [--dry-run] [--force] [--purge-state]
python3 <checkout>/bin/charter-pkg status    <project>
python3 <checkout>/bin/charter-pkg survey    <project> --track client|prototype [--out DIR | --plan | --json] [--test-cmd CMD]
                                                     [--ref BRANCH] [--keep-clone] [--no-rehearse] [--offline]
```

`--track` is required by `survey`, and by the first `install`, the one that seeds `charter/config.json`; without it the first install refuses before writing anything. On a project whose config exists it is not applied, and a value that differs from the config prints a `NOTE`. `--show-diff` prints the diff of each owned file an `install` would change (`upgrade` always prints it). `--force` replaces owned files the project modified. The parser gives every subcommand but `survey` the same flags (`main` in `bin/charter-pkg`); those not shown above have no effect there.

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
config
version
```

## Versioning and upgrade

- `package/VERSION` is the package version; `charter/VERSION` in a project records what is installed; `.charter/manifest.json` records the hashes.
- `install` reconciles on every run: missing owned files, the hook entries, the `AGENTS.md` section, the `.gitignore` line and `core.hooksPath`. On a project where all of that already holds it changes nothing. Because `.charter/manifest.json` is tracked, a fresh clone looks installed; running `install` there, or `python3 .charter/bin/charter setup` without this repository, sets the hook path the clone lacks.
- `core.hooksPath` replaces the clone's hook directory, so `install` and `setup` leave it alone when the project already runs git hooks: an executable non-sample file in the hook directory, or a tracked `lefthook.yml`, `.pre-commit-config.yaml`, `.husky/pre-commit` or husky entry in `package.json`. They print what they kept and how to run `charter check --staged` from that framework (`package/.charter/githooks/README.md`); `--replace-hooks` overrides. A framework file that already runs the gate counts as wired, for them and for the SessionStart banner.
- `install` names every path it wrote that the project's `.gitignore` matches, because a commit will not carry it.
- `upgrade` prints a unified diff for every owned file that would change, keeps any owned file the project modified locally (unless `--force`), rewrites the manifest and the version, and re-merges the hook entries (entries whose command contains `/.charter/hooks/` are replaced; other hooks are kept).
- `uninstall` removes owned files whose hash matches the manifest, the hook entries, the `AGENTS.md` section, the `.gitignore` line and `core.hooksPath`; keeps project files, and the state in the git directory and in `.charter/state/` unless `--purge-state`.
- A new version reaches a project by `upgrade` from a checkout of this repository at the new version, on a branch, committed by the owner (the commit touches `.charter/`, which CI checks against `owner`). Nothing pulls automatically. The procedure is `docs/install.md` § Upgrade; the notes below say what each version asks of a project.

Upgrade notes, by version:

- From 0.1.0: the upgrade also writes `charter/legacy-taskets.txt`; then run `python3 .charter/bin/charter setup` to move the gate log and session records out of `.charter/state/`. A 0.1.0 `charter/config.json` keeps working: its flat price table becomes the `default` row, and the package's per-model rows apply to the models it does not name.
- From 0.2.0: ledger records folded earlier carry no subagent usage, so the synthesis prints the totals over them as lower bounds. No step is needed.
- 0.4.0 changes the size gate (the size rule's named exceptions, `limits.governance_bytes`, `governance_files`). `upgrade` never rewrites a project's `charter/config.json`, so an upgraded project takes the new keys from the package defaults: a governance file over 32 KiB becomes frozen for growth on the first commit that grows it. Run `python3 .charter/bin/charter check --all --strict --size` after the upgrade, and name an exception or split the file before the next edit.
- 0.4.1 runs each probe of a closing unit a second time, before the unit's work, wherever probes run (`docs/gates.md` § Done needs evidence). A probe that already passes there is a warning; `probes.base_must_fail` makes it a refusal. Nothing that passed under 0.4.0 is refused after the upgrade. It also adds `review.required` (off): when set, done needs an anchored `review:` evidence line.
- 0.4.2 changes documentation only: `charter/README.md` lists every owner-only path and says each clone runs `charter setup`. No gate changes and no step is needed.
- 0.4.3 refuses a `charter/config.json` the gates cannot read as written: an unknown key, a value of the wrong type, a track other than `client` or `prototype`, or a file that is not JSON (`docs/gates.md` § Config). A config that 0.4.2 accepted with a typo in it is refused at the first commit after the upgrade. **Before committing the upgrade, run `python3 .charter/bin/charter config`**: it must print no `problem:` line, and the owner corrects any it prints in the same commit. The in-session hooks now also run on NotebookEdit (path gates only), and the banner and every `charter check` line name the opt-ins that are on. The installer requires `--track` on a first install and on `survey`. The SessionStart hook now shows the person a summary (version, track, opt-ins, config problems, git hook state, active unit) as a `systemMessage`; before, its whole output went to Claude's context and the person saw nothing (https://code.claude.com/docs/en/hooks, SessionStart).

## What must stay true

- Nothing in `package/` references a path outside the project. `${CLAUDE_PROJECT_DIR}` in `settings.json` is the only placeholder, and it resolves to the project.
- Everything the gates read is tracked: `.charter/`, `charter/` (except `progress.md` if you choose not to commit it), `.taskets/`, `.claude/`. State is written only in the git directory, never in the tree.
- Hook scripts run with `python3 -B` and set `sys.dont_write_bytecode`, so they leave no `__pycache__` in the tree.
- Tasket keys the engines read (`status`, `order`, `group`, `group_order`, `priority`, ...) are never renamed or reinterpreted. The package adds `scope`, `perimeter`, `decisions`, `kind`, all optional. Templates keep frontmatter comments on their own lines, which every parser skips.
- Skill names `charter-unit`, `charter-decision`, `charter-progress` and agent `charter-reviewer` do not collide with `~/.claude/Skills/` or `~/.claude/commands/` (checked 2026-09-11 against the listing in `docs/session-log.md`).
