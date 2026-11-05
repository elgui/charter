# Agent verification before owner work

Status: proposed design, 3 November 2026. No runtime enforcement or project upgrade is implemented by this note (operator report: this change).

## Existing seams

- Charter distributes rules, unit templates and CLI checks through its owned package files; the installer also manages a section of each project's AGENTS.md. This is the route to future projects and upgrades (`bin/charter-pkg:38`, `bin/charter-pkg:179`, `bin/charter-pkg:243`).
- Charter already exports acceptance identity and a fingerprint, separately from the action a criterion describes. Closing a protected criterion remains an owner act (`docs/design/owner-acceptance.md:5`).
- Required review currently means an anchored `review:` line, not authenticated reviewer independence. Executing probes is a separate opt-in (`docs/verification.md:13`).
- Tele-Claude's filed-check validator requires observation instructions but no evidence of prior agent checks or human necessity (`/home/gui/Projects/tele-claude/services/owner_desk/record.py:251`).
- Tele-Claude already keeps PR preparation separate from owner outcomes, invalidates it on a changed head, and suppresses readiness when preparation has a blocker (`/home/gui/Projects/tele-claude/services/owner_desk/pr_review.py:47`).
- Its proposal-readiness path already rechecks prerequisites before an owner ruling. Its Charter detector is the adapter for repository obligations (`/home/gui/Projects/tele-claude/services/owner_desk/readiness.py:1`, `/home/gui/Projects/tele-claude/services/owner_desk/detectors/charter.py:1`).
- Codex cards already receive Desk instructions outside the current repository. Project AGENTS.md alone cannot cover cards in future, unrelated projects (`/home/gui/Projects/tele-claude/services/harness_launch.py:51`).

<!-- charter: opinion -->
## One rule, three enforcement points

Agents own executable verification and technical review. An owner request contains only the remaining decision, authorization, private interaction or physical/personal observation. A failed check returns work to agents; an unknown result stays unknown. Neither becomes a human test merely because the worker stopped.

Use one versioned preparation contract across the three points. Charter owns acceptance identity and the declared human need; Tele-Claude owns execution records, independent review and readiness at the owner boundary. A standalone Charter project can supply evidence through another runner. Charter must not import Tele-Claude, assume its paths or require its service to run.

Do not add tasket statuses, a new task queue, a project-specific skill or another completion checkbox. Reuse Acceptance, Evidence, owner exports, Desk preparation and the existing open/unready distinction.

## 1. Shared instructions: distribute the rule through existing doors

Charter's package rules and unit skill carry the portable policy. Its installer-managed AGENTS.md section directs every harness to that policy. New installs receive it automatically; existing installs receive it through the normal release/upgrade procedure.

Tele-Claude keeps one small instruction fragment for cards, including projects without Charter. Each supported harness adapter loads that fragment on launch/resume through its supported mechanism; generated copies are checked for drift. Do not rely on the project containing Tele-Claude's AGENTS.md. Do not rewrite global agent configuration or silently change protected launch policy to deliver this feature.

The fragment says:

> Before requesting owner work, run applicable authorized checks and inspect their results. Use available service, browser and diagnostic tools. Obtain independent technical review for the change. Record the evidence and identify the exact part only the owner can supply. Failed or incomplete agent preparation remains agent work. Authorization to act and verification of the result are separate.

Detailed tool recipes stay in existing runner/review adapters, rather than being copied into every prompt. Loading the instruction is tested separately from enforcement; a model repeating the rule is not proof that it followed it.

## 2. Charter: justify human assignment when criteria are written

Ordinary criteria remain agent-owned by default. Keep the existing `owner: check|do|decide` syntax for compatibility. Add a small structured `owner_needs` mapping in tasket frontmatter, keyed by AC label, only for criteria assigned to the owner.

Illustrative proposed authoring shape, not currently executable:

```yaml
owner_needs:
  AC-3:
    reason: personal_judgment
    remaining: Approve whether the revised onboarding tone fits the audience.
```

Allowed reasons describe a real boundary: `personal_judgment`, `physical_observation`, `private_interaction`, or `reserved_authority`. A service query, automated browser check or independent code review is not a human reason. Tool unavailability is an agent preparation blocker, not a permanent human classification.

Every new or materially changed owner criterion requires a supported reason and a concrete remaining task. The gate checks structure; independent review checks whether that explanation actually requires a person. It must also examine probes for relevance: `true` is not verification.

Make this an incremental default gate for new/changed owner assignments, not another disabled opt-in. Upgrading a project must not depend on rewriting its seeded config file. Keep the broader, existing `review.required` setting distinct: this proposal enforces review of technical preparation at the owner boundary, rather than requiring a model invocation for every edit or every observation in every project.

Separate criteria when actors differ. For example, AC-1 is an authorized restart; AC-2 is an agent's health/readiness/browser checks after the restart. A passing health query cannot authorize the restart, and authorization cannot substitute for running the query. Checks dependent on the owner's action are explicitly deferred until after it; they do not block the authorization request or pretend to have passed already.

Export the need through the existing `owner --json` acceptance item. Extend the versioned acceptance fingerprint to bind the human need as well as criterion identity. Changing the reason or remaining task invalidates old preparation. Evidence and Log additions alone should not invalidate an otherwise unchanged observation contract.

Existing protected criteria remain protected. Missing legacy declarations produce preparation work; agents cannot remove owner markers, tick boxes or reinterpret old approvals to migrate them. A genuine reassignment uses the existing owner-authorized amendment route.

## 3. Owner Desk: preparation is a prerequisite to human readiness

Generalize the existing PR preparation operation to filed checks and derived owner criteria. Use the same validation/readiness function for CLI, API, browser, dealt-hand selection and the final owner operation. Presentation-only filtering is insufficient.

One preparation record contains references rather than copied reports:

| Field | Purpose |
|---|---|
| `subject` | Project identity, criterion/ask identity, acceptance fingerprint and the exact artifact or environment being checked. |
| `checks` | Runner receipts for applicable commands or tool observations: subject digest, timestamp/timezone, command/tool, result and output reference. Explicitly record failed, unknown, inapplicable and deferred checks. |
| `review` | Independent review receipt: author provider, reviewer provider/model, reviewed subject digest, verdict, coverage, findings and their disposition. |
| `human_need` | Supported reason and the exact remaining task; reference Charter's declaration when present. |
| `blockers` | Concrete preparation work, responsible session and retry condition. No elapsed timeout converts this into an owner task. |

For changes, use a pinned commit/diff and relevant criterion digest; uncommitted work needs an explicit snapshot digest and cannot masquerade as a committed review. For environment observations, bind the deployment/resource identity and observation window rather than using a repository SHA as proof of live state. Freshness requirements follow what can change; do not impose one arbitrary lifetime on all checks.

The runner writes execution/review receipts; worker-authored prose only points to them. Validate receipt provenance through the runner's existing trust boundary, not a worker-supplied `provider: anthropic` label. This improves attribution; it cannot prove that a model's judgment is correct. Locally editable records alone must not be described as tamper-proof.

Receipt production is new integration work, not a capability established by today's anchored `review:` lines. The Desk must resolve a receipt against executions it observed or a supported runner adapter it trusts. A worker cannot satisfy that lookup by supplying arbitrary JSON. Defining and testing that producer/consumer boundary is part of the first delivery slice.

Readiness has three ordinary results:

- Preparation missing, failed or stale: keep the existing ask open and unready, return the next step to an agent, and exclude it from the owner's actionable hand and needs-you count.
- All verification is agent-owned: record its outcome through the appropriate agent evidence path; do not create a human check or fabricate an owner Pass receipt. Existing owner asks are reassessed without overwriting their history.
- Preparation sufficient and a human boundary remains: show the owner the remaining task, a concise evidence summary and uncertainties. The final owner operation rechecks the binding and readiness before recording anything.

Use existing session ownership/notification and normal project work continuation to return preparation to an agent. If that session no longer exists, expose the blocker in project work for an agent to pick up. Unready work remains discoverable; suppressing an owner invitation must not erase the work or claim that an automatic retry occurred.

Apply this to both filing and detector-derived work, including PRs and HUMAN-ONLY/gate sources. A different `because` class or changing `check` to `decide`/`do` must not bypass preparation of the technical claims attached to the request.

Actual decisions, authorization and login/physical prerequisites need an explicit lightweight path: prepare what is possible beforehand, declare dependent checks deferred, ask for the prerequisite, then return verification to the agent. Do not demand an impossible post-action review before allowing the action. A reviewer outage produces a review blocker; recovery or an explicit owner exception is distinct from asking the owner to do the review.

## Independent review without repeated ceremony

Route by actual model provider, not harness name: OpenAI-authored changes receive Anthropic review; Anthropic-authored changes receive OpenAI review. A pi harness can use either provider. Other or unknown author providers require an explicit supported routing policy; no automatic claim of independence.

Adapt the existing review helpers behind a common receipt interface. The reviewer receives the pinned change, relevant instructions, checks and proposed human assignment, and verifies both technical correctness and whether the remaining task truly needs a human. The worker resolves findings and reruns affected checks; relevant changes invalidate review and require re-review.

One review can cover a coherent change and several criteria. Reuse its receipt while its declared scope and dependencies remain unchanged. Do not launch a reviewer for each passing probe or each routine observation. Lightweight prerequisite requests can record why technical change review is inapplicable. Batch related findings and bound retries; disagreements remain explicit rather than spinning indefinitely or quietly falling back to the owner.

## Delivery sequence and proof

1. Define the contract and implement Desk preparation/readiness on an isolated branch, including non-Charter filed work. Adapt existing review execution and record provenance. Test both provider directions with deterministic fixtures; perform bounded real integrations once the adapter is ready.
2. Release Charter with the criterion declaration, shared rules, templates, gate and owner export. Exercise the real candidate package against the Desk adapter in the existing cross-repository acceptance test pattern.
3. Wire the shared card instruction to every supported harness entry point. Check protected policy before changing launch behavior; prepare any necessary owner ruling separately. Test launch, resume and worker paths without overwriting global config.
4. Deploy the backward-compatible Desk consumer first, then upgrade projects by the documented Charter procedure. Review existing open checks as migration work; preserve approvals, hashes and outcomes. Package installation and Desk deployment remain separate operations.

Required regression scenarios:

- A freshly installed project gets the rule and refuses a newly unjustified owner criterion; an upgraded project preserves unrelated instructions.
- A non-Charter project is subject to the same Desk boundary.
- A browser/API/service check returns to an agent; a real preference, physical observation or private login reaches the owner with completed prerequisite checks.
- An owner-authorized restart becomes ready with post-restart checks deferred; after execution those checks return to the agent.
- Missing, forged/self-labelled, stale, wrong-provider or unrelated receipts cannot satisfy readiness. A valid scoped review can cover several criteria without repeated launches.
- Changed source, criterion/human need, environment identity or unresolved finding invalidates preparation. Unrelated Log edits do not.
- Filed, derived, CLI/API and dealt-hand paths agree. A direct owner operation cannot bypass readiness through a presentation gap.
- Unknown results and unavailable reviewers remain explicit agent blockers. No timeout or retry exhaustion creates an owner verdict.
- Legacy criteria and receipts remain readable and protected; no migration invents an observation, replays approval, silently declines an ask or changes delegation authority.

Success means fewer avoidable owner checks with at least the same applicable verification coverage. Evaluate against a sampled queue of real requests classified before and after the change, retaining links to the executed checks, reviewed subjects and remaining human work. A smaller queue alone is not evidence of improvement.
<!-- charter: /opinion -->
