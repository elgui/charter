Git hooks for the charter gates. Activate once per clone:

    python3 .charter/bin/charter setup

It runs `git config core.hooksPath .charter/githooks`. Repository config is not cloned,
so every clone needs it once; worktrees of a clone share it. The installer does the same
on every run, and the Claude Code SessionStart hook says when it is missing. A clone
that skips this step is still gated by CI (`.github/workflows/charter.yml`).
