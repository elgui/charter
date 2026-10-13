<!--
Brief for a Claude Code session in ~/Projects/charter. This is a prompt to RUN, not a report.
Written 2026-10-13 by a tele-claude session (tele-claude at 8ebdd3a, charter at cecb0db), from Gui's picks K11, K12
and K13 of the technology watch on the HERMES paper. The watch report, with the evidence, is
/home/gui/Projects/tele-claude/docs/ext/hermes-dev-primitives-2026-10-13/README.md (outside this repository).

HOW TO RUN IT
  1. cd /home/gui/Projects/charter
  2. Start Claude Code and paste:
     Carry out the brief in docs/briefs/2026-10-13-hermes-failure-record-and-perimeter-fit.md. It is done when the
     brief's "Definition of done" holds.

WHEN IT IS DONE
  You get one branch in a worktree under /home/gui/Projects/.worktrees/charter/, with a release that is tested but
  neither pushed nor merged. The final message gives the commands for both. Nothing is upgraded in any project.
-->

# Charter: a probe failure leaves a record, perimeter fit is reported, and a commit is charged to the right unit

## Why this session exists

Gui read a technology watch on "Harness Engineering for Software Engineering via Modular Executable Dev-Primitives"
(HERMES, arXiv 2610.07832, https://arxiv.org/abs/2610.07832). Its architecture is not for charter, but one mechanism is.
After a failed run, HERMES returns a structured record: the failure tagged by its source, the components it implicates,
the ones missed. Charter keeps almost none of that, though it computes most of it. A second finding came out of
measuring charter's live install in tele-claude: most perimeter warnings there charge a commit to another session's
unit. Gui took three candidates. They are this brief.

Read first: `AGENTS.md` (how this repository is worked), `docs/gates.md` (every gate), `docs/method.md` § "The rules"
and § "The progress synthesis", and `docs/bugs/2026-10-02-concurrent-sessions-in-one-clone-share-one-active-unit.md`.

## The three changes

### K11. A probe failure leaves a record, not a line

What happens today, at `cecb0db`:

- `run_probes` keeps `((r.stdout + r.stderr).strip().splitlines() or [""])[-1][:100]`: the last line of stdout and
  stderr mixed, cut to 100 characters (`package/.charter/checks.py:471`). For pytest that is usually the summary line,
  which names no failing test.
- `cmd_probe` logs `f"{len(lines)} probe(s) of {a.id}"` (`package/.charter/bin/charter`, line 979). The gate log never
  says which acceptance line failed. In tele-claude, all 23 probe/block rows of the week to 2026-10-13 read
  "N probe(s) of <unit>".
- The done gate says "N acceptance box(es) are unchecked" without naming them (`package/.charter/checks.py:403-406`).
- The chain briefing re-runs probes and prints the same one-line tails (`package/.charter/chain.py:518-522`), although
  `package/.charter/chain-rules.md:9` tells the next session to fix a failed probe first.

What to build, deterministically (no model anywhere in it):

1. A record per probe run: acceptance id, command, exit code, duration, and the stdout and stderr tails kept apart, each
   several lines and capped in bytes (choose the caps and say why). A timeout is its own outcome.
2. The paths changed since the unit's base, split into inside and outside its `perimeter:`, when a base is known. Reuse
   the base `run_probes_at_base` already finds (`package/.charter/checks.py:492-530`); do not invent a second notion.
3. The gate log names the failing acceptance ids. The done gate names the unchecked boxes.
4. A machine-readable form, such as `charter probe <id> --json`, so a tool reads records instead of scraping text. 0.4.13
   added JSON verbs; follow their shape.

**Compatibility constraint.** tele-claude's step checker parses the text output of `charter probe` with
`^- `\$ (?P<cmd>.*)` → (?P<result>.*)$` (`/home/gui/Projects/tele-claude/services/checker/core.py:98`, outside this
repository) and builds its refusal from it. Keep that line format byte-for-byte, or add the record beside it. A
tele-claude unit, `20261013-134417-e1b0`, will render the record in its worker refusals once tele-claude upgrades.

### K12. Report how well a unit's perimeter fit its work

What happens today: `check_perimeter` judges one path at a time and records nothing in aggregate
(`package/.charter/checks.py:637-658`). A grep for recall, precision or declared-versus-touched across `package/` and
`docs/` finds nothing.

What to build: for a unit, the paths its commits touched outside its perimeter, and the perimeter entries no commit
touched. Show it in `charter unit show <id>` and as one line per unit in `synth`. It is a report and a warning, never a
gate.

How a reader measured it by hand on tele-claude (reported by a subagent, not re-run here): commits since 2026-09-26
whose subject carries `(unit <id>)`, excluding `taskets:` commits, with `.taskets/`, `charter/`, `.charter/` and
`.claude/` always in, matched with `lib.matches_any`. Across 45 units the mean recall was 0.90 and 213 of 257 entries were
touched. 15 units touched a file outside their perimeter: 25 files, 13 of them tests, 22 of them noted under
`## Outside perimeter`. Its blind spot: untagged commits, and work committed under another unit's tag. Decide how charter
attributes a commit to a unit, and say what the report cannot see.

### K13. A commit is charged to the unit of the session that made it

What happens today: in tele-claude, in the 7 days to 2026-10-13, the perimeter gate wrote 72 "outside the perimeter"
rows and 40 "no active unit" rows, and 56 of the 72 came from the CLI/commit path, not the in-session hook. A reader
found that 44 of the 58 distinct (unit, path) pairs were paths another unit's perimeter covered. For example, units
20261012-1320 and 20260930-0831 were both warned about the exact perimeter of 20261011-1040, which another session had
staged (reported, not re-run here).

The likely cause, to confirm before fixing: `active_unit_source` reads `CHARTER_UNIT`, then the session's own file
`active-<CLAUDE_CODE_SESSION_ID>`, then the checkout-wide `active` file (`package/.charter/lib.py:716-730`).
`charter check` at commit calls `lib.active_unit(root)` without a session (`package/.charter/bin/charter`, line 114), so it
relies on `CLAUDE_CODE_SESSION_ID` being in the environment. A session that has an id but never ran `unit start` then
falls through to the unit another session chose last. Confirm it from the log: tele-claude's
`/home/gui/Projects/tele-claude/.git/charter/log.jsonl` has a `session` field on each row (read it; never write it).
Check also whether git passes `CLAUDE_CODE_SESSION_ID` to the hook in every way a session commits.

What to build: the fix that the evidence supports, for example "a session with an id and no unit of its own is not
charged to the checkout's unit". Update the 2026-10-02 bug file with what was found and its new status, as a dated
addition, because history is not rewritten.

## How to work

- **Never switch branches in `/home/gui/Projects/charter`.** On this machine `~/.claude` links into that checkout
  (`personal/README.md`), so a branch switch there changes the running hooks of every session at once. Work in a new
  worktree: `git -C /home/gui/Projects/charter worktree add /home/gui/Projects/.worktrees/charter/<branch> -b <branch>`.
- **This brief is untracked in the main checkout.** Once your worktree exists, move it (`mv`, not copy) to the same path
  in the worktree and make it your branch's first commit. A copy left behind would block the merge, because git refuses
  to overwrite an untracked file.
- **Pick the version.** Branches and worktrees for other releases exist (`git worktree list`; `owner-delegate-0.4.14` is
  one). Take the next version no branch claims, and name the branch after it. If you find that an in-flight release
  conflicts with yours, say so in the final message; do not rebase someone else's branch.
- **A change to `package/` is a release.** Follow `AGENTS.md` § "Working on charter itself": the version in the three
  places, the version lines in the docs, an upgrade note in `docs/package.md`, and `docs/gates.md` updated for every
  gate whose output changed.
- **Tests first, per change.** Write each test before the code it covers, in a new test module named after the release,
  and add it to the module list in `AGENTS.md`. Run the full list as `AGENTS.md` says, in the background, about 15
  minutes. This box is memory-constrained: run it under a memory cap, for example
  `systemd-run --user --scope -p MemoryMax=4G -- <the command>`.
- **Claims carry sources.** Check every document you change with `python3 package/.charter/bin/charter anchors <file>`.
- Log as you go in `docs/session-log.md` (append a dated section; do not edit old ones).

## What you do not do

- Push, merge, or open a pull request. Those are Gui's (`package/.claude/rules/charter.md:44`).
- Upgrade charter in any project, including tele-claude. Projects pick a release up through `docs/install.md` § Upgrade.
- Edit any file in `/home/gui/Projects/tele-claude`. You may read it for evidence.
- Add a model call to any gate. A gate is a rule (tele-claude's decision `gates-are-rules-not-models`).
- Set `CHARTER_OWNER`, or pass `--no-verify`.

## Definition of done

1. One branch in a worktree under `/home/gui/Projects/.worktrees/charter/`, committed, with K11, K12 and K13, each with
   its tests, and the release files bumped.
2. The full test list passes, run once after the last commit, and the final message quotes the count line and the
   absence of `^FAIL:` and `^ERROR:`.
3. `docs/gates.md` and `docs/package.md` describe the new output and the upgrade note; `charter anchors` passes on every
   document changed.
4. The 2026-10-02 bug file carries a dated addition with the confirmed cause and the fix.
5. The final message gives: the branch and its head SHA, one line per change, what was measured to confirm K13's cause,
   anything decided that Gui should know, and the commands Gui runs to push and merge.
