# The spec step: from a rail to units ready to implement

**Ruled 2 November 2026:** `charter-opt-in` on Owner Desk `oa-cr4y`, which takes D1 to D7 as recommended (`$ owner show oa-cr4y`). The text below is the proposal as ruled.

Proposal, 2 November 2026, for the owner to rule on. Nothing here is built: no package file, config, rail or installed project changed, and this document authorizes no implementation. Trial facts come from two logs kept outside this repository, so they appear as reported claims with their step numbers (E-1, E-2). Upstream facts were read at the tags cited (E-6, E-7).

<!-- charter: opinion -->
**Recommendation:** make Charter the home of the step, as an opt-in recipe rather than a required stage: one `charter-spec` skill, one `charter/templates/spec.md`, and one line in the rules file. Add no status, no rail state and no gate. Draft it now on a branch and use it by pointing a session at the file, then release it to projects only when the criterion in D3 is met. The work happens in a spec unit. Its verdict is recorded on a checkpoint unit, which stops a Run All for a person and shows in `charter owner`. Whoever is about to write a rail's units applies one test; a rail that does not meet it goes straight to units, as it does today.

Why this, and not something heavier or lighter:

- **The value was judgment.** Of 51 things the two trials caught, 20 came from reading and comparing sources and 24 from an independent review by another model family. No gate found a spec defect. Only the git hook ran and no trial tested a start gate, so that zero is not an argument against one; the case against a start gate is in § Verdict.
- **Readiness is not a state worth storing.** It is per unit, it moves with other rails, and r03's written verdict was overtaken the same day. What holds the work is already derived from live units.
- **Neither "write a page" nor "build it now" is enough.** A recipe carries the order and the review to a session that never saw these logs, which a page under `docs/` cannot do. It does not fix probes or citations: those need the small tools in § Defects, which should not wait. And nothing has yet been built from either spec, which is why the release waits.

Confidence: moderate on the home, low on the value until units run. § How we would know says what would change this.
<!-- charter: /opinion -->

<!-- charter: opinion -->
## Decisions for Gui

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Where the step lives | (a) Charter, opt-in: skill, template, rule line, no gate, no stored state. (b) Manual, with a page under `docs/examples/`. (c) Charter, required, with a readiness state | **(a)** |
| D2 | Who it applies to | (a) Any rail that meets the test, on either track. (b) Client track only | **(a)**, with the caveat that no trial covered a non-client project |
| D3 | When it reaches projects | (a) Draft on a branch now, and sessions follow the file. Release on the rule in § How we would know, which needs one non-client rail and r02's built units. (b) Release now. (c) No draft until r02's units have run | **(a)**. The third trial tests whether the recipe travels; only the units test whether it helps. It needs your pick of the rail |
| D4 | Which execution paths it covers | (a) Manual sessions and Run All only, until a chain is trialled on a specced rail. (b) Specify a chain wait now, through `owner.md` and `status: wait` | **(a)**: a checkpoint does not hold a chain, and no trial ran one |
| D5 | Teeth for decisions | All 16 merged decisions have empty `binds:` and `check:`, and on an active one those fields are yours. (a) New decisions carry `binds:` from the proposal, and the 15 active ones get one owner pass when r02's first code lands. (b) One pass now. (c) Leave them | **(a)**. A `binds:` glob on a path that does not yet exist fails nothing; a `check:` must wait for the code |
| D6 | The defects below | (a) Fix now, as their own units, without waiting for D1. (b) Bundle with the skill's release. (c) Leave them | **(a)**: defects 1 and 2 are what the second trial's slips actually need |
| D7 | Retire BMADBridge `spec-to-tasks` | (a) When the skill is released. (b) Keep it | **(a)**; it is in the personal layer and reversible |

Nothing above moves before Charter 0.4.20 is settled, which is its own desk item. The draft sits on a branch and needs no release. A release, its merge and the fleet upgrade are yours (`AGENTS.md:18`). An agent drafts and tests; you rule.
<!-- charter: /opinion -->

## What the two trials measured

Two rails of the payment repository, 1 November 2026: `r03-record-model`, then `r02-foundation`. Both specs reached "not ready" for named reasons, and both were ruled and merged (reported in E-1, E-2).

### Cost and yield by step

Clock times come from `date -u` inside tool calls, and both logs warn that this clock does not measure model effort (reported in E-1, clock note). Reading is counted in Step 2 and comparing in Step 5, and in r02 the two overlapped. A catch is one row of the logs' "What the step caught" tables, 26 in r03 and 25 in r02 (E-8).

| Step | r03 clock | r02 clock | Catches, alone | Shared with | Caught by |
|---|---|---|---|---|---|
| Read the sources (2) | 5 m 41 s | 16 m 58 s | 1, the harness stopping the session's own command | Compare, 1 | Harness, writer (reported in E-1, E-2) |
| Spec unit (3) | 1 s | 1 s | 1 | none | Writer (reported in E-1, Step 3) |
| Clause table (4) | 32 s | 2 m 45 s | 1 | none | Writer (reported in E-2, Step 4) |
| Compare sources, code, measurements (5) | 1 m 15 s | 20 m 55 s | 18 | Review, 2 | Writer (reported in E-1, E-2, Step 5) |
| Decisions under the test (6) | 4 m 00 s | 3 m 38 s | 2 | Review, 1 | Writer (reported in E-1, E-2, Step 6) |
| First review and fixes (7) | 7 m 30 s, review 5 m 08 s | 13 m 50 s, review 8 m 56 s | 18 | Second pass, 3 | codex (reported in E-1, E-2, Step 7) |
| Units (8) | 1 s | 7 m 50 s | 0 | none | (reported in E-1, E-2, Step 8) |
| Second pass and fixes (9) | 2 m 29 s, review 1 m 36 s | 7 m 17 s, review 4 m 02 s | 3 | First review, 3 | codex (reported in E-1, E-2, Step 9) |
| Readiness by hand (10) | 37 s | 4 m 22 s, with cutting the spec | 0 | none | No row, though see below (reported in E-1, E-2, Step 10) |

### Cost as captured

The transcript figures stop at 12:54:56Z in r03 and 15:27:26Z in r02, so they leave out the ruling, the merges and everything after (reported in E-1, E-2, cost tables).

| Measure | r03 | r02 |
|---|---|---|
| Elapsed | 31 minutes to that cutoff (reported in E-1) | 49 minutes to that cutoff (reported in E-2) |
| Claude turns, tool calls | 42, 113 (reported in E-1) | 64, 103 (reported in E-2) |
| Claude output tokens | 126,413 (reported in E-1) | 215,899 (reported in E-2) |
| codex tokens, two passes | 127,895 and 69,493 (reported in E-1) | 174,863 and 94,357 (reported in E-2) |
| Spec words; with decisions | 5,255; 8,306 (reported in E-1) | 2,975; 6,768 (reported in E-2) |
| Decisions, clause rows | 10, 40 (reported in E-1) | 6, 35 (reported in E-2) |
| Work units, acceptance lines | 3, 36 (E-3) | 5, 48, plus a checkpoint's 1 (E-3) |
| Open questions | 17 (E-3) | 11 (E-3) |
| Findings, first and second pass | 13 and 4 (reported in E-1) | 26 and 10 (reported in E-2) |
| First-pass findings the writer caught alone | 0 of 13 (reported in E-1) | 1 of 26 (reported in E-2) |
| Fixes judged wrong or incomplete | 2 of 13 (reported in E-1) | 2 of 26 (reported in E-2) |
| Readiness verdict | Not ready: 5 pass, 3 fail, 1 mixed (reported in E-1, Step 10) | Not ready: 6 pass, 3 fail (reported in E-2, Step 10) |
| Gate refusals | 0 (reported in E-1) | 1, correct and cheap (reported in E-2, Step 9) |
| Owner minutes, upper bounds | At most 6, then about 1 and about 5 (reported in E-1) | At most 235 elapsed on the desk, with two later asks uncounted, against about 27 estimated (reported in E-2) |

Owner minutes are elapsed time on the desk, not reading time, and neither log has reading time (reported in E-2, cost table). The largest single item was not the ruling. It was one ask that sat for at most 140 minutes against about 3 estimated, and it came back to the agent because its options were framed around the wrong person (reported in E-2, Step 18).

### What caught real problems

| Caught by | Catches of 51 |
|---|---|
| Reading and comparing, alone | 20, one of them the harness stopping the session's own command (E-8) |
| Independent review, alone | 24 (E-8) |
| Reading and review, each finding it | 2 (E-8) |
| Writer and review, each finding it | 1 (E-8) |
| Writing decisions under the test | 2 (E-8) |
| Writing the clause table | 1 (E-8) |
| Writing the spec unit | 1 (E-8) |
| A Charter gate | 0 (E-8) |

Three things sit outside the 51 rows. The one gate refusal stopped an unlogged change to a started unit's acceptance, a correct catch of a process slip, not of a spec defect (reported in E-2, Step 9). The owner caught two framing errors by reading: that a question belonged to the customer, and that the work was running from the wrong directory (reported in E-2, Steps 18 and 19). A closing advisor caught citations to files a pull-request reader could not open, and citations that a merge had left pointing at a deleted branch (reported in E-2, closing advisor note and Step 15).

The review findings were not style. Every one in both first passes was logged as real (reported in E-1, E-2, Step 7). They were mostly concurrency and failure-path defects in a design, such as a late event reviving an expired hold, which on code would have meant a migration after a later rail (reported in E-1, Step 7).

The readiness check has no catch row, yet it produced the most useful single result of the first trial: r03 could close and a contract promise still not be deliverable, because three open questions sat past the rail with no default a later rail could ship on (reported in E-1, Step 10).

### What caught nothing

- **The git hook on spec work.** Five commits with no refusal in r03, and one refusal across nine attempts in r02 (reported in E-1, E-2, Limits). This count is weaker than it looks: both sessions ran outside the project, so Claude Code's Charter hooks never fired, and what they would have refused is unknown (reported in E-1, E-2, Limits). No trial had a start gate to exercise either, so this zero is about spec defects only.
- **Comparing the clause table with the units' probes.** All 16 and all 14 table probes had a unit line, so the script found no gap, and its one alarm was a wrong glob (reported in E-1, E-2, Step 10).
- **`charter anchors` on a spec.** On the merged specs it reports 181 of 188 and 122 of 129 claim lines unanchored (E-5). It was built for reports, and `docs/gates.md:127` already keeps it off decisions and scope because their statements are normative. A spec is normative in the same way.
- **The clause table as a finder.** It caught two things in r03 and little else in r02, and both logs value it as a completeness check (reported in E-1, E-2, "Was it worth it"). In r03, two of the four second-pass errors came from it repeating the decisions (reported in E-1, Step 9).

### Limits of this evidence

Two rails, one project, one writer, one model, one day, and the two rails were chosen because they were heavy (reported in E-1, E-2, Limits). No code was written, so no probe has proved anything, and the time each spec saves is "not available until those rails run" (reported in E-1, E-2, cost tables). A rail with less contract text would give different numbers (reported in E-1, Limits).

## What already exists

| Need the trials met | Home today | Fit |
|---|---|---|
| A binding choice, its case and its ruling | `charter/decisions/`, with `proposed`, `ask:`, `recommend:`, `supersedes:` (`package/charter/templates/decision.md:4`) | Worked: 16 decisions filed, ruled, one superseded (E-3). All 16 have empty `binds:` and `check:` (E-3) |
| Provable work | Units (`package/charter/templates/unit.md:22`) | Worked: 84 acceptance lines on work units (E-3) |
| Hold work until a person continues | `gate: human` and `role: epic` in tele-claude (`/home/gui/Projects/tele-claude/services/group_automator.py:559`); `charter owner` lists a `HUMAN-ONLY` unit (`package/.charter/owner.py:233`) | A stop for a person, not a check: Continue clears it without running a probe or closing a line (E-10). Filed in both trials, and no Run All has reached either checkpoint (E-5). `later` holds nothing (`/home/gui/.claude/Skills/Tasket/SKILL.md:374`). A chain reads neither key (E-9) |
| A ruling reaches the owner | Derived asks (`/home/gui/Projects/tele-claude/docs/OWNER_DESK.md:60`) | Worked, but nothing derives from an unmerged branch, and a `do` cannot be linked to its `decide` (reported in E-1, Step 11; E-2, Step 11) |
| Independent review | R2 in `docs/method.md:93`; `/reviewPR`; `package/.claude/agents/charter-reviewer.md:5` | None takes a document with a prompt. The group review runs over a diff and takes no prompt (`package/.charter/chain_groups.py:319`). The prompted read-only form exists only for owner acts (`package/.charter/owner_acts.py:356`) |
| A record that every finding was answered | `check_review`, chain only (`package/.charter/chain_groups.py:164`) | Nothing for a document. Done by hand, then by a unit probe that greps ids (E-3) |
| Clause coverage | Clause ranges in `charter/scope.md`; path matching only (`docs/gates.md:175`) | No ledger. A table in the spec did the job (reported in E-1, Step 4) |
| Design shared by several units | None; `charter/specs/` by convention | Needed an owner scope edit to stop warning (reported in E-2, Step 13) |
| An open question with an owner and a date | None | Went to a board in another repository both times (reported in E-1, Step 13; E-2, Step 17) |
| The recipe itself | None | Hand-written briefs and a hand-written review prompt (reported in E-1, Steps 2 and 7) |

### Why readiness should not be a stored state

The first log lists a readiness state as missing from Charter (reported in E-1, Step 10). The code and the merged output argue against storing one:

1. **Rail status never moved.** Both rails are still `todo` on `main` with their specs merged (E-3). A check attached to a rail move would not have run once. The move itself is an owner verb (`package/.charter/owner.py:548`), so a refusal there would gate the owner, not an agent.
2. **Readiness is per unit.** r03's verdict is a table with one row per unit, each with its own condition (E-3). `STATUSES` in `package/.charter/rails.py:26` works at rail grain.
3. **It moves with other work.** r03's spec on `main` still says r02 has no spec and no units, and still lists `record-postgres` as a binding choice after its supersede (E-3, lines 317 and 72). r02's "Owner edits needed" text went stale the moment the owner's commit landed (reported in E-2, Step 13).
4. **A live answer already exists.** On the merged state, `charter next` and `charter owner` both list the two checkpoints as waiting on the owner, computed from the units (E-5).

## Upstream, confirmed at the tags

| Tool | What it does | What it enforces |
|---|---|---|
| spec-kit v1.2.6, released 2 November | `specify` allows at most 3 `[NEEDS CLARIFICATION]` markers and guesses the rest ([specify](https://github.com/github/spec-kit/blob/v1.2.6/templates/commands/specify.md)); `clarify` asks at most 5 questions, and skipping it only warns ([clarify](https://github.com/github/spec-kit/blob/v1.2.6/templates/commands/clarify.md)) | Prompts |
| spec-kit | `analyze` is strictly read-only, runs only after `tasks`, and recommends resolving critical issues before `implement` ([analyze](https://github.com/github/spec-kit/blob/v1.2.6/templates/commands/analyze.md)) | Nothing: it reports |
| spec-kit | `implement` stops on unchecked checklists and asks, and the user may proceed ([implement](https://github.com/github/spec-kit/blob/v1.2.6/templates/commands/implement.md)); `converge` appends unbuilt work after `implement` ([converge](https://github.com/github/spec-kit/blob/v1.2.6/templates/commands/converge.md)) | A question to the user |
| spec-kit | The default workflow has two human `approve or reject` gates, between specify, plan and tasks, run by an engine that pauses when there is no terminal ([workflow](https://github.com/github/spec-kit/blob/v1.2.6/workflows/speckit/workflow.yml), [gate step](https://github.com/github/spec-kit/blob/v1.2.6/src/specify_cli/workflows/step/gate/__init__.py)) | A real stop, for a person. It judges nothing, and `clarify` and `analyze` are not in that workflow |
| BMAD v6.12.4 | The architecture spine keeps only choices that pass "if two units one level down built this independently, could they choose incompatibly?" ([skill](https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/src/bmm-skills/plan/bmad-architecture/SKILL.md)). This is the test both trials used (reported in E-1, E-2, Step 6) | A prompt |
| BMAD | `lint_spine.py` checks placeholders, ids, required fields and version pins, and always exits 0 ([script](https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/src/bmm-skills/plan/bmad-architecture/scripts/lint_spine.py)); its reviewer gate runs this "cheap deterministic pass first" ([gate](https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/src/bmm-skills/plan/bmad-architecture/references/reviewer-gate.md)) | Reports only |
| BMAD | The readiness gate asks "could a developer implement these epics without inventing decisions nothing records?" and answers PASS, CONCERNS or FAIL ([gate](https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/src/bmm-skills/plan/bmad-sprint-planning/references/readiness-gate.md)) | A prompt. It is in v6.12.4 and no path of that name is on `main`, the V7 preview (E-7) |

The spine and the readiness gate are both in release v6.12.4, not only in the V7 preview (E-7). The spine also says what a spec's structure is worth once code lands: "the code owns this once it exists" ([template](https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/src/bmm-skills/plan/bmad-architecture/assets/spine-template.md)). spec-kit takes the opposite line, with specifications as "the central source of truth" and code regenerated from them ([spec-driven.md](https://github.com/github/spec-kit/blob/v1.2.6/spec-driven.md)).

BMAD's reviewer gate does use separate subagent contexts ([gate](https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.12.4/src/bmm-skills/plan/bmad-architecture/references/reviewer-gate.md)), but neither tool's default flow, as read, calls a reviewer from another model family, which is where 24 of the 51 catches came from (E-6, E-7, E-8). Neither tool checks a spec's quality in code either: the machine parts order the steps, stop for a person, or report (E-6, E-7).

<!-- charter: opinion -->
## Verdict on each candidate home

| Candidate | Verdict | Why |
|---|---|---|
| **Charter, required:** `charter/specs/` as an artifact class, a `ready` state, a check at `unit start` | Ruled out for now | Not because no gate caught anything: no trial tested one. Readiness is per unit and moves (above). A stop for a person already exists at dispatch. The 9 units on r00 and r01 stand without a spec. It would bind 14 repositories, 13 on the prototype track, on two trials and no built unit. A start check stays open by Charter's normal route: a warning, promoted when the log earns it |
| **Charter, opt-in:** one skill, one template, one rule line, no gate | **Recommended** | The method's text belongs with the method, and an installed skill is what reaches a session in a project. It reuses units, decisions, checkpoints and the owner queue, and adds the one thing missing: the recipe |
| **Charter, inside `charter-unit`** | Ruled out | It is installed and sits where units are created (`package/.claude/skills/charter-unit/SKILL.md:10`), so it needs no new skill. But a recipe this long would load at every unit start, and most unit starts are not this. One rule line gives the same prompt |
| **A skill above Charter:** personal or machine layer | Ruled out as the home | A personal skill cannot bind a repository, and this is project method, not one person's habit. The machine layer holds what only the machine can know (`docs/method.md:242`), and it does not travel with a clone. It would reach projects faster, since main checkouts span 0.4.16 to 0.4.19, but that is a reason to run `fleet --upgrade`, not to move the method |
| **tele-claude or an Owner Desk role** | Ruled out; keeps carrying rulings | The step used no automator and no subagent. The desk handles present owner needs and did that job. A project without tele-claude must still be able to run the step. The desk's own gaps (linking `do` to `decide`, marking an ask replaced) stand on their own |
| **Adopt spec-kit** | Ruled out; borrow one thing | It would add `spec.md`, `plan.md`, `tasks.md` and a constitution beside scope, decisions and units, which is the duplication this method exists to avoid. Its caps do not fit: 17 and 11 open questions against a limit of 3 markers, with the rest guessed, when the unknowns were the trials' most valuable output. Borrow the order: `analyze` runs after tasks exist |
| **Adopt BMAD** | Ruled out; borrow two things | Its execution bridge was rejected on evidence, while its planning artifacts stay allowed as inputs (`docs/migration.md:34`), so a project may already feed a spine or a readiness check in. As the home it does not fit. It needs a `_bmad/` install and its own tickets and memlog, and it knows nothing of units, decisions or owner acts. 17 of 37 installs never produced a planning artifact (`docs/report-2026-09-11.md:55`), the payment project has none, and the V7 preview moves these paths. Borrow the "incompatibly" test, already in use, and the readiness question |
| **Leave it as a manual practice** | Ruled out as it stands; the strongest rival | See § The counter-case. It holds until a spec has been built from, which is why D3 keeps the recipe on a branch until then. It loses on reach |

The one home is Charter: the verdict is made in a spec unit and recorded on a checkpoint unit, both in `.taskets/`. A reviewer of another model family reads it, which is codex when Claude writes, and the Owner Desk carries the ruling. Neither hosts the step.
<!-- charter: /opinion -->

<!-- charter: opinion -->
## The recommended step

**The test.** Before writing a rail's units, ask: could two units built separately choose incompatibly on something costly to undo, or does the rail answer to a text owed to someone? If neither, write the units as today. If so, run the step. The owner can always ask for it or waive it.

**The result.** One file, `charter/specs/<rail id>.md`, plus artifacts that already exist: proposed decisions, one spec unit, one checkpoint, and the work units. Its sections are the sources with their versions, the clause map where a binding text exists, pointers to decisions, the design the units share, failure modes, what later rails inherit, open questions, units, review answers, and ready-when per unit. The aim is about 3,000 words, r02's size, with no check on it.

| # | What the session does | r03 | r02 | Traced, or inference |
|---|---|---|---|---|
| 1 | Applies the test | Step 6: two decisions exist only because of it | Step 6: six choices | The test is traced. Using it as the trigger is **inference** |
| 2 | Opens the spec unit and the checkpoint first, from the project's own checkout | Steps 3, 12; catch 25 | Steps 3, 8, 12: no hold had to move; Step 19: wrong directory | Traced |
| 3 | Names each source with its version, then reads before designing | Step 2: no rail names its sources | Step 2; Step 7: wrong version in the brief | Traced |
| 4 | Compares sources, code and live measurements, and writes down each mismatch | Step 5 | Step 5: changed the design before it was written | Traced: 20 catches |
| 5 | Writes a clause map only where a binding text exists, with pointers, not copies | Steps 4, 9 | Step 4; no repeat errors after pointers | Traced |
| 6 | Turns each binding choice into a proposed decision, option surveys inside it, with `binds:` | Step 6 | Step 6 | Traced. `binds:` at proposal is **inference**, from r03 Step 6's gap |
| 7 | Sorts open questions by who can answer them: agent, owner, partner, customer. Each gets a default, or is marked blocking. A blocking choice becomes a proposed decision with `ask:` and `recommend:`, and the checkpoint gets an `— owner: do` line whose probe tests that the decision is ruled, either way. If it was rejected, the unit is rewritten before the owner closes the line, and `do` keeps that judgment from the delegate. A blocking fact someone must supply becomes a `— owner: check` line with a probe of where the answer is recorded. `decisions:` names a decision for reference and holds nothing | Step 5, items 2 to 4 | Steps 16, 18 | Sorting is traced. Placement is **inference**: untested, and it answers the one need with no home. An `— owner: decide` line is not used, because the desk cannot answer it (defect 5) |
| 8 | Writes the units before the review | Step 8; Step 9 saw them only in a narrow pass | Steps 8, 9: 8 of 10 new findings were in units or scripts | Traced. The order is **inference**, and `analyze` has the same order |
| 9 | Has a reviewer of another model family than the writer's review spec, decisions, units and owner scripts, read-only, given the sources and no conclusions, and answers every finding | Step 7 | Step 7 | Traced: with row 10, 24 catches alone |
| 10 | Runs a narrow second pass that judges each answer and reports only new defects | Step 9 | Step 9: found a blocker for about half the first pass's tokens | Traced |
| 11 | Writes ready-when per unit, looking one rail past this one, and places each condition: a condition on the whole group on the checkpoint at its head; a condition on an earlier unit of the group in `depends_on`; an outside condition on a later unit on a second checkpoint in the group; a condition past this rail on that rail | Step 10: model, import and endpoint show the three cases | Step 10 | The check is traced. The placement is **inference** from r03's stale verdict |
| 12 | Files one ruling, with its `do` ask, and says in each option who performs each act | Steps 11, 12 | Steps 11, 12 | Traced |
| 13 | Freezes the spec at the ruling: a dated record, like `docs/review/`. Live truth is in decisions, units and the checkpoint | Spec on `main` is stale | Step 13 | **Inference** |

Rows 9 and 10 are the part not to cut. The writer caught 1 of 39 first-pass findings alone. The spec unit closes when the agent's work is done and the checkpoint stops the group, so `status: blocked` is no longer needed to mean "the agent is finished, the owner is not".

**What a checkpoint does and does not do.** A `gate: human` unit stops a Run All until a person presses Continue. Continue clears the stop without running the probe or ticking the line, and on a run with no worktree of its own it also writes `status: done` to the tasket (E-10), so clearing a checkpoint is a small procedure, in this order:

1. Run the line's probe and confirm the condition.
2. Close the line. At delegate level `strict`, the owner ticks it and commits, which a desk `do` ask can script, as r02's ruling did. Where a delegate level allows it, the agent stages the tick and runs `charter handover`, and the delegate commits after rerunning the probe. A probe that only prints stays the owner's. A desk `pass` records an observation and ticks nothing.
3. An agent adds the evidence and sets the checkpoint unit to `done`.
4. The owner presses Continue.

Neither trial's checkpoint has been cleared, so this path is untested (E-5).

**Order is a Run All rule, not a guarantee.** By default a Run All makes each step depend on the one before it, but an explicit `depends_on` replaces that rule, a run can turn it off, and a dependency outside the run is ignored (E-10). So the recipe has every held unit name its checkpoint and any earlier unit it needs, all in one group. The trials' units set none. In a manual session nothing holds: `charter unit start` does not look at earlier units, so the session reads `charter owner` first. A chain is out of scope until D4 says otherwise.
<!-- charter: /opinion -->

## What is deterministic and what stays judgment

| What | Who holds it | State |
|---|---|---|
| A Run All stops at a human gate | tele-claude automator (`/home/gui/Projects/tele-claude/services/group_automator.py:559`) | Exists. It stops for a person and checks nothing (E-10) |
| What waits on the owner is listed from the files | `charter owner`, `charter next` (`package/.charter/owner.py:233`) | Exists |
| A unit cannot close without checked boxes and evidence | Done gate (`package/.charter/checks.py:389`) | Exists |
| Acceptance changed after start needs a log line | Done gate (`package/.charter/checks.py:439`) | Exists; the one refusal (reported in E-2, Step 9) |
| A decision's status and an owner line are the owner's | Owner-only gates (`docs/gates.md:29`, `docs/gates.md:30`) | Exists |
| A retired decision cannot be cited | Decision gate (`package/.charter/checks.py:642`) | Exists |
| Every clause-row probe has a unit line; every finding id has an answer | Probes in the spec unit, from the template, needing no Charter code (reported in E-1, E-2, Step 10) | Practice, carried by the template |
| A unit relying on a proposed decision is flagged | `check_unit_decisions` (`package/.charter/checks.py:665`) | Gap: defect 3 below |
| A probe's text reaches the runner whole | `PROBE_RE` (`package/.charter/checks.py:32`) | Gap: defect 1 below |
| Is the test met; which sources bind | Writer, owner on dispute (inference) | Judgment |
| Do the sources agree with the code and with each other | Writer, then reviewer (reported in E-1, E-2, Step 5) | Judgment |
| Does a probe prove the deliverable | Reviewer. A live probe that checks a service's name proves nothing about its limit (reported in E-2, Step 9, N7) | Judgment; the gates say so (`docs/gates.md:174`) |
| Is a fix correct | Second pass. `docs/gates.md:189` states the chain's fixes are not reviewed again, and 4 of 39 first-pass fixes were wrong or incomplete (reported in E-1, E-2) | Judgment |
| Could a unit start and finish without guessing | Writer, then reviewer (reported in E-1, E-2, Step 10) | Judgment |
| Rulings, waivers, and what the customer is asked | Owner (`package/.claude/rules/charter.md:28`) | Authority, not a check |

This is the line Charter already draws: the gates "do not judge whether the evidence is true" (`README.md:5`). Upstream draws it in the same place (E-6, E-7).

## Which rails, which projects

The step fits any project whose rails meet the test, on either track (inference: no trial tested this on a non-client project).

- **Track is the wrong switch.** 13 of the 14 repositories running Charter are on the prototype track and one is on the client track (E-4), so a client-only step would reach one project. `docs/review/2026-10-19-client-specificity.md:57` calls commercial relationship and enforcement strength separate questions, and `docs/review/2026-10-19-client-specificity.md:66` proposes decoupling them.
- **The value did not depend on the contract.** r02's scope item has no client acceptance, and 6 of its 8 catches from comparison came from code or vendor documents (inference, from E-2, catch table rows 1, 2, 3, 5, 7 and 9).
- **The test is not a rail count.** 8 of the 14 keep rails (E-4), and a rail whose units need no shared design meets no test. r00 and r01 already hold 9 units and get no spec (E-3). Older units are not automatically sound, though: the reading for r02 found one that had gone stale (reported in E-2, Step 5).

<!-- charter: opinion -->
## The counter-case: leave it manual

*The advocate's case.* Charter's own 2026-10-24 review says not to begin with "a mandatory six-document workflow", and to measure useful outcomes per hour of owner attention first. The trials support it. No gate caught anything. Both specs merged on Charter as it stands. No code has run, so the savings are unknown. r02 asked the owner for at most 235 minutes against 27 estimated, and it produced 6,768 words plus 49 acceptance lines for one rail. The sample is two rails picked for being heavy. `docs/examples/outcome-review.md` shows the precedent: optional guidance, "no new fields, statuses or gates". Charter's promise is "less method, not more", so write a page and stop.

*What survives.* Most of it. This design adds no gate, no status, no field and no required document, retrofits nothing, and leaves every rail that fails the test exactly as it is.

*What does not survive.* The claim that nothing needs doing. Four things slipped between two sessions, with the 280-line first log handed from one to the other, and they do not share a cure:

- **Probes.** "Probes must prove the deliverable" was applied from the start and broken anyway, in N1 and N7. The log's own conclusion is "the lesson needs a tool, not a sentence". N1 is a tool's job (defect 1) and N7 a reviewer's. A skill fixes neither.
- **Citations.** r02 logged a decision citing a file no clone has, at Step 1, then cited that file itself. That is a tool's job too (defect 2).
- **Order.** Units were written after the first review again, and 8 of the 10 new findings were in units or scripts. A recipe can carry this.
- **Sources.** The brief pointed at the wrong version of an agreement. A recipe can ask for versions, but cannot prove one right.

So two of the four need tools, which is why D6 does not wait for D1. The recipe's job is narrower: to carry the order, the review prompt and the sorting of questions to a session that never saw these logs, which are private and uncommitted. A page under `docs/examples/` would not do that, because `docs/` is not in `OWNED` (`bin/charter-pkg:38`) and never reaches a project. The outcome-review precedent is an optional observation; this is a recipe a session must find at the moment it writes units.

*Reconciling with the 2026-10-24 review.* The recommendation there is against a mandatory workflow, and this is opt-in (`docs/review/2026-10-24-ai-native-sdlc-factory-review.md:6`). It says to "link a shared intent or design only when several units need it", which is this step's test (`docs/review/2026-10-24-ai-native-sdlc-factory-review.md:87`). It names a missing responsibility: "who judges the adequacy of the proposed outcome and test, before implementation makes them expensive to change?" (`docs/review/2026-10-24-ai-native-sdlc-factory-review.md:54`). Rows 9 to 11 answer it. Its warning that "multiple documents can preserve the same misunderstanding at greater cost" was measured in r03, which is why the clause map holds pointers. Its first step is a baseline of owner attention and delivered outcomes (`docs/review/2026-10-24-ai-native-sdlc-factory-review.md:172`), which no one has run for these rails, and that is why the release waits for built units.

*Where the counter-case still wins.* Today. Until r02's units run, the recommendation's first stage is a manual recipe on a branch. If owner time per rail stays near r02's, or the units show the spec did not help, it never leaves that stage. § How we would know sets those lines.
<!-- charter: /opinion -->

## What it retires, and what it adds

<!-- charter: opinion -->
Retired: hand-written briefs and review prompts for this step; `status: blocked` as "agent finished"; and, in the personal layer, BMADBridge's `spec-to-tasks` workflow, which `docs/migration.md:36` already lists as unused and whose job this replaces. It adds one file per rail that meets the test, one skill, one template and one rule line. The rules file is 79 lines against a limit of 400, so one line fits. `docs/method.md:244` should say plainly that this is one artifact more for the rails that earn it.
<!-- charter: /opinion -->

## Defects that stand on their own

Findings only; none is fixed here.

1. **A probe is cut at its first closing backtick, silently.** `PROBE_RE` stops there (`package/.charter/checks.py:32`). In the second trial it left one unit unable to ever close (reported in E-2, Step 9, N1).
2. **A cited path that does not exist is invisible.** `charter anchors` flags a `path:line` that does not resolve but passes over a bare path. In a clean clone, a decision citing an absent file reports 0 unresolved (E-5).
3. **A unit can rely on a proposed decision in silence.** `check_unit_decisions` warns on a missing or retired decision only (`package/.charter/checks.py:665`), and `charter unit start` calls it (`package/.charter/bin/charter:820`).
4. **Warnings on paths the gates exempt.** `check_unit_scope` warns on `charter/` and `.taskets/` perimeter entries (`package/.charter/checks.py:136`) that `PERIMETER_EXEMPT` excludes elsewhere (`package/.charter/lib.py:26`). In r03 they fell from 4 to 1 only because a closed unit stops being checked: "they stopped being looked at" (reported in E-1, Step 12).

5. **Outside this repository: an `— owner: decide` line cannot be answered on the desk.** Charter sends it with no options (`package/.charter/owner.py:154`), the detector marks it `free_text: False` and `charter: True` (`/home/gui/Projects/tele-claude/services/owner_desk/detectors/charter.py:212`), and the runner refuses any value not among the options, which are empty (`/home/gui/Projects/tele-claude/services/owner_desk/runner.py:339`). Run in a throwaway desk with that payload, every answer was refused, and `oa-gnhy` is a live card of this kind (E-11).

<!-- charter: opinion -->
## How we would know

r02's and r03's units are already written and unbuilt, so the first evidence comes without any new trial. These are proposed decision rules, not predictions:

- **Release (D3)** when both hold. First, the recipe has run on a non-client rail, and that ruling took at most 30 minutes elapsed on the desk, against at most 6 for r03 and at most 69 for r02. Second, r02's units have closed, fewer than one unit in three rewrote acceptance because the spec was wrong, and no decision was superseded after code for a reason the sources already showed.
- **If that ruling runs long,** cut the review answers and the clause map from what the owner is shown, and run once more. Over the line twice means no release, and the recipe stays on its branch or becomes a page.
- **Promote to a warning, never straight to a gate,** if two rails built without a spec each need a migration or a superseded decision that the test would have flagged. This is Charter's own route: the log promotes a warning (`docs/method.md:12`).
- **Demote to a page** if three rails that meet the test pass without anyone using it, or if the comparison and review together yield under one real catch per rail.
<!-- charter: /opinion -->

## Independent review

Codex, read-only, given the proposal and the sources without the writer's reasoning, returned 12 findings and the verdict "not decision-ready" (E-12). Every citation was checked against its source, and all 12 were accepted. The writer had caught none of them, which matches the trials.

| Id | Severity | Finding | Answer |
|---|---|---|---|
| S1 | Major | An `— owner: decide` line makes a desk card nobody can answer | Confirmed, then proven by a run (E-11). Row 7 now uses a checkpoint line probing a ruling or a recorded answer; defect 5 added (E-12, E-13) |
| S2 | Major | Continue neither checks nor closes a checkpoint | Confirmed. The procedure is now stated act by act, with who performs each, and "worked" withdrawn: no checkpoint has been cleared (E-12, E-13) |
| S3 | Major | The recipe had no chain variant, while promising to hold the group | Confirmed. Made an owner choice: D4 (E-12) |
| S4 | Major | One checkpoint cannot carry every unit's condition | Confirmed. Row 11 places each condition by kind, and order is stated as a Run All rule (E-12, E-13) |
| S5 | Major | 25 was checkouts, not projects | Confirmed: 14 repositories, 13 prototype, 1 client. codex counted 7 with rails; a listing gives 8. Corrected throughout (E-4, E-12) |
| S6 | Major | A skill does not cure what the counter-case cited, and a third document trial does not test value | Accepted, and it changed the recommendation: draft now, release on a stated criterion (D3), defects first (D6). `charter-unit` added as a candidate (E-12) |
| S7 | Major | "No gate caught anything" was used against a gate nobody tested | Accepted. The zero is now limited to spec defects, and the verdict on a start check rests on other grounds (E-12) |
| S8 | Minor | The BMAD rejection cited the old bridge, not the planning workflow | Accepted. The stable planning candidate is now assessed directly (E-12) |
| S9 | Minor | The cost table hid its cutoff | Fixed: cutoffs stated, and the later uncounted asks named (E-12) |
| S10 | Minor | Acceptance counts mixed units and checkpoints | Recounted: 84 on work units, plus 2 checkpoint lines (E-3, E-12) |
| S11 | Minor | A fixed reviewer conflicts with "another model family" | Fixed: the reviewer is chosen relative to the writer (E-12) |
| S12 | Major | A private incident was carried into a public document | Fixed: the incident is gone and the defects are worded generically. E-3 keeps the project's name, which the brief allows as evidence (E-12, E-13) |

The second pass judged 8 answers closed and 4 open, and raised 4 new defects (E-13). All were checked against their sources and accepted:

| Id | Severity | Finding | Answer |
|---|---|---|---|
| N1 | Major | A proposed decision named in `decisions:` holds nothing | Row 7 now holds through a checkpoint line. The third pass found its rejection branch incomplete, and it was reworded (E-13, E-14) |
| N2 | Major | The procedure gave an agent an owner-only tick | Two paths now, by delegate level, with a desk `pass` stated as ticking nothing (E-13) |
| N3 | Major | Unit order is no guaranteed prerequisite | Stated as a Run All rule, and `depends_on` names both the checkpoint and the earlier unit, after the third pass (E-10, E-13, E-14) |
| N4 | Minor | Two rules gave different release answers on owner time | One release rule now (E-13) |

The third pass judged only those eight: 5 closed and 3 open, and the 3 came to two gaps (E-14). Both were reworded in rows 7 and 11. **Those two last edits have had no further review.**

The method worked on this document as it did on the specs, on one more sample: the writer caught 0 of the 16 findings, and the second and third passes found fixes that were incomplete. The first review's S5 and S6 changed the recommendation itself (E-12, E-13, E-14).

### Review of the draft, after the ruling

An independent review of the recipe drafted under the ruling found 13 defects, and all were confirmed (E-15). Two corrected this document: Continue can write the tasket's status, and order holds only by default, so the checkpoint text above was changed. The rest were in the draft, and they are answered on branch `charter-spec-draft`. Most came down to probes that passed for the wrong reason, such as an unfilled template, or a finding with no answer. A second pass closed 9 of the 13 and found no new major defect (E-16). The 4 it left open were probes looser than their claims. They were tightened, and all 17 probe cases then ran through `/bin/sh`, as Charter runs them, with the expected results. That last tightening has had no further review; the trial rail in D3 is its real test.

## Evidence index

- E-1 — Trial log for rail r03, `analysis/2026-11-01-charter-spec-step/trial-log.md`, 1 November 2026 (outside this repository: the owner's private analysis folder, uncommitted). Cited by step.
- E-2 — Trial log for rail r02, `analysis/2026-11-01-charter-spec-step/trial-log-r02.md`, same day (outside this repository: the same folder). Cited by step.
- E-3 — The payment repository's merged output, private, read 2 November: `$ git -C ~/Projects/orqueveaux show origin/main:charter/specs/r03-record-model.md`, `$ git -C ~/Projects/orqueveaux show origin/main:charter/specs/r02-foundation.md`, `$ git -C ~/Projects/orqueveaux show origin/main:charter/rails.md`, and the `record-*` and `foundation-*` files under `charter/decisions/`. Line numbers in this document are lines of those files at `origin/main`.
- E-4 — Fleet, read 2 November: `$ ls -d ~/Projects/*/.charter | wc -l` → 25 checkouts, worktrees among them. Grouped with `$ git rev-parse --path-format=absolute --git-common-dir` → 14 repositories. Each main checkout's `charter/config.json` and `charter/VERSION` gave 13 prototype, 1 client, 8 with `charter/rails.md`, versions 0.4.16 to 0.4.19.
- E-5 — A throwaway clone of the merged state: `$ python3 -B .charter/bin/charter anchors charter/specs/r03-record-model.md` → 188 claims, 181 unanchored. The same on the r02 spec → 129 claims, 122 unanchored. `$ python3 -B .charter/bin/charter anchors charter/decisions/record-postgres.md` → 0 unresolved, with the file it cites absent from the clone. `$ python3 -B .charter/bin/charter next` and `$ python3 -B .charter/bin/charter owner` list both checkpoints as open and waiting on the owner.
- E-6 — spec-kit at tag v1.2.6, published 2026-11-02 (https://github.com/github/spec-kit/releases/tag/v1.2.6). The five command files read match the default branch. `$ gh api repos/github/spec-kit/contents/workflows/speckit/workflow.yml?ref=v1.2.6` shows two gate steps and no `clarify` or `analyze` step.
- E-7 — BMAD-METHOD at tag v6.12.4, published 2026-10-14 (https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.12.4). `$ gh api repos/bmad-code-org/BMAD-METHOD/git/trees/main?recursive=1` returned 790 paths, not truncated, none with `readiness` in its name. Its README calls v6.12 stable and V7 a preview alpha (https://github.com/bmad-code-org/BMAD-METHOD/blob/main/README.md).
- E-8 — Catches counted by a script over the "Where" column of both logs' "What the step caught" tables: 51 rows, with Step 5 alone 18, Step 7 alone 18, Step 9 alone 3, Steps 7 and 9 together 3, Steps 5 and 7 together 2, Step 6 alone 2, Steps 6 and 7 together 1, Step 2 alone 1, Steps 2 and 5 together 1, Step 3 alone 1, Step 4 alone 1 (outside this repository: the counted tables are in E-1 and E-2).
- E-9 — `$ grep -n "gate_reason\|get(\"gate\")" package/.charter/owner.py package/.charter/chain.py package/.charter/chain_groups.py package/.charter/bin/charter`: the package reads these keys for the owner's queue and for `unit show --json` only, not to choose or start a unit.

- E-10 — Run All behaviour. `/home/gui/Projects/tele-claude/services/group_automator.py:5517` defines Continue, and `/home/gui/Projects/tele-claude/services/group_automator.py:5556` marks the step done with no probe, and `/home/gui/Projects/tele-claude/services/group_automator.py:5581` writes `status: done` to the tasket when the run has no worktree. `/home/gui/Projects/tele-claude/services/group_automator.py:4552` states the dependency rule: explicit `depends_on` first, else the previous step if the run has `sequential_deps`. `/home/gui/Projects/tele-claude/services/group_automator.py:4594` ignores a dependency outside the run. `/home/gui/Projects/tele-claude/services/owner_desk/runner.py:387` records a check. `package/.charter/delegate.py:227` refuses a closing line with no probe to rerun. `package/.charter/bin/charter:805` holds only a chain's group boundary at `unit start`.
- E-11 — `$ grep -l "— owner: decide" ~/Projects/*/.taskets/*.md` lists such lines, for example in two other repositories. `$ owner show oa-gnhy` shows a live card with no options and no verb to perform. In a throwaway desk, `runner.answer` on the shape `owner_lines` emits refused `yes`, `done` and a free-text answer with "answer one of" and an empty list, on 2 November. `/home/gui/Projects/tele-claude/tests/test_owner_desk_charter.py:185` adds options and a `perform` that Charter never sends.

- E-12 — First-pass review, 2 November, `codex exec -s read-only` at medium effort, 181,953 tokens (in the scratchpad of this session, not kept). The findings and their answers are the first table above.
- E-13 — Second-pass review, `codex exec -s read-only` at medium effort, 82,578 tokens (in the scratchpad of this session, not kept). It judged the answers to the first pass and reported only new defects.
- E-14 — Third-pass review, same command, 42,379 tokens (in the scratchpad of this session, not kept). It judged S1, S2, S4, S12 and N1 to N4 only.
- E-15 — Review of the draft, 2 November, same command, 75,975 tokens (in the scratchpad of this session, not kept), on branch `charter-spec-draft` (reported in the branch's commit messages).
- E-16 — Second-pass review of the draft, same command, 69,166 tokens (in the scratchpad of this session, not kept).

## Deliverable validation

`$ python3 -B package/.charter/bin/charter anchors docs/proposals/2026-11-spec-step.md` reports 0 unanchored and 0 unresolved. That check covers the form and resolution of citations, not whether they support the claim (`docs/method.md:165`). `$ git status --short` shows this file and one tasket that was already untracked. No package file, config, rail or installed project was changed, nothing was committed, and no branch was switched.
