"""Shared helpers for the charter tooling. Python 3 standard library only.

Everything in this file must work from a clean clone, inside a git worktree, and
without network access. It is imported by the hooks, the git hooks and the CLI.
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import fnmatch
import glob
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
    "version": "0.4.13",
    "track": "client",            # "client" | "prototype"
    "owner": "",                  # git author name or email allowed to commit owner-only changes; CI checks it
    "limits": {
        "file_lines": 800,        # rule 3: freeze-and-split threshold
        "governance_lines": 400,  # CLAUDE.md, rules, scope, decisions index
        "governance_bytes": 32768,  # the same files, in bytes: one 40,000-character line is 1 line
        "growth_slack_lines": 0,  # lines one change may add to a non-governance file over its limit (a warning)
    },
    # the governance set (globs); decisions and change requests are always governance
    "governance_files": ["CLAUDE.md", "AGENTS.md", "charter/scope.md", ".claude/rules/*.md"],
    # owner-named files judged against their own budget: {path, lines and/or bytes, because, expires}
    "size_exceptions": [],
    "exempt_from_size": ["*.lock", "*.min.*", "*.svg", "*.json", "*.csv", "*.txt"],
    # the road a project without a devis may be on (rails.py); off while the file does not exist
    "rails": {"required": False, "keys": ["rail", "roadmap"]},
    "done_statuses": ["done"],
    "probes": {                   # re-run acceptance probes of units that close in a change set
        "at_commit": False, "in_ci": False, "timeout_s": 120,
        "base_must_fail": False,  # a probe passing before the unit's work: a warning, or refused when true
    },
    # done also needs a `review:` evidence line naming an independent verdict (off by default)
    "review": {"required": False},
    # the continuous chain (chain.py): the sessions' model and effort, the window the budget is a share of
    # (0: 1M for a [1m] model, else 200k), the hand-over line and the hard cap in percent, the launcher;
    # the review at the end of each group (chain_groups.py): auto (codex if on PATH) | codex | off | a command
    # template with {base} and {out}, Codex's reasoning effort, and how long a review may run; how the owner is told
    # that the chain waits on them, halted or ended: auto (a macOS notification) | off, and a command template with
    # {chain}, {project}, {title} and {text}; the review of the owner's acts at a wait (owner_acts.py): auto (codex if
    # on PATH) | codex | off | a command template with {prompt}, {schema} and {out}, its effort and how long it may run
    "chain": {"model": "opus[1m]", "effort": "high", "window_tokens": 0, "wrap_pct": 25, "cap_pct": 30,
              "max_sessions": 12, "launcher": "auto", "review": "auto", "review_effort": "high", "review_timeout_s": 1800,
              "notify": "auto", "notify_command": "",
              "owner_review": "auto", "owner_review_effort": "medium", "owner_review_timeout_s": 300},
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
    p = artifact_root(root) / CHARTER_DIR / "config.json"
    if not p.exists():
        return config_from({})
    try:
        user = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        cfg = config_from({})
        cfg[PROBLEMS] = [f"not valid JSON ({e}); every setting is at its default, track client"]
        return cfg
    if not isinstance(user, dict):
        cfg = config_from({})
        cfg[PROBLEMS] = ["is not a JSON object; every setting is at its default, track client"]
        return cfg
    return config_from(user)


TRACKS = ("client", "prototype")
PRICE_FIELDS = ("input", "output", "cache_read", "cache_write", "cache_write_1h")
PROBLEMS = "_problems"   # set by config_from: what in the project's config.json was not applied, in words
# the type each setting must have; a dict names the keys a section may hold
CONFIG_SCHEMA = {
    "version": str, "track": str, "owner": (str, list),
    "limits": {"file_lines": int, "governance_lines": int, "governance_bytes": int, "growth_slack_lines": int},
    "governance_files": list, "size_exceptions": list, "exempt_from_size": list,
    "rails": {"required": bool, "keys": list},
    "done_statuses": list,
    "probes": {"at_commit": bool, "in_ci": bool, "timeout_s": int, "base_must_fail": bool},
    "review": {"required": bool},
    "chain": {"model": str, "effort": str, "window_tokens": int, "wrap_pct": int, "cap_pct": int, "max_sessions": int, "launcher": str,
              "review": str, "review_effort": str, "review_timeout_s": int, "notify": str, "notify_command": str,
              "owner_review": str, "owner_review_effort": str, "owner_review_timeout_s": int},
    "prices_usd_per_mtok": dict,
}


def _typed(v, t) -> bool:
    ts = t if isinstance(t, tuple) else (t,)
    # JSON true is a Python bool, which is also an int: a limit of `true` is a mistake, not 1
    return isinstance(v, ts) and not (isinstance(v, bool) and bool not in ts)


def _near(k: str, known) -> str:
    import difflib
    m = difflib.get_close_matches(k, list(known), n=1)
    return f" (did you mean `{m[0]}`?)" if m else ""


def config_from(user: dict) -> dict:
    """DEFAULT_CONFIG with a project's charter/config.json laid over it. What cannot be applied (an
    unknown key, a value of the wrong type, an unknown track) is left at its default, except an unknown
    track, which becomes client, the stricter one; each is listed under PROBLEMS, which `charter check`
    refuses (a misspelled opt-in must not switch a gate off in silence)."""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    problems: list[str] = []
    for k, v in user.items():
        t = CONFIG_SCHEMA.get(k)
        if t is None:
            problems.append(f"unknown key `{k}`{_near(k, CONFIG_SCHEMA)}; ignored")
        elif k == "prices_usd_per_mtok":
            if not isinstance(v, dict):
                problems.append("`prices_usd_per_mtok` is not an object; ignored")
                continue
            # a project's rows override the package's; the 0.1.0 flat form is its "default" row
            rows = v if any(isinstance(x, dict) for x in v.values()) else {"default": v}
            for m, row in rows.items():
                if m == "_source":
                    cfg[k][m] = row
                elif not isinstance(row, dict) or any(f not in PRICE_FIELDS or not _typed(x, (int, float)) for f, x in row.items()):
                    problems.append(f"`prices_usd_per_mtok.{m}` is not a row of {', '.join(PRICE_FIELDS)} numbers; ignored")
                else:
                    cfg[k][m] = row
        elif isinstance(t, dict):
            if not isinstance(v, dict):
                problems.append(f"`{k}` is not an object; left at its default")
                continue
            for sk, sv in v.items():
                if sk not in t:
                    problems.append(f"unknown key `{k}.{sk}`{_near(sk, t)}; ignored")
                elif not _typed(sv, t[sk]):
                    problems.append(f"`{k}.{sk}` is {json.dumps(sv)}, not a {t[sk].__name__}; left at {json.dumps(cfg[k][sk])}")
                else:
                    cfg[k][sk] = sv
        elif not _typed(v, t):
            problems.append(f"`{k}` is {json.dumps(v)}, of the wrong type; left at {json.dumps(cfg[k])}")
        elif k == "track" and v not in TRACKS:
            problems.append(f"`track` is {json.dumps(v)}, not one of {', '.join(TRACKS)}{_near(v, TRACKS)}; read as client")
            cfg[k] = "client"
        else:
            cfg[k] = v
    cfg[PROBLEMS] = problems
    return cfg


OPT_INS = (("rails", "required"), ("probes", "at_commit"), ("probes", "in_ci"), ("probes", "base_must_fail"), ("review", "required"))


def opt_ins(cfg: dict) -> list[str]:
    """The opt-in settings that are on, as `section.key`: printed by the session banner and every check."""
    return [f"{s}.{k}" for s, k in OPT_INS if (cfg.get(s) or {}).get(k) is True]


def config_line(cfg: dict) -> str:
    on = opt_ins(cfg)
    return f"track {cfg.get('track')}, opt-ins: {', '.join(on) if on else 'none'}"


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


def commit_command(root: Path, paths: list[str], message: str) -> str:
    """`git commit` of exactly these paths. The pathspec after `--` commits them whatever else is staged
    or untracked; `git -C` makes it right from any directory."""
    import shlex
    return (f"git -C {shlex.quote(str(root))} commit -m {shlex.quote(message)} -- "
            + " ".join(shlex.quote(p) for p in paths))


CHARTER_BIN = f"{TOOL_DIR}/bin/charter"
HANDOVER_FILE = "handover.json"
OWNER_LINE_LABEL = "  the owner's line, after `!` in a Claude Code prompt or as is in a terminal:"


def owner_line(root: Path) -> str:
    """The one line the owner runs to commit a handover (0.4.12; docs/design/owner-handover.md). The switch is the
    owner's to type, so it is on this line and in no file; the engine is named by its absolute path, so the line
    commits this checkout (a worktree included) from any directory."""
    import shlex
    return f"CHARTER_OWNER=1 python3 {shlex.quote(str(root / CHARTER_BIN))} owner commit"


def handover_path(root: Path) -> Path:
    """The handover waiting on the owner: in this worktree's git directory, never in the tree."""
    return local_state_dir(root) / HANDOVER_FILE


def record_handover(root: Path, paths: list[str], message: str, by: str) -> dict:
    """Record what the owner's `charter owner commit` commits: the branch, the message, the paths and each path's
    staged blob (None for a removal). Data only: no command, and no owner switch."""
    staged = {}
    for entry in git(root, "ls-files", "-s", "-z", "--", *paths).stdout.split("\0"):
        if "\t" in entry:
            meta, rp = entry.split("\t", 1)
            staged[rp] = meta.split()[1]
    rec = {"at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"), "by": by,
           "branch": git(root, "branch", "--show-current").stdout.strip(),
           "head": git(root, "rev-parse", "--verify", "-q", "HEAD").stdout.strip() or None,
           "message": message, "paths": list(paths), "staged": {p: staged.get(p) for p in paths}}
    p = handover_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=2) + "\n")
    os.replace(tmp, p)
    return rec


def load_handover(root: Path) -> dict | None:
    p = handover_path(root)
    try:
        rec = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    return rec if isinstance(rec, dict) and rec.get("paths") else None


def handover_stale(root: Path, rec: dict) -> str:
    """Why a recorded handover no longer stands, or "" when it does: it was made on another branch, or a commit since
    touched one of its paths (it was committed another way, or overtaken). A commit since that touched none of them,
    such as an agent's own work, leaves it standing."""
    branch = git(root, "branch", "--show-current").stdout.strip()
    if branch != (rec.get("branch") or ""):
        return f"it was handed over on branch {rec.get('branch') or '(detached HEAD)'}, and this checkout is on {branch or '(detached HEAD)'}"
    head = git(root, "rev-parse", "--verify", "-q", "HEAD").stdout.strip()
    if not head or head == rec.get("head"):
        return ""
    paths = [str(p) for p in rec.get("paths") or []]
    if rec.get("head"):
        r = git(root, "diff", "--name-only", "-z", str(rec["head"]), head, "--", *paths)
        touched = [p for p in r.stdout.split("\0") if p] if r.returncode == 0 else paths[:1]
    else:   # handed over before the first commit
        touched = [p for p in git(root, "ls-tree", "-r", "-z", "--name-only", head, "--", *paths).stdout.split("\0") if p]
    if touched:
        return (f"{touched[0]}" + (f" and {len(touched) - 1} more" if len(touched) > 1 else "")
                + f" changed in a commit since the handover (HEAD is {head[:7]})")
    return ""


def clear_handover(root: Path) -> None:
    with contextlib.suppress(OSError):
        handover_path(root).unlink()


def handover(root: Path, paths: list[str], message: str, owner: list[str], by: str = "charter handover") -> list[str]:
    """Who commits what is staged, and how. `owner` lists the paths among them that are the owner's change
    (`checks.owner_only_staged`); with none, the agent commits, and the owner is not asked. With some, the handover
    is recorded and the block ends with the owner's line, alone on the last line so a triple-click copies it whole."""
    branch = git(root, "branch", "--show-current").stdout.strip() or "(detached HEAD)"
    cmd = commit_command(root, paths, message)
    note = [f"  note: {branch} is the main line; the change belongs on a branch (`git switch -c <branch>` keeps what is staged)"] \
        if branch in ("main", "master") else []
    if not owner:
        clear_handover(root)
        return [f"Staged {len(paths)} file(s) on branch {branch}; none is an owner-only change, so an agent commits them:",
                f"  {cmd}"] + note
    if (root / CHARTER_BIN).is_file():
        record_handover(root, paths, message, by)
        line = owner_line(root)
    else:   # an uninstall: the engine has left the tree, so the owner commits with git itself
        clear_handover(root)
        line = f"CHARTER_OWNER=1 {cmd}"
    return ([f"Waiting on the owner: commit {len(paths)} staged file(s) on branch {branch}. The gate refuses this commit to an agent.",
             f"  owner-only among them ({len(owner)}): " + ", ".join(owner[:8]) + (f" and {len(owner) - 8} more" if len(owner) > 8 else "")]
            + note + [OWNER_LINE_LABEL, line])


def ignored(root: Path, relpaths: list[str]) -> set[str]:
    """The paths among relpaths that git ignores and does not track: local scratch, never part of a unit's work.
    A tracked file stays in, whatever the ignore rules say."""
    if not relpaths:
        return set()
    r = subprocess.run(["git", "-C", str(root), "check-ignore", "-z", "--stdin"], input="\0".join(relpaths) + "\0",
                       capture_output=True, encoding="utf-8", errors="replace")
    return {p for p in r.stdout.split("\0") if p} if r.returncode == 0 else set()


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
    # a file git ignores is local scratch, not a unit: a synthesis that cites one fails its
    # anchors in CI, where the file does not exist. The index view holds only tracked files.
    ignored = set()
    if _VIEW is None:
        r = git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "--", TASKETS_DIR)
        ignored = set(r.stdout.splitlines()) if r.returncode == 0 else set()
    for p in sorted(d.glob("*.md")):
        if rel(base, p) in ignored:
            continue
        fields, body = read_md(p)
        fields["_path"] = rel(base, p)
        fields["_body"] = body
        fields["_id"] = str(fields.get("id") or p.stem)
        out[fields["_id"]] = fields
    return out


def decision_index_text(decs: dict[str, dict]) -> str:
    """charter/decisions/INDEX.md for these decisions: what `charter decisions index` writes and a ruling commits."""
    lines = ["# Decision index", "", "Generated by `charter decisions index`; do not edit. One file per decision in this directory.", "",
             "| id | title | status | expires | binds | check |", "|---|---|---|---|---|---|"]
    for k, v in decs.items():
        lines.append(f"| {k} | {v.get('title', '')} | {v.get('status', 'active')} | {v.get('expires', '')} | {', '.join(as_list(v.get('binds')))} | {'yes' if v.get('check') else ''} |")
    return "\n".join(lines) + "\n"


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
    """A tasket that took up the method: it cites a scope item or carries `## Acceptance`. `## Done When`
    does not count here, so the installer lists a tasket that has only that heading as legacy."""
    fields, _, body = split_frontmatter(text)
    return bool(fields.get("scope")) or bool(section(body, "Acceptance"))


# The headings that hold a unit's acceptance checklist, in the order they are read. The Tasket skill
# writes `## Done When` for the same checklist.
ACCEPTANCE_HEADINGS = ("Acceptance", "Done When")


def acceptance(body: str) -> str:
    """The acceptance checklist: the first of ACCEPTANCE_HEADINGS the body has."""
    return acceptance_span(body)[2]


def acceptance_span(body: str) -> tuple[str | None, list[int], str]:
    """(heading, the index in body.splitlines() of each line of the text, text) of the checklist `acceptance` reads;
    (None, [], "") without one. `charter unit show --json` numbers the lines from it (0.4.13)."""
    for h in ACCEPTANCE_HEADINGS:
        at, s = _section_at(body, h)
        if s:
            return h, at, s
    return None, [], ""


def session_id(session: str | None = None) -> str:
    """The Claude Code session asking: a hook passes the id it was given; a command run from a
    session's shell finds it in CLAUDE_CODE_SESSION_ID. Empty outside a session."""
    return re.sub(r"[^\w.-]", "_", (session or os.environ.get("CLAUDE_CODE_SESSION_ID", "")).strip())


def session_unit_file(root: Path, session: str | None = None) -> Path | None:
    sid = session_id(session)
    return local_state_dir(root) / f"active-{sid}" if sid else None


def unit_is_open(root: Path, uid: str) -> bool:
    """False when the unit's tasket says done or a terminal status; True when it says anything
    else or cannot be read (an unknown unit is reported by whoever uses it, not hidden here)."""
    d = artifact_root(root) / TASKETS_DIR
    for p in (d.glob(f"{glob.escape(uid)}*.md") if d.is_dir() else []):
        fields, _ = read_md(p)
        if str(fields.get("id") or p.stem) == uid:
            closed = as_list(load_config(root).get("done_statuses")) + list(TERMINAL_STATUSES)
            return str(fields.get("status", "")) not in closed
    return True


def active_unit(root: Path, session: str | None = None) -> str | None:
    """The unit a session works on. CHARTER_UNIT from the environment (engines export it) wins;
    then the unit this session chose with `charter unit start`; then the checkout's last choice,
    but only while that unit is open. The checkout's `active` file is shared by every session in
    the tree: read on its own, it charged 29 of 61 sessions in tele-claude's main checkout to a
    unit that was already done (2026-09-29), and their Stop gate asked them for its Log line."""
    return active_unit_source(root, session)[0]


def active_unit_source(root: Path, session: str | None = None) -> tuple[str | None, str | None]:
    """(the unit `active_unit` returns, where it came from: "env", "session", "checkout", or None with no unit)."""
    env = os.environ.get("CHARTER_UNIT", "").strip()
    if env:
        return env, "env"
    own = session_unit_file(root, session)
    if own is not None and own.exists():
        aid = own.read_text().strip() or None
        return aid, "session" if aid else None
    p = local_state_dir(root) / "active"
    if p.exists():
        aid = p.read_text().strip() or None
        if aid and unit_is_open(root, aid):
            return aid, "checkout"
    return None, None


def section(body: str, title: str) -> str:
    """Text of the markdown section whose heading starts with the word(s) `title`, case-insensitive:
    `## Acceptance criteria` counts, `## Logging` does not. A level-1 heading is the document's title,
    never a section, so a tasket titled `# Log emails to the timeline` has no Log section."""
    return _section_at(body, title)[1]


def _section_at(body: str, title: str) -> tuple[list[int], str]:
    """(the index in body.splitlines() of each line of the text `section` returns; that text). A nested heading that
    starts with `title` again is not in the text, so the lines are not always contiguous in the body."""
    lines = body.splitlines()
    out, at, level, on = [], [], None, False
    want = title.lower()
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            if on and len(m.group(1)) <= level:
                break
            head = m.group(2).strip().lower()
            if len(m.group(1)) > 1 and head.startswith(want) and not head[len(want):len(want) + 1].isalnum():
                on, level = True, len(m.group(1))
                continue
        if on:
            out.append(line)
            at.append(i)
    kept = [k for k, l in enumerate(out) if l.strip()]   # strip() drops the blank lines at either end
    return (at[kept[0]:kept[-1] + 1] if kept else []), "\n".join(out).strip()


# ---------------------------------------------------------------- git hooks

CHARTER_HOOKS_PATH = ".charter/githooks"
CHARTER_HOOK_COMMAND = ".charter/bin/charter check --staged"
# Tracked files that make a hook framework install its own hooks in each clone.
HOOK_FRAMEWORK_FILES = ("lefthook.yml", ".lefthook.yml", "lefthook.yaml", ".lefthook.yaml",
                        ".pre-commit-config.yaml", ".husky/pre-commit")


def hooks_path(root: Path) -> str:
    return git(root, "config", "--get", "core.hooksPath").stdout.strip()


def other_hooks(root: Path) -> list[str]:
    """Git hooks the project runs that are not charter's: executable files in the clone's hook directory
    other than the `*.sample` files git ships, and hook frameworks configured by a tracked file (the
    owner's other clones run them even where this one has not installed them). Pointing core.hooksPath
    at .charter/githooks stops every one of them."""
    out: list[str] = []
    cur = hooks_path(root)
    if cur != CHARTER_HOOKS_PATH:
        common = _git_path(root, "--git-common-dir")
        d = (root / cur) if cur else (common / "hooks" if common else None)
        if d is not None and d.is_dir():
            out += [rel(root, p) for p in sorted(d.iterdir())
                    if p.is_file() and not p.name.endswith(".sample") and os.access(p, os.X_OK)]
    out += [f for f in HOOK_FRAMEWORK_FILES if (root / f).is_file()]
    pj = root / "package.json"
    if pj.is_file():
        try:
            keys = json.loads(pj.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            keys = {}
        out += [f"package.json ({k})" for k in ("husky", "simple-git-hooks") if isinstance(keys, dict) and k in keys]
    return out


def hook_wired_by(root: Path) -> str | None:
    """The tracked hook-framework file whose hooks run the charter gate, if one does."""
    for f in HOOK_FRAMEWORK_FILES:
        p = root / f
        if p.is_file() and CHARTER_HOOK_COMMAND in p.read_text(encoding="utf-8", errors="replace"):
            return f
    return None


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
