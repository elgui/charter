<!--
Brief for a Claude Code session in ~/Projects/charter. This is a prompt to RUN, not a report.
Written 2026-11-09 by a tele-claude session (tele-claude at 16380fe6, charter at cfa1071), from Gui's picks K7, K2 and K6
of the technology watch on the "flow-promises" skill. The watch report, with the evidence, is
/home/gui/Projects/tele-claude/docs/ext/flow-promises-2026-11-09/README.md (outside this repository).

HOW TO RUN IT
  1. cd /home/gui/Projects/charter
  2. Start Claude Code and paste:
     Move docs/ext/flow-promises-2026-11-09/brief-charter.md from tele-claude into docs/briefs/2026-11-09-flow-promises-checks-world-actions-owner-lines.md, then carry it out. It is done when the brief's "Definition of done" holds.

WHEN IT IS DONE
  You get one branch in a worktree under /home/gui/Projects/.worktrees/charter/, with a release that is tested but
  neither pushed nor merged. The final message gives the commands for both. Nothing is upgraded in any project.
-->

# Charter: a decision's check is seen failing, a state-machine unit lists what the world does, and only the owner weakens an owner line

## Why this session exists

Gui read a technology watch on "flow-promises", a skill in a fork of the pstack plugin
(https://github.com/bkase/plugins/blob/main/pstack/skills/flow-promises/SKILL.md, commit `6f35f6ae`). It checks a
product flow's promises with a model checker. Its toolchain is not for charter, but two of its rules are. The first comes
from pstack's create-formal-verification skill: "A check that you have never seen fail proves nothing. Show each property
failing on a broken variant of the code it guards." The second comes from the flow-promises skill itself: "list what can
happen without the user: a request that succeeds, fails, or hangs, a timer, another device or user, the app closing.
Most edge cases come from this list." Measured against tele-claude's live install, both rules found real gaps. Gui took
both, and a third finding about the acceptance gate (K6). They are this brief.

Read first: `AGENTS.md` (how this repository is worked), `docs/gates.md`, `docs/method.md` § "The rules",
`package/charter/templates/decision.md`, `package/charter/templates/unit.md`, `package/.claude/skills/charter-decision/SKILL.md`,
and the unreleased `charter-spec-draft` branch (`git show charter-spec-draft:package/charter/templates/spec.md` and its
`package/.claude/skills/charter-spec/SKILL.md`). Never check that branch out; other sessions share this worktree.

## The three changes

### K7. A decision's check is seen failing before it goes active, and a check over missing files is reported

What happens today, at `cfa1071`:

- Acceptance probes must fail at the unit's base commit, mechanically (`docs/method.md:152`; `package/.charter/checks.py`,
  lines 787-819). A decision's `check:` has no equivalent. It runs at commit only when a staged path matches its `binds:`,
  with a 60 s timeout (`package/.charter/checks.py`, lines 914-937).
- The decision template says only "a shell command that exits 0 while the decision holds", and the charter-decision skill
  says only "If it can be checked by a command, set `check:`" (`package/.claude/skills/charter-decision/SKILL.md:12`).
  `grep -rniE "mutation|broken variant|able to fail|seen fail|must fail" package --include=*.md` finds nothing about
  decisions.
- In tele-claude, 15 of 40 decisions carry a check, and all 15 are static: greps for a pattern's presence or absence,
  or a static AST script. Two are defective:
  - `agent-runtime-layering-without-herdr` binds and checks four paths that were never built. Its check is
    `! grep -rlsE '"(/usr/bin/)?tmux"' services/agent_io.py services/agent_state.py services/detect services/runtime_contract.py`.
    With the files missing, `-s` hides the error and `!` turns grep's exit 2 into a pass, so the check passes until the
    code exists under exactly those names.
  - `worker-guard-keys-on-automator-identity` checks a constant in `services/step_close.py`, while the call it protects
    moved to `services/harness_adapter.py:253`, outside its `binds:`. Deleting the call switches the worker guard off,
    and the check neither fails nor runs. tele-claude has filed a superseding decision for this one
    (`charter/decisions/worker-guard-follows-the-launch-site.md` there, proposed). Its check was shown failing on two
    scratch breaks before it was filed, which is the practice this change asks for.

What to build, deterministically (no model anywhere in it):

1. Guidance, in `package/charter/templates/decision.md` and the charter-decision skill:
   - before a decision with a `check:` goes active, record under `## Because` the scratch break you made and the
     check's non-zero exit, as a `$ <break>; <check>` line with its exit code;
   - write `check:` only once the code it guards exists.
2. A finding in `charter check --all`, at `warn` level: a decision whose `binds:` globs match no file in the tree. It must
   fire on a fixture shaped like `agent-runtime-layering-without-herdr`.
3. Optional, if it stays small: the same warning when a `check:` names a path that does not exist. Skip it if it needs
   shell parsing that is not robust.

Probes (each fails before the change):
- `grep -n "seen fail" package/charter/templates/decision.md package/.claude/skills/charter-decision/SKILL.md`
- a new test, for example `tests/test_decision_binds_vacuous.py`: a fixture decision whose `binds:` matches nothing gets
  a `warn` finding from the check-all path, and a fixture whose `binds:` matches a file gets none.

### K2. A unit that changes a state machine lists what the world does without the user

What happens today:

- No unit template, rule or skill asks for this list, in the charter package or in tele-claude.
  `git grep -n -i -E "what the world|without the user|world action|liveness|fairness"` over tele-claude's
  `.claude/rules`, `charter/templates` and `charter/decisions` prints nothing.
- The practice exists after the fact. 14 of tele-claude's 137 Conversation Studio units with an Acceptance section carry
  a line about a restart, a tick, a dying tmux or a second message. They were written after a review found those
  failures, not before the code.
- Incidents of this shape in tele-claude:
  - a 45 s give-up timer fired before the supervising session's first visible output, and 6 of 6 prompts escalated;
  - a reply was lost when a pane exited between the notification and the reply;
  - a respondent's message was lost when a second one arrived before the agent's next poll;
  - a dead-session check that ran only when the list of live sessions was not empty.

  A written list would have named the second and third word for word.
- The charter-spec draft already asks for this in its Failure modes section ("Each flow walked against the code:
  concurrency, retries, outages, restores") and in its review question 3. But a spec is written only for a rail where
  separately built units could choose incompatibly. A race contained in one unit never triggers one, and tele-claude has
  no spec at all.

What to build:

1. One comment in `package/charter/templates/unit.md`, in the Acceptance block, close to this wording:
   `<!-- A unit that changes a state machine (a poller, a session, a relay, a run) lists what the world does without the
   user: a timer or tick, a process dying, a restart, a second device or hook answering, a late completion. Give an AC
   for each one that can fire between two steps. An AC that says "never stuck" or "eventually" names what must keep
   running, and its probe stops that. -->`
2. One clause in charter-spec's review question 3, on its branch, or in a note for whoever merges that branch: "and
   what each eventually-promise needs to keep running".
3. No gate. This is guidance; a grep cannot tell which units owed the list.

Probe: `grep -n "what the world does" package/charter/templates/unit.md` (fails before).

### K6. Only the owner weakens an owner line: the acceptance gate enforces its own rule, and the owner sees old beside new

Gui ruled this one on 2026-11-09: all three parts below.

What happens today, at `cfa1071`. The line numbers come from the watch's verifier, which tested the package at
`cfa1071`, tele-claude's installed 0.4.21, origin/main and `fix/human-check-preparation`. Re-check them before relying
on them.

- The rule text says a changed acceptance line needs "a dated `## Log` line" naming the criterion
  (`package/.claude/rules/charter.md:18`). The code only checks `len(new_log) > len(old_log)`
  (`package/.charter/checks.py`, lines 550-553). So rewording an `— owner: check` line from "every screen shows Skip" to
  "the first screen shows Skip", with an added Log line `- x`, passes:
  - `check_acceptance_change` returns `[]`;
  - `owner_line_changes` returns `[]`, because it keys on AC ids opened or closed (lines 1139-1153).

  This holds for an open line in status `now`, `in-progress` or `review`, and for a ticked line in a `done` unit.
  Weakening only the probe passes the same way.
- The check reads only the old status, and a status in `PLANNING_STATUSES = ("", "next", "later")`
  (`package/.charter/lib.py:32`) is exempt (`package/.charter/checks.py:544`). Nothing refuses a move from `now` back to
  `next`. So an agent can first move the unit to `next` and commit, then reword in a later commit with no Log line. In
  one commit the commit gate catches it, because it compares against HEAD.
- An owner line without an AC id is already caught, because `acceptance_boxes` keys on its text (lines 1130-1132). The
  hole is owner lines that carry an AC id.
- The acceptance fingerprint (`package/.charter/owner.py`, lines 163-173 and 219) protects only the window between the
  desk rendering a line and Gui clicking.
  - The desk shows only the current text (`owner.py:157`).
  - The receipt is `owner accepted AC-n`, with no hash and no text (`owner.py:227`), so the accepted wording is stored
    nowhere.
- The delegate's judge gets `git diff --cached` and the staged unit (`package/.charter/delegate.py`, lines 234-235). If
  the reword landed in an earlier commit, the judge sees only `[ ]` turning into `[x]` and reruns the weakened probe.
  `MANUAL_PROBE_RE` (`delegate.py:44`) blocks only `echo`, `printf`, `true` and `:`.
- The intended contract is already tested: `test_weakening_acceptance_mid_flight_needs_a_log_line`
  (`tests/test_review_regressions.py`, lines 484-491). Its compliant Log line is
  `- 2026-09-11 15:00 AC-1 probe replaced: …`.
- In tele-claude's history since 2026-09-01, 11 acceptance lines lost a quantifier (every, never, always, each, all, no).
  None was an owner line. 9 were replanning in `next`, and 2 were deliberate and logged with a dated line naming the AC.
  So this is a hole, not an incident.

What to build, deterministically:

1. In `check_acceptance_change`, require at least one added Log line that starts with a date (`\d{4}-\d{2}-\d{2}`) and
   names the key of each changed line. For a line with an AC id the key is the id; otherwise use the text key that
   `acceptance_boxes` already computes. Keep the refusal's wording and override text in the same style.
2. A status move from a non-planning status back into planning does not exempt a reword. Either read the more advanced
   of the old and new status, or refuse the regression itself in the same gate. Choose, and say why.
3. When an owner line's text or probe changed since the unit left planning, `charter owner` and the delegate's request
   show the old wording beside the new. The old wording is the line as it stood at the last commit where the unit was
   in a planning status, or at the owner's last acceptance; choose one and say why. Store the accepted wording, or its
   hash, in the acceptance receipt, so a later reword of an accepted line is detectable.
4. No quantifier-drop warning. The watch measured it as noise (9 of 11 drops were legitimate replanning).

Probes (each fails before the change):
- a sibling of `test_weakening_acceptance_mid_flight_needs_a_log_line` that rewords an owner line, appends `- x`, and
  asserts the edit is denied;
- a test that moves a unit from `now` to `next` in one commit and rewords an AC line without a Log line in the next, and
  asserts the second is refused;
- a test that `charter owner --json` shows the previous wording of an owner line reworded after work started.

Claude cards: `pre_tool_gate.py` calls `check_acceptance_change` (around line 69), so parts 1 and 2 reach Claude
sessions through the PreToolUse hook charter installs. Gui ruled that acceptable. The CLI commit gate covers Codex and
pi.

## Constraints

- Gates stay deterministic rules, with no model in them.
- Keep every existing output format byte-for-byte. tele-claude's step checker parses `charter probe`'s text output.
- Nothing is upgraded in any project. tele-claude's install (0.4.21) takes the release later, through an upgrade commit
  that is Gui's (or his delegate's).

## Definition of done

- One branch in a worktree under `/home/gui/Projects/.worktrees/charter/`, with a release version bump and a changelog
  entry naming K7, K2 and K6.
- Every probe above passes on the branch and fail at `cfa1071`, and the new test passes in the repository's own test suite.
- The final message gives the push and merge commands and says plainly what was not done.
