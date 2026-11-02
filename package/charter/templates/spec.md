# Spec: rail <rail id>

<!-- Written with the charter-spec skill. A dated record: it freezes at the ruling, and live truth stays in the
     decisions, the units and the checkpoint. Aim for about 3,000 words. Point to what other files hold rather than
     copying it. Delete the clause map when no binding text exists. A section with nothing in it says `None:` and why.
     Delete this comment. -->

- **Rail and scope:** `<rail id>`, <scope item, if any>. Spec unit `<id>`.
- **As of:** <YYYY-MM-DD>
- **Ruled:** <date and how, or "not yet">

## Sources

| Source | Version or date | What it binds |
|---|---|---|
| <source> | <version> | <what it binds> |

## Mismatches

<Each one found by comparing the sources, the code and what the running system measures, with its source.>

## Clause map

<Only where a binding text exists. One row per promise.>

| Clause | What it asks | Unit or rail | Probe |
|---|---|---|---|
| <clause> | <what it asks> | <unit or rail> | <probe name> |

## Decisions

| Decision | In one line |
|---|---|
| <id> | <what it settles> |

## Design

<What the units share and no decision holds: the data, the contract, the flows.>

## Failure modes

<Each flow walked against the code: concurrency, retries, outages, restores.>

## What later rails inherit

<What this rail leaves them, and what it leaves undecided.>

## Open questions

| Id | Question | Who can answer | Default | Blocks | Held by |
|---|---|---|---|---|---|
| <id> | <question> | <agent, owner, partner or customer> | <default> | <what it blocks> | <spec or checkpoint> |

## Units

| Unit | What it proves |
|---|---|
| <id> | <what it proves> |

## Review

<Every finding of both passes, ids F and N. Answer: `fixed <commit>`, `dismissed <path:line>: <why>`, or `open <question id>`. For a clean review, a line: `No findings: <reviewer, date>`.>

| Id | Severity | Finding | Answer |
|---|---|---|---|
| <F1> | <severity> | <finding> | <answer> |

## Ready when

| Unit | Ready when | Held by |
|---|---|---|
| <id> | <condition> | <checkpoint or unit> |
