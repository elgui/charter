<!-- charter-section:begin -->
## Charter method

This repository runs under the charter method. Rules for every agent, whichever harness runs it: `.claude/rules/charter.md`. Scope, decisions and change requests: `charter/`. Units of work: `.taskets/`. The gates run in git hooks (activate once per clone with `python3 .charter/bin/charter setup`) and in CI (`.github/workflows/charter.yml`), so they hold for commits from Codex, pi or any other agent. The scope, the config, the tooling and the approval fields are the owner's: propose changes to them, do not make them. Claude Code additionally runs them as session hooks from `.claude/settings.json`.
<!-- charter-section:end -->
