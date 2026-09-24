# Migration guide

Five starting points, each a sequence of steps with its rollback, then what to check after a migration, then how a new package version reaches a project. Facts about a particular project do not belong here: the survey measures them. Every step is a commit on a branch; the rollback of any step is `git revert` of that commit unless stated otherwise.

Common preconditions: a clean working tree (`git status --porcelain` empty), Python 3 on the machine, a checkout of `~/Projects/charter` at the version you want.

An existing project (paths C to E) starts with the survey, not with this page: `python3 ~/Projects/charter/bin/charter-pkg survey <project> --out <dir>` reads the project without writing to it, rehearses the install in a throwaway clone, and writes `survey.md` and a generated `plan.md` whose steps each name their check and rollback. The `Migrate` workflow of the personal `CharterAdmin` skill drives it end to end. Design and the leCRM rehearsal: `docs/design/migration-workflow.md`.

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

1. Branch. `charter-pkg install --track client` (or `prototype`), commit. A project that already runs git hooks keeps them; the installer says so, and the gate is added to that framework's pre-commit (`package/.charter/githooks/README.md`). The existing taskets are untouched; the installer lists those without an acceptance section in `charter/legacy-taskets.txt`, so an engine can still close them (with a warning). `charter check --all` and CI report 0 blocking on them because the done gate judges only taskets whose status changes to done in the change set. Rollback: uninstall, commit.
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

## What to check after a migration

- `python3 .charter/bin/charter check --all --strict` from a fresh clone: 0 blocking.
- Every clone that commits runs the gate: `git config core.hooksPath` is `.charter/githooks` after `python3 .charter/bin/charter setup` once per clone (the installer also sets it, and the SessionStart banner says when it is missing), or, in a project with a hook framework, the framework's own install puts the gate in each clone. tele-claude's automator and tcv2's engine commit from worktrees, which share their clone's hooks.
- `owner` in `charter/config.json` lists the git author names the owner commits under, and the commits that set up the scope and the config are theirs.
- Optional, and outside the repository: GitHub branch protection on `main` with required review from code owners for `charter/`, `.charter/` and `.github/workflows/`; that is the only lock a pull request cannot edit (`docs/gates.md` § Owner-only changes).
- The taskets still appear on the tele-claude dashboard with their statuses; the new keys are stored and ignored there until `project_tasket_reader.py` learns them, which is a tele-claude change, not a charter step.
- The next progress update is `charter synth`, not a new progress file.

## A new package version reaching a project

1. In `~/Projects/charter`: bump `package/VERSION`, change the package, run the tests, commit, tag.
2. In the project, on a branch: `charter-pkg upgrade <project> --dry-run` and read the diff; `charter-pkg upgrade <project>`; review `git diff`; commit "charter <version>" as the owner (the commit touches `.charter/`, an owner-only path CI checks). From 0.1.0: the upgrade also writes `charter/legacy-taskets.txt`; then run `python3 .charter/bin/charter setup` to move the gate log and session records out of `.charter/state/`. A 0.1.0 `charter/config.json` keeps working: its flat price table becomes the `default` row, and the package's per-model rows apply to the models it does not name. From 0.2.0: ledger records folded earlier carry no subagent usage, so the synthesis prints the totals over them as lower bounds. No step is needed.
3. Owned files the project modified are kept and listed; reconcile them by hand or re-run with `--force`.
4. The personal-layer SessionStart hook reports "package X available, Y installed" until step 2 is done.
5. Rollback: `git revert` of the upgrade commit; `charter/VERSION` and the manifest revert with it.
