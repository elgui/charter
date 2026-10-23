#!/usr/bin/env python3
"""Build the charter maps from one source: the data below.

    python3 docs/assets/maps/build.py

writes docs/maps.md (the agent edition), docs/maps.html (the page for people) and one SVG per
view in docs/assets/maps/. The three carry the same ids: cap.* a capability, c.* a concept,
g.* a gate, a.* an owner act. Edit this file, never the outputs. Standard library only.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = (ROOT / "package/VERSION").read_text().strip()

# --------------------------------------------------------------------------------------------
# Data. Every row says where it comes from, as a repository path or `name in path`.
# --------------------------------------------------------------------------------------------

ACTORS = [
    ("owner", "Owner", "O",
     "The one person who signs, rules and merges, and holds the files that define the gates",
     "`package/.claude/rules/charter.md` § What only the owner changes"),
    ("agent", "Agent session", "A",
     "Claude Code, Codex or pi; works one unit at a time and proposes what it cannot settle",
     "`docs/method.md` § Artifacts and their owners"),
    ("reviewer", "Independent reviewer", "R",
     "A party that wrote neither side, meant to be another model family (Codex) or a person",
     "`package/.claude/agents/charter-reviewer.md`, `docs/method.md` § The rules (R2)"),
    ("delegate", "Owner's delegate", "D",
     "A watcher run by cron outside Claude Code; takes the owner acts that the owner's level allows",
     "`bin/charter-delegate`, `docs/design/owner-delegate.md`"),
    ("machines", "The gates", "G",
     "Claude Code hooks, the git hook and CI, all running one engine",
     "`package/.charter/checks.py`, `docs/gates.md`"),
    ("client", "Client", "C",
     "Signs the devis that the scope summarises; reads the accepted units",
     "`docs/daily-use.md` § 7. Report"),
]
ACTOR = {a[0]: a for a in ACTORS}

# Hue follows the cluster a capability or concept belongs to; nothing rides on hue alone.
HUES = {"art": "written charter", "unit": "the unit", "gate": "the gates", "owner": "the owner",
        "rec": "records", "chain": "the chain", "fleet": "the fleet"}

CAPS = [
    dict(
        id="cap.agree", n=1, hue="art", title="Write down what is agreed",
        promise="What is sold, the road and every design choice live in the repository, one file each, where a machine can check them.",
        what=("On the client track `charter/scope.md` summarises the signed devis, and work outside it is a change request "
              "that the owner approves. `charter/rails.md` is the road in order, and adding an item to it is the recorded re-plan. "
              "A decision is one file with its reason and its expiry; code that depends on it carries `charter:<id>`, and its "
              "`check:` command runs on the files its `binds:` names. A lesson that binds the project is a decision with `kind: lesson`."),
        actors=["owner", "agent"],
        entry=[("charter-decision skill", "\"record the decision\": writes `charter/decisions/<id>.md`", "`package/.claude/skills/charter-decision/SKILL.md`"),
               ("charter decisions index", "regenerates the decision index", "`cmd_decisions` in `package/.charter/bin/charter`"),
               ("templates", "scope, rails, decision, change", "`package/charter/templates/`"),
               ("charter rule | approve | rail", "the owner's ruling, in one commit", "`package/.charter/owner.py`")],
        files=["charter/scope.md", "charter/rails.md", "charter/decisions/<id>.md", "charter/decisions/INDEX.md", "charter/changes/<id>.md"],
        concepts=["c.track", "c.scope", "c.change", "c.rails", "c.decision", "c.owner", "c.agent"],
        sources="`docs/method.md` § Artifacts and their owners; `check_scope` in `package/.charter/checks.py`; `package/.charter/rails.py`",
        more=["docs/method.md", "docs/gates.md"]),
    dict(
        id="cap.unit", n=2, hue="unit", title="Work in units that prove themselves",
        promise="Each deliverable is one file that says what it may touch, how it will be checked, and what happened.",
        what=("A unit (a tasket in `.taskets/`) cites a scope item or a rail, declares its `perimeter:`, and lists acceptance "
              "criteria, each a probe that fails before the work and passes after. `## Evidence` names a commit or a `$ command` run, "
              "and the dated `## Log` is what the next session resumes from. `charter next` says what comes next; `charter unit start` "
              "attributes the session's edits and cost to the unit."),
        actors=["agent"],
        entry=[("charter-unit skill", "\"start unit <id>\", \"finish the unit\"", "`package/.claude/skills/charter-unit/SKILL.md`"),
               ("charter next", "the road, the next units, what waits on the owner; writes nothing", "`cmd_next` in `package/.charter/bin/charter`"),
               ("charter unit start | stop | show", "the session's active unit, and a unit's perimeter fit", "`cmd_unit` in `package/.charter/bin/charter`"),
               ("charter probe <id>", "runs the probes, prints the `$ command` evidence lines", "`cmd_probe` in `package/.charter/bin/charter`")],
        files=[".taskets/<id>.md", "charter/templates/unit.md"],
        concepts=["c.unit", "c.perimeter", "c.acceptance", "c.probe", "c.evidence", "c.log", "c.accepted", "c.agent"],
        sources="`docs/daily-use.md` § The loop; `package/charter/templates/unit.md`",
        more=["docs/daily-use.md", "package/charter/templates/unit.md"]),
    dict(
        id="cap.gate", n=3, hue="gate", title="Check every change, three times",
        promise="One engine judges each change as the agent edits, at commit, and in CI from a clean clone.",
        what=("Claude Code hooks refuse an edit before it lands; the git pre-commit hook judges what is staged, whoever commits; "
              "CI runs the same checks at merge. A hard gate refuses and names its override, the honest way past it. Everything "
              "else warns and goes to the gate log, the evidence for turning a warning into a gate. A gate fails open on its own "
              "errors, except a config it cannot read, which is refused."),
        actors=["machines", "agent"],
        entry=[("Claude Code hooks", "SessionStart, PreToolUse, PostToolUse, Stop, SessionEnd", "`package/.charter/settings-fragment.json`"),
               ("git pre-commit", "`charter check --staged`, whoever commits", "`package/.charter/githooks/pre-commit`"),
               ("CI", "`charter check --all --ci`, `charter anchors`", "`package/.github/workflows/charter.yml`"),
               ("charter setup | config | log", "activate the hook per clone; what the gates read; what they did", "`package/.charter/bin/charter`")],
        files=[".charter/checks.py", ".charter/hooks/", ".charter/githooks/pre-commit", ".github/workflows/charter.yml", "charter/config.json", ".git/charter/log.jsonl"],
        concepts=["c.gate", "c.line", "c.override", "c.keys", "c.gatelog", "c.track", "c.accepted"],
        sources="`docs/gates.md`; `package/.charter/checks.py`",
        more=["docs/gates.md"]),
    dict(
        id="cap.owner", n=4, hue="owner", title="Keep the owner in charge",
        promise="The files and fields that define the gates are the owner's. Agents propose; the owner rules in one command.",
        what=("An agent's edit of an owner-only file or field is refused in the session, at a commit made inside Claude Code, "
              "and by the author check in CI. `charter owner` lists what waits on the owner, each with its command; `charter rule`, "
              "`approve` and `rail` write a ruling and commit it. An agent stages an owner-only change and runs `charter handover`, "
              "which prints the owner's one line. Below `strict`, the owner's delegate takes the acts the level allows."),
        actors=["owner", "delegate", "agent"],
        entry=[("charter owner", "the queue that waits on the owner, with the command for each", "`queue` in `package/.charter/owner.py`"),
               ("charter rule | approve | rail", "rule a decision, approve a change, set a rail, in one commit", "`package/.charter/owner.py`"),
               ("charter handover", "records an owner-only change and prints the owner's line", "`record_handover` in `package/.charter/lib.py`"),
               ("CHARTER_OWNER=1 … owner commit", "the owner's line: `CHARTER_OWNER=1 python3 <root>/.charter/bin/charter owner commit` commits exactly what was handed over", "`docs/design/owner-handover.md`"),
               ("charter delegate plan | level", "what the delegate may take here, and the level", "`package/.charter/delegate.py`")],
        files=["charter/config.json (owner, delegate.level)", ".git/charter/handover.json"],
        concepts=["c.owner", "c.keys", "c.delegate", "c.decision", "c.change", "c.rails"],
        sources="`package/.claude/rules/charter.md:28-51`; `docs/gates.md` § Owner-only changes",
        more=["docs/design/owner-delegate.md", "docs/design/owner-handover.md"]),
    dict(
        id="cap.report", n=5, hue="rec", title="Say what is true, and what it cost",
        promise="Progress, acceptance and cost are computed from the repository, and every claim points at something a reader can open.",
        what=("`charter synth` writes `charter/progress.md`: scope and rails with their units, done and accepted apart from done "
              "and not accepted, work in progress, open decisions, perimeter fit and cost; it refuses to write if its own anchor "
              "check fails. `charter anchors` checks any deliverable: each claim line carries an anchor or admits it is reported "
              "or an inference. The SessionEnd hook records tokens per session, and `charter ledger fold` prices them into cost per accepted unit."),
        actors=["agent", "owner", "client"],
        entry=[("charter-progress skill", "\"where does this stand?\"", "`package/.claude/skills/charter-progress/SKILL.md`"),
               ("charter synth [--write]", "the progress synthesis, anchored", "`cmd_synth` in `package/.charter/bin/charter`"),
               ("charter anchors <file>", "every claim line anchored, or admitted", "`check_anchors` in `package/.charter/checks.py`"),
               ("charter ledger fold", "this machine's sessions, priced, folded per unit", "`cmd_ledger` in `package/.charter/bin/charter`"),
               ("--json on next, unit show, owner", "the same answers for a tool", "`docs/package.md` § Versioning and upgrade (0.4.13)")],
        files=["charter/progress.md (generated)", "charter/ledger.jsonl", ".git/charter/sessions.jsonl"],
        concepts=["c.synth", "c.anchor", "c.ledger", "c.accepted", "c.gatelog", "c.evidence"],
        sources="`docs/method.md` § The progress synthesis, § Accepted results, § Cost per accepted result at this scale",
        more=["docs/method.md"]),
    dict(
        id="cap.chain", n=6, hue="chain", title="Run the road unattended",
        promise="A chain of fresh sessions works the road unit after unit, each checking the last, reviewed group by group.",
        what=("`/charter-chain` starts a chain, on a new branch `chain/<id>` when run from main. Each session receives the chain rules verbatim, verifies "
              "its predecessor, works, and hands over before 25% of its context window; past 30% the hook refuses every tool but the "
              "handoff, the unit files, git and the charter CLI. `charter chain next` validates the handoff, re-runs the probes and opens the next session. At the end of each "
              "group (a rail item) Codex reviews its commits and the next session answers every finding. When the road needs the owner, "
              "the chain waits with every act in `owner.md`; the owner runs them with `charter owner run` and types `/resume-chain ok`."),
        actors=["agent", "reviewer", "owner"],
        entry=[("/charter-chain", "start a chain from a unit and an instruction", "`package/.claude/skills/charter-chain/SKILL.md`"),
               ("charter chain start | next | status | stop | report", "run, hand over, watch, end, report", "`package/.charter/chain.py`"),
               ("charter owner run", "the owner runs a waiting chain's acts", "`package/.charter/owner_acts.py`"),
               ("/resume-chain ok | skip", "the owner's resume, performed by the hook", "`package/.claude/commands/resume-chain.md`")],
        files=[".charter/chain-rules.md", "charter/templates/handoff.md", "charter/templates/owner.md", ".git/charter/chain/<id>/"],
        concepts=["c.chain", "c.reviewer", "c.rails", "c.log", "c.unit", "c.owner"],
        sources="`docs/daily-use.md` § Running units in a chain; `docs/design/continuous-chain.md`",
        more=["docs/design/continuous-chain.md", "docs/daily-use.md"]),
    dict(
        id="cap.fleet", n=7, hue="fleet", title="Install, upgrade and oversee projects",
        promise="One checkout of this repository installs the package into any project, keeps it current and watches the fleet.",
        what=("`charter-pkg install` copies the package into a project, records the hash of each owned file in "
              "`.charter/manifest.json` and stages the result for the owner's commit; `upgrade` shows each diff; `survey` measures a "
              "project before a migration; `fleet` lists every charter project and upgrades the ones behind. Each fresh clone runs "
              "`charter setup` once to activate the git hook. The machine layer, installed once per user, adds a SessionStart hook "
              "that says when a project is behind, and the CharterAdmin skill with its Migrate workflow."),
        actors=["owner", "agent"],
        entry=[("charter-pkg install | upgrade | uninstall | status", "the package into one project", "`bin/charter-pkg`"),
               ("charter-pkg fleet", "every project: list, --upgrade, --commit, --levels", "`do_fleet` in `bin/charter-pkg`"),
               ("charter-pkg survey | instructions", "measure a project before a migration; read-only", "`bin/charter_survey.py`"),
               ("charter-pkg machine install", "the hook and CharterAdmin skill in ~/.claude", "`bin/charter_machine.py`"),
               ("charter setup", "once per clone: activate the git hook", "`cmd_setup` in `package/.charter/bin/charter`")],
        files=["package/ → <project>/.charter, charter/, .claude/, .github/", ".charter/manifest.json", "charter/VERSION", "~/.claude/charter-local.md"],
        concepts=["c.track", "c.keys", "c.owner"],
        sources="`docs/install.md`; `docs/package.md`; `machine/README.md`",
        more=["docs/install.md", "docs/package.md", "machine/README.md"]),
]
CAP = {c["id"]: c for c in CAPS}

CLUSTERS = {
    "who": ("Who acts", "owner"),
    "art": ("The written charter", "art"),
    "unit": ("The unit of work", "unit"),
    "gate": ("The gates", "gate"),
    "rec": ("What is true, and what it cost", "rec"),
    "chain": ("Running the road", "chain"),
}

# (id, name, cluster, hue, sub, definition, source)
CONCEPTS = [
    ("c.owner", "Owner", "who", "owner", "rules · commits the keys · merges",
     "The person who signs and rules: approves change requests, rules decisions, commits owner-only changes and merges. Named in `owner` in `charter/config.json` for the CI author check.",
     "`package/.claude/rules/charter.md:28-40`; `check_owner_commits` in `package/.charter/checks.py`"),
    ("c.agent", "Agent session", "who", "unit", "Claude Code · Codex · pi",
     "Works one unit at a time and is its single writer. Proposes what it cannot settle: a change request, a decision, a hand-over.",
     "`docs/method.md` § Artifacts and their owners"),
    ("c.delegate", "Owner's delegate", "who", "owner", "watcher outside Claude Code",
     "Takes owner acts up to the level the owner set (strict, routine, answers, open), after rules and a model judge them. Structural changes are never delegated.",
     "`docs/design/owner-delegate.md` § Levels; `LEVEL_KINDS` in `package/.charter/lib.py`"),
    ("c.reviewer", "Independent reviewer", "chain", "chain", "another model family",
     "A party that wrote neither side: reviews each group of a chain, reviews the owner's acts at a wait, and signs the `review:` evidence line when `review.required` is on.",
     "`package/.charter/chain_groups.py`; `docs/gates.md` § Done needs evidence"),
    ("c.track", "Track", "art", "art", "client · prototype",
     "`client` when a signed devis covers the project, `prototype` otherwise. It selects which gates are hard: the scope gate runs only on the client track.",
     "`docs/method.md` § Two tracks"),
    ("c.scope", "Scope", "art", "art", "charter/scope.md",
     "The summary of the signed devis: what is sold, what is not, what is assumed. Client track only; the owner's file.",
     "`docs/method.md` § The method on one page"),
    ("c.change", "Change request", "art", "art", "charter/changes/<id>.md",
     "Work outside the scope. Anyone proposes it; its paths stay refused until the owner sets `approved`, `approved_by` and `approved_on`.",
     "`check_changes` in `package/.charter/checks.py`; `package/charter/templates/change.md`"),
    ("c.rails", "Rails", "art", "art", "charter/rails.md",
     "The road, items in order. Every open unit names one; adding an item is the recorded re-plan; a chain group is one item.",
     "`docs/gates.md` § Rails; `package/.charter/rails.py`"),
    ("c.decision", "Decision", "art", "art", "charter/decisions/<id>.md",
     "One choice with `## Because` and `expires:`. Code cites it as `charter:<id>`; its `check:` runs on files its `binds:` names. A project lesson is a decision with `kind: lesson`.",
     "`docs/gates.md` § Decisions (R1); `package/charter/templates/decision.md`"),
    ("c.unit", "Unit", "unit", "unit", ".taskets/<id>.md",
     "One deliverable as a tasket: cites a scope item or a rail, declares a perimeter, lists acceptance, carries evidence and a log. One session owns it.",
     "`docs/method.md` § The unit of work; `package/charter/templates/unit.md`"),
    ("c.perimeter", "Perimeter", "unit", "unit", "perimeter: [app/**]",
     "The paths a unit may touch. A file outside it needs a `- path: why` line under `## Outside perimeter` before the commit.",
     "`package/.claude/rules/charter.md:16`; `check_perimeter` in `package/.charter/checks.py`"),
    ("c.acceptance", "Acceptance", "unit", "unit", "## Acceptance · AC-n",
     "Checkbox lines, one binary probe each. `(guard)` marks one that protects behaviour that already works; `— owner:` one that only the owner may close.",
     "`docs/method.md` § The unit of work; `package/.claude/rules/charter.md:36`"),
    ("c.probe", "Probe", "unit", "unit", "charter probe <id>",
     "The command that answers one criterion yes or no. It fails before the work and passes after; with an opt-in the gates run it again, also at the unit's base.",
     "`docs/daily-use.md` § Words used here; `run_probes_at_base` in `package/.charter/checks.py`"),
    ("c.evidence", "Evidence", "unit", "unit", "## Evidence · sha · $ cmd",
     "A commit SHA that resolves, a `path:line`, and the `$ command` lines of the probes. A path or a URL alone is refused.",
     "`package/.claude/rules/charter.md:24`"),
    ("c.log", "Log", "unit", "unit", "## Log · dated, append-only",
     "Dated lines appended when something lands or the session stops. A resumed session reads the unit, not the transcript.",
     "`package/.claude/rules/charter.md:19`"),
    ("c.accepted", "Accepted", "unit", "pass", "done = accepted",
     "Done means accepted: every box checked and evidence that resolves. A done flip without it is refused; the synthesis lists done and accepted apart from the rest.",
     "`docs/method.md` § The rules (R9); `check_unit_done` in `package/.charter/checks.py`"),
    ("c.keys", "Owner-only keys", "gate", "owner", "config · engine · settings · CI",
     "The files and fields that define the gates: scope, rails, config, the engine, settings, the CI workflow, approval and ruling fields, split units, `— owner:` lines. Refused to an agent's edit.",
     "`docs/gates.md` § Owner-only changes; `owner_only_changes` in `package/.charter/checks.py`"),
    ("c.gate", "Gate", "gate", "gate", "package/.charter/checks.py",
     "A check that refuses (hard) or warns. Hard: scope, size, done, decisions in their retired and failing forms, anchors in CI, owner-only changes. The rest warns and is logged.",
     "`docs/method.md` § The rules"),
    ("c.line", "Three lines", "gate", "gate", "session · commit · CI",
     "Where the same gate runs: in the session (Claude Code hooks), at commit (git pre-commit, any agent), at merge (CI from a clean clone). Each catches what the one before can miss.",
     "`docs/gates.md` (introduction)"),
    ("c.override", "Override", "gate", "gate", "named in every refusal",
     "The honest way past a refusal, named in it: write the change request, move code out of a frozen file, add the evidence, propose a successor decision.",
     "`docs/method.md` § The hard gates and why a warning would not do"),
    ("c.gatelog", "Gate log", "gate", "rec", ".git/charter/log.jsonl",
     "Every finding with its gate, level and path; per machine, never committed. A warning that keeps firing on real problems is the case for making it a gate.",
     "`docs/gates.md` (introduction); `docs/daily-use.md` § The owner's weekly look"),
    ("c.anchor", "Anchor", "rec", "rec", "path:line · sha · $ cmd · URL",
     "What a claim points at. Four evidence classes: measured (resolves here), vendor (a URL), reported and inference (admitted, counted apart).",
     "`docs/method.md` § Evidence classes"),
    ("c.synth", "Progress synthesis", "rec", "rec", "charter/progress.md",
     "Generated by `charter synth` from the repository, never edited by hand; refuses to write when its own anchor check fails.",
     "`docs/method.md` § The progress synthesis"),
    ("c.ledger", "Ledger", "rec", "rec", "charter/ledger.jsonl",
     "Tokens and estimated cost per session, folded per unit; cost per accepted unit, printed as a lower bound while any cost is unknown.",
     "`docs/method.md` § Cost per accepted result at this scale"),
    ("c.chain", "Chain", "chain", "chain", "chain/<id> · s01 → s02 → …",
     "Fresh sessions over the road: rules injected verbatim, hand over at 25% of the context window (past 30% only the handoff, unit files, git and the charter CLI pass), a validated handoff, a review per group, waits on the owner with `owner.md`.",
     "`docs/method.md` § The continuous chain"),
]
CON = {c[0]: c for c in CONCEPTS}

# (from, verb, to, style, source); style: rule (the owner acts), cite, propose, gate, machine, flow, wait
RELATIONS = [
    ("c.owner", "signs", "c.scope", "rule", "`docs/method.md` § Artifacts and their owners"),
    ("c.owner", "approves", "c.change", "rule", "`approve` in `package/.charter/owner.py`"),
    ("c.owner", "orders", "c.rails", "rule", "`package/charter/templates/rails.md`"),
    ("c.owner", "rules on", "c.decision", "rule", "`rule` in `package/.charter/owner.py`"),
    ("c.owner", "holds", "c.keys", "rule", "`package/.claude/rules/charter.md:28-32`"),
    ("c.owner", "sets the level of", "c.delegate", "rule", "`docs/design/owner-delegate.md` § Where the level is read"),
    ("c.delegate", "commits some owner acts, by level", "c.keys", "rule", "`package/.claude/rules/charter.md:44`"),
    ("c.agent", "works one at a time", "c.unit", "flow", "`docs/method.md` § Artifacts and their owners"),
    ("c.agent", "proposes", "c.change", "propose", "`package/.claude/rules/charter.md:9`"),
    ("c.agent", "proposes", "c.decision", "propose", "`package/.claude/skills/charter-decision/SKILL.md`"),
    ("c.track", "client track needs", "c.scope", "cite", "`docs/method.md` § Two tracks"),
    ("c.track", "selects which are hard", "c.gate", "cite", "`docs/method.md` § Two tracks"),
    ("c.change", "unlocks paths outside", "c.scope", "cite", "`docs/gates.md` § Scope (R6)"),
    ("c.unit", "cites", "c.scope", "cite", "`package/.claude/rules/charter.md:9`"),
    ("c.unit", "names an item of", "c.rails", "cite", "`package/.claude/rules/charter.md:10`"),
    ("c.unit", "relies on", "c.decision", "cite", "`docs/method.md` § The unit of work"),
    ("c.unit", "declares", "c.perimeter", "flow", "`package/charter/templates/unit.md`"),
    ("c.unit", "lists", "c.acceptance", "flow", "`package/charter/templates/unit.md`"),
    ("c.unit", "keeps", "c.log", "flow", "`package/.claude/rules/charter.md:19`"),
    ("c.acceptance", "is answered by", "c.probe", "flow", "`docs/method.md` § The unit of work"),
    ("c.probe", "prints the $ lines of", "c.evidence", "machine", "`cmd_probe` in `package/.charter/bin/charter`"),
    ("c.evidence", "points at", "c.anchor", "flow", "`package/.claude/rules/charter.md:24`"),
    ("c.acceptance", "every box checked for", "c.accepted", "flow", "`docs/gates.md` § Done needs evidence (R9)"),
    ("c.evidence", "must resolve for", "c.accepted", "flow", "`docs/gates.md` § Done needs evidence (R9)"),
    ("c.keys", "define", "c.gate", "gate", "`docs/gates.md` § Owner-only changes"),
    ("c.gate", "runs at", "c.line", "gate", "`docs/gates.md` (introduction)"),
    ("c.gate", "names in each refusal", "c.override", "gate", "`docs/method.md` § The hard gates and why a warning would not do"),
    ("c.gate", "logs every finding to", "c.gatelog", "machine", "`docs/gates.md` (introduction)"),
    ("c.gatelog", "promotes a warning to", "c.gate", "machine", "`docs/method.md` § The method on one page"),
    ("c.gate", "refuses done without", "c.accepted", "gate", "`check_unit_done` in `package/.charter/checks.py`"),
    ("c.gate", "watches", "c.perimeter", "gate", "`check_perimeter` in `package/.charter/checks.py`"),
    ("c.gate", "runs the check: of", "c.decision", "gate", "`run_decision_checks` in `package/.charter/checks.py`"),
    ("c.anchor", "checks every line of", "c.synth", "machine", "`cmd_synth` in `package/.charter/bin/charter`"),
    ("c.synth", "counts", "c.accepted", "machine", "`docs/method.md` § The progress synthesis"),
    ("c.synth", "reads", "c.ledger", "machine", "`docs/method.md` § The progress synthesis"),
    ("c.ledger", "charges each session to", "c.unit", "machine", "`package/.charter/hooks/session_end.py`"),
    ("c.chain", "runs one after another", "c.unit", "flow", "`docs/method.md` § The continuous chain"),
    ("c.chain", "takes a group per item of", "c.rails", "cite", "`package/.charter/chain_groups.py`"),
    ("c.chain", "resumes from", "c.log", "flow", "`docs/method.md` § The continuous chain"),
    ("c.chain", "waits with owner.md on", "c.owner", "wait", "`package/.charter/owner_acts.py`"),
    ("c.reviewer", "reviews each group of", "c.chain", "flow", "`package/.charter/chain_groups.py`"),
    ("c.reviewer", "signs the review: line of", "c.evidence", "propose", "`docs/gates.md` § Done needs evidence (R9)"),
]

# Gates x lines. Cell: (glyph, note); glyph: R refuses, C refuses under a condition, W warns, - not checked.
GATES = [
    ("g.scope", "Scope", "R6", ("C", "client"), ("C", "client"), ("C", "client"),
     "Write a change request; the owner approves it", "`docs/gates.md` § Scope (R6)"),
    ("g.rails", "Rails", "R6", ("-", ""), ("C", "rails.required"), ("C", "rails.required"),
     "Name an open rail item; the owner adds items", "`docs/gates.md` § Rails"),
    ("g.size", "Size: frozen file", "R3", ("R", ""), ("R", ""), ("R", ""),
     "Move code out; or the owner opens a split unit or names an exception", "`docs/gates.md` § Size (R3)"),
    ("g.done", "Done needs evidence", "R9", ("R", ""), ("R", ""), ("R", ""),
     "Check the boxes and cite a commit or a $ command; or keep it open", "`docs/gates.md` § Done needs evidence (R9)"),
    ("g.probes", "Probes run again", "R9", ("-", ""), ("C", "probes.at_commit"), ("C", "probes.in_ci"),
     "Make the probe pass; one that passed before the work is refused with probes.base_must_fail", "`docs/gates.md` § Done needs evidence (R9)"),
    ("g.decisions", "Decisions", "R1", ("R", "retired citation"), ("R", ""), ("R", ""),
     "Propose a successor decision; the owner retires the old one", "`docs/gates.md` § Decisions (R1)"),
    ("g.perimeter", "Perimeter", "R4", ("W", ""), ("C", "client"), ("-", ""),
     "Add `- path: why` under ## Outside perimeter", "`docs/gates.md` § Perimeter (R4)"),
    ("g.owner", "Owner-only changes", "R6 R7", ("R", ""), ("R", "in Claude Code"), ("R", "author"),
     "Leave it staged, run charter handover; the owner commits", "`docs/gates.md` § Owner-only changes"),
    ("g.config", "Config readable", "", ("W", "banner"), ("R", ""), ("R", ""),
     "The owner corrects charter/config.json", "`docs/gates.md` § Config"),
    ("g.memory", "Memory", "R8", ("-", ""), ("W", ""), ("W", ""),
     "Give the decision a ## Because and a later expires:", "`docs/gates.md` § Memory (R8)"),
    ("g.stop", "Completion claim", "R9 R10", ("R", "once a turn"), ("-", ""), ("-", ""),
     "Cite a commit, a path:line or a $ command, or say what is not done", "`docs/gates.md` § Stop gate (R9/R10 in the session)"),
    ("g.anchors", "Anchored deliverables", "R10", ("-", ""), ("-", ""), ("C", "client"),
     "Anchor each claim, or mark it reported or inference", "`docs/gates.md` § Anchors (R10)"),
    ("g.budget", "Chain budget", "", ("C", "chain, past 30%"), ("-", ""), ("-", ""),
     "Write the handoff and run charter chain next", "`docs/gates.md` § Chain budget and hand-over (0.4.9)"),
]

# Who may change what. cols: agent, routine, answers, open, owner ("y" yes, "" no)
ACTS = [
    ("a.code", "Edit code inside the unit's perimeter", "y", "", "", "", "y", "edit, then commit on a branch", "`package/.claude/rules/charter.md:16`"),
    ("a.propose", "Write a unit; propose a decision or a change request", "y", "", "", "", "y", "charter-unit, charter-decision skills", "`package/.claude/rules/charter.md:51`"),
    ("a.upgrade", "Commit an upgrade's package files as the installer wrote them", "y", "", "", "", "y", "charter-pkg upgrade, then commit", "`package/.claude/rules/charter.md:32`"),
    ("a.check", "Close an `— owner: check` line whose probe passes on re-run", "", "y", "y", "y", "y", "the watcher reruns the probe", "`package/.claude/rules/charter.md:44`"),
    ("a.settings", "Commit an upgrade's settings change, exactly as the installer writes it", "", "y", "y", "y", "y", "charter handover --wait", "`docs/design/owner-delegate.md` § Levels"),
    ("a.ruling", "Transcribe the owner's own ruling: rule, approve, rail", "", "", "y", "y", "y", "charter handover --ask … --quote", "`package/.claude/rules/charter.md:47`"),
    ("a.road", "Edit charter/rails.md or charter/scope.md", "", "", "", "y", "y", "edit, then charter handover", "`package/.claude/rules/charter.md:44`"),
    ("a.merge", "Merge the owner's own reviewed pull request", "", "", "", "y", "y", "/reviewPR, then handover --merge N", "`package/.claude/rules/charter.md:48`"),
    ("a.structural", "Config (the level too), .charter/**, settings, CI workflow, split units, `— owner: do|decide`", "", "", "", "", "y", "the owner's line: … owner commit", "`docs/design/owner-delegate.md` § Levels"),
    ("a.run", "Run a waiting chain's acts; resume a chain", "", "", "", "", "y", "charter owner run; /resume-chain ok", "`package/.claude/rules/charter.md:37-40`"),
    ("a.commit", "Push, deploy, and every other commitment", "", "", "", "", "y", "the owner's word, in the session", "`package/.claude/rules/charter.md:57`"),
]

CHAIN_STATES = [
    ("running", "a session works; the next opens at its hand-over", "`package/.charter/chain.py`"),
    ("waiting", "a session needs the owner; every act is in owner.md", "`docs/gates.md` § Chain budget and hand-over (0.4.9)"),
    ("halted", "a session asked a question, or a review could not run", "`docs/daily-use.md` § Running units in a chain"),
    ("stalled", "two sessions in a row landed nothing", "`docs/gates.md` § Chain budget and hand-over (0.4.9)"),
    ("stopped", "the owner ran charter chain stop", "`docs/daily-use.md` § Running units in a chain"),
    ("complete", "the road is finished, on a clean tree", "`docs/daily-use.md` § Running units in a chain"),
]

LIMITS = [
    "A gate checks that evidence is cited and resolves, not that it proves the claim; the reviewer and the owner judge that (`docs/gates.md` § What a gate cannot see).",
    "A Bash command is not an Edit or a Write: the session hooks do not see a file it changes, the git hook and CI do (`docs/gates.md` § What a gate cannot see).",
    "A gate that crashes lets the change through and logs `decision=error`; `--no-verify` skips the git hook, and CI runs the checks again (`docs/method.md` § The hard gates and why a warning would not do).",
    "A merge, a deployment, a push and a purchase are actions, not files: no gate sees them, the rules file carries them (`docs/gates.md` § What a gate cannot see).",
    "The lock that holds against an agent acting as the owner is outside the repository: branch protection and code owners (`docs/gates.md` § Owner-only changes).",
]

# --------------------------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------------------------

def esc(s: str) -> str:
    return html.escape(s, quote=True)


def plain(s: str) -> str:
    """Markdown backticks out, for SVG text and tooltips."""
    return s.replace("`", "")


def tw(s: str, size: float, mono: bool = False) -> float:
    return len(s) * size * (0.6 if mono else 0.5)


def wrap(s: str, width: float, size: float, mono: bool = False) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cur and tw(t, size, mono) > width:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def text(x, y, s, cls="", size=None, anchor=None, weight=None, extra=""):
    a = []
    if cls:
        a.append(f'class="{cls}"')
    if size:
        a.append(f'font-size="{size}"')
    if anchor:
        a.append(f'text-anchor="{anchor}"')
    if weight:
        a.append(f'font-weight="{weight}"')
    return f'<text x="{x:.1f}" y="{y:.1f}" {" ".join(a)} {extra}>{esc(s)}</text>'


def lines_text(x, y, lines, lh, cls="", size=None, anchor=None):
    return "".join(text(x, y + i * lh, ln, cls, size, anchor) for i, ln in enumerate(lines))


def rpath(pts, r=10) -> str:
    """A polyline with rounded corners."""
    if len(pts) == 2:
        (x1, y1), (x2, y2) = pts
        return f"M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        l1 = max(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** .5, 1)
        l2 = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5, 1)
        rr = min(r, l1 / 2, l2 / 2)
        ax, ay = x1 - (x1 - x0) / l1 * rr, y1 - (y1 - y0) / l1 * rr
        bx, by = x1 + (x2 - x1) / l2 * rr, y1 + (y2 - y1) / l2 * rr
        d += f" L{ax:.1f},{ay:.1f} Q{x1:.1f},{y1:.1f} {bx:.1f},{by:.1f}"
    d += f" L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
    return d


STYLES = ["rule", "cite", "propose", "gate", "machine", "flow", "wait"]


def defs(prefix: str) -> str:
    m = "".join(
        f'<marker id="{prefix}-{s}" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" class="mk mk-{s}"/></marker>' for s in STYLES)
    return f"<defs>{m}</defs>"


def edge(prefix, rid, pts, style, label=None, lx=None, ly=None, anchor="middle", data=""):
    out = [f'<g class="e e-{style}" id="{rid}" {data}>',
           f'<path d="{rpath(pts)}" marker-end="url(#{prefix}-{style})"/>']
    if label:
        for i, ln in enumerate(label.split("\n")):
            out.append(text(lx, ly + i * 13, ln, "el", anchor=anchor))
    out.append("</g>")
    return "".join(out)


def tooltip(s: str) -> str:
    return f"<title>{esc(plain(s))}</title>"


def disc(x, y, r, letter, filled, hue):
    cls = f"disc d-{hue}" + (" filled" if filled else "")
    return (f'<circle cx="{x}" cy="{y}" r="{r}" class="{cls}"/>'
            f'<text x="{x}" y="{y + r * .36:.1f}" text-anchor="middle" class="dl{" filled" if filled else ""} t-{hue}" font-size="{r * 1.05:.0f}">{letter}</text>')


def actor_discs(x, y, actors, r=11):
    out, cx = [], x
    for a in actors:
        filled = a == "owner"
        hue = {"owner": "owner", "agent": "unit", "reviewer": "chain", "delegate": "owner", "machines": "gate", "client": "art"}[a]
        out.append(f'<g class="who" data-actor="{a}">{tooltip(ACTOR[a][1] + ": " + ACTOR[a][3])}{disc(cx, y, r, ACTOR[a][2], filled, hue)}</g>')
        cx += 2 * r + 6
    return "".join(out)


SVG_CSS = """
.cm{font-family:var(--sans)}
.cm text{fill:var(--fg)}
.cm .t-muted,.cm .sub{fill:var(--muted)}
.cm .mono{font-family:var(--mono)}
.cm .serif{font-family:var(--serif);font-weight:700}
.cm .cap{font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.cm .b{font-weight:700}
.cm .el{font-size:11.5px;fill:var(--muted);paint-order:stroke;stroke:var(--paper);stroke-width:4px;stroke-linejoin:round}
.cm .cl{fill:var(--paper);stroke-width:1.4}
.cm .cl-owner{stroke:var(--owner)}.cm .cl-art{stroke:var(--art)}.cm .cl-unit{stroke:var(--line)}.cm .cl-gate{stroke:var(--block)}
.cm .cl-rec{stroke:var(--rec)}.cm .cl-chain{stroke:var(--warn)}.cm .cl-fleet{stroke:var(--muted)}.cm .cl-pass{stroke:var(--pass)}
.cm .bg-owner{fill:var(--owner-bg)}.cm .bg-art{fill:var(--art-bg)}.cm .bg-unit{fill:var(--panel2)}.cm .bg-gate{fill:var(--block-bg)}
.cm .bg-rec{fill:var(--rec-bg)}.cm .bg-chain{fill:var(--warn-bg)}.cm .bg-fleet{fill:var(--panel2)}.cm .bg-pass{fill:var(--pass-bg)}
.cm .t-owner{fill:var(--owner)}.cm .t-art{fill:var(--art)}.cm .t-unit{fill:var(--fg)}.cm .t-gate{fill:var(--block)}
.cm .t-rec{fill:var(--rec)}.cm .t-chain{fill:var(--warn)}.cm .t-fleet{fill:var(--muted)}.cm .t-pass{fill:var(--pass)}
.cm .s-owner{stroke:var(--owner)}.cm .s-art{stroke:var(--art)}.cm .s-unit{stroke:var(--line)}.cm .s-gate{stroke:var(--block)}
.cm .s-rec{stroke:var(--rec)}.cm .s-chain{stroke:var(--warn)}.cm .s-fleet{stroke:var(--muted)}.cm .s-pass{stroke:var(--pass)}
.cm .f-owner{fill:var(--owner)}.cm .f-art{fill:var(--art)}.cm .f-unit{fill:var(--line)}.cm .f-gate{fill:var(--block)}
.cm .f-rec{fill:var(--rec)}.cm .f-chain{fill:var(--warn)}.cm .f-fleet{fill:var(--muted)}.cm .f-pass{fill:var(--pass)}
.cm .frame{fill:none;stroke:var(--line);stroke-width:1.2;stroke-dasharray:6 5}
.cm .card{fill:var(--paper);stroke:var(--line);stroke-width:1.6}
.cm .chip{fill:var(--panel2);stroke:none}
.cm .tchip{fill:var(--paper);stroke:var(--faint);stroke-width:1}
.cm .disc{stroke-width:2;fill:var(--paper)}
.cm .disc.d-owner{stroke:var(--owner)}.cm .disc.d-unit{stroke:var(--line)}.cm .disc.d-chain{stroke:var(--warn)}
.cm .disc.d-gate{stroke:var(--block)}.cm .disc.d-art{stroke:var(--art)}
.cm .disc.filled.d-owner{fill:var(--owner)}
.cm .dl{font-weight:700}.cm .dl.filled{fill:#fff}
.cm .e path{fill:none;stroke-width:1.5}
.cm .e-rule path{stroke:var(--owner);stroke-width:2.6}
.cm .e-cite path{stroke:var(--art)}
.cm .e-propose path{stroke:var(--muted);stroke-dasharray:6 4}
.cm .e-gate path{stroke:var(--block);stroke-width:1.8}
.cm .e-machine path{stroke:var(--rec);stroke-dasharray:2 3;stroke-width:1.8}
.cm .e-flow path{stroke:var(--line)}
.cm .e-wait path{stroke:var(--owner);stroke-dasharray:7 4;stroke-width:2}
.cm .mk{stroke:none}
.cm .mk-rule,.cm .mk-wait{fill:var(--owner)}.cm .mk-cite{fill:var(--art)}.cm .mk-propose{fill:var(--muted)}
.cm .mk-gate{fill:var(--block)}.cm .mk-machine{fill:var(--rec)}.cm .mk-flow{fill:var(--line)}
.cm .glyph-R{fill:var(--block)}.cm .glyph-C{fill:var(--block)}.cm .glyph-W{fill:none;stroke:var(--warn);stroke-width:1.8;stroke-dasharray:3 2}
.cm .glyph-dot{fill:var(--faint)}
.cm .gauge{fill:var(--panel2);stroke:var(--line);stroke-width:1}
.cm .gauge-fill{fill:var(--warn)}
.cm .yes{fill:var(--owner-bg);stroke:var(--owner);stroke-width:1.2}
.cm .yes-agent{fill:var(--panel2);stroke:var(--line);stroke-width:1.2}
.cm .grid{stroke:var(--faint);stroke-width:1}
.cm .n,.cm .tile,.cm .gr,.cm .ar{cursor:pointer}
"""

TOKENS_LIGHT = ("--paper:#ffffff;--page:#e9e6de;--fg:#1c1c1e;--muted:#5d6166;--line:#3c3c40;--faint:#dcd9cf;--panel2:#f2f0ea;"
                "--block:#4338ca;--block-bg:#e3e7ff;--warn:#a85d00;--warn-bg:#fdf0cf;--pass:#157a3c;--pass-bg:#ddf6e5;"
                "--owner:#0d7068;--owner-bg:#d6f5f0;--art:#244b77;--art-bg:#edf2f8;--rec:#5b4a9e;--rec-bg:#eeeaf8;--limit:#d42a2a;")
TOKENS_DARK = ("--paper:#17191d;--page:#0f1013;--fg:#e8e6e1;--muted:#a0a4ab;--line:#8a8d93;--faint:#34373d;--panel2:#23262c;"
               "--block:#9aa1ff;--block-bg:#232650;--warn:#f0a640;--warn-bg:#3a2b10;--pass:#57d488;--pass-bg:#12301f;"
               "--owner:#43c9ba;--owner-bg:#0f2f2c;--art:#94b8e4;--art-bg:#1a2432;--rec:#b7a8ee;--rec-bg:#241f37;")
FONTS = ('--serif:"Charter","Bitstream Charter","Charis SIL",Georgia,serif;'
         '--sans:"Liberation Sans Narrow","Arial Narrow","Roboto Condensed","Helvetica Neue",Arial,sans-serif;'
         '--mono:"Liberation Mono","DejaVu Sans Mono",Menlo,Consolas,monospace;')


def svg_doc(view: str, w: int, h: int, title: str, desc: str, body: str, standalone: bool, crop: int = 0) -> str:
    style = ""
    if standalone:
        style = ("<style>svg.cm{" + TOKENS_LIGHT + FONTS + "}"
                 "@media (prefers-color-scheme:dark){svg.cm{" + TOKENS_DARK + "}}"
                 "svg.cm .page{fill:var(--page)}" + SVG_CSS + "</style>")
    y0 = 0 if standalone else crop
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" class="cm map-{view}" viewBox="0 {y0} {w} {h - y0}" role="img" '
            f'aria-labelledby="{view}-title {view}-desc" data-view="{view}">'
            f'<title id="{view}-title">{esc(title)}</title><desc id="{view}-desc">{esc(desc)}</desc>{style}')
    bg = f'<rect class="page" x="0" y="0" width="{w}" height="{h}" fill="var(--paper)"/>' if standalone else ""
    return head + bg + defs(view) + body + "</svg>"


# ---- the functional map ------------------------------------------------------------------

def cap_tile(c, x, y, w, h, chips_cols=1, text_w=None):
    hue = c["hue"]
    out = [f'<g class="tile" id="{c["id"]}" data-id="{c["id"]}" tabindex="0" role="button" aria-label="{esc(c["title"])}">',
           tooltip(c["title"] + ". " + c["promise"]),
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" class="cl cl-{hue} bg-{hue}" stroke-width="1.6"/>',
           f'<rect x="{x}" y="{y}" width="8" height="{h}" rx="4" class="f-{hue}"/>',
           f'<circle cx="{x + 34}" cy="{y + 30}" r="15" class="f-{hue}"/>',
           text(x + 34, y + 36, str(c["n"]), "dl filled", 16, "middle")]
    tx = x + 58
    tw_ = (text_w or w) - 70
    tl = wrap(c["title"], tw_, 19)
    out.append(lines_text(tx, y + 37, tl, 22, f"serif t-{hue}", 19))
    yy = y + 37 + 22 * (len(tl) - 1) + 26
    pl = wrap(c["promise"], (text_w or w) - 44, 13.5)
    out.append(lines_text(x + 22, yy, pl, 17.5, "", 13.5))
    yy += 17.5 * len(pl) + 8
    # entry points as chips
    if text_w:
        cx0, cy0, cw = x + text_w + 10, y + 20, (w - text_w - 30) / chips_cols
    else:
        cx0, cy0, cw = x + 22, yy, (w - 44) / chips_cols
    for i, (cmd, _what, _src) in enumerate(c["entry"]):
        col, row = i % chips_cols, i // chips_cols
        ex, ey = cx0 + col * cw, cy0 + row * 27
        label = cmd if tw(cmd, 12, True) < cw - 16 else cmd[: int((cw - 22) / 7.2)] + "…"
        out.append(f'<rect x="{ex:.1f}" y="{ey:.1f}" width="{cw - 8:.1f}" height="22" rx="5" class="tchip"/>'
                   + text(ex + 8, ey + 15.5, label, "mono", 12))
    out.append(actor_discs(x + w - 22 - (len(c["actors"]) - 1) * 28, y + h - 22, c["actors"]))
    out.append("</g>")
    return "".join(out)


def functional_svg(standalone: bool) -> str:
    W, H = 1400, 880
    P = "functional"
    b = []
    # the charter repository, outside any project
    b.append('<g class="tile" id="cap.fleet" data-id="cap.fleet" tabindex="0" role="button" aria-label="Install, upgrade and oversee projects">')
    c = CAP["cap.fleet"]
    b.append(tooltip(c["title"] + ". " + c["promise"]))
    b.append('<rect x="20" y="20" width="250" height="840" rx="12" class="cl cl-fleet bg-fleet" stroke-width="1.6"/>')
    b.append('<rect x="20" y="20" width="8" height="840" rx="4" class="f-fleet"/>')
    b.append('<circle cx="54" cy="50" r="15" class="f-fleet"/>' + text(54, 56, "7", "dl filled", 16, "middle"))
    b.append(lines_text(78, 50, ["Install, upgrade", "and oversee projects"], 21, "serif t-fleet", 17))
    b.append(lines_text(40, 106, wrap(c["promise"], 205, 13), 17, "", 13))
    # the repository and its three parts
    b.append('<rect x="40" y="186" width="210" height="150" rx="8" class="card"/>')
    b.append(text(54, 208, "this repository: charter", "b", 13))
    for i, (p, d) in enumerate([("package/", "copied into each project"), ("machine/", "~/.claude, once per user"), ("bin/charter-pkg", "the installer")]):
        b.append(text(54, 234 + i * 34, p, "mono", 12.5) + text(54, 249 + i * 34, d, "sub", 11.5))
    b.append(edge(P, "fl-1", [(145, 336), (145, 386)], "flow", "install · upgrade", 152, 366, "start"))
    for i, (cmd, _w, _s) in enumerate(c["entry"]):
        lab = cmd.replace("charter-pkg ", "")
        ey = 400 + i * 27
        b.append(f'<rect x="40" y="{ey}" width="210" height="22" rx="5" class="tchip"/>' + text(48, ey + 15.5, (lab if len(lab) < 29 else lab[:27] + "…"), "mono", 12))
    b.append(lines_text(40, 556, ["The machine layer, once per user:", "a SessionStart hook says when a", "project is behind; the CharterAdmin", "skill runs fleet status, upgrades", "and the Migrate workflow."], 16, "sub", 12))
    b.append(text(40, 662, "THE FLEET, UNDER ONE DIRECTORY", "cap t-muted", 11))
    for k in range(3):
        b.append(f'<rect x="{40 + k * 12}" y="{674 + k * 12}" width="176" height="74" rx="7" class="card"/>')
    b.append(text(76, 718, "a project", "b", 13) + text(76, 736, ".charter/manifest.json", "mono", 11)
             + text(76, 751, f"charter/VERSION {VERSION}", "mono", 11))
    b.append(text(40, 790, "each owned file hashed; CI refuses", "sub", 11.5) + text(40, 805, "an engine file that differs", "sub", 11.5))
    b.append(actor_discs(212, 832, ["owner", "agent"], 11))
    b.append("</g>")
    b.append(edge(P, "fl-2", [(270, 450), (300, 450)], "flow"))

    # the project frame
    b.append('<rect x="300" y="20" width="1080" height="840" rx="14" class="frame"/>')
    b.append(text(318, 44, "ONE PROJECT UNDER CHARTER", "cap t-muted", 12))
    b.append(text(1362, 44, "track: client (signed devis) · prototype", "sub", 12, "end"))

    b.append(cap_tile(CAP["cap.owner"], 320, 60, 1040, 160, chips_cols=2, text_w=430))
    b.append(cap_tile(CAP["cap.agree"], 320, 290, 300, 300))
    b.append(cap_tile(CAP["cap.unit"], 690, 290, 300, 300))
    b.append(cap_tile(CAP["cap.gate"], 1060, 290, 300, 300))
    b.append(cap_tile(CAP["cap.chain"], 320, 650, 470, 190, chips_cols=1, text_w=230))
    b.append(cap_tile(CAP["cap.report"], 850, 650, 510, 190, chips_cols=1, text_w=240))

    # flows between capabilities
    b.append(edge(P, "fl-3", [(620, 420), (690, 420)], "cite", "units\ncite", 655, 400))
    b.append(edge(P, "fl-4", [(990, 420), (1060, 420)], "gate", "each\nchange", 1025, 400))
    b.append(edge(P, "fl-5", [(470, 220), (470, 290)], "rule", "signs scope · orders rails · rules", 478, 260, "start"))
    b.append(edge(P, "fl-6", [(1210, 220), (1210, 290)], "rule", "holds the keys", 1218, 260, "start"))
    b.append(edge(P, "fl-7", [(840, 290), (840, 220)], "propose", "proposes · hands over", 848, 260, "start"))
    b.append(edge(P, "fl-8", [(760, 650), (760, 590)], "flow", "runs units", 768, 626, "start"))
    b.append(edge(P, "fl-9", [(930, 590), (930, 650)], "machine", "evidence · cost", 938, 626, "start"))
    b.append(edge(P, "fl-10", [(1210, 590), (1210, 650)], "machine", "logs findings", 1218, 626, "start"))
    b.append(edge(P, "fl-11", [(330, 745), (310, 745), (310, 140), (320, 140)], "wait", "waits on", 314, 610, "start"))
    body = "".join(b)
    return svg_doc("functional", W, H, f"What charter provides (charter {VERSION})",
                   "Seven capabilities: one outside any project (install and oversee) and six inside a project: keep the owner in charge, "
                   "write down what is agreed, work in units, check every change, run the road unattended, say what is true and what it cost.",
                   body, standalone)


# ---- the conceptual map -------------------------------------------------------------------

def cnode(cid, x, y, w=220, h=48):
    _id, name, _cl, hue, sub, definition, _src = CON[cid]
    return (f'<g class="n" id="{cid}" data-id="{cid}" tabindex="0" role="button" aria-label="{esc(name)}">{tooltip(name + ": " + definition)}'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" class="cl cl-{hue}" stroke-width="1.6"/>'
            f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" class="f-{hue}"/>'
            + text(x + 16, y + 20, name, f"b t-{hue}", 15)
            + text(x + 16, y + 38, sub, "mono sub", 11.5) + "</g>")


def cperson(cid, x, y, filled):
    _id, name, _cl, hue, sub, definition, _src = CON[cid]
    letter = {"c.owner": "O", "c.agent": "A", "c.delegate": "D", "c.reviewer": "R"}[cid]
    return (f'<g class="n" id="{cid}" data-id="{cid}" tabindex="0" role="button" aria-label="{esc(name)}">{tooltip(name + ": " + definition)}'
            + disc(x, y, 19, letter, filled, hue)
            + text(x + 28, y - 2, name, f"b t-{hue}", 15) + text(x + 28, y + 15, sub, "sub", 11.5) + "</g>")


def concepts_svg(standalone: bool) -> str:
    W, H = 1400, 1000
    P = "concepts"
    b = []
    # clusters
    b.append('<rect x="14" y="10" width="1372" height="108" rx="12" class="cl cl-owner" fill="none" stroke-dasharray="2 4"/>')
    b.append(text(30, 30, "WHO ACTS", "cap t-muted", 11))
    b.append('<rect x="20" y="160" width="305" height="560" rx="12" class="cl cl-art bg-art"/>')
    b.append(text(36, 182, "THE WRITTEN CHARTER", "cap t-art", 11))
    b.append('<rect x="1045" y="160" width="335" height="560" rx="12" class="cl cl-gate bg-gate"/>')
    b.append(text(1061, 182, "THE GATES", "cap t-gate", 11))
    b.append('<rect x="20" y="752" width="355" height="236" rx="12" class="cl cl-chain bg-chain"/>')
    b.append(text(36, 774, "RUNNING THE ROAD", "cap t-chain", 11))
    b.append('<rect x="425" y="752" width="955" height="236" rx="12" class="cl cl-rec bg-rec"/>')
    b.append(text(441, 774, "WHAT IS TRUE, AND WHAT IT COST", "cap t-rec", 11))

    # the unit, drawn as the file it is
    b.append('<g class="n" id="c.unit" data-id="c.unit" tabindex="0" role="button" aria-label="Unit">' + tooltip("Unit: " + CON["c.unit"][5]))
    b.append('<path d="M400,160 H970 L1000,190 V720 H400 Z" class="card"/><path d="M970,160 V190 H1000" class="card" fill="none"/>')
    b.append(text(420, 188, "Unit", "serif", 20) + text(470, 188, ".taskets/<id>.md · one deliverable, one owning session", "mono sub", 12))
    fm = [("scope: S2", "cites a scope item (client track)"), ("rail: r3", "names an item of the road"),
          ("decisions: [pick-db]", "relies on these decisions"), (None, None), ("status: next → done", "")]
    for i, (k, d) in enumerate(fm):
        yy = 222 + i * 25
        if k:
            b.append(text(420, yy, k, "mono", 13) + text(640, yy, d, "sub", 12))
    b.append("</g>")
    # perimeter row as its own concept
    b.append('<g class="n" id="c.perimeter" data-id="c.perimeter" tabindex="0" role="button" aria-label="Perimeter">' + tooltip("Perimeter: " + CON["c.perimeter"][5])
             + '<rect x="412" y="282" width="566" height="24" rx="5" class="chip"/>'
             + text(420, 299, "perimeter: [app/**]", "mono b", 13) + text(640, 299, "the paths it may touch; outside needs a note", "sub", 12) + "</g>")
    # sections
    def section(cid, x, y, w, h, head, body_lines):
        _i, name, _c, hue, _s, definition, _src = CON[cid]
        out = (f'<g class="n" id="{cid}" data-id="{cid}" tabindex="0" role="button" aria-label="{esc(name)}">{tooltip(name + ": " + definition)}'
               f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" class="cl cl-{hue}" stroke-width="1.6"/>'
               + text(x + 12, y + 20, head, f"mono b t-{hue}", 13))
        for i, ln in enumerate(body_lines):
            out += text(x + 12, y + 40 + i * 17, ln, "mono", 11.5)
        return out + "</g>"
    b.append(section("c.acceptance", 420, 360, 280, 82, "## Acceptance", ["- [ ] AC-1: … — probe: `pytest …`", "- [ ] AC-2: (guard) …", "- [ ] AC-3: … — owner: check"]))
    b.append(section("c.evidence", 420, 470, 280, 74, "## Evidence", ["- 3f2a9c1 adds the endpoint", "- `$ pytest …` → exit 0"]))
    b.append(section("c.log", 420, 600, 280, 92, "## Log", ["- 09-11 14:20 started; probe fails", "- 09-11 15:02 AC-1 closed at 3f2a9c1", "a new session resumes from here"]))
    b.append(cnode("c.probe", 750, 370, 225, 52))
    # accepted, a stamp
    b.append('<g class="n" id="c.accepted" data-id="c.accepted" tabindex="0" role="button" aria-label="Accepted">' + tooltip("Accepted: " + CON["c.accepted"][5])
             + '<rect x="750" y="478" width="225" height="96" rx="10" class="cl cl-pass bg-pass" stroke-width="2.4"/>'
             + '<rect x="755" y="483" width="215" height="86" rx="7" fill="none" class="s-pass" stroke-width="1"/>'
             + text(862, 507, "status: done = accepted", "b t-pass", 14.5, "middle")
             + text(862, 529, "every box checked", "", 12.5, "middle")
             + text(862, 547, "evidence that resolves", "", 12.5, "middle")
             + text(862, 563, "else refused, in session and at commit", "sub", 11, "middle") + "</g>")

    # who
    b.append(cperson("c.owner", 120, 66, True))
    b.append(cperson("c.agent", 640, 66, False))
    b.append(cperson("c.delegate", 1150, 66, False))
    # the written charter
    b.append(cnode("c.track", 100, 200, 205))
    b.append(cnode("c.scope", 100, 290, 205))
    b.append(cnode("c.change", 100, 380, 205))
    b.append(cnode("c.rails", 100, 480, 205))
    b.append(cnode("c.decision", 100, 600, 205))
    # gates
    b.append(cnode("c.keys", 1110, 200, 250))
    b.append('<g class="n" id="c.gate" data-id="c.gate" tabindex="0" role="button" aria-label="Gate">' + tooltip("Gate: " + CON["c.gate"][5])
             + '<rect x="1070" y="300" width="290" height="250" rx="10" class="cl cl-gate" stroke-width="1.8"/>'
             + '<rect x="1070" y="300" width="6" height="250" rx="3" class="f-gate"/>'
             + text(1088, 322, "Gate", "b t-gate", 16) + text(1130, 322, "refuses (hard) or warns", "sub", 12)
             + text(1088, 342, "scope · rails · size · done ·", "mono", 11) + text(1088, 356, "decisions · perimeter · memory ·", "mono", 11)
             + text(1088, 370, "anchors · owner-only · config", "mono", 11) + "</g>")
    b.append('<g class="n" id="c.line" data-id="c.line" tabindex="0" role="button" aria-label="Three lines">' + tooltip("Three lines: " + CON["c.line"][5])
             + text(1088, 388, "runs at three lines", "sub", 12))
    for i, (t1, t2) in enumerate([("session", "hooks"), ("commit", "pre-commit"), ("merge", "CI, clean clone")]):
        xx = 1088 + i * 88
        b.append(f'<rect x="{xx}" y="396" width="82" height="44" rx="6" class="cl cl-gate bg-gate" stroke-width="{1 + i * .8:.1f}"/>'
                 + text(xx + 41, 414, t1, "b", 12.5, "middle") + text(xx + 41, 430, t2, "sub", 10.5, "middle"))
    b.append("</g>")
    b.append('<g class="n" id="c.override" data-id="c.override" tabindex="0" role="button" aria-label="Override">' + tooltip("Override: " + CON["c.override"][5])
             + '<rect x="1088" y="456" width="256" height="80" rx="6" fill="none" class="s-gate" stroke-dasharray="4 3" stroke-width="1.4"/>'
             + text(1100, 476, "Override", "b t-gate", 14) + text(1160, 476, "named in every refusal", "sub", 11.5)
             + text(1100, 494, "write the change request · move", "", 11.5) + text(1100, 510, "the code out · add the evidence ·", "", 11.5)
             + text(1100, 526, "propose a successor decision", "", 11.5) + "</g>")
    b.append(cnode("c.gatelog", 1110, 640, 250))
    # chain
    b.append(cnode("c.chain", 110, 800, 240, 52))
    b.append(cperson("c.reviewer", 130, 930, False))
    # records
    b.append(cnode("c.anchor", 455, 905, 250))
    b.append(cnode("c.synth", 760, 905, 230))
    b.append(cnode("c.ledger", 1110, 905, 230))

    # edges. (from, to) -> points, label, label position
    R = {(r[0], r[2]): r for r in RELATIONS}
    def E(f, t, pts, lab=None, lx=None, ly=None, anchor="middle", label=True):
        rel = R[(f, t)]
        i = RELATIONS.index(rel)
        verb = rel[1] if lab is None else lab
        return edge(P, f"r{i}", pts, rel[3], verb if label else None, lx, ly, anchor, f'data-from="{f}" data-to="{t}"')
    # the owner: a spine down the left
    b.append(E("c.owner", "c.scope", [(101, 70), (50, 70), (50, 314), (100, 314)], "signs", 56, 308, "start"))
    b.append(E("c.owner", "c.change", [(50, 300), (50, 404), (100, 404)], "approves", 56, 398, "start"))
    b.append(E("c.owner", "c.rails", [(50, 390), (50, 504), (100, 504)], "orders", 56, 498, "start"))
    b.append(E("c.owner", "c.decision", [(50, 490), (50, 624), (100, 624)], "rules on", 56, 618, "start"))
    b.append(E("c.owner", "c.keys", [(120, 85), (120, 136), (1190, 136), (1190, 200)], "holds the keys", 900, 132))
    b.append(E("c.owner", "c.delegate", [(120, 47), (120, 28), (1150, 28), (1150, 46)], "sets the level of", 640, 24))
    b.append(E("c.delegate", "c.keys", [(1150, 85), (1150, 116), (1290, 116), (1290, 200)], "commits some owner acts, by level", 1144, 112, "end"))
    # the agent
    b.append(E("c.agent", "c.unit", [(640, 86), (640, 160)], "works, one at a time", 648, 112, "start"))
    b.append(E("c.agent", "c.change", [(621, 66), (340, 66), (340, 396), (305, 396)], "proposes", 500, 62))
    b.append(E("c.agent", "c.decision", [(340, 380), (340, 616), (305, 616)], label=False))
    # the track
    b.append(E("c.track", "c.scope", [(220, 248), (220, 290)], "client track needs", 228, 274, "start"))
    b.append(E("c.change", "c.scope", [(140, 380), (140, 338)], "unlocks paths outside", 148, 368, "start"))
    # the unit cites
    b.append(E("c.unit", "c.scope", [(412, 217), (385, 217), (385, 306), (305, 306)], label=False))
    b.append(E("c.unit", "c.rails", [(412, 242), (370, 242), (370, 500), (305, 500)], label=False))
    b.append(E("c.unit", "c.decision", [(412, 267), (355, 267), (355, 632), (305, 632)], label=False))
    b.append(E("c.acceptance", "c.probe", [(700, 396), (750, 396)], "answered by", 725, 390))
    b.append(E("c.probe", "c.evidence", [(800, 422), (800, 455), (720, 455), (720, 500), (700, 500)], "prints the $ lines", 806, 446, "start"))
    b.append(E("c.acceptance", "c.accepted", [(700, 430), (730, 430), (730, 505), (750, 505)], label=False))
    b.append(E("c.evidence", "c.accepted", [(700, 530), (750, 530)], label=False))
    b.append(E("c.evidence", "c.anchor", [(420, 520), (410, 520), (410, 929), (455, 929)], "points at", 404, 880, "end"))
    # gates
    b.append(E("c.keys", "c.gate", [(1235, 248), (1235, 300)], "define", 1243, 280, "start"))
    b.append(E("c.gate", "c.gatelog", [(1150, 550), (1150, 640)], "logs every finding", 1144, 600, "end"))
    b.append(E("c.gatelog", "c.gate", [(1300, 640), (1300, 550)], "promotes a\nwarning to", 1306, 590, "start"))
    b.append(E("c.gate", "c.accepted", [(1070, 520), (1020, 520), (1020, 560), (975, 560)], "refuses done\nwithout", 1022, 590, "middle"))
    # records
    b.append(E("c.anchor", "c.synth", [(705, 929), (760, 929)], "checks", 732, 923))
    b.append(E("c.synth", "c.accepted", [(860, 905), (860, 574)], "counts", 866, 800, "start"))
    b.append(E("c.synth", "c.ledger", [(990, 929), (1110, 929)], "reads cost from", 1050, 923))
    b.append(E("c.ledger", "c.unit", [(1225, 905), (1225, 736), (1010, 736), (1010, 700), (1000, 700)], "charges each session to the unit", 1110, 732))
    # chain
    b.append(E("c.chain", "c.unit", [(350, 812), (390, 812), (390, 700), (400, 700)], "runs units", 394, 760, "start"))
    b.append(E("c.chain", "c.log", [(350, 840), (560, 840), (560, 692)], "resumes from", 566, 820, "start"))
    b.append(E("c.chain", "c.rails", [(130, 800), (130, 740), (80, 740), (80, 520), (100, 520)], "a group per item", 88, 690, "start"))
    b.append(E("c.chain", "c.owner", [(110, 826), (30, 826), (30, 70), (99, 70)], "waits on the owner", 36, 745, "start"))
    b.append(E("c.reviewer", "c.chain", [(130, 909), (130, 852)], "reviews each group", 138, 886, "start"))
    body = "".join(b)
    return svg_doc("concepts", W, H, f"How charter's ideas fit (charter {VERSION})",
                   "Twenty-five concepts in six clusters: who acts, the written charter, the unit of work, the gates, running the road, "
                   "and what is true. Lines carry a verb; their style says who acts: thick teal the owner, navy a citation, dashed grey a proposal, "
                   "indigo a gate, dotted violet a machine record.", body, standalone)


# ---- gates x lines -------------------------------------------------------------------------

def glyph(kind, x, y):
    if kind == "R":
        return f'<path d="M{x},{y - 12} L{x + 10},{y - 8} V{y + 1} C{x + 10},{y + 7} {x + 5},{y + 11} {x},{y + 13} C{x - 5},{y + 11} {x - 10},{y + 7} {x - 10},{y + 1} V{y - 8} Z" class="glyph-R"/>'
    if kind == "C":
        return (f'<path d="M{x},{y - 12} L{x + 10},{y - 8} V{y + 1} C{x + 10},{y + 7} {x + 5},{y + 11} {x},{y + 13} C{x - 5},{y + 11} {x - 10},{y + 7} {x - 10},{y + 1} V{y - 8} Z" fill="none" class="s-gate" stroke-width="1.6"/>'
                f'<path d="M{x},{y - 12} L{x - 10},{y - 8} V{y + 1} C{x - 10},{y + 7} {x - 5},{y + 11} {x},{y + 13} Z" class="glyph-C"/>')
    if kind == "W":
        return f'<path d="M{x},{y - 11} L{x + 11},{y} L{x},{y + 11} L{x - 11},{y} Z" class="glyph-W"/>'
    return f'<circle cx="{x}" cy="{y}" r="3.5" class="glyph-dot"/>'


def gates_svg(standalone: bool) -> str:
    W = 1400
    top, rh = 150, 44
    H = top + rh * len(GATES) + 92
    cols = [(470, "In the session", "Claude Code hooks, before the edit lands"), (640, "At commit", "git pre-commit, whoever commits"),
            (810, "At merge", "CI, from a clean clone")]
    b = []
    b.append(text(24, 40, "Every gate, at each line a change crosses", "serif", 22))
    b.append(text(24, 64, f"charter {VERSION} · the same engine (package/.charter/checks.py) runs at all three; each line catches what the one before can miss", "sub", 13))
    # the path of a change
    b.append(edge("gates", "gt-path", [(380, 100), (930, 100)], "flow"))
    b.append(text(372, 104, "edit", "sub", 12, "end") + text(940, 104, "main (the owner merges)", "sub", 12))
    for x, t1, t2 in cols:
        b.append(f'<rect x="{x - 72}" y="84" width="144" height="34" rx="8" class="cl cl-gate bg-gate"/>' + text(x, 100, t1, "b t-gate", 13, "middle")
                 + text(x, 113, t2.split(",")[0], "sub", 10.5, "middle"))
    b.append(text(24, 140, "GATE", "cap t-muted", 11) + text(990, 140, "THE WAY PAST A REFUSAL (THE OVERRIDE)", "cap t-muted", 11))
    for i, (gid, name, rule, s, c, ci, override, _src) in enumerate(GATES):
        y = top + i * rh
        b.append(f'<g class="gr" id="{gid}" data-id="{gid}" tabindex="0" role="button" aria-label="{esc(name)}">{tooltip(name + ": " + override)}')
        b.append(f'<rect x="16" y="{y}" width="{W - 32}" height="{rh}" class="{"chip" if i % 2 == 0 else "page"}" fill="{"" if i % 2 == 0 else "none"}"/>')
        b.append(text(28, y + 27, name, "b", 15) + (text(230, y + 27, rule, "mono sub", 11.5) if rule else ""))
        for (x, _a, _b), (kind, note) in zip(cols, (s, c, ci)):
            gy = y + (17 if note else 22)
            b.append(glyph(kind, x, gy))
            if note:
                b.append(text(x, y + 39, note, "mono sub", 10.5, "middle"))
        for k, ln in enumerate(wrap(plain(override), 380, 13)[:2]):
            b.append(text(990, y + 19 + k * 16 + (8 if len(wrap(plain(override), 380, 13)) == 1 else 0), ln, "", 13))
        b.append("</g>")
    ly = top + rh * len(GATES) + 40
    for k, (kind, lab) in enumerate([("R", "refuses, naming the override"), ("C", "refuses under the condition named (a track, an opt-in, a chain session)"),
                                     ("W", "warns, and logs to the gate log"), ("-", "not checked at this line")]):
        x = 40 + [0, 260, 720, 990][k]
        b.append(glyph(kind, x, ly) + text(x + 20, ly + 5, lab, "", 13))
    b.append(text(24, ly + 38, "Every gate fails open on its own errors and logs them; a config the gates cannot read is refused instead. "
                               "Sources: docs/gates.md § The gates, § Git hook, § CI, § Config.", "sub", 12))
    return svg_doc("gates", W, H, f"Every gate at each line (charter {VERSION})",
                   "A matrix of thirteen gates against the three lines a change crosses: the session, the commit and the merge, "
                   "with the override that gets past each refusal.", "".join(b), standalone, 74)


# ---- who may change what ---------------------------------------------------------------------

def authority_svg(standalone: bool) -> str:
    W = 1400
    top, rh = 268, 40
    H = top + rh * len(ACTS) + 70
    colx = [570, 690, 780, 870, 990]
    b = []
    b.append(text(24, 40, "Who may change what", "serif", 22))
    b.append(text(24, 64, "An agent proposes and hands over; the owner rules. Between them, the delegate takes what the owner's level allows, never more.", "sub", 13))
    # the hand-over path
    steps = [(24, 250, "The agent stages it", ["and runs charter handover,", "which records what is staged"], "unit", False),
             (314, 260, "The delegate, if the level allows", ["rules and a model judge it,", "then it commits as the owner's delegate"], "owner", False),
             (614, 380, "Otherwise the owner's one line", ["CHARTER_OWNER=1 python3 <root>/.charter/bin/", "charter owner commit   (after ! or in a terminal)"], "owner", True),
             (1034, 346, "Pre-commit and CI still judge it", ["the switch lifts the owner-only check,", "and nothing else"], "gate", False)]
    for x, w, t1, t2, hue, mono in steps:
        b.append(f'<rect x="{x}" y="86" width="{w}" height="66" rx="9" class="cl cl-{hue} bg-{hue}"/>' + text(x + 12, 107, t1, f"b t-{hue}", 13.5)
                 + "".join(text(x + 12, 125 + k * 15, ln, "mono" if mono else "sub", 11 if mono else 12) for k, ln in enumerate(t2)))
    b.append(edge("authority", "au-1", [(274, 119), (314, 119)], "propose") + edge("authority", "au-2", [(574, 119), (614, 119)], "wait", "or", 594, 112)
             + edge("authority", "au-3", [(994, 119), (1034, 119)], "gate"))
    # the stair of levels
    b.append(text(24, 186, "ACT", "cap t-muted", 11))
    heads = [("Agent", "", "unit"), ("routine", "delegate", "owner"), ("answers", "delegate", "owner"), ("open", "delegate", "owner"), ("Owner", "", "owner")]
    for k, (x, (t1, t2, hue)) in enumerate(zip(colx, heads)):
        if t2:
            sh = (k - 1) * 18
            b.append(f'<rect x="{x - 42}" y="{224 - sh}" width="84" height="{30 + sh}" rx="4" class="bg-owner cl cl-owner" stroke-width="1"/>')
        b.append(text(x, 246, t1, f"b t-{hue}", 14, "middle"))
    b.append(text(780, 172, "the owner's delegate, by level (strict: none)", "sub", 12, "middle"))
    b.append(f'<path d="M648,178 H912" class="s-owner" stroke-width="1"/>')
    b.append(text(1070, 246, "HOW", "cap t-muted", 11))
    for i, (aid, label, *yes, how, src) in enumerate(ACTS):
        y = top + i * rh
        b.append(f'<g class="ar" id="{aid}" data-id="{aid}" tabindex="0" role="button" aria-label="{esc(plain(label))}">{tooltip(label)}')
        b.append(f'<rect x="16" y="{y}" width="{W - 32}" height="{rh}" class="chip" fill-opacity="{.9 if i % 2 == 0 else 0}"/>')
        al = wrap(plain(label), 470, 13.5)
        if len(al) == 1:
            b.append(text(28, y + 25, al[0], "", 13.5))
        else:
            b.append(lines_text(28, y + 17, wrap(plain(label), 490, 12.5)[:2], 14, "", 12.5))
        for k, (x, v) in enumerate(zip(colx, yes)):
            if v:
                cls = "yes-agent" if k == 0 else "yes"
                b.append(f'<rect x="{x - 38}" y="{y + 8}" width="76" height="{rh - 16}" rx="5" class="{cls}"/>')
                b.append(text(x, y + 25, "✓", "b " + ("t-unit" if k == 0 else "t-owner"), 14, "middle"))
            else:
                b.append(f'<circle cx="{x}" cy="{y + rh / 2}" r="3" class="glyph-dot"/>')
        b.append(text(1070, y + 25, how, "mono", 11.5))
        b.append("</g>")
    y = top + rh * len(ACTS) + 30
    b.append(text(24, y, "No level delegates a config, settings or .charter/ change, a — owner: do or decide line, or the level itself; "
                         "the level is read from the default branch, and from GitHub, whichever is stricter.", "sub", 12))
    b.append(text(24, y + 20, "Sources: package/.claude/rules/charter.md § What only the owner changes, § The owner's delegate; docs/design/owner-delegate.md § Levels.", "sub", 12))
    return svg_doc("authority", W, H, f"Who may change what (charter {VERSION})",
                   "Owner acts by who may take them: the agent, the owner's delegate at each level (routine, answers, open), or only the owner; "
                   "and the path an owner-only change takes from the agent to a commit.", "".join(b), standalone, 76)


# ---- the chain -------------------------------------------------------------------------------

def chain_svg(standalone: bool) -> str:
    W, H = 1400, 630
    P = "chain"
    b = []
    b.append(text(24, 40, "A chain of sessions over the road", "serif", 22))
    b.append(text(24, 64, "/charter-chain starts it; every session checks the one before; Codex reviews each group; the owner answers a wait with one command and two words.", "sub", 13))
    # group bands
    b.append(f'<rect x="150" y="96" width="560" height="196" rx="12" class="bg-art cl cl-art" stroke-dasharray="5 4"/>' + text(166, 116, "GROUP 1 = RAIL ITEM r1", "cap t-art", 11))
    b.append(f'<rect x="850" y="96" width="530" height="196" rx="12" class="bg-art cl cl-art" stroke-dasharray="5 4"/>' + text(866, 116, "GROUP 2 = RAIL ITEM r2", "cap t-art", 11))
    # start
    b.append('<rect x="20" y="150" width="112" height="84" rx="10" class="cl cl-owner bg-owner"/>' + text(76, 178, "/charter-chain", "mono b t-owner", 12, "middle")
             + text(76, 196, "unit + instruction", "sub", 11.5, "middle") + text(76, 212, "on chain/<id>", "mono sub", 10.5, "middle"))

    def session(x, label, fill, note):
        out = (f'<rect x="{x}" y="132" width="170" height="122" rx="10" class="card"/>' + text(x + 14, 154, label, "b", 15)
               + text(x + 14, 172, note, "sub", 11.5))
        # the context gauge, with the hand-over and cap lines
        out += f'<rect x="{x + 14}" y="186" width="142" height="14" rx="3" class="gauge"/>'
        out += f'<rect x="{x + 14}" y="186" width="{142 * fill:.1f}" height="14" rx="3" class="gauge-fill"/>'
        for pct, lab, anc, dx in ((.25, "25%", "end", -3), (.30, "30%", "start", 3)):
            xx = x + 14 + 142 * pct / .4
            out += f'<path d="M{xx:.1f},182 V204" class="s-{"chain" if pct == .25 else "gate"}" stroke-width="2"/>'
            out += text(xx + dx, 216, lab, "mono sub", 10, anc)
        out += text(x + 14, 236, "verify · work · log", "sub", 11.5) + text(x + 14, 250, "hand over at 25%", "sub", 11.5)
        return out
    b.append(session(180, "s01", .23 / .4, "first session"))
    b.append(session(470, "s02", .25 / .4, "verifies s01 first"))
    b.append(session(900, "s03", .2 / .4, "answers R1…Rn first"))
    b.append(session(1180, "s04", .1 / .4, "and so on"))
    b.append(edge(P, "ch-1", [(132, 192), (180, 192)], "flow"))
    b.append(edge(P, "ch-2", [(350, 192), (470, 192)], "flow", "handoff +", 410, 172) + text(410, 214, "chain next", "mono sub", 11, "middle"))
    # review diamond
    b.append(f'<path d="M780,150 L830,192 L780,234 L730,192 Z" class="cl cl-chain bg-chain" stroke-width="1.8"/>' + text(780, 189, "Codex", "b t-chain", 12, "middle") + text(780, 204, "review", "sub", 11, "middle"))
    b.append(edge(P, "ch-3", [(640, 192), (730, 192)], "flow", "group ends", 685, 182))
    b.append(edge(P, "ch-4", [(830, 192), (900, 192)], "flow", "findings", 865, 182))
    b.append(edge(P, "ch-5", [(1070, 192), (1180, 192)], "flow", "handoff +", 1125, 172) + text(1125, 214, "chain next", "mono sub", 11, "middle"))
    b.append(text(780, 252, "group cleared at a commit", "sub", 11.5, "middle") + text(780, 266, "the owner can merge up to", "sub", 11.5, "middle"))
    # what chain next does
    b.append('<rect x="850" y="306" width="530" height="80" rx="8" class="chip"/>'
             + text(864, 326, "charter chain next", "mono b", 12.5)
             + lines_text(864, 344, wrap("refuses a malformed handoff · records what the session committed · re-runs the probes "
                                         "of the units it closed · runs the gates on its change set · opens the next session", 500, 12)[:3], 16, "", 12))
    b.append(lines_text(150, 316, ["Each session reads its predecessor's handoff, verifies that", "work first, then works unit after unit. Past 30% of its window",
                                    "the hook refuses every tool but the handoff, git and charter."], 15, "sub", 12))
    # the wait
    b.append(edge(P, "ch-6", [(520, 254), (520, 380), (134, 380), (134, 426)], "wait", "a session needs the owner", 330, 374))
    wy = 426
    b.append(text(560, wy - 12, "WHEN THE ROAD NEEDS THE OWNER: SUDO, A SETTING, AN ACCOUNT, A RULING", "cap t-owner", 11))
    wsteps = [(24, 220, "Session waits", "status: wait · every act", "in owner.md, paste-ready", "chain"),
              (290, 220, "Codex reads the acts", "sends back what an agent", "could do itself", "chain"),
              (556, 250, "The owner runs them", "! python3 .charter/bin/", "charter owner run", "owner"),
              (852, 230, "The owner resumes", "/resume-chain ok", "closes the lines whose acts passed", "owner"),
              (1128, 250, "The next session", "checks the owner's acts first,", "then goes on", "unit")]
    for k, (x, w, t1, t2, t3, hue) in enumerate(wsteps):
        b.append(f'<rect x="{x}" y="{wy}" width="{w}" height="78" rx="10" class="cl cl-{hue} bg-{hue}"/>' + text(x + 12, wy + 22, t1, f"b t-{hue}", 14)
                 + text(x + 12, wy + 42, t2, "mono" if t2.startswith(("!", "/")) else "", 12) + text(x + 12, wy + 59, t3, "mono" if t3.startswith("charter") else "sub", 12))
        if k:
            px = wsteps[k - 1][0] + wsteps[k - 1][1]
            b.append(edge(P, f"ch-w{k}", [(px, wy + 39), (x, wy + 39)], "wait" if hue == "owner" or k == 4 else "flow"))
    # end states
    ey = 548
    b.append(text(24, ey, "A CHAIN IS ALWAYS IN ONE OF THESE STATES", "cap t-muted", 11))
    for k, (st, what, _src) in enumerate(CHAIN_STATES):
        x = 24 + k * 228
        b.append(f'<rect x="{x}" y="{ey + 10}" width="218" height="60" rx="8" class="{"bg-pass cl cl-pass" if st == "complete" else "chip"}"/>'
                 + text(x + 10, ey + 29, st, "mono b", 12.5) + lines_text(x + 10, ey + 46, wrap(what, 196, 11.5)[:2], 14, "sub", 11.5))
    return svg_doc("chain", W, H, f"A chain of sessions (charter {VERSION})",
                   "A continuous chain: sessions s01, s02 and on, each with a context gauge that hands over at 25% and is capped at 30%; "
                   "a Codex review at the end of each group; and the owner's side of a wait: owner.md, charter owner run, /resume-chain ok.",
                   "".join(b), standalone, 80)


VIEWS = [("functional", functional_svg), ("concepts", concepts_svg), ("gates", gates_svg), ("authority", authority_svg), ("chain", chain_svg)]

# --------------------------------------------------------------------------------------------
# The agent edition
# --------------------------------------------------------------------------------------------

def cname(cid):
    return CON[cid][1]


def markdown() -> str:
    L = []
    w = L.append
    w("# Charter maps: what charter provides, and how its ideas fit")
    w("")
    w(f"Charter {VERSION} (`package/VERSION`). The agent edition of `docs/maps.html`; the same data draws the SVGs in `docs/assets/maps/`. "
      "Generated by `docs/assets/maps/build.py`: edit the script, then run `python3 docs/assets/maps/build.py`.")
    w("")
    w("## How to read this file")
    w("")
    w("- Ids are the same in all three editions (`docs/maps.html`, `docs/assets/maps/*.svg`): `cap.*` a capability, `c.*` a concept, `g.*` a gate, `a.*` an act only some may take.")
    w("- Each row cites where it comes from, as a repository path or a `name in path`. The full references are `docs/method.md`, `docs/gates.md` and `docs/daily-use.md`.")
    w("- Section 2 answers \"what can I do with charter\"; section 3 answers \"what does this word mean and what is it tied to\". Sections 5 to 7 are the three close-ups (`docs/assets/maps/gates.svg`, `docs/assets/maps/authority.svg`, `docs/assets/maps/chain.svg`).")
    w("- Other pictures of charter: `docs/charter-map.html` (the elements on one map, drawn at 0.4.8), `docs/method-visual.html` (the method in diagrams), `docs/cheatsheet.html` (the desk sheet).")
    w("")
    w("## 1. Who acts")
    w("")
    w("| id | Who | What they do | Source |")
    w("|---|---|---|---|")
    for aid, name, _l, what, src in ACTORS:
        w(f"| `{aid}` | {name} | {what} | {src} |")
    w("")
    w("## 2. The functional map: what charter provides")
    w("")
    w("Seven capabilities. One sits outside any project (`cap.fleet`); the other six run inside each project that has the package. "
      "The picture is `docs/assets/maps/functional.svg`.")
    w("")
    w("| id | Capability | Promise | Who acts | Source |")
    w("|---|---|---|---|---|")
    for c in CAPS:
        w(f"| `{c['id']}` | {c['n']}. {c['title']} | {c['promise']} | {', '.join(ACTOR[a][1] for a in c['actors'])} | {c['sources'].split(';')[0]} |")
    w("")
    w("How they connect (`docs/assets/maps/functional.svg`): units cite what is agreed (`cap.agree` → `cap.unit`); each change a unit "
      "makes crosses the gates (`cap.unit` → `cap.gate`); the gates log every finding and the units carry the evidence that reports "
      "are computed from (→ `cap.report`); a chain runs units one after another and waits on the owner (`cap.chain`); the owner "
      "signs and rules what is agreed and holds the keys that define the gates (`cap.owner`); the fleet tooling installs all of it (`cap.fleet`) (`docs/method.md` § The method on one page).")
    w("")
    for c in CAPS:
        w(f"### `{c['id']}` {c['n']}. {c['title']}")
        w("")
        w(f"{c['promise']} {c['what']} ({c['sources']})")
        w("")
        w(f"- **Who acts:** {', '.join('`' + a + '`' for a in c['actors'])} (section 1, `docs/maps.md`).")
        w("- **Entry points:**")
        for cmd, what, src in c["entry"]:
            w(f"  - `{cmd}`: {what} ({src})")
        w(f"- **Files it reads or writes in a project:** {', '.join('`' + f + '`' for f in c['files'])} (`docs/package.md` § What lands in a project).")
        w(f"- **Rests on the concepts:** {', '.join('`' + k + '` ' + cname(k) for k in c['concepts'])} (section 3, `docs/maps.md`).")
        w(f"- **Read more:** {', '.join('`' + m + '`' for m in c['more'])}.")
        w("")
    w("## 3. The conceptual map: how its ideas fit")
    w("")
    w("Twenty-five concepts in six clusters. The picture is `docs/assets/maps/concepts.svg`; there the unit is drawn as the file it is, "
      "with its parts inside it.")
    w("")
    w("| id | Concept | Cluster | What it is | Source |")
    w("|---|---|---|---|---|")
    for cid, name, cl, _h, _sub, definition, src in CONCEPTS:
        w(f"| `{cid}` | {name} | {CLUSTERS[cl][0]} | {definition} | {src} |")
    w("")
    w("### Relations")
    w("")
    w("Each line reads as a sentence, subject → verb → object. The style says who acts: `rule` the owner, `propose` an agent's proposal "
      "waiting on the owner, `cite` a reference written in a file, `gate` a check, `machine` a record a program writes, `flow` structure, "
      "`wait` a chain waiting on the owner (`docs/assets/maps/concepts.svg`).")
    w("")
    w("| From | Verb | To | Style | Source |")
    w("|---|---|---|---|---|")
    for f, verb, t, style, src in RELATIONS:
        w(f"| `{f}` {cname(f)} | {verb.rstrip(',')} | `{t}` {cname(t)} | {style} | {src} |")
    w("")
    w("## 4. Capabilities × concepts")
    w("")
    w("An `x` means the capability rests on the concept. The pairing is this map's reading, kept as the `concepts` list of each capability in `docs/assets/maps/build.py`.")
    w("")
    head = "| Concept | " + " | ".join(f"`{c['id'][4:]}`" for c in CAPS) + " | Defined in |"
    w(head)
    w("|---|" + "---|" * len(CAPS) + "---|")
    for cid, name, *_ in CONCEPTS:
        cells = " | ".join("x" if cid in c["concepts"] else "" for c in CAPS)
        w(f"| `{cid}` {name} | {cells} | `docs/assets/maps/build.py` |")
    w("")
    w("## 5. Every gate, at each line")
    w("")
    w("`refuses`: a hard gate, naming its override. `refuses (condition)`: refuses only under the named track, opt-in or chain session. "
      "`warns`: logged to the gate log. `-`: not checked at this line. The picture is `docs/assets/maps/gates.svg` (`docs/gates.md` § The gates).")
    w("")
    w("| id | Gate | Rule | Session | Commit | Merge (CI) | The way past a refusal | Source |")
    w("|---|---|---|---|---|---|---|---|")
    word = {"R": "refuses", "C": "refuses", "W": "warns", "-": "-"}
    for gid, name, rule, s, c, ci, override, src in GATES:
        cells = []
        for kind, note in (s, c, ci):
            v = word[kind]
            if note and kind != "-":
                v += f" ({note})"
            cells.append(v)
        w(f"| `{gid}` | {name} | {rule or '-'} | {' | '.join(cells)} | {override} | {src} |")
    w("")
    w("## 6. Who may change what")
    w("")
    w("`yes` where the actor may take the act. The delegate's columns are the owner's levels (`delegate.level` in `charter/config.json`), "
      "each adding to the one before; `strict`, the default, delegates nothing. The picture is `docs/assets/maps/authority.svg` "
      "(`docs/design/owner-delegate.md` § Levels).")
    w("")
    w("| id | Act | Agent | Delegate: routine | Delegate: answers | Delegate: open | Owner | How | Source |")
    w("|---|---|---|---|---|---|---|---|---|")
    for aid, label, *yes, how, src in ACTS:
        w(f"| `{aid}` | {label} | {' | '.join('yes' if v else '-' for v in yes)} | `{how}` | {src} |")
    w("")
    w("An owner-only change travels one way: the agent stages it and runs `charter handover`; the delegate commits it if the level "
      "allows, else the owner runs one line, `CHARTER_OWNER=1 python3 <root>/.charter/bin/charter owner commit`, after `!` in Claude Code "
      "or in a terminal; the pre-commit gate and CI still judge the commit (`docs/gates.md` § Owner-only changes).")
    w("")
    w("## 7. A chain of sessions")
    w("")
    w("The picture is `docs/assets/maps/chain.svg` (`docs/daily-use.md` § Running units in a chain; `docs/design/continuous-chain.md`).")
    w("")
    w("1. `/charter-chain <unit> <instruction>` starts a chain; `charter chain start` creates `chain/<id>` when run on main and opens session 1 (`resolve_launcher` in `package/.charter/chain.py`).")
    w("2. Each session receives `.charter/chain-rules.md` verbatim, verifies its predecessor's work, works unit after unit, and hands over at 25% of its context window; past 30% the hook refuses every tool but writing the handoff or a unit file, `git` and the charter CLI (`docs/gates.md` § Chain budget and hand-over (0.4.9)).")
    w("3. `charter chain next` refuses a malformed handoff, records what the session committed, re-runs the probes of the units it closed, runs the gates on its change set, and opens the next session (`cmd_next` in `package/.charter/chain.py`).")
    w("4. A group is the units of one rail item. When it ends, Codex reviews its commits in a worktree; the next session answers each finding as fixed or dismissed before the next group starts, and the group is cleared at a commit the owner can merge up to (`package/.charter/chain_groups.py`).")
    w("5. When the road needs the owner, the session writes every act into `owner.md` and waits; Codex reads the acts and sends back what an agent could do; the owner runs them with `charter owner run` and types `/resume-chain ok`, which closes the lines whose acts passed (`package/.charter/owner_acts.py`).")
    w("")
    w("| State | Meaning | Source |")
    w("|---|---|---|")
    for st, what, src in CHAIN_STATES:
        w(f"| `{st}` | {what} | {src} |")
    w("")
    w("## 8. Where the gates stop")
    w("")
    for l in LIMITS:
        w(f"- {l}")
    w("")
    return "\n".join(L)


# --------------------------------------------------------------------------------------------
# The page for people
# --------------------------------------------------------------------------------------------

PAGE_CSS = """
:root{%LIGHT%%FONTS%color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){%DARK%color-scheme:dark}}
:root[data-theme="dark"]{%DARK%color-scheme:dark}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--page);color:var(--fg);font:15px/1.5 var(--sans)}
.wrap{max-width:1560px;margin:0 auto;padding:22px 16px 48px}
h1,h2,h3{font-family:var(--serif);margin:0;line-height:1.15}
h1{font-size:32px;letter-spacing:-.01em}
h2{font-size:24px;margin:0 0 4px}
h3{font-size:16px;margin:0 0 6px}
p{margin:0 0 10px}
a{color:var(--art)}
code{font-family:var(--mono);font-size:.86em;background:var(--panel2);padding:0 .3em;border-radius:3px;overflow-wrap:anywhere}
.muted{color:var(--muted)}
header.top{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:12px 24px;border-bottom:2px solid var(--fg);padding-bottom:12px;margin-bottom:18px}
header.top p{margin:6px 0 0;color:var(--muted);max-width:820px}
nav.toc{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:14px;margin-top:8px}
.controls{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.controls span{font-size:13px;color:var(--muted);margin-right:2px}
button.lens,button.theme{font:600 13px var(--sans);border:1.5px solid var(--line);background:var(--paper);color:var(--fg);border-radius:16px;padding:4px 12px;cursor:pointer}
button.lens[aria-pressed="true"]{background:var(--fg);color:var(--paper)}
section.view{margin:26px 0 8px}
.lede{color:var(--muted);max-width:900px;margin-bottom:12px}
.stage{display:grid;grid-template-columns:minmax(0,1fr);gap:14px}
@media (min-width:1240px){.stage{grid-template-columns:minmax(0,1fr) 340px}}
.mapbox{background:var(--paper);border:1px solid var(--faint);border-radius:10px;padding:6px;overflow-x:auto;-webkit-overflow-scrolling:touch}
.mapbox svg{display:block;width:100%;height:auto;min-width:880px}
.hint{font-size:13px;color:var(--muted);margin:6px 4px 0}
aside.detail{background:var(--paper);border:1px solid var(--faint);border-radius:10px;padding:16px;align-self:start;position:sticky;top:12px;min-height:200px;max-height:calc(100vh - 24px);overflow:auto}
aside.detail .kind{display:inline-block;font:700 11px var(--sans);letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;border-radius:10px;background:var(--panel2);color:var(--muted);margin-bottom:8px}
aside.detail h3{font-size:21px;margin-bottom:8px}
aside.detail h4{font:700 12px var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:12px 0 5px}
aside.detail ul{margin:4px 0 10px;padding-left:18px}
aside.detail li{margin-bottom:3px}
aside.detail .src{font-size:12.5px;color:var(--muted);border-top:1px solid var(--faint);padding-top:7px;margin-top:6px}
.chips{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0 10px}
.chips button{font:600 12.5px var(--sans);border:1px solid var(--faint);background:var(--panel2);color:var(--fg);border-radius:12px;padding:2px 9px;cursor:pointer}
.chips button:hover{border-color:var(--line)}
.cmd{font:12.5px/1.45 var(--mono);background:var(--panel2);border-left:3px solid var(--fg);padding:5px 8px;margin:0 0 6px;overflow-wrap:anywhere}
.cmd span{display:block;font-family:var(--sans);font-size:12.5px;color:var(--muted)}
details.words{margin-top:12px;background:var(--paper);border:1px solid var(--faint);border-radius:10px;padding:10px 14px}
details.words summary{cursor:pointer;font-weight:700}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin-top:10px}
.card{border:1px solid var(--faint);border-left:5px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--paper)}
.card h3{font-size:15px}
.card p{font-size:14px;margin:0}
.h-owner{border-left-color:var(--owner)}.h-art{border-left-color:var(--art)}.h-unit{border-left-color:var(--line)}.h-gate{border-left-color:var(--block)}
.h-rec{border-left-color:var(--rec)}.h-chain{border-left-color:var(--warn)}.h-fleet{border-left-color:var(--muted)}.h-pass{border-left-color:var(--pass)}
.closeups{display:grid;grid-template-columns:minmax(0,1fr);gap:22px}
.closeups figure{margin:0}
.closeups figcaption{color:var(--muted);font-size:14px;margin:6px 4px 0;max-width:900px}
section.legend{margin-top:26px;background:var(--paper);border:1px solid var(--faint);border-radius:10px;padding:16px 18px 8px}
.lgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:4px 26px}
.lrow{display:grid;grid-template-columns:56px 1fr;gap:10px;align-items:center;padding:4px 0;border-bottom:1px dotted var(--faint);font-size:14px}
.lrow svg{width:56px;height:30px;display:block}
footer{margin-top:16px;font-size:12.5px;color:var(--muted)}
/* selection */
.cm.dim .n,.cm.dim .tile,.cm.dim .e{opacity:.2;transition:opacity .15s}
.cm.dim .lit{opacity:1}
.cm .lit>rect:first-of-type,.cm .lit>path:first-of-type,.cm .lit>circle:first-of-type{stroke-width:3.2}
.cm .e.lit path{stroke-width:3}
.cm .tile:focus,.cm .n:focus,.cm .gr:focus,.cm .ar:focus{outline:none}
.cm .tile:focus-visible>rect:first-of-type,.cm .n:focus-visible>rect:first-of-type{stroke:var(--fg);stroke-width:3}
.cm .gr.sel>rect:first-of-type,.cm .ar.sel>rect:first-of-type{fill:var(--block-bg);fill-opacity:1}
@media print{body{background:#fff}.controls,.hint,aside.detail{display:none}.stage{grid-template-columns:1fr}.mapbox{border:0;overflow:visible}.mapbox svg{min-width:0}section.view{break-inside:avoid}}
"""

PAGE_JS = r"""
(function(){
const D = JSON.parse(document.getElementById('data').textContent);
const byId = {};
D.caps.forEach(c => byId[c.id] = Object.assign({kind:'cap'}, c));
D.concepts.forEach(c => byId[c.id] = Object.assign({kind:'concept'}, c));
D.gates.forEach(g => byId[g.id] = Object.assign({kind:'gate'}, g));
D.acts.forEach(a => byId[a.id] = Object.assign({kind:'act'}, a));
const esc = s => String(s).replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));
const md = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');
const chip = id => byId[id] ? `<button data-go="${id}">${esc(byId[id].name || byId[id].title)}</button>` : '';
const panels = {functional: document.getElementById('panel-functional'), concepts: document.getElementById('panel-concepts')};
const svgs = {functional: document.querySelector('svg.map-functional'), concepts: document.querySelector('svg.map-concepts'),
              gates: document.querySelector('svg.map-gates'), authority: document.querySelector('svg.map-authority')};
function q(svg, id){ return svg ? svg.querySelector('[id="' + id + '"]') : null; }
function clear(){
  for (const s of Object.values(svgs)) { if (!s) continue; s.classList.remove('dim');
    s.querySelectorAll('.lit,.sel').forEach(n => n.classList.remove('lit','sel')); }
}
function lightConcepts(ids){
  const s = svgs.concepts; if (!s) return; s.classList.add('dim');
  ids.forEach(id => { const n = q(s, id); if (n) n.classList.add('lit'); });
  s.querySelectorAll('.e').forEach(e => { if (ids.includes(e.dataset.from) && ids.includes(e.dataset.to)) e.classList.add('lit'); });
}
function capPanel(c){
  return `<span class="kind">capability ${c.n}</span><h3>${esc(c.title)}</h3><p><b>${md(c.promise)}</b></p><p>${md(c.what)}</p>`
    + `<p class="muted">Who acts: ${c.actors.map(a => esc(D.actors[a])).join(', ')}</p>`
    + `<h4>Entry points</h4>` + c.entry.map(e => `<div class="cmd">${esc(e[0])}<span>${md(e[1])}</span></div>`).join('')
    + `<h4>Files</h4><ul>${c.files.map(f => `<li><code>${esc(f)}</code></li>`).join('')}</ul>`
    + `<h4>Rests on</h4><div class="chips">${c.concepts.map(chip).join('')}</div>`
    + `<div class="src">Sources: ${md(c.sources)}</div>`;
}
function conceptPanel(c){
  const rel = D.relations.filter(r => r.from === c.id || r.to === c.id);
  const caps = D.caps.filter(k => k.concepts.includes(c.id));
  return `<span class="kind">${esc(c.cluster)}</span><h3>${esc(c.name)}</h3><p><code>${esc(c.sub)}</code></p><p>${md(c.definition)}</p>`
    + (rel.length ? `<h4>Tied to</h4><ul>${rel.map(r => `<li>${r.from === c.id ? '' : chip(r.from) + ' '}<i>${esc(r.verb.replace(/,$/, ''))}</i>${r.to === c.id ? '' : ' ' + chip(r.to)}</li>`).join('')}</ul>` : '')
    + (caps.length ? `<h4>Used by</h4><div class="chips">${caps.map(k => chip(k.id)).join('')}</div>` : '')
    + `<div class="src">Source: ${md(c.source)}</div>`;
}
function gatePanel(g){
  const cell = c => c[0] === 'R' ? 'refuses' : c[0] === 'C' ? 'refuses' + (c[1] ? ' (' + esc(c[1]) + ')' : '') : c[0] === 'W' ? 'warns' : 'not checked';
  return `<span class="kind">gate${g.rule ? ' · ' + esc(g.rule) : ''}</span><h3>${esc(g.name)}</h3><ul><li>In the session: ${cell(g.cells[0])}</li><li>At commit: ${cell(g.cells[1])}</li><li>At merge: ${cell(g.cells[2])}</li></ul><p><b>The way past a refusal:</b> ${md(g.override)}</p><div class="src">Source: ${md(g.source)}</div>`;
}
function actPanel(a){
  const who = ['the agent','the delegate at routine','the delegate at answers','the delegate at open','the owner'].filter((_, k) => a.yes[k]);
  return `<span class="kind">who may</span><h3>${md(a.label)}</h3><p>${who.length ? 'Taken by ' + who.join(', ') + '.' : ''} How: <code>${esc(a.how)}</code></p><div class="src">Source: ${md(a.source)}</div>`;
}
function reveal(p){ if (matchMedia('(max-width: 1239px)').matches) p.scrollIntoView({behavior:'smooth', block:'nearest'}); }
function select(id, scroll){
  const it = byId[id]; if (!it) return;
  clear();
  if (it.kind === 'cap') {
    const s = svgs.functional; s.classList.add('dim'); const n = q(s, id); if (n) n.classList.add('lit');
    panels.functional.innerHTML = capPanel(it); lightConcepts(it.concepts);
    if (scroll) s.closest('section').scrollIntoView({behavior:'smooth'}); else reveal(panels.functional);
  } else if (it.kind === 'concept') {
    const s = svgs.concepts; s.classList.add('dim');
    const near = new Set([id]);
    D.relations.forEach(r => { if (r.from === id || r.to === id) { near.add(r.from); near.add(r.to); } });
    s.querySelectorAll('.e').forEach(e => { if (e.dataset.from === id || e.dataset.to === id) e.classList.add('lit'); });
    near.forEach(k => { const n = q(s, k); if (n) n.classList.add('lit'); });
    panels.concepts.innerHTML = conceptPanel(it);
    if (scroll) s.closest('section').scrollIntoView({behavior:'smooth'}); else reveal(panels.concepts);
  } else {
    const s = it.kind === 'gate' ? svgs.gates : svgs.authority; const n = q(s, id); if (n) n.classList.add('sel');
    const p = document.getElementById(it.kind === 'gate' ? 'note-gates' : 'note-authority'); p.innerHTML = it.kind === 'gate' ? gatePanel(it) : actPanel(it);
  }
  try { history.replaceState(null, '', '#' + id); } catch (e) {}
}
document.addEventListener('click', ev => {
  const go = ev.target.closest('[data-go]'); if (go) { select(go.dataset.go, true); return; }
  const n = ev.target.closest('svg.cm [data-id]'); if (n) { select(n.dataset.id, false); return; }
  if (ev.target.closest('svg.cm')) { clear(); }
});
document.addEventListener('keydown', ev => {
  if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.matches && ev.target.matches('svg.cm [data-id]')) { ev.preventDefault(); select(ev.target.dataset.id, false); }
  if (ev.key === 'Escape') clear();
});
// lenses: light what one actor does
document.querySelectorAll('button.lens').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('button.lens').forEach(o => o.setAttribute('aria-pressed', String(o === b)));
  clear(); const a = b.dataset.lens; if (a === 'all') return;
  const caps = D.caps.filter(c => c.actors.includes(a)).map(c => c.id);
  const s = svgs.functional; s.classList.add('dim'); caps.forEach(id => { const n = q(s, id); if (n) n.classList.add('lit'); });
  const cs = D.concepts.filter(c => c.actors.includes(a)).map(c => c.id); if (cs.length) lightConcepts(cs);
}));
const tb = document.querySelector('button.theme');
tb.addEventListener('click', () => {
  const r = document.documentElement; const dark = r.dataset.theme ? r.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  r.dataset.theme = dark ? 'light' : 'dark'; try { localStorage.setItem('charter-maps-theme', r.dataset.theme); } catch (e) {}
});
try { const t = localStorage.getItem('charter-maps-theme'); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
const h = decodeURIComponent(location.hash.slice(1)); if (h && byId[h]) select(h, false);
})();
"""

LENS_ACTORS = {  # which concepts light up under each lens
    "owner": ["c.owner", "c.scope", "c.rails", "c.decision", "c.change", "c.keys", "c.delegate"],
    "agent": ["c.agent", "c.unit", "c.perimeter", "c.acceptance", "c.probe", "c.evidence", "c.log", "c.change", "c.decision"],
    "reviewer": ["c.reviewer", "c.chain", "c.evidence"],
    "delegate": ["c.delegate", "c.keys", "c.owner"],
    "machines": ["c.gate", "c.line", "c.override", "c.gatelog", "c.keys", "c.accepted", "c.synth", "c.ledger", "c.anchor"],
}


def legend_row(svg_inner, label):
    return f'<div class="lrow"><svg class="cm" viewBox="0 0 56 30" aria-hidden="true">{svg_inner}</svg><div>{label}</div></div>'


def page(svgs: dict[str, str]) -> str:
    data = {
        "actors": {a[0]: a[1] for a in ACTORS},
        "caps": [dict(id=c["id"], n=c["n"], title=c["title"], name=c["title"], promise=c["promise"], what=c["what"], actors=c["actors"],
                      entry=c["entry"], files=c["files"], concepts=c["concepts"], sources=c["sources"]) for c in CAPS],
        "concepts": [dict(id=k[0], name=k[1], cluster=CLUSTERS[k[2]][0], sub=k[4], definition=k[5], source=k[6],
                          actors=[a for a, ids in LENS_ACTORS.items() if k[0] in ids]) for k in CONCEPTS],
        "relations": [dict(**{"from": r[0]}, verb=r[1], to=r[2], style=r[3]) for r in RELATIONS],
        "gates": [dict(id=g[0], name=g[1], rule=g[2], cells=[g[3], g[4], g[5]], override=g[6], source=g[7]) for g in GATES],
        "acts": [dict(id=a[0], label=a[1], name=plain(a[1]), yes=[bool(v) for v in a[2:7]], how=a[7], source=a[8]) for a in ACTS],
    }
    css = PAGE_CSS.replace("%LIGHT%", TOKENS_LIGHT).replace("%DARK%", TOKENS_DARK).replace("%FONTS%", FONTS) + SVG_CSS
    cards = "".join(f'<div class="card h-{c["hue"]}"><h3>{c["n"]}. {esc(c["title"])}</h3><p>{esc(c["promise"])}</p>'
                    f'<div class="chips"><button data-go="{c["id"]}">open</button></div></div>' for c in CAPS)
    concept_cards = "".join(f'<div class="card h-{k[3]}"><h3>{esc(k[1])}</h3><p>{esc(plain(k[5]))}</p>'
                            f'<div class="chips"><button data-go="{k[0]}">open</button></div></div>' for k in CONCEPTS)
    lens = "".join(f'<button class="lens" data-lens="{a}" aria-pressed="false">{n}</button>' for a, n in
                   [("owner", "Owner"), ("agent", "Agent"), ("reviewer", "Reviewer"), ("delegate", "Delegate"), ("machines", "Gates")])
    legend = "".join([
        legend_row('<rect x="4" y="4" width="48" height="22" rx="5" class="cl cl-art bg-art"/><rect x="4" y="4" width="5" height="22" rx="2" class="f-art"/>',
                   "<b>Box with a coloured edge</b>: a capability or a concept. The colour is its cluster: navy the written charter, black the unit, indigo the gates, teal the owner, violet records, amber the chain, grey the fleet."),
        legend_row('<circle cx="16" cy="15" r="11" class="disc d-owner filled"/><circle cx="42" cy="15" r="11" class="disc d-unit"/>',
                   "<b>Filled disc</b>: the owner. <b>Outlined disc</b>: an agent, a reviewer or the delegate."),
        legend_row('<g class="e e-rule"><path d="M4,15 H52"/></g>', "<b>Thick teal</b>: the owner acts (signs, rules, approves, holds)."),
        legend_row('<g class="e e-cite"><path d="M4,15 H52"/></g>', "<b>Navy</b>: a reference written in a file (a unit cites its scope item)."),
        legend_row('<g class="e e-propose"><path d="M4,15 H52"/></g>', "<b>Dashed grey</b>: a proposal that waits on the owner."),
        legend_row('<g class="e e-gate"><path d="M4,15 H52"/></g>', "<b>Indigo</b>: a gate acts."),
        legend_row('<g class="e e-machine"><path d="M4,15 H52"/></g>', "<b>Dotted violet</b>: a program writes a record."),
        legend_row('<g class="e e-wait"><path d="M4,15 H52"/></g>', "<b>Dashed teal</b>: a chain waits on the owner."),
        legend_row(glyph("R", 16, 15) + glyph("C", 42, 15), "<b>Solid shield</b>: refuses. <b>Half shield</b>: refuses under a named condition."),
        legend_row(glyph("W", 16, 15) + glyph("-", 42, 15), "<b>Dashed diamond</b>: warns and logs. <b>Dot</b>: not checked there."),
    ])
    body = f"""<div class="wrap">
<header class="top"><div>
<h1>Charter maps</h1>
<p>What charter provides, and how its ideas fit. Charter {VERSION}. The same maps as text, for an agent: <a href="maps.md">maps.md</a>.
Also: <a href="charter-map.html">the elements on one map</a> (drawn at 0.4.8), <a href="method-visual.html">the method in diagrams</a>, <a href="cheatsheet.html">the desk sheet</a>.</p>
<nav class="toc"><a href="#functional">1 · What it provides</a><a href="#concepts">2 · How its ideas fit</a><a href="#gates">3 · Every gate</a><a href="#authority">4 · Who may change what</a><a href="#chain">5 · A chain of sessions</a><a href="#legend">Legend</a></nav>
</div>
<div class="controls"><span>Light up:</span><button class="lens" data-lens="all" aria-pressed="true">Everything</button>{lens}<button class="theme" title="Light or dark">◐</button></div>
</header>

<section class="view" id="functional"><h2>1 · What charter provides</h2>
<p class="lede">Seven capabilities, in the words of the person using them. Six run inside each project that carries the package; the seventh, on the left, installs and watches them. Select one to see its commands, its files, and the ideas it rests on, lit in map 2.</p>
<div class="stage"><div><div class="mapbox">{svgs["functional"]}</div><p class="hint">Select a capability. Esc clears. On a phone, the map scrolls sideways.</p>
<details class="words"><summary>The seven capabilities, as a list</summary><div class="cards">{cards}</div></details></div>
<aside class="detail" id="panel-functional" aria-live="polite"><span class="kind">start here</span><h3>A method you can check</h3>
<p>Charter keeps what was agreed, the work and its evidence in the repository, and has machines check them at three lines. A person, the owner, makes the calls software cannot.</p>
<p class="muted">Select a capability on the map.</p></aside></div></section>

<section class="view" id="concepts"><h2>2 · How its ideas fit</h2>
<p class="lede">Twenty-five ideas in six clusters. The unit is drawn as the file it is, with its parts inside it; lines carry a verb, and their style says who acts. Select an idea to see what it is tied to.</p>
<div class="stage"><div><div class="mapbox">{svgs["concepts"]}</div><p class="hint">Select an idea, or a word in the side panel. Esc clears.</p>
<details class="words"><summary>The twenty-five ideas, as a list</summary><div class="cards">{concept_cards}</div></details></div>
<aside class="detail" id="panel-concepts" aria-live="polite"><span class="kind">read it as sentences</span><h3>Owner signs scope</h3>
<p>Every line is a sentence: <i>the owner signs the scope</i>, <i>a unit cites a scope item</i>, <i>a gate refuses done without acceptance</i>, <i>the chain waits on the owner</i>.</p>
<p class="muted">Select an idea on the map.</p></aside></div></section>

<section class="view closeups">
<figure id="gates"><h2>3 · Every gate, at each line</h2><p class="lede">A change crosses three lines on its way to main. Read across a row to see where a gate catches it; the last column is the honest way past.</p>
<div class="mapbox">{svgs["gates"]}</div><figcaption id="note-gates">Select a row for its detail.</figcaption></figure>
<figure id="authority"><h2>4 · Who may change what</h2><p class="lede">The staircase is the owner's delegate: each level the owner grants takes a few more acts off the owner's desk. The last rows stay the owner's at every level.</p>
<div class="mapbox">{svgs["authority"]}</div><figcaption id="note-authority">Select a row for its detail.</figcaption></figure>
<figure id="chain"><h2>5 · A chain of sessions</h2><p class="lede">The road worked without a person at the keyboard: fresh sessions, a context budget, a review per group, and the owner's side of a wait.</p>
<div class="mapbox">{svgs["chain"]}</div></figure>
</section>

<section class="legend" id="legend"><h2>Legend</h2><div class="lgrid">{legend}</div></section>
<footer>Generated by <code>docs/assets/maps/build.py</code> from one data source, which also writes <a href="maps.md">maps.md</a> and the SVGs in <code>docs/assets/maps/</code>. Every claim on these maps cites its source in maps.md; the references are <a href="method.md">method.md</a>, <a href="gates.md">gates.md</a> and <a href="daily-use.md">daily-use.md</a>.</footer>
</div>"""
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>Charter maps</title><meta name=\"description\" content=\"What charter {VERSION} provides, and how its ideas fit: a functional map, a conceptual map and three close-ups.\">"
            f"<style>{css}</style></head><body>{body}"
            f"<script type=\"application/json\" id=\"data\">{data_json}</script>"
            f"<script>{PAGE_JS}</script></body></html>\n")


def main() -> None:
    out = HERE
    inline = {}
    for name, fn in VIEWS:
        (out / f"{name}.svg").write_text(fn(True) + "\n")
        inline[name] = fn(False)
    (ROOT / "docs/maps.html").write_text(page(inline))
    (ROOT / "docs/maps.md").write_text(markdown())
    for p in [*(out / f"{n}.svg" for n, _ in VIEWS), ROOT / "docs/maps.html", ROOT / "docs/maps.md"]:
        print(p.relative_to(ROOT))


if __name__ == "__main__":
    main()
