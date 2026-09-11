Git hooks for the charter gates. Activate once per clone:

    git config core.hooksPath .charter/githooks

Worktrees share the repository config, so one setting covers them. A clone that
skips this step is still gated by CI (`.github/workflows/charter.yml`).
