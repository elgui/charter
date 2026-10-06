# An upgrade reads charter's own hook, set by absolute path, as another project hook

- Seen: 2026-10-05, hermes-custom at dc23699 (worktree on `charter-0.4.9`), charter 0.4.6 -> 0.4.9
- Status: open

## What happened

hermes-custom's `core.hooksPath` is the absolute `/Users/gui/dev/hermes-custom/.charter/githooks` (`$ git -C ~/dev/hermes-custom config --show-origin --get core.hooksPath` -> `file:.git/config	/Users/gui/dev/hermes-custom/.charter/githooks`). The directory is charter's own. `charter-pkg upgrade`, run in a linked worktree, printed:

```
KEEP git hooks: /Users/gui/dev/hermes-custom-charter-0.4.9 runs /Users/gui/dev/hermes-custom/.charter/githooks/pre-commit; pointing core.hooksPath at .charter/githooks would stop them. Add `python3 -B .charter/bin/charter check --staged` to their pre-commit (.charter/githooks/README.md), or re-run with --replace-hooks to stop them.
```

(`$ python3 ~/dev/charter/bin/charter-pkg upgrade ~/dev/hermes-custom-charter-0.4.9`.)

The hook it calls "theirs" is charter's pre-commit. It already runs `$ROOT/.charter/bin/charter check --staged`, which resolves to the committing checkout. Expected: the upgrade sees charter's gate as wired, and prints nothing or `core.hooksPath left ...`. The advice to add the command to "their" pre-commit is wrong here. `--replace-hooks` would be harmless, but the message makes it sound risky.

## Reproduce

In a charter project, `git config core.hooksPath "$PWD/.charter/githooks"` (absolute), then `git worktree add ../wt -b x` and `python3 <charter>/bin/charter-pkg upgrade ../wt --dry-run`.

## Where

`bin/charter-pkg:286-296`: `cur_path == charter_lib.CHARTER_HOOKS_PATH` compares the configured path with the relative `.charter/githooks`, so an absolute path to charter's own directory falls through to `other_hooks` (inference: `other_hooks` and `hook_wired_by` in `package/.charter/lib.py` not read).

## Workaround

None needed: nothing is changed, and commits in the worktree run the worktree's charter through `$ROOT`.

## Suggested fix

Treat a `core.hooksPath` that resolves to `<toplevel or main worktree>/.charter/githooks` as charter's own.
