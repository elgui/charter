---
name: charter-chain
description: Run the road as a continuous chain of fresh sessions. Each one verifies its predecessor, works unit after unit under a context budget (hand over at 25%, hard cap 30% of the window), and hands over through a validated handoff; at the end of each group of units (a rail item) Codex reviews the group and the next session answers every finding before the next group starts. This session starts the chain and monitors it. USE WHEN the user types /charter-chain, says "start the chain", "chain the units", "continuous chain", "keep going unit after unit in fresh sessions", "chain status", "stop the chain", "resume the chain".
argument-hint: "[unit-id] [mission…] | status | stop | resume [note]"
---

# charter-chain

You are the monitoring session. The chain's sessions do the work; you start the chain, watch it and report to the owner. Do no unit work here: your context stays small, and an edit from here would be attributed to the chain's active unit.

## Start: `/charter-chain [unit-id] [mission]`

1. **Mission.** Everything in `$ARGUMENTS` after a leading unit id, verbatim. The owner's words go to every session unchanged, so do not rephrase, shorten or "improve" them. Write them with the Write tool to a new file in your scratchpad, never on a command line. No words: no mission file, and the default mission works the road from the unit.
2. **Unit.** The leading id if `.taskets/` has it; otherwise the first unit under "Next on the road" (or "Open units") in `python3 .charter/bin/charter next`. Say which in one line.
3. **Dry run.** `python3 .charter/bin/charter chain start --unit <id> [--mission-file <file>] --dry-run`. If it refuses (uncommitted changes, a chain already running, no launcher), give the owner its lines verbatim and stop: a dirty tree is the owner's to commit or stash. Pass `--model`, `--effort`, `--launcher`, `--review` or `--here` only when the owner asked; the defaults are in `charter/config.json` under `chain` (model `opus[1m]`, effort `high`, hand over at 25%, cap 30%, at most 12 sessions, launcher `auto`: the spawn plugin's tabs; review `auto`: Codex at the end of each group when `codex` is on PATH, effort `high`).
4. **Start.** The same command without `--dry-run`. On main or master it creates and checks out `chain/<id>`; say so. Report in three lines: chain id and branch; where session 1 opened (a tab titled `[s] chain <id> s01`, a window, or headless) and the budget; the `review:` line as printed (the reviewer, and the group the chain starts on).
5. **Monitor**, below.

## Monitor

- Use the Monitor tool on `python3 .charter/bin/charter chain watch <id> --from <line>`, starting at line 1. Each event arrives as one line, `#<line> <time> <who> <kind>: <text>`. If the watch ends on the Monitor deadline, start it again from the next line number. When it prints `watch ends`, the chain is over. Without the Monitor tool, run the same command with Bash `run_in_background` and read it when it notifies.
- Tell the owner in one line each: `launched` (session n is up), `closed` (what it landed: commits, units closed, peak context), `waiting` (a tab stopped at a menu: which tab and what it asks), `stalled` (a session ended its turn without handing over: its tab needs a look), `cap`, `review` (a group ended and its review started; the chain waits for it, minutes), `reviewed` (how many findings, and which session answers them), `cleared` (the group and the commit the owner can merge up to), and the end. Stay quiet on `joined`, `wrap` and `tab-closed`.
- Act only on the owner's word. A halted or stalled chain waits for them: you never resume it, edit a handoff, or do a session's work.

## When it ends

Run `python3 .charter/bin/charter chain status <id>` and report:

- the outcome: complete, stopped, or halted with its reason verbatim (it is what the owner must decide);
- each session's peak context and what it landed; the units closed and their commits;
- each group from the `groups` lines of `chain status`: its range, its findings and who answered them, and the commit it is cleared at;
- what waits on the owner: the halt, the branch to review and merge (merging is theirs: up to any cleared commit, with a merge commit or a fast-forward, not a squash, so the later groups still apply), and the "Waiting on the owner" lines of `python3 .charter/bin/charter next`;
- that `python3 .charter/bin/charter chain report <id>` prints every group's review and its answers as one comment for the pull request, which the owner opens and posts.

## Other verbs

- `status`: `python3 .charter/bin/charter chain status`, relayed as printed.
- `stop`: `python3 .charter/bin/charter chain stop`. The live session is told to hand over, and no session follows it.
- `resume [note]`: only on the owner's word, after a halt, a stop or a stall. Write the note verbatim to a file, run `python3 .charter/bin/charter chain resume --note-file <file>` (`--more N` raises the session limit; `--window <tokens>`, `--wrap <pct>`, `--cap <pct>` set the budget, when the halt says a session's start-up reached the hand-over line), then monitor again. After a review that could not run, resume runs it again; `--skip-review` clears the group without it, and only the owner asks for that.
- `report`: `python3 .charter/bin/charter chain report`, relayed as printed.

## What holds the chain

For the owner's questions; the detail is in `docs/design/continuous-chain.md` of the charter repository.

- **Rules**: `.charter/chain-rules.md`, owner-only, injected verbatim into each session by the hook when it joins. The chain halts if the file changes while it runs, so the rules cannot drift from session to session.
- **Handoff**: `charter/templates/handoff.md`. `chain next` refuses a handoff that is malformed, longer than 80 lines, cites a commit that does not resolve, or leaves uncommitted work unnamed.
- **Verification**: `chain next` records each session's commits, re-runs the probes of the units it closed and runs the gates on its change set. The next session gets that report, and checks that the evidence proves the criteria, which no gate can.
- **Budget**: the hook reads the session's context from its transcript, tells it to hand over at 25%, and refuses everything but the handoff at 30%.
- **Groups**: one branch, one group (rail item) at a time. `charter unit start` refuses a unit of a group that has not started; `chain next` then runs `codex exec review --base <group start>` in a worktree of its own at the group's last commit, and launches the next session when it ends. That session answers every finding under `## Review` (fixed, dismissed with evidence, or halt) before the next group starts. A defect found later in an earlier group is fixed forward on the same branch, so nothing is ever rebased.
- **Records**: `chain status` prints the chain's directory; every session's transcript stays (`claude --resume <session id>`).
