# Working on a project under charter, day to day

What to do once charter is installed (`docs/install.md`), for the owner and for the agent. The rules the agent follows are in the project's `.claude/rules/charter.md` (`package/.claude/rules/charter.md`); this page puts them in the order a working day uses them, and says what the owner does that the agent cannot. The commands and outputs quoted below come from a rehearsal of charter 0.4.3 on a scratch repository on 2026-09-24 (in the scratchpad).

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

1. **Open a session.** Read the banner.
2. **Pick or write the unit**, with probes that fail today.
3. **Start it**, and record the failing baseline.
4. **Work** inside its perimeter; record decisions as they are made.
5. **Commit.** The gate runs on every commit, whoever makes it.
6. **Close it**: probes pass, boxes checked, evidence cited, `status: done`.
7. **Report** when someone asks where things stand.

The owner's part runs beside it: commit what only the owner may, approve or refuse what the agent proposed, and once a week read what the gates did (§ What only the owner does, below; `package/.claude/rules/charter.md:28-38`).

## 1. Open a session

In Claude Code, the SessionStart hook gives Claude the full charter index: rules, active unit, decisions, proposals, gate activity. It shows you a short summary in the transcript, starting with this line (`package/.charter/hooks/session_start.py`):

```
charter 0.4.3, track prototype, opt-ins: none. Rules: .claude/rules/charter.md. CLI: python3 .charter/bin/charter --help
```

Claude Code puts a SessionStart hook's plain output into Claude's context without showing it; only its `systemMessage` appears in the transcript (https://code.claude.com/docs/en/hooks, SessionStart). Before 0.4.3 the hook printed plain output only, so a project on 0.4.2 or older shows you nothing. Ask the agent "what did the charter banner say?", or run `python3 .charter/bin/charter config`. The summary, line by line:

- **The track and opt-ins** are the settings every gate reads. `python3 .charter/bin/charter config` prints the same line from a terminal or from another agent (`cmd_config` in `package/.charter/bin/charter`).
- **A line starting `charter/config.json:`** means the config has a key, type or track the gates cannot read. Commits and CI are refused until the owner corrects it (`docs/gates.md` § Config). The agent cannot fix it: the file is the owner's.
- **"The charter git hook is not active in this clone"**: run `python3 .charter/bin/charter setup` once. If it says the clone runs other git hooks, tell the owner instead (`package/.claude/rules/charter.md:11`).
- **The active unit**, when one is set, with its open criteria, or a reminder to start one (`package/.charter/hooks/session_start.py:43-54`).

Codex and other agents get no banner. They read the `AGENTS.md` section the installer wrote, which points at the same rules (`package/AGENTS.md`), and the git hook and CI gate their commits as they gate Claude's.

## 2. Pick or write the unit

One unit per deliverable. To the agent: "start unit `<id>`", or "write a unit for <deliverable>". Both load the `charter-unit` skill (`package/.claude/skills/charter-unit/SKILL.md`), which creates a missing unit from `charter/templates/unit.md`.

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

`unit start` attributes the session's edits and cost to the unit; an engine sets `CHARTER_UNIT=<id>` instead (`package/.claude/rules/charter.md:7`). Before the work, the probe should fail. In the rehearsal:

```
charter/probe block [.taskets/20260924-greet.md]: AC-1 probe failed: ... exited 1: ModuleNotFoundError: No module named 'app.greet'
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
2. Check each `- [x] AC-n` whose probe passed.
3. Under `## Evidence`: the commit SHA, the `path:line` of the change, and the `$ command` lines `charter probe` printed. With `review.required` on, also a `- review:` line that names the independent reviewer and anchors their verdict.
4. `status: done`, and a closing `## Log` line.
5. `python3 .charter/bin/charter unit stop` (`package/.charter/bin/charter:558`).

A done flip without that evidence is refused, in the session and at commit. In the rehearsal, setting `status: done` with the box unchecked and no evidence gave `charter check: 2 blocking` and `Refused.`; with steps 1 to 4 the same commit passed (in the scratchpad rehearsal, 2026-09-24).

The final message of the turn cites the same evidence. A completion claim without a commit, a `path:line` or a `$ command` is blocked once by the Stop hook (`package/.claude/rules/charter.md:25`).

## 7. Report

To the agent: "where does this stand?". The `charter-progress` skill runs (`package/.claude/skills/charter-progress/SKILL.md`):

```
python3 .charter/bin/charter ledger fold      # this machine's ended sessions, with estimated cost
python3 .charter/bin/charter synth --write    # charter/progress.md, refused if its own anchoring check fails
```

The synthesis lists scope, done and accepted units with their evidence, work in progress, blocked units, open decisions and change requests, and cost per accepted unit (`docs/method.md` § The progress synthesis). It is generated; nobody edits it by hand. For a client, send the scope section and the accepted units.

## What only the owner does

The agent prepares these and stops; the owner acts (`package/.claude/rules/charter.md:28-38`):

| When | What | How |
|---|---|---|
| The agent staged an owner-only file (install, upgrade, config) | Commit it | `git commit` from your own terminal, or `CHARTER_OWNER=1 git commit` from a terminal inside Claude Code (`docs/install.md` step 8) |
| A change request is `proposed` | Approve it, or refuse it | Set `status: approved`, `approved_by:` and `approved_on:` in `charter/changes/<id>.md`; until all three are set its paths stay refused (`package/.charter/checks.py:650`) |
| A decision is superseded | Retire the old one | Set its `status: superseded` and `superseded_by:` (`package/.claude/skills/charter-decision/SKILL.md`) |
| A frozen file must grow | Open a split unit, or name an exception | A unit with `kind: split` and the file in `perimeter:`, or a `size_exceptions` entry with a budget, `because:` and `expires:` (`docs/gates.md` § Size) |
| The road changes | Re-plan | Add or reorder items in `charter/rails.md` (`package/charter/templates/rails.md`) |
| A pull request is ready | Push, open, merge | The agent never pushes, opens or merges (`docs/install.md` § Rules for the agent) |

## The owner's weekly look

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
