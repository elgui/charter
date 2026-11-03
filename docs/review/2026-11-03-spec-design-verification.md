# Spec-design verification, 3 November 2026

The spec-design recipe remains an unpublished draft, separate from Charter 0.4.22. Its branch now includes current main, and the updated desk sheet makes that distinction explicit (`$ git log main..charter-spec-draft`; `package/VERSION`; `docs/cheatsheet.html`).

## Source and scope

Verification started from published main `b2df24e` and the eight-commit draft ending at `2fc5dca`. A separate verification branch was rebased onto main first. The original draft was then rebased onto the same main; their trees compare equal. Neither rebase published or installed the draft (`$ git diff --exit-code charter-spec-draft verify/spec-design-20261103`; `$ git log main..charter-spec-draft`).

The reviewed recipe, spec template, rule line and installer-owned paths are the draft's feature. Its executable-code change adds the two files to the package-size allowlist. The four warning/report fixes are already on main in 0.4.22 (`$ git diff main...charter-spec-draft --stat`; `docs/package.md`, § Versioning and upgrade).

## Behavioral checks

An isolated prototype installation of the draft passed 25 fixture assertions. Its installer manifest hashes both new files, and its package allowlist includes them. The five acceptance probes were extracted from the skill, filled with fixture ids and run through `/bin/sh`, matching the interpreter used by Charter (`$ git show charter-spec-draft:package/.claude/skills/charter-spec/SKILL.md`, § The spec unit; `package/.charter/bin/charter`, `cmd_probe`).

| Probe | Observed checks | Evidence |
|---|---|---|
| AC-1 | Rejects the untouched template and remaining table placeholders; accepts filled section structure | `docs/review/2026-11-03-spec-design-fixtures.txt:5` |
| AC-2 | Rejects blank question/recommendation; accepts a proposed decision before the ruling | `docs/review/2026-11-03-spec-design-fixtures.txt:8` |
| AC-3 | Accepts both held units; rejects a missing dependency on the first unit, wrong group and checkpoint with worker role | `docs/review/2026-11-03-spec-design-fixtures.txt:10` |
| AC-4 | Rejects absent review and incomplete fixed/dismissed answers; accepts fixed, dismissed, open and an explicit clean review | `docs/review/2026-11-03-spec-design-fixtures.txt:14` |
| AC-5 | Ignores spec-unit self-coverage; rejects a missing clause probe and accepts coverage on work units | `docs/review/2026-11-03-spec-design-fixtures.txt:23` |

These are tests of form, not proof that a design is correct. The recipe states that limit and requires independent review after the units exist (`$ git show charter-spec-draft:package/.claude/skills/charter-spec/SKILL.md`, § The spec unit and § The review).

Two more isolated fixtures upgraded an installed copy of current main to the draft, one on each track. Both installed the skill and template, preserved the existing scope and config byte for byte, and passed `charter check --staged` (`$ python3 <draft>/bin/charter-pkg upgrade <fixture>`; `$ python3 <fixture>/.charter/bin/charter check --staged`). No real project was upgraded by these fixtures.

The focused regression run on the rebased draft passed 88 tests: spec-step defects, installer, package-exact upgrades, size exceptions, owner acceptance and instruction review (`$ python3 -B -m unittest test_spec_step_defects test_installer test_release_commit_0_4_6 test_size_exceptions test_owner_acceptance test_instruction_review`, from `tests/` with resolved `TMPDIR`).

## Operational boundaries

The recipe uses one group, explicit checkpoint and unit dependencies, independent review, and a readiness row per unit. A Run All checkpoint is a human stop: Continue does not run its probe. Manual sessions must read owner obligations themselves; `unit start` does not enforce earlier units. The package chain ignores the human gate. The recipe therefore excludes chains (`$ git show charter-spec-draft:package/.claude/skills/charter-spec/SKILL.md`, § Does this rail need it? and § The units).

The ruling stamp is independent of checkpoint closure: the spec freezes when its ruling lands even if other start conditions remain open. This is the final draft correction, checked against the current skill and template (`$ git show charter-spec-draft --`; `$ git show charter-spec-draft:package/charter/templates/spec.md`).

## Release and remaining authority

The approved D3 rule requires both a successful non-client trial under its elapsed-time threshold and evidence from built units. Passing regressions does not satisfy that rule (branch `charter-spec-draft`, `docs/proposals/2026-11-spec-step.md`, § How we would know; `$ owner show oa-cr4y`).

The non-client ruling was filed at 2026-11-02 22:47:37 UTC and answered at 2026-11-03 09:02:34 UTC: 614.95 minutes elapsed, compared with the approved 30 minutes. These are desk timestamps, not reading time. The existing rule therefore keeps the draft unreleased; this verification neither waives it nor starts another trial. Measurement checked 2026-11-03T16:03:33+00:00 (`$ owner show oa-xa6l --json`; `$ owner show oa-cr4y --json`).

Main and its remote tracking ref were synchronized after fetch. All registered worktrees were inspected; the original working checkout retains one pre-existing, unrelated untracked tasket. It was preserved. No stale branch or worktree was deleted (`$ git fetch origin`; `$ git status --short --branch`; `$ git worktree list --porcelain`; `$ git -C <worktree> status --porcelain=v1`).

The refreshed reference and its evidence are on a separate documentation branch. Its integration remains the owner's act; publication is a separate derived push ask (`AGENTS.md`, Working on charter itself; `docs/cheatsheet-review.md`).

The earlier acceptance-feature deployment handoffs are complete: the backend restart receipt closed at 2026-11-03 13:34:21 UTC and the dashboard deployment receipt at 13:39:30 UTC, both with exit 0 and verification true. These are existing execution receipts, not a new observation of application behavior; neither approval was reissued (`$ owner show oa-bhh6 --json`; `$ owner show oa-jcro --json`).

## Full regression result

The complete module list in `AGENTS.md` passed on both published main and the rebased draft: 752 tests each, one skipped in each run. Main took 962.111 seconds; the draft took 961.956 seconds. Both emitted non-fatal subprocess/file ResourceWarnings, with no failure or error blocks. The exact command and tested revisions are retained (`docs/review/2026-11-03-spec-design-tests.txt:4`).

The temporary verification worktree was removed after its run; its branch remains as the tested revision. The original draft and main working trees are clean. The documentation update is committed separately for owner integration (`$ git worktree list`; `$ git status --short --branch`; `$ git -C <draft> status --short --branch`).
