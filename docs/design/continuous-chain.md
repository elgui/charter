# The continuous chain (0.4.7; groups and their review, 0.4.8)

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
| "as long as things go well, iterate on the next unit" | The Stop hook keeps a session from ending its turn before it handed over. The chain stops itself on a halt, on a finished road, when two sessions in a row land nothing, at the session limit, or when the owner stops it | `on_stop`, `cmd_next`, `stalled` in `package/.charter/chain.py` |
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
- The chain halts; it never decides for the owner. A halted, stopped or stalled chain waits for `charter chain resume` (`cmd_resume` in `package/.charter/chain.py`).

## Groups and their review (0.4.8)

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
- **A worktree of its own at the group's last commit.** The review must see the committed group, not the live tree, where the owner's resume or a later session may write; the runner adds a detached worktree in a temporary directory and removes it after (`run_review` in `package/.charter/chain_groups.py`).
- **A runner, not a wait inside `chain next`.** `chain next` runs in the session's Bash tool, whose foreground commands time out after 2 minutes by default and 10 at most (`BASH_DEFAULT_TIMEOUT_MS`, `BASH_MAX_TIMEOUT_MS`, https://code.claude.com/docs/en/env-vars), and a review at high effort can take longer than that. The runner is a detached process (`charter chain review-run`) that records the review and launches the next session the way `chain next` would; it writes its pid so `chain resume` refuses while it runs (`start_review`, `cmd_review_run`, `review_running` in `package/.charter/chain_groups.py`).
- **A session that answers the review, and nothing else.** The group's merge point must hold the group and its fixes and nothing of the next group, so the answering session cannot start a unit of the next group, and the next group starts from its last commit. When the review finds nothing, no such session is spent (`unit_start_refusal`, `clear` and `cmd_review_run` in `package/.charter/chain_groups.py`).
- **A review that cannot run halts the chain.** Codex missing, logged out, failing or past `chain.review_timeout_s` (30 minutes by default) halts it with the reviewer's last lines; `chain resume` runs the review again, and `chain resume --skip-review` clears the group without it, which only the owner asks for (`on_resume` in `package/.charter/chain_groups.py`).
- **`chain.review` is `auto` by default**: Codex where `codex` is on PATH, else off, and `chain start` says which. `off` keeps the chain of 0.4.7, without groups. A command template with `{base}` and `{out}` runs another reviewer; the tests use one (`resolve_review` in `package/.charter/chain_groups.py`; `tests/test_groups_0_4_8.py`).

### What it does not do

- The answering session's fixes are not reviewed again by Codex: the next session verifies them (`package/.charter/chain-rules.md` § 1), and `chain next` re-runs the probes and the gates. A group that goes back to work after its review is reviewed again from where the last review ended, so that review covers the fixes; each review and its answers are kept, and `chain report` prints them in order (`advance`, `rounds` in `package/.charter/chain_groups.py`).
- A session can work on a unit of the next group without `charter unit start`, since an edit without an active unit is only logged as unattributed (`package/.claude/rules/charter.md` § Before you change code). `chain next` names in the facts a unit of a later group that moved, a unit whose `rail:` or `group:` changed, and a changed path that only a later unit's perimeter covers; that work then falls in the review of the group before, or in no review when the session was answering one. A change to a path the current group also covers is not named (`crossing` in `package/.charter/chain_groups.py`).
- A review that ends after the owner stopped the chain is recorded and ends nothing: `chain resume` launches the answering session, or completes the chain (`_review_and_record`, `clear`, `on_resume` in `package/.charter/chain_groups.py`).
- It does not open a pull request or post a comment: pushing is the owner's (`package/.claude/rules/charter.md` § Decisions and memory). `charter chain report` prints every group's review and answers as one comment for the owner to post.
- A review costs minutes at each group's end, and Codex usage on the owner's subscription. On a 4-line diff at low effort it took 26 s (`$ codex exec review --base <sha> -c model_reasoning_effort=low -o <file>` in a scratch repository, 2026-10-04); in the two trial runs, groups of one or two small functions took 39 to 75 s at high effort (`docs/trials/2026-10-04-groups.md`). A larger group is not measured (unverified).

## Trial

`docs/trials/2026-10-04-chain.md`: three chains on a test bed, headless and in cmux tabs, with what each showed and what it changed.

`docs/trials/2026-10-04-groups.md`: a chain over two rails with the Codex review at each group's end (0.4.8). The first review found a real defect, the next session fixed it, and the chain completed on its own.
