# Hooks and gates reference

Every gate lives in `package/.charter/checks.py` and is called from three places: the Claude Code hooks in `package/.charter/hooks/`, the git hook `package/.charter/githooks/pre-commit` (through `charter check --staged`), and CI (`package/.github/workflows/charter.yml`, through `charter check --all --ci` and `charter anchors`). Every finding is appended to `.charter/state/log.jsonl` with its gate, level, path and the event that raised it; `charter log` summarises it.

Hook contract facts this design rests on (https://code.claude.com/docs/en/hooks, fetched 2026-09-11): `PreToolUse` denies through `hookSpecificOutput.permissionDecision: "deny"` and the reason reaches Claude; `PostToolUse` cannot block, but exit 2 puts stderr in front of Claude; `Stop` blocks with `decision: "block"` and receives `stop_hook_active`; Claude Code ends the turn after eight consecutive Stop blocks; `-p` runs treat the folder as trusted so committed project hooks run; `${CLAUDE_PROJECT_DIR}` stays at the session's start directory when Claude enters a worktree while `cwd` in the hook input follows it; hook stdout is capped at 10,000 characters.

## Claude Code hooks (`package/.claude/settings.json`)

| Event | Matcher | Script | What it checks | Can block | Timeout |
|---|---|---|---|---|---|
| `SessionStart` | all | `session_start.py` | Prints version, track, active unit with open criteria and last log line, active decisions with their `check:`, proposed decisions and changes, gate activity over 7 days | No (context only) | 20 s |
| `PreToolUse` | `Edit|Write` | `pre_tool_gate.py` | Scope (R6), size (R3), done-needs-evidence on `.taskets/*.md` (R9), decision markers (R1: retired citation blocks, missing marker warns). Computes the post-edit file content for Edit by applying `old_string`→`new_string` to the file on disk | Yes: deny with reason and override | 30 s |
| `PostToolUse` | `Edit|Write` | `post_tool_gate.py` | Perimeter without note (R4, warns), decision `check:` commands bound to the edited file (R1, exit 2 with stderr), records the session's edited paths in `.charter/state/session-<id>.json` | Exit 2 shows stderr; the edit has landed | 90 s |
| `Stop` | all | `stop_gate.py` | A final message that claims completion without any resolving anchor (R9/R10); an active unit at `done` that fails the done gate. Blocks once, then passes through when `stop_hook_active` is set. Adds a `systemMessage` when code was edited and the unit's file was not | Yes, once per turn | 30 s |
| `SessionEnd` | all | `session_end.py` | Sums token usage from the transcript (deduplicated by message id and request id) into `.charter/state/sessions.jsonl` (R11) | No | 10 s |

Every hook script wraps its body in a try/except that logs `gate=error` and allows; a hook that cannot run must not stop the tool. A hook path that is wrong in `settings.json` is reported by Claude Code as a non-blocking error on first run ("Failed with non-blocking status code"), so check `.charter/state/log.jsonl` has entries after the first session on a new clone.

## The gates

### Scope (R6): out-of-scope path without an approved change request

- Checks: an edited or staged path matches the `paths:` of an item under `## Out of scope` in `charter/scope.md` and no `charter/changes/*.md` with `status: approved` lists a glob covering it. Only on `track: client`.
- Blocks: `PreToolUse` deny; pre-commit; CI on the paths changed against `--base` (PR base SHA or the push's previous SHA). Files already out of scope before the change set are a warning ("legacy").
- Override: write the change request from `charter/templates/change.md`; the owner sets `status: approved`, `approved_by:`, `approved_on:`. `charter check` refuses `approved` without the two fields (R7). Recorded in `charter/changes/<slug>.md`; the approval is a commit by the owner.
- Also: a unit whose `scope:` names an unknown id is refused; a unit with no `scope:` is a warning.

### Size (R3): frozen file

- Checks: after the edit or in the staged version the file exceeds `limits.file_lines` (800 by default) and grew. Governance files (`CLAUDE.md`, `AGENTS.md`, `charter/scope.md`, `.claude/rules/*.md`, `charter/decisions/*`, `charter/changes/*`) use `limits.governance_lines` (400). Globs in `exempt_from_size` are skipped. At 80% of the limit a warning says to plan a split.
- Blocks: `PreToolUse` deny; pre-commit; CI with `--strict` reports every file over the limit.
- Override: an open unit with `kind: split` whose `perimeter:` covers the file. While it is open the file may grow (warning only), so the split can be done in steps. Recorded in that unit's `## Log` and `## Evidence`. Shrinking a file is always allowed.

### Done needs evidence (R9)

- Checks: a tasket whose `status` is in `done_statuses` must have a `## Acceptance` checklist with every box checked and a `## Evidence` section with at least one resolving anchor (a commit that `git cat-file -e` finds, a `path:line` within the file's length, a URL, or a `$ command` line). Anchors that do not resolve are refused.
- Blocks: `PreToolUse` deny on the tasket edit; pre-commit for a tasket whose status changes to done in the commit (with `--strict`, every done tasket); CI with `--strict`.
- Override: none by flag. Keep the status open, or add the evidence. A tasket that must be closed without evidence is `parked` or `skipped`, both terminal for the engines and both honest.

### Decisions (R1)

- Checks: every `charter:<id>` marker in an edited or staged file names an existing decision; a decision with `status: superseded` or `retired` cannot be cited (the message names `superseded_by`). A file matching an active decision's `binds:` globs without its marker is a warning. Every active decision's `check:` command is run; a non-zero exit is "contradicted".
- Blocks: `PreToolUse` deny for a retired citation; `PostToolUse` exit 2 (stderr to Claude) when a bound file's check fails after the edit; pre-commit and CI for both.
- Override: supersede the decision with a new record that sets `supersedes:` and set the old one to `superseded` with `superseded_by:`. The new record carries its own `## Because`. Recorded in `charter/decisions/`.

### Perimeter (R4)

- Checks: the active unit (`.charter/state/active`, or `CHARTER_UNIT`) declares `perimeter:` globs; an edited or staged path outside them, outside `.taskets/`, `charter/` and `.charter/`, and not named under the unit's `## Outside perimeter` section.
- Blocks: `PostToolUse` warning in session; pre-commit block on the client track, warning on the prototype track; CI does not know the active unit and does not check this.
- Override: the note itself (`- path: why`), or widening `perimeter:`. No active unit is a warning ("edits are not attributed"), never a block.

### Memory (R8)

- Checks: an active decision without `## Because`, without `expires:`, or past a dated `expires:`; a `kind: lesson` without `owner:`.
- Warning only, in `charter check --memory` and CI output.

### Stop gate (R9/R10 in the session)

- Checks: `last_assistant_message` contains a completion claim (done, complete, implemented, fixed, shipped, tests pass, a check mark) and no resolving anchor, and does not admit "not done" or "unverified"; or the active unit is `done` and fails the done gate.
- Blocks once. The second Stop in the same turn passes through and logs `done/passed`. Reason text names what to cite.

### Anchors (R10)

- Command: `charter anchors <file>...`, exit 1 on any unanchored claim line or unresolved anchor. Definitions in `docs/method.md` § Accepted results. Exempt sections: `<!-- charter: opinion -->` ... `<!-- charter: /opinion -->`. Admitted claims: `(unverified)`, `(reported in ...)`, `(estimate ...)`, `(to be confirmed)`.
- Runs in CI on `charter/progress.md`, `docs/progress*.md`, `docs/report*.md` and the PR body. Not on decisions or the scope, whose statements are normative.
- `charter synth` runs it on its own output and refuses to write on failure.

## Git hook

`package/.charter/githooks/pre-commit` runs `python3 -B .charter/bin/charter check --staged`. Activated by `git config core.hooksPath .charter/githooks` (the installer does it; a clean clone must run it once, and CI is the backstop). A relative `core.hooksPath` resolves inside linked worktrees, verified in the trial (G7). `git commit --no-verify` skips it; CI runs the same checks.

## CI

`package/.github/workflows/charter.yml`: on pull requests and pushes to `main` and `staging`: `charter check --all --ci --base <sha>` where the base is the PR base SHA or the push's previous SHA; `charter anchors` on syntheses and reports; `charter anchors` on the PR body. It needs Python 3 and nothing else on the runner.

## What a gate cannot see

- A `PreToolUse` hook does not run for an Edit whose `old_string` is absent from the file: Claude Code rejects that Edit first (trial T1c). It does not run for files added with `@` in a prompt, nor for files changed by a Bash command; the git hook and CI see those.
- The perimeter gate depends on the session declaring its unit. Nothing forces `charter unit start`; the log shows unattributed edits and the SessionStart banner says so.
- The done gate checks the shape of the evidence, not its truth (a real commit that did something else passes). The reviewer agent and the owner check the truth.
- The scope gate matches paths. Work that is out of scope but lands in an in-scope path is invisible to it; the unit's `scope:` and the owner's review carry that.
- A permission denial (`--permission-prompts none`) and a gate denial read alike to the agent. The log distinguishes them.
