# Migration guide

How a project adopts the method, from five starting points: each a sequence of steps with its rollback, then what the owner checks after a migration. The install itself, with its preconditions, the owner's commit, per-clone setup and upgrades, is `docs/install.md`; this page starts where a step says "install". Facts about a particular project do not belong here: the survey measures them. Every step is a commit on a branch; the rollback of any step is `git revert` of that commit unless stated otherwise.

An existing project (paths C to E) starts with the survey (`docs/install.md` step 2), which writes a generated `plan.md` whose steps each name their check and rollback. The `Migrate` workflow of the machine layer's `CharterAdmin` skill drives it end to end (`machine/README.md`). Design and the leCRM rehearsal: `docs/design/migration-workflow.md`.

## Path A: a new client project

1. Create the repository, first commit; the survey and the install need one (`docs/install.md` step 0). Rollback: delete the repository.
2. Install with `--track client` (`docs/install.md`); the owner commits it with `owner` set in `charter/config.json`. Rollback: `charter-pkg uninstall`, committed by the owner, or `git revert` of the install.
3. The owner writes `charter/scope.md` from the signed devis (template `package/charter/templates/scope.md`): one in-scope item per sold deliverable with the paths it will live in, the out-of-scope items the conversation raised, the assumptions the price rests on. An agent may draft it outside the project; the file is owner-only (`package/.claude/rules/charter.md:32`). Commit. Rollback: revert.
4. Create the first units from the scope with the `charter-unit` skill or the Tasket skill: one deliverable each, `scope:` set, `perimeter:` set, acceptance probes named (`package/.claude/skills/charter-unit/SKILL.md`). Commit. Rollback: revert.
5. Record two project decisions the gates rely on, as the owner. `charter/decisions/merge-commits.md`: pull requests are merged with a merge commit, because a squash or rebase merge removes the commits units cite as evidence (limit L4 in `docs/review/2026-09-11-weakness-evaluation.md`). And, if the test suite runs on this machine without live credentials, set `probes.at_commit` to `true` in `charter/config.json`, so a unit's probes are re-run by the commit that closes it; set `probes.in_ci` too once the workflow installs the test dependencies. Commit. Rollback: revert.
6. Run `charter check --all`; expect 0 blocking (`docs/install.md` step 9). The owner pushes; the CI workflow runs on the first pull request (`package/.github/workflows/charter.yml`).

## Path B: a new personal prototype

1. Repository, first commit (`docs/install.md` step 0).
2. Install with `--track prototype` (`docs/install.md`); the owner commits it. No scope file; the scope gate is off, decisions, size and done gates are on.
3. Kick off with `bmad-quick-dev` or party mode if you like; when the prototype has a deliverable, write it as a unit with acceptance probes (`docs/method.md` § Two tracks, row BMAD).
4. When a client appears, the owner writes `charter/scope.md`, sets `track` to `client`, and commits (`docs/install.md` step 1). Rollback: revert that commit.

## Path C: an existing project with taskets

1. Install on a branch, following the survey's plan (`docs/install.md`). A project that already runs git hooks keeps them; the installer says so, and the gate is added to that framework's pre-commit (`docs/install.md` step 6). The existing taskets are untouched; the installer lists those without an acceptance section in `charter/legacy-taskets.txt`, so an engine can still close them (with a warning). `charter check --all` and CI report 0 blocking on them because the done gate judges only taskets whose status changes to done in the change set. Rollback: uninstall, commit.
2. The owner writes the scope (client track) and records the decisions of Path A step 5; commit (`package/.claude/rules/charter.md:32`).
3. Triage the taskets with the existing Housekeep audit: each open one gets `scope:` and `perimeter:` and an `## Acceptance` section with probes, or is parked with a line saying why. A tasket with an acceptance section is gated whether or not it is listed; remove its id from `charter/legacy-taskets.txt` as you go. Taskets already `done` stay as they are. Since 0.4.4 the synthesis lists those done before the install commit, and the legacy ones without `## Acceptance`, under "Done before charter", apart from the units done under charter without evidence (`_unit_state` in `package/.charter/bin/charter`). Commit per batch. Rollback: revert the batch.
4. Turn any decision that lives in `CLAUDE.md` or in a tasket body into `charter/decisions/<slug>.md`; leave a one-line pointer in `CLAUDE.md` if other text refers to it (`package/.claude/rules/charter.md:42`). `charter decisions index`. Commit. Rollback: revert.
5. `charter synth --write`, read it, commit (`package/.claude/skills/charter-progress/SKILL.md`).

## Path D: an existing project with BMAD

1. Path C steps 1 and 2: the install (`docs/install.md`), then the scope and decisions.
2. Keep `_bmad/` and the planning artifacts (brief, PRD, architecture, epics) where they are; they are inputs. Cite them from units (`## Context`; `package/charter/templates/unit.md:18-20`).
3. Stop editing `sprint-status.yaml` and stories: the unit is the tasket. If a story is in flight, create its unit with the story's acceptance criteria turned into probes and mark the story file with a pointer. Commit. BMAD on the client track is planning artifacts only (`docs/method.md` § Two tracks).
4. `BMADBridge` workflows `StoryToAlgorithm`, `SpecToTasks`, `UpdateSprint` are not used (they never ran in any project, `docs/report-2026-09-11.md` § The map, lane 3); `BrainstormToCouncil` and party mode stay for ideation.
5. Rollback of steps 3 and 4: nothing to revert; resume editing the BMAD files. The installer writes nothing under `_bmad/` (`OWNED` in `bin/charter-pkg`).

## Path E: an existing project with ad-hoc documents

1. Path C steps 1 and 2: the install (`docs/install.md`), then the scope and decisions.
2. Inventory root markdown: for each file decide keep (reference), fold into a decision, fold into a unit's context, or archive under `docs/history/` with a one-line index. Progress and status files are archived, not kept: the synthesis replaces them (`docs/method.md` § Less method, not more). One commit per group. Rollback: revert the group.
3. Governance size: `charter check --all --size --strict` lists files over the limits; `CLAUDE.md` over 400 lines or 32 KiB is frozen for growth until split (`package/.charter/lib.py:36-38`; the decisions that live in it move out in step 4 of path C).
4. Path C steps 3 to 5: triage, decisions, synthesis (the survey's `plan.md` lists them, `bin/charter_plan.py`).

## What to check after a migration

- The checks of `docs/install.md` step 9 pass, the fresh-clone one included.
- Every clone that commits runs the gate (`docs/install.md` § Every other clone). tele-claude's automator and tcv2's engine commit from worktrees, which share their clone's hooks.
- `owner` in `charter/config.json` lists the git author names the owner commits under, and the commits that set up the scope and the config are theirs (`check_owner_commits` in `package/.charter/checks.py`).
- Optional, and outside the repository: GitHub branch protection on `main` with required review from code owners for `charter/`, `.charter/` and `.github/workflows/`; that is the only lock a pull request cannot edit (`docs/gates.md` § Owner-only changes).
- The taskets still appear on the tele-claude dashboard with their statuses; the new keys are stored and ignored there until `project_tasket_reader.py` learns them, which is a tele-claude change, not a charter step (`docs/method.md` § Seams designed, not built, Engines).
- The next progress update is `charter synth`, not a new progress file (`package/.claude/skills/charter-progress/SKILL.md`).

## A new package version reaching a project

The procedure is `docs/install.md` § Upgrade. What each version asks of a project after the upgrade is in `docs/package.md` § Versioning and upgrade. Changing the package itself (edit, test, bump `package/VERSION`) is described in `AGENTS.md` at the root of this repository.
