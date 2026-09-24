# Migration workflow

How an existing project moves onto charter: measured by code (`bin/charter_survey.py`), rehearsed in a clone, decided by the owner, then executed one checked commit at a time. Built in package 0.3.0 and proven on a clone of leCRM on 2026-09-13. The real migration then ran on two leCRM branches, `chore/deploy-ignore-charter` and `charter/install`, made in separate worktrees and stopped before their pull requests (outside this repository: `git -C ~/Projects/leCRM log origin/main..charter/install`).

## The pieces

| Piece | Where | What it does |
|---|---|---|
| Survey | `bin/charter_survey.py`, run as `charter-pkg survey <project>` | Reads the project through git plumbing at the main line, never the index (`GIT_OPTIONAL_LOCKS=0`); rehearses the install in a throwaway clone |
| Report and plan | `bin/charter_plan.py` | Renders the facts as `survey.md`, and as `plan.md`: owner decisions, then one step per commit with its check, its rollback and the fact it rests on |
| Skill | `personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md` | Judgement and sequencing: settle what the facts settle, put the rest on a Slate, rehearse the whole plan, execute after the go-ahead |
| Tests | `tests/test_migration.py` | 24 tests; all but two, which guard kept behaviour, fail on 99e1a2a |

The skill lives in the personal layer because it calls this repository's installer, and `package/` never references anything outside the project (`docs/package.md`). It reaches `~/.claude` through the symlink manifest, option B of `personal/README.md`.

## Why the facts are measured

Until 0.3.0, `docs/migration.md` carried an orqueveaux plan written by hand on 2026-09-11 (`$ git show 99e1a2a:docs/migration.md`). A rehearsal a day later found four of its facts wrong: the legacy tasket count, the scope source, a line reference, and a file count that depended on an unmerged branch (reported in the parent session's handoff, 2026-09-13). The leCRM rehearsal found what no runbook would have said:

| Finding | Measured with | What it changed |
|---|---|---|
| Every clone runs lefthook; the install's `core.hooksPath` would stop gofmt, eslint, codegen sync and the push gate | `$ ls ~/Projects/leCRM/.git/hooks` | The installer and `charter setup` keep existing hooks unless `--replace-hooks`; the gate is wired into `lefthook.yml` instead |
| `deploy-prod.yml` rebuilds the demo on any push to `main` outside docs, markdown and taskets, so the install, a ledger fold or a legacy-list edit would redeploy it | `$ git show main:.github/workflows/deploy-prod.yml` | A plan step extends `paths-ignore` before the install merges |
| `.claude/settings.json` is ignored, so the install commit would leave the session hooks out | `$ git check-ignore -v .claude/settings.json` | The installer names every written path a commit will not carry |
| 39 of 44 open taskets keep their checklist under `## Done When`, the heading the Tasket skill writes, and charter read only `## Acceptance` | `$ charter-pkg survey ~/Projects/leCRM` | The package reads `## Done When` as the acceptance checklist; taskets listed as legacy at install keep their warning |
| `charter synth` refused to write: a tasket titled `# Log emails to the timeline` was read as its own Log section | `$ charter synth` (in the clone) | `lib.section` ignores level-1 titles and matches whole words |
| 21 of the 29 files frozen at install are BMAD skill files installed from elsewhere | `$ charter check --all --strict --size` (in the clone) | The survey reports frozen counts with tests, tooling and vendored code exempt |
| 31 of the last 50 first-parent commits are squash merges | `$ git log --first-parent -n 50 --format=%P main` | The plan records the merge-commit decision |
| `docs/sprint-plan.md` looked archivable, but ADR-010 and two SQL migrations cite it; a hand check cut off at five matches missed them | `$ git grep -l sprint-plan.md main -- . :!.taskets` | Archive candidates carry the files that cite them; cited ones stay |

## The survey

| Section | Reads | Keys in `survey.json` |
|---|---|---|
| Checkout | `$ git status --porcelain`, `$ tmux list-panes -a` | `checkout`: branch, drift, uncommitted files, sessions working in the tree |
| Taskets | `$ git cat-file --batch` over `.taskets/*.md` | `taskets`: classes by acceptance (none, `## Done When`, a heading the package does not read, prose, checklist, checklist with probes) by open, done and closed; statuses outside the engines' vocabulary; frontmatter comments; ids; the installer's legacy count |
| Size | every tracked blob, with `size_limit_for` from package/.charter/checks.py | `size`: frozen files, counts with tests, tooling or vendored code exempt, governance files; `frozen_in_open_work` |
| Hooks | `$ git config --get core.hooksPath`, the hook directory | `hooks`: installed hooks and frameworks the charter hook path would stop |
| Claude Code files | `$ git check-ignore -v --stdin` | `claude`: tracked files, settings keys (never values), installer paths a commit will not carry |
| CI | the workflows under `.github/workflows/`, read as text by `parse_triggers` in bin/charter_survey.py | `ci`: push triggers on the main line, whether each deploys, whether the install or a one-file charter commit starts it, `continue-on-error` lines |
| Remote and history | `$ git log`, `$ gh repo view` | `remote`, `history`, `credentials` (prefix and length only), `binaries`, `test_candidates` |
| Documents | `$ git log --name-only`, `$ git grep -l` | `markdown`, `decisions`: archive candidates and who cites them, decision records, `CLAUDE.md` sections, BMAD files |
| Rehearsal | a clone of the main line, by `rehearse` in bin/charter_survey.py | `rehearsal`: install, staging by name, the owner commit through the pre-commit gate, `check --all`, strict size, `synth`, an optional test command |

Both documents pass the anchoring check, run in-process by `do_survey` in bin/charter-pkg: `charter anchors --root <project>` would append to the project's gate log. Exit 0 is clean, 2 is a refused argument, 3 is a rendered line that failed the check.

## From facts to a plan

`decisions()` in bin/charter_plan.py turns facts into owner decisions, and `plan()` in the same file turns them into steps:

| Fact | Owner decision | Step | Code |
|---|---|---|---|
| No `charter/scope.md` | Track | Install with `--track` | bin/charter_plan.py |
| Other hooks, none wired | Wire, replace, or CI only | Wire the gate into the framework's pre-commit | bin/charter_plan.py |
| A deploying workflow the install starts | Extend `paths-ignore`, or accept | The `paths-ignore` change, merged first | bin/charter_plan.py |
| An installer path `.gitignore` matches | Commit it, or keep it local | Stop ignoring it, then stage it in the install | bin/charter_plan.py |
| Open taskets with a checklist under a heading the package does not read | Convert, alias, or leave | Triage by plan group | bin/charter_plan.py |
| Frozen files that exemption groups would free | Which groups | Owner config | bin/charter_plan.py |
| More than one author in 90 days | Who is told | none: the owner's act | bin/charter_plan.py |
| Squash merges on the main line | none | The merge-commit decision | bin/charter_plan.py |
| Frozen files named by open work | none | One `kind: split` unit each, opened by the owner | bin/charter_plan.py |

Every step names its check and its rollback. The `git add` list comes from `add_paths` in bin/charter_survey.py, derived from the installer's `OWNED` list; the rehearsal stages with it and reports anything left unstaged.

## The rehearsal of the whole plan on leCRM

Phase 4 of the skill ran every step of the generated plan in a kept clone of leCRM's `main` at 9b61c1bd (in the clone):

| Step | Check | Result |
|---|---|---|
| Install, staged by name | pre-commit gate | 0 blocking, 30 files, none left unstaged (in the clone) |
| Extend `paths-ignore` of `deploy-prod.yml` | the survey again | the install and every one-file charter commit no longer start it (in the clone) |
| Commit `.claude/settings.json` | pre-commit gate | refused without `CHARTER_OWNER=1`, accepted with it (in the clone) |
| Wire the gate into `lefthook.yml` | a commit | lefthook ran `charter` beside its own checks; the SessionStart banner stopped warning (in the clone) |
| Owner config | `charter check --all --strict --size` | 7 frozen, as the survey predicted (in the clone) |
| Decisions `merge-commits` and `sqlc-pin` | a commit that bumps sqlc in one file | refused by the decision's `check:` (in the clone) |
| Convert the `lecrm-docs-honesty` group | `charter probe` | the probes run and fail, since the work is not done; tele-claude's reader and writer keep the new keys (in the clone) |
| Archive `docs/sprint-plan.md` | the survey's citations | wrong: ADR-010 and two migrations cite it; reverted, which rehearsed a rollback (in the clone) |
| Split unit for `crm/handlers.go` | strict size | refused to an agent, accepted from the owner; the file warns instead of blocking (in the clone) |
| `charter synth --write` | `charter anchors charter/progress.md` | 216 claims, all anchored (in the clone) |

## The owner's answers

On 2026-09-13 the owner took the recommended option on all eight calls of the Slate `lecrm-charter-migration-2026-09-13` (operator report: the owner, 2026-09-13):

| Call | Answer | Source |
|---|---|---|
| L1 `## Done When` | The package reads it as the acceptance checklist; taskets listed as legacy at install still close with a warning (`lib.acceptance` in package/.charter/lib.py) | (operator report: the Slate answers, 2026-09-13) |
| L2 Demo redeploy | The charter paths join `paths-ignore` in `deploy-prod.yml`, merged before the install | (operator report: the Slate answers, 2026-09-13) |
| L3 lefthook | The gate runs as a `charter` command in `lefthook.yml` | (operator report: the Slate answers, 2026-09-13) |
| L4 Session hooks | `.claude/settings.json` is committed; Léo is not active, so no message | (operator report: the Slate answers, 2026-09-13) |
| L5 Size | BMAD tooling and tests are exempt | (operator report: the Slate answers, 2026-09-13) |
| L6 Real install | On a branch once the two sessions working in the tree are done, stopping before the pull request | (operator report: the Slate answers, 2026-09-13) |
| L7 Skill home | The personal layer is symlinked from the charter repository | (operator report: the Slate answers, 2026-09-13) |
| L8 Runbook | Project facts leave `docs/migration.md` | (operator report: the Slate answers, 2026-09-13) |
