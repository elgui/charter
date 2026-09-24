# Migrate

Move an existing project onto charter: measure it with code, rehearse in a clone, put the owner's calls on a Slate, then execute one checked commit at a time on a branch.

```bash
~/.claude/Tools/SkillWorkflowNotification Migrate CharterAdmin
```
```
Running the **Migrate** workflow from the **CharterAdmin** skill...
```

## Rules

1. **Project facts come from the survey.** Never from memory, an old runbook or another session's notes. Quote a number only from a survey run today, with the command it came from. A fact the survey does not measure is measured by hand with the command cited, or marked `(inference)`.
2. **Nothing writes to the project before the owner's go-ahead.** The survey only reads. Until phase 5 there is no install, no branch, no `git fetch`, and no `charter anchors --root <project>`, because that command appends to the project's gate log.
3. **Rehearse before acting.** The survey rehearses the install; phase 4 rehearses the rest of the plan.
4. **One step, one commit, one check.** Every step lands on the branch `charter/install` as its own commit, is staged by name with the plan's `git add` list (never `git add -A`), and is followed by its check. A red check stops the migration: revert that commit and report.
5. **The owner's acts stay the owner's.** These are the commits that touch owner-only paths (the install, the config, `.claude/settings.json`), which the owner makes; telling collaborators; pushing, opening or merging the pull request, and anything that deploys. An explicit answer in the session or on the Slate is the owner's word; nothing else is.
6. **No figures in a repository.** `charter/scope.md` names deliverables, paths and assumptions, never a price or a rate.

## Phase 1: survey

```bash
M=~/Projects/charter/bin/charter-pkg
OUT=<scratchpad>/survey-<name>
python3 $M survey <project> --track prototype --out $OUT
```

- Read `$OUT/survey.md` and `$OUT/plan.md` in full. `$OUT/survey.json` holds the same facts for anything you compute.
- Exit 3 means a rendered line failed its own anchoring check. That is a survey bug: fix `bin/charter_plan.py` in the charter repository with a test, never the output by hand.
- When the report lists a test command, run the survey again with `--test-cmd "<the unit-test command>"`. The rehearsal clone has no untracked files and so no `.env`. Exit 0 there makes `probes.at_commit: true` viable.
- The flags are in `tools/Survey.help.md`.

## Phase 2: settle what the facts settle

Go through the owner decisions in `plan.md`:

- **Track.** Use `client` only when a signed devis or contract covers the project; look in `${PAI_DATA_DIR}/35_CLIENTS/<client>/`. A proposal is not a scope. Otherwise use `prototype`. If the track changes, run the survey again with `--track client`.
- **Lookups are not decisions.** Anything a read of the repository answers, answer it yourself and cite the command.
- **Merge and add.** Merge decisions that always move together. Add the ones the facts raise that the generator cannot see, such as a collaborator's operator profile or a deploy the branch model implies.

## Phase 3: the owner's calls on a Slate

Use the Slate skill's Build workflow with `--publish`.

- Each decision's essence and background quote the survey, with the source.
- Always include a go-ahead decision for the real tree. Name the sessions and the uncommitted files the survey found there.
- Hand over the link, then carry on with phase 4 while the owner answers.

## Phase 4: rehearse the whole plan

```bash
TMPDIR=<scratchpad>/tmp python3 $M survey <project> --track <track> --keep-clone --out $OUT
```

The report's last line gives the kept clone's path; `TMPDIR` keeps it in the scratchpad rather than `/tmp`. The install is already committed there. Then:

1. Apply the rest of `plan.md` in that clone, taking each decision's default: wire the hook, write the config, record the decisions, triage one plan group of taskets, run `charter synth --write`.
2. Commit each step. The owner-only commits use `CHARTER_OWNER=1`, which is fine in a clone.
3. Run each step's check and keep its output.
4. Where the rehearsal disagrees with the plan, correct `plan.md` and cite `(in the clone)`. If the plan generator got it wrong, fix `bin/charter_plan.py` with a test.

## Phase 5: execute on the real tree, after the go-ahead only

Check the preconditions again rather than assume them:

```bash
python3 $M survey <project> --no-rehearse --offline --out $OUT/pre
```

- No sessions in the tree, and no uncommitted files.
- The main line equal to its origin.

Then:

1. `git -C <project> fetch origin`, then create the branch in its own worktree so the checkout, and anyone's uncommitted work in it, is never touched: `git -C <project> worktree add -b charter/install <scratchpad>/<name>-install origin/<main line>`. A change the plan merges first, such as `paths-ignore`, gets its own branch and worktree the same way.
2. `git -C <project> branch --unset-upstream charter/install`. A branch created from `origin/<main line>` tracks it, and under some `push.default` settings a bare `git push` would push it onto the main line.
3. Run the plan's steps in order in the worktree: make the change, stage it by name, commit, run the check. A step that touches owner-only paths stops with its files staged: hand the owner the commit command (`docs/install.md` step 8 in the charter repository) and continue after their commit. Never set `CHARTER_OWNER` or pass `--no-verify` on the real tree; only the throwaway rehearsal clone of phase 4 uses it.
4. After each step that changes a measured fact (the install, the config, a triage batch), run `python3 $M survey <project> --ref charter/install --no-rehearse --offline --out $OUT/after-<n>`. `--ref` reads the branch, never the checkout.
5. Draft the pull-request descriptions in the scratchpad and check them with `python3 .charter/bin/charter anchors --pr <file>` from the worktree.
6. `git -C <project> worktree remove <worktree>`; the branches stay. Stop before the pull request. The owner pushes, opens it, merges it and deploys.

## Phase 6: report

- The paths of the survey and the plan.
- The step table, with each check's output and the commit it followed.
- What is left, the Slate link, and the decisions still open.
- If the survey lacked a measurement you needed, add it to `bin/charter_survey.py` with a test before the next migration, and say so.
