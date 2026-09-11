# Session log — fable/method-2026-09-11

Brief: `docs/briefs/2026-09-11-fable-method.md`. Model: claude-fable-5-1, effort high.
Started 2026-09-11 14:09 UTC (server clock; `date` output). Interactive session in Claude Code 2.1.268 with a `/goal` stop hook.

## Deliverable checklist

- [ ] Map (6 lanes) with evidence index
- [ ] Design: artifacts, rules table, hard gates, accepted results, progress synthesis, two tracks, cost, seams
- [ ] Package: committed layer (.claude/, hooks, git hooks, CI, AGENTS.md, templates)
- [ ] Package: personal layer (designed, not installed)
- [ ] Package: versioning, installer (idempotent, dry-run), upgrade with diff, uninstall
- [ ] Package: tests for hook scripts and installer (fail without the code)
- [ ] Documentation: method, rules table, hook/gate reference, migration guide (orqueveaux worked example)
- [ ] Trial on a scratch project: install / re-install / upgrade / uninstall; Sonnet headless sessions per gate; worktree run; personal-layer run; git hooks and CI exercised directly
- [ ] Trial record `docs/trials/2026-09-11.md` with costs
- [ ] Try to break it: falsification evidence per rule and gate
- [ ] Independent reviewer (Codex CLI) re-check of headline claims; unconfirmed claims flagged
- [ ] Report `docs/report-2026-09-11.md` passes the package's anchoring check
- [ ] Decisions for me (topic-named)
- [ ] Session ledger (log + report)
- [ ] Final message

## Decisions made (and why)

- `git init -b main`, brief committed alone on `main` (743bb96), branch `fable/method-2026-09-11` created. Per brief § The package.

## Built

(nothing yet)

## Verified

- `claude --help` (2.1.268) lists `--setting-sources <user,project,local>`, `--settings <file-or-json>`, `--permission-mode` choices acceptEdits|auto|bypassPermissions|manual|dontAsk|plan, `--permission-prompts host|none`, `--max-budget-usd`, `--effort low..max`, `-w/--worktree`, `--output-format stream-json`.

## Open

## Session ledger

| When (UTC) | What | Model / effort | Cost | Outcome |
|---|---|---|---|---|
| 14:09 | Session start | fable-5-1 / high | — | — |
