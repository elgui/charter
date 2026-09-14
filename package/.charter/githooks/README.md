Git hooks for the charter gates. Activate once per clone:

    python3 .charter/bin/charter setup

It runs `git config core.hooksPath .charter/githooks`. Repository config is not cloned,
so every clone needs it once; worktrees of a clone share it. The installer does the same
on every run, and the Claude Code SessionStart hook says when it is missing. A clone
that skips this step is still gated by CI (`.github/workflows/charter.yml`).

## A project that already runs git hooks

`core.hooksPath` replaces the whole hook directory, so it stops every hook the clone ran
before: lefthook, pre-commit, husky, or scripts in `.git/hooks`. The installer and
`charter setup` therefore leave it alone when they find such hooks, and say so. Run the
gate from the existing framework instead; the SessionStart banner and `charter setup`
recognise a tracked framework file that contains `.charter/bin/charter check --staged`.

lefthook (`lefthook.yml`):

    pre-commit:
      commands:
        charter:
          run: python3 -B .charter/bin/charter check --staged

pre-commit (`.pre-commit-config.yaml`):

    - repo: local
      hooks:
        - id: charter
          name: charter gates
          entry: python3 -B .charter/bin/charter check --staged
          language: system
          pass_filenames: false
          always_run: true

husky (`.husky/pre-commit`):

    python3 -B .charter/bin/charter check --staged

`charter setup --replace-hooks` points `core.hooksPath` at `.charter/githooks` anyway and
stops the other hooks; only the owner decides that.
