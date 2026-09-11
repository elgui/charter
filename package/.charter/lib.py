"""Shared helpers for the charter tooling. Python 3 standard library only.

Everything in this file must work from a clean clone, inside a git worktree, and
without network access. It is imported by the hooks, the git hooks and the CLI.
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CHARTER_DIR = "charter"
TOOL_DIR = ".charter"
STATE_DIR = ".charter/state"
TASKETS_DIR = ".taskets"

DEFAULT_CONFIG = {
    "version": "0.1.0",
    "track": "client",            # "client" | "prototype"
    "owner": "",                  # git author name that approves change requests
    "limits": {
        "file_lines": 800,        # rule 3: freeze-and-split threshold
        "governance_lines": 400,  # CLAUDE.md, rules, scope, decisions index
    },
    "exempt_from_size": ["*.lock", "*.min.*", "*.svg", "*.json", "*.csv", "*.txt"],
    "done_statuses": ["done"],
    "prices_usd_per_mtok": {      # estimates for the ledger; update when Anthropic does
        "input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75
    },
}


# ---------------------------------------------------------------- repo & config

def repo_root(start: str | os.PathLike | None = None) -> Path:
    """Root of the git checkout that contains `start` (a worktree counts)."""
    start = Path(start or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    try:
        out = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start


def load_config(root: Path) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    p = root / CHARTER_DIR / "config.json"
    if p.exists():
        try:
            user = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            raise SystemExit(f"charter/config.json is not valid JSON: {e}")
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def git(root: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=check)


def rel(root: Path, path: str | os.PathLike) -> str:
    """Path relative to the repo root, forward slashes; absolute if outside."""
    p = Path(path)
    if not p.is_absolute():
        p = (root / p)
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def inside(root: Path, path: str | os.PathLike) -> bool:
    return not Path(rel(root, path)).is_absolute()


def matches_any(relpath: str, globs: list[str]) -> bool:
    for g in globs:
        if fnmatch.fnmatch(relpath, g) or fnmatch.fnmatch("/" + relpath, "/" + g):
            return True
        # allow "dir/**" to match "dir/x" and "dir/a/b"
        if g.endswith("/**") and (relpath == g[:-3] or relpath.startswith(g[:-3] + "/")):
            return True
    return False


# ---------------------------------------------------------------- frontmatter

_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)


def split_frontmatter(text: str) -> tuple[dict, str, str]:
    """Return (fields, raw_frontmatter, body). Flat `key: value` and simple
    `key: [a, b]` / `key:\n  - a` lists are parsed; anything else is kept as a string.
    Unknown keys are preserved verbatim, which is what the tasket parsers require."""
    m = _FM_RE.match(text)
    if not m:
        return {}, "", text
    raw = m.group(1)
    fields: dict = {}
    current_list_key = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if current_list_key and re.match(r"^\s+-\s+", line):
            fields[current_list_key].append(_scalar(line.split("-", 1)[1].strip()))
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "":
            fields[key] = []
            current_list_key = key
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            fields[key] = [_scalar(x.strip()) for x in inner.split(",")] if inner else []
        else:
            fields[key] = _scalar(val)
    return fields, raw, text[m.end():]


def _scalar(v: str):
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def read_md(path: Path) -> tuple[dict, str]:
    fields, _, body = split_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    return fields, body


def as_list(v) -> list[str]:
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return [x.strip() for x in str(v).split(",") if x.strip()]


# ---------------------------------------------------------------- artifacts

def scope(root: Path) -> dict:
    """Parse charter/scope.md. Items are headings `### S1 — title` (in scope) under
    `## In scope`, `## Out of scope`, `## Assumptions`; each item may carry a
    `paths:` line listing globs. Returns {"in": {id: {...}}, "out": {...}, "assumptions": [...], "text": str}"""
    p = root / CHARTER_DIR / "scope.md"
    result = {"in": {}, "out": {}, "assumptions": [], "exists": p.exists(), "path": p}
    if not p.exists():
        return result
    section = None
    current = None
    for line in p.read_text(encoding="utf-8").splitlines():
        h2 = re.match(r"^##\s+(.*)", line)
        if h2 and not line.startswith("###"):
            t = h2.group(1).strip().lower()
            section = "in" if t.startswith("in scope") else "out" if t.startswith("out of scope") else \
                "assumptions" if t.startswith("assumption") else None
            current = None
            continue
        h3 = re.match(r"^###\s+([A-Za-z]+[-_]?\d+)\b\s*[—:-]?\s*(.*)", line)
        if h3 and section in ("in", "out"):
            current = h3.group(1)
            result[section][current] = {"title": h3.group(2).strip(), "paths": []}
            continue
        if section == "assumptions" and line.strip().startswith("-"):
            result["assumptions"].append(line.strip()[1:].strip())
        pm = re.match(r"^\s*paths:\s*(.*)", line)
        if pm and current and section in ("in", "out"):
            val = pm.group(1).strip().strip("`")
            result[section][current]["paths"] = [x.strip().strip("`") for x in re.split(r"[,\s]+", val) if x.strip()]
    return result


def decisions(root: Path) -> dict[str, dict]:
    """charter/decisions/*.md → {id: fields+body}. id = filename stem unless `id:` set."""
    out = {}
    d = root / CHARTER_DIR / "decisions"
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.md")):
        if p.name.lower() in ("readme.md", "index.md"):
            continue
        fields, body = read_md(p)
        did = str(fields.get("id") or p.stem)
        fields["_path"] = rel(root, p)
        fields["_body"] = body
        fields.setdefault("status", "active")
        out[did] = fields
    return out


def change_requests(root: Path) -> dict[str, dict]:
    out = {}
    d = root / CHARTER_DIR / "changes"
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.md")):
        if p.name.lower() in ("readme.md", "index.md"):
            continue
        fields, body = read_md(p)
        cid = str(fields.get("id") or p.stem)
        fields["_path"] = rel(root, p)
        fields["_body"] = body
        fields.setdefault("status", "proposed")
        out[cid] = fields
    return out


def taskets(root: Path) -> dict[str, dict]:
    out = {}
    d = root / TASKETS_DIR
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.md")):
        fields, body = read_md(p)
        fields["_path"] = rel(root, p)
        fields["_body"] = body
        fields["_id"] = str(fields.get("id") or p.stem)
        out[fields["_id"]] = fields
    return out


def active_unit(root: Path) -> str | None:
    p = root / STATE_DIR / "active"
    if p.exists():
        v = p.read_text().strip()
        return v or None
    return os.environ.get("CHARTER_UNIT") or None


def section(body: str, title: str) -> str:
    """Text of the markdown section whose heading (any level) starts with `title`, case-insensitive."""
    lines = body.splitlines()
    out, level, on = [], None, False
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            if on and len(m.group(1)) <= level:
                break
            if m.group(2).strip().lower().startswith(title.lower()):
                on, level = True, len(m.group(1))
                continue
        if on:
            out.append(line)
    return "\n".join(out).strip()


# ---------------------------------------------------------------- log

def log_event(root: Path, kind: str, gate: str, decision: str, detail: str, **extra) -> None:
    """Append one JSON line to .charter/state/log.jsonl. Every gate and warning
    writes here; the log is how a warning earns promotion to a gate."""
    d = root / STATE_DIR
    try:
        d.mkdir(parents=True, exist_ok=True)
        rec = {"ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
               "kind": kind, "gate": gate, "decision": decision, "detail": detail}
        rec.update(extra)
        with (d / "log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------- hook I/O

def read_hook_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def deny(reason: str) -> None:
    """PreToolUse: deny the tool call. Exit 2 with stderr is what Claude sees."""
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)


def allow_with_context(event: str, context: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))
    sys.exit(0)


def block_stop(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def count_lines(path: Path) -> int:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0
