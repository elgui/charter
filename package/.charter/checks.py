"""The gate logic. Pure functions over repository state; no hook I/O here.

Every check returns a list of Finding. `level` is "block" or "warn". Callers
(hooks, git hooks, CI) decide what a block means in their context. A check that
cannot run because of a broken artifact returns a Finding with gate="error" and
level="warn": gates fail open and the log shows it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import lib

# The default governance set; a project sets its own with `governance_files` in charter/config.json.
GOVERNANCE_FILES = ["CLAUDE.md", "AGENTS.md", "charter/scope.md"]
GOVERNANCE_GLOBS = [".claude/rules/*.md"]
DEFAULT_GOVERNANCE = GOVERNANCE_FILES + GOVERNANCE_GLOBS
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# An id ends in a letter or digit: `see charter:foo.` cites `foo`, not the unknown id `foo.`
# (3 of the decisions gate's first 7 blocks in tele-claude were that trailing period).
MARKER_RE = re.compile(r"charter:([a-z0-9](?:[a-z0-9._-]*[a-z0-9])?)", re.I)
CHECKBOX_RE = re.compile(r"^\s*-\s*\[( |x|X)\]\s*(AC-\d+|[^\n]*)", re.M)
PROBE_RE = re.compile(r"^\s*-\s*\[[ xX]\]\s*(AC-\d+)?[^\n]*?probe:\s*`([^`\n]+)`", re.M)
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
FILELINE_RE = re.compile(r"(?<![\w/.~-])((?:~/|/)?(?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_.\-]+\.[A-Za-z0-9]+):(\d+)(?:-(\d+))?")
URL_RE = re.compile(r"https?://[^\s)>\]]+")
PATH_RE = re.compile(r"(?<![\w/:.~-])((?:~/|/)?(?:\.?[A-Za-z0-9_.\-]+/)+[A-Za-z0-9_.\-]*|[A-Za-z0-9_\-]+\.(?:md|py|json|jsonl|ya?ml|toml|txt|sh|ts|js|csv|html))(?![\w/])")
# a recorded run: a line (or list item) starting with `$ cmd`, or `$ cmd` in backticks anywhere
RUN_RE = re.compile(r"^\s*(?:[-*]\s+)?`?\$ \S[^\n]*|`\$ [^`\n]+`", re.M)
ISSUE_RE = re.compile(r"(?<![\w&/#])(?:[\w.-]+/[\w.-]+)?#\d+\b")
DONE_CLAIM_RE = re.compile(
    r"\b(done|complete[d]?|finished|implemented|fixed|resolved|shipped|all tests pass(?:ed|ing)?|ready to merge)\b"
    r"|✅|\[x\]", re.I)

# Files whose content decides what the gates enforce. Edit and Write on them are owner acts.
OWNER_ONLY_FILES = ["charter/scope.md", "charter/config.json", "charter/rails.md",
                    ".claude/settings.json", ".claude/settings.local.json", ".github/workflows/charter.yml"]
OWNER_ONLY_GLOBS = [lib.TOOL_DIR + "/**"]
# Written only by the CLI; a hand edit in a session is refused, a commit of the CLI's output is not.
CLI_ONLY_FILES = ["charter/ledger.jsonl"]


@dataclass
class Finding:
    gate: str            # scope | size | done | decisions | perimeter | memory | anchors | error
    level: str           # block | warn
    message: str
    path: str = ""
    override: str = ""   # what a person or agent can do to legitimately pass

    def line(self) -> str:
        p = f" [{self.path}]" if self.path else ""
        o = f" Override: {self.override}" if self.override else ""
        return f"charter/{self.gate} {self.level}{p}: {self.message}{o}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def add(self, *f: Finding) -> None:
        self.findings.extend(f)

    @property
    def blocks(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "block"]

    @property
    def warns(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warn"]


# ---------------------------------------------------------------- scope (R6)

def check_scope(root: Path, cfg: dict, relpaths: list[str]) -> list[Finding]:
    """Paths under an out-of-scope glob need an approved change request that covers them."""
    if cfg.get("track") != "client":
        return []
    sc = lib.scope(root)
    out: list[Finding] = []
    if not sc["exists"]:
        return [Finding("scope", "warn", "charter/scope.md is missing on the client track",
                        override="write charter/scope.md from the signed devis (template in charter/templates/scope.md)")]
    approved = lib.approved_changes(root)
    for rp in relpaths:
        for xid, item in sc["out"].items():
            if item["paths"] and lib.matches_any(rp, item["paths"]):
                covered = [cid for cid, c in approved.items() if lib.matches_any(rp, lib.as_list(c.get("paths")))]
                if covered:
                    break
                out.append(Finding("scope", "block",
                                   f"{rp} is under out-of-scope item {xid} ({item['title']}) and no approved change request covers it",
                                   path=rp,
                                   override="write charter/changes/<slug>.md (template in charter/templates/change.md); the owner sets status: approved"))
                break
    return out


def check_unit_scope(root: Path, cfg: dict, unit: dict) -> list[Finding]:
    """A unit on the client track must cite an existing scope item or an approved change."""
    if cfg.get("track") != "client":
        return []
    sc = lib.scope(root)
    if not sc["exists"]:
        return []
    status = str(unit.get("status", ""))
    if status in lib.as_list(cfg.get("done_statuses")) or status in lib.TERMINAL_STATUSES:
        return []
    cited = lib.as_list(unit.get("scope"))
    if not cited:
        return [Finding("scope", "warn", f"unit {unit['_id']} cites no scope item (scope: S<n> or a change id)", path=unit["_path"],
                        override="add `scope: <id>` naming an item in charter/scope.md or an approved change request")]
    approved = lib.approved_changes(root)
    known = set(sc["in"]) | set(approved)
    bad = [c for c in cited if c not in known]
    if bad:
        return [Finding("scope", "block", f"unit {unit['_id']} cites unknown scope id(s): {', '.join(bad)}", path=unit["_path"],
                        override="cite an existing in-scope item or an approved change request")]
    out: list[Finding] = []
    cited_paths = [p for c in cited for p in (sc["in"][c]["paths"] if c in sc["in"] else lib.as_list(approved[c].get("paths")))]
    for g in lib.as_list(unit.get("perimeter")):
        probe = g.replace("**", "x").replace("*", "x")   # a representative path for the glob
        for xid, item in sc["out"].items():
            if item["paths"] and lib.matches_any(probe, item["paths"]) and not any(lib.matches_any(probe, lib.as_list(c.get("paths"))) for c in approved.values()):
                out.append(Finding("scope", "warn", f"unit {unit['_id']} perimeter entry {g} falls under out-of-scope item {xid} ({item['title']})",
                                   path=unit["_path"], override="narrow `perimeter:`, or propose a change request for that path"))
        if cited_paths and not lib.matches_any(probe, cited_paths):
            out.append(Finding("scope", "warn", f"unit {unit['_id']} perimeter entry {g} is not covered by the paths of {', '.join(cited)}",
                               path=unit["_path"], override="cite the scope item that covers it, or narrow `perimeter:`"))
    return out


def check_scope_file(root: Path, cfg: dict) -> list[Finding]:
    """What in charter/scope.md makes the scope gate fail open."""
    if cfg.get("track") != "client":
        return []
    sc = lib.scope(root)
    return [Finding("scope", "warn", f"charter/scope.md: {p}", path="charter/scope.md",
                    override="fix charter/scope.md (template in charter/templates/scope.md)") for p in sc["problems"]] if sc["exists"] else []


# ---------------------------------------------------------------- size (R3)

def is_governance(cfg: dict, rp: str) -> bool:
    """Governance files carry the governance line limit and the byte budget. Decisions and change
    requests always do; the rest of the set is `governance_files`, today's list by default."""
    if rp.startswith("charter/decisions/") or rp.startswith("charter/changes/"):
        return True
    gov = cfg.get("governance_files")
    return lib.matches_any(rp, lib.as_list(gov) if gov is not None else DEFAULT_GOVERNANCE)


def _today() -> str:
    import datetime as _dt
    return _dt.date.today().isoformat()


def size_exceptions(cfg: dict, today: str | None = None) -> tuple[dict, dict, list[Finding]]:
    """(live, expired, problems) from `size_exceptions` in charter/config.json. An exception names one
    path, a budget in `lines` and/or `bytes`, `because:` and a dated `expires:`; without either of the
    last two it is ignored. Expiry is exclusive, as for decisions: on its `expires:` date it has stopped."""
    today = today or _today()
    live: dict = {}
    expired: dict = {}
    problems: list[Finding] = []
    raw = cfg.get("size_exceptions") or []
    if not isinstance(raw, list):
        return live, expired, [Finding("size", "warn", "size_exceptions in charter/config.json is not a list; ignored", path="charter/config.json")]
    for i, e in enumerate(raw):
        where = f"size_exceptions[{i}]"
        if not isinstance(e, dict) or not isinstance(e.get("path"), str) or not e.get("path"):
            problems.append(Finding("size", "warn", f"{where} names no `path`; ignored", path="charter/config.json"))
            continue
        rp = e["path"]
        missing = [k for k in ("because", "expires") if not str(e.get(k, "") or "").strip()]
        budget_ok = all(isinstance(e.get(k), int) and not isinstance(e.get(k), bool) and e.get(k) > 0 for k in ("lines", "bytes") if k in e) and ("lines" in e or "bytes" in e)
        if missing or not budget_ok:
            why = (f"no {' or '.join('`' + k + ':`' for k in missing)}" if missing else "") + \
                  ("" if budget_ok else ("; " if missing else "") + "no positive `lines` or `bytes` budget")
            problems.append(Finding("size", "warn", f"{where} ({rp}) has {why}; ignored, the default limit applies", path="charter/config.json",
                                    override="the owner adds `because:` (the case) and a dated `expires:` to the exception"))
            continue
        exp = str(e["expires"]).strip()
        if not DATE_RE.fullmatch(exp):
            problems.append(Finding("size", "warn", f"{where} ({rp}) expires on `{exp}`, not a date; ignored", path="charter/config.json"))
            continue
        if exp <= today:
            expired[rp] = exp
            problems.append(Finding("size", "warn", f"{where} ({rp}) expired on {exp}; the default limit applies again", path="charter/config.json",
                                    override="the owner renews it with a new `expires:`, or the file is split"))
            continue
        live[rp] = e
    return live, expired, problems


def check_size_exceptions(cfg: dict, today: str | None = None) -> list[Finding]:
    return size_exceptions(cfg, today)[2]


@dataclass
class SizeBudget:
    lines: int
    bytes: int | None = None
    exception: dict | None = None
    expired_on: str = ""

    def label(self, unit: str) -> str:
        n = self.lines if unit == "line" else self.bytes
        if self.exception and (unit in ("line",) and "lines" in self.exception or unit == "byte" and "bytes" in self.exception):
            return f"the {n}-{unit} budget of its size exception (expires {self.exception['expires']})"
        tail = f" (its size exception expired on {self.expired_on})" if self.expired_on else ""
        return f"the {n}-{unit} limit{tail}"


# the installer's files outside .charter/ (OWNED in bin/charter-pkg; tests/test_chain_reliability.py keeps the two in
# step). Fixed paths, not the manifest: a manifest is a file a session can rewrite, and read from the tree it would not
# be the one a staged check judges; and not globs, which would exempt a project's own file named like one of these
# (cross-review, 2026-10-04)
PACKAGE_FILES = frozenset((
    ".claude/rules/charter.md", ".claude/skills/charter-unit/SKILL.md", ".claude/skills/charter-decision/SKILL.md",
    ".claude/skills/charter-progress/SKILL.md", ".claude/skills/charter-chain/SKILL.md", ".claude/commands/resume-chain.md",
    ".claude/agents/charter-reviewer.md",
    ".github/workflows/charter.yml", "charter/README.md", "charter/templates/scope.md", "charter/templates/decision.md",
    "charter/templates/change.md", "charter/templates/unit.md", "charter/templates/rails.md", "charter/templates/handoff.md",
    "charter/templates/owner.md"))


def size_budget_for(root: Path, cfg: dict, rp: str, today: str | None = None) -> SizeBudget | None:
    if lib.matches_any(rp, lib.as_list(cfg.get("exempt_from_size"))) or rp.startswith(lib.TOOL_DIR + "/") or rp in PACKAGE_FILES:
        # .charter/ and the installer's other files are the package's; the project cannot split them, an upgrade
        # replaces them (trial 2026-10-04: a 30-line limit refused the upgrade's own skill and handoff template)
        return None
    limits = cfg.get("limits") or {}
    if is_governance(cfg, rp):
        gb = limits.get("governance_bytes", 32768)
        b = SizeBudget(int(limits.get("governance_lines", 400)), int(gb) if gb else None)
    else:
        b = SizeBudget(int(limits.get("file_lines", 800)))
    live, expired, _ = size_exceptions(cfg, today)
    e = live.get(rp)
    if e:
        b.exception = e
        if "lines" in e:
            b.lines = int(e["lines"])
        if "bytes" in e:
            b.bytes = int(e["bytes"])
    elif rp in expired:
        b.expired_on = expired[rp]
    return b


def size_limit_for(root: Path, cfg: dict, rp: str) -> int | None:
    """The line limit for rp, an exception's budget included; None when rp is exempt."""
    b = size_budget_for(root, cfg, rp)
    return b.lines if b else None


def split_unit_for(root: Path, rp: str, cfg: dict | None = None) -> str | None:
    """Id of an open unit with kind: split that names rp in its perimeter. Only literal paths count:
    a glob would unfreeze every file under it."""
    closed = lib.as_list((cfg or {}).get("done_statuses") or ["done"]) + list(lib.TERMINAL_STATUSES)
    for uid, u in lib.taskets(root).items():
        if str(u.get("kind", "")) == "split" and str(u.get("status", "")) not in closed:
            if rp in [g for g in lib.as_list(u.get("perimeter")) if not any(c in g for c in "*?[")]:
                return uid
    return None


def check_size(root: Path, cfg: dict, rp: str, new_lines: int, old_lines: int,
               new_bytes: int | None = None, old_bytes: int = 0) -> list[Finding]:
    """A file over its line limit, or a governance file over its byte budget, is frozen for growth.
    A live named exception replaces the limit it names; an open split unit unfreezes the file.
    `limits.growth_slack_lines` (default 0) lets one change add that many lines to a non-governance
    file over its line limit, with a warning: in tele-claude, 66 files over 800 lines had no
    exception, so a one-line fix to any of them was refused (the size gate blocked 143 times in
    its first week there)."""
    b = size_budget_for(root, cfg, rp)
    if b is None:
        return []
    over = []
    if new_lines > b.lines and new_lines > old_lines:
        over.append(("line", new_lines, f"would grow to {new_lines} lines" if old_lines else f"is {new_lines} lines"))
    if b.bytes and new_bytes is not None and new_bytes > b.bytes and new_bytes > old_bytes:
        over.append(("byte", new_bytes, f"would grow to {new_bytes} bytes" if old_bytes else f"is {new_bytes} bytes"))
    if over:
        su = split_unit_for(root, rp, cfg)
        what = "; ".join(f"{v}, over {b.label(u)}" for u, n, v in over)
        if su:
            return [Finding("size", "warn", f"{rp} {what}; allowed because split unit {su} is open", path=rp)]
        slack = int((cfg.get("limits") or {}).get("growth_slack_lines", 0) or 0)
        if ([u for u, _, _ in over] == ["line"] and old_lines and new_lines - old_lines <= slack
                and not is_governance(cfg, rp)):
            return [Finding("size", "warn", f"{rp} {what}; allowed as {new_lines - old_lines} of the "
                                            f"{slack}-line growth slack. Plan a split", path=rp)]
        return [Finding("size", "block", f"{rp} {what}; the file is frozen for growth", path=rp,
                        override=f"move code out of it into a new file (shrinking is always allowed), or ask the owner to open a unit with `kind: split` and `perimeter: [{rp}]`, or to name it in `size_exceptions` with a budget, `because:` and `expires:`")]
    # Warn when a change CROSSES 80%, not on every change above it. An exception's budget is 1.25x
    # the file's size on the day it was granted, so 80% of it is that size: warning above 80% warned
    # on every line any exception file gained.
    if new_lines > int(b.lines * 0.8) >= old_lines:
        return [Finding("size", "warn", f"{rp} is at {new_lines} lines, {b.lines} is the limit; plan a split", path=rp)]
    if b.bytes and new_bytes is not None and new_bytes > int(b.bytes * 0.8) >= old_bytes:
        return [Finding("size", "warn", f"{rp} is at {new_bytes} bytes, {b.bytes} is the budget; plan a split", path=rp)]
    return []


# ---------------------------------------------------------------- done (R9)

def _resolves(root: Path, anchor_kind: str, value: str, extra: str = "") -> bool:
    if anchor_kind == "sha":
        return lib.git(root, "cat-file", "-e", f"{value}^{{commit}}").returncode == 0
    if anchor_kind == "fileline":
        p = _abs(root, value)
        if not _exists(p, file=True):
            return False
        n = int(extra)
        return 1 <= n <= max(1, lib.count_lines(p))
    if anchor_kind == "path":
        return _exists(_abs(root, value))
    if anchor_kind == "url":
        return True
    return False


DOC_DIR: Path | None = None   # set by the anchors command: paths may be relative to the document


def _exists(p: Path, file: bool = False) -> bool:
    """A path this user may not look at (under another user's home) does not resolve here; pathlib raises there."""
    try:
        return p.is_file() if file else p.exists()
    except OSError:
        return False


def _abs(root: Path, value: str) -> Path:
    """Repo-relative by default; `~/` and `/` paths resolve on this machine (a report written
    here is checked here; CI sees them as unresolved, which is the honest reading)."""
    if value.startswith("~/"):
        return Path(os.path.expanduser(value))
    if value.startswith("/"):
        return Path(value)
    if not _exists(root / value) and DOC_DIR is not None and _exists(DOC_DIR / value):
        return DOC_DIR / value
    return root / value


def classify_anchors(root: Path, text: str) -> dict[str, list[str]]:
    """Anchors in a text by kind: sha, fileline, url, path and run resolve; bad do not."""
    k: dict[str, list[str]] = {"sha": [], "fileline": [], "url": [], "path": [], "run": [], "bad": []}
    for m in FILELINE_RE.finditer(text):
        (k["fileline"] if _resolves(root, "fileline", m.group(1), m.group(2)) else k["bad"]).append(f"{m.group(1)}:{m.group(2)}")
    # a hex run inside a path (a UUID directory, a hash-named file) is part of the path, not a commit
    for m in SHA_RE.finditer(re.sub(r"\S*/\S*", " ", text)):
        v = m.group(0)
        if re.fullmatch(r"\d+", v):
            # digits only: a number, unless git knows it as a commit (a short SHA is all digits ~4% of the time)
            if _resolves(root, "sha", v):
                k["sha"].append(v)
            continue
        (k["sha"] if _resolves(root, "sha", v) else k["bad"]).append(v)
    k["url"] = URL_RE.findall(text)
    stripped = URL_RE.sub(" ", FILELINE_RE.sub(" ", text))
    for m in PATH_RE.finditer(stripped):
        cand = m.group(1).rstrip("/.")
        if "*" in cand or not cand or cand.startswith("-"):
            continue
        if _exists(_abs(root, cand)):
            k["path"].append(cand)
    k["run"] = [m.group(0).strip()[:60] for m in RUN_RE.finditer(text)]
    return k


def evidence_anchors(root: Path, text: str) -> tuple[list[str], list[str]]:
    """(resolving, unresolved) anchors found in a text."""
    k = classify_anchors(root, text)
    return k["fileline"] + k["sha"] + k["url"] + k["path"] + k["run"], k["bad"]


def check_unit_done(root: Path, cfg: dict, unit_text: str, path: str) -> list[Finding]:
    """Given the full text a tasket would have after an edit, refuse `done` without evidence."""
    fields, _, body = lib.split_frontmatter(unit_text)
    status = str(fields.get("status", ""))
    if status not in lib.as_list(cfg.get("done_statuses")):
        return []
    uid = str(fields.get("id") or Path(path).stem)
    # strict on purpose: a legacy tasket keeps its warning until it gains `## Acceptance`, even with `## Done When`
    if uid in lib.legacy_taskets(root) and not lib.section(body, "Acceptance"):
        return [Finding("done", "warn", f"legacy tasket {uid} set to {status} without acceptance criteria (listed in {lib.LEGACY_FILE})", path=path)]
    out: list[Finding] = []
    acc = lib.acceptance(body)
    boxes = CHECKBOX_RE.findall(acc)
    if not boxes:
        out.append(Finding("done", "block", "status is done but there is no `## Acceptance` checklist (`## Done When` counts too)", path=path,
                           override="add `## Acceptance` with `- [x] AC-n: ... — probe: <command>` lines, or keep the status open"))
    else:
        unchecked = [b for b in boxes if b[0] == " "]
        if unchecked:
            names = [b[1].strip()[:60] for b in unchecked]   # the AC id, else the line's text (0.4.15)
            named = ", ".join(names[:10]) + (f", +{len(names) - 10} more" if len(names) > 10 else "")
            out.append(Finding("done", "block", f"status is done but {len(unchecked)} acceptance box(es) are unchecked: {named}", path=path,
                               override="run each probe, check the box, and cite the run under `## Evidence`; or keep the status open"))
    k = classify_anchors(root, lib.section(body, "Evidence"))
    if not k["sha"] and not k["run"]:
        out.append(Finding("done", "block", "status is done but `## Evidence` names no commit that resolves and no `$ command` run; a path or a URL alone shows nothing ran", path=path,
                           override="add the commit SHA(s) and each probe as a `$ command` line with its result (`charter probe <unit>` prints them)"))
    if k["bad"]:
        out.append(Finding("done", "block", f"evidence anchors do not resolve: {', '.join(k['bad'][:5])}", path=path,
                           override="fix the anchors so they point at commits and lines that exist; a commit a squash or rebase merge "
                                    "removed resolves in CI once the pull-request heads are fetched (.github/workflows/charter.yml)"))
    if (cfg.get("review") or {}).get("required") and not review_lines(root, lib.section(body, "Evidence")):
        out.append(Finding("done", "block", "status is done but `## Evidence` has no `review:` line; this project requires an independent review before done", path=path,
                           override="add `- review: <reviewer and model> — <verdict> — <anchor>` naming where the verdict is (a PR comment URL, a commit, a `$ command` run)"))
    return out


REVIEW_RE = re.compile(r"^\s*-?\s*review:\s*(\S.*)$", re.M | re.I)


def review_lines(root: Path, evidence: str) -> list[str]:
    """`review:` lines in `## Evidence` that carry an anchor which resolves."""
    return [m.group(1) for m in REVIEW_RE.finditer(evidence) if evidence_anchors(root, m.group(1))[0]]


def acceptance_items(body: str) -> list[str]:
    """Acceptance lines with the tick normalised, so ticking a box is not a change."""
    return [re.sub(r"\[[xX]\]", "[ ]", l.strip()) for l in lib.acceptance(body).splitlines() if CHECKBOX_RE.match(l)]


def check_acceptance_change(old_text: str, new_text: str, path: str) -> list[Finding]:
    """Once a unit leaves planning, removing or rewriting an acceptance line needs a `## Log` line saying why."""
    if not old_text:
        return []
    of, _, ob = lib.split_frontmatter(old_text)
    if str(of.get("status", "")) in lib.PLANNING_STATUSES:
        return []
    _, _, nb = lib.split_frontmatter(new_text)
    new_items = acceptance_items(nb)
    changed = [i for i in acceptance_items(ob) if i not in new_items]
    if not changed:
        return []
    old_log = [l for l in lib.section(ob, "Log").splitlines() if l.strip()]
    new_log = [l for l in lib.section(nb, "Log").splitlines() if l.strip()]
    if len(new_log) > len(old_log):
        return []
    return [Finding("done", "block", f"acceptance changed after work started ({changed[0][:80]}) with no new `## Log` line", path=path,
                    override="append a dated `## Log` line saying which criterion changed and why, in the same edit")]


def unit_probes(text: str) -> list[tuple[str, str]]:
    """(criterion id, command) for each `probe: `cmd`` in a unit's acceptance checklist."""
    return [(ac, cmd) for ac, cmd, _ in _probe_lines(text)]


def run_probes(root: Path, text: str, path: str, timeout: int) -> tuple[list[Finding], list[str]]:
    """Run a unit's probes from the repository root. Returns findings and evidence lines."""
    return run_probes_recorded(root, text, path, timeout)[:2]


# A probe record keeps the end of each stream, at most this many lines and bytes, cut at a line (0.4.15). pytest -q
# ends with one `FAILED <test> - <error>` line per failing test, then the count; 20 lines hold that for a dozen
# failures. 2 KiB per stream keeps one probe's record under 4 KiB, half of what a chain handoff may hold (8 KiB,
# `MAX_BYTES` in .charter/chain.py), so the briefing that carries it stays readable.
TAIL_LINES, TAIL_BYTES = 20, 2048


def _tail(text: str) -> tuple[str, int]:
    """(the end of a stream within TAIL_LINES and TAIL_BYTES, cut at a line; how many lines the stream had).
    Blank lines at either end do not count; a single line longer than the cap keeps its end."""
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    kept, size = [], 0
    for line in reversed(lines[-TAIL_LINES:]):
        b = len(line.encode("utf-8")) + (1 if kept else 0)
        if size + b > TAIL_BYTES:
            if not kept:
                kept.append(line.encode("utf-8")[-TAIL_BYTES:].decode("utf-8", "ignore"))
            break
        kept.append(line)
        size += b
    return "\n".join(reversed(kept)), len(lines)


def _stream(v) -> str:
    """A stream a timeout left behind: bytes on POSIX even when text was asked for."""
    return v.decode("utf-8", "replace") if isinstance(v, bytes) else (v or "")


def probe_record(root: Path, ac: str, cmd: str, timeout: int) -> tuple[dict, str]:
    """Run one probe. (its record, the one-line tail the text line has always shown: the last line of stdout and
    stderr together, cut to 100 characters)."""
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, shell=True, cwd=str(root), capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
        out, err, code = r.stdout, r.stderr, r.returncode
        outcome = "passed" if code == 0 else "failed"
        line = ((out + err).strip().splitlines() or [""])[-1][:100]
    except subprocess.TimeoutExpired as e:
        out, err, code, outcome = _stream(e.stdout), _stream(e.stderr), None, "timeout"
        line = f"timed out after {timeout} s"
    (out_tail, out_n), (err_tail, err_n) = _tail(out), _tail(err)
    return {"ac": ac, "command": cmd, "outcome": outcome, "exit": code, "duration_s": round(time.monotonic() - t0, 2),
            "stdout_tail": out_tail, "stderr_tail": err_tail, "stdout_lines": out_n, "stderr_lines": err_n}, line


def run_probes_recorded(root: Path, text: str, path: str, timeout: int) -> tuple[list[Finding], list[str], list[dict]]:
    """`run_probes` with each probe's record (0.4.15). The evidence lines are the ones 0.4.14 printed, byte for byte:
    tele-claude's checker parses them (`_PROBE_LINE`, services/checker/core.py:98 in tele-claude)."""
    out, lines, records = [], [], []
    probes = unit_probes(text)
    if not probes:
        out.append(Finding("probe", "block", f"{path} has no `probe:` command in `## Acceptance`, so nothing can be re-run", path=path,
                           override="name a command for each criterion: `- [ ] AC-1: ... — probe: `<command>``"))
    for ac, cmd in probes:
        rec, tail = probe_record(root, ac, cmd, timeout)
        records.append(rec)
        code = rec["exit"]
        lines.append(f"- `$ {cmd}` → " + (f"exit {code}" if code is not None else tail) + (f" ({tail})" if tail and code else ""))
        if code != 0:
            out.append(Finding("probe", "block", f"{ac} probe failed: `{cmd}` " + (f"exited {code}: {tail}" if code is not None else tail), path=path,
                               override="make the probe pass, or reopen the unit"))
    return out, lines, records


def failure_lines(records: list[dict]) -> list[str]:
    """Each failed probe with its stdout and stderr tails, for a person or the next session. Every tail line starts
    with `| ` after its indent, so no line of a probe's output reads as a probe line once stripped."""
    out = []
    for r in records:
        if r["outcome"] == "passed":
            continue
        how = f"exited {r['exit']}" if r["outcome"] == "failed" else "timed out"
        out.append(f"{r['ac']} failed: `{r['command']}` {how} after {r['duration_s']} s")
        for stream in ("stdout", "stderr"):
            tail, n = r[f"{stream}_tail"], r[f"{stream}_lines"]
            if not n:
                out.append(f"  {stream}: empty")
                continue
            kept = tail.splitlines()
            out.append(f"  {stream}, last {len(kept)} of {n} line(s):")
            out += [f"  | {l}" for l in kept]
    return out


def changed_since_base(root: Path, unit: dict, path: str) -> dict | None:
    """The paths changed between the unit's base (`unit_base`, the one the probes run at) and the working tree,
    untracked files included, split by the unit's `perimeter:`; with no perimeter every path is inside. Paths the
    perimeter gate exempts are left out. None when the unit has no base. In a checkout other sessions commit to,
    their work since the base is in it too."""
    base = unit_base(root, path)
    if not base:
        return None
    tracked = lib.git(root, "-c", "core.quotePath=false", "diff", "--name-only", "-z", base).stdout.split("\0")
    untracked = lib.git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0")
    paths = sorted({p for p in tracked + untracked if p and not p.startswith(lib.PERIMETER_EXEMPT)})
    per = lib.as_list(unit.get("perimeter"))
    inside = [p for p in paths if not per or lib.matches_any(p, per)]
    return {"base": base, "inside": inside, "outside": [p for p in paths if p not in inside]}


def changed_lines(changed: dict | None) -> list[str]:
    if changed is None:
        return ["changed since the unit's base: unknown (the commit that added the unit has no parent)"]
    out = changed["outside"]
    return [f"changed since {changed['base'][:10]}, the unit's base: {len(changed['inside'])} path(s) inside the perimeter, {len(out)} outside"
            + (": " + ", ".join(out[:10]) + (f", +{len(out) - 10} more" if len(out) > 10 else "") if out else "")]


def unit_base(root: Path, path: str) -> str | None:
    """The repository before the unit existed: the parent of the commit that added its file, HEAD
    when the file is not committed yet, None when that commit has no parent."""
    r = lib.git(root, "log", "--follow", "--diff-filter=A", "--format=%H", "--", path)
    added = [l for l in r.stdout.split() if l.strip()]
    if not added:
        return lib.git(root, "rev-parse", "--verify", "--quiet", "HEAD").stdout.strip() or None
    p = lib.git(root, "rev-parse", "--verify", "--quiet", f"{added[-1]}^")
    return p.stdout.strip() or None


def run_probes_at_base(root: Path, cfg: dict, text: str, path: str, timeout: int) -> list[Finding]:
    """A probe that already passes before the unit's work does not test it (method.md § Real tests, point 2).
    Runs each probe in a detached worktree at `unit_base`; a criterion marked `(guard)` protects
    existing behaviour and is expected to pass there. Untracked dependencies (node_modules, a venv)
    are absent from the worktree, so a probe that fails there for that reason is not reported."""
    probes = [(ac, cmd) for ac, cmd, line in _probe_lines(text) if "(guard)" not in line]
    base = unit_base(root, path) if probes else None
    if not base:
        return []
    # a git hook runs with GIT_INDEX_FILE (and may run with GIT_DIR) pointing at the main checkout;
    # inherited, they make `worktree add` and the probes in the worktree act on the wrong index
    env = {k: v for k, v in os.environ.items() if k not in _GIT_LOCAL_ENV}
    tmp = Path(tempfile.mkdtemp(prefix="charter-base-"))
    wt = tmp / "base"
    try:
        r = subprocess.run(["git", "-C", str(root), "worktree", "add", "--detach", "--quiet", str(wt), base],
                           capture_output=True, encoding="utf-8", errors="replace", env=env)
        if r.returncode != 0:
            return [Finding("error", "warn", f"could not check out {base[:10]} to run {path}'s probes before the change: {r.stderr.strip()[:100]}", path=path)]
        level = "block" if (cfg.get("probes") or {}).get("base_must_fail") else "warn"
        out = []
        for ac, cmd in probes:
            try:
                code = subprocess.run(cmd, shell=True, cwd=str(wt), capture_output=True, timeout=timeout, env=env).returncode
            except subprocess.TimeoutExpired:
                continue
            if code == 0:
                out.append(Finding("probe", level, f"{ac} probe already passes at {base[:10]}, before the unit's work: `{cmd}` does not test the change", path=path,
                                   override="make the probe exercise the new behaviour, or mark a criterion that guards existing behaviour `(guard)`"))
        return out
    finally:
        subprocess.run(["git", "-C", str(root), "worktree", "remove", "--force", str(wt)], capture_output=True, env=env)
        shutil.rmtree(tmp, ignore_errors=True)


_GIT_LOCAL_ENV = ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_PREFIX", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY")


def _probe_lines(text: str) -> list[tuple[str, str, str]]:
    """(criterion id, command, whole line) for each probe, so a line's markers can be read."""
    _, _, body = lib.split_frontmatter(text)
    return [(m.group(1) or f"line {i + 1}", m.group(2).strip(), m.group(0)) for i, m in enumerate(PROBE_RE.finditer(lib.acceptance(body)))]


# ---------------------------------------------------------------- decisions (R1)

def decision_index(root: Path) -> dict[str, dict]:
    return lib.decisions(root)


def check_decisions_text(root: Path, decs: dict[str, dict], rp: str, text: str) -> list[Finding]:
    """Markers in `text` must reference active decisions; bound files must carry a marker."""
    out: list[Finding] = []
    cited = set(m.group(1) for m in MARKER_RE.finditer(text))
    for did in cited:
        d = decs.get(did)
        if d is None:
            out.append(Finding("decisions", "block", f"{rp} cites decision `{did}` which does not exist", path=rp,
                               override=f"create charter/decisions/{did}.md or fix the marker"))
        elif str(d.get("status")) in ("superseded", "retired"):
            succ = d.get("superseded_by") or "(none named)"
            out.append(Finding("decisions", "block", f"{rp} cites decision `{did}` which is {d.get('status')}; successor: {succ}", path=rp,
                               override=f"cite {succ} instead, or reopen the decision by a new record"))
    for did, d in decs.items():
        if str(d.get("status", "active")) != "active":
            continue
        binds = lib.as_list(d.get("binds"))
        if binds and lib.matches_any(rp, binds) and did not in cited:
            out.append(Finding("decisions", "warn", f"{rp} is bound by decision `{did}` ({d.get('title', '')}) but carries no `charter:{did}` marker", path=rp,
                               override=f"add a comment containing `charter:{did}` near the code that depends on it"))
    return out


def check_unit_decisions(root: Path, decs: dict[str, dict], unit: dict) -> list[Finding]:
    """A unit's `decisions:` key names what it relies on; say when one is gone or no longer active."""
    out = []
    for did in lib.as_list(unit.get("decisions")):
        d = decs.get(did)
        if d is None:
            out.append(Finding("decisions", "warn", f"unit {unit['_id']} relies on decision {did}, which does not exist", path=unit["_path"]))
        elif str(d.get("status", "active")) in ("superseded", "retired"):
            out.append(Finding("decisions", "warn", f"unit {unit['_id']} relies on decision {did}, which is {d.get('status')}; successor: {d.get('superseded_by') or '(none named)'}",
                               path=unit["_path"], override="re-read the unit against the successor and update `decisions:`"))
    return out


def duplicate_ids(root: Path) -> list[Finding]:
    """Two files claiming one decision or change id: the later file would silently replace the earlier."""
    out = []
    for kind, sub in (("decision", "decisions"), ("change request", "changes")):
        seen: dict[str, str] = {}
        d = lib.artifact_root(root) / lib.CHARTER_DIR / sub
        for p in sorted(d.glob("*.md")) if d.is_dir() else []:
            if p.name.lower() in ("readme.md", "index.md"):
                continue
            fields, _ = lib.read_md(p)
            i = str(fields.get("id") or p.stem)
            relp = f"{lib.CHARTER_DIR}/{sub}/{p.name}"
            if i in seen:
                out.append(Finding("decisions" if sub == "decisions" else "changes", "block",
                                   f"{kind} id `{i}` is claimed by both {seen[i]} and {relp}", path=relp,
                                   override="give the new file its own id; to replace a decision, supersede it"))
            else:
                seen[i] = relp
    return out


def id_collision(root: Path, rp: str, new_text: str) -> list[Finding]:
    """A decision or change file whose id another file already holds."""
    sub = "decisions" if rp.startswith(lib.CHARTER_DIR + "/decisions/") else "changes"
    new_id = str(lib.split_frontmatter(new_text)[0].get("id") or Path(rp).stem)
    held = (lib.decisions(root) if sub == "decisions" else lib.change_requests(root)).get(new_id)
    if held is not None and held["_path"] != rp:
        return [Finding("decisions" if sub == "decisions" else "changes", "block", f"id `{new_id}` is already held by {held['_path']}",
                        path=rp, override="give this file its own id; to replace a decision, supersede it")]
    return []


def run_decision_checks(root: Path, decs: dict[str, dict], only_bound_to: list[str] | None = None) -> list[Finding]:
    """Run each active decision's `check:` command. Non-zero exit = the decision is contradicted."""
    out: list[Finding] = []
    for did, d in decs.items():
        if str(d.get("status", "active")) != "active":
            continue
        cmd = d.get("check")
        if not cmd:
            continue
        if only_bound_to is not None:
            binds = lib.as_list(d.get("binds"))
            if not binds or not any(lib.matches_any(rp, binds) for rp in only_bound_to):
                continue
        try:
            r = subprocess.run(str(cmd), shell=True, cwd=str(root), capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        except subprocess.TimeoutExpired:
            out.append(Finding("decisions", "warn", f"decision `{did}` check timed out: {cmd}", path=d["_path"]))
            continue
        if r.returncode != 0:
            tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]
            out.append(Finding("decisions", "block", f"decision `{did}` is contradicted: `{cmd}` exited {r.returncode} {tail[0][:120]}", path=d["_path"],
                               override=f"restore the invariant, or supersede the decision with a new record that names {did} in `supersedes:` and sets its status to superseded"))
    return out


# ---------------------------------------------------------------- perimeter (R4)

def check_perimeter(root: Path, cfg: dict, unit: dict | None, relpaths: list[str], at_commit: bool,
                    others: dict[str, str] | None = None) -> list[Finding]:
    """`others` maps a staged path to the session that edited it when the committing session did not
    (`edited_by_other_sessions`): such a path outside the perimeter is named as that session's, not as this unit's."""
    others = others or {}
    skip = lib.ignored(root, relpaths)   # a file git ignores is local scratch (a tool's journal), not the unit's work
    relpaths = [rp for rp in relpaths if rp not in skip]
    if unit is None:
        if relpaths:
            return [Finding("perimeter", "warn", "no active unit; edits are not attributed (`charter unit start <id>`)")]
        return []
    per = lib.as_list(unit.get("perimeter"))
    if not per:
        return []
    always = [lib.TASKETS_DIR + "/**", lib.CHARTER_DIR + "/**", lib.TOOL_DIR + "/**"]
    notes = lib.section(unit.get("_body", ""), "Outside perimeter")
    out: list[Finding] = []
    for rp in relpaths:
        if lib.matches_any(rp, per) or lib.matches_any(rp, always):
            continue
        if rp in notes or os.path.basename(rp) in notes:
            continue
        level = "block" if (at_commit and cfg.get("track") == "client") else "warn"
        if rp in others:
            out.append(Finding("perimeter", level, f"{rp} is staged, but session {others[rp]} edited it and this session did not; "
                               f"a plain `git commit` charges it to unit {unit['_id']}", path=rp,
                               override="commit only this session's paths, `git commit -m <message> -- <your paths>`, and leave the other "
                                        f"session's to it; or, if this work is the unit's, add `- {rp}: <why>` under `## Outside perimeter` in {unit['_path']}"))
            continue
        out.append(Finding("perimeter", level, f"{rp} is outside the perimeter of unit {unit['_id']} and has no note", path=rp,
                           override=f"add `- {rp}: <why>` under `## Outside perimeter` in {unit['_path']}, or widen `perimeter:`"))
    return out


def edited_by_other_sessions(root: Path, session: str | None, relpaths: list[str]) -> dict[str, str]:
    """{path: session id} for each path another live session's record lists as edited and this session's does not.
    The records are the hooks' `session-<id>.json` in this worktree's git directory, removed at SessionEnd; they list
    Edit, Write and NotebookEdit, not a file a Bash command changed. Empty outside a session. The index is the
    checkout's, so a plain `git commit` takes what any session staged (0.4.15)."""
    sid = lib.session_id(session)
    d = lib.local_state_dir(root)
    if not sid or not d.is_dir():
        return {}
    mine, theirs, want = set(), {}, set(relpaths)
    for f in sorted(d.glob("session-*.json")):
        other = f.name[len("session-"):-len(".json")]
        try:
            edited = json.loads(f.read_text(encoding="utf-8")).get("edited") or []
        except (OSError, ValueError, AttributeError):
            continue
        # a record the hooks did not write is read as listing nothing: a raise here would fail the gate open
        edited = {p for p in edited if isinstance(p, str)} if isinstance(edited, list) else set()
        if lib.session_id(other) == sid:
            mine = edited
            continue
        for rp in sorted(edited & want):
            theirs.setdefault(rp, other)
    return {rp: other for rp, other in theirs.items() if rp not in mine}


# ---------------------------------------------------------------- perimeter fit (0.4.15)

# a commit subject that says `unit <id>` (`(unit <id>)`, `(#105, unit <id>)`) names that unit; an id, one character or more, ends in a letter or digit
UNIT_TAG_RE = re.compile(r"\bunit\s+([A-Za-z0-9](?:[\w.-]*[A-Za-z0-9])?)")


def resolve_unit_tag(tag: str, ids) -> tuple[str | None, bool]:
    """(the unit a commit tag names, whether it was ambiguous). A tag is an id, or the start of exactly one id
    followed by `-` (tele-claude tags `unit 20261008-1730` for `20261008-1730-activity-ledger-...`)."""
    if tag in ids:
        return tag, False
    cands = [i for i in ids if i.startswith(tag + "-")]
    return (cands[0], False) if len(cands) == 1 else (None, len(cands) > 1)


def perimeter_fits(root: Path, units: dict[str, dict]) -> tuple[dict[str, dict], dict]:
    """How each unit's `perimeter:` fit the files its commits touched: ({unit id: fit}, counts over the history).
    One pass over the commits of HEAD, merges left out. A commit counts for a unit when its subject says `unit <id>`,
    the tag the charter-unit skill asks for (tele-claude's sessions wrote it before charter did); a subject that names two or more units counts for none, since its
    files cannot be shared out, and the body is not read, because a squash merge lists every unit it carries there
    (tele-claude b9f273d: 12 units, 107 files). Work committed under no tag, or under another unit's tag, is not seen.
    A report, never a gate (0.4.15)."""
    r = lib.git(root, "-c", "core.quotePath=false", "log", "--no-merges", "--format=%x1e%H%x1f%s%x1f", "--name-only", "HEAD")
    ids = set(units)
    paths_of: dict[str, set] = {uid: set() for uid in units}
    commits = dict.fromkeys(units, 0)
    seen = {"commits": 0, "untagged": 0, "ambiguous": 0, "several": 0}
    for rec in r.stdout.split("\x1e")[1:] if r.returncode == 0 else []:
        parts = rec.split("\x1f")
        if len(parts) < 3:
            continue
        seen["commits"] += 1
        named, unsure = set(), False
        for tag in UNIT_TAG_RE.findall(parts[1]):
            uid, amb = resolve_unit_tag(tag, ids)
            unsure |= amb
            if uid:
                named.add(uid)
        if len(named) != 1 or unsure:   # a tag two ids share names a second unit, whichever one it meant
            seen["several" if named else "ambiguous" if unsure else "untagged"] += 1
            continue
        uid = named.pop()
        commits[uid] += 1
        paths_of[uid] |= {p for p in parts[2].splitlines() if p.strip()}
    fits = {}
    for uid, u in units.items():
        per = lib.as_list(u.get("perimeter"))
        every = sorted(paths_of[uid])
        paths = [p for p in every if not p.startswith(lib.PERIMETER_EXEMPT)]   # the unit's own tasket is not its work
        outside = [p for p in paths if per and not lib.matches_any(p, per)]
        notes = lib.section(u.get("_body", ""), "Outside perimeter")
        fits[uid] = {"commits": commits[uid], "touched": paths, "outside": outside,
                     "outside_noted": [p for p in outside if p in notes or os.path.basename(p) in notes],
                     "entries": per, "untouched_entries": [e for e in per if not any(lib.matches_any(p, [e]) for p in every)]}
    return fits, seen


def _names(items: list[str], n: int = 10) -> str:
    return ", ".join(items[:n]) + (f", +{len(items) - n} more" if len(items) > n else "")


def fit_text(fit: dict, short: bool = False) -> str:
    """One unit's fit in words: `charter unit show <id>` (short=False) and a `charter synth` line (short=True)."""
    if not fit["commits"]:
        return "no commit message says `unit <id>` for this unit"
    s = (f"{fit['commits']} commit(s), {len(fit['touched'])} path(s)" if short
         else f"{fit['commits']} commit(s) name this unit, {len(fit['touched'])} path(s) touched")
    if not fit["entries"]:
        return s + "; no `perimeter:` declared"
    out, noted = fit["outside"], fit["outside_noted"]
    s += f"; {len(out)} outside the perimeter"
    if out:
        s += f" ({len(noted)} noted" + ("" if short else " under `## Outside perimeter`") + f"): {_names(out)}"
    s += f"; {len(fit['entries']) - len(fit['untouched_entries'])} of {len(fit['entries'])} perimeter entries touched"
    return s + (f"; untouched: {_names(fit['untouched_entries'])}" if fit["untouched_entries"] else "")


# ---------------------------------------------------------------- memory (R8)

def check_memory(root: Path, cfg: dict, today: str) -> list[Finding]:
    out: list[Finding] = []
    for did, d in lib.decisions(root).items():
        if str(d.get("status", "active")) != "active":
            continue
        if not lib.section(d.get("_body", ""), "Because") and not d.get("because"):
            out.append(Finding("memory", "warn", f"decision `{did}` records no case that justified it (`## Because`)", path=d["_path"]))
        exp = str(d.get("expires", "")).strip()
        dated = re.fullmatch(r"\d{4}-\d{2}-\d{2}", exp)
        if not exp:
            out.append(Finding("memory", "warn", f"decision `{did}` has no `expires:` (a date or a condition)", path=d["_path"]))
        elif dated and exp <= today:   # exclusive: a decision stops applying at the start of its `expires:` date
            out.append(Finding("memory", "warn", f"decision `{did}` expired on {exp}; renew it or retire it", path=d["_path"]))
        taken = str(d.get("date", "")).strip()
        if dated and re.fullmatch(r"\d{4}-\d{2}-\d{2}", taken) and exp <= taken:
            out.append(Finding("memory", "warn", f"decision `{did}` expires on {exp}, not later than its date {taken}", path=d["_path"]))
        if str(d.get("kind", "")) == "lesson" and not d.get("owner"):
            out.append(Finding("memory", "warn", f"lesson `{did}` has no owner", path=d["_path"]))
    return out


# ---------------------------------------------------------------- change requests (R7)

def check_changes(root: Path) -> list[Finding]:
    out: list[Finding] = []
    for cid, c in lib.change_requests(root).items():
        if str(c.get("status")) == "approved" and not (c.get("approved_by") and c.get("approved_on")):
            out.append(Finding("scope", "block", f"change request `{cid}` is approved without `approved_by:` and `approved_on:`; it unlocks nothing", path=c["_path"],
                               override="only the owner approves; record who and when"))
    return out


# ---------------------------------------------------------------- owner-only changes (R6, R7, R3)

def _fm(text: str | None) -> dict:
    return lib.split_frontmatter(text or "")[0]


# `— owner: do|check|decide` on an acceptance line: a line only the owner closes (owner.OWNER_SEG_RE names the kind)
OWNER_MARK_RE = re.compile(r"\s[—–]\s*owner:", re.I)
BOX_LINE_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*(.*)$")


def acceptance_boxes(text: str) -> list[tuple[int, str, bool, bool]]:
    """(offset in text, key, checked, marked for the owner) for each checkbox of a unit's acceptance section; the key
    is the line's AC id, else its text before the first ` — ` segment."""
    sec = lib.acceptance(lib.split_frontmatter(text or "")[2])
    base = (text or "").find(sec) if sec else -1
    out, pos = [], 0
    for l in sec.splitlines(keepends=True) if base >= 0 else []:
        m = BOX_LINE_RE.match(l.rstrip("\n"))
        if m:
            ac = re.match(r"(AC-\d+)\b", m.group(2))
            key = ac.group(1) if ac else re.split(r"\s[—–]\s", m.group(2))[0].strip().lower()
            out.append((base + pos, key, m.group(1) != " ", bool(OWNER_MARK_RE.search(l))))
        pos += len(l)
    return out


def owner_line_changes(old: str | None, new: str | None) -> list[str]:
    """The owner's lines of a unit that this change closes: an open `— owner:` line that is ticked, unmarked or
    removed, and a line that arrives ticked with the mark. Counted per key, so a duplicate id hides nothing (cross-review,
    2026-10-04). Marking a line, and reopening one, stay free: a session marks what it waits on, and the owner closes it
    (0.4.9, after an agent ticked one in the wait trial). A line without an AC id is known by its text, so rewording
    it reads as closing it: give such a line an id."""
    def counts(text):
        c: dict[str, list[int]] = {}
        for _, k, checked, marked in acceptance_boxes(text or ""):
            if marked:
                c.setdefault(k, [0, 0])[1 if checked else 0] += 1
        return c
    o, n = counts(old), counts(new)
    return [k for k in dict.fromkeys(list(o) + list(n))
            if n.get(k, [0, 0])[1] > o.get(k, [0, 0])[1] or n.get(k, [0, 0])[0] < o.get(k, [0, 0])[0]]


# The files Claude Code reads settings from, by name, and reloads mid-session
# (https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/managed-settings):
# user and project `settings.json`, `settings.local.json` (in a worktree, the main checkout's, which
# is outside the worktree), `managed-settings.json`, and every `*.json` in `managed-settings.d/`.
SETTINGS_FILE_NAMES = ("settings.json", "settings.local.json", "managed-settings.json")


def reaches_the_session(rp: str) -> bool:
    """Whether an `env` block written to `rp` could reach the running session: anything inside the
    project (`rp` relative), and a Claude Code settings file anywhere, by name, through a link too.
    Other files outside the project, a scratchpad or /tmp, reach nothing."""
    if not Path(rp).is_absolute():
        return True
    try:
        paths = (Path(rp), Path(rp).resolve())
    except (OSError, RuntimeError):
        return True
    return any(p.name in SETTINGS_FILE_NAMES or (p.parent.name == "managed-settings.d" and p.suffix == ".json")
               for p in paths)


def owner_only_changes(rp: str, old: str | None, new: str | None, context: str = "edit",
                       done_statuses: list[str] | None = None) -> list[str]:
    """Why changing `rp` from `old` to `new` is the owner's act (empty when it is not). `context` is
    "edit" for a session's Edit or Write, "commit" for a commit or CI; the ledger is refused only in
    "edit", because the CLI writes it and an agent commits what the CLI wrote."""
    old, new = old or "", new or ""
    if old == new:
        return []
    why: list[str] = []
    if context == "edit" and "CHARTER_OWNER" in new and "CHARTER_OWNER" not in old and reaches_the_session(rp):
        # a settings file's `env` block reaches the hooks mid-session (settings reference, `env`)
        why.append("it sets CHARTER_OWNER, which switches the owner-only checks off")
    if rp in OWNER_ONLY_FILES or lib.matches_any(rp, OWNER_ONLY_GLOBS):
        why.append(f"{rp} decides what the gates enforce")
    elif rp == lib.LEGACY_FILE:
        ids = lambda t: {x for x in (l.split("#", 1)[0].strip() for l in t.splitlines()) if x}
        added = sorted(ids(new) - ids(old))
        if added:   # removing an entry only strengthens the done gate
            why.append(f"adding {', '.join(added[:3])} to {rp} exempts them from the done gate")
    elif context == "edit" and rp in CLI_ONLY_FILES:
        why.append(f"{rp} is written by `charter ledger`, never by hand")
    elif rp.startswith(lib.CHARTER_DIR + "/changes/") and rp.endswith(".md"):
        o, n = _fm(old), _fm(new)
        for k in ("status", "approved_by", "approved_on"):
            if str(o.get(k) or "") != str(n.get(k) or "") and (old or n.get(k) not in (None, "", [], "proposed")):
                why.append(f"`{k}:` of a change request is set by the owner")
        if str(o.get("status")) == "approved" and lib.as_list(o.get("paths")) != lib.as_list(n.get("paths")):
            why.append("the paths of an approved change request are what the owner approved")
    elif rp.startswith(lib.CHARTER_DIR + "/decisions/") and rp.endswith(".md") and old:
        o, n = _fm(old), _fm(new)
        for k in ("status", "superseded_by"):
            if str(o.get(k) or "") != str(n.get(k) or ""):
                why.append(f"`{k}:` of an existing decision is changed by the owner; propose a successor instead")
        if str(o.get("status", "active")) == "active":
            for k in ("check", "binds"):
                if lib.as_list(o.get(k)) != lib.as_list(n.get(k)):
                    why.append(f"`{k}:` of an active decision is what the gate enforces; supersede the decision instead")
    elif rp.startswith(lib.TASKETS_DIR + "/") and rp.endswith(".md"):
        lines = owner_line_changes(old, new)
        if lines:
            why.append(f"it closes {', '.join(lines[:4])}, marked `— owner:`: only the owner closes such a line "
                       "(`/resume-chain ok <note>` when a chain waits on it)")
        o, n = _fm(old), _fm(new)
        if str(n.get("kind", "")) == "split":
            was_split = str(o.get("kind", "")) == "split"
            closed = tuple(done_statuses or ["done"]) + lib.TERMINAL_STATUSES
            added = set(lib.as_list(n.get("perimeter"))) - set(lib.as_list(o.get("perimeter")))
            reopened = was_split and str(o.get("status", "")) in closed and str(n.get("status", "")) not in closed
            if not was_split or added or reopened:   # narrowing or closing a split unit is free
                why.append("a `kind: split` unit unfreezes files for the size gate; opening, widening or reopening one is the owner's act (R3)")
    return why


def may_be_owner_only(rp: str) -> bool:
    """Cheap pre-filter for `owner_only_changes` in commit context."""
    return (rp in OWNER_ONLY_FILES or rp == lib.LEGACY_FILE or lib.matches_any(rp, OWNER_ONLY_GLOBS)
            or rp.startswith((lib.CHARTER_DIR + "/changes/", lib.CHARTER_DIR + "/decisions/", lib.TASKETS_DIR + "/")))


OWNER_OVERRIDE = ("this is the owner's act: edit the file yourself, or start Claude Code with CHARTER_OWNER=1 "
                  "for an owner session; as an agent, propose it (a change request, a new decision) and say so")
# at commit the change is already made: the agent leaves it staged and hands the owner one command, not a new session
OWNER_COMMIT_OVERRIDE = ("the owner commits it: leave it staged, run `python3 .charter/bin/charter handover` "
                         "(where it says the owner's delegate takes it, wait with `--wait` first) "
                         "and give the owner the line it prints")


MANIFEST = lib.TOOL_DIR + "/manifest.json"


def blob(root: Path, spec: str) -> bytes | None:
    """The raw bytes of `git show <spec>` (`:path` for the index, `<rev>:path`), None when absent."""
    r = subprocess.run(["git", "-C", str(root), "show", spec], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def release_change(rp: str, read) -> bool:
    """True when `rp`, as `read` returns it (bytes, None when absent), is a package file exactly as the installer
    wrote it: its hash is the one the manifest at the same revision records, and for the manifest itself, every
    file it lists matches. That is an upgrade, which an agent commits. A hand edit of the engine does not match
    and stays the owner's; an edit that also rewrites the manifest is deliberate, and no gate in the tree it
    edits can stop it (docs/gates.md, What this cannot do)."""
    try:
        files = json.loads(read(MANIFEST) or b"").get("files") or {}
    except (ValueError, AttributeError):
        return False
    sha = lambda b: hashlib.sha256(b).hexdigest() if b is not None else None
    if rp == MANIFEST:
        return bool(files) and all(sha(read(f)) == h for f, h in files.items())
    return rp in files and sha(read(rp)) == files[rp]


def owner_only_staged(root: Path, cfg: dict, paths: list[str]) -> dict[str, list[str]]:
    """The staged paths whose change is the owner's, with the reasons; an upgrade's package files are not."""
    out = {}
    read = lambda f: blob(root, f":{f}")
    for rp in [p for p in paths if may_be_owner_only(p)]:
        why = owner_only_changes(rp, head_text(root, rp), staged_text(root, rp), "commit", lib.as_list(cfg.get("done_statuses")))
        if why and not release_change(rp, read):
            out[rp] = why
    return out


# ---------------------------------------------------------------- the kinds of an owner act (0.4.14)

# the kind word after `— owner:`: owner.OWNER_SEG_RE, repeated here because owner.py imports this module; a bare
# `owner:` is a check
OWNER_KIND_RE = re.compile(r"\s[—–]\s*owner:\s*(decide|do|check)?\b", re.I)
SCOPE_FILE = lib.CHARTER_DIR + "/scope.md"
RAILS_FILE = lib.CHARTER_DIR + "/rails.md"
SETTINGS_FILE = ".claude/settings.json"


def _owner_lines_by_key(text: str) -> dict[str, list[tuple[bool, str, str]]]:
    """key -> [(checked, the line after its box, kind)] for each line of a unit's acceptance marked `— owner:`."""
    sec = lib.acceptance(lib.split_frontmatter(text or "")[2])
    out: dict[str, list[tuple[bool, str, str]]] = {}
    for l in (sec or "").splitlines():
        m = BOX_LINE_RE.match(l.rstrip("\n"))
        mk = OWNER_KIND_RE.search(l) if m else None
        if not mk:
            continue
        ac = re.match(r"(AC-\d+)\b", m.group(2))
        key = ac.group(1) if ac else re.split(r"\s[—–]\s", m.group(2))[0].strip().lower()
        out.setdefault(key, []).append((m.group(1) != " ", m.group(2).rstrip(), (mk.group(1) or "check").lower()))
    return out


def owner_line_kinds(old: str | None, new: str | None) -> dict[str, str]:
    """For each owner line this change closes (`owner_line_changes`), its kind of act: `owner-check` when it is the one
    open `— owner: check` line of that key, now ticked, its words and probe unchanged; `structural` for every other
    close (a `do` or `decide` line, a removed, unmarked or reworded line, one that arrives ticked)."""
    o, n = _owner_lines_by_key(old or ""), _owner_lines_by_key(new or "")
    out = {}
    for k in owner_line_changes(old, new):
        ol, nl = o.get(k, []), n.get(k, [])
        ticked = len(ol) == 1 and len(nl) == 1 and not ol[0][0] and nl[0][0] and ol[0][1] == nl[0][1]
        out[k] = "owner-check" if ticked and ol[0][2] == "check" else "structural"
    return out


def settings_installer_exact(old: str | None, new: str | None, fragment: dict | None) -> bool:
    """Whether `new` is what the installer makes of `old`: the charter hooks of `fragment` merged in, nothing else."""
    if not isinstance(fragment, dict) or not isinstance(fragment.get("hooks"), dict):
        return False
    try:
        o = json.loads(old) if (old or "").strip() else {}
        n = json.loads(new or "")
    except ValueError:
        return False
    return isinstance(o, dict) and lib.merge_settings(o, fragment) == n


def owner_act_kinds(rp: str, old: str | None, new: str | None, context: str = "commit",
                    done_statuses: list[str] | None = None, fragment: dict | None = None) -> list[str]:
    """The kinds of owner act that changing `rp` from `old` to `new` is, for the delegate's level (lib.LEVEL_KINDS); empty
    when it is no owner act. `owner-check`: closing `— owner: check` lines; `upgrade`: a settings change exactly as the
    installer writes it, given the package's settings `fragment`; `rails` and `scope`: an edit of charter/rails.md or
    charter/scope.md. Everything else the owner-only check names is `structural`, which no level delegates. A ruling
    (`ruling`) is never an edit: the delegate writes it from a recorded ask (delegate.py)."""
    why = owner_only_changes(rp, old, new, context, done_statuses)
    if not why:
        return []
    old, new = old or "", new or ""
    if any("CHARTER_OWNER" in w for w in why):
        return ["structural"]
    if rp == SCOPE_FILE:
        return ["scope"]
    if rp == RAILS_FILE:
        return ["rails"]
    if rp == SETTINGS_FILE:
        return ["upgrade"] if settings_installer_exact(old, new, fragment) else ["structural"]
    if rp.startswith(lib.TASKETS_DIR + "/") and rp.endswith(".md"):
        kinds = set(owner_line_kinds(old, new).values())
        if any("kind: split" in w for w in why):
            kinds.add("structural")
        return sorted(kinds) or ["structural"]
    return ["structural"]


ENGINE_FRAGMENT = Path(__file__).resolve().parent / "settings-fragment.json"


def staged_fragment(root: Path) -> dict | None:
    """The settings fragment an upgrade's settings change is measured against: the one that ships with this engine, and
    only when the staged copy is that same file. A fragment the staged manifest vouches for is not enough, since an
    agent can write both (review of 2026-10-13, item 4). In a session the engine is the project's own, so the answer is
    advisory; the watcher runs the engine of its own charter checkout, which decides."""
    try:
        mine = ENGINE_FRAGMENT.read_bytes()
        frag = json.loads(mine)
    except (OSError, ValueError):
        return None
    if blob(root, f":{lib.SETTINGS_FRAGMENT}") != mine:
        return None
    return frag if isinstance(frag, dict) else None


def owner_kinds_staged(root: Path, cfg: dict, paths: list[str]) -> dict[str, list[str]]:
    """The staged paths whose change is the owner's (`owner_only_staged`), each with its kinds of owner act."""
    frag = staged_fragment(root)
    done = lib.as_list(cfg.get("done_statuses"))
    return {rp: owner_act_kinds(rp, head_text(root, rp), staged_text(root, rp), "commit", done, frag) or ["structural"]
            for rp in owner_only_staged(root, cfg, paths)}


def check_owner_only_staged(root: Path, cfg: dict, paths: list[str]) -> list[Finding]:
    """At commit: an owner-only change committed from inside Claude Code without CHARTER_OWNER=1 is refused.
    Outside Claude Code the committer cannot be told apart from the owner; CI checks the author."""
    out = []
    for rp, why in owner_only_staged(root, cfg, paths).items():
        if not lib.owner_session():
            level = "block" if lib.in_claude_code() else "warn"
            out.append(Finding("protected", level, f"{rp}: {'; '.join(why)}", path=rp, override=OWNER_COMMIT_OVERRIDE))
    return out


def check_owner_commits(root: Path, cfg: dict, base: str) -> list[Finding]:
    """In CI: every commit in base..HEAD that makes an owner-only change must be authored by `owner`.

    `owner` is read from the base's config, not the one under review: otherwise a change set could
    name its own author the owner and pass for everything else it changes. Only a base without a
    config (the install itself) falls back to the config under review."""
    at_base = lib.git(root, "show", f"{base}:{lib.CHARTER_DIR}/config.json")
    try:
        owner = json.loads(at_base.stdout).get("owner") if at_base.returncode == 0 else cfg.get("owner")
    except (json.JSONDecodeError, AttributeError):
        owner = cfg.get("owner")
    owners = [o.strip().lower() for o in lib.as_list(owner)]
    log = lib.git(root, "log", "--format=%H%x00%an%x00%ae", f"{base}..HEAD")
    if log.returncode != 0:
        return []
    out, unattributed = [], []
    done = lib.as_list(cfg.get("done_statuses"))

    def show(rev, rp):
        r = lib.git(root, "show", f"{rev}:{rp}")
        return r.stdout if r.returncode == 0 else ""

    for line in log.stdout.splitlines():
        sha, name, email = (line.split("\0") + ["", ""])[:3]
        parents = lib.git(root, "rev-list", "--parents", "-n", "1", sha).stdout.split()[1:]
        names = lib.git(root, "diff-tree", "--no-commit-id", "--name-only", "-r",
                        *(["-m"] if len(parents) > 1 else ["--root"]), sha).stdout.splitlines()
        mb = lib.git(root, "merge-base", "--octopus", *parents).stdout.strip() if len(parents) > 1 else ""
        for rp in sorted(set(p for p in names if may_be_owner_only(p))):
            new = show(sha, rp)
            olds = [show(p, rp) for p in parents] or [""]
            if len(parents) <= 1:
                why = owner_only_changes(rp, olds[0], new, "commit", done)
            elif all(new != o for o in olds):
                why = owner_only_changes(rp, olds[0], new, "commit", done)   # content no parent had
            else:
                # the merge keeps one side; it answers for any other side whose own change it drops
                # (a side that changed the file since the merge base), not for what it carries over
                at_base = show(mb, rp) if mb else None
                why = next((w for o in olds if o != new and o != at_base
                            for w in [owner_only_changes(rp, o, new, "commit", done)] if w), [])
            if not why or release_change(rp, lambda f, rev=sha: blob(root, f"{rev}:{f}")):
                continue
            if not owners:
                unattributed.append(f"{sha[:10]} {rp}")
            elif name.strip().lower() not in owners and email.strip().lower() not in owners:
                out.append(Finding("protected", "block", f"commit {sha[:10]} by {name} <{email}> changes {rp}, which is the owner's: {'; '.join(why)}",
                                   path=rp, override="the owner makes this change in their own commit (the `owner` key in charter/config.json names them)"))
    if unattributed:
        out.append(Finding("protected", "warn", f"charter/config.json names no owner, so {len(unattributed)} owner-only change(s) are unattributed: {', '.join(unattributed[:3])}",
                           path="charter/config.json", override="set `owner` to the git author name or email of the person who signs"))
    return out


def check_manifest(root: Path) -> list[Finding]:
    """The installed tooling must match the hashes the installer recorded in .charter/manifest.json."""
    mp = root / lib.TOOL_DIR / "manifest.json"
    if not mp.exists():
        return []
    try:
        files = json.loads(mp.read_text()).get("files", {})
    except json.JSONDecodeError:
        return [Finding("protected", "block", ".charter/manifest.json is not valid JSON", path=".charter/manifest.json")]
    out = []
    for rp, h in files.items():
        p = root / rp
        cur = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        if cur == h:
            continue
        gate_code = rp.startswith(lib.TOOL_DIR + "/")
        out.append(Finding("protected", "block" if gate_code else "warn",
                           f"{rp} {'is missing' if cur is None else 'differs from the hash in .charter/manifest.json'}", path=rp,
                           override="restore it with `charter-pkg upgrade --force`; an intended change is the owner's commit, with the new hash in the manifest"))
    return out


# ---------------------------------------------------------------- anchors (R10)

@dataclass
class AnchorReport:
    claims: int = 0
    anchored: int = 0
    admitted: int = 0
    unanchored: list[tuple[int, str]] = field(default_factory=list)
    unresolved: list[tuple[int, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.unanchored and not self.unresolved


# The admitted markers, by evidence class (docs/method.md § Evidence classes): reported is `reported in`,
# `operator report` (also tcv2's `operator_report`), `claimed by`, `outside this repository` and the
# scratch locations; inference is `inference`, `unverified`, `not verified`, `estimate` and `to be confirmed`.
ADMIT_RE = re.compile(r"\((?:unverified|reported in[^)]*|operator[ _-]report[^)]*|inference[^)]*|not verified|estimate[^)]*|to be confirmed|claim(?:ed)? by[^)]*|(?:in|on|from) the (?:test bed|clone|scratchpad|upstream clone)[^)]*|outside this repository[^)]*)\)", re.I)
EVIDENCE_REF_RE = re.compile(r"\bE-\d+\b")


def _anchors_in(root: Path, text: str, evidence_ids: set[str], issues: bool = False) -> tuple[int, list[str]]:
    """Count anchors in text; return (count of resolving anchors, list of unresolved)."""
    ok, bad = evidence_anchors(root, text)
    for m in EVIDENCE_REF_RE.finditer(text):
        (ok if m.group(0) in evidence_ids else bad).append(m.group(0))
    if issues:   # a pull request's `#123` / `owner/repo#123` points at an issue the reader can open
        ok.extend(ISSUE_RE.findall(text))
    return len(ok), bad


def check_anchors(root: Path, text: str, min_len: int = 40, issues: bool = False) -> AnchorReport:
    rep = AnchorReport()
    lines = text.splitlines()
    # evidence index ids defined in the document: lines starting with "- E-<n>" or "| E-<n>"
    evidence_ids = set()
    for line in lines:
        m = re.match(r"^\s*(?:[-*]|\|)\s*(E-\d+)\b", line)
        if m:
            evidence_ids.add(m.group(1))
    in_code, in_opinion = False, False
    para: list[tuple[int, str]] = []

    def flush():
        if not para:
            return
        joined = " ".join(t for _, t in para)
        first = para[0][0]
        is_claim = len(joined) >= min_len or re.search(r"\d", joined)
        if not is_claim:
            para.clear()
            return
        rep.claims += 1
        n_ok, bad = _anchors_in(root, joined, evidence_ids, issues)
        admitted = ADMIT_RE.search(joined) is not None
        if bad and not admitted:
            rep.unresolved.append((first, ", ".join(bad[:4])))
        if admitted:
            rep.admitted += 1
        elif n_ok:
            rep.anchored += 1
        else:
            rep.unanchored.append((first, joined[:90]))
        para.clear()

    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        if s.startswith("```") or s.startswith("~~~"):
            if not in_code and s.startswith("```") and i < len(lines) and lines[i].strip().startswith("$ "):
                pass
            in_code = not in_code
            flush()
            continue
        if in_code:
            continue
        if "<!-- charter: opinion -->" in s:
            in_opinion = True; flush(); continue
        if "<!-- charter: /opinion -->" in s:
            in_opinion = False; flush(); continue
        if in_opinion or s.startswith("<!--") or s.startswith("#") or not s:
            flush(); continue
        if re.match(r"^\|?\s*:?-{2,}", s):   # table separator
            flush(); continue
        if s.startswith("|") and i < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i].strip()):
            flush(); continue            # table header row
        if s.startswith("|") or s.startswith("- ") or s.startswith("* ") or re.match(r"^\d+\.\s", s):
            flush()
            para.append((i, s))
            flush()
            continue
        para.append((i, s))
    flush()
    return rep


# ---------------------------------------------------------------- staged / tree helpers

def usable_base(root: Path, base: str | None) -> str | None:
    """The commit the change set is measured from: `base`, else HEAD~1. None when it is not in this
    clone: an all-zero SHA (a push that created the branch), a SHA a force-push removed, or a root commit."""
    ref = base or "HEAD~1"
    if re.fullmatch(r"0+", ref):
        return None
    r = lib.git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if r.returncode != 0 or not r.stdout.strip():
        return None
    mb = lib.git(root, "merge-base", r.stdout.strip(), "HEAD")   # a PR base may have moved on since the branch
    return mb.stdout.strip() if mb.returncode == 0 and mb.stdout.strip() else r.stdout.strip()


def fallback_base(root: Path) -> tuple[str | None, str]:
    """Where to measure from when the given base is unusable (0.4.17): the merge base with the main line when that is
    behind HEAD; HEAD~1 when HEAD is on the main line but the checked-out branch is another one (a branch reset to
    main); (None, "") otherwise. The main line is looked up on the remote first: a CI runner building another branch
    has origin/main but no local main. A push to the main line itself, a detached HEAD, or no main line in the clone
    gets (None, ""): a force push to main may have rewritten more than its last commit."""
    head = lib.git(root, "rev-parse", "HEAD").stdout.strip()
    r = lib.git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    refs = ([r.stdout.strip()] if r.returncode == 0 and r.stdout.strip() else []) + ["origin/main", "origin/master", "main", "master"]
    lines = []
    for ref in dict.fromkeys(refs):
        if lib.git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode != 0:
            continue
        lines.append(ref.removeprefix("origin/"))
        mb = lib.git(root, "merge-base", ref, "HEAD").stdout.strip()
        if mb and mb != head:
            return mb, f"the merge base with {ref}"
    branch = lib.git(root, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    if not lines or not branch or branch in lines:
        return None, ""
    b = usable_base(root, None)
    return (b, "HEAD~1") if b else (None, "")


def changed_paths(root: Path, base: str | None) -> list[str] | None:
    """Paths changed from the merge base of `base` (default HEAD~1) and HEAD; None when the base is
    unusable, and the caller then checks every tracked path."""
    b = usable_base(root, base)
    if b is None:
        return None
    r = lib.git(root, "diff", "--name-only", "--diff-filter=ACMR", b, "HEAD")
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.splitlines() if p.strip()]


def base_text(root: Path, base: str, rp: str) -> str | None:
    """`rp` as it was at `base`, None when it did not exist there."""
    r = lib.git(root, "show", f"{base}:{rp}")
    return r.stdout if r.returncode == 0 else None


def unstaged_paths(root: Path) -> list[str]:
    """Tracked files whose working-tree content differs from the index."""
    r = lib.git(root, "diff", "--name-only")
    return [p for p in r.stdout.splitlines() if p.strip()]


def rename_sources(root: Path, base: str | None = None) -> dict[str, str]:
    """{new path: old path} for each file the change set renames: the index against HEAD when `base`
    is None, else `base` against HEAD. A `git mv` of a 4,955-line file into docs/history was measured
    as a new 4,955-line file and refused; before the move it was that size under its old name."""
    args = ["diff", "--name-status", "-M", "--diff-filter=R", "-z"] + (["--cached"] if base is None else [base, "HEAD"])
    r = lib.git(root, *args)
    if r.returncode != 0:
        return {}
    t = r.stdout.split("\0")
    out = {}
    i = 0
    while i + 2 < len(t):
        if t[i].startswith("R"):
            out[t[i + 2]] = t[i + 1]
            i += 3
        else:
            i += 2
    return out


def staged_paths(root: Path) -> list[str]:
    r = lib.git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [p for p in r.stdout.splitlines() if p.strip()]


def staged_text(root: Path, rp: str) -> str:
    r = lib.git(root, "show", f":{rp}")
    return r.stdout if r.returncode == 0 else ""


def head_text(root: Path, rp: str) -> str:
    r = lib.git(root, "show", f"HEAD:{rp}")
    return r.stdout if r.returncode == 0 else ""
