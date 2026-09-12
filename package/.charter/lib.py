"""Shared helpers for the charter tooling. Python 3 standard library only.

Everything in this file must work from a clean clone, inside a git worktree, and
without network access. It is imported by the hooks, the git hooks and the CLI.
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHARTER_DIR = "charter"
TOOL_DIR = ".charter"
STATE_DIR = ".charter/state"      # the 0.1.0 location; `charter setup` moves what it finds there
TASKETS_DIR = ".taskets"
LEGACY_FILE = "charter/legacy-taskets.txt"

# Statuses both engines treat as closed without being done (tele-claude project_tasket_reader.py:23-34).
TERMINAL_STATUSES = ("deleted", "superseded", "parked", "skipped", "realized", "deferred")
# Statuses of a unit still being planned: its acceptance criteria may change without a log line.
PLANNING_STATUSES = ("", "next", "later")

DEFAULT_CONFIG = {
    "version": "0.2.1",
    "track": "client",            # "client" | "prototype"
    "owner": "",                  # git author name or email allowed to commit owner-only changes; CI checks it
    "limits": {
        "file_lines": 800,        # rule 3: freeze-and-split threshold
        "governance_lines": 400,  # CLAUDE.md, rules, scope, decisions index
    },
    "exempt_from_size": ["*.lock", "*.min.*", "*.svg", "*.json", "*.csv", "*.txt"],
    "done_statuses": ["done"],
    "probes": {                   # re-run acceptance probes of units that close in a change set
        "at_commit": False, "in_ci": False, "timeout_s": 120,
    },
    # estimates for the ledger, USD per million tokens; keys are model-id prefixes (the longest match
    # wins), "default" for the rest; cache_write is the 5-minute TTL, cache_write_1h the 1-hour one
    "prices_usd_per_mtok": {
        "_source": "https://platform.claude.com/docs/en/about-claude/pricing, read 2026-09-11; estimates, update when Anthropic does",
        "default": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75, "cache_write_1h": 6.0},
        "claude-fable-5-1": {"input": 10.0, "output": 50.0, "cache_read": 0.25, "cache_write": 12.5, "cache_write_1h": 20.0},
        "claude-fable-5": {"input": 10.0, "output": 50.0, "cache_read": 1.0, "cache_write": 12.5, "cache_write_1h": 20.0},
        "claude-opus-5": {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_write": 6.25, "cache_write_1h": 10.0},
        "claude-opus-4-8": {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_write": 6.25, "cache_write_1h": 10.0},
        "claude-opus-4-7": {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_write": 6.25, "cache_write_1h": 10.0},
        "claude-opus-4-6": {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_write": 6.25, "cache_write_1h": 10.0},
        "claude-sonnet-5": {"input": 2.0, "output": 10.0, "cache_read": 0.2, "cache_write": 2.5, "cache_write_1h": 4.0},
        "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75, "cache_write_1h": 6.0},
        "claude-haiku-4-5": {"input": 1.0, "output": 5.0, "cache_read": 0.1, "cache_write": 1.25, "cache_write_1h": 2.0},
    },
}


# ---------------------------------------------------------------- repo & config

def repo_root(start: str | os.PathLike | None = None) -> Path:
    """Root of the git checkout that contains `start` (a worktree counts)."""
    start = Path(start or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    try:
        out = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                             capture_output=True, check=True).stdout
        return Path(os.fsdecode(out).strip())   # a path: decoded as the filesystem does, never raises
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start


def load_config(root: Path) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    p = artifact_root(root) / CHARTER_DIR / "config.json"
    if p.exists():
        try:
            user = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            raise SystemExit(f"charter/config.json is not valid JSON: {e}")
        for k, v in user.items():
            if k == "prices_usd_per_mtok" and isinstance(v, dict):
                # a project's rows override the package's; the 0.1.0 flat form is its "default" row
                cfg[k].update(v if any(isinstance(x, dict) for x in v.values()) else {"default": v})
            elif isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def owner_session() -> bool:
    """True when Claude Code (or the committing shell) was started with CHARTER_OWNER=1.
    Hook processes inherit Claude Code's environment; a Bash command's exports do not reach them."""
    return os.environ.get("CHARTER_OWNER", "") == "1"


def in_claude_code() -> bool:
    """True inside a process started by Claude Code (it sets CLAUDECODE=1 for its tools)."""
    return os.environ.get("CLAUDECODE", "") == "1"


def git(root: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    """Output decoded as UTF-8, undecodable bytes replaced: `git show` of a binary file must not raise."""
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, encoding="utf-8", errors="replace", check=check)


_GIT_DIRS: dict[tuple[str, str], Path | None] = {}


def _git_path(root: Path, which: str) -> Path | None:
    """Absolute `git rev-parse --git-dir` or `--git-common-dir` for the checkout at root."""
    key = (str(root), which)
    if key not in _GIT_DIRS:
        r = git(root, "rev-parse", "--path-format=absolute", which)
        if r.returncode != 0:   # git older than 2.31: the answer is relative to root
            r = git(root, "rev-parse", which)
        out = r.stdout.strip()
        _GIT_DIRS[key] = ((root / out).resolve() if out else None) if r.returncode == 0 else None
    return _GIT_DIRS[key]


def shared_state_dir(root: Path) -> Path:
    """The gate log and session records: in the git common directory, so every worktree of a
    repository writes to one place, the records outlive a removed worktree, and nothing commits them."""
    d = _git_path(root, "--git-common-dir")
    return d / "charter" if d else root / STATE_DIR


def local_state_dir(root: Path) -> Path:
    """The active unit and per-session scratch: in this worktree's own git directory."""
    d = _git_path(root, "--git-dir")
    return d / "charter" if d else root / STATE_DIR


# ---------------------------------------------------------------- the staged view

_VIEW: Path | None = None


def artifact_root(root: Path) -> Path:
    """Where the charter artifacts are read from: the tree, or the index while `index_view` is open."""
    return _VIEW if _VIEW is not None else root


@contextlib.contextmanager
def index_view(root: Path):
    """Read charter/ and .taskets/ as staged, so the pre-commit judges the commit, not the working tree."""
    global _VIEW
    tmp = Path(tempfile.mkdtemp(prefix="charter-index-"))
    try:
        # paths pass from one git command to the other as bytes, so no file name is ever decoded
        listed = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", CHARTER_DIR, TASKETS_DIR], capture_output=True).stdout
        if listed.strip(b"\0"):
            subprocess.run(["git", "-C", str(root), "checkout-index", "-f", "-z", "--stdin", f"--prefix={tmp}/"],
                           input=listed, capture_output=True)
        _VIEW = tmp
        yield tmp
    finally:
        _VIEW = None
        shutil.rmtree(tmp, ignore_errors=True)


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
    A `#` at the start of a value or after whitespace, outside quotes, starts a comment,
    as in YAML. Unknown keys are preserved verbatim, which is what the tasket parsers require."""
    m = _FM_RE.match(text)
    if not m:
        return {}, "", text
    raw = m.group(1)
    fields: dict = {}
    current_list_key = None
    blank: set[str] = set()
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if current_list_key and re.match(r"^\s+-\s+", line):
            fields[current_list_key].append(_scalar(strip_comment(line.split("-", 1)[1].strip())))
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = strip_comment(val.strip())
        if val == "":
            fields[key] = []
            current_list_key = key
            blank.add(key)
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            fields[key] = [_scalar(x.strip()) for x in inner.split(",")] if inner else []
        else:
            fields[key] = _scalar(val)
    for key in blank:   # `key:` with no list under it is empty, as YAML reads it, not an empty list
        if fields.get(key) == []:
            fields[key] = ""
    return fields, raw, text[m.end():]


def strip_comment(v: str) -> str:
    """Drop a trailing comment: `#` at the start or after whitespace, outside quotes. Quotes are
    honoured anywhere in the value, so a quoted `#` inside a `check:` command survives."""
    quote = None
    for i, ch in enumerate(v):
        prev = v[i - 1] if i else " "
        if quote:
            if ch == quote and not (quote == '"' and prev == "\\"):
                quote = None
        elif ch in "\"'" and (prev.isspace() or prev in "[,"):
            quote = ch
        elif ch == "#" and prev.isspace():
            return v[:i].rstrip()
    return v


def inline_comments(text: str) -> list[str]:
    """Frontmatter keys whose value carries a trailing comment. tcv2's reader keeps such comments
    as part of the value (~/Projects/tcv2/services/tasket_routing.py:707-732), so an engine can
    read `status: done  # x` as a status it does not know."""
    m = _FM_RE.match(text)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line[:1].isspace() or ":" not in line:
            continue
        key, _, val = line.partition(":")
        if strip_comment(val.strip()) != val.strip():
            out.append(key.strip())
    return out


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
    """Parse charter/scope.md (see `parse_scope`), adding "exists" and "path"."""
    p = artifact_root(root) / CHARTER_DIR / "scope.md"
    result = parse_scope(p.read_text(encoding="utf-8")) if p.exists() else parse_scope("")
    result.update(exists=p.exists(), path=p)
    return result


def _heading(t: str) -> str:
    return re.sub(r"[\s_-]+", " ", t.strip().lower())


def parse_scope(text: str) -> dict:
    """Items are `###` headings under `## In scope` and `## Out of scope` (hyphens, underscores and
    case are ignored, so `## Out-of-Scope` counts); each may carry a `paths:` line of globs. An item
    heading without an id (`### Invoicing`) is still read, keyed by its heading, so its paths are
    still gated. Returns {"in": {id: {...}}, "out": {...}, "assumptions": [...], "problems": [...]};
    "problems" lists what makes a gate fail open, in words for `charter check --scope`."""
    result: dict = {"in": {}, "out": {}, "assumptions": [], "problems": []}
    section, unknown, current = None, None, None
    for line in text.splitlines():
        h2 = re.match(r"^##\s+(.*)", line)
        if h2:
            t = _heading(h2.group(1))
            section = ("in" if t.startswith("in scope") else
                       "out" if t.startswith(("out of scope", "not in scope")) else
                       "assumptions" if t.startswith("assumption") else None)
            unknown = h2.group(1).strip() if section is None else None
            current = None
            continue
        h3 = re.match(r"^###\s+(.*)", line)
        if h3:
            current = None
            head = h3.group(1).strip()
            if section in ("in", "out"):
                m = re.match(r"([A-Za-z]+[-_]?\d+)\b\s*[—–:-]?\s*(.*)", head)
                current = m.group(1) if m else head
                result[section][current] = {"title": (m.group(2).strip() if m else head), "paths": [], "has_id": bool(m)}
            elif unknown is not None:
                result["problems"].append(f"`### {head}` sits under `## {unknown}`, which is not In scope, Out of scope or Assumptions; it is not read")
            continue
        if section == "assumptions" and line.strip().startswith("-"):
            result["assumptions"].append(line.strip()[1:].strip())
        pm = re.match(r"^\s*paths:\s*(.*)", line)
        if pm and current and section in ("in", "out"):
            val = pm.group(1).strip().strip("`")
            result[section][current]["paths"] = [x.strip().strip("`") for x in re.split(r"[,\s]+", val) if x.strip()]
    if text.strip() and not result["in"]:
        result["problems"].append("no item under `## In scope`; units have nothing to cite")
    for sec, label in (("in", "in-scope"), ("out", "out-of-scope")):
        for iid, item in result[sec].items():
            if not item["has_id"]:
                result["problems"].append(f"{label} item `### {iid}` has no id (write `### {'S' if sec == 'in' else 'X'}<n> — title`); "
                                          + ("its paths are gated under its heading" if sec == "out" else "units cannot cite it by a stable id"))
            if sec == "out" and not item["paths"]:
                result["problems"].append(f"out-of-scope item {iid} ({item['title']}) has no paths: line, so the scope gate refuses nothing for it")
    return result


def decisions(root: Path) -> dict[str, dict]:
    """charter/decisions/*.md → {id: fields+body}. id = filename stem unless `id:` set."""
    out = {}
    base = artifact_root(root)
    d = base / CHARTER_DIR / "decisions"
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.md")):
        if p.name.lower() in ("readme.md", "index.md"):
            continue
        fields, body = read_md(p)
        did = str(fields.get("id") or p.stem)
        fields["_path"] = rel(base, p)
        fields["_body"] = body
        fields.setdefault("status", "active")
        out[did] = fields
    return out


def change_requests(root: Path) -> dict[str, dict]:
    out = {}
    base = artifact_root(root)
    d = base / CHARTER_DIR / "changes"
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.md")):
        if p.name.lower() in ("readme.md", "index.md"):
            continue
        fields, body = read_md(p)
        cid = str(fields.get("id") or p.stem)
        fields["_path"] = rel(base, p)
        fields["_body"] = body
        fields.setdefault("status", "proposed")
        out[cid] = fields
    return out


def taskets(root: Path) -> dict[str, dict]:
    out = {}
    base = artifact_root(root)
    d = base / TASKETS_DIR
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.md")):
        fields, body = read_md(p)
        fields["_path"] = rel(base, p)
        fields["_body"] = body
        fields["_id"] = str(fields.get("id") or p.stem)
        out[fields["_id"]] = fields
    return out


def approved_changes(root: Path) -> dict[str, dict]:
    """Change requests that count as approved: status approved, with who and when recorded (R7)."""
    return {cid: c for cid, c in change_requests(root).items()
            if str(c.get("status")) == "approved" and c.get("approved_by") and c.get("approved_on")}


def legacy_taskets(root: Path) -> set[str]:
    """Ids listed in charter/legacy-taskets.txt: taskets the installer found before charter."""
    p = artifact_root(root) / LEGACY_FILE
    if not p.exists():
        return set()
    return {x for x in (line.split("#", 1)[0].strip() for line in p.read_text().splitlines()) if x}


def is_charter_unit(text: str) -> bool:
    """A tasket that took up the method: it cites a scope item or carries an acceptance section."""
    fields, _, body = split_frontmatter(text)
    return bool(fields.get("scope")) or bool(section(body, "Acceptance"))


def active_unit(root: Path) -> str | None:
    """CHARTER_UNIT from the environment (engines export it), else `charter unit start`'s choice."""
    env = os.environ.get("CHARTER_UNIT", "").strip()
    if env:
        return env
    p = local_state_dir(root) / "active"
    if p.exists():
        return p.read_text().strip() or None
    return None


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
    """Append one JSON line to log.jsonl in the shared state directory. Every gate and
    warning writes here; the log is how a warning earns promotion to a gate."""
    d = shared_state_dir(root)
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
    """PreToolUse: deny the tool call. Prints the JSON decision and exits 0; the reason reaches Claude."""
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


def is_binary(text: str) -> bool:
    """A NUL in the first 8,000 characters: the test git itself uses to call a file binary."""
    return "\x00" in text[:8000]


def line_count(text: str) -> int:
    """Lines in a text, counting a last line without a newline, as `count_lines` does for a file."""
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def count_lines(path: Path) -> int:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0
