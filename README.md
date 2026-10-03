# charter

A working method for client projects run alone with agents. Each project keeps one short written charter: what was sold, what was decided, and what each unit of work must prove before it counts as done. Claude Code hooks, git hooks and CI enforce it, so it does not depend on an agent choosing to follow it (`docs/method.md:5-14`).

This repository was called `methodo` until 2026-09-24 (decision `package-name` in `docs/report-2026-09-11.md`). Dated records under `docs/` still say `methodo`; they are left as written.

## The problem

Agents working on client projects fail in a few recurring ways. The survey of this machine's projects that started charter found them in real repositories (`docs/method.md` § What the evidence said the method must solve):

- **"Done" is fakeable.** A karaokay tasket is `status: done` with all nine of its acceptance boxes unchecked. The tasket engines read `status` and dispatch the next unit on top of it; no program reads a warning (`docs/method.md:22`, `docs/method.md:111`).
- **Nobody checks the rules.** No hook in the user-level Claude Code settings looked at taskets. The only mechanical check, in tcv2, tested that *something* changed, not that the criteria were met (`docs/method.md:23`).
- **Governance documents grow until nobody reads them.** tcv2's `CLAUDE.md` had reached 873 lines with twenty design rulings woven inline and amended in place. orqueveaux tracked progress in 33 root markdown files, most of them stale (`docs/method.md:24`).
- **The scope has no home.** No tasket cited what the client had bought, so work nobody paid for looked the same as work somebody did (`docs/method.md:25`).

Instructions in prose do not fix this. An agent in the middle of a task reads a warning as advice (`docs/method.md:112`), and a long rules file is the first thing it skims.

## The idea

Write it down; let machines hold it:

- **`charter/scope.md`** says what is sold, what is not, and what the price assumes. Work outside it becomes a change request that only the owner approves (`docs/method.md:9`).
- **`charter/decisions/<id>.md`** holds one design decision per file, with the reason for it and an expiry date. Code that depends on a decision cites it as `charter:<id>`, and a decision can carry a command that checks it still holds (`docs/method.md:10`).
- **A tasket in `.taskets/`** is the unit of work. It names the scope item it delivers and the paths it may touch, lists acceptance criteria as runnable probes, and keeps its own evidence and log (`docs/method.md:11`).

The gates run in three places, and each one catches what the one before it can miss (`docs/gates.md`):

| Where | When | Catches |
|---|---|---|
| Claude Code hooks | As the agent edits | Early, with the reason and the way forward in the agent's context (`docs/gates.md:7-15`) |
| Git pre-commit hook | At every commit, whichever agent or person commits | Changes made through Bash, by Codex or pi, or by hand (`docs/gates.md:107`) |
| CI | At merge, from a clean clone | Anything a `--no-verify` or a missing local hook let through (`docs/gates.md:113`) |

A few principles shape the design (`docs/method.md`):

- **Say where each decision is written and who settles it.** A gate refuses; it does not decide. When something is stuck, it is settled by the owner or by a reviewer that wrote neither side (`docs/method.md:16`).
- **Hard gates only where a warning fails.** Five things are refused outright. Everything else warns, and every warning is logged, so the log shows which warnings are ignored often enough to become gates (`docs/method.md:12`, `docs/method.md:107-113`).
- **Every refusal names the way forward**: the change request to write, the evidence to add, the code to move out, the decision to supersede. No refusal leaves the agent stuck (`docs/method.md:119`).
- **The owner holds the keys.** The files that define the gates (scope, config, tooling, hook wiring, the CI workflow) are the owner's. An agent's edit of them is refused in session and at commit, and CI checks who committed them (`docs/gates.md:35-37`).
- **Fewer documents, with more force.** The method removes per-phase progress files, roadmaps kept by hand, and rulings buried in `CLAUDE.md`. Progress is generated from the repository on demand (`charter synth`), and every line of it is anchored (`docs/method.md:228`, `docs/method.md:173-186`).

## What it blocks

Each row is a gate running today (`docs/gates.md` gives each gate's exact trigger and override):

| An agent tries to... | What happens |
|---|---|
| Mark a tasket `done` with an unchecked box, or with "it works" as the evidence | Refused. Done needs every box checked and evidence naming a commit that resolves or a `$ command` that was run (`docs/gates.md:67-68`) |
| Edit a path the scope lists as out of scope | Refused until the owner approves a change request covering it, on the client track (`docs/gates.md:45-47`) |
| Cite a decision that has been retired, or break a decision's `check:` | Refused, and the message names the decision that replaced it (`docs/gates.md:77-78`) |
| Grow a file past its size limit (800 lines for code; 400 lines or 32 KiB for governance files such as `CLAUDE.md`) | Refused. Shrinking is always allowed. The owner can open a split unit or name a budgeted exception (`docs/gates.md:60-63`) |
| Close a unit whose probes already passed before the work started | Where probes run (at commit or in CI, when the project turns them on), flagged, because such a probe tests nothing; refused with `probes.base_must_fail` (`docs/gates.md:69-70`) |
| Publish a progress report with an unanchored claim | `charter synth` will not write it (`package/.charter/bin/charter:422`), and on the client track CI fails `charter anchors` on reports (`docs/gates.md:98-103`) |
| Edit or commit the scope, the config, the tooling or the CI workflow | Refused to an agent; the owner makes that change (`docs/gates.md:19-37`) |

This is the exact output when a tasket is committed as `done` with an unchecked box and "it works" as its evidence (in the scratchpad: a scratch repository, 2026-09-24):

```
charter/done block [.taskets/u1.md]: status is done but 1 acceptance box(es) are unchecked Override: run each probe, check the box, and cite the run under `## Evidence`; or keep the status open
charter/done block [.taskets/u1.md]: status is done but `## Evidence` names no commit that resolves and no `$ command` run; a path or a URL alone shows nothing ran Override: add the commit SHA(s) and each probe as a `$ command` line with its result (`charter probe <unit>` prints them)
charter check: 2 blocking, 0 warning(s) [staged, track prototype]
Refused. Each line above names its override. `git commit --no-verify` skips this hook; CI runs it again.
```

There are two tracks. `client` is for work under a signed devis and turns the scope gate on. `prototype` has no scope file and keeps the other gates (`docs/method.md` § Two tracks).

## What it does not do

The guarantees are narrower than "the agent cannot misbehave", and the docs say where they stop (`docs/gates.md` § What a gate cannot see; `docs/method.md` § The zero-hallucination guarantee):

- **It checks that evidence exists and resolves, not that it proves the claim.** A cited `file:line` that says something else passes. A probe that fails before the work for an unrelated reason passes the before-and-after check. The reviewer and the owner check the truth (`docs/gates.md:121`, `docs/method.md:163-169`).
- **The scope gate matches paths.** Out-of-scope work that lands in an in-scope file is invisible to it (`docs/gates.md:122`).
- **On the owner's machine, the agent can act as the owner.** A Bash command is not an Edit, and the agent commits under the owner's git identity. A pull request can also edit the workflow that checks it. The real lock sits outside the repository: GitHub branch protection with required code-owner review (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).
- **Most commitments are actions, not files.** No gate sees a deployment, a production data change or a merge. The rules file tells the agent they are the owner's (`docs/gates.md:125`, `package/.claude/rules/charter.md:44`).
- **`git commit --no-verify` skips the local hook**, and nothing records the skip. CI runs the same checks at merge (`docs/method.md:121`).
- **Gates fail open on their own errors.** A crashing gate logs the error and lets the change through, because a gate that breaks the tool is worse than one that misses once (`docs/method.md:123`, `docs/gates.md:109`).
- **The session hooks are Claude Code's.** Codex, pi and other harnesses get the git hook and CI, not the in-session guidance (`package/AGENTS.md:4`).

## Where it runs

Four projects on this machine run charter: tcv2, leCRM, karaokay and skill-delivery. All four are on the prototype track; none is on the client track yet (`$ for p in ~/Projects/*/; do [ -f "$p/charter/VERSION" ] && echo "$p"; done`, 2026-09-24). The owner ruled on 2026-09-24 not to add gates until two or three real projects have run a full cycle (operator report, 2026-09-24). Client sign-off per scope item is deferred until a client-track project has run one (commit b281a17).

## Getting started

To install charter on a project, ask an agent to do it; it follows **`docs/install.md`**, the one step-by-step procedure. The agent checks the preconditions and chooses the track with you. For a project that already has code, it runs a read-only survey first. It then does a dry run and installs on a branch. It stops with the files staged, because the install commit touches files that are yours to commit. Each other clone then runs `python3 .charter/bin/charter setup` once. After that, the working day (units, probes, evidence, reports, and what only you do) is **`docs/daily-use.md`**.

A look first, changing nothing, from a checkout of this repository wherever it sits (`docs/install.md` § Step 0):

    python3 bin/charter-pkg survey  <project> --track prototype --out <dir>  # a project with history: read-only
    python3 bin/charter-pkg install <project> --track prototype --dry-run    # a new project

## What is in here

Three things live in this one repository. Each goes to a different place and is tracked by a different git history (`bin/charter-pkg`, `personal/README.md`).

| Part | Path | Where it ends up | Tracked by |
|---|---|---|---|
| **The package** (the committed layer) | `package/` | Copied into each project by `bin/charter-pkg install` as `.charter/`, `charter/`, `.claude/rules|skills|agents`, a CI workflow | The **project's** git: the project commits the copy. This repository only holds the source |
| **The personal layer** | `personal/` | `~/.claude`, through two symlinks back into this checkout (the `CharterAdmin` skill and the `charter-personal.py` hook); installed once per machine, `personal/README.md` | **This** repository: an edit here is live on the machine at once |
| **The tooling around them** | `bin/`, `tests/` | Stays here. `bin/charter-pkg` installs, upgrades, surveys; `tests/` tests the package and the installer | This repository |

## Documentation map

| Read this | For |
|---|---|
| `docs/install.md` | **Installing, setting up, upgrading or removing charter on a project.** The only procedure; other documents point to it |
| `docs/daily-use.md` | **Working on a project once charter is installed**: the daily loop for the agent, what only the owner does, the weekly look at the gates and opt-ins, and a glossary |
| `docs/method.md` | The method: the rules R1 to R12, real tests, evidence classes, the synthesis, the two tracks, cost, the seams not built |
| `docs/gates.md` | Every gate: what it checks, where it blocks, its override, its limits |
| `docs/package.md` | Layout, commands and flags, what lands in a project, and the upgrade notes for each version |
| `docs/migration.md` | Adopting the method from five starting points (new client project, prototype, taskets, BMAD, ad-hoc documents) |
| `docs/design/migration-workflow.md` | How the survey and the `Migrate` workflow work, and the leCRM rehearsal |
| `docs/design/charter-next.md` | Why `charter next` exists, what a read-only tool such as NowWhat may call, and what was deferred (0.4.4) |
| `docs/design/continuous-chain.md` | The continuous chain (`/charter-chain`, 0.4.7): fresh sessions that verify each other and hand over under a context budget |
| `docs/method-visual.html` | The method in diagrams, offline |
| `AGENTS.md` | Working on charter itself: tests and releasing a new package version |

**History** (how it was built and why; nothing reads these at run time, and they are not rewritten): `docs/report-2026-09-11.md` (the build report and its decisions), `docs/session-log.md`, `docs/briefs/`, `docs/review/` (weakness evaluation, harmonization review, findings), `docs/trials/` (per-gate trial results with costs).
