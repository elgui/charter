# Installing charter on a project

The one procedure for an agent asked to install, set up, upgrade or remove charter on a project. Other documents point here rather than repeat it. The outputs quoted below come from a rehearsal of charter 0.4.1 on a scratch repository on 2026-09-24 (in the scratchpad); the counts and paths vary with the project, and the version in each line is the one in `package/VERSION`.

Conventions used throughout:

```
M=~/Projects/charter/bin/charter-pkg      # the installer, run from the charter checkout
P=/absolute/path/to/the/project
```

## Rules for the agent

1. **Owner-only files are committed by the owner.** In an installed project these paths are the owner's: `.charter/**`, `charter/config.json`, `charter/scope.md`, `charter/rails.md`, `.claude/settings.json`, `.claude/settings.local.json` and `.github/workflows/charter.yml` (the full list, fields included, is in `package/.claude/rules/charter.md` § What only the owner changes). The pre-commit gate refuses a commit of them made from inside Claude Code (`docs/gates.md` § Owner-only changes). An install and an upgrade always touch them, so **you prepare and stage; the owner commits** (step 8).
2. **Never set `CHARTER_OWNER`, never pass `--no-verify`**, and never work around a refusal by writing the file through Bash. The refusal is the method working, not a fault (`package/.claude/rules/charter.md:36`). The one exception is a throwaway rehearsal clone that the survey made (`--keep-clone`), which is not the project.
3. **Never push, open or merge a pull request, or deploy.** Those are the owner's acts (`package/.claude/rules/charter.md` § Decisions and memory, "Commitments").
4. **Facts about an existing project come from the survey** (step 1), measured today, never from memory or another session's notes (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md:14`).
5. **Stop and report** any check that fails.

## Step 0: preconditions

| Check | Command | Expected | If not |
|---|---|---|---|
| The project is a git repository with a commit | `git -C $P rev-parse --verify HEAD` | a commit SHA | A new project: `git init`, a first commit, then continue (`bin/charter-pkg:368` refuses a survey without one) |
| The working tree is clean | `git -C $P status --porcelain` | no output | Stop. List the files to the owner. Do not stash, commit or discard someone else's work. `install` does not check this itself (`do_install` in `bin/charter-pkg`), so this step is the only guard |
| No other session works in the tree | `tmux list-panes -a -F '#{pane_current_path}' \| grep -F "$P"` | no output (`no server running` also means none) | Stop and tell the owner, or work in a separate worktree (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md:76`) |
| The charter checkout is the version you mean to install | `cat ~/Projects/charter/package/VERSION; git -C ~/Projects/charter status --short` | the version; no output | Ask the owner which version to install |
| Whether charter is already there | `python3 $M status $P` | `package version: X; installed: none` (`bin/charter-pkg:349`) | `installed: <version>`: go to [Upgrade](#upgrade) instead |

## Step 1: choose the path

- **A new project** (a first commit and little else): step 2.
- **A project that already has code, taskets or documents**: survey it first. The survey reads the project without writing to it and rehearses the install in a throwaway clone (`docs/design/migration-workflow.md`):

  ```
  python3 $M survey $P --out <a directory outside the project>
  ```

  Expected: `wrote <dir>/survey.json, survey.md, plan.md`, exit 0. Read `survey.md` and `plan.md` in full. The plan's steps, each with its check and rollback, take the place of steps 3 to 7 below for this project; steps 0, 8 and 9 and the rules above still apply. With the personal layer installed, the `Migrate` workflow of the `CharterAdmin` skill drives the whole survey, rehearsal and execution (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md`). What comes after the install for each kind of project (taskets, BMAD, ad-hoc documents) is in `docs/migration.md`.

  Survey exit codes: 2 for a directory that is not a git repository with a commit, an `--out` inside the project or an unknown `--ref`; 3 when a line of its own report fails the anchoring check, which is a bug in `bin/charter_plan.py` to fix with a test, never by editing the output.

## Step 2: choose the track

- **`client`** only when a signed devis or contract covers the project (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md:38`). The scope gate is on and `charter/scope.md` is required.
- **`prototype`** otherwise. No scope file; the decisions, size and done gates stay hard (`docs/method.md:188-202`).

The full comparison is `docs/method.md` § Two tracks. Always pass `--track`: without it the installer seeds the package default, which is `client` (`package/charter/config.json`). A prototype that gains a client switches later, when the owner writes `charter/scope.md` and sets `track` to `client`.

## Step 3: branch

```
git -C $P switch -c charter/install
```

Never on the main line.

## Step 4: dry run

```
python3 $M install $P --track <track> --dry-run
```

Expected: one `would create`, `would seed`, `would merge hooks into` or `would update` line per path, then `dry run: <n> change(s); charter <version>` (`bin/charter-pkg:252`; 35 on a repository with no charter files, in the scratchpad rehearsal). `git -C $P status --porcelain` still prints nothing. Read the output for these lines:

| Line | Meaning | What to do |
|---|---|---|
| `KEEP git hooks: <project> runs <framework>; pointing core.hooksPath at .charter/githooks would stop them. ...` | The project runs lefthook, pre-commit, husky or its own `.git/hooks` scripts (`bin/charter-pkg:232`) | Continue; step 6 wires the gate into that framework |
| `IGNORED by <file> (<pattern>), so a commit will not carry it: <path>` | The project's `.gitignore` matches a path the installer writes, often `.claude/settings.json` (`bin/charter-pkg:248`; `docs/design/migration-workflow.md:24`) | Ask the owner: stop ignoring it so the commit carries it, or keep it local and accept that other clones have no session hooks |
| `would seed (<n> legacy tasket(s)) .../charter/legacy-taskets.txt` | Taskets without an acceptance section; they may still close, with a warning (`bin/charter-pkg:179`) | Nothing now; triage is in `docs/migration.md` Path C |

## Step 5: install

```
python3 $M install $P --track <track>
```

Expected: the same lines without `would`, then `<n> change(s); charter <version>`, and, unless hooks were kept, `git config core.hooksPath .charter/githooks (was unset)` (`bin/charter-pkg:236`). Then:

- `python3 $M install $P --track <track>` again prints `charter <version> already installed in <project>; nothing to do` (`bin/charter-pkg:250`). The install is idempotent.
- `git -C $P config core.hooksPath` prints `.charter/githooks`, unless hooks were kept (`bin/charter-pkg:236`).

## Step 6: a project that already runs git hooks

Skip this step unless step 4 printed `KEEP git hooks`. `core.hooksPath` replaces a clone's whole hook directory, so the installer leaves it alone and the gate runs from the existing framework instead (`package/.charter/githooks/README.md`). Add the gate to the framework's pre-commit. For lefthook, in `lefthook.yml`:

```
pre-commit:
  commands:
    charter:
      run: python3 -B .charter/bin/charter check --staged
```

The snippets for pre-commit and husky are in `package/.charter/githooks/README.md`. Check: `cd $P && python3 .charter/bin/charter setup` prints `git hook: lefthook.yml runs the charter gate; core.hooksPath left unset`. `--replace-hooks` would stop the project's other hooks: use it only on the owner's explicit word.

## Step 7: stage by name

Stage what the installer wrote, by name, never with `git add -A`, which could take untracked files that are not yours (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md:17`). On a new project:

```
cd $P && git add .charter charter .taskets AGENTS.md .gitignore .github/workflows/charter.yml \
  .claude/settings.json .claude/rules/charter.md .claude/agents/charter-reviewer.md \
  .claude/skills/charter-unit .claude/skills/charter-decision .claude/skills/charter-progress
```

Add the framework file from step 6 if you changed one. On an existing project, use the `git add` list in the survey's `plan.md` (`docs/design/migration-workflow.md:63`).

Check: `git -C $P status --porcelain` shows no `??` line under those paths (34 staged files on a repository with no charter files, in the scratchpad rehearsal: `$ git -C $P diff --cached --name-only | wc -l`).

If a draft of `charter/scope.md` is wanted on the client track, write it outside the project (a scratchpad) from `charter/templates/scope.md` and hand it to the owner with the commit. The scope is the owner's file (`package/.claude/rules/charter.md:32`).

## Step 8: the owner commits

Owner's step. Stop and hand over:

- the branch and the staged file list;
- the `owner` value to put in `charter/config.json`: the git author name or email the owner commits under (`git -C $P config user.name`, `git -C $P config user.email`), or a list of them. CI refuses owner-only changes from any other author once it is set, and warns while it is empty (`check_owner_commits` in `package/.charter/checks.py`). The install commit is the one place CI reads it from the change under review, so it belongs in this commit: the owner edits the file, then `git add charter/config.json`;
- on the client track, the scope draft;
- the command for the owner to run:

  ```
  cd <project> && git commit -m "charter <version>"                     # from the owner's own terminal
  cd <project> && CHARTER_OWNER=1 git commit -m "charter <version>"     # from a terminal inside Claude Code or its IDE extension
  ```

  In a Claude Code prompt, the owner can type the second form after a `!`: shell mode runs the command directly, without going through Claude, and adds its output to the session (https://code.claude.com/docs/en/interactive-mode#shell-mode-with-prefix).

Expected for the owner: `charter/protected warn [...]` lines, one per owner-only file, then `charter check: 0 blocking, <n> warning(s) [staged, track <track>]`: outside Claude Code the protected check warns (`package/.charter/checks.py:749`).

If you run `git commit` yourself, the gate refuses it: one `charter/protected block [<path>]` line per owner-only file, then `charter check: 16 blocking, 1 warning(s)` and `Refused.` on a new project (`package/.charter/bin/charter:55-57`, in the scratchpad rehearsal). That is the expected outcome, not a fault; leave the files staged and hand over.

## Step 9: verify

After the owner's commit:

| Check | Command (from `$P`) | Expected |
|---|---|---|
| Every gate on the tree | `python3 .charter/bin/charter check --all` | `charter check: 0 blocking, ...`. A warning `charter/config.json names no owner` means `owner` is still empty (`package/.charter/checks.py:803`) |
| The installed version | `python3 .charter/bin/charter version` | the target version, as in `package/VERSION` |
| The files match the package | `python3 $M status $P` | `installed: <version>`, `locally modified: 0; missing: 0; differ from package: 0`, and `git core.hooksPath: .charter/githooks` (or `unset` where a framework runs the gate; `bin/charter-pkg:349-360`) |
| The session hooks run | start a new Claude Code session in `$P`, then `python3 .charter/bin/charter log` | the banner prints the version and track; the log has entries. A wrong hook path shows only as a non-blocking error on first run (`docs/gates.md` § Claude Code hooks) |
| The gate runs in a fresh clone | `git clone $P <scratch dir>/clone && cd <scratch dir>/clone && python3 .charter/bin/charter check --all --strict` | `0 blocking` (`docs/migration.md` § What to check after a migration) |

The owner's side of a migration (branch protection, telling collaborators, the tele-claude dashboard) is listed in `docs/migration.md` § What to check after a migration.

Report: the branch, the commit SHA, and the output of each check. Stop before the pull request: the owner pushes, opens it and merges it, with a merge commit (`docs/migration.md` Path A, step 5, says why).

## Every other clone: `setup`

Git does not clone repository config, so each clone activates the git hook once; its worktrees share it (`package/.charter/githooks/README.md:5-6`):

```
cd <clone> && python3 .charter/bin/charter setup
```

Expected, one of:

- `git config core.hooksPath .charter/githooks (was unset); worktrees of this clone share it` (`package/.charter/bin/charter:626`)
- `git hook already active (core.hooksPath = .charter/githooks)` (`package/.charter/bin/charter:617`)
- `git hook: <framework file> runs the charter gate; core.hooksPath left unset`: the framework's own install puts the gate in this clone (`package/.charter/bin/charter:619`).
- `KEEP git hooks: this clone runs <framework>; ...`: the project runs other hooks and the gate is not wired into them yet. Tell the owner (step 6); do not re-run with `--replace-hooks` (`package/.charter/bin/charter:621`).

`setup` needs no charter checkout. A clone that skips it is still gated by CI. The SessionStart banner says when the hook is missing (`package/.charter/githooks/README.md`).

## Upgrade

A new package version reaches a project only by an upgrade; nothing pulls it. The personal-layer SessionStart hook says `package X available, Y installed` when a project is behind (`personal/claude-home/hooks/charter-personal.py`).

1. Step 0 again.
2. `git -C $P switch -c charter-<version>`.
3. Read the upgrade notes in `docs/package.md` § Versioning and upgrade for every version between the installed one and the target. Some ask for a step after the upgrade.
4. `python3 $M upgrade $P --dry-run`. Expected: `upgrade <installed> -> <version> in <project>`, a unified diff for each owned file that would change, then `dry run: <n> change(s); charter <version>` (`bin/charter-pkg:136-155`). `nothing installed in <project>; use install` means there is nothing to upgrade (`bin/charter-pkg:133`).
5. `python3 $M upgrade $P`. A line `KEEP (locally modified, use --force to overwrite) <path>` means the project changed a package file. Show the owner the difference; `--force` replaces it, on the owner's word only. `upgrade` never rewrites `charter/config.json`, so new config keys take the package defaults (`docs/package.md` § Versioning and upgrade).
6. Stage the changed and new files by name (`git -C $P status --porcelain` lists them), then hand over as in step 8, with the message `charter <version>`.
7. Step 9, and the note's checks.

Rollback: `git revert` of the upgrade commit; `charter/VERSION` and the manifest revert with it (`docs/migration.md` § A new package version reaching a project).

## Uninstall

```
python3 $M uninstall $P --dry-run
python3 $M uninstall $P
```

It removes the owned files whose hash matches the manifest, the hook entries, the `AGENTS.md` section, the `.gitignore` line and `core.hooksPath`. It keeps the project's own files (`charter/scope.md`, decisions, changes, `charter/config.json`, the legacy list, the ledger, `.taskets/`) and the gate log unless `--purge-state` (`bin/charter-pkg:257-344`). The removal touches owner-only paths, so the owner commits it (step 8). Right after an install, `git revert` of the install commit does the same.

## When a gate refuses

Every refusal names its override (`docs/method.md:119`). The common ones:

| Message | Cause | What the agent does |
|---|---|---|
| `charter/protected block [<path>]` at commit | An owner-only file committed from inside Claude Code (`package/.charter/checks.py:749`) | Leave it staged; hand over (step 8) |
| A `PreToolUse` denial on an Edit or Write of an owner-only file | The same rule, in session (`docs/gates.md:35`) | Propose instead: a change request (`charter/templates/change.md`), a successor decision, or a draft outside the project; say so in your final message |
| `KEEP git hooks: ...` | The project runs another hook framework (`bin/charter-pkg:232`) | Step 6 |
| `IGNORED by ...` | `.gitignore` matches a written path (`bin/charter-pkg:248`) | Ask the owner (step 4) |
| `KEEP (locally modified, use --force to overwrite) <path>` | A package file changed in the project (`bin/charter-pkg:152`) | Show the owner; `--force` only on their word |
| `nothing installed in <project>; use install` | `upgrade` on a project without charter (`bin/charter-pkg:133`) | Step 1 |
| `not a git repository with a commit` | `survey` on a repository with no commit (`bin/charter-pkg:368`) | A first commit, then survey |
| `--out must be outside the project` | `survey --out` inside the project (`bin/charter-pkg:372`) | Pick a directory outside it |
| A scope, size, done, decision or perimeter refusal after the install | The gates doing their job on real work | Follow the override in the message; `docs/gates.md` has each gate's override |
| `charter check` printing one error line and passing | A gate crashed; gates fail open on their own errors (`docs/gates.md:109`) | Report it with `python3 .charter/bin/charter log`; it is a charter bug |

## Not part of a project install

The personal layer (the `CharterAdmin` skill and the `charter-personal.py` SessionStart hook) is installed once per machine into `~/.claude`, not into projects: `personal/README.md`. Changing the method itself happens in this repository: `AGENTS.md` at its root.
