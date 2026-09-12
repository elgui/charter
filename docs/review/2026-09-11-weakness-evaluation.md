# Weakness evaluation, 2026-09-11

What became of the fourteen findings of the 2026-09-11 weakness review of the charter package, on branch `fix/charter-review-2026-09-11` from base 71ddc0b. The package is now 0.2.0 (`package/VERSION`, `package/charter/config.json`, `package/.charter/lib.py:32`). The classification was written before any code changed and is kept as written; the columns after it record the outcome. Diagrams of the result: `docs/method-visual.html`.

Class: **F** when a change inside `package/` removes the finding, **P** when it removes part and a residue is a property of the design, **A** when no change inside the repository can remove it. A residue is named by its limit id (L1 to L9), the same ids the red markers carry in `docs/method-visual.html`.

## Findings and outcome

| # | Finding | Class | Why | What changed | Test that proves it | Remaining limit |
|---|---|---|---|---|---|---|
| 1 | Inline `#` comments in the templates disable gates | F | The parser kept everything after the colon, and the templates put comments after gated values. tcv2's reader keeps inline comments verbatim and calls the shape an incident (`~/Projects/tcv2/services/tasket_routing.py:707-732`) | `strip_comment` reads a comment as YAML does (`package/.charter/lib.py:233`); a key with no value parses as empty (`package/.charter/lib.py:194`); templates keep comments on their own lines (`package/charter/templates/unit.md:4`); an inline comment in a tasket warns (`package/.charter/hooks/pre_tool_gate.py:57`) | `TemplateComments` (`tests/test_review_regressions.py:77`) | None |
| 2 | CI mode: size never fires, legacy done taskets block, a committed synthesis fails anchors, an unusable base checks nothing | F | Missing base comparisons and a silent fallback | `_check` measures size and done against the merge base (`package/.charter/bin/charter:61`); `usable_base` and `changed_paths` fall back to every tracked path with a warning (`package/.charter/checks.py:719`, `package/.charter/checks.py:732`); the written synthesis leaves gate activity out (`package/.charter/bin/charter:251`) | `CiMode` (`tests/test_review_regressions.py:151`) | None |
| 3 | A fresh clone never gets the pre-commit hook | F | The installer returned before it set `core.hooksPath` | The installer reconciles on every run (`bin/charter-pkg:128`); `charter setup` in the committed layer (`package/.charter/bin/charter:552`); the SessionStart banner says when the hook is off (`package/.charter/hooks/session_start.py:25`) | `FreshClone` (`tests/test_review_regressions.py:220`) | L9: `--no-verify` still skips the hook |
| 4 | The gated agent can edit the gates | P | Edit and Write on the gate inputs can be refused and CI can check authors; the agent shares the owner's machine and identity | `owner_only_changes` lists the owner's files and fields (`package/.charter/checks.py:486`); PreToolUse denies them unless `CHARTER_OWNER=1` (`package/.charter/hooks/pre_tool_gate.py:38`); pre-commit refuses them inside Claude Code (`package/.charter/checks.py:545`); CI checks authors, merges included (`package/.charter/checks.py:557`), and gate code against the manifest (`package/.charter/checks.py:602`); split units unfreeze named files only (`package/.charter/checks.py:153`); a second file cannot take a decision's id (`package/.charter/checks.py:369`, `package/.charter/checks.py:390`) | `ProtectedFiles` (`tests/test_review_regressions.py:248`) | L1: a Bash edit and a commit under the owner's identity; L2: a pull request can edit the workflow that judges it |
| 5 | Done can be faked | P | Evidence can be required to name a commit or a run, and probes can be re-run; the agent writes the probes | Evidence needs a resolving commit or a `$ command` run (`package/.charter/checks.py:245`, `package/.charter/checks.py:213`); probes run with `--probe` or `probes.at_commit` / `probes.in_ci` (`package/.charter/checks.py:307`); `charter probe <id>` prints evidence lines (`package/.charter/bin/charter:580`); a criterion changed after work started needs a log line (`package/.charter/checks.py:281`) | `DoneEvidence` (`tests/test_review_regressions.py:446`) | L3: the agent writes its own probes |
| 6 | Evidence SHAs vanish after a squash merge | P | CI can fetch the pull-request heads GitHub keeps; a local squash leaves nothing to fetch | CI fetches `refs/pull/*/head` (`package/.github/workflows/charter.yml:14`); the synthesis counts an unresolvable SHA of a committed done unit as historical (`package/.charter/bin/charter:213`) | `SquashedEvidence` (`tests/test_review_regressions.py:497`) | L4: a squash made outside a hosted pull request |
| 7 | State is per checkout and disposable | P | The git directory is shared by worktrees and never committed; CI runners and engine code are outside the package | The log and session records live in the git common directory (`package/.charter/lib.py:124`), the active unit in each worktree's git directory (`package/.charter/lib.py:131`); `CHARTER_UNIT` wins (`package/.charter/lib.py:418`); `charter setup` moves 0.1.0 state | `SharedState` (`tests/test_review_regressions.py:539`) | L5: runner logs end with the job; engines must export `CHARTER_UNIT` |
| 8 | Cost per accepted result cannot be computed | F, one limit | Acceptance frozen at fold time, one price table, no rework | Acceptance is read when the synthesis runs (`package/.charter/bin/charter:251`); prices per model from the pricing page (`package/charter/config.json`, `package/.charter/bin/charter:381`); 1-hour cache writes priced apart (`package/.charter/hooks/session_end.py:41`); rework from the first done commit (`package/.charter/bin/charter:243`); human minutes (`package/.charter/bin/charter:407`) | `Ledger` (`tests/test_review_regressions.py:563`) | L6: a session is charged to one unit |
| 9 | The scope parser fails open | F, one limit | Heading matching was exact and id-less items were dropped | Tolerant headings and id-less items gated (`package/.charter/lib.py:299`); `charter check --scope` reports what fails open (`package/.charter/checks.py:134`); a unit perimeter that reaches out of scope warns (`package/.charter/checks.py:100`) | `ScopeParser` (`tests/test_review_regressions.py:626`) | L7: globs cannot see intent |
| 10 | Engines' done flips refused on taskets that predate charter | F | Option (a), grandfathering, chosen; (b) would let a new tasket without the keys escape the gate, (c) would stall a supervised run on its first legacy tasket | The installer lists taskets found without acceptance (`bin/charter-pkg:168`); they close with a warning (`package/.charter/lib.py:404`, `package/.charter/checks.py:245`); adding an id is owner-only, removing one is free | `LegacyTaskets` (`tests/test_review_regressions.py:662`) | None |
| 11 | The Stop gate blocks explanation turns and accepts any path | F | Needed a per-turn activity marker, a stricter anchor, and a channel Claude reads | Judged only after an attempted Edit or Write or a moved HEAD (`package/.charter/hooks/stop_gate.py:33`); a commit, `path:line` or run is required; the log reminder is `additionalContext` after a commit landed (`package/.charter/hooks/stop_gate.py:60`) | `StopGateTurns` (`tests/test_review_regressions.py:702`) | None |
| 12 | PR-body anchors fail ordinary bodies and ignore edits | F | Trigger types and a warn-only mode | `types: [opened, edited, synchronize, reopened]` (`package/.github/workflows/charter.yml:4`); `charter anchors --pr` warns and counts `#123` (`package/.charter/bin/charter:182`) | `PullRequestBody` (`tests/test_review_regressions.py:752`) | None |
| 13 | Pre-commit judges the working tree, not the index | F | Artifacts can be read from the index; commands that run in the tree can refuse when it differs | `index_view` (`package/.charter/lib.py:148`); decision checks and probes refuse when the tree differs from the index (`package/.charter/checks.py:750`) | `StagedContent` (`tests/test_review_regressions.py:788`) | None |
| 14 | `check:` is arbitrary shell from markdown | A | Running a command is the feature; CI already runs a pull request's code through its tests | Nothing to change; documented (`docs/gates.md`); the SessionStart banner lists every `check:`, and changing one on an active decision is owner-only (`package/.charter/checks.py:486`) | None | L8 |

## Mismatches found beyond the brief's list

| What | Where it was | What changed | Test |
|---|---|---|---|
| Anchors were hard on the prototype track, where `docs/method.md` (Two tracks) says warning | `package/.charter/bin/charter:182` | The code follows the design table | `tests/test_review_regressions.py:772` |
| The size gate measured the package's own `.charter/checks.py`, which a project cannot split and an upgrade grows | `package/.charter/checks.py:145` | `.charter/` is exempt from a project's size gate | `tests/test_installer.py:78` |
| A 7-character short SHA made only of digits (about one in 27, (10/16)^7) was never an anchor | `package/.charter/checks.py:213` | A digits-only token counts when git resolves it as a commit | `tests/test_review_regressions.py:728` |
| A hex run inside a path (a UUID directory) was read as an unresolved commit | `package/.charter/checks.py:213` | Tokens that contain `/` are not scanned for SHAs | `tests/test_review_regressions.py:194` |
| Claude Code writes its cache with the 1-hour TTL, twice the input price, and the ledger priced every write at the 5-minute rate | `package/.charter/hooks/session_end.py:41` | Writes priced by TTL, per model (https://platform.claude.com/docs/en/about-claude/pricing) | `tests/test_review_regressions.py:596` |
| `docs/method.md` said the log records a `--no-verify` skip; nothing does | `docs/method.md` (What happens when a gate cannot be satisfied) | The sentence now says nothing records it | None |
| The personal hook read session records from `.charter/state/` | `personal/claude-home/hooks/charter-personal.py` | Reads the git common directory first, then the 0.1.0 location | Run by hand on a test project |

## Choices made

| Question from the brief | Choice | Reason |
|---|---|---|
| Finding 10 | Grandfather list (option a) | Keeps engines closing the work that predates the method and gates everything written after it (`bin/charter-pkg:168`) |
| Probes in CI | Opt-in per project, at commit and in CI (`package/charter/config.json`) | A default that blocks because a runner lacks the test dependencies breaks the tool, which the method ranks worse than a missed check (`docs/method.md`) |
| Owner switch | `CHARTER_OWNER=1` in the environment Claude Code starts with (`package/.charter/lib.py:94`) | Hook processes inherit Claude Code's environment (https://code.claude.com/docs/en/hooks); a settings `env` change reaches a running session (https://code.claude.com/docs/en/settings-reference), so an edit that introduces `CHARTER_OWNER` is itself refused |
| Pre-commit owner check | Refuse inside Claude Code, warn outside (`package/.charter/checks.py:545`) | Claude Code sets `CLAUDECODE=1` in its tools and IDE terminals (https://code.claude.com/docs/en/env-vars); outside it the committer cannot be told from the owner |
| Split units | Opening, widening or reopening one is owner-only; narrowing or closing is free (`package/.charter/checks.py:486`) | The R3 row of `docs/method.md` names the owner as the one who opens it, and shrinking a frozen file never needs one |
| Stop-gate log reminder | `additionalContext`, only when a commit landed and the unit's log did not move (`package/.charter/hooks/stop_gate.py:60`) | `systemMessage` reaches the user, not Claude; a reminder on every edit turn would cost a continuation each time (https://code.claude.com/docs/en/hooks, Stop decision control) |
| Merge policy | Not recorded | The owner's call; CI's pull-request fetch covers merges made through GitHub (`package/.github/workflows/charter.yml:14`); see the open questions |
| Version | 0.2.0 (`package/VERSION`) | New gates and a new state location change behaviour |

## Independent review

A fresh-context `code-reviewer` subagent reviewed the diff twice, with the fences of the brief and no write access (outside this repository: the session's subagent transcripts). Every finding was reproduced as a failing test before it was fixed.

| Finding | Severity given | Fix | Test |
|---|---|---|---|
| CI's author check could not see a change made inside a merge commit | High | Merges are diffed per parent | `tests/test_review_regressions.py:361` guards the benign case; `tests/test_review_regressions.py:379` the attack |
| A merge that kept the stale side of an owner-only file reverted the owner's later change unseen | Medium-high | A merge answers for any side's change since the merge base that it drops (`package/.charter/checks.py:557`) | `tests/test_review_regressions.py:379` |
| Narrowing a split unit was refused | Medium | Only opening, widening or reopening is owner-only (`package/.charter/checks.py:486`) | `ProtectedFiles` (`tests/test_review_regressions.py:248`) |
| Reopening a split unit closed under a custom done status passed | Low-medium | `done_statuses` is passed through | `ProtectedFiles` (`tests/test_review_regressions.py:248`) |
| `status: # tbd` parsed as `[]` | Low-medium | A key with no value is empty (`package/.charter/lib.py:194`) | `TemplateComments` (`tests/test_review_regressions.py:77`) |
| No prompt to set `owner`; a path with a space split in the Stop gate | Low | SessionStart line on the client track (`package/.charter/hooks/session_start.py:29`); `splitlines` in `package/.charter/hooks/stop_gate.py` | `tests/test_review_regressions.py:420` |

Checked by the reviewer and found correct: the base and size logic of `--all`, the done-flip logic, 0.1.0 price-table compatibility, `strip_comment` on quoted `#`, URL fragments and apostrophes, duplicate ids, root commits, installer reconciliation, and the tolerant scope headings (outside this repository: the reviewer's reports in the session transcript).

## Verification

- The suite: `$ cd tests && python3 -B -m unittest -q test_gates test_installer test_review_regressions` → 111 tests, OK (30, 7 and 74).
- The 74 regression tests and the 0.1.0 upgrade test, run against 71ddc0b in a temporary worktree, fail 70 of 75. The five that pass there are guards against over-correction: an untouched oversized file stays unblocked, a done flip stays gated, a new tasket stays gated, the printed synthesis passes its own check, and a merge is not blamed for an owner change it carries (outside this repository: the run's output in the session scratchpad).
- Two original tests changed because the behaviour they encoded changed: the Stop test now makes an edit first (`tests/test_gates.py`, `StopGate`), and the session-record test reads the git directory (`tests/test_gates.py`, `SessionHooks`).
- The parent session's reproduction script, re-run after the fixes, reports 16 of its 20 experiments no longer reproduced. Of the other four, 1a and 1c substitute template text that moved with the comments, and the two PR-body cases run `charter anchors` in document mode where CI now runs `--pr`; the regression tests cover all four cases (outside this repository: `verify.py` and its output in the parent and this session's scratchpads).
- Its squash experiment, re-run: in a clone without pull-request refs, CI still refuses the push that closes the unit (L4), and the synthesis lists the unit as accepted with a historical commit (outside this repository: `verify6.py`, same place).
- `docs/method-visual.html` parses with balanced tags, unique ids, resolving internal links and marker references, no script and no external URL in an attribute; it was rendered in headless Chromium at 1280 and 400 pixels wide, light and dark (outside this repository: screenshots in the session scratchpad).

## Follow-ups outside this repository

- tele-claude: add `scope`, `perimeter`, `decisions`, `kind` to the reader allowlist (`~/Projects/tele-claude/services/project_tasket_reader.py:230-234`).
- tele-claude and tcv2: export `CHARTER_UNIT=<id>` to the sessions an engine starts, so the perimeter gate and the ledger see the unit (L5); the package reads it first (`package/.charter/lib.py:418`).
- tcv2: when the board's done flip is refused by the pre-commit, show the gate's reason; the rollback exists (`~/Projects/tcv2/services/tasket_ops.py:708-718`).
- GitHub, when the first adopter has a remote: branch protection on `main` with required review from code owners for `charter/`, `.charter/` and `.github/workflows/` (L2; https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).
- The personal layer's hook changed in this repository (`personal/claude-home/hooks/charter-personal.py`); it takes effect wherever the owner installed it.

## Decisions taken

The owner asked for one commit and left the other questions to common sense and good practice (reported in the owner's message of 2026-09-12). What was settled:

| Question | Decision | Where it is recorded |
|---|---|---|
| Commit | One commit on `fix/charter-review-2026-09-11`, not pushed | The branch's history (reported in the owner's message of 2026-09-12) |
| Probes by default | The package keeps both switches off; a project whose tests run on its machine without live credentials turns `probes.at_commit` on, and `probes.in_ci` once its workflow installs the test dependencies | `docs/migration.md` Path A step 5 and the orqueveaux step 2; `package/charter/config.json` |
| Merge policy | Client projects record `merge-commits.md` as a decision, so evidence commits survive (L4) | `docs/migration.md` Path A step 5 and the orqueveaux step 7 |
| Owner switch | `CHARTER_OWNER=1` at launch stays the owner's way in a session; editing by hand remains open | `docs/gates.md` (Owner-only changes); `package/.claude/rules/charter.md` |
| Stop reminder | Kept: one continuation after a commit lands without a log line, and never otherwise | `package/.charter/hooks/stop_gate.py:60` |
| Version | 0.2.0 | `package/VERSION` |
