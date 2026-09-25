# Installing charter on a project

The one procedure for an agent asked to install, set up, upgrade or remove charter on a project. Other documents point here rather than repeat it. The outputs quoted below come from a rehearsal of charter 0.4.4 on a scratch repository on 2026-09-25 (in the scratchpad); the counts and paths vary with the project, and the version in each line is the one in `package/VERSION`. Once the owner has committed the install, day-to-day work follows `docs/daily-use.md`.

Conventions used throughout:

```
C=/absolute/path/to/a/charter/checkout    # a clone of this repository; ~/Projects/charter on the owner's machine
M=$C/bin/charter-pkg                      # the installer; Python 3 standard library only
P=/absolute/path/to/the/project
```

Nothing in the installer or the survey depends on where the checkout sits or on the home directory; `SurveyOnAnotherMachine` in `tests/test_migration.py` runs the survey with an empty `HOME`.

## Rules for the agent

1. **Owner-only files are committed by the owner.** In an installed project these paths are the owner's: `.charter/**`, `charter/config.json`, `charter/scope.md`, `charter/rails.md`, `.claude/settings.json`, `.claude/settings.local.json` and `.github/workflows/charter.yml` (the full list, fields included, is in `package/.claude/rules/charter.md` § What only the owner changes). The pre-commit gate refuses a commit of them made from inside Claude Code (`docs/gates.md` § Owner-only changes). An install always touches them, so **you prepare and stage; the owner commits** (step 8). An upgrade touches them too, but from 0.4.6 package files exactly as the installer wrote them are not an owner-only change (`release_change` in `package/.charter/checks.py`): the installer's block says who commits, and when it says an agent, you commit. Only a merge into `.claude/settings.json` or a kept local file sends an upgrade to the owner.
2. **Never set `CHARTER_OWNER`, never pass `--no-verify`**, and never work around a refusal by writing the file through Bash. The refusal is the method working, not a fault (`package/.claude/rules/charter.md:36`). The one exception is a throwaway rehearsal clone that the survey made (`--keep-clone`), which is not the project.
3. **Never push, open or merge a pull request, or deploy.** Those are the owner's acts (`package/.claude/rules/charter.md` § Decisions and memory, "Commitments").
4. **Facts about an existing project come from the survey** (step 2), measured today, never from memory or another session's notes (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md:14`).
5. **Stop and report** any check that fails (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md:17`).

## Step 0: preconditions

| Check | Command | Expected | If not |
|---|---|---|---|
| The project is a git repository with a commit | `git -C $P rev-parse --verify HEAD` | a commit SHA | A new project: `git init`, a first commit, then continue (`bin/charter-pkg:498` refuses a survey without one) |
| The working tree is clean | `git -C $P status --porcelain` | no output | Stop. List the files to the owner. Do not stash, commit or discard someone else's work. `install` does not check this itself (`do_install` in `bin/charter-pkg`), so this step is the only guard |
| No other session works in the tree | `tmux list-panes -a -F '#{pane_current_path}' \| grep -F "$P"` | no output (`no server running` also means none) | Stop and tell the owner, or work in a separate worktree (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md:76`) |
| The charter checkout is the version you mean to install | `cat $C/package/VERSION; git -C $C status --short` | the version, as in `package/VERSION`; no output | Ask the owner which version to install |
| Whether charter is already there | `python3 $M status $P` | `package version: X; installed: none` (`bin/charter-pkg:479`) | `installed: <version>`: go to [Upgrade](#upgrade) instead |

## Step 1: choose the track

- **`client`** only when a signed devis or contract covers the project (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md:38`). The scope gate is on and `charter/scope.md` is required.
- **`prototype`** otherwise. No scope file; the decisions, size and done gates stay hard (`docs/method.md:188-202`).

The full comparison is `docs/method.md` § Two tracks. The survey and the first install both require `--track` and refuse to run without it, before writing anything (`main` and `do_install` in `bin/charter-pkg`). Once `charter/config.json` exists the installer never changes its track: a later `--track` that differs prints `NOTE --track <track> not applied: charter/config.json already says track <other>; the owner changes it there`. A prototype that gains a client switches when the owner writes `charter/scope.md` and sets `track` to `client`.

## Step 2: choose the path

- **A new project** (a first commit and little else): step 3 (`docs/migration.md` Paths A and B).
- **A project that already has code, taskets or documents**: survey it first. The survey reads the project without writing to it and rehearses the install in a throwaway clone (`docs/design/migration-workflow.md`):

  ```
  python3 $M survey $P --track <track> --out <a directory outside the project>
  ```

  Expected: `wrote <dir>/survey.json, survey.md, plan.md`, exit 0. Read `survey.md` and `plan.md` in full. The plan's steps, each with its check and rollback, take the place of steps 3 to 7 below for this project; steps 0, 8 and 9 and the rules above still apply. With the personal layer installed, the `Migrate` workflow of the `CharterAdmin` skill drives the whole survey, rehearsal and execution (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md`). What comes after the install for each kind of project (taskets, BMAD, ad-hoc documents) is in `docs/migration.md`.

  If the survey changes your view of the track, run it again with the other `--track`. Survey exit codes: 2 for a missing `--track`, a directory that is not a git repository with a commit, an `--out` inside the project or an unknown `--ref`; 3 when a line of its own report fails the anchoring check, which is a bug in `bin/charter_plan.py` to fix with a test, never by editing the output.

## Step 3: branch

```
git -C $P switch -c charter/install
```

Never on the main line.

## Step 4: dry run

```
python3 $M install $P --track <track> --dry-run
```

Expected: one `would create`, `would seed`, `would merge hooks into` or `would update` line per path, then `dry run: <n> change(s); charter <version>` (`bin/charter-pkg:298`; 35 on a repository with no charter files, in the scratchpad rehearsal). `git -C $P status --porcelain` still prints nothing. Read the output for these lines:

| Line | Meaning | What to do |
|---|---|---|
| `KEEP git hooks: <project> runs <framework>; pointing core.hooksPath at .charter/githooks would stop them. ...` | The project runs lefthook, pre-commit, husky or its own `.git/hooks` scripts (`bin/charter-pkg:276`) | Continue; step 6 wires the gate into that framework |
| `IGNORED by <file> (<pattern>), so a commit will not carry it: <path>` | The project's `.gitignore` matches a path the installer writes, often `.claude/settings.json` (`bin/charter-pkg:294`; `docs/design/migration-workflow.md:24`) | Ask the owner: stop ignoring it so the commit carries it, or keep it local and accept that other clones have no session hooks |
| `would seed (<n> legacy tasket(s)) .../charter/legacy-taskets.txt` | Taskets without an acceptance section; they may still close, with a warning (`bin/charter-pkg:223`) | Nothing now; triage is in `docs/migration.md` Path C |

## Step 5: install

```
python3 $M install $P --track <track>
```

Expected: the same lines without `would`, then `<n> change(s); charter <version>`, and, unless hooks were kept, `git config core.hooksPath .charter/githooks (was unset)` (`bin/charter-pkg:280`). Then:

- `python3 $M install $P --track <track>` again prints `charter <version> already installed in <project>; nothing to do` (`bin/charter-pkg:296`). The install is idempotent.
- `git -C $P config core.hooksPath` prints `.charter/githooks`, unless hooks were kept (`bin/charter-pkg:280`).

## Step 6: a project that already runs git hooks

Skip this step unless step 4 printed `KEEP git hooks`. `core.hooksPath` replaces a clone's whole hook directory, so the installer leaves it alone and the gate runs from the existing framework instead (`package/.charter/githooks/README.md`). Add the gate to the framework's pre-commit. For lefthook, in `lefthook.yml`:

```
pre-commit:
  commands:
    charter:
      run: python3 -B .charter/bin/charter check --staged
```

The snippets for pre-commit and husky are in `package/.charter/githooks/README.md`. Check: `cd $P && python3 .charter/bin/charter setup` prints `git hook: lefthook.yml runs the charter gate; core.hooksPath left unset`. `--replace-hooks` would stop the project's other hooks: use it only on the owner's explicit word.

## Step 7: what is staged

From 0.4.5 the installer stages what it wrote, by name, and nothing else (`stage_and_hand_over` in `bin/charter-pkg`). It never runs `git add -A` over the project, which could take untracked files that are not yours. A path the project's `.gitignore` matches is left out and reported as `IGNORED` (step 4). If you changed a framework file in step 6, stage it by name yourself.

Check: `git -C $P diff --cached --name-only` lists the installer's files and your framework file, and nothing else (34 staged files on a repository with no charter files, in the scratchpad rehearsal of 2026-09-25: `$ git -C $P diff --cached --name-only | wc -l`).

If a draft of `charter/scope.md` is wanted on the client track, write it outside the project (a scratchpad) from `charter/templates/scope.md` and hand it to the owner with the commit. The scope is the owner's file (`package/.claude/rules/charter.md:32`).

## Step 8: the owner commits

Owner's step. The installer ends with the handover block (`lib.handover` in `package/.charter/lib.py`):

```
Waiting on the owner: commit 34 staged file(s) on branch charter-install. The gate refuses this commit to an agent.
  in a Claude Code prompt:  ! CHARTER_OWNER=1 git -C /path/to/project commit -m 'charter 0.4.5' -- .charter/bin/charter ...
  from your own terminal:   git -C /path/to/project commit -m 'charter 0.4.5' -- .charter/bin/charter ...
```

The paths after `--` make git commit exactly those files, whatever else is staged or untracked (https://git-scm.com/docs/git-commit#Documentation/git-commit.txt---only), so the owner's other work cannot slip in. With `--`, git takes each listed file as it is in the working tree, so an edit the owner makes to one of them before committing, such as the `owner` value below, is carried without a new `git add`. If you staged more after the installer ran, `python3 .charter/bin/charter handover` prints the block again from the index (`cmd_handover` in `package/.charter/bin/charter`); it changes nothing.

Stop and hand over:

- first, the two command lines, copied verbatim from the block. Do not paraphrase them, and do not suggest starting a session with `CHARTER_OWNER=1`: that lifts the owner-only checks for everything the session does, where `!` lifts them for one command (`package/.charter/lib.py:189` reads the variable from the environment Claude Code started with);
- the `owner` value to put in `charter/config.json` (then `python3 .charter/bin/charter config` must print no `problem:` line, since a misspelled key is refused at this very commit; `docs/gates.md` § Config): the git author name or email the owner commits under (`git -C $P config user.name`, `git -C $P config user.email`), or a list of them. CI refuses owner-only changes from any other author once it is set, and warns while it is empty (`check_owner_commits` in `package/.charter/checks.py`). The install commit is the one place CI reads it from the change under review, so it belongs in this commit: the owner edits the file, then `git add charter/config.json`;
- on the client track, the scope draft;
- what else is untracked or modified in the project and stays out of the commit, in one line, so the owner knows it was seen (`$ git -C $P status --porcelain`).

In a Claude Code prompt, `!` runs the command in shell mode, without going through Claude, and adds its output to the session (https://code.claude.com/docs/en/interactive-mode#shell-mode-with-prefix). From the owner's own terminal, the gate cannot tell them apart from the owner and only warns, so no variable is needed.

Expected for the owner: `charter/protected warn [...]` lines from their own terminal, none with `CHARTER_OWNER=1`, then `charter check: 0 blocking, <n> warning(s) [staged, track <track>, opt-ins: none]` (`check_owner_only_staged` in `package/.charter/checks.py`).

If you run `git commit` yourself, the gate refuses it: one `charter/protected block [<path>]` line per owner-only file, each ending `Override: the owner commits it: leave it staged, run python3 .charter/bin/charter handover and give the owner the command it prints`, then `Refused.` (`OWNER_COMMIT_OVERRIDE` in `package/.charter/checks.py`). That is the expected outcome, not a fault; leave the files staged and hand over.

## Step 9: verify

After the owner's commit:

| Check | Command (from `$P`) | Expected |
|---|---|---|
| Every gate on the tree | `python3 .charter/bin/charter check --all` | `charter check: 0 blocking, ...`. A warning `charter/config.json names no owner` means `owner` is still empty (`package/.charter/checks.py:841`) |
| The installed version | `python3 .charter/bin/charter version` | the target version, as in `package/VERSION` |
| The config reads as written | `python3 .charter/bin/charter config` | `track <track>, opt-ins: none`, exit 0. A `problem:` line names a key, type or track the gates cannot read; the owner corrects it (`cmd_config` in `package/.charter/bin/charter`) |
| The files match the package | `python3 $M status $P` | `installed: <version>`, `locally modified: 0; missing: 0; differ from package: 0`, and `git core.hooksPath: .charter/githooks` (or `unset` where a framework runs the gate; `bin/charter-pkg:479-490`) |
| The session hooks run | start a new Claude Code session in `$P`, then `python3 .charter/bin/charter log` | the transcript shows the summary line `charter <version>, track <track>, opt-ins: ...` (a `systemMessage`; the full index goes to Claude's context only, https://code.claude.com/docs/en/hooks); the log has entries. A wrong hook path shows only as a non-blocking error on first run (`docs/gates.md` § Claude Code hooks) |
| The gate runs in a fresh clone | `git clone $P <scratch dir>/clone && cd <scratch dir>/clone && python3 .charter/bin/charter check --all --strict` | `0 blocking` (`docs/migration.md` § What to check after a migration) |

The owner's side of a migration (branch protection, telling collaborators, the tele-claude dashboard) is listed in `docs/migration.md` § What to check after a migration.

Report: the branch, the commit SHA, and the output of each check. Stop before the pull request: the owner pushes, opens it and merges it, with a merge commit (`docs/migration.md` Path A, step 5, says why). From here on, the project is worked as `docs/daily-use.md` describes.

## Every other clone: `setup`

Git does not clone repository config, so each clone activates the git hook once; its worktrees share it (`package/.charter/githooks/README.md:5-6`):

```
cd <clone> && python3 .charter/bin/charter setup
```

Expected, one of:

- `git config core.hooksPath .charter/githooks (was unset); worktrees of this clone share it` (`package/.charter/bin/charter:633`)
- `git hook already active (core.hooksPath = .charter/githooks)` (`package/.charter/bin/charter:624`)
- `git hook: <framework file> runs the charter gate; core.hooksPath left unset`: the framework's own install puts the gate in this clone (`package/.charter/bin/charter:626`).
- `KEEP git hooks: this clone runs <framework>; ...`: the project runs other hooks and the gate is not wired into them yet. Tell the owner (step 6); do not re-run with `--replace-hooks` (`package/.charter/bin/charter:628`).

`setup` needs no charter checkout. A clone that skips it is still gated by CI. The SessionStart banner says when the hook is missing (`package/.charter/githooks/README.md`).

## Upgrade

A new package version reaches a project only by an upgrade; nothing pulls it. The personal-layer SessionStart hook says `package X available, Y installed` when a project is behind (`personal/claude-home/hooks/charter-personal.py`).

1. Step 0 again: `upgrade` does not check the working tree either (`do_install` in `bin/charter-pkg` runs both).
2. `git -C $P switch -c charter-<version>`: the upgrade lands on a branch (`personal/claude-home/Skills/CharterAdmin/SKILL.md:65`).
3. Read the upgrade notes in `docs/package.md` § Versioning and upgrade for every version between the installed one and the target. Some ask for a step after the upgrade.
4. `python3 $M upgrade $P --dry-run`. Expected: `upgrade <installed> -> <version> in <project>`, a unified diff for each owned file that would change, then `dry run: <n> change(s); charter <version>` (`bin/charter-pkg:169-192`). `nothing installed in <project>; use install` means there is nothing to upgrade (`bin/charter-pkg:166`).
5. `python3 $M upgrade $P`. It stages what it wrote and ends with a block that says who commits. `Staged <n> file(s) ...; none is an owner-only change, so an agent commits them:` is followed by the command: run it yourself (from 0.4.6, `release_change` in `package/.charter/checks.py`). `Waiting on the owner:` is step 8's block. A line `KEEP (locally modified, use --force to overwrite) <path>` means the project changed a package file. Show the owner the difference; `--force` replaces it, on the owner's word only. `upgrade` never rewrites `charter/config.json`, so new config keys take the package defaults (`docs/package.md` § Versioning and upgrade).
6. Any step a version's note asks for that writes a file the owner does not own, such as `charter ledger fold` writing `charter/ledger.jsonl`: commit it yourself, apart from the upgrade, since the gate refuses only owner-only changes (`CLI_ONLY_FILES` in `package/.charter/checks.py`). Then commit the upgrade, or hand it over as in step 8 when the block says so. The report opens with what waits on the owner, if anything, then says what the upgrade changed.
7. Step 9, and the checks the version's note in `docs/package.md` asks for.

Several projects: `python3 $M fleet` lists every charter project under `~/Projects` (`--root` for another directory) with its version, branch and what waits on the owner, and reads only. `python3 $M fleet --upgrade` upgrades the ones behind and stages each. It commits a project itself when nothing staged is an owner-only change, through the project's gate (from 0.4.6), and ends with one handover block for the projects left, whose command commits each by pathspec (`do_fleet` in `bin/charter-pkg`). It lands each upgrade on the branch the project is on and does not run the checks of step 0, so read the table first. Hand any block over as in step 8.

Rollback: `git revert` of the upgrade commit; `charter/VERSION` and the manifest revert with it (`docs/migration.md` § A new package version reaching a project).

## Uninstall

```
python3 $M uninstall $P --dry-run
python3 $M uninstall $P
```

It removes the owned files whose hash matches the manifest, the hook entries, the `AGENTS.md` section, the `.gitignore` line and `core.hooksPath`. It keeps the project's own files (`charter/scope.md`, decisions, changes, `charter/config.json`, the legacy list, the ledger, `.taskets/`) and the gate log unless `--purge-state` (`bin/charter-pkg:305-397`). The removal touches owner-only paths, so the owner commits it (step 8). Right after an install, `git revert` of the install commit does the same.

## When a gate refuses

Every refusal names its override (`docs/method.md:119`). The common ones:

| Message | Cause | What the agent does |
|---|---|---|
| `charter/protected block [<path>]` at commit | An owner-only file committed from inside Claude Code (`check_owner_only_staged` in `package/.charter/checks.py`) | Leave it staged; `python3 .charter/bin/charter handover`; hand over (step 8) |
| A `PreToolUse` denial on an Edit or Write of an owner-only file | The same rule, in session (`docs/gates.md:35`) | Propose instead: a change request (`charter/templates/change.md`), a successor decision, or a draft outside the project; say so in your final message |
| `KEEP git hooks: ...` | The project runs another hook framework (`bin/charter-pkg:276`) | Step 6 |
| `IGNORED by ...` | `.gitignore` matches a written path (`bin/charter-pkg:294`) | Ask the owner (step 4) |
| `KEEP (locally modified, use --force to overwrite) <path>` | A package file changed in the project (`bin/charter-pkg:189`) | Show the owner; `--force` only on their word |
| `nothing installed in <project>; use install` | `upgrade` on a project without charter (`bin/charter-pkg:166`) | Step 2 |
| `the first install needs --track client or --track prototype` | `install` without `--track` on a project with no `charter/config.json` (`bin/charter-pkg:172`); nothing was written | Step 1, then pass `--track` |
| `charter-pkg survey: error: the following arguments are required: --track` | `survey` without `--track` (`main` in `bin/charter-pkg`) | Step 1, then pass `--track` |
| `charter/config block [charter/config.json]: charter/config.json: ...` | A key, a value's type or the track in the config is not one the gates read; an unknown track is read as `client` (`config_from` in `package/.charter/lib.py`) | Tell the owner; the message names the key and, for a near miss, the key meant. The file is the owner's |
| `not a git repository with a commit` | `survey` on a repository with no commit (`bin/charter-pkg:498`) | A first commit, then survey |
| `--out must be outside the project` | `survey --out` inside the project (`bin/charter-pkg:502`) | Pick a directory outside it |
| A scope, size, done, decision or perimeter refusal after the install | The gates doing their job on real work | Follow the override in the message; `docs/gates.md` has each gate's override |
| `charter check` printing one error line and passing | A gate crashed; gates fail open on their own errors, though not on a config they cannot read (`docs/gates.md` § Git hook) | Report it with `python3 .charter/bin/charter log`; it is a charter bug |

## Not part of a project install

The personal layer (the `CharterAdmin` skill and the `charter-personal.py` SessionStart hook) is installed once per machine into `~/.claude`, not into projects: `personal/README.md`. Changing the method itself happens in this repository: `AGENTS.md` at its root.
