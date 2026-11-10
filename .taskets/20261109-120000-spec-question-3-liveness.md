---
id: 20261109-120000-spec-question-3-liveness
title: Add the eventually-promise clause to charter-spec's review question 3 when that branch lands
status: next
priority: p3
created: 2026-11-09
updated: 2026-11-09
category: method
tags: [charter, charter-spec, flow-promises]
origin: flow-promises-2026-11-09
perimeter: [package/.claude/skills/charter-spec/SKILL.md]
decisions: []
kind: work
---

## Context

The flow-promises brief's K2 asks for one clause in charter-spec's review question 3: "and what each eventually-promise needs to keep running" (`docs/briefs/2026-11-09-flow-promises-checks-world-actions-owner-lines.md`, § K2, item 2). The spec step lives only on the unreleased branch `charter-spec-draft`, where question 3 reads "Walk each flow against the real code, with concurrency, retries, outages and restores. What breaks?" (`git show charter-spec-draft:package/.claude/skills/charter-spec/SKILL.md`, line 110 at dee2f42). That branch is shared and was not checked out for 0.4.26, so this note holds the change for whoever merges it. Release 0.4.26 put the matching guidance in `package/charter/templates/unit.md`.

## Acceptance

- [ ] AC-1: question 3 of the charter-spec review asks what each eventually-promise needs to keep running — probe: `grep -n "what each eventually-promise needs to keep running" package/.claude/skills/charter-spec/SKILL.md`

## Evidence

## Log

- 2026-11-09 12:00 created by the 0.4.26 session; the spec branch was left untouched
- 2026-11-09 14:00 the clause is committed on `charter-spec-draft` as 235f2b4 (question 3 of the spec review, `package/.claude/skills/charter-spec/SKILL.md:110` on that branch); AC-1's probe greps the working tree, so it already passes in a `charter-spec-draft` checkout; on `main` it passes only once that branch merges, and the unit stays `next` until then
