"""charter-pkg instructions: the instruction files a Claude Code session reads in a project, and the lines in them
that overlap a charter rule.

Charter's rules reach a session as one more instruction file (`.claude/rules/charter.md`). Claude Code concatenates
every instruction file it loads and does not rank them: "if a user rule and a project rule conflict, Claude may follow
either one" (https://code.claude.com/docs/en/memory, "User-level rules"). So a line elsewhere that says the opposite of
a charter rule, or says the same thing another way, decides what a session does as much as charter does. This module
lists those lines for the owner to read; it does not judge them, because an overlap is often an agreement.

Read-only. Python 3 standard library only. Files outside the project are read only when named (`extra`): the survey
stays independent of the home directory (`SurveyOnAnotherMachine` in tests/test_migration.py), and the caller that
knows the machine (the CharterAdmin skill, the owner) passes `~/.claude/CLAUDE.md` and `~/.claude/rules/*.md`.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# The files Claude Code loads from a project (https://code.claude.com/docs/en/memory, "Choose where to put CLAUDE.md
# files", "Organize rules with .claude/rules/", "AGENTS.md"). AGENTS.md is read only where no CLAUDE.md,
# .claude/CLAUDE.md or CLAUDE.local.md exists; other agents (Codex, pi) read it in any case, so it is scanned too.
NAMES = ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md")
IMPORT_HOPS = 4   # "a maximum depth of four hops" (same page, "Import additional files")
OWN = (".claude/rules/charter.md",)   # charter's own rules, which every other line is compared with
SECTION_BEGIN, SECTION_END = "<!-- charter-section:begin -->", "<!-- charter-section:end -->"   # charter's part of AGENTS.md

# A line overlaps a charter rule when it names the same subject as an instruction: the subject's pattern matches and
# the line is phrased as a rule (the topic's phrasing pattern, None for a subject that is a rule wherever it is named). `needle` is a phrase of the charter rule it meets, looked up in the
# package's rules file at run time so the cited line follows the file.
IMPERATIVE = re.compile(r"(?i)\b(always|never|must|mandatory|required|only|do not|don't|before|without|instead|"
                        r"important|forbidden|refuse|ask|confirm|wait for)\b")
# deploy and production are named in descriptions as often as in rules; there the line must forbid or require
STRONG = re.compile(r"(?i)\b(always|never|must|mandatory|do not|don't|without|forbidden|refuse|ask|confirm|wait for)\b")
TOPICS = [
    ("owner-switch", "the owner switch or bypassing git hooks", re.compile(r"CHARTER_OWNER|--no-verify"), None,
     "Setting `CHARTER_OWNER` anywhere"),
    ("root", "root, sudo or permissions", re.compile(r"(?i)\bsudo\b|\bas root\b|\broot access\b|\bchmod\b|\bwiden\w* (a |the )?permissions?\b"), STRONG,
     "widening a permission"),
    ("hand-over", "what is handed to the owner to run, and how", re.compile(
        r"(?i)copy-?past|\bpaste\b|\bhand(ed|s)? (it |them |this )?(over|back|to the (user|owner))|\bone line\b|`! "), IMPERATIVE,
     "Give the owner that line verbatim"),
    ("ask-first", "acting only after the owner's word", re.compile(
        r"(?i)\b(ask|confirm|confirmation|approval|approve)\b[^.]{0,80}\bbefore\b|\bwithout (asking|approval|confirmation)\b|"
        r"\bwait for (the user'?s? |explicit |the owner'?s? )?(approval|confirmation|go-ahead|word)"), IMPERATIVE,
     "Commitments are the owner's alone"),
    ("git-mainline", "committing, pushing or merging", re.compile(
        r"(?i)\bgit (commit|push|merge)\b|\bgh pr merge\b|\bauto-?merge|\b(commit|push|merg)\w*\b[^.]{0,60}\b(main|master)\b|"
        r"\bpush(es|ing)?\b[^.]{0,30}\b(after|every|each) commit"), IMPERATIVE,
     "merging into main"),
    ("deploy", "deploying or touching production", re.compile(
        r"(?i)\b(never|always|must|don't|do not|only)\b[^.]{0,40}\b(deploy\w*|push\w* to (prod|production))\b|"
        r"\bdeploy\w*\b[^.]{0,40}\b(without|only after|after (every|each)|automatically)\b"), None,
     "deployment, production data or schema"),
    ("done", "closing work as done", re.compile(
        r"(?i)\bstatus:\s*done\b|\bmark\w* (it |them |as |the \w+ )*(as )?done\b|\bclos(e|ing) (the |a )?(tasket|unit|story|ticket)"), IMPERATIVE,
     "is refused without"),
    ("decisions", "where decisions are written", re.compile(r"(?i)\b(ADRs?|architecture decisions?|decision records?|decisions? log)\b"), IMPERATIVE,
     "Do not put it in `CLAUDE.md`"),
    ("memory", "what goes into memory", re.compile(r"(?i)auto-?memory|\bMEMORY\.md\b|\bremember\b"), IMPERATIVE,
     "Personal auto-memory is for your own habits"),
    ("git-hooks", "git hooks", re.compile(r"(?i)\bpre-commit\b|core\.hooksPath|\bgit hooks?\b|\bhusky\b|\blefthook\b"), IMPERATIVE,
     "If the session banner says the git hook is not active"),
    ("subagents", "subagents", re.compile(r"(?i)\bsub-?agents?\b|\bparallel agents\b"), IMPERATIVE,
     "Subagents read; the parent writes"),
]
# `@path` outside code; a path starts with `~/`, `/`, `.` or a word character and runs to the next blank
IMPORT_RE = re.compile(r"(?<![\w`@])@((?:~/|/|\.{1,2}/)?[\w.\-]+(?:/[\w.\-]+)*)")


def rule_lines(rules: Path) -> dict[str, tuple[int, str]]:
    """topic id -> (line, text) of the charter rule it meets, in the package's rules file."""
    text = rules.read_text().splitlines()
    out = {}
    for tid, _, _, _, needle in TOPICS:
        for i, line in enumerate(text, 1):
            if needle in line:
                out[tid] = (i, line.strip().lstrip("- ").strip())
                break
    return out


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))


def _show(root: Path, ref: str, path: str) -> str | None:
    r = _git(root, "show", f"{ref}:{path}")
    return r.stdout if r.returncode == 0 else None


def imports(text: str) -> list[str]:
    """The `@path` imports of an instruction file. Fenced blocks and code spans are skipped, as Claude Code does."""
    out, fence = [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = not fence
            continue
        if fence:
            continue
        out += IMPORT_RE.findall(re.sub(r"`[^`]*`", " ", line))
    return [p for p in out if "/" in p or p.endswith(".md")]


def project_files(root: Path, ref: str, paths: list[str]) -> list[dict]:
    """The project's instruction files: tracked ones read at `ref`, untracked CLAUDE.local.md read from the checkout."""
    found = [p for p in paths if p.rsplit("/", 1)[-1] in NAMES
             or (p.startswith(".claude/rules/") and p.endswith(".md"))]
    found = [p for p in found if p not in OWN and not p.startswith((".charter/", "charter/templates/", "node_modules/"))
             and "/node_modules/" not in p]
    out = []
    for p in sorted(found):
        t = _show(root, ref, p)
        if t is not None:
            try:
                same = (root / p).read_text(errors="replace") == t
            except OSError:
                same = False
            out.append({"path": p, "text": t, "where": "project", "how": how_loaded(p), "same": same})
    for p in sorted(x for x in _untracked_local(root) if x not in found):
        try:
            out.append({"path": p, "text": (root / p).read_text(errors="replace"), "where": "checkout", "how": how_loaded(p), "same": True})
        except OSError:
            pass
    return out


def _untracked_local(root: Path) -> list[str]:
    r = _git(root, "ls-files", "--others", "--exclude-standard", "--ignored", "--", "CLAUDE.local.md", "*/CLAUDE.local.md")
    r2 = _git(root, "ls-files", "--others", "--exclude-standard", "--", "CLAUDE.local.md", "*/CLAUDE.local.md")
    return sorted({x for x in (r.stdout + r2.stdout).splitlines() if x.strip()})


def how_loaded(p: str) -> str:
    if p.startswith(".claude/rules/"):
        return "at launch, or when a file it names under `paths:` is read"
    if "/" not in p or p == ".claude/CLAUDE.md":
        return ("at launch, only when the project has no CLAUDE.md (Claude Code); always by other agents"
                if p == "AGENTS.md" else "at launch")
    return "when a file under its directory is first read"


def follow_imports(root: Path, ref: str, files: list[dict], tracked: set[str]) -> list[dict]:
    """Add the files the instruction files import, up to four hops. A project path is read at `ref`; a path outside
    the project is read from this machine, and only when it is named by a file already read."""
    seen = {f["path"] for f in files} | {f.get("abs", "") for f in files}
    queue = [(f, 0) for f in files]
    out = list(files)
    while queue:
        f, hop = queue.pop(0)
        if hop >= IMPORT_HOPS:
            continue
        base = (root / f["path"]).parent if f["where"] in ("project", "checkout") else Path(f["abs"]).parent
        for imp in imports(f["text"]):
            target = Path(os.path.expanduser(imp)) if imp.startswith("~/") else Path(imp) if imp.startswith("/") else base / imp
            target = Path(os.path.normpath(target))
            try:
                rel = target.relative_to(root).as_posix()
            except ValueError:
                rel = None
            if rel is not None and rel in tracked:
                if rel in seen:
                    continue
                t = _show(root, ref, rel)
                if t is None:
                    continue
                try:
                    same = (root / rel).read_text(errors="replace") == t
                except OSError:
                    same = False
                nf = {"path": rel, "text": t, "where": "project", "how": f"through an import in {f['path']}", "same": same}
            else:
                key = str(target)
                if key in seen or not target.is_file():
                    continue
                try:
                    t = target.read_text(errors="replace")
                except OSError:
                    continue
                nf = {"path": key, "abs": key, "text": t, "where": "machine", "how": f"through an import in {f['path']}"}
            seen.add(nf["path"])
            out.append(nf)
            queue.append((nf, hop + 1))
    return out


def extra_files(paths: list[str]) -> list[dict]:
    out = []
    for p in paths:
        ap = Path(os.path.expanduser(p)).resolve()
        if ap.is_file():
            out.append({"path": str(ap), "abs": str(ap), "text": ap.read_text(errors="replace"), "where": "machine",
                        "how": "as named with --instructions"})
    return out


def scan(f: dict, rules: dict[str, tuple[int, str]]) -> list[dict]:
    """The lines of one file that overlap a charter rule: the first line per section and topic, with a count."""
    hits: dict[tuple[str, str], dict] = {}
    section, fence, in_charter = "(top)", False, False
    for i, line in enumerate(f["text"].splitlines(), 1):
        s = line.strip()
        if s == SECTION_BEGIN:
            in_charter = True
        if s == SECTION_END:
            in_charter = False
            continue
        if in_charter:
            continue
        if s.startswith("```") or s.startswith("~~~"):
            fence = not fence
            continue
        if fence or not s:
            continue
        if s.startswith("#"):
            section = s.lstrip("#").strip()
            continue
        for tid, label, pat, phrasing, _ in TOPICS:
            if tid not in rules or not pat.search(s):
                continue
            if phrasing is not None and not phrasing.search(s):
                continue
            k = (section, tid)
            if k in hits:
                hits[k]["more"] += 1
                continue
            hits[k] = {"path": f["path"], "where": f["where"], "same": f.get("same", True), "line": i, "section": section, "topic": tid, "label": label,
                       "text": s[:160], "more": 0, "rule_line": rules[tid][0], "rule": rules[tid][1][:160]}
    return sorted(hits.values(), key=lambda h: h["line"])


def review(root: Path, ref: str, paths: list[str], rules_file: Path, extra: list[str] = ()) -> dict:
    """The instruction files and their overlaps with charter's rules. `rules_file` is the package's rules file."""
    rules = rule_lines(rules_file)
    files = follow_imports(root, ref, project_files(root, ref, paths) + extra_files(list(extra)), set(paths))
    overlaps = [h for f in files for h in scan(f, rules)]
    return {"rules_file": str(rules_file), "files": [{k: f[k] for k in ("path", "where", "how")} | {"lines": f["text"].count("\n"),
                                                     "same": f.get("same", True)} for f in files],
            "extra_named": list(extra), "overlaps": overlaps}
