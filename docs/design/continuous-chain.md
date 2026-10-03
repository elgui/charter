# The continuous chain (0.4.7)

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

## Trial

`docs/trials/2026-10-04-chain.md`: three chains on a test bed, headless and in cmux tabs, with what each showed and what it changed.
