---
id: 20261102-191100-sdgat
title: "Checkpoint: Charter 0.4.20 is on main"
status: later
priority: p2
created: 2026-11-02
updated: 2026-11-02
category: tooling
tags: [charter, spec-step]
origin: spec-step-proposal-20261102
group: spec-step-defects
group_order: 110
order: 1
role: epic
gate: human
gate_reason: "HUMAN-ONLY: Charter 0.4.20 is on main (oa-j6jt), then continue; these fixes are a package release, and one before it would collide with that release"
perimeter: []
decisions: []
kind: work
---

## Context

No worker runs this. It holds the group at its place in a Run All, because `status: later` is not a skip signal. Each unit behind it changes `package/`, which makes a release (`AGENTS.md:18`), so they wait for 0.4.20. Clearing it: confirm the probe, the owner closes the line, set this unit to `done`, then Continue.

## Acceptance

- [ ] AC-1: Charter 0.4.20 is on `origin/main` — owner: check — probe: `git show origin/main:package/VERSION | grep -qvx '0.4.19'`

## Evidence

- $ git show origin/main:package/VERSION → 0.4.21, after the push of 2026-11-03; the probe passes

## Log

- 2026-11-03: 0.4.21 reached origin/main, so the group went ahead on branch `fix/spec-step-defects`. The owner line stays open for the owner to close.

## Outside perimeter
