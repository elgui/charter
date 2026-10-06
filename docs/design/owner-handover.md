# The owner's line (0.4.12)

When an install, an upgrade or `charter handover` leaves an owner-only change staged, the owner gets one short line to run instead of a command an agent assembles. The line is the same in a Claude Code prompt, after `!`, and in a terminal (`owner_line` in `package/.charter/lib.py`):

```
CHARTER_OWNER=1 python3 /path/to/project/.charter/bin/charter owner commit
```

## What was asked

On 2026-10-06 leCRM was upgraded from charter 0.4.8 to 0.4.11 in a worktree (https://github.com/elgui/lecrm/pull/99). The upgrade merged hooks into `.claude/settings.json`, which is the owner's file. The installer's block gave the owner `! CHARTER_OWNER=1 git -C <worktree> commit -m 'charter 0.4.11' -- <17 paths>` (`lib.handover` in `package/.charter/lib.py` at 0.4.11). Getting that commit made took three round trips (operator report from the leCRM session, 2026-10-06):

1. The agent handed over a `bash -euo pipefail <<'EOF'` block. Pasting it was unreliable (operator report, 2026-10-06).
2. The auto-mode classifier refused the agent's own `CHARTER_OWNER=1 git commit`, "judged dangerous", even after the owner wrote "do it yourself". On 2026-09-25 that phrase had been enough (`personal/claude-home/Skills/CharterAdmin/SKILL.md:74` at 0.4.11).
3. What worked: a scratchpad script without the switch, run by the owner as `CHARTER_OWNER=1 bash <path>` (operator report, 2026-10-06).

The owner's words: "I'm tired of copy-pasting blocks, because the copy-paste here is faulty." The same day they rewrote their global rule for commands handed to them (outside this repository: `~/.claude/CLAUDE.md` § Commands Handed to the User). In short: the agent does the work first; what is truly the owner's goes into a script; the owner gets one line that runs it; the owner-only switch appears on the owner's line only, never in a file an agent writes (reported in `~/.claude/CLAUDE.md`, 2026-10-06).

## Choices

| Question | Chosen | Why | Weighed and not taken |
|---|---|---|---|
| What the owner's line runs | A verb of the project's own engine, `charter owner commit` (`_owner_commit` in `package/.charter/bin/charter`), which commits the handover recorded in the git directory | Nothing is generated to run: no agent writes a script, so there is nothing to `bash -n` and nothing that could carry the switch. The engine that runs is the one the commit installs | A script the tools generate under the git directory or a scratchpad (code an agent's tool wrote, run blind by the owner). Folding the commit into `charter owner run` (its contract is a chain's `owner.md`: a pinned review, `owner-run.json`, then `/resume-chain ok`; an install or an upgrade has no chain) |
| Who sets the owner switch | The owner, on the line: `CHARTER_OWNER=1` in front. The verb never sets it | Two layers keep holding against an agent, as at 0.4.11. The hook denies any Bash command that names the switch (`package/.charter/hooks/chain_gate.py`), and the classifier refused it on 2026-10-06. Under both, the pre-commit gate refuses an owner-only change made inside Claude Code without the switch (`check_owner_only_staged` in `package/.charter/checks.py`). A verb that set the switch itself, as `rule`, `approve` and `rail` do (`_commit` in `package/.charter/owner.py`), would leave the hook's text match as the only refusal. A script file sidesteps that match, and the hooks of a session that just installed charter load only "normally" (https://code.claude.com/docs/en/hooks-guide). It matches the owner's rule word for word | The verb sets the switch, and the line has none (shorter, and the same line works without it in a terminal; but it opens for the commit the hole that issue #2 names for the ruling verbs) |
| Where the handover lives | `<git dir>/charter/handover.json`, per worktree: the branch, the message, the paths, and each path's staged blob. It is data, not a command, and holds no switch. The commit removes it | Never in the tree, so never committed. The git directory is where every per-worktree record already lives (`local_state_dir` in `package/.charter/lib.py`). A scratchpad belongs to one session, and the owner may run the line from another | Recording nothing and committing whatever is staged when the owner runs the line (the owner's own staged work would slip in, which the 0.4.5 pathspec was there to stop) |
| Which checkout the line commits | The one that holds the engine the line names, by absolute path. The verb takes its root from its own location, not from the directory it runs in | leCRM's upgrade was in a worktree while the session sat in the main checkout. A relative `.charter/bin/charter` would have run the main checkout's 0.4.8 engine | A relative path, as `charter owner run` prints (`RUN_CMD` in `package/.charter/owner_acts.py`). A chain's owner runs that in the chain's own tree |
| What the owner sees before it commits | The message, the path count, the paths changed since the handover, and anything else staged that stays out. Then git's own output, with the gate's lines | The owner may edit a handed-over file before committing: install step 8 asks for the `owner` value in `charter/config.json`. That is reported and committed as it is now, as the 0.4.5 pathspec commit already did (https://git-scm.com/docs/git-commit#Documentation/git-commit.txt---only) | Refusing any change since the handover (it would refuse the edit step 8 asks for) |
| Several projects (`charter-pkg fleet --upgrade`) | One line for the whole fleet: `CHARTER_OWNER=1 python3 <charter>/bin/charter-pkg fleet --commit`. It runs each project's `owner commit` for the handovers that fleet recorded (`do_fleet_commit` in `bin/charter-pkg`) | The line stays the same length however many projects wait. The switch reaches each project's commit from the owner's line, through the environment | One `owner commit` per project joined with `;` (it grows with the fleet). Committing every handover found, whoever recorded it (a stale handover from an earlier session would be committed unseen) |
| Uninstall | The pathspec `git commit` stays, on one line with the switch in front (`handover` in `package/.charter/lib.py`) | The engine has left the tree by the time the owner commits, so no verb is there to run | — |

## The shape

```
agent: charter-pkg install|upgrade, or charter handover      (stages; never commits an owner-only change)
         └─ handover.json in <git dir>/charter/: branch, message, paths, staged blobs
         └─ prints: Waiting on the owner … then the owner's line, alone on the last line
owner: ! CHARTER_OWNER=1 python3 /abs/project/.charter/bin/charter owner commit     (or the same, in a terminal)
         └─ refuses: no handover here; another branch; a chain session; inside Claude Code without the switch
         └─ git commit -m <message> -- <paths>; the pre-commit gate runs; the switch lifts only the owner-only check
         └─ removes handover.json; prints the commit
```

## Each requirement and what holds it

| Requirement | What holds it |
|---|---|
| The owner gets one short line, the same in Claude Code and in a terminal | `owner_line` and `handover` in `package/.charter/lib.py`: the line is printed last, alone, unindented, so a triple-click copies it whole (the 0.4.10 standard, `docs/bugs/2026-10-05-owner-acts-not-paste-ready.md`) |
| No file an agent writes holds the switch | `record_handover` in `package/.charter/lib.py` writes data only: no command and no switch (`tests/test_owner_commit_0_4_12.py`) |
| What is committed is what was handed over | `_owner_commit` in `package/.charter/bin/charter` commits the recorded paths by pathspec with the recorded message. It refuses on another branch, and names what changed since the handover and what is staged but not handed over |
| An agent never commits an owner-only change | The verb does not set the switch. Without it, inside Claude Code, the verb refuses, and the pre-commit gate would refuse too. The hook denies a Bash command that names the switch or runs `charter owner commit` (`OWNER_RUN_RE` in `package/.charter/hooks/chain_gate.py`). `_owner_commit` refuses in a working chain session |
| The line commits the right checkout from any directory | `cmd_owner` in `package/.charter/bin/charter` gives `_owner_commit` the checkout of the engine's own path, which `owner_line` in `package/.charter/lib.py` prints in full (`tests/test_owner_commit_0_4_12.py`, class `Worktree`) |
| One line for a fleet | `do_fleet` in `bin/charter-pkg` records each waiting project's handover (`by: fleet`). `--commit` runs each one's `owner commit` |
