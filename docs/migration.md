# Migration guide

Five starting points, each a sequence of steps with its rollback, then orqueveaux as the worked example, then how a new package version reaches a project. Every step is a commit on a branch; the rollback of any step is `git revert` of that commit unless stated otherwise.

Common preconditions: a clean working tree (`git status --porcelain` empty), Python 3 on the machine, a checkout of `~/Projects/methodo` at the version you want.

## Path A: a new client project

1. Create the repository, first commit. Rollback: delete the repository.
2. `charter-pkg install <project> --track client`, commit. Rollback: `charter-pkg uninstall`, commit.
3. Write `charter/scope.md` from the signed devis (template `charter/templates/scope.md`): one in-scope item per sold deliverable with the paths it will live in, the out-of-scope items the conversation raised, the assumptions the price rests on. Set `owner` in `charter/config.json` to your git author name: CI refuses owner-only changes from anyone else. Commit. Rollback: revert.
4. Create the first units from the scope with the `charter-unit` skill or the Tasket skill: one deliverable each, `scope:` set, `perimeter:` set, acceptance probes named. Commit. Rollback: revert.
5. Record two project decisions the gates rely on, as the owner. `charter/decisions/merge-commits.md`: pull requests are merged with a merge commit, because a squash or rebase merge removes the commits units cite as evidence (limit L4 in `docs/review/2026-09-11-weakness-evaluation.md`). And, if the test suite runs on this machine without live credentials, set `probes.at_commit` to `true` in `charter/config.json`, so a unit's probes are re-run by the commit that closes it; set `probes.in_ci` too once the workflow installs the test dependencies. Commit. Rollback: revert.
6. Run `charter check --all`; expect 0 blocking. Push; the CI workflow runs on the first pull request.

## Path B: a new personal prototype

1. Repository, first commit.
2. `charter-pkg install <project> --track prototype`, commit. No scope file; the scope gate is off, decisions, size and done gates are on.
3. Kick off with `bmad-quick-dev` or party mode if you like; when the prototype has a deliverable, write it as a unit with acceptance probes.
4. When a client appears: write `charter/scope.md`, set `track` to `client`, commit. Rollback: revert that commit.

## Path C: an existing project with taskets

1. Branch. `charter-pkg install --track client` (or `prototype`), commit. The existing taskets are untouched; the installer lists those without an acceptance section in `charter/legacy-taskets.txt`, so an engine can still close them (with a warning). `charter check --all` and CI report 0 blocking on them because the done gate judges only taskets whose status changes to done in the change set. Rollback: uninstall, commit.
2. Write the scope, set `owner`, and record the decisions of Path A step 5; commit.
3. Triage the taskets with the existing Housekeep audit: each open one gets `scope:` and `perimeter:` and an `## Acceptance` section with probes, or is parked with a line saying why. A tasket with an acceptance section is gated whether or not it is listed; remove its id from `charter/legacy-taskets.txt` as you go. Taskets already `done` stay as they are; the synthesis lists them under "done but not accepted" until someone adds evidence, which is the truthful state. Commit per batch. Rollback: revert the batch.
4. Turn any decision that lives in `CLAUDE.md` or in a tasket body into `charter/decisions/<slug>.md`; leave a one-line pointer in `CLAUDE.md` if other text refers to it. `charter decisions index`. Commit. Rollback: revert.
5. `charter synth --write`, read it, commit.

## Path D: an existing project with BMAD

1. Path C steps 1 and 2.
2. Keep `_bmad/` and the planning artifacts (brief, PRD, architecture, epics) where they are; they are inputs. Cite them from units (`## Context`).
3. Stop editing `sprint-status.yaml` and stories: the unit is the tasket. If a story is in flight, create its unit with the story's acceptance criteria turned into probes and mark the story file with a pointer. Commit.
4. `BMADBridge` workflows `StoryToAlgorithm`, `SpecToTasks`, `UpdateSprint` are not used (they never ran in any project, `docs/report-2026-09-11.md` § Map, lane 3); `BrainstormToCouncil` and party mode stay for ideation.
5. Rollback of steps 3 and 4: nothing to revert; resume editing the BMAD files.

## Path E: an existing project with ad-hoc documents

1. Path C steps 1 and 2.
2. Inventory root markdown: for each file decide keep (reference), fold into a decision, fold into a unit's context, or archive under `docs/history/` with a one-line index. Progress and status files are archived, not kept: the synthesis replaces them. One commit per group. Rollback: revert the group.
3. Governance size: `charter check --all --size --strict` lists files over the limits; `CLAUDE.md` over 400 lines is frozen for growth until split (the decisions that live in it move out in step 4 of path C).
4. Path C steps 3 to 5.

## Orqueveaux, worked example

State on 2026-09-11 (lane 6, `docs/report-2026-09-11.md` § Map): 161 tracked files; the checkout is on `chore/docs-housekeeping` with uncommitted changes, `main` and `staging` have diverged (34 and 19 commits each way); 33 tracked root markdown files, 14 of them per-phase progress files last committed in December 2025; `CLAUDE.md` 462 lines; no scope document; the devis lives in the vault; 7 taskets, none with acceptance criteria; CI has every quality gate on `continue-on-error`; the deploy workflow force-pushes to Dokku after an 80% coverage gate. The steps below were rehearsed on a clone of `main` at `7093485` (`docs/trials/2026-09-11.md` § Orqueveaux clone); the real repository was not touched.

### Before anything

- Commit or stash the work on `chore/docs-housekeeping`; do the migration on a new branch from `main`.
- `tests/conftest.py:153-166` holds fallback values shaped like a Stripe key and a HubSpot token (lane 6 § 7). Confirm they are test placeholders, or rotate them, before the repository's visibility changes. Not a charter step, but the first thing a reviewer will see.

### Steps

| # | Step | Files | Check afterwards | Rollback |
|---|---|---|---|---|
| 1 | `charter-pkg install ~/Projects/orqueveaux --track client`; commit "charter 0.2.1" | adds `.charter/`, `charter/` (with `legacy-taskets.txt` listing the seven taskets), `.claude/settings.json`, `.claude/rules/charter.md`, three skills, one agent, `.github/workflows/charter.yml`, `AGENTS.md`; appends one line to `.gitignore` | `charter check --all` → 0 blocking, warnings for the missing scope and the unset owner | `charter-pkg uninstall`, commit |
| 2 | Write `charter/scope.md` from the devis in `${PAI_DATA_DIR}/35_CLIENTS/Orquevaux/proposal-2026-09/`: the three payment stages, the HubSpot order and line-item sync, the admin dashboard as in-scope items with paths under `app/`; the upsells listed in `docs/AUDIT_AND_BUSINESS_REPORT_2026-06.md` as out-of-scope items until sold; assumptions (Stripe test mode for QA, HubSpot API limits). Set `owner` in `charter/config.json`; set `probes.at_commit` to `true` once the unit tests run without the live Stripe and HubSpot keys | `charter/scope.md`, `charter/config.json` | `charter check --all --scope` → only "legacy" warnings if any existing file sits under an out-of-scope glob | revert |
| 3 | Convert the seven taskets: keep ids and every key the engines read; add `scope:`, `perimeter:` (the `## Fix` section already names the files), `## Acceptance` with probes (`pytest tests/unit/test_webhook_processor.py -k application_status -q` and the like), rename `## Fix` to `## Context` plus `## Log`; remove each converted id from `charter/legacy-taskets.txt`. Their `status: pending` is not in either engine's vocabulary (`~/Projects/tele-claude/services/project_tasket_reader.py:23-34`); set `next` or `later` | `.taskets/*.md`, `charter/legacy-taskets.txt` | `charter check --all --done --scope` clean; `charter synth` lists them under "Open" with criteria counts; `charter probe <id>` runs each probe | revert |
| 4 | Decisions out of prose: `DOMAIN_DECISION.md` becomes `charter/decisions/domain.md`; the "Documentation Ownership by Agent" section of `CLAUDE.md:413-455` becomes `charter/decisions/doc-ownership.md` or is dropped (two of its three agents were never created); the idempotency store choice recorded in `app/utils/idempotency.py:1-13` becomes `charter/decisions/idempotency-store.md` with `binds: [app/utils/idempotency.py]` and the marker added in that file; the currency rounding rule in `app/utils/currency_parser.py:66-68` likewise with a `check:` such as `grep -q ROUND_HALF_UP app/utils/currency_parser.py`. `charter decisions index` | `charter/decisions/*.md`, two source files gain a comment | `charter check --all --decisions` clean | revert |
| 5 | Archive the fourteen `PHASE*` files, `IMPLEMENTATION_PLAN.md`, `NEXT_STEPS.md` and `docs/COMPLETED_PHASES.md` under `docs/history/` with `docs/history/README.md` listing them and their last-commit dates. Keep `JOURNAL.md` (the incident log the taskets cite), `ARCHITECTURE.md`, `CONFIGURATION.md`, `FORM_MAPPING_GUIDE.md`, `TESTING.md`, `LOCAL_TESTING.md`, `README.md`, `overview.md` and the setup runbooks. Move `QUICK_SSL_COMMANDS.sh` to `scripts/` | 18 files move | `git ls-files '*.md' | grep -v / | wc -l` drops from 33 to 17 | `git mv` back, or revert |
| 6 | `CLAUDE.md` (462 lines, over the 400-line governance limit, frozen for growth): remove the sections moved in step 4 and any command list that `TESTING.md` already carries; add one line pointing at `.claude/rules/charter.md`. Target under 300 lines | `CLAUDE.md` | `charter check --all --size --strict` no longer lists `CLAUDE.md` | revert |
| 7 | `GIT_WORKFLOW.md`: replace the promotion model with the observed one (`staging` and `main` diverged) or reconcile the branches first; either way record the branch rule as `charter/decisions/branch-model.md`, with merge commits only so evidence commits survive (Path A step 5). `.claude/agents/archive/` is deleted (already marked archive) | 2 files | `charter check --all` clean | revert |
| 8 | CI: keep `ci.yml` and `deploy.yml`; the new `charter.yml` runs beside them. Consider turning `continue-on-error` off for `ruff` and `mypy` in `ci.yml` as a separate decision; not a charter step | `.github/workflows/` | the PR shows three workflows | revert |
| 9 | The ten source and test files over 800 lines (`INFRASTRUCTURE.md` 3,048, `tests/unit/test_hubspot_service.py` 2,334, `app/services/hubspot_service.py` 1,641, ...; full list in `docs/trials/2026-09-11.md` § Orqueveaux clone) are frozen for growth from step 1. Create one `kind: split` unit per file that will need to grow soon (`hubspot_service.py`, `checkout.py`, `mapping_config.py`); the rest wait | `.taskets/` | `charter check --all --size --strict` shows them as warnings while the split units are open | close or delete the split units |
| 10 | `charter synth --write`, commit; open the pull request with a body that passes `charter anchors --pr` | `charter/progress.md` | CI green on `charter.yml` (the written synthesis carries no per-machine lines, so it passes from a clean clone) | revert |

### What to check afterwards

- `python3 .charter/bin/charter check --all --strict` from a fresh clone: 0 blocking.
- `git config core.hooksPath` is `.charter/githooks` in every clone that commits: run `python3 .charter/bin/charter setup` once per clone (the installer also sets it on every run, and the SessionStart banner says when it is missing). tele-claude's automator and tcv2's engine commit from worktrees, which inherit it from their clone.
- `owner` in `charter/config.json` is your git author name or email, and the commits that set up the scope and the config are yours.
- Optional, and outside the repository: GitHub branch protection on `main` with required review from code owners for `charter/`, `.charter/` and `.github/workflows/`; that is the only lock a pull request cannot edit (`docs/gates.md` § Owner-only changes).
- The seven taskets still appear on the tele-claude dashboard with their statuses (the new keys are stored and ignored there until `project_tasket_reader.py:230-234` learns them; that change is a tele-claude tasket, not a charter step).
- The next client update is `charter synth` plus the scope section, not a new `PHASE8_PROGRESS.md`.

## A new package version reaching a project

1. In `~/Projects/methodo`: bump `package/VERSION`, change the package, run the tests, commit, tag.
2. In the project, on a branch: `charter-pkg upgrade <project> --dry-run` and read the diff; `charter-pkg upgrade <project>`; review `git diff`; commit "charter <version>" as the owner (the commit touches `.charter/`, an owner-only path CI checks). From 0.1.0: the upgrade also writes `charter/legacy-taskets.txt`; then run `python3 .charter/bin/charter setup` to move the gate log and session records out of `.charter/state/`. A 0.1.0 `charter/config.json` keeps working: its flat price table becomes the `default` row, and the package's per-model rows apply to the models it does not name. From 0.2.0: ledger records folded earlier carry no subagent usage, so the synthesis prints the totals over them as lower bounds. No step is needed.
3. Owned files the project modified are kept and listed; reconcile them by hand or re-run with `--force`.
4. The personal-layer SessionStart hook reports "package X available, Y installed" until step 2 is done.
5. Rollback: `git revert` of the upgrade commit; `charter/VERSION` and the manifest revert with it.
