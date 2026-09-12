# Charter and the Astra methodology: evaluation and harmonization, 2026-09-12

This document compares two methods. The first is charter 0.2.0, this repository at commit ab0a8b1. The second is the coordination methodology that a GPT-6 Astra session built for tcv2, published as draft PR #24 (E-1). The owner lifted the fence between the two sessions for this comparison (reported in the owner's message of 2026-09-12).

tcv2 itself was only read. Astra's branch was read from a clone in this session's scratchpad, and charter was installed and exercised in a second scratch clone (E-16). Citations follow three conventions:

- charter files are cited as `path:line`, for example docs/method.md:43;
- tcv2 files that exist on its `main` are cited under `~/Projects/tcv2/`;
- files that exist only on Astra's branch are cited through the evidence index as E-n with `L` line numbers, which are the file's line numbers at the PR head (E-1).

Recommendations and questions sit in opinion sections, which the anchoring check exempts by declaration (docs/method.md:143).

## The call

<!-- charter: opinion -->
- **Keep two methods, and give them one vocabulary and interoperable artifacts.** The two answer the same video with the same rules, but they do different jobs.
  - Charter is a set of hard gates for a solo client project, placed at the commit and in CI.
  - Astra's method is the coordination frame of a multi-harness engine. In it, evidence informs and never decides, and the first effort goes to authority defects inside the engine.
  - A merged method would force one posture on both jobs.
  - The shared layer should be: the vocabulary below, the tasket body format for acceptance and evidence, the decision-record format, the evidence classes, and one attempt record that both ledgers can write and one reader can fold.
- **Charter should first take Astra's measurement discipline.** Astra's rule that a missing figure stays unknown exposes three defects in charter's ledger:
  - an unknown cost is added as zero;
  - subagent usage is never counted;
  - no coverage is stated.

  After that, charter should take four more things from Astra:
  - its broader list of commitments;
  - its rule that subagents read and the parent writes;
  - named exceptions to the size freeze;
  - its evidence classes and expiry semantics.
- **Fix one defect before anything else.** The interop trial found a charter defect unrelated to Astra: the pre-commit refuses every commit that stages a binary file, and exits with a traceback. tcv2 tracks 51 binary files.
- **Do not install charter on tcv2 now.** Three things stand in the way:
  - the size gate would freeze 28 files, the engine's core modules among them;
  - charter's CI would refuse PR #24 for three insertions the owner's brief authorised;
  - tcv2's tasket writer cannot write charter's frontmatter keys.

  Once changes 1 to 4 below are made, a prototype-track trial on a tcv2 clone is cheap and would settle the question.
- **tcv2 could take from charter what Astra's road proposes but has not built:**
  - the live decision-reference validator;
  - a machine-readable acceptance section with probes;
  - the done gate at commit;
  - the anchoring check for reports.
<!-- charter: /opinion -->

## What Astra produced

| Artifact | Path on the PR branch | What it is | Evidence |
|---|---|---|---|
| Report | `docs/factory/coordination-2026-09-12.md` | Rules, subagent policy per harness, HARNESS design, measurement, falsification, road, five decisions | E-2 |
| Harness evidence | `HARNESS.md`, `services/harness_evidence.py`, an advisory block in `services/tasket_routing.py` | Dated suitability of one model and harness pair for one operation; warnings at pre-flight, never a route change | E-3, E-5, E-18 |
| Measurement reader | `services/factory_measure.py` | Read-only accounting of retained run snapshots; failed rows counted; unknowns left `None` | E-6 |
| Instruction file | `AGENTS.md`, 3,434 bytes, plus one pointer line in `CLAUDE.md` | Fences for interactive sessions and for `codex-native` workers | E-4, E-12 L58 |
| Road taskets | four taskets in group `tcv2-factory-coordination`, orders 10 to 40 | Owned permissions, acceptance content, durable cost, portable decisions | E-13 |
| Lane notes | `docs/factory/notes/*.md`, evidence index, session log | Subagents, connections, decisions and memory, acceptance and cost, outside sources, validation, blind review | E-7 to E-12, E-15, E-19 |
| Roadmap insertion | 22 lines in the pivot roadmap | Proposed tracker rows, recommended order | E-18 |
| Tests | `tests/test_harness_evidence.py`, `tests/test_factory_measure.py`, and an isolated-copy check that they fail without the slice | Full CI passed with 1,431 tests and 107 skipped | E-12 L104-116, E-20 |

## Concept map

| Concept | Charter | Astra | Relation | Evidence |
|---|---|---|---|---|
| Source doctrine | The same video, the same five rules, and a rule table in a shape asked for so the two could be compared | Same | Same | docs/briefs/2026-09-11-fable-method.md:253-294, :384-389; ~/Projects/tcv2/docs/factory/brief-2026-09-11.md:278-291, :511-518 |
| Posture | Five hard gates at the session hook, the commit and CI; everything else warns (docs/method.md:104) | HARNESS advice warns and cannot block dispatch, even with `--strict`; the record's form is checked in CI by a test | Different by design | E-3 L57-60; E-21 L42-43; ~/Projects/tcv2/.github/workflows/ci.yml:33 |
| Where the must-hold checks live | git hook and CI, so they hold whichever harness commits | tcv2's engine pre-flight and pytest in CI | Compatible: neither depends on one harness's hooks for what must hold | docs/method.md:12; docs/briefs/2026-09-11-fable-method.md:78-81; E-4 L3-4 |
| Instruction file for other harnesses | A section appended to `AGENTS.md` between markers | `AGENTS.md` with fences only; a fresh Codex confirmed it discovers the file | Compatible: the section fits, 4,118 bytes after install | package/AGENTS.md:1-5; bin/charter-pkg:193-204; E-9 L57-60; E-16 |
| Unit of work | A tasket plus optional `scope`, `perimeter`, `decisions`, `kind`, and the sections `## Acceptance`, `## Evidence`, `## Log`, `## Outside perimeter` | A tasket with the route triple, `depends_on`, `roadmap`; body `# Do`, boundary prose, and `## Done when` with one executable command | Compatible; the section names differ | docs/method.md:45-79; E-13 |
| Frontmatter writer | Any editor; `PreToolUse` gates the edit and the pre-commit gates the commit | Only `python -m services.tasket_ops`, one commit per operation; it writes six named keys | Conflicting for charter's four keys; compatible for `status` and the body | docs/gates.md:12, :96; E-4 L14-17; ~/Projects/tcv2/services/tasket_ops.py:48-50 |
| Single writer | One owning session per unit: "Parallel agents read; one hand writes" | One writer per worktree, and one assembler owning integration | Same principle; Astra names the assembler | docs/method.md:43; E-2 L10-14, L40-49 |
| Subagents | R12 names "Guidance in the rules file", but the rules file contains none | A policy per harness: children read, the parent writes, until child gate coverage is proven | Complementary; Astra fills a charter gap | docs/method.md:102; `$ grep -in "wait\|staff\|subagent\|parallel" package/.claude/rules/charter.md` → no match; E-2 L129-134 |
| Independent review (R2) | A party that wrote neither side; the `charter-reviewer` agent is described as read-only but has Bash | A reviewer who wrote neither side, every finding verified; a tool list that keeps Bash is not a read-only boundary | Same rule; Astra's note corrects charter's label | package/.claude/agents/charter-reviewer.md:3-4; E-2 L55-57; E-9 L24 |
| Authority | Owner-only files and fields, `CHARTER_OWNER=1`, a CI author check; limit: the agent shares the owner's identity | Gui mints rulings, tracker ids and the route triple; the board grant is read through `git show HEAD:`, an application boundary rather than an OS one | Same shape, same admitted limit | docs/gates.md:19-39; E-4 L19-21, L44-46; E-8 L8-13 |
| Scope | R6: the signed devis summarised in `charter/scope.md`; out-of-scope paths hard | "Permission follows exact scope": the committed grant, plus a proposed scope fingerprint before a precedent is reused | Complementary: commercial scope against operational permission | docs/method.md:96; E-2 L51-64 |
| Commitments | R7: a change to what is sold, a price, a promise on time | Deployment, production data or schema, purchase or budget, public release, another person's work, grant widening, merging into main | Compatible; Astra's list covers software operations | docs/method.md:97; package/.claude/rules/charter.md:43; E-2 L51-54 |
| Decisions (R1) | One file per decision, `charter:<id>` markers; a retired citation or a failing `check:` is refused | Named by document, date and subject, with supersession; a live-reference validator is proposed, not built | Same; charter has built what Astra proposes | docs/method.md:91; package/.charter/checks.py:333-353; E-2 L76-83; E-13 portable-decisions L34-35 |
| Freeze and split (R3) | Counted in lines: 800 for code, 400 for a fixed governance list; overridden only by shrinking the file or by a split unit the owner opens | Counted in bytes: 32 KiB for actively loaded governance, AGENTS under 8 KB; narrow corrections and named exceptions allowed; the split is checked by a reviewer who did not grow the file | Conflicting in unit, scope and exceptions | docs/gates.md:50-54; package/.charter/checks.py:20-21, :148; E-2 L85-92 |
| Perimeter (R4) | `perimeter:` globs, and a note under `## Outside perimeter`; hard at commit on the client track | Departures noted in the step log; a planned-against-actual path audit is proposed | Same; charter's gate is the audit Astra proposes | docs/method.md:94; E-2 L94-102 |
| Memory (R8) | Lessons as decisions with an owner, `## Because` and `expires:`; expiry warns | Owner, source case, applicability, review date, expiry, supersession; HARNESS.md is the first typed instance | Same; Astra adds typed sources and exclusive expiry | docs/method.md:98; package/.charter/checks.py:452-466; E-2 L104-113; E-3 |
| Log and index (R5) | A `## Log` in each unit; the decision index handed over at session start | A session log with checklist, commits, next step and ledger; a bounded index for each new worker | Same | docs/method.md:95; E-15; E-2 L107-108 |
| Acceptance (R9) | Done needs every box checked and evidence that resolves; re-running the probes is opt-in | Git evidence is a preliminary signal; acceptance adds criterion revision, evidence bounds, executed checks, an independent verdict and reviewer; unknown is `None`, never a rejection | Complementary layers; the word "accepted" conflicts | package/.charter/checks.py:245-273, :307-324; E-2 L66-74 |
| Proof that a test tests something | "It fails without the change" is required, not checked | An isolated copy with the pre-change code must make the new tests fail; scripted | A charter gap that Astra has built | docs/method.md:131; E-12 L21-25; E-20 |
| Anchored deliverables (R10) | `charter anchors`, hard in CI for reports and syntheses | "Evidence, or it didn't happen" as a writing rule, plus an evidence index; no checker | Same discipline; mechanical only in charter | docs/method.md:100; ~/Projects/tcv2/docs/factory/brief-2026-09-11.md:99-101; E-19 |
| Cost per accepted result (R11) | Per session and unit: estimated USD, rework, human minutes | Per attempt: failed rows in the numerator, unknowns kept `None`, child inclusion stated | Same measure; Astra is stricter about unknowns | docs/method.md:190; E-6; E-7 L91-109 |
| Staffing (R12) | Put an agent where a real wait disappears | Add a reader only where a measured wait exists; a one-week pilot on a fixed scope | Same | docs/method.md:102; E-2 L115-122, L325 |
| Evidence classes | Anchors, plus the admitted markers `(unverified)`, `(reported in …)`, `(estimate …)`, `(outside this repository …)` | Source kinds `measured`, `operator_report`, `vendor`, `inference`; five evidence classes in the index | Compatible | package/.charter/checks.py:639; E-5 L20; E-19 L31-33 |
| Model suitability | None: charter does not route | Dated evidence per model and harness pair; advisory; never rewrites the route | Astra only | E-3; ~/Projects/tcv2/docs/factory/brief-2026-09-11.md:556-558 |
| Cross-harness review obtained | None: Codex authentication was revoked, so a fresh Opus subagent reviewed instead | None: Claude OAuth had expired, so a fresh Codex child reviewed instead | The same gap on both sides | docs/report-2026-09-11.md:111; E-11 L4-10 |
| Decisions for the owner | id, stake, options, stakes and reversibility scored 1 to 5, what waits | Same shape | Same | docs/report-2026-09-11.md:116; E-2 L319-325 |

## Astra's eight rules against charter's twelve

| Astra rule | Astra's own status | Charter rule | Charter enforcement | Relation | Evidence |
|---|---|---|---|---|---|
| One writer per worktree | Partial | Single writer (no number), R12 | Guidance | Same principle | E-2 L29; docs/method.md:43, :102 |
| Permission follows exact scope | Gap in the master shortcut | R6, R7, R2 | Hard for R6 and for R7's form; R2 warns | Complementary | E-2 L30; docs/method.md:92, :96-97 |
| Accept measured work | Weak existing gate | R9, R10 | Hard | Complementary layers | E-2 L31; docs/method.md:99-100 |
| Decisions are named and referenced | Partial | R1 | Hard for retired citations and failing checks | Same | E-2 L32; docs/method.md:91 |
| Oversized governance freezes for a split | Proposed | R3 | Hard | Conflicting details | E-2 L33; docs/method.md:93 |
| Perimeter departures are recorded | Partial | R4 | Hard at commit on the client track | Same | E-2 L34; docs/method.md:94 |
| Memory has owner, case and expiry | First slice (HARNESS.md) | R8, R5 | Warning | Same | E-2 L35; docs/method.md:95, :98 |
| Optimize cost per accepted result | Partial measurement | R11 | Warning | Same measure | E-2 L36; docs/method.md:101 |

Charter has three rules that Astra does not state as rules of their own (docs/method.md:89-102; E-2 L27-36):

- **R2.** Astra folds arbitration into its permission and acceptance rules (E-2 L30-31, L55-57).
- **R6.** tcv2 has no client scope: its fences keep client names, code and data out of its commits (E-4 L33).
- **R10.** Astra practises it without a checker (E-19).

Astra has two policies with no charter counterpart: the subagent policy per harness, and HARNESS.md (E-2 L129-134; E-3).

## Interoperability, tested

Charter 0.2.0 was installed on a clone of the PR head in the session scratchpad. tcv2's own tools were run with its venv (E-16). The table is the result.

| # | Question | What was run | Result |
|---|---|---|---|
| 1 | What does the installer change? | `$ python3 ~/Projects/methodo/bin/charter-pkg install . --track client --dry-run` | 32 changes. The package files go under `.charter/`, `.claude/` and `.github/workflows/charter.yml`. The installer creates a new `.claude/settings.json`, since tcv2 tracks none; its untracked `settings.local.json` holds only permissions. It appends the charter section to `AGENTS.md`, which grows from 3,434 to 4,118 bytes, and adds one line to `.gitignore`. It also sets `core.hooksPath`, which is unset in `~/Projects/tcv2` today (`$ git -C ~/Projects/tcv2 config --get core.hooksPath` → exit 1). |
| 2 | Which taskets does the done gate exempt? | The same install, reading `charter/legacy-taskets.txt` | 24 of the 27 taskets are listed as legacy, Astra's four among them. The three that carry an `## Acceptance` section are gated (package/.charter/lib.py:412-415). |
| 3 | Can a legacy tasket still close through tcv2's writer? | `$ python -m services.tasket_ops --project-root . set-status 20260912-0910-tcv2-factory-owned-permissions done` | Yes. It committed, because legacy taskets close with a warning (in the scratchpad clone of tcv2). |
| 4 | Is a new tasket in Astra's shape gated? | `create` with a `## Done when` body, then `set-status … done` | Refused by charter's pre-commit on two counts: no `## Acceptance` checklist, and no commit or `$ command` in the evidence. `tasket_ops` rolled the file back (~/Projects/tcv2/services/tasket_ops.py:707-718). |
| 5 | Does a tasket in charter's body shape work in tcv2? | `create --body-file` with `## Acceptance`, `## Evidence` and `## Log`, then `set-status … done` | Committed. tcv2's routing validator raised no finding about the body (in the scratchpad clone of tcv2). |
| 6 | Can tcv2's writer set charter's keys? | `$ python -m services.tasket_ops create --help` | No. It has no option for `scope`, `perimeter`, `decisions` or `kind`. |
| 7 | Would charter's CI accept PR #24? | `$ python3 .charter/bin/charter check --all --ci --base baf75af` | No: three blocking size findings, on files whose insertions the brief authorised (~/Projects/tcv2/docs/factory/brief-2026-09-11.md:67-68, :580, :608, :639). See the list below the table (in the scratchpad clone of tcv2). |
| 8 | What does the size gate freeze on install? | `check_size` over every tracked text file, binaries skipped (a script in the scratchpad) | 28 files, among them the modules Astra's first road tasket must change (E-13 owned-permissions L25-38). See the list below the table (in the scratchpad clone of tcv2). |
| 9 | Do binary files pass? | A modified PNG staged; a new PNG staged; CI mode over a modified PNG; `check --size --strict` | No, and tcv2 tracks 51 binary files. See the breakdown below the table (in the scratchpad clone of tcv2). |
| 10 | Would charter trip tcv2's own guards? | Read the FR56 guard and the CI workflow | No. The FR56 lexical guard scans only `services/` (~/Projects/tcv2/tests/test_no_direct_pi_cli.py:13). The package ships no test file (`$ find package -name 'test_*'` → 0 files). |
| 11 | Does Astra's report pass charter's anchoring check? | `$ python3 .charter/bin/charter anchors docs/factory/coordination-2026-09-12.md` | No: 73 claim lines, 28 anchored, 45 unanchored, 1 unresolved. Most unanchored lines are rule statements, proposals and decision rows, which charter would fence as opinion. The unresolved anchor is a tele-claude commit, which cannot resolve from tcv2 (in the scratchpad clone of tcv2). |

Row 7, the three blocking findings. The line counts reproduce with `wc -l` in a checkout of the PR head (E-1):

| File | Lines at the PR head | Charter's limit | Reproduce |
|---|---|---|---|
| `CLAUDE.md` | 875 | 400 (governance) | `$ wc -l CLAUDE.md` |
| `docs/omnigent-pivot-roadmap-2026-07-06.md` | 1,694 | 800 | `$ wc -l docs/omnigent-pivot-roadmap-2026-07-06.md` |
| `services/tasket_routing.py` | 1,417 | 800 | `$ wc -l services/tasket_routing.py` |

Row 8, the largest engine files among the 28 frozen (in the scratchpad clone of tcv2):

| File | Lines at the PR head | Reproduce |
|---|---|---|
| `services/tasket_ops.py` | 1,865 | `$ wc -l services/tasket_ops.py` |
| `services/worker_runner.py` | 1,717 | `$ wc -l services/worker_runner.py` |
| `services/tasket_routing.py` | 1,417 | `$ wc -l services/tasket_routing.py` |
| `services/main.py` | 1,259 | `$ wc -l services/main.py` |
| `services/supervise_run.py` | 1,211 | `$ wc -l services/supervise_run.py` |

Row 9, how binary files fail, case by case (in the scratchpad clone of tcv2, with the pre-commit active):

| Case | Command | Result |
|---|---|---|
| A modified PNG, staged | `$ git commit -m "trial: touch a png"` | Refused, with a `UnicodeDecodeError` traceback |
| A new PNG, staged | `$ git add new-image.png && git commit -m "trial: add a new png"` | Refused, with the same traceback |
| CI mode, a modified PNG in the change set | `$ python3 .charter/bin/charter check --all --ci --base HEAD~1` | Exit 1, with the same error |
| CI mode, a new PNG in the change set | `$ python3 .charter/bin/charter check --all --ci --base HEAD~1` | Exit 0; a new file has no base text to decode |
| Every tracked file | `$ python3 .charter/bin/charter check --size --strict` | Crashes on the first tracked binary |

The cause is that the output of `git show` is decoded as text (package/.charter/lib.py:106; package/.charter/checks.py:744-747, :761-763). This contradicts the method's statement that "every gate fails open on its own errors" (docs/method.md:122).

## Measurement: two records

| Field | Charter ledger (`charter/ledger.jsonl`) | Astra's reader | Astra's future row |
|---|---|---|---|
| Unit of record | One session (package/.charter/bin/charter:438-440) | One retained run step (E-6 L58-63) | One attempt of a logical result (E-7 L95-99) |
| Identity | Session id and unit (package/.charter/bin/charter:438) | Instance, run id, tasket id, session id (E-6 L58-60) | Adds group, logical result, tasket revision and an attempt link (E-7 L95-96) |
| Route | The model, inside `usage.by_model` (package/.charter/hooks/session_end.py:33-34) | Requested harness, model and effort; effective route `None` (E-6 L61-62) | Requested and effective route (E-7 L96) |
| Usage | Tokens summed from the main transcript (package/.charter/hooks/session_end.py:14-47) | None: `tokens: None` (E-6 L73) | Usage basis, finality, descendant inclusion (E-7 L98) |
| Cost | Estimated USD from a price table, or `total_cost_usd` for headless runs (package/.charter/bin/charter:394-404, :456-459) | `metered_usd: None` (E-6 L73) | Dollars, quota tokens, worker time and human minutes kept apart (E-13 durable-cost L36-37) |
| Human time | `human_minutes` rows (package/.charter/bin/charter:446-447) | `human_minutes: None` (E-6 L73) | Interventions and minutes (E-7 L99) |
| Acceptance | Read from the unit when the synthesis runs (package/.charter/bin/charter:348) | An engine-verified proxy; independent acceptance `None` (E-6 L56-57, L72) | Independently accepted outcome and source, plus the criterion revision (E-7 L97-98) |
| Failed attempts | Every session counts in the numerator (package/.charter/bin/charter:349) | Failed rows count; known missing runs are listed (E-6 L66, L75) | Kept, with the retry cause (E-7 L99-100) |
| Unknown values | `est_usd` is `None` when a session has no usage, and the synthesis then adds it as 0 (package/.charter/bin/charter:396-397, :345) | `None`; no ratio when a step is untimed (E-6 L71) | Never zero; an incomplete numerator is stated (E-7 L105-108) |
| Children | `subagent_output`, counted from `isSidechain` lines in the main transcript (package/.charter/hooks/session_end.py:43-44), which holds none (E-17) | `child_usage_inclusion: None` (E-6 L76) | Descendant inclusion required (E-7 L98, L106) |

The synthesis prints an "estimated total" and a figure per accepted unit (package/.charter/bin/charter:351-353). Both figures have three gaps:

- Every session without usage adds zero (package/.charter/bin/charter:345).
- Subagent tokens are absent. Claude Code writes each subagent's transcript to `<session>/subagents/agent-*.jsonl`, and the `SessionEnd` hook reads only `transcript_path` (package/.charter/hooks/session_end.py:59; E-17). The main transcripts of the five sessions in this project contain no `isSidechain` line, while one subagent file of the session that built charter holds 75 assistant usage records and 23,524 output tokens (E-17).
- Neither figure says how many sessions lacked usage, so a reader cannot tell a complete total from a lower bound (package/.charter/bin/charter:351-353).

## Where the two conflict

| # | Point | Charter | Astra or tcv2 | Evidence |
|---|---|---|---|---|
| C1 | Who writes tasket frontmatter | Any editor, gated | Only `tasket_ops`, which has no option for charter's keys | docs/gates.md:12; E-4 L14-17; E-16 (trial row 6) |
| C2 | Size rule | Counted in lines, on every file, with a fixed governance list; overridden only by shrinking or by a split unit | Counted in bytes, for governance only; named exceptions allowed; a reviewer checks the split | docs/gates.md:50-54; package/.charter/checks.py:20-21; E-2 L85-92 |
| C3 | Unknown cost | Added as 0 | Stays `None`, with no ratio | package/.charter/bin/charter:345; E-6 L71-73 |
| C4 | "Accepted" | The gate passed: boxes checked, evidence resolves | An independent verdict with reviewer and criterion revision; the engine's "verified" is only a proxy | package/.charter/bin/charter:233-235; E-2 L66-69; E-6 L78 |
| C5 | Decision series | `charter/decisions/<slug>.md` | D-rulings inside `CLAUDE.md`, and the instruction "do not mint a competing ruling series" | docs/method.md:35; E-2 L82-83 |
| C6 | Expiry boundary | A decision counts as expired from the day after its `expires:` date | An entry expires at the start of its `expires_on` date | package/.charter/checks.py:462; E-3 L6; E-5 L97 |
| C7 | Governance set | `CLAUDE.md`, `AGENTS.md`, the scope, rules files, decisions, changes | `CLAUDE.md`, the roadmap, the routing ladder, `AGENTS.md` | package/.charter/checks.py:20-21, :148; E-8 L96-100 |

The two do not conflict on authority. Both give commitments to the owner alone, and both send technical disputes to a party that wrote neither side (docs/method.md:92, :97; E-2 L51-57). Both also admit the same limit: the gate is an application boundary on a machine that the agent shares with the owner (docs/gates.md:39; E-8 L8-13).

## E.2 and E.4

Phase E is tcv2's acceptance rail (~/Projects/tcv2/docs/omnigent-pivot-roadmap-2026-07-06.md:5). The items in play are these:

| Item | What it is | Evidence |
|---|---|---|
| E.1 | Done. It made the gate addressable, and showed the gate returns `verified` both for a labelled reconstruction of a step that corrupted a client document and for a real good step. | ~/Projects/tcv2/docs/omnigent-pivot-roadmap-2026-07-06.md:68 |
| E.2 | "The gate reads WHAT changed, not just that something changed." Still todo. | ~/Projects/tcv2/docs/omnigent-pivot-roadmap-2026-07-06.md:69 |
| E.3 | Closes two limits the gate states but does not enforce. | ~/Projects/tcv2/docs/omnigent-pivot-roadmap-2026-07-06.md:70 |
| E.4 | A routing floor: verification work is never routed to `haiku`. | ~/Projects/tcv2/docs/omnigent-pivot-roadmap-2026-07-06.md:71 |
| E.5 | Lives on tele-claude's board. | ~/Projects/tcv2/docs/factory/brief-2026-09-11.md:406 |

Today the port credits any new commit after the step's baseline (~/Projects/tcv2/services/git_evidence.py:633-636).

Astra's plan for E.2 has four parts (E-13 acceptance-content L30-36):

- a relevance judgment layered above the three ported checks, with three possible verdicts (E-13 acceptance-content L30-31);
- three real good histories to test against (E-13 acceptance-content L32-33);
- a recorded criterion revision;
- a named independent reviewer.

Astra's first decision, `factory-order`, recommends taking the owned-permissions and dependency tasket first, then E.2 together with E.4 (E-2 L321). That tasket makes five changes (E-13 owned-permissions L25-38):

- it stops a question-answer marker from approving a permission (E-13 owned-permissions L26-27);
- it binds precedent reuse to an applicability contract (E-13 owned-permissions L27-30);
- it records the real worker session id (E-13 owned-permissions L30-31);
- it counts a gate as resolved only on a recognised terminal state (E-13 owned-permissions L31-32);
- it enforces `depends_on`.

Interaction with charter:

- **E.4 and the authority fixes** do not interact with charter. Charter neither routes work nor runs a master (`$ grep -rnw harness package/.charter` → no match).
- **E.2** interacts directly. E.2 needs a machine-readable criterion and a revision to judge against (E-13 acceptance-content L33-36). Charter's `## Acceptance` lines with probes are such a criterion, and the format passes through tcv2's writer and routing validator (E-16, trial row 5).

## Harmonized vocabulary

<!-- charter: opinion -->
One word per concept, usable in both repositories. Where the two already agree, the term is theirs; where they differ, the proposal names which side's word to keep.

| Term | Meaning | Charter today | Astra today |
|---|---|---|---|
| owner | The person who signs: approves commitments, mints rulings and tracker ids, owns routing | `owner` in `charter/config.json` | Gui |
| commitment | Anything that changes an external obligation: what is sold, price, dates, deployment, production data or schema, purchase or budget, public release, another person's work, widening a permission, merging into main | R7, commercial items only | Astra's list, operational items |
| unit | One tasket, one deliverable, one owning session | unit | tasket, step |
| attempt | One session or run step spent on a unit, failed or not; the numerator counts every attempt | session record | attempt, run step |
| engine-verified | The engine's git evidence found work landed within the step's bound; a proxy | none | `verified` |
| gate-accepted | Charter's done gate passed: every criterion checked, evidence resolves, probes re-run when enabled | "accepted" | none |
| reviewed | A party that wrote neither side confirmed the result against the criterion at a named revision | R2, not recorded per unit | "independently accepted" |
| unknown | Not measured; never zero, never a rejection; a ratio over it is incomplete or undefined | none (added as 0) | `None` |
| evidence class | `measured` (an anchor resolves: `path:line`, commit, `$ command` run), `reported` (an operator or document claim), `vendor` (a URL), `inference` (unverified or opinion) | anchors plus admitted markers | source kinds |
| expiry | Exclusive at the start of the date; expired evidence stays as history and loses its weight; an expired lesson does not revoke its source's authority | `expires:`, inclusive | `expires_on`, exclusive |
| decision | One named record per decision: name, date, owner, case, when it stops applying, supersession; code cites it by name | `charter/decisions/<slug>.md` | named ruling by document, date, subject |
| lesson | A decision about how the house works, with an owner and an expiry, promoted only by the owner | `kind: lesson` | durable house lesson |
| suitability record | Dated evidence that a model and harness pair suits an operation; advisory | none | HARNESS.md entry |
| perimeter | The paths a unit may touch without a note | `perimeter:` | tasket perimeter, subject repo |
| departure note | One line saying which path outside the perimeter was touched and why | `## Outside perimeter` | step-log note |
| arbiter | The party that wrote neither side and settles a technical conflict | charter-reviewer, Codex, owner | independent reviewer |
| assembler | The one who merges the reference version; on a solo project, the owner's merge | the owner's merge | integrator, assembler |
| freeze | A file over its budget accepts no growth until it is split or excepted | frozen file | freeze pending split |
| named exception | An owner-approved growth budget for one frozen file, with a reason and an expiry | none | named exception |
<!-- charter: /opinion -->

## What charter should adopt from Astra

<!-- charter: opinion -->
Each item maps to a change in the ranked table below.

- **Unknown stays unknown**, and every ratio states its coverage (changes 2 and 8). The measure is only honest when a missing figure is visible.
- **Count the children** (change 3). Astra refuses to assume that a parent's usage includes its children's. Charter did assume it, and it is wrong here.
- **Named exceptions to the freeze, and a byte budget for governance** (change 4). Otherwise charter refuses the growth that the owner explicitly asks for.
- **"Accepted" split into gate-accepted and reviewed, with the probe run bound to a revision** (change 5). This is Astra's criterion revision and reviewer, at tasket scale.
- **A broader list of commitments** (change 6). A solo developer's riskiest commitments are often operational ones, not commercial ones.
- **Subagents read, the parent writes** (change 7). This makes R12 a written rule and makes the reviewer label true.
- **Proof that a test fails without the change** (change 9). This is Astra's isolated-copy check, generalised.
- **Exclusive expiry and typed evidence classes** (changes 10 and 11).
<!-- charter: /opinion -->

## What tcv2 could adopt from charter

<!-- charter: opinion -->
These are follow-ups for tcv2, written as proposals. None of them is an edit made here.

- **The live decision-reference validator.** The portable-decisions tasket asks for "a machine check for named live decision references with missing/superseded cases". Charter's R1 check does that: markers, unknown ids, retired citations with a named successor, duplicate ids (package/.charter/checks.py:333-353, :369-390). If D-rulings move out of `CLAUDE.md`, one file per ruling with the D-number kept in the slug (`d23-the-write-and-commit-are-one-act.md`) meets both Astra's naming rule and charter's format.
- **The acceptance body format as E.2's criterion source.** `## Acceptance` lines with `probe:` commands, and `## Evidence` with `$ command` lines and SHAs, work through `tasket_ops` today (trial row 5). E.2's relevance layer could then read criteria rather than prose.
- **The done gate at commit.** With charter's pre-commit, `tasket_ops` already refuses and rolls back an unevidenced done flip (trial row 4). A tcv2-native equivalent needs no charter install.
- **`charter anchors` on factory reports and PR bodies, with proposals fenced as opinion.** Astra's report already follows the discipline by hand (trial row 11).
- **Attempt rows compatible with charter's ledger** from the durable-cost tasket, so one reader can fold both engines (see the shared record under change 8).
- **`tasket_ops create` passing optional keys through verbatim** (decision `tasket-keys-writer`). D23 exists to protect ordering invariants, which pass-through keys do not touch.
- **Show the gate's reason on the board when a done flip is refused.** This is already listed as a charter follow-up (docs/review/2026-09-11-weakness-evaluation.md:79).
<!-- charter: /opinion -->

## Settling the conflicts

<!-- charter: opinion -->
- **C1, frontmatter writer.** The body sections carry the done gate, and charter's four keys stay optional, so tcv2 works without them (trial row 5). Whether `tasket_ops` passes the keys through is tcv2's ruling.
- **C2, size rule.** Keep charter's line limit for code on client projects, which is its own decision. Add three things:
  - named exceptions;
  - a byte budget for governance;
  - a configurable governance set.

  Astra's governance-only freeze fits tcv2. Charter's code freeze fits small client repositories. Both can be configured from one mechanism.
- **C3, unknown cost.** Astra's rule wins.
- **C4, "accepted".** Adopt the three words: engine-verified, gate-accepted, reviewed. Charter's stored data does not change, only what the synthesis calls it.
- **C5, decision series.** In tcv2, D-rulings would move into decision files that keep their number, so no second series appears. Charter does not ask tcv2 to adopt its directory.
- **C6, expiry boundary.** Take Astra's exclusive boundary.
- **C7, governance set.** Make the set a configuration value, with charter's current list as the default.
<!-- charter: /opinion -->

## Proposed changes to methodo, ranked

<!-- charter: opinion -->
Effort: XS is under an hour, S a few hours, M a day. Reversibility is scored 1 to 5, where 5 means easily reversed. Nothing here is implemented yet.

| # | Change | Effort | Reversibility | Motivating evidence | Where |
|---|---|---|---|---|---|
| 1 | Binary-safe gates: read `git show` output as bytes and skip files with a NUL byte in the size, done and decision checks; wrap `charter check` so an unexpected exception logs `decision=error` and exits 0, as the method promises; add a regression test with a staged PNG | S | 5 | Trial row 9: every commit that stages a binary is refused with a traceback; tcv2 tracks 51 binaries; docs/method.md:122 | `lib.git`, `checks.base_text`, `checks.staged_text`, `_check` in `bin/charter` |
| 2 | Unknown stays unknown: do not add a missing `est_usd` as 0; print the coverage (sessions with usage out of all sessions, human minutes recorded or not); label the per-accepted figure "incomplete" when coverage is under 100%; undefined at zero accepted is already right | S | 5 | package/.charter/bin/charter:345, :351; E-6 L71-73; E-7 L105-108 | `cmd_synth` |
| 3 | Count subagents: `SessionEnd` also sums `<transcript dir>/<session id>/subagents/*.jsonl` and records `children_included: true`, with subagent usage kept apart so R12's share measures something | S | 5 | E-17: main transcripts hold no sidechain line, while subagent files hold usage; package/.charter/hooks/session_end.py:44, :59 | `hooks/session_end.py` |
| 4 | Size: owner-only named exceptions in `charter/config.json` (`path`, budget, `because`, `expires`); a governance byte budget (default 32 KiB) beside the line limit; the governance set configurable, with today's list as the default | M | 4 | Trial rows 7 and 8; E-2 L85-92; the roadmap's longest line is 40,497 characters (E-8 L96-97) | `checks.size_limit_for`, `check_size`, config, docs/gates.md |
| 5 | Acceptance words and revision: the synthesis says "accepted by the gate" and "reviewed"; a `## Evidence` line `- reviewed by <who> at <sha>: <verdict>` is recognised; `charter probe` prints `at <HEAD sha>` and `(dirty)` when the tree differs from HEAD | S | 5 | package/.charter/bin/charter:213-240, :580-594; E-2 L66-74 | `_unit_state`, `cmd_probe`, `cmd_synth`, docs/method.md § Accepted results |
| 6 | R7 lists the operational commitments beside the commercial ones | XS | 5 | docs/method.md:97; package/.claude/rules/charter.md:43; E-2 L51-54 | docs/method.md, rules file, docs/gates.md |
| 7 | R12 made real: rules-file lines "subagents read, the parent writes; a subagent that can run Bash is not read-only"; the `charter-reviewer` description corrected to say it has no Edit or Write, rather than that it is read-only | XS | 5 | docs/method.md:102 and the empty grep; package/.claude/agents/charter-reviewer.md:3-4; E-9 L24 | rules file, agent file |
| 8 | One attempt record: optional ledger fields `harness`, `model`, `effort`, `run_id`, `attempt`, `instance`, `usage_basis`, `usage_final`, `children_included`, `worker_seconds`; plus a short `docs/interop/attempt-record.md` with the reader rules (deduplicate by session, failed attempts in the numerator, unknown never zero, undefined at zero accepted, coverage printed with every ratio) | M | 4 | The measurement table above; E-7 L91-109 | `cmd_ledger`, a new doc |
| 9 | `charter probe --without <rev>`: run the unit's probes in a temporary worktree at the base revision, expect them to fail, and print both results as evidence lines | M | 5 | docs/method.md:131; E-20; E-13 owned-permissions L77-78 | `cmd_probe`, docs/method.md |
| 10 | Exclusive expiry (`expires` on or before today counts as expired) and `expires` later than `date` in decisions; the template says so | XS | 5 | package/.charter/checks.py:462; E-3 L6; E-5 L58, L97 | `check_memory`, decision template |
| 11 | Evidence classes: `charter anchors` also admits `(operator report …)` and `(inference …)`; docs/method.md maps the four classes | XS | 5 | package/.charter/checks.py:639; E-5 L20 | `ADMIT_RE`, docs/method.md |
| 12 | Engines seam: note that where a project has a frontmatter writer (tcv2's `tasket_ops`), charter's keys are optional and its body sections carry the gate | XS | 5 | Trial rows 5 and 6 | docs/method.md § Seams |
| 13 | Cost per accepted unit per model in the synthesis, so charter's ledger can feed a suitability record like HARNESS.md | S | 5 | E-3 L23-25; package/.charter/hooks/session_end.py:33 | `cmd_synth` |

Changes 1 to 3 fix defects in code; the other ten adopt Astra's practice or document a seam. Changes 1 to 3 and 6, 7, 10 and 12 need no design choice. Changes 4, 5, 8 and 11 wait on the decisions below.
<!-- charter: /opinion -->

## Decisions for you

<!-- charter: opinion -->
Each entry gives an id and the question, the stake in one sentence, the options with the recommendation first, stakes and reversibility scored 1 to 5 (5 means high stakes; 5 means easily reversible), and what waits on it.

**harmonization-shape.** How close should charter and Astra's method get?

- Stake: this decides whether changes 8 and 11 are an interface spec or charter-internal.
- Options:
  1. Two methods with a shared vocabulary and interoperable artifacts. Recommended: it respects the two jobs and costs one short spec.
  2. One merged method for both repositories.
  3. Charter adopts Astra's pieces, with no shared spec.
- Stakes 3, reversibility 4.
- Waits: changes 8 and 11, and the tcv2 follow-ups.

**charter-defects-now.** Implement changes 1 to 3 now?

- Stake: charter currently refuses commits with binaries and overstates its measure.
- Options:
  1. Yes, on a branch cut from `main` once `fix/charter-review-2026-09-11` is merged, each with a regression test. Recommended: they are defects, not design.
  2. Bundle them with the adoptions.
  3. Wait.
- Stakes 3, reversibility 5.
- Waits: any first install on a repository that tracks binaries.

**size-rule.** How should the freeze change?

- Stake: as shipped, charter refuses owner-authorised growth and cannot express a governance budget in bytes.
- Options:
  1. Named exceptions, a governance byte budget and a configurable governance set, keeping 800 lines for code. Recommended.
  2. Keep lines only and add exceptions.
  3. Adopt Astra's governance-only freeze and drop the code limit.
- Stakes 3, reversibility 5.
- Waits: change 4, and the earlier `size-limits` question about tests (docs/report-2026-09-11.md:120).

**accepted-word.** Rename the synthesis categories?

- Stake: "accepted" in charter means less than "accepted" in Astra's method.
- Options:
  1. "Accepted by the gate" and "reviewed", plus a reviewer evidence line. Recommended.
  2. Keep "accepted" and document it as a proxy.
  3. Require a reviewer line for "accepted".
- Stakes 2, reversibility 5.
- Waits: change 5.

**charter-on-tcv2.** Install charter on tcv2?

- Stake: two gate systems on one engine repository could refuse each other's work.
- Options:
  1. Not now. After changes 1 to 4, run a prototype-track trial on a tcv2 clone and decide from its log. Recommended.
  2. Install now. CI would refuse PR #24, and 28 files would be frozen.
  3. Never: tcv2 keeps its own gates and adopts formats only.
- Stakes 4, reversibility 3.
- Waits: Gui's `factory-order` and `factory-size` decisions in tcv2.

**tasket-keys-writer.** Should `tasket_ops create` pass through optional keys?

- Stake: charter's perimeter gate needs `perimeter:`, which tcv2's writer cannot set today. This is a tcv2 ruling under D23.
- Options:
  1. Pass through unknown optional keys verbatim at creation. Recommended: D23 guards ordering invariants.
  2. Name the four keys explicitly.
  3. Keep them out of tcv2.
- Stakes 2, reversibility 5.
- Waits: a charter trial on tcv2 with perimeter.

**decisions-home-in-tcv2.** When `CLAUDE.md` is split, where do D-rulings go?

- Stake: two decision series in one repository is the drift both methods try to stop.
- Options:
  1. One file per ruling, D-number in the slug, charter's fields. Recommended: this meets Astra's naming rule and gets a validator for free.
  2. A tcv2-specific manifest.
  3. Leave them in `CLAUDE.md`.
- Stakes 3, reversibility 4.
- Waits: Astra's `factory-memory` and `factory-size` decisions.

**cross-review.** Run the cross-harness reviews that both sessions missed?

- Stake: neither method has had a review from a different harness, which is its own rule 2.
- Options:
  1. Yes: Codex on charter with the saved prompt (`docs/review/prompt-2026-09-11.md`), and a Claude review of PR #24. Recommended: cheap, and it closes a gap both reports admit.
  2. Only one of the two.
  3. No.
- Stakes 2, reversibility 5.
- Waits: nothing.

**branch-order.** Merge `fix/charter-review-2026-09-11` into `main` before this work?

- Stake: this review branch sits on top of it, and the changes above would too.
- Options:
  1. Merge it first, then cut the change branches from `main`. Recommended.
  2. Stack the change branches on it.
  3. Keep everything unmerged until harmonization is done.
- Stakes 2, reversibility 4.
- Waits: the change branches.

The E.2 and E.4 ordering is Gui's `factory-order` decision in tcv2, and this document does not decide it. The only charter-side consequence is this: if E.2 reads charter's acceptance format, change 5 should land first, so that the criterion revision and the reviewer line mean the same thing in both repositories.
<!-- charter: /opinion -->

## Limits of this evaluation

- Astra's work was read at the PR head only. Its runtime claims about the VPS, Omnigent and the deployed configuration were not re-verified here, and are cited as Astra's (E-2 L333-334).
- The interop trial ran in a scratch clone with tcv2's venv, and tcv2's full test suite was not run with charter installed (in the scratchpad clone of tcv2).
- No party that wrote neither side has reviewed this document (outside this repository: this session's transcript).

## Evidence index

- E-1 Draft PR #24, `astra/factory-20260911` into `main`, head 936cb5618bdb98453b4a73e167670bccc74a27a5, base baf75af (outside this repository: tcv2): https://github.com/elgui/tcv2/pull/24; read with `$ gh pr view 24 --json headRefOid,commits` and `$ gh pr diff 24 --name-only`. No comments or reviews on the PR (`$ gh api repos/elgui/tcv2/pulls/24/reviews` → 0).
- E-2 Astra's report: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/docs/factory/coordination-2026-09-12.md
- E-3 HARNESS.md: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/HARNESS.md
- E-4 AGENTS.md: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/AGENTS.md
- E-5 The HARNESS validator and advice: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/services/harness_evidence.py
- E-6 The measurement reader: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/services/factory_measure.py
- E-7 The acceptance and cost lane, with the future row contract: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/docs/factory/notes/acceptance-cost.md
- E-8 The decisions and memory lane, with the size inventory: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/docs/factory/notes/decisions-memory.md
- E-9 The subagents lane: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/docs/factory/notes/subagents.md
- E-10 The connections lane: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/docs/factory/notes/connections.md
- E-11 The fresh-context review: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/docs/factory/notes/independent-review.md
- E-12 The validation record, including CI run 34687292264: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/docs/factory/notes/validation.md and https://github.com/elgui/tcv2/actions/runs/34687292264
- E-13 The four road taskets:
  - owned-permissions: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/.taskets/20260912-0910-tcv2-factory-owned-permissions.md
  - acceptance-content: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/.taskets/20260912-0910-tcv2-factory-acceptance-content.md
  - durable-cost: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/.taskets/20260912-0910-tcv2-factory-durable-cost.md
  - portable-decisions: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/.taskets/20260912-0910-tcv2-factory-portable-decisions.md
- E-14 Astra's brief, unchanged by the PR: `~/Projects/tcv2/docs/factory/brief-2026-09-11.md`
- E-15 The session log: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/docs/factory/session-log.md
- E-16 The interop trial (in the scratchpad clone of tcv2). The setup was:
  - `$ git clone --no-checkout ~/Projects/tcv2 tcv2-astra` then `$ git fetch git@github.com:elgui/tcv2.git astra/factory-20260911` inside the clone;
  - a second clone checked out at the PR head (`$ git clone -q tcv2-astra tcv2-charter`);
  - `$ python3 ~/Projects/methodo/bin/charter-pkg install . --track client`;
  - the commands in the trial table, with tcv2's tools run as `$ ~/Projects/tcv2/venv/bin/python -m services.tasket_ops`.

  Nothing under `~/Projects/tcv2` was written.
- E-17 Claude Code's transcript layout in this project: `~/.claude/projects/-home-gui-Projects-methodo/8ac70e2b-aca6-4baa-8d95-ef0b955f4546/subagents/` holds 14 files. The measurement:
  - `$ grep -c '"isSidechain":true' <each main transcript>` → 0 for all five;
  - in ~/.claude/projects/-home-gui-Projects-methodo/8ac70e2b-aca6-4baa-8d95-ef0b955f4546/subagents/agent-a07c5299d3ca0976b.jsonl: 319 sidechain lines, 75 assistant usage records, 23,524 output tokens.
- E-18 The PR's changes to existing tcv2 files, `$ git diff baf75af...HEAD -- CLAUDE.md services/tasket_routing.py docs/omnigent-pivot-roadmap-2026-07-06.md` (in the scratchpad clone of tcv2):
  - a pointer line and a blank line in `CLAUDE.md` (in the scratchpad clone of tcv2);
  - a 24-line advisory block in `validate_group` (in the scratchpad clone of tcv2);
  - a 22-line roadmap frame (E-12 L98).
- E-19 Astra's independent evidence index: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/docs/factory/evidence-index.md
- E-20 The isolated-copy check that the slice's tests fail without it: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/scripts/factory_without_slice_check.py
- E-21 The HARNESS tests, including the test that validates the committed record: https://github.com/elgui/tcv2/blob/936cb5618bdb98453b4a73e167670bccc74a27a5/tests/test_harness_evidence.py

## Session ledger

| When (UTC) | What | Model / effort | Usage | Outcome |
|---|---|---|---|---|
| 10:56 | Session start on branch `fix/charter-review-2026-09-11`, clean at ab0a8b1 | claude-opus-5 (1M context); effort not exposed to the session | see the last row | accepted |
| 10:58 to 11:15 | Read PR #24, Astra's brief, report, notes, code and taskets; read charter's method, gates and code (E-1 to E-20) | same | see the last row | accepted |
| 11:00 to 11:12 | Interop trial in two scratch clones: the installer, three done flips through `tasket_ops`, CI mode over the PR, the binary cases, the anchor check on Astra's report (E-16) | same, plus tcv2's venv Python | see the last row | three charter defects found: binary files (trial row 9), subagent usage (E-17), unknowns added as zero (package/.charter/bin/charter:345) |
| 11:15 onward | This document, docs/review/2026-09-12-astra-harmonization.md, on branch `review/astra-harmonization-2026-09-12` | same | see the last row | pending the owner's review |
| Total | No subagents, no reviewer, no interruption (outside this repository: this session's transcript) | same | At 11:22, measured over 63 API turns: 126 input, 112,357 output, 15,087,592 cache-read and 339,849 cache-write (1-hour) tokens. Summed from the main transcript with charter's own `sum_usage`; this session has no subagent directory. Priced at 13.75 USD (estimate from charter's price table for claude-opus-5; a subscription session, so no bill) | the owner's acceptance is pending |
