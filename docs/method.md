# Charter: a working method for client projects run with agents

Version 0.4.1. Package layout and commands: `docs/package.md`. Hook and gate reference: `docs/gates.md`. Migration: `docs/migration.md`.

## The method on one page

A project keeps one small written charter that every unit of work cites and that machines check:

- **`charter/scope.md`** says what is sold, what is not, and what is assumed. It is a summary of the signed devis. Anything outside it becomes a change request that the owner approves.
- **`charter/decisions/*.md`** are the design decisions. Code that depends on one carries a `charter:<id>` marker, and a decision can carry a runnable check. A retired decision cannot be cited.
- **A tasket in `.taskets/`** is the unit of work. It cites a scope item, declares the paths it may touch, lists acceptance criteria as runnable probes, and carries its own evidence and log. Its status cannot flip to `done` without evidence.
- **Gates** run in three places: Claude Code hooks (guidance and early blocking in a session), git hooks (blocking at commit, whichever agent commits) and CI (blocking at merge, from a clean clone). Five gates are hard, and the files and fields that define them are the owner's: an agent's edit of them is refused and CI checks who committed them. Everything else warns and is logged, and the log is what promotes a warning to a gate.
- **`charter synth`** produces a progress report from the repository state on demand. Every line of it carries an anchor, and it refuses to publish if its own anchoring check fails.
- **`charter/ledger.jsonl`** records tokens and estimated cost per session and per unit, priced per model. Cost per accepted result is computed from it, with acceptance read from the unit when the synthesis runs.

The doctrine behind it, from the video and its primary sources (`docs/report-2026-09-11.md` § Map): none of the rules says who commands; each says where the decision is written and who settles it when it gets stuck. For a person working alone with agents, "who settles it" is either a reviewer that wrote neither side, or the owner.

## What the evidence said the method must solve

The mapping lanes (`docs/report-2026-09-11.md` § Map, evidence index E-1..) found one dominant failure and three secondary ones:

1. **"Done" is fakeable.** Nearly every recorded house-memory lesson is about a false done claim or a silent routing failure, none about a false negative (`~/.claude/projects/-home-gui-Projects-tcv2/memory/supervised-run-end-of-run-verification.md`; lane 1 § 7). A karaokay tasket is `status: done` with all nine acceptance boxes unchecked (`~/Projects/karaokay/.taskets/20260511-3032-youtube-url-import.md`). Two of 23 projects with taskets have no acceptance criteria at all (chauvet, orqueveaux; lane 1 § 1c).
2. **Nothing enforces anything on taskets.** No hook in `~/.claude/settings.json` references `.taskets/` (lane 2 § A2). The only mechanical gate is tcv2's git-evidence check, which tests that *something* changed, not that the criteria were met (`~/Projects/tcv2/services/git_evidence.py:563-713`).
3. **Governance documents grow without bound and decisions get lost in them.** tcv2's `CLAUDE.md` is 873 lines with twenty D-rulings woven inline, amended in place, and a gap at D6-D11 (lane 1 § 3). orqueveaux tracks progress in 33 tracked root markdown files, 14 of them per-phase, most stale since December 2025 (lane 6 § 2).
4. **Scope has no home in the repo.** orqueveaux's devis and proposal live in the vault, deliberately gitignored (`~/Projects/orqueveaux/.gitignore`, trailing block; lane 6 § 8). No tasket cites what was sold.

BMAD is not part of the execution problem: its execution bridge never ran anywhere (no `story-brief.md`, no `pre-seeded-isc.md` in any project; lane 3 § 4), and its planning artifacts are write-once by nature (1 to 4 commits each; lane 3 § 1). Party mode and `bmad-quick-dev` are used standalone and stay available on the prototype track.

## Artifacts and their owners

| Artifact | Path | Written by | May change it | Read by | Kept small by |
|---|---|---|---|---|---|
| Scope | `charter/scope.md` | Owner, from the signed devis | Owner only: an agent's Edit or Write is refused, CI checks the author; agents propose via change request | Every unit (`scope:`), scope gate, synth | One item per sold deliverable; governance size limit (400 lines, 32 KiB) |
| Rails | `charter/rails.md` | Owner, from the roadmap | Owner only: adding an item is the recorded re-plan | Every open unit (`rail:` or `roadmap:#<id>`), rails gate, synth | One row per item on the road |
| Change request | `charter/changes/<slug>.md` | Any agent or the owner | Status, `approved_by`, `approved_on`, and the paths of an approved one, only by the owner | Scope gate, synth | One file per request; approved ones fold into scope at the next devis |
| Decision | `charter/decisions/<slug>.md` | Whoever settles it (agent for local design, owner for commitments) | Status, `superseded_by`, and the `check:` and `binds:` of an active one, only by the owner; superseded by a new file | Decision gate (`charter:<id>` markers, `check:`), agents at session start (index), synth | One decision per file and one file per id; `expires:` and `because:` required; the index is generated, never hand-edited |
| Unit of work | `.taskets/<id>.md` | The Tasket skill, a board, or an engine | The session that owns it (one writer) | Both tasket engines (unchanged keys), done gate, perimeter gate, synth | One deliverable per unit; the log section is append-only and dated |
| Log and memory | `## Log` in the unit; lessons as decisions with `kind: lesson` | The owning session | Append only | Next session on the same unit (resume reads the unit, not the transcript) | Evidence collapses to anchors on close; lessons carry `expires:` |
| Ledger | `charter/ledger.jsonl` | `SessionEnd` hook and `charter ledger` | Nobody by hand (an Edit or Write is refused) | `charter synth`, the owner | One record per session, folded per unit |
| Legacy list | `charter/legacy-taskets.txt` | The installer, from the taskets it finds without acceptance | Anyone removes an id; only the owner adds one | Done gate | One id per line |
| Rules | `.claude/rules/charter.md`, `AGENTS.md` section | The package (versioned) | The package upgrade; local additions go in a separate rules file | Claude Code, Codex, pi | Governance size limit; anything project-specific is a decision, not a rule |
| Progress synthesis | `charter/progress.md` (generated) | `charter synth` | Nobody by hand | Owner, client reporting | Regenerated from state; never edited |

The single-writer rule from the surgical team applies per artifact: a unit has one owning session, a decision has one file, the scope has one owner. Parallel agents read; one hand writes.

### The unit of work: tasket plus an ISA-like body

Taskets stay the unit because two engines already dispatch them and the format round-trips unknown keys (`~/Projects/tele-claude/services/project_tasket_reader.py:230-234` copies an allowlist and leaves the rest on disk; `~/Projects/tcv2/services/tasket_ops.py:319-363` touches only named keys). The method adds only optional keys, so an existing tasket stays valid and an engine that ignores the new keys still routes correctly. Comments go on their own lines: tcv2's reader keeps everything after the colon, so `status: done  # x` reaches its runner as the value `done  # x` (`~/Projects/tcv2/services/tasket_routing.py:707-732`), and charter warns on such a line.

```yaml
# the scope item or approved change request this unit delivers
scope: S2
# paths this unit may touch without a note
perimeter: [app/services/**, tests/unit/**]
# decisions this unit relies on; `charter check --decisions` warns when one is retired
decisions: [payment-idempotency-store]
# work | split; a split unit lets a frozen file grow while it is split, and the owner opens it
kind: work
```

The done gate is the one place the method changes what an engine can do with `status`: a done flip on a tasket without checked acceptance and evidence is refused at commit, so an engine that commits through the git hook sees the refusal (`~/Projects/tcv2/services/tasket_ops.py:708-718` rolls the board back). The installer lists the taskets it finds without acceptance in `charter/legacy-taskets.txt`; those close with a warning, so an engine keeps closing the work that predates the method, and every tasket written after it is gated. The checklist is `## Acceptance`, or `## Done When`, the heading the Tasket skill writes for the same thing; a tasket with only `## Done When` is still listed as legacy at install, and is read like `## Acceptance` once its id leaves the list.

The body carries what upstream PAI's ISA carries and taskets lacked (lane 2 § C):

```markdown
## Acceptance
- [ ] AC-1: /health returns 200 with `{"ok": true}` — probe: `pytest tests/unit/test_health.py -q`
- [ ] AC-2: (guard) no new file over 800 lines — probe: `charter check --size`

## Evidence
- 3f2a9c1 adds the endpoint (app/routers/health.py:12-30)
- `$ pytest tests/unit/test_health.py -q` → exit 0 (2 passed) at 3f2a9c1

## Log
- 2026-09-11 14:20 started; baseline `pytest -q` → 40 passed
- 2026-09-11 15:02 AC-1 closed at 3f2a9c1

## Outside perimeter
- app/settings.py: added HEALTH_PATH because the router reads it (kept to one line)
```

An acceptance line is a binary probe: one command whose exit code or output answers yes or no. If the probe cannot be named, the criterion is not ready. `charter probe <id>` runs a unit's probes and prints the `$ command` lines for `## Evidence`. Once the unit leaves `next` or `later`, removing or rewriting a criterion needs a `## Log` line saying why, in the same change. This is upstream ISA's rule (`LifeOS/install/LIFEOS/DOCUMENTATION/ISA/ISAFormat.md:606-608` at commit 5e2f2e8) and tcv2's AC2 (`~/Projects/tcv2/.claude/skills/Tasket-2/SKILL.md:297-341`), adopted as is. Long-running work is carried by the `## Log` section: a resumed session reads the unit, not the transcript. No separate ISA document is introduced; one file per unit is enough at this scale, and the hierarchy upstream built for huge builds went unused there (0 of 472 archived ISAs, `ISAHierarchy.md:7`).

Why not the ISA format itself: it is a personal-layer format (`~/.claude/LIFEOS/MEMORY/WORK/`), it carries seventeen sections, and its parser is private. The tasket keeps the engines and adds the three sections that matter.

## The rules

One table, in the shape the brief asked for so it can be set beside the Astra session's later.

| # | Rule | Decisions written in | Arbiter when stuck | Mechanism | Hard gate or warning | Compliance measured by | Cost |
|---|---|---|---|---|---|---|---|
| R1 | Every design decision is written down, and code that depends on it cites it (video rule 1) | `charter/decisions/<id>.md`, `charter:<id>` markers in code | Owner, or a reviewer on another model for local design | `.charter/bin/charter check --decisions` in pre-commit and CI; `PreToolUse` warns on edits to bound files without the marker; `check:` commands run | **Hard** at commit and CI when a cited decision is retired or a `check:` fails; warning when a bound file lacks its marker | Log entries `gate=decisions`; count of markers per bound file | One marker line per file; a `check:` command per decision that has one |
| R2 | A conflict between two changes is settled by a party that wrote neither (video rule 2) | The decision record the settlement produces | A reviewer agent on another model or harness (`codex exec`), then the owner | `charter-review` agent definition; `/reviewPR` already does this with Codex (`~/.claude/commands/reviewPR.md`) | Warning: the method asks for it on every merge to `main`; not mechanically enforced because the merge itself is the owner's act | Decisions with `arbiter:` set; PRs with a review comment | One review session per merge |
| R3 | A file past the size limit is frozen until an independent unit splits it (video rule 3) | The split unit (`kind: split`), or a named exception with `because:` and `expires:` | The owner, by creating the split unit or the exception (an agent's Edit or Write of one is refused) | `PreToolUse` denies a growing edit past `limits.file_lines`; pre-commit refuses a staged file that grew past it; CI refuses a file that grew past it in the change set; an open split unit that names the file unfreezes it, and a live `size_exceptions` entry in the owner-only config gives it its own budget | **Hard** | Log `gate=size`; files over the limit in `charter check --size --strict` | Limits in `charter/config.json`: lines for code, lines and bytes (32 KiB) for the configurable governance set; exemptions by glob; owner-named exceptions per path with a budget, `because:` and `expires:` |
| R4 | An agent may work outside its perimeter if it leaves a note saying why (video rule 4) | `## Outside perimeter` in the unit | Owner, at review | `PostToolUse` warns on an edit outside the active unit's `perimeter:`; pre-commit refuses to land such a path without a note | Warning in session, **hard** at commit | Log `gate=perimeter`; notes per unit | One line per excursion |
| R5 | Each unit keeps its own log, and an index of decisions is handed to every new session (video rule 5) | `## Log` in the unit; `charter/decisions/INDEX.md` (generated) | Nobody: append only | `SessionStart` hook prints the active unit, its open criteria, and the decision index | Warning: when a commit landed in a turn and the unit's log did not move, the Stop hook tells Claude once (`additionalContext`) | Log line count per unit vs commits | Seconds per session; one short continuation per reminder |
| R6 | The scope is the signed devis, and everything outside it is a change request to the owner | `charter/scope.md`, `charter/changes/<id>.md` | Owner only | `PreToolUse` denies edits under an out-of-scope path without an approved change, and an agent's edit of the scope itself; pre-commit and CI refuse them; `charter check --scope` validates that every open unit cites a scope item and reports what makes the scope file fail open | **Hard** | Log `gate=scope`; change requests per quarter | Writing the scope once per devis |
| R7 | Commitments go up to the person who signs. A commitment is anything that changes an external obligation: what is sold, price, dates, deployment, production data or schema, purchase or budget, public release, another person's work, widening a permission, merging into main | `charter/changes/<id>.md` with `status: approved` and `approved_by:` for what is sold, price and dates; the owner's word in the session for the rest | Owner | Only the owner's approval flips a change to approved; agents can only propose. Mechanically: `charter check` refuses `approved` without `approved_by` and `approved_on`, and such a change unlocks nothing; `PreToolUse` refuses an agent's edit of the approval fields; CI refuses them from an author who is not `owner`. Widening a permission is gated where it is a file (`.claude/settings.json`, owner-only). The other operational commitments are guidance in the rules file: no gate sees a deployment or a merge | **Hard** in form and in session for change requests and settings; warning (the rules file) for the operational items; identity is not provable on a machine the agent shares with the owner (stated limit) | Changes approved per period | Nil |
| R8 | Shared memory has an owner and an expiry; a habit becomes a rule only by decision | Lessons as decisions with `kind: lesson`, `owner:`, `because:`, `expires:` | Owner | `charter check --memory` warns on lessons past expiry or lacking `because:`; the rules file forbids writing project-binding lessons into personal auto-memory | Warning | Expired lessons count; lessons without a case | One paragraph per lesson |
| R9 | Done means accepted: acceptance probes ran and passed, and the evidence resolves | `## Acceptance` and `## Evidence` in the unit | The done gate; the owner on dispute | `PreToolUse` refuses a tasket edit that sets `done` without checked criteria and evidence naming a commit or a `$ command` run; pre-commit and CI refuse the same for units that close in the change set; with `probes.at_commit` or `probes.in_ci` the probes are re-run; Stop hook blocks once a done claim without a commit, `path:line` or run | **Hard** | Log `gate=done`; units done vs units accepted in the synthesis | The probes themselves |
| R10 | Every deliverable is anchored: a report, a PR description, a synthesis, documentation | The deliverable itself | Nobody: the check is mechanical | `charter anchors <file>` in CI on `charter/progress.md`, `docs/progress*.md`, `docs/report*.md`; `charter anchors --pr` on the PR body | **Hard** in CI for the listed paths; warning on the PR body and elsewhere | Unanchored claim count per deliverable | Minutes per deliverable |
| R11 | Cost per accepted result is recorded per unit | `charter/ledger.jsonl` | Nobody | `SessionEnd` hook records tokens per model; `charter ledger` folds per unit and adds human time; `charter synth` reads acceptance from the unit | Warning (a session without a ledger record is logged) | Records per session; cost per accepted unit with its coverage, and sessions after the first done, in `charter synth` | Nil |
| R12 | Effort goes where a real wait disappears; do not staff a step whose inputs still move | The unit's `## Log` states why a subagent was used | Owner | Guidance in the rules file, § Subagents: subagents read and the parent writes, and a subagent that can run Bash is not read-only; the ledger shows subagent cost per unit | Warning | Ledger: subagent cost share per unit | Nil |

Hard gates are R3, R6, R7 (form), R9 and R10 in CI, plus R1 in its retired-decision and failing-check forms, and the owner-only changes that guard them (`docs/gates.md` § Owner-only changes). Everything else warns and is logged to `log.jsonl` in the git common directory.

## The hard gates and why a warning would not do

| Gate | Failure it prevents | Why a warning is not enough | Claude Code hook | Git hook | CI |
|---|---|---|---|---|---|
| Done needs evidence (R9) | A tasket marked done with unchecked criteria is dispatched as done by an engine; the next unit builds on nothing. tele-claude's automator reads `status` at five call sites and never reads warnings (`~/Projects/tele-claude/services/group_automator.py:5059,6064,6073,6175,6256`) | The consumer of the status is a program | `PreToolUse` on `Edit|Write` of `.taskets/*.md` computes the post-edit file and denies | `pre-commit` refuses staged taskets that reach `done` without evidence | `charter check --done` on the units that close in the change set; probes when `probes.in_ci` |
| Out of scope without an approved change (R6) | Work the client never bought, billed nowhere; the video's discount that quietly becomes a house rule | An agent under momentum reads a warning as advice | `PreToolUse` on `Edit|Write` denies paths under an out-of-scope glob | `pre-commit` refuses | `charter check --scope` |
| Contradicting a decision (R1, hard form) | Code built on a retired decision, or a decision's invariant silently broken | The contradiction is invisible in a diff review; only the check sees it | `PreToolUse` warns; `PostToolUse` runs the decision `check:` commands touched by the edit and reports | `pre-commit` refuses a retired citation or a failing `check:` | `charter check --decisions` |
| Frozen file (R3) | A file everyone edits becomes the most-disputed file (1,173 agents and ~8,000 conflicts on one file, reported in the video from Cursor's rerun) and, at this scale, an 873-line `CLAUDE.md` nobody can read | A warning has never shrunk a file; only a refusal does | `PreToolUse` denies a growing edit past the limit | `pre-commit` refuses | `charter check --size` |
| Anchored deliverables (R10) | A report or PR description that asserts what did not happen; the class of failure house memory records most often | The reader of the deliverable is a person who cannot re-derive it | none in session (the `charter-progress` skill runs the check before publishing) | none (deliverables are written after commits) | `charter anchors` on listed paths; the PR body as a warning |

What happens when a gate cannot be satisfied:

- A `PreToolUse` denial returns a reason that names the override: the change request to write, the code to move out of a frozen file, the evidence to add, the successor decision to propose. The agent can always take that step, so no denial leaves it without one; an approval, a retirement or a split unit then waits for the owner.
- The Stop hook blocks at most once per turn. It reads `stop_hook_active` and lets the second attempt through with a logged warning (`.charter/hooks/stop_gate.py`). A Stop hook that can never pass would otherwise loop until Claude Code's cap of eight blocks.
- A git hook that refuses prints the same override. `git commit --no-verify` remains available to the owner; CI then catches what was skipped. Nothing records the skip itself.
- CI is the last line and has no override besides changing the artifacts. That is intended.
- Every gate fails open on its own errors (a missing config, a parse error, an unexpected exception): it logs `decision=error`, prints the error on one line and allows. That holds in CI too, where the step passes and the error appears as a warning on the run (`docs/gates.md` § CI). A gate that breaks the tool is worse than a gate that misses once, and the log shows the misses.

## Accepted results

### Real tests

A test counts as real for acceptance when:

1. It exercises behaviour through the public surface the criterion names (an HTTP route, a CLI, a function's contract), not the implementation's internals.
2. It fails without the change. The unit's `## Evidence` records the failing run before and the passing run after, or the probe is a command whose output the criterion predicts. Wherever probes run (`probes.at_commit`, `probes.in_ci`, `--probe`), each probe of a closing unit is also run in a worktree at the parent of the commit that added the unit; one that passes there is reported, and refused with `probes.base_must_fail`. A criterion that guards behaviour which already exists is marked `(guard)` and is expected to pass there.

A project that sets `review.required` also needs, before done, a `review:` line under `## Evidence` anchoring an independent verdict, meant to come from a model family other than the one that wrote the code. It proves the verdict is cited, not that it was earned.
3. It runs in CI from a clean clone with no live credentials. A test that needs a real Stripe or HubSpot key is an end-to-end check that lives outside acceptance (orqueveaux's e2e suite is `xfail` for this reason, `~/Projects/orqueveaux/tests/e2e/test_payment_flow.py:38`).

A test that asserts the implementation's own structure (a mock was called with these arguments, a private attribute holds this value) is not acceptance evidence. It may still exist.

### The zero-hallucination guarantee, operationally

`charter anchors <file>` checks a markdown deliverable and fails if any claim line is unanchored. Definitions:

- A **claim line** is a prose line, list item or table row that is at least 40 characters long or contains a digit, outside code fences, headings, HTML comments and table separators. Adjacent prose lines form one paragraph and share anchors.
- An **anchor** is one of: a `path:line` or `path:line-line` reference to a file in the repository whose line exists; a bare repository path that exists; a git object name (7 to 40 hex characters, not part of a path) that `git cat-file -e` resolves, a digits-only one counting only when it resolves; an `http(s)://` URL; a line or list item that starts with `$ `, or a backticked `` `$ command` ``; an `E-<n>` reference to an entry in the document's own evidence index, which itself must be anchored. In a pull-request description (`--pr`), `#123` is also an anchor.
- A claim marked with a **reported** or an **inference** marker (the table below) passes as an admitted claim and is counted separately.
- A section fenced by `<!-- charter: opinion -->` ... `<!-- charter: /opinion -->` is exempt: recommendations, options and questions are not factual claims.

The report is: claim lines, anchored, admitted unverified, unanchored, and anchors that do not resolve. The gate is unanchored = 0 and unresolved = 0.

### Evidence classes

Every claim in a checked deliverable belongs to one of four classes. They use the words of tcv2's HARNESS.md source kinds, so a claim typed in one repository reads the same in the other (https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/services/harness_evidence.py, `_SOURCE_KINDS`).

| Class | What it is | How charter recognises it | `charter anchors` counts it as | tcv2 source kind |
|---|---|---|---|---|
| measured | An anchor that resolves in this repository | `path:line`, a bare path, a commit, a `$ command` run, an `E-<n>` entry | anchored | `measured` |
| vendor | A published source outside the project | An `http(s)://` URL | anchored | `vendor` |
| reported | An operator's or a document's claim that this repository cannot resolve | `(reported in ...)`, `(operator report ...)`, `(claimed by ...)`, `(outside this repository ...)`, and a scratch location: `(in the scratchpad ...)`, `(in the clone ...)`, `(on the test bed ...)` | admitted | `operator_report` |
| inference | Unverified, derived or opinion | `(inference ...)`, `(unverified)`, `(not verified)`, `(estimate ...)`, `(to be confirmed)`; an opinion fence | admitted; an opinion fence is exempt | `inference` |

tcv2 refuses a `measured` source that is a URL and a `vendor` source that is not one; charter's anchors agree on both. `(operator_report ...)`, tcv2's spelling, is admitted as well.

What the guarantee cannot cover, stated plainly:

- It checks that evidence is cited and resolves, not that the evidence supports the claim. A `file:line` that exists but says something else passes.
- A URL is checked for form, and with `--network` for reachability, never for content.
- A claim rewritten to avoid the 40-character threshold passes. The threshold catches carelessness, not intent.
- Opinion sections are exempt by declaration, so a fact hidden in an opinion section passes.
- It runs on the working tree; a deliverable committed at one SHA and checked at another can drift. CI checks at the merge SHA.

An honest guarantee is: every factual claim in a checked deliverable points at something a reader can open, and the pointer is not broken.

## The progress synthesis

`charter synth [--write]` reads the repository and prints (or writes to `charter/progress.md`):

1. **Scope**: each in-scope item with the units that cite it and their statuses; out-of-scope items with any approved change against them.
1. **Rails** (when `charter/rails.md` exists): each item of the road in order, with the units that cite it and their states, then the open units off the rails. It replaces a hand-kept tracker.
2. **Done and accepted**: units with `status: done`, all acceptance boxes checked and evidence that names a commit or a run and resolves; each line anchored to the unit file and its evidence. A commit the clone cannot resolve, cited by a unit whose done status is committed, is counted as historical (a squash or rebase merge removed it) and named as such.
3. **In progress**: units with a non-terminal status and at least one log line, with the last log line and date.
4. **Blocked**: units with `status: blocked` and their stated blocker.
5. **Open decisions**: decisions with `status: proposed`, and change requests with `status: proposed`.
6. **Gate activity**: counts per gate and decision from the gate log over the last 30 days, which is the warning-to-gate promotion evidence. Printed only: the written `charter/progress.md` leaves it out, because the log lives on one machine and CI checks the file from a clean clone.
7. **Cost**: from the ledger, the estimated total, cost per accepted unit (every session's cost, accepted or not, divided by the units accepted now), and the coverage: how many sessions have a cost, and how many of those record subagent usage. An unknown cost is never added as zero. While any session lacks a cost or subagent usage, the total and the figure per accepted unit are printed as lower bounds ("at least", "incomplete"). Per unit: its sessions, those without a cost, the subagents' share, the sessions after its first done, and the human minutes recorded, or "no human time recorded".

It then runs `charter anchors` on its own output and exits non-zero without writing if the check fails. It is read-only apart from `charter/progress.md`.

## Two tracks

`charter/config.json` `track` selects the gates:

| | Client (`client`) | Prototype (`prototype`) |
|---|---|---|
| Scope file | Required; the scope gate is hard | Absent; the scope gate is off |
| Rails file | Optional; runs beside the scope gate | Optional, and where the prototype has a roadmap, the way to keep it on it: `charter/rails.md` lists the road's items, every open unit names one, a warning by default and refused in the change set with `rails.required` |
| Decisions | Hard as above | Hard as above (cheap, and prototypes become products) |
| Size | Hard | Hard |
| Done needs evidence | Hard | Hard, but acceptance may be a single probe |
| Perimeter notes | Hard at commit | Warning only |
| Anchored deliverables | CI hard | Warning |
| BMAD | Planning artifacts only (brief, PRD, architecture, epics) as inputs to units; stories and sprint status are not used | Party mode and `bmad-quick-dev` welcome; their output becomes units when the prototype turns into a project |
| Ledger | On | On |

A prototype that acquires a client switches track by writing `charter/scope.md` and setting `track` to `client`; nothing else changes.

## Cost per accepted result at this scale

Recorded per session by the `SessionEnd` hook into `sessions.jsonl` in the git common directory (per machine, shared by worktrees, never committed): session id, active unit, input, output, cache-read and cache-write tokens summed per model, with 5-minute and 1-hour cache writes apart (Claude Code writes most of its cache with the 1-hour TTL, priced at twice the input rate: https://platform.claude.com/docs/en/about-claude/pricing), turn count. The sums cover the session's transcript and every subagent transcript Claude Code writes beside it, `<session id>/subagents/*.jsonl`; the main transcript holds none of the subagents' usage (docs/review/2026-09-12-astra-harmonization.md, E-17). The subagents' share is kept apart as well, and `children_included: true` records that their files were read. A session without a readable transcript has `usage: null`. `charter ledger fold` folds these into `charter/ledger.jsonl` (committed) with an estimated cost from `prices_usd_per_mtok`, a per-model table in the config taken from that pricing page and labelled an estimate in every output, and the subagents' share of it (`subagent_est_usd`, null for a record made before charter 0.2.1). A session with no usage has `est_usd: null`, which the synthesis counts as unknown, not as zero. Acceptance is read from the unit when `charter synth` runs, not frozen at fold time. Rework is the number of sessions that ended after the first commit that set the unit's status to done (`git log -G`). Headless runs report cost directly in their result JSON (`total_cost_usd`); `charter ledger add --result <json>` records those, and `charter ledger add --human-minutes N --unit <id>` records a person's time. Limits: a session is charged whole to the unit active when it ends, so a session that moved between units is misattributed; splitting it would need unit start and stop times matched against the transcript's timestamps.

Cost of the recording itself: a few milliseconds per session end, one JSON line per session.

## Seams designed, not built

**External contributor.** `charter brief <unit>` would render a self-contained markdown brief: the unit body, the scope items it cites (text, not the file), the decisions it relies on (text), the acceptance probes, the perimeter, and the repository URL and branch. It contains no path outside the repository, no vault reference, no personal tooling. The contributor works in their own repository or fork; acceptance runs the same probes against their branch in CI (`probes.in_ci`). The seam is the brief plus CI, and it needs no personal layer. Two things a contributor's pull request brings that an in-repository check cannot stop: it can edit `.github/workflows/charter.yml` and `.charter/`, which run from the pull request's own tree, and CI runs its decision `check:` commands as it runs its tests. CI refuses such changes from an author who is not `owner`, but the workflow doing the refusing is itself editable; the lock is branch protection with required code-owner review on those paths (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners). `charter brief` is not built in 0.3.0.

**Engines.** tele-claude's automator and tcv2's engine already dispatch `.taskets/`; the method changes no key they read. For them to *see* the new keys (`scope`, `perimeter`, `decisions`, `kind`), tele-claude's reader allowlist at `~/Projects/tele-claude/services/project_tasket_reader.py:230-234` needs four names added; until then the keys are stored and ignored, which is safe. The git hooks and CI gate their commits exactly as they gate an interactive session's, so an engine's done flip on a tasket written after the install needs acceptance and evidence (the legacy list above covers the earlier ones). An engine that exports `CHARTER_UNIT=<id>` to the session it starts gets the perimeter gate and a ledger attributed to that unit; neither engine does yet.

Where a project has a single frontmatter writer, charter's four keys are optional and its body sections carry the done gate. tcv2 is such a project. Its agents change frontmatter only through `python -m services.tasket_ops`, and body edits are ordinary committed edits (https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/AGENTS.md#L14-L17, rulings D23 and D24). `tasket_ops create` has no option for `scope`, `perimeter`, `decisions` or `kind` (docs/review/2026-09-12-astra-harmonization.md, trial row 6). A tasket created through it with `## Acceptance`, `## Evidence` and `## Log` in its body still closes through `set-status`, with charter's pre-commit and tcv2's routing validator both passing (trial row 5). Without the keys, the perimeter gate has nothing to check and a client-track unit without `scope:` warns. The owner has ruled that `tasket_ops create` should pass optional keys through verbatim, to be implemented in tcv2 (docs/review/2026-09-12-astra-harmonization.md § Decisions for you, `tasket-keys-writer`, option 1 chosen on 2026-09-12).

**Worktrees.** Both engines run steps in worktrees. The committed layer therefore lives only in tracked files: `.charter/`, `charter/`, `.claude/`, and the hook path set via `git config core.hooksPath .charter/githooks` (repository config is shared by worktrees, and `charter setup` sets it in a fresh clone), or, in a project that already runs a hook framework, a `charter check --staged` entry in that framework's tracked config. State written during a run goes to the git directory, an output and never an input: the gate log and session records to the common directory, which every worktree shares and which outlives a removed worktree; the active unit and per-session scratch to the worktree's own git directory, so two worktrees can work on two units. `${CLAUDE_PROJECT_DIR}` stays at the main checkout when a session enters a worktree mid-session, so hooks read `cwd` from their input to find the tree they act on. A CI runner's log is gone when the job ends.

## Where the personal layer stops

Everything above runs from a clean clone. The personal layer (`personal/` in this repository) adds what only makes sense on Gui's machines: a `CharterAdmin` skill that folds transcript costs across projects, turns open decisions into a Crossroads or Slate page, and pins the package version; and manifest lines for `~/.claude` assembly. The committed layer never references it.

## Less method, not more

Compared with today, the method removes: per-phase progress files, hand-maintained roadmaps with inline status, D-numbers inside `CLAUDE.md`, BMAD stories and sprint status, and unbounded auto-memory as the carrier of project rules. It adds: one scope file, one file per decision, three sections in a tasket, one config file, and gates that were absent. The net is fewer documents with more force.
