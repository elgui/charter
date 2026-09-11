"""Bootstrap for hook entry points: put .charter/ on sys.path and locate the tree."""
import os
import sys
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
