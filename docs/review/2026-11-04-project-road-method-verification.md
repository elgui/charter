# Project Road methodology verification, 4 November 2026

The documentation connects road preparation, units, decisions, probes, independent review, chains, external supervision and remaining owner work. The new integration design provides ten acceptance scenarios and a finite six-step implementation sequence. Existing reference docs and the canonical map builder changed; no package release, machine layer or dated record was changed (`b59bbe9`, `f1b1fd3`, `docs/design/project-road-control-center.md`).

## Isolation and source status

Work is on `docs/project-road-method-20261104`, based on local integrated documentation revision `f382868`. The inherited shared checkout remains at `878e98b` on `design/agent-verification-before-owner`, clean. Published Charter main was `b2df24e`, package 0.4.22; the extra local base work is documentation. Tele-Claude's separately prepared implementation worktree starts at its published main containing the existing Road, SVG redesign and readiness prompts. Its source references are pinned in the integration inventory (`$ git worktree list --porcelain`, `$ git status --short --branch`, `$ git diff --name-only b2df24e f382868`, `docs/design/project-road-control-center.md`).

The spec recipe at `dee2f42` is implemented but unreleased. PR #37 was open at `702b5fd`, a proposal only. Tele-Claude's inspected installed manifest records 0.4.21. These three facts prevent the UI from claiming source/draft behavior is already installed (`$ git rev-parse charter-spec-draft`, `$ gh pr view 37 --json state,headRefOid,mergedAt`, `docs/review/2026-11-03-spec-design-verification.md`, `docs/design/project-road-control-center.md`).

## Checks and observed results

The full command in `AGENTS.md` ran in the owned worktree's tests directory with resolved `TMPDIR`, Python `-B`, no quiet flag, in the background. Result: **752 tests in 861.987 seconds; OK, one skipped**, observed on 2026-11-04 UTC. There were no FAIL or ERROR blocks. Non-fatal subprocess/unclosed-file ResourceWarnings and a chain fixture's trailing “session 1 is already closed” line remain in the log; neither is omitted from the evidence (`$ python3 -B -m unittest` with the exact 34-module list in `AGENTS.md:16`, private `charter-tests.log` in the evidence directory below).

| Check | Result and practical limit | Source command |
|---|---|---|
| Changed Markdown anchors | README, method, daily use, verification, integration design and generated maps pass: no unanchored claim or unresolved anchor. Existing installed-project path examples and historical paths are reported missing in the source repository, without blocking. Anchoring proves resolvability, not truth. | `$ python3 package/.charter/bin/charter anchors README.md docs/method.md docs/daily-use.md docs/verification.md docs/design/project-road-control-center.md docs/maps.md` |
| Canonical map generation | All six SVGs, HTML and text edition regenerated. Exact output comparison, XML parsing, per-view unique IDs and eight shared journey stages pass. | `$ python3 docs/assets/maps/build.py`; private `check_map_consistency.py` |
| Builder syntax / whitespace | Pass. | `$ python3 -m py_compile docs/assets/maps/build.py`; `$ git diff --check` |
| Browser rendering | Chromium on the Tele-Claude VPS: desktop and narrow viewport, keyboard capability selection, dark mode, journey text alternative and no page errors pass. Journey text stays within the SVG viewBox; new journey and chain images were visually inspected. Local files only, no authentication or owner-device trial. | Private `$ python check_maps.py` using Playwright; `docs/assets/maps/journey.svg`, `docs/assets/maps/chain.svg` |
| Handoff fit | MetaPrompt selected AstraRules with exact catalogue fit; A1, A2, A3, A4, adapted A5, A7, A8 and A11. Lint passes. The source-guide checksum changed; the fetched guidance was read, and the selected behavioral blocks agree. Model/effort stay explicitly requested gpt-6-astra/xhigh. | `$ bun ~/.claude/skills/MetaPrompt/tools/ResolveModel.ts --harness codex --model gpt-6-astra`; `$ bun ~/.claude/skills/MetaPrompt/tools/CheckGuides.ts --only astra`; `$ bun ~/.claude/skills/MetaPrompt/tools/LintPrompt.ts --model astra --repo <registered-parent> <briefing>` |

Evidence is retained privately at `/home/gui/.local/share/project-road-method-20261104/`; the complete user request, implementation briefing, launch guard and later delivery receipt are in `/tmp/spawn-briefing-Fv5aIO/`. These paths are VPS inspection artifacts, not browser access handoffs (operator report: this session; `$ hostname` returned `vps-25b8e3b3`).

## Consequential assumptions checked

| Basis / recommendation | Alternative or risk | Falsification check and result |
|---|---|---|
| Extend the integrated page. | Starting from the old viewer branch would repeat or lose newer work. | Published Tele-Claude main contains the [readiness commit](https://github.com/elgui/tele-claude/commit/8a851015) and [now-status correction](https://github.com/elgui/tele-claude/commit/b1bd0f9f); relevant files are clean. New isolated worktree uses that immutable published base (`$ git branch --contains REF` in Tele-Claude; `docs/design/project-road-control-center.md`). |
| Keep preparation distinct from admission. | “Candidate” or filled sections could imply runnable readiness. | Existing Road API is GET-only and assessment explicitly excludes runtime checks. New acceptance scenarios bind actual admission to source and execution identity (`docs/design/project-road-control-center.md`). |
| Reuse supervision helpers and validate the selected plan. | Repeated group launches could drop cross-group prerequisites. | Automator takes one group and ignores dependencies absent from its step list. Existing finite-road helpers are inventoried for reuse; exact selected-plan launch remains integration work (`docs/design/project-road-control-center.md`). |
| Use chains only with proved compatible semantics. | A human checkpoint might be bypassed. | Chain CLI accepts unit/mission, and the unreleased spec recipe expressly excludes chains; the map now names the limitation (`package/.charter/chain.py:1814`, `$ git show dee2f42:package/.claude/skills/charter-spec/SKILL.md`). |
| Require actual independent review. | A deterministic checker or Codex reviewing OpenAI work could be labelled independent. | Required-review gate authenticates no provider; chain auto review may be off. Child contract explicitly requires Anthropic review of its OpenAI-authored code (`package/.charter/checks.py:390`, `package/.charter/chain_groups.py:86`, `docs/verification.md`). |

No new PAI effectiveness statistics, successful implementation rail, deployment or owner acceptance are claimed by this documentation work. The implementation child must produce the real disposable rail and sandbox evidence, with precise limits if a prerequisite is unavailable (`docs/design/project-road-control-center.md`).
