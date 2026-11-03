---
name: charter-spec
description: Turn a rail into units precise enough to build without guessing, with its sources compared, its binding choices decided, an independent review answered and a readiness verdict per unit. USE WHEN the owner asks for a spec for a rail, OR you are about to write a rail's units and two units built separately could choose incompatibly on something costly to undo, OR the rail answers to a text owed to someone, such as a contract or an agreement. Not for a rail whose units are plain; write those directly.
---

# charter-spec

An opt-in recipe. It adds one file, `charter/specs/<rail id>.md` from `charter/templates/spec.md`, and otherwise uses what the project already has: a spec unit, a checkpoint unit, proposed decisions and work units. It adds no gate and no status. In a project installed before this recipe, take the template from the checkout you read this file from.

## Does this rail need it?

Before writing a rail's units, ask:

- Could two units built separately choose incompatibly, on something costly to undo: a schema, money, identity, a live path?
- Does the rail answer to a text owed to someone?

If neither, write the units. The owner can ask for a spec or waive one. A rail that already has units is left alone.

This recipe covers manual sessions and a Run All. A chain does not read `gate:`, so a checkpoint does not hold it: do not run a specced rail in a chain yet. Work from the project's own checkout, because its hooks do not fire from anywhere else. If the rail stands on another rail with no spec, say so to the owner: before starting if it would change the work, otherwise in the ruling. That rail is usually the true first step.

## The steps

1. **Open the units.** Write the spec unit from `charter/templates/unit.md`, then the checkpoint, before any work unit, all in one group (§ The units). Set `status: now` on the spec unit by hand, then run `python3 .charter/bin/charter unit start <id>`.
2. **Name the sources.** List every text, file and system the rail rests on, with its version or date, and read them before designing. List what sits beside each source and read anything newer: a later text can contradict the one the rail cites. Where a text was sent to someone, check that the copy you were handed is the copy that was sent. Say which sources are untracked, because a clean clone cannot check them.
3. **Compare.** Set the sources beside the code and beside what the running system measures, and write down each mismatch with its source. This step finds the most. Read the code the design touches, and do not trust an earlier unit or brief about it.
4. **Map the clauses,** only where a binding text exists. One row per promise: clause, what it asks, the unit or rail that owns it, the probe. Point to decisions; never copy them into the table.
5. **Decide what binds.** For each choice ask: could two units built separately choose incompatibly? If it is also a real trade-off, it is a decision (`/charter-decision`) with `status: proposed`, `ask:`, `recommend:`, and `binds:` for the paths it will govern, even if they do not exist yet. Delete the template's `check:` line until the code exists, because ruling the decision active runs it, and give the unit that lands the code an `— owner: do` line to add it, since `check:` and `binds:` of an active decision are the owner's. Option surveys go in the decision, not the spec.
6. **Sort the open questions** by who can answer: agent, owner, partner, customer. Answer the agent's. Give each of the others a default, or mark it blocking. Hold a blocking one on a checkpoint (§ The units). Keep the rest in the spec: a question nobody can act on yet is not an ask.
7. **Write the units,** with named probes. A probe must fail before the work, must prove the deliverable and not a state of the workflow, and must not contain a backtick, which cuts it silently. A probe of a live system proves the property, not a name. Where a unit lists every X, make the list a probe. Run each work unit's probe once before the review, through `/bin/sh` as Charter does, to see it fail. Commit `— owner:` lines knowing they are append-only: the gates read removing or renumbering a committed one as closing it, even on a unit not yet started.
8. **First review.** Have a reviewer of a model family other than the writer's read the spec, the decisions, the units and any script meant for the owner (§ The review). Check each finding's citations against the source, then answer every finding in `## Review`. If a fix changes a decision's recommendation, reread that decision's other reasons. Do this after the units exist: a review that runs before them cannot see them.
9. **Later passes.** Have the same reviewer judge each answer and report only new defects. Fixes are where the next errors are, so repeat until a pass finds no new major defect. A pass may be scoped to the last round's changes, and a clean scoped pass covers only that scope. Fix what is left and say it was not re-reviewed. If a fourth pass still finds a major defect, stop and tell the owner: the design may be what is wrong.
10. **Ready when.** Ask of each unit: could it start and finish without guessing? Write one row per unit, and look one rail past this one: a rail can close with a promise still undeliverable, because a question sits past it with no default. Place each condition (§ The units).
11. **One ruling.** On the default branch, the proposed decisions reach the owner through `python3 .charter/bin/charter owner`. From an unmerged branch they reach no tool that reads the default branch, so hand them over yourself, in one ask, and name the branch. Give the owner a way to answer each decision on its own when there are more than three. `charter rule` commits where it runs, so a ruling on a branch is a reviewed script the owner runs on that branch. Where the decisions need several owner acts, ask for them together, and say who performs each. An answer is not leave to run an owner verb.
12. **Close and freeze.** Close the spec unit when the agent's work is done; the checkpoint holds what the owner has not done, so `status: blocked` is not needed. When the ruling lands, the agent that prepared it stamps it in the spec's header, even if the checkpoint stays open for other conditions. From then on the spec is a dated record: live truth is in the decisions, the units and the checkpoint.

## The units

The spec unit, the checkpoint and every work unit share one group, because a run takes one group and ignores a dependency outside it:

```yaml
# on every unit of the rail
rail: <rail id>
group: <the group the rail's row claims, else the rail id>
group_order: <n>
order: <n>
# on the checkpoint, which has no worker
role: epic
gate: human
depends_on: [<spec unit id>]
gate_reason: "HUMAN-ONLY: <what must hold>, then continue"
perimeter: []
# on each held unit
depends_on: [<checkpoint id>, <each earlier unit it needs>]
```

Number `order` with the spec unit first, the checkpoint next, then the work units. Name every dependency. An explicit `depends_on` replaces the rule that a step waits for the one before it, and a run can turn that rule off, so order alone does not hold anything. The checkpoint's status can stay `later`: `gate: human` with `role: epic` stops a Run All whatever its status, unless the status is terminal. On a work unit `later` holds nothing. `python3 .charter/bin/charter owner` lists a checkpoint.

Place each condition by kind:

| Condition | Where it goes |
|---|---|
| On the whole group | The checkpoint, named in every held unit's `depends_on` |
| On an earlier unit of the group | That unit, in `depends_on` |
| Outside, on a later unit | A second checkpoint in the group, in that unit's `depends_on` |
| Past this rail | A checkpoint on that rail |
| Past this rail, and no rail holds it | An open question, named in the ruling so the owner can add a rail. If it blocks, a checkpoint in this group, as for any blocking question |

Each condition is one acceptance line with a probe:

- A fact someone must supply: an `— owner: check` line whose probe tests where the answer is recorded.
- A blocking choice: a proposed decision, and an `— owner: do` line whose probe tests that it is ruled either way, `grep -Eq '^status: (active|rejected)' charter/decisions/<id>.md`. If it was rejected, rewrite the unit before the owner closes the line. `do` keeps that judgment from the delegate.

Do not use `— owner: decide` here: the owner's queue gives such a line no options to answer with.

Continue on a Run All clears the stop. It runs no probe and ticks no line, and on a run with no worktree of its own it also writes `status: done` to the checkpoint, so the order matters:

1. Run the line's probe and confirm the condition.
2. Close the line. At delegate level `strict`, the owner ticks it and commits. Where the level delegates it, the agent stages the tick and runs `python3 .charter/bin/charter handover`, and the delegate commits after rerunning the probe. A probe that only prints stays the owner's.
3. Add the evidence, and set the checkpoint to `done`.
4. The owner presses Continue.

A manual session has no such stop, and `unit start` does not look at earlier units. Read `python3 .charter/bin/charter owner` before starting a unit of a specced rail.

## The spec unit

Its acceptance, with each `<...>` filled in and `[<]rail id>` left as it is. Write the ids once the units exist. Drop AC-2 for a rail with no binding choice, and say why under `## Decisions`. Drop AC-5 where there is no clause map.

```markdown
- [ ] AC-1: the spec is filled in — probe: `f=charter/specs/<rail>.md; for h in Sources Mismatches Decisions Design 'Failure modes' 'What later rails inherit' 'Open questions' Units Review 'Ready when'; do grep -qx "## $h" $f || exit 1; done; ! grep -qE '^(<|[|] <)|[<]rail id>' $f`
- [ ] AC-2: each binding choice is a decision, and the gates pass — probe: `for d in <decision ids>; do f=charter/decisions/$d.md; grep -Eq '^ask: *[^ ]' $f && grep -Eq '^recommend: *[^ ]' $f || exit 1; done && python3 .charter/bin/charter check --all`
- [ ] AC-3: the units exist and the checkpoint holds them — probe: `for u in <work unit ids>; do f=$(ls .taskets/$u*.md); grep -q '^depends_on:.*<checkpoint id>' $f && grep -qx 'group: <group>' $f || exit 1; done; f=$(ls .taskets/<checkpoint id>*.md); grep -qx 'gate: human' $f && grep -qx 'role: epic' $f && grep -qx 'group: <group>' $f`
- [ ] AC-4: every finding is answered — probe: `awk -F'[|]' '/^[|] [FN][0-9]+ /{n++; a=$(NF-1); gsub(/^ +/,"",a); if (a !~ /^(fixed [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]|dismissed [^ ]+:[0-9]+: .|open [^ ]+)/) bad=1} /^No findings/{n++} END{exit (bad || !n)}' charter/specs/<rail>.md`
- [ ] AC-5: every clause-map probe has a unit line — probe: `for p in <clause-map probes>; do grep -lE -- "^- \[.\].*$p" .taskets/*.md | grep -qv '<spec unit id>' || { echo "no acceptance line: $p"; exit 1; }; done`
```

Put no ruling in these probes, so they stay true before and after the owner rules. They check form. The later passes check that the table holds every finding of every report, and that each answer is true. The spec's statements are normative, so do not run `charter anchors` on it, but its citations must still exist in a clean clone.

## The review

Give the reviewer the paths and the questions, not your conclusions. Any read-only session of another model family will do, for every pass. If none is available, stop and tell the owner: the writer cannot review its own spec. When Claude wrote the spec and `codex` is installed:

```bash
codex exec -C <root> -s read-only --ephemeral -c model_reasoning_effort=medium -o <report> "<prompt>" < /dev/null
```

Keep the `< /dev/null`: with stdin open, `codex exec` waits for it. When Codex wrote the spec, a Claude session with no Edit or Write tool will do, such as the `charter-reviewer` agent. The prompt asks for defects only, not style, each with its severity, line, evidence and fix:

1. Does every number, count and quotation match its source?
2. Does each citation say what is claimed, and does each cited path exist in a clean clone?
3. Walk each flow against the real code, with concurrency, retries, outages and restores. What breaks?
4. Which conclusion does the evidence not support, and which caveat was dropped?
5. Can each probe fail before the work and pass after it, and does it prove the deliverable?
6. Could two units still choose incompatibly? Is anything promised on no unit?
7. Does any step give an agent an owner's act? What does each owner script do beyond its title?
8. What is the strongest case that this design is wrong?

The review can find defects in code outside the rail. Give each a unit or an open question, because nothing else will hold it.
