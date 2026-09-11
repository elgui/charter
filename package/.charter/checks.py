"""The gate logic. Pure functions over repository state; no hook I/O here.

Every check returns a list of Finding. `level` is "block" or "warn". Callers
(hooks, git hooks, CI) decide what a block means in their context. A check that
cannot run because of a broken artifact returns a Finding with gate="error" and
level="warn": gates fail open and the log shows it.
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import lib

GOVERNANCE_FILES = ["CLAUDE.md", "AGENTS.md", "charter/scope.md"]
GOVERNANCE_GLOBS = [".claude/rules/*.md"]
MARKER_RE = re.compile(r"charter:([a-z0-9][a-z0-9._-]*)", re.I)
CHECKBOX_RE = re.compile(r"^\s*-\s*\[( |x|X)\]\s*(AC-\d+|[^\n]*)", re.M)
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
FILELINE_RE = re.compile(r"(?<![\w/.~-])((?:~/|/)?(?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_.\-]+\.[A-Za-z0-9]+):(\d+)(?:-(\d+))?")
URL_RE = re.compile(r"https?://[^\s)>\]]+")
PATH_RE = re.compile(r"(?<![\w/:.~-])((?:~/|/)?(?:\.?[A-Za-z0-9_.\-]+/)+[A-Za-z0-9_.\-]*|[A-Za-z0-9_\-]+\.(?:md|py|json|jsonl|ya?ml|toml|txt|sh|ts|js|csv|html))(?![\w/])")
DONE_CLAIM_RE = re.compile(
    r"\b(done|complete[d]?|finished|implemented|fixed|resolved|shipped|all tests pass(?:ed|ing)?|ready to merge)\b"
    r"|✅|\[x\]", re.I)


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
    approved = {cid: c for cid, c in lib.change_requests(root).items() if str(c.get("status")) == "approved"}
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
    cited = lib.as_list(unit.get("scope"))
    if not cited:
        if str(unit.get("status", "")) in lib.as_list(cfg.get("done_statuses")) + ["deleted", "superseded", "parked", "skipped", "realized", "deferred"]:
            return []
        return [Finding("scope", "warn", f"unit {unit['_id']} cites no scope item (scope: S<n> or a change id)", path=unit["_path"],
                        override="add `scope: <id>` naming an item in charter/scope.md or an approved change request")]
    known = set(sc["in"]) | {cid for cid, c in lib.change_requests(root).items() if str(c.get("status")) == "approved"}
    bad = [c for c in cited if c not in known]
    if bad:
        return [Finding("scope", "block", f"unit {unit['_id']} cites unknown scope id(s): {', '.join(bad)}", path=unit["_path"],
                        override="cite an existing in-scope item or an approved change request")]
    return []


# ---------------------------------------------------------------- size (R3)

def size_limit_for(root: Path, cfg: dict, rp: str) -> int | None:
    if lib.matches_any(rp, lib.as_list(cfg.get("exempt_from_size"))):
        return None
    if rp in GOVERNANCE_FILES or lib.matches_any(rp, GOVERNANCE_GLOBS) or rp.startswith("charter/decisions/") or rp.startswith("charter/changes/"):
        return int(cfg["limits"]["governance_lines"])
    return int(cfg["limits"]["file_lines"])


def split_unit_for(root: Path, rp: str) -> str | None:
    """Id of an open unit with kind: split whose perimeter covers rp."""
    for uid, u in lib.taskets(root).items():
        if str(u.get("kind", "")) == "split" and str(u.get("status", "")) not in ("done", "deleted", "superseded", "parked", "skipped", "realized", "deferred"):
            if lib.matches_any(rp, lib.as_list(u.get("perimeter"))):
                return uid
    return None


def check_size(root: Path, cfg: dict, rp: str, new_lines: int, old_lines: int) -> list[Finding]:
    limit = size_limit_for(root, cfg, rp)
    if limit is None:
        return []
    if new_lines > limit and new_lines > old_lines:
        su = split_unit_for(root, rp)
        if su:
            return [Finding("size", "warn", f"{rp} is over {limit} lines ({new_lines}); allowed because split unit {su} is open", path=rp)]
        verb = f"would grow to {new_lines} lines" if old_lines else f"is {new_lines} lines"
        return [Finding("size", "block", f"{rp} {verb}, over the {limit}-line limit; the file is frozen for growth",
                        path=rp, override=f"create a unit with `kind: split` and `perimeter: [{rp}]` and split the file, or reduce it below {limit} lines")]
    if new_lines > int(limit * 0.8) and new_lines > old_lines:
        return [Finding("size", "warn", f"{rp} is at {new_lines} lines, {limit} is the limit; plan a split", path=rp)]
    return []


# ---------------------------------------------------------------- done (R9)

def _resolves(root: Path, anchor_kind: str, value: str, extra: str = "") -> bool:
    if anchor_kind == "sha":
        return lib.git(root, "cat-file", "-e", f"{value}^{{commit}}").returncode == 0
    if anchor_kind == "fileline":
        p = _abs(root, value)
        if not p.is_file():
            return False
        n = int(extra)
        return 1 <= n <= max(1, lib.count_lines(p))
    if anchor_kind == "path":
        return _abs(root, value).exists()
    if anchor_kind == "url":
        return True
    return False


def _abs(root: Path, value: str) -> Path:
    """Repo-relative by default; `~/` and `/` paths resolve on this machine (a report written
    here is checked here; CI sees them as unresolved, which is the honest reading)."""
    if value.startswith("~/"):
        return Path(os.path.expanduser(value))
    if value.startswith("/"):
        return Path(value)
    return root / value


def evidence_anchors(root: Path, text: str) -> tuple[list[str], list[str]]:
    """(resolving, unresolved) anchors found in a text."""
    ok, bad = [], []
    for m in FILELINE_RE.finditer(text):
        (ok if _resolves(root, "fileline", m.group(1), m.group(2)) else bad).append(f"{m.group(1)}:{m.group(2)}")
    for m in SHA_RE.finditer(text):
        v = m.group(0)
        if re.fullmatch(r"\d+", v):
            continue
        (ok if _resolves(root, "sha", v) else bad).append(v)
    for m in URL_RE.finditer(text):
        ok.append(m.group(0))
    stripped = URL_RE.sub(" ", FILELINE_RE.sub(" ", text))
    for m in PATH_RE.finditer(stripped):
        cand = m.group(1).rstrip("/.")
        if "*" in cand or not cand or cand.startswith("-"):
            continue
        if _abs(root, cand).exists():
            ok.append(cand)
    for line in text.splitlines():
        if line.strip().startswith("$ ") or line.strip().startswith("`$ "):
            ok.append(line.strip()[:60])
    return ok, bad


def check_unit_done(root: Path, cfg: dict, unit_text: str, path: str) -> list[Finding]:
    """Given the full text a tasket would have after an edit, refuse `done` without evidence."""
    fields, _, body = lib.split_frontmatter(unit_text)
    status = str(fields.get("status", ""))
    if status not in lib.as_list(cfg.get("done_statuses")):
        return []
    out: list[Finding] = []
    acc = lib.section(body, "Acceptance")
    boxes = CHECKBOX_RE.findall(acc)
    if not boxes:
        out.append(Finding("done", "block", "status is done but there is no `## Acceptance` checklist", path=path,
                           override="add `## Acceptance` with `- [x] AC-n: ... — probe: <command>` lines, or keep the status open"))
    else:
        unchecked = [b for b in boxes if b[0] == " "]
        if unchecked:
            out.append(Finding("done", "block", f"status is done but {len(unchecked)} acceptance box(es) are unchecked", path=path,
                               override="run each probe, check the box, and cite the run under `## Evidence`; or keep the status open"))
    ev = lib.section(body, "Evidence")
    ok, bad = evidence_anchors(root, ev) if ev else ([], [])
    if not ev or not ok:
        out.append(Finding("done", "block", "status is done but `## Evidence` has no resolving anchor (commit SHA, path:line, URL or `$ command` run)", path=path,
                           override="add the commit SHA(s), the file:line of the change and the test run output under `## Evidence`"))
    if bad:
        out.append(Finding("done", "block", f"evidence anchors do not resolve: {', '.join(bad[:5])}", path=path,
                           override="fix the anchors so they point at commits and lines that exist"))
    return out


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
            r = subprocess.run(str(cmd), shell=True, cwd=str(root), capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            out.append(Finding("decisions", "warn", f"decision `{did}` check timed out: {cmd}", path=d["_path"]))
            continue
        if r.returncode != 0:
            tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]
            out.append(Finding("decisions", "block", f"decision `{did}` is contradicted: `{cmd}` exited {r.returncode} {tail[0][:120]}", path=d["_path"],
                               override=f"restore the invariant, or supersede the decision with a new record that names {did} in `supersedes:` and sets its status to superseded"))
    return out


# ---------------------------------------------------------------- perimeter (R4)

def check_perimeter(root: Path, cfg: dict, unit: dict | None, relpaths: list[str], at_commit: bool) -> list[Finding]:
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
        out.append(Finding("perimeter", level, f"{rp} is outside the perimeter of unit {unit['_id']} and has no note", path=rp,
                           override=f"add `- {rp}: <why>` under `## Outside perimeter` in {unit['_path']}, or widen `perimeter:`"))
    return out


# ---------------------------------------------------------------- memory (R8)

def check_memory(root: Path, cfg: dict, today: str) -> list[Finding]:
    out: list[Finding] = []
    for did, d in lib.decisions(root).items():
        if str(d.get("status", "active")) != "active":
            continue
        if not lib.section(d.get("_body", ""), "Because") and not d.get("because"):
            out.append(Finding("memory", "warn", f"decision `{did}` records no case that justified it (`## Because`)", path=d["_path"]))
        exp = str(d.get("expires", "")).strip()
        if not exp:
            out.append(Finding("memory", "warn", f"decision `{did}` has no `expires:` (a date or a condition)", path=d["_path"]))
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", exp) and exp < today:
            out.append(Finding("memory", "warn", f"decision `{did}` expired on {exp}; renew it or retire it", path=d["_path"]))
        if str(d.get("kind", "")) == "lesson" and not d.get("owner"):
            out.append(Finding("memory", "warn", f"lesson `{did}` has no owner", path=d["_path"]))
    return out


# ---------------------------------------------------------------- change requests (R7)

def check_changes(root: Path) -> list[Finding]:
    out: list[Finding] = []
    for cid, c in lib.change_requests(root).items():
        if str(c.get("status")) == "approved" and not (c.get("approved_by") and c.get("approved_on")):
            out.append(Finding("scope", "block", f"change request `{cid}` is approved without `approved_by:` and `approved_on:`", path=c["_path"],
                               override="only the owner approves; record who and when"))
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


ADMIT_RE = re.compile(r"\((?:unverified|reported in[^)]*|not verified|estimate[^)]*|to be confirmed|claim(?:ed)? by[^)]*|(?:in|on|from) the (?:test bed|clone|scratchpad|upstream clone)[^)]*|outside this repository[^)]*)\)", re.I)
EVIDENCE_REF_RE = re.compile(r"\bE-\d+\b")


def _anchors_in(root: Path, text: str, evidence_ids: set[str]) -> tuple[int, list[str]]:
    """Count anchors in text; return (count of resolving anchors, list of unresolved)."""
    ok, bad = evidence_anchors(root, text)
    for m in EVIDENCE_REF_RE.finditer(text):
        (ok if m.group(0) in evidence_ids else bad).append(m.group(0))
    return len(ok), bad


def check_anchors(root: Path, text: str, min_len: int = 40) -> AnchorReport:
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
        n_ok, bad = _anchors_in(root, joined, evidence_ids)
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

def changed_paths(root: Path, base: str | None) -> list[str]:
    """Paths changed between `base` and HEAD (default HEAD~1). Empty when there is no parent."""
    if base:
        r = lib.git(root, "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD")
        if r.returncode != 0:
            r = lib.git(root, "diff", "--name-only", "--diff-filter=ACMR", base, "HEAD")
    else:
        r = lib.git(root, "diff", "--name-only", "--diff-filter=ACMR", "HEAD~1", "HEAD")
    if r.returncode != 0:
        return []
    return [p for p in r.stdout.splitlines() if p.strip()]


def staged_paths(root: Path) -> list[str]:
    r = lib.git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [p for p in r.stdout.splitlines() if p.strip()]


def staged_text(root: Path, rp: str) -> str:
    r = lib.git(root, "show", f":{rp}")
    return r.stdout if r.returncode == 0 else ""


def head_text(root: Path, rp: str) -> str:
    r = lib.git(root, "show", f"HEAD:{rp}")
    return r.stdout if r.returncode == 0 else ""


def head_status_of_unit(root: Path, rp: str) -> str:
    fields, _, _ = lib.split_frontmatter(head_text(root, rp))
    return str(fields.get("status", ""))
