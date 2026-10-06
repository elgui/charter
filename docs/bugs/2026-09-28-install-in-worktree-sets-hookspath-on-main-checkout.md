# An install into a linked worktree sets core.hooksPath for the main checkout too

- Seen: 2026-09-28, claude-plugins at b0b3de8, charter 0.4.6
- Status: open

## What happened

Following Migrate phase 5, the install ran in a linked worktree on `charter/install`:

```
$ git -C ~/dev/claude-plugins worktree add -b charter/install <scratchpad>/claude-plugins-install origin/main
$ python3 ~/dev/charter/bin/charter-pkg install <scratchpad>/claude-plugins-install --track prototype
...
git config core.hooksPath .charter/githooks (was unset)
```

The setting landed in the repository's shared config, so it also applies to the main checkout, which is still on `main` and has no `.charter/`:

```
$ git -C ~/dev/claude-plugins config --show-origin --get core.hooksPath
file:.git/config	.charter/githooks
```

Migrate.md step 1 says the worktree exists "so the checkout, and anyone's uncommitted work in it, is never touched". The checkout's hook configuration is touched. In claude-plugins this was harmless because the survey found no hooks installed. In a project whose `.git/hooks` holds active hooks (the survey's "Hooks installed in this clone" row), the main checkout would silently stop running them until the branch merges, because a relative hooksPath that doesn't exist runs nothing.

## Reproduce

1. Take a repo with a `.git/hooks/pre-commit` and no charter.
2. `git worktree add -b charter/install ../wt origin/main && charter-pkg install ../wt --track prototype`
3. In the main checkout, `git commit`: the old pre-commit hook no longer runs.

## Where

- `bin/charter-pkg:280-282`: `git -C <project> config core.hooksPath .charter/githooks`, which writes to the common config when `<project>` is a linked worktree.
- The KEEP guard at `bin/charter-pkg:276` judges the hooks at install time but doesn't consider the other worktrees sharing the config (inference: not traced further).

## Workaround

None needed in claude-plugins: it had no hooks, and after the merge the main checkout needs this exact setting anyway.

## Suggested fix

When the target is a linked worktree (`git rev-parse --git-dir` ≠ `--git-common-dir`), either write the setting with `git config --worktree` (which needs `extensions.worktreeConfig`) or skip it and print that the owner runs `charter setup` after the merge. Or Migrate.md could state the side effect and have the survey's hooks row gate it.
