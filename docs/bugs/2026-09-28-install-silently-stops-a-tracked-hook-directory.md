# The install silently stops a project's hooks kept in a tracked directory such as `.githooks/`

- Seen: 2026-09-28, claude-plugins at b0b3de8, charter 0.4.6
- Status: open

## What happened

claude-plugins keeps its pre-commit hook in the tracked file `.githooks/pre-commit` (refuse a plugin change whose version was not bumped, then run the plugin's tests). Its README activates it once per clone with `git config core.hooksPath .githooks`. The survey reported nothing to keep:

```
$ charter-pkg survey /Users/gui/dev/claude-plugins --track prototype --out <dir>
| Hooks the charter hook path would stop | none | `$ ls /Users/gui/dev/claude-plugins/.charter/githooks` |
| Framework file already running the charter gate | none | `$ git grep -n 'charter check --staged'` |
```

and the install set `core.hooksPath .charter/githooks`, after which `.githooks/pre-commit` never ran again. Nothing in the survey, the plan or the install output named it. Expected: a `KEEP git hooks` line naming `.githooks/pre-commit`, as for lefthook, pre-commit or husky.

## Reproduce

```
git init p && cd p && mkdir .githooks && printf '#!/bin/sh\nexit 0\n' > .githooks/pre-commit && chmod +x .githooks/pre-commit
git add . && git commit -m init          # a clone where core.hooksPath is not set yet, as any fresh clone
charter-pkg survey . --track prototype   # "Hooks the charter hook path would stop: none"
```

## Where

- `package/.charter/lib.py:619-640` (`other_hooks`): looks in the clone's current hook directory and at `HOOK_FRAMEWORK_FILES` (`lib.py:611`), which lists lefthook, pre-commit and husky files only. A tracked hook directory is invisible when the clone has not activated it yet, which is every fresh clone, and the survey reads a fresh rehearsal clone.
- `package/.charter/lib.py:643-649` (`hook_wired_by`): the same list, so a `.githooks/pre-commit` that runs the gate is not recognised either.
- `bin/charter_plan.py:135`: the survey row reports `other_hooks` only.

## Workaround

claude-plugins moved the hook to `scripts/check-plugins.sh`, run by decision `plugin-version-bumped` (`check: sh scripts/check-plugins.sh`), and deleted `.githooks/`.

## Suggested fix

Treat any tracked directory holding executable git hook names (`pre-commit`, `commit-msg`, `pre-push`…), or one named in the README as a `core.hooksPath`, as a hook framework: report it as KEEP in the survey and the install, and let `hook_wired_by` recognise the gate command inside it.
