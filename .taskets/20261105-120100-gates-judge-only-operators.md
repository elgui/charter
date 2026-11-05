---
id: 20261105-120100-gates-judge-only-operators
title: Gates that judge only a project's operators
status: later
priority: p3
created: 2026-11-05
updated: 2026-11-05
category: tooling
tags: [charter, gates, client-track, idea]
origin: branch-reconcile-20261105
plan: false
kind: work
perimeter: [package/.charter/**, tests/**, AGENTS.md, docs/gates.md, docs/method.md, docs/package.md, docs/method-visual.html, docs/assets/maps/**, docs/maps.md, docs/maps.html, package/VERSION, package/charter/config.json]
decisions: []
---

## Context

A client project ruled that charter's gates should judge only the people who operate it with agents, and stay silent for a collaborator who commits by hand (a designer, say). A brief for that feature was written on 2026-10-14 on the branch `brief/operators-switch` (`6e54779`, kept as the local tag `archive/brief-operators-switch`, not published because it names the client and a collaborator). It proposes an `operators` config key, an early silent exit in the hooks and the commit check for other authors, a CI skip for their commits, and a choice of where the rule is written. It measured the effect by replaying that collaborator's commits. Nothing of it exists on `main` (`$ git grep -n operators origin/main -- package/` finds nothing).

## Acceptance

- [ ] AC-1: with `operators` set, a commit by a non-operator passes the hooks and the commit check without a finding, and an operator's commit is judged as before (not verified) — probe: `cd tests && python3 -B -m unittest test_gates`
- [ ] AC-2: an unknown or malformed `operators` value fails closed, like every config key (not verified) — probe: `cd tests && python3 -B -m unittest test_config_0_4_3`

## Boundaries

Read the archived brief first, and keep its client detail out of this public repository. Who counts as an operator is the owner's setting (config is owner-only). A package change is a release (AGENTS.md).

## Log

- 2026-11-05: Filed while reconciling unmerged branches; nothing implemented (operator report, 2026-11-05). The brief's five rehearsal findings were rechecked on `main`: four still open are issues #38 to #41 (`$ gh issue view 38`); the fifth (triaged units shown as in progress) is addressed by the logged unit state of 0.4.23: a Log alone now reports `logged`, not `in-progress` (`package/.charter/bin/charter:302`).
