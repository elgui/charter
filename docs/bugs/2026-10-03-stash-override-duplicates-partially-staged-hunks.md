# The decisions gate's stash override duplicates a hunk that is both staged and in the working tree

- Seen: 2026-10-03, hermes-custom at 3646619 → f8d94ca, charter 0.4.6
- Status: open

## What happened

`python3 -B .charter/bin/charter check --staged` refused the commit:

    charter/decisions block: decision `check:` commands run in the working tree, which differs from the index for .taskets/20260928-0930-vault-unification.md, …, charter/decisions/INDEX.md; they would judge files this commit does not contain Override: stage everything, or `git stash --keep-index`, commit, `git stash pop`

The session followed the override: `git stash push --keep-index`, `git commit`, `git stash pop`. Both exited 0.
`ops/README.md` had a hunk staged on its own (via `git update-index --cacheinfo`) while the working tree also held
another unit's uncommitted hunk in the same file. After the pop, the staged hunk appeared **twice** in the
working tree: `grep -c "Why the 27B's write calls failed" ops/README.md` → `2`. The pop reported no conflict,
so the duplicate is silent.

The expected result: the working tree after the pop equals the one before the commit (one copy, now committed,
plus the other unit's hunk).

## Reproduce

In a clone with a tracked file `f`:

    printf 'a\n' > f; git add f; git commit -qm base
    printf 'a\nMINE\nTHEIRS\n' > f                 # two hunks in the tree
    printf 'a\nMINE\n' | git hash-object -w --stdin | xargs -I{} git update-index --cacheinfo 100644,{},f
    git stash push --keep-index -q && git commit -qm mine && git stash pop -q
    grep -c MINE f                                   # 2 is the bug (inference: --keep-index leaves MINE in the tree, and the pop re-applies it)

(inference: the reproduction is reasoned from git's documented `--keep-index` behaviour and was not run as written.)

## Where

`package/.charter/bin/charter:156` and `:182`, the `override=` text of the decisions block.

## Workaround

After the pop, diff the working tree against what it held before the commit and delete any duplicate. Here:
an identical 26-line block at `ops/README.md:283-308`, removed by hand.

## Seen again

2026-10-04, hermes-custom at 7d6ae13, same block on a commit of unit `20261004-1545-bonito-q8-switch`, while two other
live sessions had unstaged and untracked files in the clone. Here the override itself is the hazard: `git stash
--keep-index` takes those sessions' working-tree edits away until the pop. Workaround used, which is the
temporary-worktree direction below done by hand: `git worktree add --detach <tmp> HEAD`, `git diff --cached --binary |
git -C <tmp> apply --index`, commit in `<tmp>` (the hook ran there: `charter check: 0 blocking`), then
`git update-ref refs/heads/main <new> <old>` and `git worktree remove <tmp>`. Result: commit b802b7e, no other file touched.

## Suggested fix

Suggest `git stash push --keep-index --include-untracked` followed by `git checkout stash@{0} -- .` plus
`git stash drop` instead of `pop`, or have the gate run the `check:` commands in a temporary worktree of the
index (`git worktree add` / `git checkout-index --prefix`), so no stash is needed.
