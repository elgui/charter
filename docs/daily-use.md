# Working on a project under charter, day to day

What to do once charter is installed (`docs/install.md`), for the owner and for the agent. The rules the agent follows are in the project's `.claude/rules/charter.md` (`package/.claude/rules/charter.md`); this page puts them in the order a working day uses them, and says what the owner does that the agent cannot. The commands and outputs quoted below come from a rehearsal of charter 0.4.4 on a scratch repository on 2026-09-25 (in the scratchpad).

## Words used here

| Word | Meaning |
|---|---|
| unit, tasket | One deliverable, as a markdown file in `.taskets/` with its acceptance criteria, evidence and log (`docs/method.md` § The unit of work) |
| probe | A command that proves one acceptance criterion; it fails before the work and passes after (`package/charter/templates/unit.md:24-26`) |
| evidence | Under `## Evidence`: a commit SHA, a `path:line` and the `$ command` lines of the probes; a path or a URL alone is refused (`package/.claude/rules/charter.md:24`) |
| track | `client` when a signed devis (quote) or contract covers the project, `prototype` otherwise (`docs/method.md` § Two tracks) |
| scope | `charter/scope.md`, the summary of the signed devis; client track only (`docs/method.md:9`) |
| rails | `charter/rails.md`, the road a project without a devis is on; optional (`docs/gates.md` § Rails) |
| decision | `charter/decisions/<id>.md`, a choice other code depends on, cited in code as `charter:<id>` (`package/.claude/skills/charter-decision/SKILL.md`) |
| change request | `charter/changes/<id>.md`, work outside the scope, waiting for the owner's approval (`package/.claude/skills/charter-decision/SKILL.md`) |
| opt-in | A stricter setting the owner turns on in `charter/config.json`: `rails.required`, `probes.at_commit`, `probes.in_ci`, `probes.base_must_fail`, `review.required` (`OPT_INS` in `package/.charter/lib.py`) |

## The loop

1. **Open a session.** Read the banner (`package/.charter/hooks/session_start.py`).
2. **Pick or write the unit**, with probes that fail today (`package/charter/templates/unit.md:24-26`).
3. **Start it**, and record the failing baseline (`package/.claude/skills/charter-unit/SKILL.md`).
4. **Work** inside its perimeter; record decisions as they are made (`package/.claude/rules/charter.md:15-19`).
5. **Commit.** The gate runs on every commit, whoever makes it (`package/.charter/githooks/pre-commit`).
6. **Close it**: probes pass, boxes checked, evidence cited, `status: done` (`package/.claude/rules/charter.md:24`).
7. **Report** when someone asks where things stand (`package/.claude/skills/charter-progress/SKILL.md`).

The owner's part runs beside it: commit what only the owner may, approve or refuse what the agent proposed, and once a week read what the gates did (§ What only the owner does, below; `package/.claude/rules/charter.md:28-38`).

## 1. Open a session

In Claude Code, the SessionStart hook gives Claude the full charter index: rules, active unit, decisions, proposals, gate activity. It shows you a short summary in the transcript, starting with this line (`package/.charter/hooks/session_start.py`):

```
charter 0.4.4, track prototype, opt-ins: none. Rules: .claude/rules/charter.md. CLI: python3 .charter/bin/charter --help
```

Claude Code puts a SessionStart hook's plain output into Claude's context without showing it; only its `systemMessage` appears in the transcript (https://code.claude.com/docs/en/hooks, SessionStart). Before 0.4.3 the hook printed plain output only, so a project on 0.4.2 or older shows you nothing. Ask the agent "what did the charter banner say?", or run `python3 .charter/bin/charter config`. The summary, line by line:

- **The track and opt-ins** are the settings every gate reads. `python3 .charter/bin/charter config` prints the same line from a terminal or from another agent (`cmd_config` in `package/.charter/bin/charter`).
- **A line starting `charter/config.json:`** means the config has a key, type or track the gates cannot read. Commits and CI are refused until the owner corrects it (`docs/gates.md` § Config). The agent cannot fix it: the file is the owner's.
- **"The charter git hook is not active in this clone"**: run `python3 .charter/bin/charter setup` once. If it says the clone runs other git hooks, tell the owner instead (`package/.claude/rules/charter.md:11`).
- **The active unit**, when one is set, with its open criteria, or `No active unit. Start one with ...` (`package/.charter/hooks/session_start.py:43-54`).

For the rest of the picture, run `python3 .charter/bin/charter next`, or ask the agent to. It prints the active unit, the road's open items with their units, the next units in the road's order (without `charter/rails.md`, the open units by priority), the units off the road, the done units that lack acceptance, what waits on you, and the gate log over the last 7 days. It writes nothing, not even the gate log, so it is safe to run at any time (`cmd_next` in `package/.charter/bin/charter`, 0.4.4).

Codex and other agents get no banner. They read the `AGENTS.md` section the installer wrote, which points at the same rules (`package/AGENTS.md`), and the git hook and CI gate their commits as they gate Claude's. From the command line, `charter next` gives them the active unit, the road and what waits on the owner.

## 2. Pick or write the unit

One unit per deliverable. To the agent: "start unit `<id>`", or "write a unit for <deliverable>". Both load the `charter-unit` skill (`package/.claude/skills/charter-unit/SKILL.md`), which creates a missing unit from `charter/templates/unit.md`. With no unit in mind, `charter next` lists the open units the road names, in its order, with the ones already started first.

A unit is ready when:

- every line under `## Acceptance` names a probe that can be run, and that probe **fails now**. A criterion that protects behaviour which already works says `(guard)` (`package/charter/templates/unit.md:26`);
- `perimeter:` lists the paths it may touch (`package/charter/templates/unit.md:11`);
- on the client track, `scope:` names an item of `charter/scope.md` or an approved change (`package/.claude/rules/charter.md:9`);
- where `charter/rails.md` exists, `rail:` names an open item of it. Work the road does not name waits until the owner adds a rail item, because that is the re-plan (`package/.claude/rules/charter.md:10`).

Write the criteria before the code. Once the unit has left `next` or `later`, changing a criterion needs a dated `## Log` line saying why (`package/.claude/rules/charter.md:18`).

## 3. Start it

```
python3 .charter/bin/charter unit start <id>
python3 .charter/bin/charter probe <id>
```

`unit start` attributes the session's edits and cost to the unit; an engine sets `CHARTER_UNIT=<id>` instead (`package/.claude/rules/charter.md:7`). The choice is the session's: another session in the same checkout does not inherit it (0.4.15); a choice made outside any session, from a terminal, is inherited by a session with none of its own while the unit is open (`docs/gates.md` § Perimeter). When a probe fails, `charter probe` prints each failed probe's stdout and stderr tails and the paths changed since the unit's base; `--json` gives the same record to a tool. `charter unit show <id>` prints how the unit's perimeter fit the files its commits touched. Before the work, the probe should fail. In the rehearsal:

```
charter/probe block [.taskets/20260925-greet.md]: AC-1 probe failed: ... exited 1: ModuleNotFoundError: No module named 'app.greet'
- `$ python3 -c "from app.greet import greet; assert greet()=='hello'"` → exit 1 (ModuleNotFoundError: No module named 'app.greet')
```

That failure is the baseline: it goes into the unit's `## Log` as the session's first line. A probe that already passes proves nothing about the work (`docs/gates.md` § Done needs evidence).

## 4. Work

- Stay inside `perimeter:`. A file outside it gets a `- <path>: <why>` line under `## Outside perimeter` before the commit (`package/.claude/rules/charter.md:16`).
- When a choice is made that other code will depend on, say "record the decision". The `charter-decision` skill writes `charter/decisions/<slug>.md`, and the code cites it as `charter:<slug>` (`package/.claude/skills/charter-decision/SKILL.md`). Project lessons go there too, as `kind: lesson`, not into personal memory (`package/.claude/rules/charter.md:43`).
- A file over the size limit is frozen. Move code out of it into a new file; letting it grow needs a `kind: split` unit the owner opens (`package/.claude/rules/charter.md:17`).
- Work the client did not buy, or a change to price, dates or what is sold, becomes a change request, not a commit (`package/.claude/rules/charter.md:44`).
- Append a dated `## Log` line whenever something lands or the session stops. The next session resumes from the unit, not from the transcript (`package/.claude/rules/charter.md:19`).
- Subagents read; the parent session writes (`package/.claude/rules/charter.md:49`).

In a Claude Code session, the gates act on each Edit, Write and NotebookEdit before it lands: an out-of-scope path, an owner-only file or a growing frozen file is refused with the override named (`docs/gates.md` § Claude Code hooks).

## 5. Commit

Commit on a branch as usual. The git hook runs `charter check --staged` and ends with one summary line (`package/.charter/bin/charter`, `cmd_check`):

```
charter check: 0 blocking, 0 warning(s) [staged, track prototype, opt-ins: none]
```

A refusal prints one line per finding, each with its `Override:`. Do what the override says. Never use `--no-verify`, and never write a refused file through another tool: CI runs the same checks from a clean clone, and the refusal is the method working (`docs/install.md` § Rules for the agent). The common refusals and their fixes are in `docs/install.md` § When a gate refuses.

## 6. Close the unit

To the agent: "finish the unit" (`package/.claude/skills/charter-unit/SKILL.md` § Finish).

1. `python3 .charter/bin/charter probe <id>`. In the rehearsal, after the work: ``- `$ python3 -c "from app.greet import greet; assert greet()=='hello'"` → exit 0``.
2. Check each `- [x] AC-n` whose probe passed (`package/.claude/skills/charter-unit/SKILL.md` § Finish, step 1).
3. Under `## Evidence`: the commit SHA, the `path:line` of the change, and the `$ command` lines `charter probe` printed. With `review.required` on, also a `- review:` line that names the independent reviewer and anchors their verdict.
4. `status: done`, and a closing `## Log` line (`package/.claude/rules/charter.md:19`).
5. `python3 .charter/bin/charter unit stop` (`package/.charter/bin/charter:738`).

A done flip without that evidence is refused, in the session and at commit. In the rehearsal, setting `status: done` with the box unchecked and no evidence gave `charter check: 2 blocking` and `Refused.`; with steps 1 to 4 the same commit passed (in the scratchpad rehearsal, 2026-09-25).

The final message of the turn cites the same evidence. A completion claim without a commit, a `path:line` or a `$ command` is blocked once by the Stop hook (`package/.claude/rules/charter.md:25`).

## 7. Report

To the agent: "where does this stand?". The `charter-progress` skill runs (`package/.claude/skills/charter-progress/SKILL.md`):

```
python3 .charter/bin/charter ledger fold      # this machine's ended sessions, with estimated cost
python3 .charter/bin/charter synth --write    # charter/progress.md, refused if its own anchoring check fails
```

The synthesis lists scope, done and accepted units with their evidence, work in progress, blocked units, open decisions and change requests, and cost per accepted unit (`docs/method.md` § The progress synthesis). Units done before charter was installed are listed apart, because the done gate never asked them for evidence (0.4.4). It is generated; nobody edits it by hand. For a client, send the scope section and the accepted units.

## Running units in a chain

To the agent: `/charter-chain` with the first unit and the instruction, for example `/charter-chain u1 go with unit 1, and keep going while things go well` (`package/.claude/skills/charter-chain/SKILL.md`). The session you type it in starts the chain and monitors it; the work happens in fresh sessions, one after another:

1. `charter chain start` checks that the tree is clean, no chain runs and a launcher exists, creates the branch `chain/<id>` when you are on main, and opens session 1. With the spawn plugin installed it opens as a tab beside yours, titled `[s] chain <id> s01`; otherwise pass `--launcher headless` (`resolve_launcher` in `package/.charter/chain.py`).
2. Each session gets the rules from `.charter/chain-rules.md` through the hook, your instruction verbatim, and its predecessor's handoff and verification. It verifies that work first, then works unit after unit, and hands over at 25% of its context window. At 30% the hook refuses everything but the handoff (`docs/gates.md` § Chain budget and hand-over). The check runs before each tool, so one tool's output can still carry a session a little past 30%, and a transcript the hook cannot read leaves the session unchecked.
3. `charter chain next`, run by the session, refuses a malformed handoff, records what the session committed, re-runs the probes of the units it closed, runs the gates on its change set, and opens the next session with all of that in its briefing. It closes the tab of the session before (`cmd_next` in `package/.charter/chain.py`).
4. At the end of each group of units (an item of `charter/rails.md`), the chain waits a few minutes for Codex to review the group's commits, in a worktree of its own. If it finds something, the next session answers each finding (fixed, dismissed with evidence, or a halt for you) before the next group starts. Each group is then cleared at a commit you can merge up to (`docs/design/continuous-chain.md` § Groups and their review).
5. The chain ends on its own: `complete` when the road is finished, `halted` when a session needs you (the reason is the question), `stopped` by `charter chain stop`. Two sessions in a row that land nothing halt it, and so does the session limit (12 by default; `chain` in `lib.DEFAULT_CONFIG`, `package/.charter/lib.py`).

The monitoring session tells you each hand-over in one line (`package/.claude/skills/charter-chain/SKILL.md` § Monitor). When the chain waits on you, the session's last message lists your acts, from the `owner.md` it wrote, each with Codex's note on its risk. Run them all with one command, `! python3 .charter/bin/charter owner run`, in the chain's tab, any session of the project, or a terminal: each `sudo` asks for Touch ID or your password there, and the run records what passed (`run` in `package/.charter/owner_acts.py`). Then type `/resume-chain ok`: it closes the `— owner:` lines whose acts passed, and a failed one stays open, its output passed to the next session. `/resume-chain skip <your note>` goes on with every line open, and any note goes verbatim to the next session. Type it in the chain's tab once its session has handed over, or in a session of your own; a session still at work refuses it. A halt is answered the same way, with `/resume-chain <your note>`. The charter hook performs it, and the prompt never reaches the model. Nobody else can resume the chain: `charter chain resume` refuses, the monitoring session only tells you what to type, and "resume" or "continue" in its chat means it goes on monitoring (`docs/gates.md` § The owner's resume). `charter chain status` shows every session's peak context and what it landed, from any terminal. The commits are on `chain/<id>`: review and merge them as usual (merging is yours). `charter chain status` lists each group with the commit it is cleared at; merge up to one with a merge commit or a fast-forward, not a squash, so the later groups still apply. `charter chain report` prints every group's review and its answers as one comment for the pull request you open (`cmd_report` in `package/.charter/chain_groups.py`).

Don't work in the same clone while a chain runs: both sessions would share one active unit (`docs/bugs/2026-10-02-concurrent-sessions-in-one-clone-share-one-active-unit.md`). A folder Claude Code has not trusted stops a new tab at the trust menu; the monitoring session reports `waiting`, and the session starts once you answer it.

## What only the owner does

The agent prepares these and stops; the owner acts (`package/.claude/rules/charter.md:28-38`). Where the project's delegate level allows it, the owner's delegate takes the first rows instead and hands back what it will not take, with its reason, by the waiting session and a Telegram message; a daily digest lists what it did, each with a revert line (`docs/design/owner-delegate.md`):

| When | What | How |
|---|---|---|
| The agent staged an owner-only file (install, upgrade, config) | Commit it | Run the one line the agent handed over, `CHARTER_OWNER=1 python3 <root>/.charter/bin/charter owner commit`, after `!` in the Claude Code prompt or in a terminal; `python3 .charter/bin/charter handover` prints it again (`docs/install.md` step 8) |
| A decision is `proposed` | Adopt it, or reject it | `python3 .charter/bin/charter rule <id> active` (or `rejected`): status, a `## Ruling` line, the index and the commit in one command; `active` first runs the decision's `check:` (`rule` in `package/.charter/owner.py`) |
| A change request is `proposed` | Approve it, or refuse it | `python3 .charter/bin/charter approve <id>` (or `--reject`) sets `status:`, `approved_by:` and `approved_on:` and commits; until all three are set its paths stay refused (`package/.charter/checks.py:650`) |
| A decision is superseded | Retire the old one | `python3 .charter/bin/charter rule <old> superseded --by <new>` sets `status: superseded` and `superseded_by:` (`package/.claude/skills/charter-decision/SKILL.md`) |
| A frozen file must grow | Open a split unit, or name an exception | A unit with `kind: split` and the file in `perimeter:`, or a `size_exceptions` entry with a budget, `because:` and `expires:` (`docs/gates.md` § Size) |
| The road changes | Re-plan | Add or reorder items in `charter/rails.md` (`package/charter/templates/rails.md`); `python3 .charter/bin/charter rail <id> done` closes one in one commit |
| A pull request is ready | Push, open, merge | The agent never pushes, opens or merges (`docs/install.md` § Rules for the agent); at delegate level `open`, the delegate merges the owner's own green PR that `/reviewPR` marked (`docs/design/owner-delegate.md` § Merges) |
| A project should ask the owner less | Lower its delegate level | `CHARTER_OWNER=1 python3 <charter>/bin/charter-pkg fleet --levels <project>=routine|answers|open`, or `charter delegate level <name>` in the project, as the owner; `strict` takes everything back (`docs/design/owner-delegate.md` § Levels) |

## The owner's weekly look

- `python3 .charter/bin/charter next`: under "Waiting on the owner" it lists proposed decisions and change requests, each rail whose units are all finished (close it, or have a unit written for what is left), and owner-only files staged for your commit (`cmd_next` in `package/.charter/bin/charter`). `python3 .charter/bin/charter owner` prints the same queue alone, with HUMAN-ONLY units and acceptance lines only you can close, and the command for each (`--json` for a tool).
- `python3 .charter/bin/charter log`: what the gates refused and warned about over 30 days. A warning that keeps firing on real problems is the evidence for turning it into a gate; one that fires on nothing is noise to remove (`docs/method.md:12`).
- `python3 .charter/bin/charter config`: the track and opt-ins in force. Turn an opt-in on only when the project can bear it (each is described in `docs/gates.md` § Done needs evidence and § Rails):
  - `probes.at_commit` or `probes.in_ci` once the probes run offline and fast; the survey's `--test-cmd` measures that (`personal/claude-home/Skills/CharterAdmin/workflows/Migrate.md:31`);
  - `probes.base_must_fail` once the probes reliably fail before the work (`docs/package.md` § Versioning and upgrade, 0.4.1);
  - `review.required` when an independent reviewer (another model, or a person) checks each unit (`package/.charter/checks.py:380`);
  - `rails.required` once `charter/rails.md` exists and every open unit names a rail (`package/charter/templates/rails.md`).
- A typo in any of these is refused at the next commit and named in the next banner, so a misspelled opt-in cannot stay off unnoticed (`docs/gates.md` § Config).
- `python3 .charter/bin/charter synth`, without `--write`, adds the gate activity the written file leaves out (`package/.claude/skills/charter-progress/SKILL.md`).

## Moving to a new charter version

The personal-layer hook shows you `charter: package X available, Y installed` in the transcript when a project is behind, and names the proposals waiting on you (`personal/claude-home/hooks/charter-personal.py`). Ask the agent to upgrade; it follows `docs/install.md` § Upgrade and stops with the files staged for your commit.
