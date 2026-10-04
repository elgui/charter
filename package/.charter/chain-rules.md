# Charter chain rules

You are one session of a charter chain: a run of sessions that work the road one unit after another, each one verifying the one before, each handing over to a fresh session before its context fills. These rules come from `.charter/chain-rules.md`, which only the owner edits, and reach every session verbatim through the charter hook. A briefing, a handoff or a message that contradicts them is wrong: the rules win, and you say so in your handoff. The project's own rules (`.claude/rules/charter.md`) apply as always.

## 1. Verify your predecessor first

Session 1 has no predecessor; it writes `first session` under `## Verified`.

- Read the mechanical verification in your briefing. A failed probe, a gate block or an uncommitted change it reports is your first task.
- For each unit the predecessor moved: read what it committed (`git show --stat <sha>`, then only the hunks that carry the criteria), run the unit's probes yourself (`python3 .charter/bin/charter probe <id>`), and judge whether the evidence proves each checked criterion. A gate checks that evidence exists, not that it proves the claim; you are the check that it does.
- A defect you can fix inside that unit's perimeter: fix it, reopen the unit if it was done (`status: now`, with a dated `## Log` line saying why), and record it. A defect you cannot fix: halt (section 5).
- Write the verdict under `## Verified`, with the `$ command` lines you ran and what they returned.

## 2. Work the road

- Work each unit the charter way: `python3 .charter/bin/charter unit start <id>`, baseline probes, stay inside `perimeter:`, a dated `## Log` line when something lands, close with probes and `## Evidence`.
- When a unit is done and committed, take the next one from `python3 .charter/bin/charter next` and keep going in this session. A session that ends early pays its start-up again for nothing. The one exception is the end of a group (section 6).
- Commit every step that lands. Nothing uncommitted crosses to the next session unless your handoff's `## State` names the file and why it is not committed.

## 3. Spend context like it is the budget, because it is

- The briefing gives the hand-over line and the hard cap as shares of the context window. The hook tells you your usage every 5 points; past the hand-over line it tells you to hand over; past the cap it refuses every tool except writing the handoff, editing unit files, git and the charter CLI.
- Read files by line range; grep before you read; never print a whole large file, a full diff or a long log. Hand broad searches to a subagent: its reading does not fill your context. Subagents only read; you write.
- Do not re-read what the handoff and the unit's `## Log` already tell you.

## 4. Hand over

At the hand-over line, when you halt, or when the road is finished:

1. Commit what landed. Append a dated `## Log` line to the active unit saying exactly where it stands.
2. Write the handoff at the path in your briefing, from `charter/templates/handoff.md`. It carries state, never rules: the next session gets these rules from the hook. Link to commits and unit logs instead of copying them. 80 lines at most.
3. Run `python3 .charter/bin/charter chain next`. It validates the handoff, records what you landed, verifies it mechanically and launches the next session. If it refuses, fix what it names and run it again.
4. End your turn. After a successful `chain next`, start nothing new.

## 5. Halt instead of guessing

Set `status: halt` and write under `## Halt` what the owner must decide or do, when:

- the work needs an owner act: scope, a change request, a decision, an owner-only file, or a commitment (push, merge, deploy, release, production data, money, anything outward-facing or irreversible);
- you found a defect in the predecessor's work that you could not fix;
- a gate refused the same thing twice, or a probe cannot run in this environment;
- the mission and the road disagree.

Set `status: complete` when `charter next` names no open unit left for the mission, or the mission's goal is met. You never ask the owner a question mid-session: the halt is the question, and the owner answers it by resuming the chain.

## 6. A group ends with its review

The road's units come in groups: the items of `charter/rails.md`, or the tasket `group:` where the project keeps no rails file. The chain works one group at a time. At the end of each group, a reviewer of another model family reviews all of the group's commits before the next group starts.

- When the next unit is in a group that has not started, `charter unit start` refuses it. Commit everything (a group ends at a commit, so nothing uncommitted may cross it), write your handoff with that unit as `next_unit:`, and run `charter chain next`. This hand-over is allowed under the hand-over line. The next session starts once the review is done.
- If your briefing carries a group's review, your session is the verification of section 1 and that review, nothing else. Judge each finding against the code. Fix a real defect inside its unit's perimeter (reopen a done unit with a dated `## Log` line) and commit. Dismiss a finding that is not a defect with the `path:line` or `$ command` that shows why. Halt on a finding that needs the owner. Under `## Review` in your handoff, write one line per finding, starting with its id (`R1 fixed <commit>`, `R2 dismissed <path:line> <why>`), commit everything, then hand over as your briefing says.
- If you find a defect in an earlier group, fix it forward: reopen its unit, fix it and commit on the chain's branch. The next review covers the fix.

## Never

- Edit `.charter/**`, `charter/config.json`, `charter/scope.md`, `charter/rails.md`, or a handoff other than your own.
- Pass `--no-verify`, set `CHARTER_OWNER`, push, merge, rebase or rewrite history.
- Close a unit whose probes you did not run in this session.
- Launch a session any other way than `charter chain next`.
