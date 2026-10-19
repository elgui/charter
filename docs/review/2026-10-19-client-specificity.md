# Charter client specificity assessment

Assessment date: 2026-10-19. Baseline: commit 76de1a9, package version 0.4.16 (`package/VERSION`). This record evaluates the current implementation separately from possible broader positioning.

## Conclusion

(inference) Charter is broader than client delivery, but narrower than a generic project methodology. Its reusable core controls agent work in a Git repository: define a unit, record decisions, require evidence, and reserve governance decisions for an accountable owner. Client scope is a meaningful specialization of that core.

The README frames Charter as a working method for projects built with coding agents, while the full method still has a client-project title (`README.md:3`; `docs/method.md:1`).

<!-- charter: opinion -->
The broad README framing is defensible. A precise supporting description is: “Charter is a repository-based method for agent-assisted software work, with a client-delivery track for agreed scope and change requests.” Calling it a general project methodology would imply a breadth the current workflow does not supply.
<!-- charter: /opinion -->

## Actual track differences

| Behavior | Client | Prototype | Source |
|---|---|---|---|
| Explicitly excluded paths | Block without an approved change covering the path | Scope gate off | `package/.charter/checks.py:84` |
| Open unit scope reference | Unknown IDs block; missing reference warns | Not checked | `package/.charter/checks.py:108` |
| Missing scope file | Warning, although the method calls it required | Not required | `package/.charter/checks.py:90`; `docs/method.md:208` |
| Outside the active unit's perimeter without a note | Block at commit | Warning | `docs/gates.md:104` |
| Deliverable anchoring | Blocking mode | Warning mode | `docs/gates.md:126`; `docs/method.md:214` |
| Done evidence, decision checks, size limits | Enforced | Enforced | `docs/method.md:210` |
| Probe execution, independent review, required rails | Configurable opt-ins | Same opt-ins | `package/charter/config.json:9`; `docs/gates.md:205` |

The scope gate enforces explicit exclusions, not complete coverage by an approved deliverable. It iterates out-of-scope path globs. Missing scope references and mismatched perimeter coverage warn; work outside every listed deliverable is not automatically blocked (`package/.charter/checks.py:84`; `package/.charter/checks.py:108`).

(inference) For example, excluding `app/invoicing/**` protects against an agent starting an invoicing subsystem there. Adding an unrequested discount feature inside an allowed checkout module can pass that protection. The owner must still judge whether the feature belongs: the gate cannot see semantic scope changes within an allowed path (`docs/gates.md:175`).

## Assumptions and tradeoffs

**Commercial agreement.** The scope template asks for a signed devis, sold deliverables, client acceptance, and assumptions behind the price. The adoption procedure assigns the client track only to projects covered by a signed quote or contract (`package/charter/templates/scope.md:3`; `docs/install.md:37`).

(inference) That language fits client work. It would impose an artificial commercial model on internal maintenance if it were required everywhere. The prototype track already avoids that requirement.

**Accountable ownership.** Scope, roadmap, configuration, and protected decision fields route to the owner. The method describes a person working alone with agents, with an independent reviewer or the owner settling disputes (`package/.claude/rules/charter.md:28`; `docs/method.md:16`).

(inference) This fits a solo developer directing agents particularly well. A team with distributed product and technical authority would need clearer role allocation. Central authority makes escalation legible but concentrates decisions and attention.

**Repository-local units.** Taskets hold acceptance criteria, evidence, and continuation logs. The BMAD migration replaces execution stories and sprint status with taskets; it retains planning artifacts as inputs (`package/charter/templates/unit.md:1`; `docs/migration.md:31`).

(inference) Keeping the work and its evidence together reduces lost context. Adoption nevertheless changes the work artifact; Charter is more opinionated than a collection of checks attached to any existing tracker.

**Observable acceptance.** Criteria name runnable probes. The supplied configuration leaves automatic probe execution and independent review requirements off. The gates check evidence records, not whether evidence establishes the criterion (`package/charter/templates/unit.md:22`; `package/charter/config.json:12`; `docs/gates.md:174`).

(inference) This fits implementation and maintenance. Exploratory research and aesthetic judgment need carefully chosen intermediate deliverables and human acceptance. A passing command cannot settle those judgments. Recordkeeping buys reviewability, not proof of correctness.

**Installed package and agent harness.** Adoption includes a versioned package, per-clone setup, and upgrades. Claude Code receives session integration; other agents read repository instructions and encounter Git and CI checks (`docs/install.md`; `docs/daily-use.md`).

(inference) The repository checks are portable, while the depth of agent integration varies. Setup and upkeep are part of the cost even for a project with no client. A project does not need the original tasket engines to use the documented CLI loop (`docs/daily-use.md`, sections 2 and 3).

## The mature product without a client

The install procedure assigns projects without a signed contract to `prototype`. That track also weakens perimeter and deliverable anchoring enforcement. Rails and stricter probes and review are available on both tracks (`docs/install.md:37`; `docs/method.md:202`; `docs/gates.md:205`).

(inference) An internal service with a release roadmap and strict review requirements exposes the mismatch: commercial relationship and enforcement strength are separate questions, but the current presets couple them. A mature product can lack a client, while an experiment can deserve strict evidence controls.

## Recommendation and adoption path

<!-- charter: opinion -->
Keep the broad README framing with the precise supporting description above. Position Charter around repository-based agent-assisted software work, and present commercial scope as a specialization.

For adoption today, follow `docs/install.md`: use the prototype track for a non-client project, add rails when it has a roadmap, and enable probe and review opt-ins as the workflow supports them. Be explicit that perimeter and anchoring checks remain warnings on that track. Do not invent a commercial contract merely to obtain stronger checks.

For a future release, separate scope policy from enforcement strength. Preserve `client` and `prototype` as compatible presets, while making perimeter and anchoring strictness independently selectable. Add a maintained internal product to the adoption examples. This is a proposed design change, not a capability of the current configuration.

Any implementation should preserve existing projects' behavior during upgrade and follow the repository's package release procedure. The useful next step is a focused policy design and migration specification, rather than an immediate rename of the tracks.

Do not yet position Charter as a universal project framework. Its strongest supported value is a durable work record and enforceable checkpoints for coding agents, with humans responsible for the meaning of the evidence.
<!-- charter: /opinion -->
