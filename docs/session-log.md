# Session log — fable/method-2026-09-11

Brief: `docs/briefs/2026-09-11-fable-method.md`. Model: claude-fable-5-1, effort high, Claude Code 2.1.268, one continuous interactive session with a `/goal` stop hook. Started 2026-09-11 14:09 UTC (server clock).

A fresh context resumes from here: the checklist says what exists, "Open" says what is left, the ledger says what it cost.

## Deliverable checklist

- [x] Map (6 lanes, scratch files in the session scratchpad; findings cited in `docs/report-2026-09-11.md` § The map and its evidence index)
- [x] Design: `docs/method.md` (artifacts and owners, rules table, hard gates, accepted results, synthesis, two tracks, cost, seams)
- [x] Package, committed layer: `package/` (.charter tooling and hooks, .claude settings, rules, three skills, one agent, CI workflow, git hook, templates, AGENTS.md section, .gitignore fragment)
- [x] Package, personal layer: `personal/` (hook, CharterAdmin skill, settings fragments, README with two install options); not installed
- [x] Versioning and setup: `bin/charter-pkg` install (idempotent, dry run), upgrade (diff first, keeps local edits), uninstall, status; manifest with hashes
- [x] Tests: `tests/test_gates.py`, `tests/test_installer.py`, 36 tests; 15 fail with the gates neutered
- [x] Documentation: `docs/method.md`, rules table (in method and report), `docs/gates.md`, `docs/package.md`, `docs/migration.md` with orqueveaux
- [x] Trial: `docs/trials/2026-09-11.md` and `docs/trials/2026-09-11/*.summary.json`; install, re-install, upgrade, downgrade, uninstall, reinstall; 13 Sonnet sessions; worktree; personal layer via `--settings`; git hooks and CI commands directly; orqueveaux clone
- [x] Try to break it: `docs/report-2026-09-11.md` § What would falsify the method
- [x] Independent reviewer: Codex CLI refused (refresh token revoked); a fresh-context Opus subagent ran the same prompt (`docs/review/prompt-2026-09-11.md`); findings in the report § Reviewer findings
- [x] Report `docs/report-2026-09-11.md` passes `charter anchors` (see Verified)
- [x] Decisions for the owner: report § Decisions for you, nine topic-named entries
- [x] Session ledger: below and in the report
- [x] Final message

## Decisions made (and why)

- `git init -b main`, brief committed alone on `main` (743bb96), branch `fable/method-2026-09-11`. Per brief.
- Python 3 stdlib only for hooks, CLI, installer; tests with `unittest`: a clean clone or CI runner has python3, not necessarily jq, pyyaml or pytest.
- Committed layer as plain tracked files wired from `.claude/settings.json`, not a plugin: repo-declared plugins need the trust dialog and are ignored in `-p` runs (settings reference § extraKnownMarketplaces), and plugin state lives in `~/.claude/plugins`.
- Package and directory name `charter`; repository name left as `methodo` with a rename proposed (decision `package-name`).
- Unit of work = tasket with four optional keys (`scope`, `perimeter`, `decisions`, `kind`) and three body sections (Acceptance, Evidence, Log); no separate ISA file. Both engines round-trip unknown keys (lane 1).
- Five hard gates (done-needs-evidence, scope, decisions in their retired-citation and failing-check forms, size, anchors in CI); everything else warns and logs.
- Scope gate judges changed paths (staged, or `--base`..HEAD in CI); pre-existing out-of-scope files are "legacy" warnings. Found on the first smoke test.
- Anchors run in CI on syntheses, reports and the PR body only; decisions and the scope are normative. Found in the trial (C4).
- `AGENTS.md` section markers renamed `charter-section:` after they collided with `charter:<id>` markers.
- Hooks run `python3 -B` and set `sys.dont_write_bytecode` after the trial showed `__pycache__` in the tree.
- Trial test bed: synthetic project (cheapest); orqueveaux clone only for the installer and read-only checks.
- Trial permission mode: `acceptEdits` plus a local allow-list plus `--permission-prompts none`.
- Reviewer: Codex unavailable (auth), Opus subagent with the same read-only prompt instead; recorded as a substitution, not as the brief's preferred cross-harness review.
- All six lanes and all trial sessions on Sonnet; the reviewer on Opus; design, code and judgment here.

## Built

`package/` (0.1.0), `bin/charter-pkg`, `bin/make-testbed`, `bin/trial-run`, `personal/`, `tests/`, `docs/method.md`, `docs/gates.md`, `docs/package.md`, `docs/migration.md`, `docs/trials/2026-09-11.md`, `docs/report-2026-09-11.md`, `docs/review/prompt-2026-09-11.md`, `README.md`.

## Verified

- `claude --help` (2.1.268) lists `--setting-sources <user,project,local>`, `--settings <file-or-json>`, `--permission-mode` choices acceptEdits|auto|bypassPermissions|manual|dontAsk|plan, `--permission-prompts host|none`, `--max-budget-usd`, `--max-turns`, `--effort low..max`, `-w/--worktree`, `--output-format stream-json`, `--include-hook-events`.
- Video transcript read in full (26,957 bytes, `/home/gui/Projects/tcv2/video_metodo.txt`); extra figures beyond the brief: most-disputed file touched by 1,173 agents with about 8,000 conflicts before, 47 after; 80% of tests passed; four configurations from $1,300 to $10,500 (all "reported in the video").
- Primary sources fetched by me with curl: cursor.com/blog/agent-swarm-model-economics contains "more than 70,000 conflicts", "compile-checked reference back to its doc", "neutral third-party agent", "flag bloated files", "outside its scope and leave a comment", "Field Guide ... index.md is automatically injected"; anthropic.com/research/multiagent-systems contains "21 vulnerabilities over a 6.5 million token run ... 266 vulnerabilities over a 27 million token run" and "these prompts did not make much difference".
- Hooks reference (code.claude.com/docs/en/hooks.md, 3,802 lines, fetched 2026-09-11): `-p` sessions treat the folder as trusted; exit 2 blocks on PreToolUse/UserPromptSubmit/Stop/SubagentStop/TaskCompleted/PostToolBatch; PostToolUse exit 2 only shows stderr; Stop overridden after 8 consecutive blocks, receives `stop_hook_active`; `${CLAUDE_PROJECT_DIR}` stays put in worktrees while `cwd` follows; file tool `file_path` always absolute; hook stdout capped at 10,000 chars.
- Plugins: `extraKnownMarketplaces`/`enabledPlugins` honoured only after trust and ignored in `-p` runs in untrusted folders (settings-reference.md § extraKnownMarketplaces).
- Permission modes: acceptEdits auto-approves edits and common fs commands; `--permission-prompts none` denies anything that would prompt.
- Runtimes: python3 3.11.2, jq 1.6, node 24, bun 1.3.8, git 2.39.5; pytest absent from PATH; codex-cli 0.152.0; pi 0.82.1.
- `~/Projects/tele-claude/services/project_tasket_reader.py:23-43,196-248,315-327` re-read: allowlist and `filter_by_group` as lane 1 said.
- Transcript usage entries repeat per content block (39 duplicate message ids in 80 entries of this session's transcript at 14:30); `session_end.py` deduplicates by (message id, request id).
- Tests: 36 OK at every commit since ba860ea; mutation run (all check functions emptied) → 15 failures, restored → OK.
- Trial: all gates fired where designed; details in `docs/trials/2026-09-11.md`.
- Test bed after install: `git config core.hooksPath` → `.charter/githooks`; inside a linked worktree the same value resolves and the hook refuses (G7).
- Report anchoring: `python3 package/.charter/bin/charter --root . anchors docs/report-2026-09-11.md` → ok, 86 claims, 81 anchored, 5 admitted unverified, 0 unanchored, 0 unresolved (at 14:59 UTC).
- orqueveaux clone install: 31 changes, `check --all` 0 blocking, 11 files over size limits, `synth` passes its own check.
- Codex: `codex exec` exits 1 with "Your access token could not be refreshed because your refresh token was revoked" (scratchpad `review/codex.log`).

## Open

- Nothing blocking. Follow-ups deliberately left undone are listed in the report.

## Session ledger

| When (UTC) | What | Model / effort | Cost or tokens | Outcome |
|---|---|---|---|---|
| 14:09 | Session start; repo initialised; brief on `main` (743bb96); branch created | fable-5-1 / high | in the session total | accepted |
| 14:12 | Lanes 1-6 dispatched in parallel (read-only, scratch files) | sonnet subagents | lane 1: 205,355 tokens, 48 tool uses, 405 s; lane 2: 154,741, 46, 348 s; lane 3: 119,927, 34, 334 s; lane 4: 216,704, 48, 405 s; lane 5: 74,578, 15, 155 s; lane 6: 104,540, 27, 295 s (harness-reported) | all accepted after spot checks; lane 4's plugin claim reconciled with the settings reference |
| 14:16 | Lane 5 returned; both primary URLs re-checked by me | fable | — | accepted |
| 14:16-14:25 | Docs read: hooks, settings, permissions, headless, plugins | fable | — | — |
| 14:25-14:35 | `docs/method.md`, package, smoke test, three defects fixed | fable | — | — |
| 14:36 | Tests (36) written; mutation run 15 failures | fable | — | accepted |
| 14:38-14:44 | Trial: 13 Sonnet sessions | sonnet / low | 1.04 USD reported total; per run in the trial record; five overwritten early runs 0.035-0.044 each (from run output) | rework: T1 rerun four times, T6 once |
| 14:44 | Git hooks, CI commands, installer, orqueveaux clone exercised directly | fable | — | accepted; wording and workflow scope fixed |
| 14:45-14:55 | Trial record, gates, package, migration, report written | fable | — | — |
| 14:56 | Codex review attempted | codex-cli 0.152.0 / gpt-5.6-terra | 0 (auth failure) | not run |
| 14:57-15:00 | Opus reviewer, same prompt, read-only | opus subagent | 67,963 tokens, 21 tool uses, 148 s | 12/12 confirmed; D0 nuance folded into the report; conftest literals flagged as a live finding |
| 15:00 | Session total (start 14:09, end about 15:01, no interruption) | fable-5-1 / high | transcript usage deduplicated by message id at 14:59: 2,638 input, 202,095 output, 25,187,821 cache-read, 462,579 cache-write tokens over 88 API turns; subscription session, no dollar figure reported | all deliverables accepted; the ledger's own entry is the first data point of R11 |
