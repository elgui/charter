# The package

Repository `charter` (named `methodo` until 2026-09-24; decision `package-name` in the report). Version `package/VERSION`, 0.4.7. Python 3 standard library only; no dependency is installed in a project.

## Layout of this repository

| Path | What |
|---|---|
| `package/` | The committed layer, copied into a project by the installer |
| `package/.charter/` | Tooling: `lib.py`, `checks.py`, `rails.py`, `bin/charter`, `hooks/*.py`, `githooks/pre-commit` |
| `package/.claude/` | `settings.json` (hook wiring, merged into the project's), `rules/charter.md`, `skills/charter-*/SKILL.md`, `agents/charter-reviewer.md` |
| `package/.github/workflows/charter.yml` | CI gates |
| `package/charter/` | `README.md`, `config.json` (seeded once), `templates/` (scope, rails, decision, change, unit) |
| `package/AGENTS.md` | The section appended to a project's `AGENTS.md` for Codex and pi |
| `package/.gitignore.fragment` | The line appended to a project's `.gitignore` (`.charter/state/`) |
| `bin/charter-pkg` | Installer: `install`, `upgrade`, `uninstall`, `status`, and `survey`, which measures a project before a migration. Flags under [Commands](#commands); the procedure is `docs/install.md` |
| `bin/charter_survey.py`, `bin/charter_plan.py` | The survey: the facts, read-only on the project, and the report and plan rendered from them (`docs/design/migration-workflow.md`) |
| `bin/make-testbed`, `bin/trial-run` | Trial tooling |
| `personal/` | The personal layer, not installed by the installer (`personal/README.md`) |
| `tests/` | The command is in `AGENTS.md` at the repository root. `test_review_regressions.py` holds one class per finding of the 2026-09-11 review, `test_harmonization_regressions.py` one class per defect the 2026-09-12 harmonization trial found, `test_migration.py` the survey and the defects the 2026-09-13 leCRM rehearsal found; the others are named after the feature or review they test |
| `docs/` | Reference: `install.md`, `daily-use.md`, `method.md`, `gates.md`, `package.md`, `migration.md`, `method-visual.html` (the method in diagrams), `design/`. History: `trials/`, `review/`, `briefs/`, `report-2026-09-11.md`, `session-log.md` |

## What lands in a project

```
<project>/
  .charter/            tooling (owned by the package)
  .git/charter/        gate log and session records (per machine, shared by worktrees, never committed)
  charter/             scope.md, rails.md (optional), decisions/, changes/, config.json, legacy-taskets.txt, VERSION, ledger.jsonl, progress.md, templates/
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
python3 <checkout>/bin/charter-pkg fleet     [--root DIR] [--upgrade]
python3 <checkout>/bin/charter-pkg survey    <project> --track client|prototype [--out DIR | --plan | --json] [--test-cmd CMD]
                                                     [--ref BRANCH] [--keep-clone] [--no-rehearse] [--offline]
```

`--track` is required by `survey`, and by the first `install`, the one that seeds `charter/config.json`; without it the first install refuses before writing anything. On a project whose config exists it is not applied, and a value that differs from the config prints a `NOTE`. `--show-diff` prints the diff of each owned file an `install` would change (`upgrade` always prints it). `--force` replaces owned files the project modified. The parser gives every subcommand but `survey` the same flags (`main` in `bin/charter-pkg`); those not shown above have no effect there.

In a project (`python3 .charter/bin/charter ...`; the source is `package/.charter/bin/charter`):

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
next [--limit N]
handover [-m MESSAGE]
version
```

## Versioning and upgrade

- `package/VERSION` is the package version; `charter/VERSION` in a project records what is installed; `.charter/manifest.json` records the hashes.
- `install` reconciles on every run: missing owned files, the hook entries, the `AGENTS.md` section, the `.gitignore` line and `core.hooksPath`. On a project where all of that already holds it changes nothing. Because `.charter/manifest.json` is tracked, a fresh clone looks installed; running `install` there, or `python3 .charter/bin/charter setup` without this repository, sets the hook path the clone lacks.
- `core.hooksPath` replaces the clone's hook directory, so `install` and `setup` leave it alone when the project already runs git hooks: an executable non-sample file in the hook directory, or a tracked `lefthook.yml`, `.pre-commit-config.yaml`, `.husky/pre-commit` or husky entry in `package.json`. They print what they kept and how to run `charter check --staged` from that framework (`package/.charter/githooks/README.md`); `--replace-hooks` overrides. A framework file that already runs the gate counts as wired, for them and for the SessionStart banner.
- `install` names every path it wrote that the project's `.gitignore` matches, because a commit will not carry it (`bin/charter-pkg:294`).
- `upgrade` prints a unified diff for every owned file that would change, keeps any owned file the project modified locally (unless `--force`), rewrites the manifest and the version, and re-merges the hook entries (entries whose command contains `/.charter/hooks/` are replaced; other hooks are kept; `do_install` and `merge_settings` in `bin/charter-pkg`).
- `uninstall` removes owned files whose hash matches the manifest, the hook entries, the `AGENTS.md` section, the `.gitignore` line and `core.hooksPath`; keeps project files, and the state in the git directory and in `.charter/state/` unless `--purge-state`.
- A new version reaches a project by `upgrade` from a checkout of this repository at the new version, on a branch, committed by the owner (the commit touches `.charter/`, which CI checks against `owner`). Nothing pulls automatically. The procedure is `docs/install.md` § Upgrade; the notes below say what each version asks of a project.

Upgrade notes, by version:

- From 0.1.0: the upgrade also writes `charter/legacy-taskets.txt`; then run `python3 .charter/bin/charter setup` to move the gate log and session records out of `.charter/state/`. A 0.1.0 `charter/config.json` keeps working: its flat price table becomes the `default` row, and the package's per-model rows apply to the models it does not name (`_price` and `cmd_setup` in `package/.charter/bin/charter`; the legacy list came with ab0a8b1).
- From 0.2.0: ledger records folded earlier carry no subagent usage, so the synthesis prints the totals over them as lower bounds (subagent usage came with 7ece80d, 0.2.1). No step is needed.
- 0.4.0 changes the size gate (the size rule's named exceptions, `limits.governance_bytes`, `governance_files`). `upgrade` never rewrites a project's `charter/config.json`, so an upgraded project takes the new keys from the package defaults: a governance file over 32 KiB becomes frozen for growth on the first commit that grows it. Run `python3 .charter/bin/charter check --all --strict --size` after the upgrade, and name an exception or split the file before the next edit (1e02b6c).
- 0.4.1 runs each probe of a closing unit a second time, before the unit's work, wherever probes run (`docs/gates.md` § Done needs evidence). A probe that already passes there is a warning; `probes.base_must_fail` makes it a refusal. Nothing that passed under 0.4.0 is refused after the upgrade. It also adds `review.required` (off): when set, done needs an anchored `review:` evidence line (b281a17).
- 0.4.2 changes documentation only: `charter/README.md` lists every owner-only path and says each clone runs `charter setup`. No gate changes and no step is needed (cbb55fe).
- 0.4.3 refuses a `charter/config.json` the gates cannot read as written: an unknown key, a value of the wrong type, a track other than `client` or `prototype`, or a file that is not JSON (`docs/gates.md` § Config). A config that 0.4.2 accepted with a typo in it is refused at the first commit after the upgrade. **Before committing the upgrade, run `python3 .charter/bin/charter config`**: it must print no `problem:` line, and the owner corrects any it prints in the same commit. The in-session hooks now also run on NotebookEdit (path gates only), and the banner and every `charter check` line name the opt-ins that are on. The installer requires `--track` on a first install and on `survey`. The SessionStart hook now shows the person a summary (version, track, opt-ins, config problems, git hook state, active unit) as a `systemMessage`; before, its whole output went to Claude's context and the person saw nothing (https://code.claude.com/docs/en/hooks, SessionStart).
- 0.4.4 adds `charter next`, which answers "what comes next" from the project's own files: the active unit, the open rails and the units on them in the road's order, units off the road, what waits on the owner, and the gate log over 7 days. It writes nothing, not even the gate log, so any agent or tool can run it (`cmd_next` in `package/.charter/bin/charter`). The synthesis lists units the done gate never judged under **Done before charter** instead of "Done but not accepted". These are units done before the commit that added `charter/VERSION` and not reopened since, and legacy units without `## Acceptance`. In skill-delivery that moved 17 units (`$ python3 package/.charter/bin/charter --root ~/Projects/skill-delivery synth`, 2026-09-24). The perimeter gate ignores files that git ignores and does not track, such as a tool's local journal (`lib.ignored`); a tracked file is judged as before. A path in a unit's evidence that this user may not read no longer crashes the synthesis: on 2026-09-24, leCRM's crashed on a path under `/root` with 0.3.0 and 0.4.3 alike. No gate is added and no step is needed.
- 0.4.5 changes how the owner's commit is handed over. `install`, `upgrade` and `uninstall` stage what they wrote or removed, by name, and end with one command for the owner, `git -C <project> commit -m 'charter <version>' -- <paths>`, in the form typed after `!` in a Claude Code prompt and in the form for the owner's own terminal (`stage_and_hand_over` in `bin/charter-pkg`, `lib.handover`). The paths after `--` commit exactly those files, so untracked or other staged work stays out (https://git-scm.com/docs/git-commit#Documentation/git-commit.txt---only). `charter handover` prints the same block from the index. `charter-pkg fleet` lists every charter project under a directory, and with `--upgrade` upgrades the ones behind and hands over one command for all of them (`do_fleet` in `bin/charter-pkg`). The gate's refusal of an owner-only commit now says to leave it staged and run `charter handover`, where it used to suggest starting Claude Code with `CHARTER_OWNER=1` (`OWNER_COMMIT_OVERRIDE` in `package/.charter/checks.py`). Motivated by upgrade reports of 2026-09-25 that gave the owner a count of files, no command, and that suggestion (`tests/test_handover_0_4_5.py`). No gate changes and no step is needed; the upgrade to 0.4.5 is itself handed over this way.
- 0.4.6 lets an agent commit an upgrade. A package file whose content hashes to what `.charter/manifest.json` records at the same revision, and a manifest whose every listed file matches, is no longer an owner-only change at commit or in CI (`release_change` in `package/.charter/checks.py`). A hand edit of the engine does not match and is refused as before, and `.claude/settings.json` stays the owner's, so an upgrade that merges new hook entries into it still waits on the owner. The installer's block and `charter handover` say which case applies; `charter-pkg fleet --upgrade` commits the projects whose gate agrees and hands over the rest (`tests/test_release_commit_0_4_6.py`). The in-session Edit and Write gate on `.charter/**` is unchanged. The upgrade to 0.4.6 is itself the agent's to commit: the commit runs the new gate from the working tree. No step is needed.
- 0.4.7 takes the noise out of four gates, measured in tele-claude's gate log (603 events, 2026-09-27 to 2026-09-29, `.git/charter/log.jsonl`). The Stop gate warns about an anchor that does not resolve from the checkout, through `additionalContext`, instead of blocking: all 9 of its blocks there were real anchors it could not see (a bare `file.py:123`, a file or a SHA in another repository). A completion claim with no anchor at all still blocks. The size gate warns when a change crosses 80% of a limit, not on every change above it; an exception's budget is 1.25 times the file's size, so it warned on every line an exception file gained. A `git mv` is measured against the file's old name, not as a new file (`rename_sources`). An opt-in `limits.growth_slack_lines` (default 0) lets one change add that many lines to a non-governance file over its limit, with a warning. A `charter:<id>` marker ends at a letter or digit, so `charter:foo.` cites `foo` (3 of the decisions gate's 7 blocks there). The active unit is the session's own: `charter unit start` records it for the session (`CLAUDE_CODE_SESSION_ID`, or the hook's `session_id`), and the checkout's shared choice applies to other sessions only while its unit is open; it had charged 29 of 61 sessions to a unit already done (reported by the 2026-09-29 safeguard audit) (`active_unit` in `package/.charter/lib.py`). Tests: `tests/test_gate_noise_0_4_7.py`. No step is needed; a project that wants the slack sets it in `charter/config.json`, which is the owner's.

## What must stay true

- Nothing in `package/` references a path outside the project. `${CLAUDE_PROJECT_DIR}` in `settings.json` is the only placeholder, and it resolves to the project.
- Everything the gates read is tracked: `.charter/`, `charter/` (except `progress.md` if you choose not to commit it), `.taskets/`, `.claude/`. State is written only in the git directory, never in the tree.
- Hook scripts run with `python3 -B` and set `sys.dont_write_bytecode`, so they leave no `__pycache__` in the tree (`package/.claude/settings.json:4`, `package/.charter/hooks/_common.py:5`).
- Tasket keys the engines read (`status`, `order`, `group`, `group_order`, `priority`, ...) are never renamed or reinterpreted. The package adds `scope`, `perimeter`, `decisions`, `kind`, all optional. Templates keep frontmatter comments on their own lines, which every parser skips (`package/charter/templates/unit.md:1-16`).
- Skill names `charter-unit`, `charter-decision`, `charter-progress` and agent `charter-reviewer` do not collide with `~/.claude/Skills/` or `~/.claude/commands/` (checked 2026-09-11 against the listing in `docs/session-log.md`).
