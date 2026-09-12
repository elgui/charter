"""Bootstrap for hook entry points: put .charter/ on sys.path and locate the tree."""
import json
import os
import sys
sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import lib  # noqa: E402
import checks  # noqa: E402


def tree_for(data: dict) -> Path:
    """The checkout the hook acts on. `cwd` follows Claude into a worktree;
    CLAUDE_PROJECT_DIR stays at the session's start directory."""
    cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    root = lib.repo_root(cwd)
    if (root / lib.TOOL_DIR).is_dir():
        return root
    # not a charter project at cwd; fall back to the project dir
    alt = lib.repo_root(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
    return alt


def session_file(root: Path, sid: str) -> Path:
    return lib.local_state_dir(root) / f"session-{sid}.json"


def read_session(root: Path, sid: str) -> dict:
    """Per-session scratch: `edited` (paths this session), `turn_edited` (since the last Stop),
    `head` (HEAD at the last Stop or at session start)."""
    p = session_file(root, sid)
    try:
        cur = json.loads(p.read_text()) if p.exists() else {}
    except (OSError, json.JSONDecodeError):
        cur = {}
    cur.setdefault("edited", [])
    cur.setdefault("turn_edited", [])
    return cur


def write_session(root: Path, sid: str, cur: dict) -> None:
    p = session_file(root, sid)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cur))
    except OSError:
        pass


def head(root: Path) -> str:
    return lib.git(root, "rev-parse", "HEAD").stdout.strip()


def post_edit_text(data: dict) -> str | None:
    """Content the file will have after a Write or Edit, or None if unknowable."""
    ti = data.get("tool_input") or {}
    name = data.get("tool_name")
    path = ti.get("file_path")
    if not path:
        return None
    if name == "Write":
        return ti.get("content", "")
    if name == "Edit":
        try:
            cur = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            cur = ""
        old, new = ti.get("old_string", ""), ti.get("new_string", "")
        if old and old in cur:
            return cur.replace(old, new) if ti.get("replace_all") else cur.replace(old, new, 1)
        if not old:
            return cur + new
        return None
    return None
