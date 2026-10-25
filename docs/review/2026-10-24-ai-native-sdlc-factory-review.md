# The software factory after the AI-native SDLC playbook

Research report, 2026-10-24. Research and proposals only; no implementation or rollout is authorized by this report. The evidence snapshot and its limits are recorded below. E-1, E-2.

<!-- charter: opinion -->
**Recommendation:** keep Charter as the repository contract and tele-claude as the execution and owner interface. First make their existing checks agree about what was verified; then pilot a small outcome-review layer connecting a problem to its delivered change and observed result. Measure useful outcomes per hour of owner attention before adding more autonomous execution. Do not begin with a replacement platform or a mandatory six-document workflow.
<!-- charter: /opinion -->

## Sources, scope, and assumptions

The primary source is Louis Claxton's [The AI-native SDLC playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook), displayed as published August 21, 2026. It links a [54-page PDF playbook](https://cdn.prod.website-files.com/6889473510b50328dbb70ae6/6aba736348bdf4f08183f463_AI%20Native%20SDLC%20Playbook_designv2%20%281%29.pdf). I read the article's substantive lifecycle sections and the corresponding PDF text, including deployment and maintenance. The browser tool could not open the PDF; direct HTTPS download succeeded and `pdftotext` extracted its text. Neither primary source remained inaccessible. The PDF's diagrams were not independently analyzed. E-1.

Anthropic presents a practice guide, not a controlled evaluation of this factory. Its central claim is that the constraint moves beyond coding; its proposed response combines committed handoffs, automated verification, human judgment, and production feedback. It also proposes regression evaluations of agent configuration. These are Anthropic's claims and prescriptions, not demonstrated outcomes for Charter or tele-claude. The article supplies no comparative dataset from which I can estimate this owner's productivity gain. [Article](https://claude.com/resources/articles/the-ai-native-sdlc-playbook).

The local investigation traced selected paths from intake through task dispatch, checking, owner action, delivery, and learning. Charter was clean on `owner-json-content-payload-20261024` at `a2067b4`; tele-claude was on `main` with concurrent staged, unstaged, and untracked work. The latter's snapshot identity and changed areas are in E-2. Source code establishes implemented mechanisms, not that they are enabled, exercised successfully, or valuable in production. No product tests, live deployments, private transcripts, historical owner-time datasets, or remote branch-protection settings were examined or exercised. E-2, E-16.

<!-- charter: opinion -->
I assume the objective is **useful delivered software per unit of owner attention**, subject to acceptable defects, lead time, cost, and recovery. A useful outcome is an agreed user or operational improvement observed after delivery; a checked tasket is an intermediate result. For a client, contractual acceptance also matters. Gui may fill product, engineering, release, and service-owner roles, but those responsibilities still need distinct evidence.

All experiment thresholds below are proposed decision rules, not predictions or measured baselines. Small pilots establish feasibility and expose failure modes; they do not establish statistical reliability or commercial demand.
<!-- charter: /opinion -->

## The approach space, before the detailed recommendation

<!-- charter: opinion -->
Most answers would recommend four approaches:

1. Standardize intent, specification, plan, review, and incident documents.
2. Run more agents and parallel worktrees with a supervising agent.
3. Add stronger hooks, tests, and independent reviews.
4. Add a dashboard for throughput, cost, and interruptions.

Their common assumption is that worthwhile work is already entering the factory and the main opportunity is to process it faster or more reliably. Each can help, but all can also make the factory better at completing the wrong work.

Approaches outside that set:

| Approach | Assumption it drops | Assessment |
|---|---|---|
| Limit active work and cancel weak bets | More accepted work and greater concurrency are desirable | Serious, cheap experiment. Reduce simultaneous demands on the owner before investing in orchestration. |
| Judge whether an improvement happened, independently of task completion | Acceptance probes adequately represent user value | Serious complementary layer. A technically correct change may deserve reversal or no further investment. |
| Make Charter a small portable evidence protocol; retire overlapping execution responsibilities | Charter and tele-claude should both grow into fuller factory platforms | Serious pivot. Worth testing outside tele-claude before moving code or removing working features. |
| Let a self-improving agent generate work, change its own checks, and promote itself | Human choice of objectives and independent evaluation are still necessary | Not credible here as a general solution. Its success measure could move with its behavior; the current evidence does not validate such autonomy. |

The first three are developed below. The fourth should not become a roadmap item on the strength of the playbook.
<!-- charter: /opinion -->

## What the factory already does

The useful architectural distinction is already present: Charter owns durable project records and checks; tele-claude owns interactive execution and its runtime state. Their integration is real: tasket metadata reaches tele-claude, worker environments can carry the Charter unit, and Owner Desk consumes Charter's owner-command JSON. E-3, E-7, E-9.

| Lifecycle responsibility | Evidence in the repositories | Assessment |
|---|---|---|
| Understand a problem and choose work | Conversation Studio can send a completed summary to a project's inbox; the receiving project decides how to adopt it. Taskets have Context, Acceptance, Evidence, and Log; rails and client scope constrain work. E-3, E-8. | Strong raw materials. An inbox note is not an accepted product intent, and a rail is not proof of demand. I found no shared requirement connecting every delivered change to an observed outcome. |
| Design and preserve decisions | Decisions have rationale, affected paths, optional executable checks, and expiry. Client scope and approved changes are separate from general project work. E-3, E-4. | A better fit than copying the same decision into several stage documents. Missing responsibility: who judges the adequacy of the proposed outcome and test, before implementation makes them expensive to change? |
| Execute and resume work | Charter has continuous chains, group reviews, handoffs, and owner waits. Tele-claude has group automation, worktrees, supervision, and harness-specific launch support. E-7, E-10, E-17. | Strength and overlap. Two orchestration paths can have different completion and review semantics. A common contract is more urgent than another scheduler. |
| Verify completion | Charter checks acceptance boxes and evidence references; probe execution and review requirements are configurable. Tele-claude's checker checks new attributed commits, perimeter, unchanged acceptance, and executes probes; closure checks that HEAD and the worktree still match its verdict. E-5, E-6, E-7. | Substantial assurance machinery already exists. It establishes bounded technical evidence, not semantic correctness or usefulness. Interactive work and automated work do not receive identical checking by default. |
| Obtain judgment and authority | Charter defines owner-only acts and delegation levels. Owner Desk derives asks, hashes payloads, claims executions, checks state, and records results. It uses Charter's verbs rather than replacing them. E-9. | A major strength: an owner decision has an executable, inspectable route. This division is complementary, not two independent approval systems; preserve it. |
| Deliver and recover | Restart and frontend detectors compare timestamps; restart verification can check HTTP health. Production code is linked to the shared checkout. A separate smoke exercises boot and GET routes; a packaging/release initiative is being drafted concurrently. E-12, E-13, E-19. | Action completion and release identity are different. The inspected path does not establish that the exact reviewed backend, frontend, configuration, and dependencies form the release now serving users. |
| Learn and measure | Charter records usage, estimated cost, optional human minutes, and expiring lessons. Tele-claude records activity and attention-related events, monitors health, and versions shared skills. E-4, E-11, E-14, E-15. | Not a blank slate. But these records do not, by themselves, measure improved user outcomes or regress the behavior of the complete agent configuration. |

### Important qualifications to those strengths

**The integration documentation has drifted.** Charter's method says tele-claude still needs the Charter tasket keys and does not export the active unit. The inspected reader already passes the keys; `step_close` builds worker identity and `CHARTER_UNIT` exports. Treat that method paragraph as stale guidance, not as an implementation backlog. E-7, E-18.

**Configured strength is lower than some method language suggests.** The package defaults and tele-claude's project configuration disable commit/CI probes, base-must-fail, and required review. The automator's checker separately runs probes. Thus a claim about “Charter enforcing tests” needs its execution path and configuration attached. The installed version file says 0.4.18 while tele-claude's config version field says 0.4.6; a version label alone is inadequate evidence of capability. E-5, E-6, E-16.

**A gate error can become a successful exit.** Charter's exception handler deliberately returns zero, including in CI, with a warning. This is documented policy, not a newly discovered accidental bug. It protects continuity but cannot justify treating a successful process exit alone as a completed verification. E-5.

**Acceptance text is better protected than the test implementation.** Tele-claude compares acceptance with the base revision and runs its own checker/Charter entry point. The tests invoked by those commands still run from the worker workspace. Preflight warns when a referenced test does not exist at the base. These measures reduce self-grading; they do not establish independent test adequacy. Charter's ordinary acceptance-edit check merely requires an added log line. E-5, E-6.

**Commercial scope and operational assurance are different responsibilities.** Charter's scope enforcement matches excluded paths, so an out-of-agreement feature implemented within an allowed path can escape that check. The owner still interprets the agreement, judges changed obligations, and accepts the result. Internal products also need strong assurance even when there is no client scope file. E-3, E-4, E-20.

**“Independent review” has several meanings.** Charter's ordinary required-review gate checks an anchored review line, not reviewer identity or whether the verdict approves the final revision. Its chain performs a separate model review, but checking the response to findings is structural and the next session verifies the fixes. Tele-claude's checker is separate from the worker branch, but its author-email check is attribution, not authenticated identity. E-5, E-6, E-10.

**The apparent platform is larger than the configured platform.** The repository disables Maestro, metaloop, and orchestration families; runtime configuration can override that list. Their presence in source is not evidence of an operating learning loop. Conversely, the concurrent shared-harness supervision work should not be described as absent, nor counted as delivered merely because its draft documentation says “landed.” E-2, E-14, E-17.

**CI and deployment remain evidence questions.** Workflow files are present, while tele-claude's instructions say GitHub Actions has been disabled. I did not verify remote execution or required-check settings. The smoke's documented scope excludes cards, hooks, POST routes, and the dashboard. Neither a workflow file nor a smoke pass proves the entire factory works. E-13, E-16.

## What to take from Anthropic, and what to challenge

The most useful inspiration is its **Test** treatment of configuration evaluations and its **Maintain** treatment of feedback, rather than its inventory of documents. My conclusion is to test the behavior of the factory and connect delivery to observation using records already present. This is an architectural judgment, not an Anthropic result. [Article, Test and Maintain](https://claude.com/resources/articles/the-ai-native-sdlc-playbook); E-11, E-15.

<!-- charter: opinion -->
Five assumptions deserve resistance:

1. **Coding may still be the constraint for some work.** Separate owner queue time, execution time, review, integration, and release delay before deciding where to automate. A model taking hours on a difficult change and an owner taking minutes to accept it call for different investments than the reverse.
2. **Artifacts are not automatically useful handoffs.** Multiple documents can preserve the same misunderstanding at greater cost. Use one tasket for a small change; link a shared intent or design only when several units need it. Revising a plan after implementation can document drift without validating the original decision.
3. **Passing tests is bounded evidence.** A frozen test can miss the bug's important cases. A fresh reviewer can share the author's assumptions. Use an independently chosen counterexample or held-out scenario for consequential behavior; allow justified test changes with explicit review rather than banning all test edits.
4. **Automation requires congestion control.** If a trigger opens more work than the owner can judge, an incident loop becomes a backlog generator. Deduplicate, cap queued diagnoses, and stop admitting new work when acceptance is overloaded. Low-volume operational data also needs denominators and minimum sample sizes; statistical-looking thresholds are not automatically calibrated.
5. **Auditability and enforcement need distinct mechanisms.** A hash identifies bytes; it does not establish the legitimacy of the person authorizing them. A git author is not proof of identity. Keeping the owner in the narrative does not establish an authority boundary in the execution path.
<!-- charter: /opinion -->

Two technical details make the last point concrete. The playbook's illustrative production gate matches command text and checks an environment variable; by inspection, it is not a complete release-authorization mechanism. Actual hook behavior depends on event and configuration. Likewise, telemetry is not an automatic full-transcript archive: Anthropic's monitoring reference makes content collection opt-in, with truncation and tool-specific coverage. Use retained tool outputs and explicit receipts for evidence. These are implementation cautions about the examples, not reasons to reject the lifecycle approach. [Playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook), [hooks reference](https://code.claude.com/docs/en/hooks), [monitoring reference](https://code.claude.com/docs/en/monitoring-usage).

## Proposals and the trade between three directions

<!-- charter: opinion -->
| Direction | What changes | Best reason to choose it | Principal cost |
|---|---|---|---|
| Incremental improvement | Align verification contracts, add targeted replay cases, improve release evidence | Preserves useful working paths; smallest implementation risk | Can perfect task completion without improving product choices |
| Complementary outcome review | Link original problem, checked revision, delivered release, and later observation | Tests whether the factory produces value and where owner attention goes | Can become another bookkeeping layer if it copies records or adds approvals |
| Pivot to a portable assurance core | Charter becomes a small contract/verdict system; execution lives in adapters, with tele-claude one consumer | Removes competing runtime responsibilities and tests broader usefulness | Migration, compatibility, and loss of working integrations; demand outside this setup is unproven |

### P0 — Measure flow and reduce work in progress first

**Workflow:** take ten recent changes and classify where elapsed time and owner effort went. Prospectively follow ten comparable changes, with at most two items simultaneously waiting for owner acceptance. Finish, reject, or defer an item before admitting another. Urgent incidents get an explicit exception. Count a delivered outcome once even if it required several taskets.

**Ownership:** Gui chooses priorities and records brief active-attention estimates; tele-claude supplies existing wait/session events; Charter supplies tasket evidence and optional human-minute records. Start with a report, not a new service.

**Benefit and tradeoff:** potentially reduces context recovery and queue age without product code. It may idle agents and reduce apparent task throughput. Activity events are only proxies for attention, so manually validate a small sample and include time spent preparing, reviewing, answering, and recovering context.

**Smallest experiment and decision:** a five-working-day pilot, extended until ten comparable changes exist. Continue if at least 90% can be traced from request to delivery, owner minutes per useful outcome fall by at least 20%, and useful outcomes do not fall by more than 10%. Stop or revise the cap if delivery worsens without an attention benefit. Report all cases and medians; do not infer a reliable p95 from ten items. Unknown time and cost stay unknown.

### P1 — Make verification an explicit result, independent of the caller

**Workflow:** each closure produces a machine-readable result tied to the unit, base, evaluated revision, acceptance definition, checker version, commands, and retained output. Distinguish pass, fail, and undetermined. Record a human override separately. An exception, missing probe, stale revision, or unavailable checker must not satisfy an assurance-required transition. Authoring can continue when the check is unavailable; the system must not label it verified.

**Ownership:** Charter defines the portable contract and core record semantics; tele-claude retains dispatch, retries, human routing, and its checker adapter; the execution environment retains outputs. Owner Desk remains the interface for actual owner action. Start by wrapping existing results, not replacing the checker. Reconcile the differing perimeter and acceptance rules explicitly rather than silently forcing them to match.

**Benefit and tradeoff:** makes automated and interactive claims comparable and prevents a successful exit from overstating assurance. Costs include compatibility work and surfacing previously hidden “unknown” states. Use named enforcement settings independent of client/prototype status; a maintained internal product can need strong checks without a commercial scope file.

**Smallest experiment and decision:** eight synthetic cases through the CLI, chain, and automator adapters: valid pass, real failure, checker exception, absent probe, changed acceptance, changed test body, moved HEAD, and human override. Every unsafe or unknown case must avoid automatic verified status, every valid case must pass, and overrides must remain distinguishable. Fail the design on any false verified result. Then shadow ten real closures; investigate disagreements and reject the adapter if it adds more than one avoidable owner interruption per ten. Enable blocking only after the shadow run.

### P2 — Add outcome review as a projection of existing records

**Workflow:** for one substantive change, record the affected person or operation, current problem, desired observation, and review date in the tasket's context or a linked shared intent. Accept or reject the bet before decomposition. At delivery, link the release receipt. At the review date, compare the observed result with the original expectation and choose continue, adjust, stop, or revert. Link an incident or failed expectation to a new tasket or lesson; do not generate work automatically merely because a metric moved.

**Ownership:** the product owner chooses the outcome and whether it was worth doing; a service owner supplies operational observations; Charter remains the record of work and decisions; tele-claude renders the links and routes present-tense asks through Owner Desk. One component owns each state. There is no second task board or automatic reopening of a technically completed task.

**Benefit and tradeoff:** can expose well-built but useless work, forgotten deployment, and recurring problems. Sparse usage may make the result inconclusive, and attribution may be confounded by other changes. “Not observed yet” is a valid state. Future review dates belong in planning, not as premature Owner Desk asks.

**Smallest experiment and decision:** three changes in one maintained project, followed for two weeks or an agreed usage window. Give each a predeclared result, such as fewer failed checkout attempts per attempt, or fewer owner interventions per completed automation run. Continue if at least two receive a credible observation, the review changes at least one real decision, and bookkeeping takes at most five owner minutes per change. Drop the separate layer if it supplies no decision beyond the existing tasket; retain only useful fields and links.

### P3 — Evaluate the factory's configuration, not just its Python

**Workflow:** turn recurring factory mistakes into replayable tasks with an expected behavior and an independent scoring fixture. Record model identifier, harness version, instructions, skill and hook revisions, tools, initial workspace, and budget. Run before promoting a configuration change. Keep normal software tests separate from behavioral evaluations; neither substitutes for the other.

**Ownership:** Charter maintains portable contract cases; tele-claude owns harness delivery, restart, and supervision cases; the owner or an independent reviewer approves expected outcomes. The relevant skill owner maintains that skill's cases. Link an incident to its regression case and a decision's expiry to a reassessment, not endless additions to global instructions.

**Benefit and tradeoff:** catches changes that preserve parser tests but worsen agent behavior. Model variability, cost, and fixture leakage can obscure results. Keep held-out cases and repeat failures; a small all-green suite is not a safety guarantee.

**Smallest experiment and decision:** six historical failure cases plus two ordinary successful tasks. Compare the current setup with one candidate change, three runs per case, in disposable workspaces with a fixed spend ceiling. Require no new false-done or unauthorized-action outcomes, at least 20% fewer corrections on the targeted failure class, and at most 25% more cost per accepted result. If the baseline failures cannot be reproduced, improve the cases before judging the candidate. Do not begin with nightly fleet-wide evaluations.

### P4 — Carry verified identity through delivery

**Workflow:** produce a release manifest containing the code revision/tree, built frontend digest, relevant configuration and dependency identities, verification results, and rollback target. Owner Desk presents the exact candidate. The release runner deploys it, records the running identity, and exercises one changed user path plus health. A later checkout edit cannot silently redefine that candidate. Rehearse rollback with state compatibility considered separately from code rollback.

**Ownership:** extend the existing tele-claude packaging/release work; the release runner owns environment changes, Charter references its evidence, and Owner Desk conveys authorization. This is not a new Charter deployment subsystem or a second packaging initiative.

**Benefit and tradeoff:** closes the gap between reviewed code and delivered behavior. It costs build/storage effort and a migration away from convenient shared-checkout coupling. A release hash does not prove that a database rollback is safe.

**Smallest experiment and decision:** one disposable environment, one backend/frontend change, and one rollback. Require exact agreement between checked and running identities, a successful changed-path check, rejection of a stale candidate, and restoration of the prior code within a proposed five-minute recovery target without losing seeded state. Reject the design if mutable checkout contents can alter an approved release. Production migration follows only after the separate release initiative demonstrates this.

### P5 — Test the portable-core pivot without performing the migration

**Workflow:** apply the same contract and verdict to one small change driven from tele-claude and one driven by a plain CLI/CI adapter. Keep taskets and decisions as the authoritative project records. Prototype an adapter outside the distributable package. If portability proves useful, move execution, session-budget policy, and owner-action transport out of Charter's core behind maintained adapters; preserve current behavior through compatibility support.

**Ownership:** Charter owns formats and validation; the consuming runtime owns scheduling and isolation; deployment tooling owns releases; Owner Desk is an optional owner interface. A component move is justified by a stable responsibility boundary, not by its language or directory.

**Benefit and tradeoff:** reduces overlap and permits adoption without the whole dashboard. It can strand valuable chain/delegate behavior and create migration work whose payoff exists only outside the current user base.

**Smallest experiment and decision:** two disposable repositories and the same eight P1 fixtures through both adapters. Require identical verdict semantics without importing tele-claude runtime services, no loss of needed owner handling, and a second operator or project demonstrating a real use case. Reject the pivot if it merely relocates complexity or the adapter needs as much ceremony as the current stack. Architectural portability alone is insufficient evidence of product demand.
<!-- charter: /opinion -->

These proposals extend rather than rediscover existing work: the checker is already designed without engine imports; an earlier Charter review proposes separating scope policy from enforcement strength; and tele-claude's packaging proposal already names a release initiative. Those facts favor small adapters and coordinated experiments. They do not establish that the proposals above have been implemented. E-6, E-19, E-20.

## Recommendation and practical sequence

<!-- charter: opinion -->
Choose **incremental assurance improvements plus a small complementary outcome review**, with the portable-core pivot kept as a tested alternative. The current factory has useful mechanisms worth preserving. The strongest unproven link is between those mechanisms and useful delivery for the owner's time.

1. **Baseline first:** run P0's retrospective and prospective sample. Separate code execution, owner waiting, active attention, review, integration, release, and observation. Track defects and rework alongside throughput; record subscription usage separately from estimated API cost.
2. **Resolve meanings:** run P1's fixtures and define verified, human-credited, delivered, and observed. Correct stale integration documentation in a later implementation task. Choose one execution path for each pilot; do not nest Charter chain scheduling inside tele-claude scheduling for it.
3. **Observe three outcomes:** run P2 manually before building a UI. Use the existing taskets, release evidence, and Owner Desk. Keep the workflow only if it changes decisions cheaply.
4. **Build assurance where failure warrants it:** run P3 on the recurrent failure class found in the baseline. Progress P4 through the existing packaging effort; require a verified delivery path before treating deployment as an automatic consequence of a checker pass.
5. **Decide architecture from evidence:** run P5 if cross-runtime inconsistency or duplicate maintenance remains a major cost. Retire or move one overlapping responsibility at a time; preserve consumers throughout migration.

The first decision point is after ten traced changes and three outcome reviews, not after building another platform. If most owner effort is mechanical handoff, prioritize adapters and release preparation. If most is choosing or correcting objectives, invest in intake and outcome review. If execution dominates, improve task decomposition, tools, or model configuration instead. Continue to treat quality, cost, and recoverability as constraints on the throughput result.
<!-- charter: /opinion -->

## Strongest case for the alternative: pivot now to a portable assurance core

<!-- charter: opinion -->
*The advocate's case:* Charter's distinctive value is an inspectable work contract. Every additional scheduler, session convention, delegate, and personal integration makes that value harder to extract. Tele-claude is already a substantial operating environment. Adding an outcome layer risks becoming a third coordinator over two systems whose semantics still differ.

The right move is subtraction: publish a small contract for proposed work, evidence, verdict, and authorized exceptions; make an ordinary runner able to consume it; and let tele-claude be one excellent interface. Separate transport from truth. Validate on a project that does not use this owner's dashboard. This would force clear boundaries, reduce vendor and harness assumptions, and reveal whether Charter is a reusable product rather than a local operating method. Measurements and outcome review can then attach to a simpler foundation.
<!-- charter: /opinion -->

## Does that change the recommendation?

<!-- charter: opinion -->
Not yet. I have **moderate confidence** in the recommended direction, high confidence in the identified code-level distinctions, and low confidence in any numerical productivity forecast. The investigation does not establish that duplicate orchestration is the dominant current cost or that an outside operator wants the portable core.

I would switch toward the pivot if a twenty-change follow-up showed that over 30% of measured owner or maintenance effort went to reconciling execution/verification paths, and P5 removed at least half that effort without losing needed capabilities. A successful second-operator pilot would strengthen the case. Conversely, if outcome review fails to change any decision in six completed observation windows or persistently exceeds its five-minute budget, I would drop the complementary layer and retain only incremental improvements.

The deliberately smaller bet is to establish a chain of evidence from “wanted” to “verified” to “delivered” to “helped,” while keeping each responsibility with a component or person that already owns it.
<!-- charter: /opinion -->

## Evidence index

- E-1 — Primary sources: [article](https://claude.com/resources/articles/the-ai-native-sdlc-playbook) and [PDF](https://cdn.prod.website-files.com/6889473510b50328dbb70ae6/6aba736348bdf4f08183f463_AI%20Native%20SDLC%20Playbook_designv2%20%281%29.pdf), accessed 2026-10-24. `$ pdfinfo /tmp/charter-sdlc-research-20261024/playbook.pdf` reports 54 pages; `$ pdftotext -layout /tmp/charter-sdlc-research-20261024/playbook.pdf /tmp/charter-sdlc-research-20261024/playbook.txt` produced the text inspected. No source PDF or extraction was added to the repository.
- E-2 — Snapshot commands: `$ git -C /home/gui/Projects/charter status --short`, `$ git -C /home/gui/Projects/charter branch --show-current`, `$ git -C /home/gui/Projects/charter rev-parse HEAD`; Charter was clean at a2067b4. `$ git -C /home/gui/Projects/tele-claude rev-parse HEAD` returned `adbe51a87173667ecd48f34ce381100bd042ef1e` in that other repository; its branch was main and status listed 41 changed entries at the final research check. Staged supervision adapters and untracked packaging documents were present. The other repository's commit is recorded here as an external snapshot identifier, not a Charter commit (outside this repository).
- E-3 — Charter's artifact ownership and tasket design: `docs/method.md:29`, `docs/method.md:202`, `package/charter/templates/unit.md:18`; path-based scope implementation: `package/.charter/checks.py:84`, with its semantic limit at `docs/gates.md:175`. Installation is separately governed by `docs/install.md:1` and source-repository behavior by `AGENTS.md:1`.
- E-4 — Decisions, memory, and commitments: `package/charter/templates/decision.md:7`, `package/.claude/rules/charter.md:53`, `package/.charter/checks.py:876`.
- E-5 — Structural done/review checks and acceptance-change behavior: `package/.charter/checks.py:389`, `package/.charter/checks.py:429`, `package/.charter/checks.py:439`. Optional probe execution and baseline checks: `package/.charter/bin/charter:122`, `package/.charter/bin/charter:169`, `package/.charter/checks.py:592`; defaults: `package/charter/config.json:11`. Error exit behavior: `package/.charter/bin/charter:1295`, `docs/gates.md:161`. Relevant tests were read, not run: `tests/test_probe_at_base.py:32`, `tests/test_review_required.py:20`.
- E-6 — Tele-claude checker implementation: `/home/gui/Projects/tele-claude/services/checker/core.py:451`, `/home/gui/Projects/tele-claude/services/checker/core.py:479`, `/home/gui/Projects/tele-claude/services/checker/core.py:537`; preflight self-grading warning: `/home/gui/Projects/tele-claude/services/automation_preflight.py:159`; separate invocation and dirty-tree refusal: `/home/gui/Projects/tele-claude/services/step_close.py:321`, `/home/gui/Projects/tele-claude/services/step_close.py:344`. Engine independence is documented at `/home/gui/Projects/tele-claude/docs/CHECKER.md:11`.
- E-7 — Integrated tasket keys: `/home/gui/Projects/tele-claude/services/project_tasket_reader.py:229`; worker attribution: `/home/gui/Projects/tele-claude/services/step_close.py:138`; credited state and closure freshness: `/home/gui/Projects/tele-claude/services/step_close.py:663`. Group execution states: `/home/gui/Projects/tele-claude/docs/GROUP_AUTOMATOR.md:33`.
- E-8 — Intake implementation: `/home/gui/Projects/tele-claude/services/guided_project_inbox.py:86`, `/home/gui/Projects/tele-claude/services/guided_project_inbox.py:117`; project result retrieval: `/home/gui/Projects/tele-claude/services/guided_project_results.py:1`. An exported inbox note remains for the project's own session to adopt.
- E-9 — Owner boundaries and delegation: `package/.claude/rules/charter.md:42`, `package/.charter/delegate.py:1`; Owner Desk consumes the package protocol: `/home/gui/Projects/tele-claude/services/owner_desk/detectors/charter.py:71`. Payload identity and execution: `/home/gui/Projects/tele-claude/services/owner_desk/store.py:257`, `/home/gui/Projects/tele-claude/services/owner_desk/runner.py:193`, `/home/gui/Projects/tele-claude/services/owner_desk/runner.py:214`. Filing and derivation rules: `/home/gui/Projects/tele-claude/docs/OWNER_DESK.md:49`, `/home/gui/Projects/tele-claude/docs/OWNER_DESK.md:263`.
- E-10 — Chain/group responsibility and review semantics: `package/.charter/chain_groups.py:1`, `package/.charter/chain_groups.py:86`, `package/.charter/chain_groups.py:164`, `docs/method.md:226`. Separate review can be configured off; a review response's form does not prove its truth.
- E-11 — Cost and attention: `package/.charter/hooks/session_end.py:47`, `package/.charter/hooks/session_end.py:71`, `docs/method.md:187`, `docs/method.md:222`; tele-claude activity schema and loss-on-error behavior: `/home/gui/Projects/tele-claude/services/activity_ledger.py:76`, `/home/gui/Projects/tele-claude/services/activity_ledger.py:121`. Harness quota readings are a separate concept: `/home/gui/Projects/tele-claude/services/harness_usage.py:1`.
- E-12 — Delivery detection: `/home/gui/Projects/tele-claude/services/owner_desk/detectors/restart.py:80`, `/home/gui/Projects/tele-claude/services/owner_desk/detectors/restart.py:90`, `/home/gui/Projects/tele-claude/services/owner_desk/detectors/dist.py:52`, `/home/gui/Projects/tele-claude/services/owner_desk/detectors/dist.py:61`.
- E-13 — Shared-checkout deployment and smoke scope: `/home/gui/Projects/tele-claude/AGENTS.md:156`, `/home/gui/Projects/tele-claude/docs/SANDBOX.md:14`, `/home/gui/Projects/tele-claude/docs/SANDBOX.md:215`. These are repository descriptions; production execution was not independently observed in this investigation.
- E-14 — Disabled families and runtime override: `/home/gui/Projects/tele-claude/config/surface.yaml:21`, `/home/gui/Projects/tele-claude/services/surface_flags.py:86`, `/home/gui/Projects/tele-claude/services/main.py:640`. Health monitoring has its own narrower purpose: `/home/gui/Projects/tele-claude/services/health_monitor.py:1`.
- E-15 — Skill versioning is not a task-replay evaluator: the inspected publish path stages, commits, and optionally pushes changes at `/home/gui/Projects/tele-claude/services/skill_manager.py:571`; the feature is described as version control at `/home/gui/Projects/tele-claude/docs/SKILL_MANAGEMENT_API.md:383`. No whole-factory behavior evaluation is established by those paths; this is a bounded finding, not a claim that no other evaluator exists.
- E-16 — Tele-claude's explicit opt-ins: `/home/gui/Projects/tele-claude/charter/config.json:310`; version fields: `/home/gui/Projects/tele-claude/charter/config.json:2`, `/home/gui/Projects/tele-claude/charter/VERSION:1`. Workflow files: `/home/gui/Projects/tele-claude/.github/workflows/ci.yml:48`, `/home/gui/Projects/tele-claude/.github/workflows/charter.yml:15`; instruction saying Actions is disabled: `/home/gui/Projects/tele-claude/AGENTS.md:222`. Remote workflow status was not checked.
- E-17 — Existing harness launch boundary: `/home/gui/Projects/tele-claude/services/harness_launch.py:1`. Concurrent staged supervision document: `/home/gui/Projects/tele-claude/docs/HARNESS_SUPERVISION.md:20`. Its reported test results were not rerun or treated as this investigation's validation.
- E-18 — Stale engine-seam description: `docs/method.md:234`, compared with E-7. Correct the reference in a later change; this report preserves existing records and product files.
- E-19 — Concurrent packaging initiative and its stated implementation status: `/home/gui/Projects/tele-claude/docs/PACKAGING.md:1`. This document was untracked during inspection; its claimed owner choice was not independently verified, and no deployment was inferred from it.
- E-20 — Earlier proposal to separate commercial scope from enforcement strength: `docs/review/2026-10-19-client-specificity.md:61`. This dated record is cited, not rewritten.

## Deliverable validation

Only this new dated report was written in the workspace. `$ python3 -B package/.charter/bin/charter anchors docs/review/2026-10-24-ai-native-sdlc-factory-review.md` passed with no unanchored claims or unresolved references; the command checks reference form and resolution, not whether the cited evidence entails each conclusion (`package/.charter/checks.py:1298`). Recommendations and experiment designs are explicitly marked as opinion so that they are not represented as observed results. No product files were changed, and no branch was switched or commit made.
