---
name: charter-spec
description: Turn a rail into units precise enough to build without guessing, with its sources compared, its binding choices decided, an independent review answered and a readiness verdict per unit. USE WHEN the owner asks for a spec for a rail, OR you are about to write a rail's units and two units built separately could choose incompatibly on something costly to undo, OR the rail answers to a text owed to someone, such as a contract or an agreement. Not for a rail whose units are plain; write those directly.
---

# charter-spec

An opt-in recipe. It adds one file, `charter/specs/<rail id>.md` from `charter/templates/spec.md`, and otherwise uses what the project already has: a spec unit, a checkpoint unit, proposed decisions and work units. It adds no gate and no status.

## Does this rail need it?

Before writing a rail's units, ask:

- Could two units built separately choose incompatibly, on something costly to undo: a schema, money, identity, a live path?
- Does the rail answer to a text owed to someone?

If neither, write the units. The owner can ask for a spec or waive one. A rail that already has units is left alone.

This recipe covers manual sessions and a Run All. A chain does not read `gate:`, so a checkpoint does not hold it: do not run a specced rail in a chain yet. Work from the project's own checkout, because its hooks do not fire from anywhere else. If the rail stands on another rail with no spec, say so to the owner before starting: that rail is usually the true first step.

## The steps

1. **Open the units.** Write the spec unit from `charter/templates/unit.md`, then the checkpoint (§ The checkpoint), before any work unit. Set `status: now` on the spec unit by hand, then `charter unit start <id>`.
2. **Name the sources.** List every text, file and system the rail rests on, with its version or date, and read them before designing. Check that the copy you were handed is the copy that was sent.
3. **Compare.** Set the sources beside the code and beside what the running system measures, and write down each mismatch with its source. This step finds the most. Read the code the design touches, and do not trust an earlier unit or brief about it.
4. **Map the clauses,** only where a binding text exists. One row per promise: clause, what it asks, the unit or rail that owns it, the probe. Point to decisions; never copy them into the table.
5. **Decide what binds.** For each choice ask: could two units built separately choose incompatibly? If it is also a real trade-off, it is a decision (`/charter-decision`) with `status: proposed`, `ask:`, `recommend:`, and `binds:` for the paths it will govern, even if they do not exist yet. Leave `check:` empty until the code exists, because `charter check --all` runs it. Option surveys go in the decision, not the spec.
6. **Sort the open questions** by who can answer: agent, owner, partner, customer. Answer the agent's. Give each of the others a default, or mark it blocking. Hold a blocking one on a checkpoint (§ The checkpoint). Keep the rest in the spec: a question nobody can act on yet is not an ask.
7. **Write the units,** with named probes. A probe must fail before the work, must prove the deliverable and not a state of the workflow, and must not contain a backtick, which cuts it silently. A probe of a live system proves the property, not a name.
8. **First review.** Have a reviewer of a model family other than the writer's read the spec, the decisions, the units and any script meant for the owner (§ The review). Check each finding's citations against the source, then answer every finding in `## Review`. Do this after the units exist: a review that runs before them cannot see them.
9. **Second pass.** Have the same reviewer judge each answer and report only new defects. Fixes are where the next errors are.
10. **Ready when.** Ask of each unit: could it start and finish without guessing? Write one row per unit, and look one rail past this one: a rail can close with a promise still undeliverable, because a question sits past it with no default. Place each condition (§ The checkpoint). Run the probes that compare the spec with the units.
11. **One ruling.** The proposed decisions reach the owner through `charter owner`. Where they need several owner acts, ask for them together, and say who performs each. An answer is not leave to run an owner verb.
12. **Close and freeze.** Close the spec unit when the agent's work is done; the checkpoint holds what the owner has not done, so `status: blocked` is not needed. Stamp the ruling in the spec's header. From then on the spec is a dated record: live truth is in the decisions, the units and the checkpoint.

## The checkpoint

A unit with no worker: `role: epic`, `gate: human`, a `gate_reason` that starts `HUMAN-ONLY:`, `perimeter: []`, and an `order` before the units it holds. `status: later` holds nothing in a Run All. `charter owner` lists a checkpoint, and a Run All stops at it.

Place each condition by kind:

| Condition | Where it goes |
|---|---|
| On the whole group | The checkpoint at its head |
| On an earlier unit of the group | Unit order. Where a unit has an explicit `depends_on`, which replaces order, name both that unit and the checkpoint |
| Outside, on a later unit | Its own checkpoint, ordered before that unit |
| Past this rail | A checkpoint on that rail |

Each condition is one acceptance line with a probe:

- A fact someone must supply: an `— owner: check` line whose probe tests where the answer is recorded.
- A blocking choice: a proposed decision, and an `— owner: do` line whose probe tests that it is ruled either way, `grep -Eq '^status: (active|rejected)' charter/decisions/<id>.md`. If it was rejected, rewrite the unit before the owner closes the line. `do` keeps that judgment from the delegate.

Do not use `— owner: decide` here: `charter owner` gives such a line no options to answer with.

Continue on a Run All clears the stop and does nothing else: it runs no probe, closes no line and closes no unit. Clearing a checkpoint takes four acts:

1. Run the line's probe and confirm the condition.
2. Close the line. At delegate level `strict`, the owner ticks it and commits. Where the level delegates it, the agent stages the tick and runs `charter handover`, and the delegate commits after rerunning the probe. A probe that only prints stays the owner's.
3. Add the evidence and set the checkpoint to `done`.
4. The owner presses Continue.

A manual session has no such stop, and `charter unit start` does not look at earlier units. Read `charter owner` before starting a unit of a specced rail.

## The spec unit

Its acceptance, with `<rail>` and the decision prefix filled in:

```markdown
- [ ] AC-1: the spec holds its sections — probe: `for h in Sources Decisions 'Open questions' Units Review 'Ready when'; do grep -q "^## $h" charter/specs/<rail>.md || exit 1; done`
- [ ] AC-2: each binding choice is a decision, and the gates pass — probe: `ls charter/decisions/<prefix>-*.md && python3 .charter/bin/charter check --all`
- [ ] AC-3: the units exist, held by a checkpoint — probe: `grep -l '^rail: <rail>' .taskets/*.md | xargs grep -l '^gate: human' | grep -q .`
- [ ] AC-4: every finding is answered — probe: `grep -Eq '^[|] F1 ' charter/specs/<rail>.md && ! grep -E '^[|] [FN][0-9]+ ' charter/specs/<rail>.md | grep -vE 'fixed|dismissed|open'`
```

Put no ruling in these probes, so they stay true before and after the owner rules. The spec's own statements are normative, so do not run `charter anchors` on it: its citations still have to exist in a clean clone, and the review checks that.

## The review

Give the reviewer the paths and the questions, not your conclusions. When Claude wrote the spec:

```bash
codex exec -C <root> -s read-only --ephemeral -c model_reasoning_effort=medium -o <report> "<prompt>" < /dev/null
```

Keep the `< /dev/null`: with stdin open, `codex exec` waits for it. When Codex wrote the spec, use a session of another family with no Edit or Write tool, such as the `charter-reviewer` agent. The prompt asks for defects only, not style, each with its severity, line, evidence and fix:

1. Does every number, count and quotation match its source?
2. Does each citation say what is claimed, and does each cited path exist in a clean clone?
3. Walk each flow against the real code, with concurrency, retries, outages and restores. What breaks?
4. Which conclusion does the evidence not support, and which caveat was dropped?
5. Can each probe fail before the work and pass after it, and does it prove the deliverable?
6. Could two units still choose incompatibly? Is anything promised on no unit?
7. Does any step give an agent an owner's act? What does each owner script do beyond its title?
8. What is the strongest case that this design is wrong?

The review can find defects in code outside the rail. Give each a unit or an open question, because nothing else will hold it.
