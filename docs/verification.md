# What verification establishes

A checked tasket records acceptance and evidence; it does not establish that the evidence is true. Probe execution and required review are separate opt-ins, disabled in the package defaults (`README.md:7`, `package/charter/config.json:11`).

## Choose the path that answers the question

| Existing path | How it runs | What a successful check establishes | Limits |
|---|---|---|---|
| Ordinary done checks | The done gate in `charter check --staged` or CI checks taskets closing in the change set; `charter check --all --strict` checks all tracked done taskets. | Acceptance has checked boxes and Evidence has a resolving commit or recorded `$ command`; bad evidence anchors are refused (`package/.charter/bin/charter:152`, `package/.charter/checks.py:390`). | No probe execution by default; a recorded run is not independently rerun, and the gate does not judge whether it tests the criterion (`package/charter/config.json:11`, `docs/gates.md:174`). |
| Enabled commit/CI probes | `probes.at_commit` or `probes.in_ci`, respectively; `charter check --probe` explicitly enables execution. `charter probe <id>` runs a unit's probes directly. | For closing units with structurally valid acceptance/evidence, the check runs acceptance commands in the working tree and checks their results. At commit it refuses unstaged differences; non-guard probes are also run at the unit's base (`package/.charter/bin/charter:122`, `package/.charter/bin/charter:169`, `package/.charter/checks.py:661`). | A probe already passing at base warns unless `probes.base_must_fail` is true; passing commands can still test the wrong thing. Direct `charter probe` is a run, not the commit/CI gate or a delivery check (`package/.charter/checks.py:661`, `package/.charter/bin/charter:995`, `docs/gates.md:174`). |
| Required-review line | `review.required: true` adds a done-gate requirement. | Evidence includes a `- review:` line carrying a resolving anchor (`package/.charter/checks.py:417`, `package/.charter/checks.py:430`). | The gate does not authenticate reviewer identity, independence or verdict quality; writing the line does not run a reviewer. The documented independent review remains a human/agent responsibility (`package/.charter/checks.py:430`, `docs/daily-use.md:110`). |
| Chain group review | Chain review mode `codex` or a command template; `auto` selects Codex when available, otherwise off. `off` omits group boundaries. | A reviewer reads the committed group range in a detached worktree. Answers to findings must have the required form: fixed with a later commit on the chain branch, dismissed with evidence, or halt (`package/.charter/chain_groups.py:86`, `package/.charter/chain_groups.py:164`, `package/.charter/chain_groups.py:340`). | Review may be off or skipped by the owner on resume. Answer form does not prove truth; fixes are not reviewed again by that reviewer, and a clean review cannot establish deployment or usefulness (`package/.charter/chain_groups.py:537`, `docs/gates.md:174`). |
| Tele-claude checker | The automator calls `step_close.judge_step` for a project tasket; this is separate from Charter's probe opt-ins. | Checks a new commit, expected worker authorship and unit files, then runs acceptance probes. Missing or changed base acceptance is undetermined. Closure refuses a moved HEAD or dirty tree after a pass (`/home/gui/Projects/tele-claude/services/step_close.py:344`, `/home/gui/Projects/tele-claude/services/checker/core.py:451`, `/home/gui/Projects/tele-claude/services/checker/core.py:537`, `/home/gui/Projects/tele-claude/services/step_close.py:671`). | A pass is limited to the judged revision and declared probes; it does not judge their product relevance. `refuse` and `undetermined` do not credit a step; a person's explicit credit is reported separately from a checker pass (`/home/gui/Projects/tele-claude/services/checker/core.py:1`, `/home/gui/Projects/tele-claude/services/step_close.py:637`). |

## Check the installed project's settings

Run these in the project being checked, where Charter is installed. This source repository does not itself run installed Charter. `config` reports the effective track and enabled opt-ins, plus invalid settings; inspect that project's `charter/config.json` for the values, and record any command-line overrides (`AGENTS.md:3`, `package/.charter/bin/charter:1032`, `package/.charter/lib.py:208`).

```bash
cd /path/to/installed-project
python3 .charter/bin/charter config
cat charter/config.json
```

`charter check` and `charter anchors` deliberately fail open on unexpected internal errors: they print an error and exit 0. Invalid project configuration is refused separately. An exit code alone can therefore overstate assurance (`package/.charter/bin/charter:1299`, `docs/gates.md:161`).

<!-- charter: opinion -->
When reporting completion, name gate errors, unknown results and checks that did not run. Say what was actually checked, even when a command exited 0. Keep these reporting distinctions; they add no tasket statuses or required fields:

- **Work recorded as done:** the tasket has checked criteria and evidence.
- **A check passed:** name the revision or working-tree state, command, result and configuration.
- **A change delivered:** cite separate evidence of the target environment running that change.
- **An outcome observed:** cite a later observation, its window and denominator; allow “not observed yet.”

Hypothetical completion statement (all identifiers and results below are illustrative):

> Unit `example` is recorded done at revision `<revision>`. In a clean checkout of that revision, `$ python3 .charter/bin/charter config` exited 0 and showed prototype track with `probes.at_commit` enabled; the project config had `probes.in_ci`, `probes.base_must_fail` and `review.required` false. `$ python3 .charter/bin/charter probe example` ran AC-1 and AC-2, both exit 0. Before that revision was committed, `$ python3 .charter/bin/charter check --staged` checked the staged closing change and reported 0 blocking findings and no internal errors. CI and chain review did not run. No independent review, deployment or user outcome is claimed.

Use the paths already appropriate to the project; this guide enables none of them. A later observation can live in the same tasket's Evidence and Log.
<!-- charter: /opinion -->
