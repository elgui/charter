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

- Hook scripts and installer in Python 3 stdlib only, tests via `python3 -m unittest`: a clean clone or CI runner has python3 but not necessarily jq/pyyaml/pytest.
- Committed layer as plain files in the repo wired from `.claude/settings.json`, not a plugin (see Verified: plugins need trust and live outside the repo).
- All six lanes dispatched as Sonnet subagents (scan-and-summarise work; judgment stays here).

- `git init -b main`, brief committed alone on `main` (743bb96), branch `fable/method-2026-09-11` created. Per brief § The package.

## Built

(nothing yet)

## Verified

- Video transcript read in full (26,957 bytes, `/home/gui/Projects/tcv2/video_metodo.txt`); doctrine matches the brief's summary; extra figures: most-disputed file touched by 1,173 agents / ~8,000 conflicts before, 47 after; 80% of tests passed; four configurations cost $1,300 to $10,500 (all "reported in the video").
- Primary sources checked by me with curl (not only by lane 5): cursor.com/blog/agent-swarm-model-economics contains "more than 70,000 conflicts", "compile-checked reference back to its doc", "neutral third-party agent", "flag bloated files", "outside its scope and leave a comment", "Field Guide ... index.md is automatically injected"; anthropic.com/research/multiagent-systems contains "21 vulnerabilities over a 6.5 million token run ... 266 vulnerabilities over a 27 million token run" and "these prompts did not make much difference".
- Hooks reference (code.claude.com/docs/en/hooks.md, fetched 2026-09-11): `-p` sessions treat the folder as trusted so committed `.claude/settings.json` hooks run; exit 2 blocks on PreToolUse/UserPromptSubmit/Stop/SubagentStop/TaskCompleted/PostToolBatch; PostToolUse exit 2 only shows stderr to Claude (warning channel); Stop hooks are overridden after 8 consecutive blocks and receive `stop_hook_active`; `${CLAUDE_PROJECT_DIR}` stays at the session's start dir when Claude enters a worktree, `cwd` follows; file tool `file_path` is always absolute; hook stdout capped at 10,000 chars.
- Plugins: `extraKnownMarketplaces`/`enabledPlugins` in a repo's `.claude/settings.json` are honoured only after the trust dialog and "in a folder you haven't trusted, including a `-p` run there, it ignores them" (settings-reference.md § extraKnownMarketplaces); plugin state lives in `~/.claude/plugins`. So a plugin cannot be the vehicle for the committed layer; it is a candidate only for the personal layer.
- Permission modes (permission-modes.md): acceptEdits auto-approves edits and common fs commands; `--permission-prompts none` denies anything that would prompt; dontAsk denies all not in allow rules.
- Runtimes on this box: python3 3.11.2, jq 1.6, node 24, bun 1.3.8, git 2.39.5; pytest not on PATH. Package scripts will use python3 stdlib only (no pyyaml, no pytest).

- `claude --help` (2.1.268) lists `--setting-sources <user,project,local>`, `--settings <file-or-json>`, `--permission-mode` choices acceptEdits|auto|bypassPermissions|manual|dontAsk|plan, `--permission-prompts host|none`, `--max-budget-usd`, `--effort low..max`, `-w/--worktree`, `--output-format stream-json`.

## Open

## Session ledger

| When (UTC) | What | Model / effort | Cost | Outcome |
|---|---|---|---|---|
| 14:09 | Session start | fable-5-1 / high | — | — |
| 14:12 | Lanes 1-6 dispatched in parallel (read-only, scratch files) | sonnet (subagents) | see below | — |
| 14:16 | Lane 5 returned (primary sources) | sonnet | 74,578 tokens, 15 tool uses, 155 s | accepted after I re-checked both primary URLs |
