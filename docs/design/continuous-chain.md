# The continuous chain (0.4.9)

A chain runs the road as a series of fresh Claude Code sessions. Each one verifies the one before, works unit after unit under a context budget, and hands over to the next through a validated handoff. The owner starts it with `/charter-chain` and a session of their own monitors it (`package/.claude/skills/charter-chain/SKILL.md`). The engine is `package/.charter/chain.py`; the hook is `package/.charter/hooks/chain_gate.py`.

## What was asked

The owner's words, 2026-10-04 (operator report, this session), as typed in a charter project:

> go with unit 1. Optimize context window, and as long as things go well, iterate on the next unit until it's done. Like a long chain of units, each session should eventually verify what has done the previous one, and tell the next one "the rules" so it can apply it and transmit it later. To prevent deterioration, let's fix those rules by adding a workflow in Charter : continuous chain. Once done, start the chain and monitor. No session should go over 30% of context usage. Or when it does, then it should launch a new session with the normalized handoff. *(operator report, 2026-10-04)*

The owner chose, the same day: sessions open as visible tabs through the spawn plugin rather than in a headless driver; on main or master a chain works on a branch `chain/<id>`; a real trial before release (operator report, 2026-10-04).

## The shape

```
owner's session ──/charter-chain──▶ charter chain start ──launch──▶ s01 ─┐
      ▲                                  (branch, chain.json,           │ works units; the hook measures context
      │                                   briefing s01)                 │ at 25%: "hand over"; at 30%: only the handoff
      │                                                                 ▼
      │  chain watch (Monitor)        s02 ◀──launch── charter chain next (run by s01):
      └──────── events.log ◀───────── ...              validate handoff, facts (commits, probes, gates),
                                                       close s01, brief s02, close the tab before
```

Every session's first prompt is a briefing written by code (`briefing` in `package/.charter/chain.py`). Its first line, `charter-chain: <id> session <n>`, is what the hook joins the session by. It carries the owner's mission verbatim, the budget, the predecessor's handoff verbatim, and the mechanical verification of the predecessor's work.

## Each requirement and what holds it

| Asked | Held by | Where |
|---|---|---|
| "No session should go over 30% of context usage" | The hook measures the session's context after every tool call from its transcript, says the share every 5 points, says hand over at 25%, and past 30% denies every tool but the handoff, the unit files, git and the charter CLI | `on_post_tool`, `on_pre_tool`, `allowed_at_cap`, `context_tokens` in `package/.charter/chain.py` |
| "launch a new session with the normalized handoff" | The handoff is a fixed template; `charter chain next` refuses one that does not validate, then launches the next session | `package/charter/templates/handoff.md`; `check_handoff`, `cmd_next`, `launch` |
| "each session should eventually verify what has done the previous one" | `chain next` records the commits, re-runs the probes of every unit closed in the session, runs the gates on its change set and reports the tree; the next session gets that report, judges the evidence (rules § 1) and must cite a run, a commit or a `path:line` under `## Verified` | `facts`, `check_handoff` in `package/.charter/chain.py`; `package/.charter/chain-rules.md` § 1 |
| "tell the next one the rules ... To prevent deterioration, let's fix those rules" | The rules are a file only the owner edits, injected verbatim into every session by the hook. The handoff carries state, never rules. The chain records the file's SHA-256 at the start and halts if it changes | `package/.charter/chain-rules.md`; `join`; owner-only by `.charter/**` (`OWNER_ONLY_GLOBS` in `package/.charter/checks.py`) |
| "as long as things go well, iterate on the next unit" | The Stop hook keeps a session from ending its turn before it handed over. The chain stops itself on a halt, on a finished road, when two sessions in a row change nothing outside the unit files, when a session's start-up alone reached the hand-over line, at the session limit, or when the owner stops it | `on_stop`, `cmd_next`, `stalled`, `started_past_line` in `package/.charter/chain.py` |
| "Optimize context window" | A `continue` handover below the line is refused when nothing was committed, or below half the line, unless the session says why (`--early`); the rules say to read by range and hand broad searches to subagents | `cmd_next` in `package/.charter/chain.py`; `package/.charter/chain-rules.md` § 3 |
| "start the chain and monitor" | `/charter-chain` starts it and follows `charter chain watch` with the Monitor tool; every event is one line in `events.log` | `package/.claude/skills/charter-chain/SKILL.md`; `cmd_watch`, `event` |

## Choices, and why

- **Each session launches the next, not a driver.** The owner wanted visible tabs (operator report, 2026-10-04). A driver that reads a headless session's stream cannot see an interactive tab, so the hand-over moves into the session: `charter chain next` is the only way to launch. The `headless` launcher (`claude -p`, detached) remains for unattended runs and for the trial.
- **The spawn plugin's shim opens the tabs.** It already handles tele-claude, tmux, cmux and a terminal window, and reports a child stopped at a menu (`plugins/spawn/agent-backend/agent_session.py` in https://github.com/elgui/claude-plugins). The package finds it under the Claude Code config directory and does not copy it; `CHARTER_SPAWN_SHIM` overrides, and a command template is a third way (`resolve_launcher` in `package/.charter/chain.py`).
- **The hook is wired in the project's settings, with a fast exit.** The shim passes a model and an effort and nothing else, so a per-launch `--settings` cannot add the hook, and the entries live in `package/.claude/settings.json`. A session not in a chain tests one file and leaves, without importing charter or running git: 25.6 ms median against 20.9 ms for a bare `python3` (30 runs each, 2026-10-04).
- **Joining by a marker in the first prompt.** A `UserPromptSubmit` hook receives the prompt and the session id (https://code.claude.com/docs/en/hooks), so it needs no cooperation from the launcher or the model. `charter chain join` is the fallback, using `CLAUDE_CODE_SESSION_ID`, which a session's Bash commands carry. That was observed in a `-p` session on 2026-10-04, where `echo $CLAUDE_CODE_SESSION_ID` printed the session's id.
- **Context from the transcript.** No hook input carries context usage; the status line does (`context_window`, https://code.claude.com/docs/en/statusline), but the status line is the person's own configuration. The transcript's last main-chain response gives input, cache and output tokens; its format is internal (https://code.claude.com/docs/en/sessions), so an unreadable transcript makes the budget gate allow. The window is not recorded anywhere a hook can read, so it is 1M for a `[1m]` model, else 200k, unless `chain.window_tokens` says otherwise (`window_for`).
- **Rules through the hook, not in the briefing.** The briefing is written by code from the previous handoff; the rules never pass through a model's hands, so they cannot be paraphrased on the way (`briefing` and `join` in `package/.charter/chain.py`).

## What it does not do

- It does not check that a session read the code it verified. It checks that `## Verified` cites a run and it re-runs the probes itself. A probe that tests the wrong thing passes, as it does for the done gate (`docs/gates.md` § What a gate cannot see).
- The budget lags by one response; a tool result counts as its characters divided by 4 until the next response reports it (`on_post_tool` in `package/.charter/chain.py`).
- Past the cap, `git` is allowed whole, because committing is part of handing over (`allowed_at_cap` in `package/.charter/chain.py`).
- Two sessions in one clone share one active unit (`docs/bugs/2026-10-02-concurrent-sessions-in-one-clone-share-one-active-unit.md`). The chain's own sessions run one at a time, but the owner working in the same clone during a chain is the reported bug.
- The chain never decides or acts for the owner. A waiting, halted, stopped or stalled chain waits for the owner to type `/resume-chain` in a Claude Code session (`owner_prompt` in `package/.charter/chain.py`, § Waiting on the owner), which can also set a new budget (`--window`, `--wrap`, `--cap`) for the sessions that follow. It does not resume on its own when the owner ticks a line: the owner chose one command they type, with a note for the next session, over a process that polls for hours (2026-10-04).
- It does not fit the budget to the start-up. A session pays its start-up (system prompt, tools, skills, MCP instructions, rules, briefing) before any work, and in a cmux tab that was 49,500 tokens on 2026-10-04, against about 32,000 headless. A chain whose hand-over line is under it would only relaunch sessions that hand over at once, so the first session that starts past the line halts the chain with the figure (`started_past_line`), and `chain start` warns beforehand (`measured_startup`; `docs/trials/2026-10-04-chain-tab.md`).

## Groups and their review

The engine is `package/.charter/chain_groups.py`; `chain.py` calls it at the start, at each hand-over, on resume and in the briefing.

### What was asked

The owner's words, 2026-10-04, as typed (operator report, 2026-10-04):

> make sure there is no drift or merge conflicts, and that each new group starts with what has been done before (even if it later needs fixes). Maybe the best way to to auto-trigger a command like "/reviewPR" that performs a PR review with codex native. I have a subscription for it. *(operator report, 2026-10-04)*

Of three ways put to the owner the same day, they chose: one chain branch on which each group is cleared at a commit they can merge up to, rather than a stacked branch per group; at a group's end, review, fix and go on without them; the review run locally and kept with the chain, not a pull request opened by code (operator report, 2026-10-04).

### The shape

```
 group r1 (rail r1)                    end of r1                                  group r2
 s01 ─ s02 ─ s03 ─chain next─▶ review runner ──────────────────────────▶ s04 answers ─▶ s05 starts r2
 start ............. end        git worktree add --detach <tmp> <end>      every finding   (start = s04's last commit)
                                codex exec review --base <start> -o ...
                                no findings ──────────────────────────────────────────▶ s04 starts r2 (start = end)
```

A group is the units of one item of `charter/rails.md`: a unit's group is its first open rail in the order `charter next` uses (`group_of` in `package/.charter/chain_groups.py`, `road_key` in `package/.charter/bin/charter`). A project without a rails file groups by the tasket `group:` key; a project with neither has one group, reviewed when the road ends.

### Each requirement and what holds it

| Asked | Held by | Where |
|---|---|---|
| "each new group starts with what has been done before" | One branch: a group starts at the commit the one before was cleared at, never from main | `clear` in `package/.charter/chain_groups.py` |
| "even if it later needs fixes" | A defect in an earlier group is fixed forward on the same branch; a session may start a unit of an earlier group, and the next review covers the fix | `unit_start_refusal` (earlier groups pass) in `package/.charter/chain_groups.py`; `package/.charter/chain-rules.md` § 6 |
| "no drift or merge conflicts" | Nothing is ever rebased or merged inside the chain: there is one line of history. Each cleared group is a commit the owner merges up to, with a merge commit or a fast-forward | `cmd_report` in `package/.charter/chain_groups.py`; `package/.claude/skills/charter-chain/SKILL.md` § When it ends |
| "auto-trigger ... a PR review with codex" | At a group's end `chain next` starts a runner that reviews the group's whole range with `codex exec review --base <start>`, in a detached worktree at the group's last commit | `advance`, `start_review`, `run_review`, `review_command` in `package/.charter/chain_groups.py` |
| The next group starts from the reviewed group | `charter unit start` refuses, in a chain session, a unit of a group that has not started; the session hands over (allowed under the hand-over line), and the runner launches the next session only once the review is in | `unit_start_refusal`, `ends_group` in `package/.charter/chain_groups.py`; `cmd_unit` in `package/.charter/bin/charter` |
| Every finding is dealt with | The next session gets the findings verbatim, numbered R1..Rn; `chain next` refuses its handoff until `## Review` has one line per finding, starting with its id: `fixed` with a commit after the reviewed range, or `dismissed` with a `path:line` or a `$ command`. A halt leaves the whole review to the session after the owner's answer | `briefing_lines`, `check_review`, `on_resume` in `package/.charter/chain_groups.py`; `package/charter/templates/handoff.md` |
| The merge point holds the whole group | Nothing uncommitted crosses a group's end, nor the end of the session that answers its review, even when `## State` names it | `needs_commit` in `package/.charter/chain_groups.py`; `cmd_next` in `package/.charter/chain.py` |

### Choices, and why

- **One branch, not a branch per group.** With a stacked branch per group, a fix to group A after group B started lands on A and must be merged into B and every group after it; a conflict there needs a session, and the chain rules forbid sessions to merge or rebase (`package/.charter/chain-rules.md` § Never). tele-claude's group automator, the prior art, opens one branch per group from `main`, so a group sees the one before only after the owner merged it: tcv2's `auto/*` pull requests #22 to #103 all have `main` as their base (`$ gh pr list -R elgui/tcv2 --state all --json number,headRefName,baseRefName`, 2026-10-04). A linear branch gives the per-group review and the per-group merge without a second line of history to keep in step.
- **Merge up to a cleared commit, not a squash.** The owner squash-merges some pull requests (tcv2 #103 landed as one commit, `3144973`, `$ git log --first-parent origin/main` in tcv2, 2026-10-04). A squash of a group's prefix gives `main` a commit the chain branch does not have, and the later groups' pull request shows the prefix again; a merge commit or a fast-forward does not.
- **Codex's built-in review, no prompt.** `codex exec review --base <sha>` reviews the range from a commit (measured with codex-cli 0.147.0 on 2026-10-04: `--base` takes a SHA), and refuses a custom prompt with `--base` ("the argument '--base <BRANCH>' cannot be used with '[PROMPT]'", same day). Its last message, written with `-o`, gives one line per finding, `- [P1] <title> — <path>:<line>`, which `parse` numbers; a text that names a severity but has no such line becomes one finding to read whole, so a change of format is never a silent "nothing found" (`parse` in `package/.charter/chain_groups.py`). The `/reviewPR` command the owner uses elsewhere ran the same review as its first pass, `codex review --base main`, then posted a comment on the pull request (https://github.com/elgui/tcv2/pull/8); its file is not on this machine (`~/.claude/commands/` has no `reviewPR.md`, 2026-10-04), so the chain does not call it.
- **A worktree of its own at the group's last commit.** The review must see the committed group, not the live tree, where the owner's resume or a later session may write; the runner adds a detached worktree in a temporary directory of the chain's own (`charter-review-<repository hash>-<chain id>`) and removes it after; a runner killed before that leaves it, and the chain's next review removes it first (`review_tmp`, `run_review`, `_drop_tree` in `package/.charter/chain_groups.py`).
- **A runner, not a wait inside `chain next`.** `chain next` runs in the session's Bash tool, whose foreground commands time out after 2 minutes by default and 10 at most (`BASH_DEFAULT_TIMEOUT_MS`, `BASH_MAX_TIMEOUT_MS`, https://code.claude.com/docs/en/env-vars), and a review at high effort can take longer than that. The runner is a detached process (`charter chain review-run`) that records the review and launches the next session the way `chain next` would; it writes its pid so `chain resume` refuses while it runs (`start_review`, `cmd_review_run`, `review_running` in `package/.charter/chain_groups.py`).
- **A session that answers the review, and nothing else.** The group's merge point must hold the group and its fixes and nothing of the next group, so the answering session cannot start a unit of the next group, and the next group starts from its last commit. When the review finds nothing, no such session is spent (`unit_start_refusal`, `clear` and `cmd_review_run` in `package/.charter/chain_groups.py`).
- **A review that cannot run halts the chain.** Codex missing, logged out, failing or past `chain.review_timeout_s` (30 minutes by default) halts it with the reviewer's last lines; `chain resume` runs the review again, and `chain resume --skip-review` clears the group without it, which only the owner asks for (`on_resume` in `package/.charter/chain_groups.py`).
- **`chain.review` is `auto` by default**: Codex where `codex` is on PATH, else off, and `chain start` says which. `off` runs the chain without groups. A command template with `{base}` and `{out}` runs another reviewer; the tests use one (`resolve_review` in `package/.charter/chain_groups.py`; `tests/test_groups_0_4_8.py`).

### What it does not do

- The answering session's fixes are not reviewed again by Codex: the next session verifies them (`package/.charter/chain-rules.md` § 1), and `chain next` re-runs the probes and the gates. A group that goes back to work after its review is reviewed again from where the last review ended, so that review covers the fixes; each review and its answers are kept, and `chain report` prints them in order (`advance`, `rounds` in `package/.charter/chain_groups.py`).
- A session can work on a unit of the next group without `charter unit start`, since an edit without an active unit is only logged as unattributed (`package/.claude/rules/charter.md` § Before you change code). `chain next` names in the facts a unit of a later group that moved, a unit whose `rail:` or `group:` changed, and a changed path that only a later unit's perimeter covers; that work then falls in the review of the group before, or in no review when the session was answering one. A change to a path the current group also covers is not named (`crossing` in `package/.charter/chain_groups.py`).
- A review that ends after the owner stopped the chain is recorded and ends nothing: `chain resume` launches the answering session, or completes the chain (`cmd_review_run`, `_record`, `clear`, `on_resume` in `package/.charter/chain_groups.py`). The runner records under the chain's lock, which `charter chain stop` takes too, so a stop is never overwritten by a stale copy of the state, nor the review's outcome by the stop (`chain_lock` in `package/.charter/chain.py`).
- It does not open a pull request or post a comment: pushing is the owner's (`package/.claude/rules/charter.md` § Decisions and memory). `charter chain report` prints every group's review and answers as one comment for the owner to post.
- A review costs minutes at each group's end, and Codex usage on the owner's subscription. On a 4-line diff at low effort it took 26 s (`$ codex exec review --base <sha> -c model_reasoning_effort=low -o <file>` in a scratch repository, 2026-10-04); in the two trial runs, groups of one or two small functions took 39 to 75 s at high effort (`docs/trials/2026-10-04-groups.md`). A larger group is not measured (unverified).

## Waiting on the owner

### What was asked

"The chain should handle elegantly and with decent UX the case where a human is mandatory. I don't mind if the chain has to pause to wait for me (when relevant)" (operator report, 2026-10-04). The road that prompted it, a confidential zone on a Mac, has a step only the owner can take in every unit: sudo with Touch ID, a disk-encryption setting, a paid bucket, a decision, an irreversible purge. Before this, a session halted at the first one, and the owner learned of it by watching.

### The shape

```
session n: does what does not need the owner, commits, marks the unit's lines `— owner: do|check`
         └─ handoff status: wait, ## Wait (one line per act), next_unit
chain next ── clean tree? ──> chain state `waiting`, event `wait`
                              ├─ macOS notification, chain.notify_command
                              └─ `charter owner` / `charter next`: the chain, its acts, the line to type
owner: does the acts, types `/resume-chain ok <note>` (or `skip <note>`) in a Claude Code session of their own
         └─ prompt hook: closes the waited lines in a commit made as the owner, resumes; the prompt never reaches the model
session n+1: briefing says the chain waited and which lines the owner closed; checks each act first; waits again on any not done
```

### Each requirement and what holds it

| Requirement | What holds it |
|---|---|
| Work that does not need the owner is done before the chain pauses | Chain rules § 5, steps 1 to 3 (`package/.charter/chain-rules.md`) |
| The pause names each act, how to do it, and what it closes | `check_handoff` refuses `status: wait` without `## Wait`; the acts are the unit's `— owner:` lines, which `owner_lines` in `package/.charter/owner.py` lists |
| The chain waits at a commit, and goes on from one | `cmd_next` in `package/.charter/chain.py` refuses `wait` (and `complete`) with uncommitted changes; `_resume` refuses a waiting chain's resume while the owner's changes are uncommitted, and prints the commit (`tests/test_chain_wait.py`) |
| The owner is told | `notify` in `package/.charter/chain.py`, on waiting, halted, complete, a tab at a menu and a stall; `chain.notify` (`auto`: macOS, or `off`) and `chain.notify_command` (`{chain}`, `{project}`, `{title}`, `{text}`); `CHARTER_NOTIFY=off` silences it |
| The owner sees what to do where they already look | `owner_items` in `package/.charter/chain.py`, read by `queue` in `package/.charter/owner.py`: `charter owner [--json]` and `charter next` list the chain with its acts and the `/resume-chain` line to type, with the owner's lines it closes |
| Nothing goes on until the owner says so | State `waiting`; `cmd_start` in `package/.charter/chain.py` refuses while a chain waits; only the owner's `/resume-chain` launches (`owner_prompt`, `_resume`); `charter chain resume` refuses everyone (`cmd_resume`; `tests/test_owner_gate.py`) |
| The owner's acts are the owner's, not an agent's | An `— owner:` line is closed only by the owner: the Edit gate and the commit gate inside Claude Code refuse an agent's tick, unmarking or removal, and CI checks the author (`owner_line_changes` in `package/.charter/checks.py`). The resume is the owner's own prompt, performed by the prompt hook and blocked from the model, refused in a headless or chain session (`typed_by_owner`). A line closed since the wait by any other commit is named to the owner and to the next session, which reopens it unless the owner's note claims it (`closed_outside`). The hook denies any session's Bash command that names `CHARTER_OWNER` (`package/.charter/hooks/chain_gate.py`). See § The owner's acts below |
| The next session does not take the acts on trust | The briefing after a wait says so (`briefing` in `package/.charter/chain.py`); chain rules § 5 (`package/.charter/chain-rules.md`) |
| A chain session never performs an owner act | `charter rule`, `approve` and `rail` refuse inside an open chain session (`live_session`, `_owner_verb` in `package/.charter/bin/charter`), and the hook denies such a command whatever its environment (`OWNER_ACT_RE`, `on_pre_tool` in `package/.charter/chain.py`); `AskUserQuestion` is denied with a pointer to `wait` |

### The owner's acts

In the wait trial an agent stood in for the owner, and the chain accepted it. Session 1 of chain `20261004-204830` waited on "approve the tone of `farewell('Ada')`, then tick AC-2". 24 s later, the session that ran the trial (not the owner, and not a chain session) ran one Bash command: `sed -i` ticked AC-2, `git commit -am "w1 AC-2: tone approved (owner stand-in, trial)"` (on the test bed), and `charter chain resume --note "Tone approved: ... I ticked AC-2."`. Session 2 closed the unit and the chain completed (`docs/trials/2026-10-04-chain-wait.md`; `docs/trials/2026-10-04-owner-gate.md`). Nothing told that act from the owner's: the CLI accepted any caller, an owner line was ordinary text, and the commit's author was the repository's git user.

What was weighed, with the owner (operator report, 2026-10-04):

| Mechanism | What an agent can still do | Taken |
|---|---|---|
| Refuse `chain resume` in any Claude Code process (`CLAUDECODE`) | `env -u CLAUDECODE`; type the command into a plain terminal tab (`cmux send`, `osascript`); run from a session of another project, whose hooks are not the project's | no: no proof, and a determined agent passes (operator report, 2026-10-04) |
| Touch ID: a Secure Enclave key signs the resume and the ticks; the chain and CI verify the signature | trigger the prompt with a misleading reason, and hope the owner touches | no: the owner does not want Touch ID (operator report, 2026-10-04) |
| The owner's own prompt: `/resume-chain`, performed by the prompt hook | type the command into an interactive tab by a program (`cmux send`, `tmux send-keys`, `osascript`); write the chain's state files or the engine by hand | yes, with owner lines made owner-only content (`owner_prompt` in `package/.charter/chain.py`) |

The owner also said that "resume" in a chat often means "continue" after an interruption, so the monitoring session never takes it as a resume, and a slash command is what they type. The hook, not the model, performs the command: Claude Code passes the raw prompt to `UserPromptSubmit` and, for a defined command, to `UserPromptExpansion` with its arguments, and a hook that answers `{"decision": "block"}` keeps the prompt from the model (https://code.claude.com/docs/en/hooks). `disable-model-invocation: true` keeps the model from invoking the command (https://code.claude.com/docs/en/skills). In `claude -p`, Claude Code set `CLAUDE_CODE_ENTRYPOINT=sdk-cli` and `CLAUDE_CODE_SESSION_ATTENDED=0` in the hook's environment over what the caller passed (2.1.289, in the scratchpad), so `typed_by_owner` refuses a headless session. A `do` line and a `check` line are gated alike: closing either says the owner did it. What stays open is in `docs/gates.md` § What a gate cannot see.

### What it does not do

- It does not check that the owner did an act. The owner's `/resume-chain AC-2` says they did; the next session checks what it can (a probe, the owner's note) and waits again on what is not done (chain rules § 5, `package/.charter/chain-rules.md`).
- It does not work on other units while it waits. A wait pauses the whole chain; units that do not depend on the owner's act wait too (`_hand_over` in `package/.charter/chain.py`).
- At a group's end, the review runs on resume, not during the wait (`on_resume` in `package/.charter/chain_groups.py`).

## Trial

`docs/trials/2026-10-04-chain.md`: three chains on a test bed, headless and in cmux tabs, with what each showed and what it changed.

`docs/trials/2026-10-04-chain-tab.md`: a chain in cmux tabs whose sessions all started past the hand-over line, and the four defects it showed.

`docs/trials/2026-10-04-chain-tab-rerun.md`: the same bed on this release (labelled 0.4.8 in the record) in tabs, where the review runner opened the next session's tab and the chain completed in 3 minutes.

`docs/trials/2026-10-04-groups.md`: a chain over two rails with the Codex review at each group's end (labelled 0.4.8 in the record). The first review found a real defect, the next session fixed it, and the chain completed on its own.
