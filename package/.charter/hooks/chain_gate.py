#!/usr/bin/env python3
"""Chain gate: UserPromptSubmit, UserPromptExpansion, PreToolUse, PostToolUse and Stop for a charter chain (.charter/chain.py).

It runs on every prompt and every tool call of every session, so a session that is not in a chain leaves within a
few milliseconds: no git, no charter import, one file test. A prompt joins its session to a chain when it carries
the marker line `charter-chain: <id> session <n>`; from then on the hook measures the session's context, tells it
when to hand over, refuses everything but the handoff past the cap, and keeps it from ending its turn before
`charter chain next` closed it. In any session, the owner's `/resume-chain` prompt resumes a paused chain here, and
the prompt is blocked from the model (0.4.9); a Bash command that names CHARTER_OWNER is denied, since an agent never
sets it. Fails open on its own errors, as every charter gate does."""
import json
import os
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path


def common_git_dir(start: Path):
    """The git common directory, found without running git: `.git` as a directory, or a worktree's `.git` file."""
    for d in (start, *start.parents):
        g = d / ".git"
        if g.is_dir():
            return g
        if g.is_file():
            txt = g.read_text(errors="replace").strip()
            if not txt.startswith("gitdir:"):
                return None
            gd = Path(txt[7:].strip())
            gd = gd if gd.is_absolute() else (d / gd).resolve()
            cd = gd / "commondir"
            if cd.exists():
                c = Path(cd.read_text().strip())
                return c if c.is_absolute() else (gd / c).resolve()
            return gd
    return None


def main() -> int:
    try:
        return gate()
    except Exception as e:  # fail open, visibly, the fast path included
        print(json.dumps({"systemMessage": f"charter chain_gate error (gate skipped): {e!r}"}))
        return 0


def gate() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    ev, sid = data.get("hook_event_name") or "", data.get("session_id") or ""
    cwd = Path(data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    prompt = data.get("prompt") or ""
    resume = (ev == "UserPromptExpansion" and (data.get("command_name") or "").lstrip("/") == "resume-chain") or (
        ev == "UserPromptSubmit" and prompt.lstrip().startswith("/resume-chain"))
    command = str((data.get("tool_input") or {}).get("command") or "") if data.get("tool_name") == "Bash" else ""
    if ev == "PreToolUse" and re.search(r"(?:-u\s*|unset\s+(?:-v\s+)?|\b)CLAUDECODE\b(?!=1)", command) and not re.fullmatch(r"\s*(?:echo|printenv)\s+\$?CLAUDECODE\s*", command):
        # without CLAUDECODE the commit gate takes the committer for the owner and only warns (cross-review, 2026-10-04)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": ev, "permissionDecision": "deny", "permissionDecisionReason":
                          "charter: an agent never unsets or changes CLAUDECODE; the commit gate reads it to tell an agent from the owner."}}))
        return 0
    if ev == "PreToolUse" and "CHARTER_OWNER" in command:
        # the owner switch turns the owner-only checks off for one commit; the owner sets it from their own prompt (`!`)
        # or terminal, and an agent never does (.claude/rules/charter.md). Every session of the project, not only a chain's
        print(json.dumps({"hookSpecificOutput": {"hookEventName": ev, "permissionDecision": "deny", "permissionDecisionReason":
                          "charter: an agent never sets CHARTER_OWNER; it switches the owner-only checks off. Leave the change staged "
                          "and run `python3 .charter/bin/charter handover`: it prints the command the owner runs."}}))
        return 0
    if ev in ("UserPromptSubmit", "UserPromptExpansion"):
        if not resume and "charter-chain: " not in prompt:
            return 0
    else:
        g = common_git_dir(cwd)
        if g is None or not sid or not (g / "charter" / "chain" / "sessions" / sid).exists():
            return 0
    from _common import tree_for, lib  # noqa: F401  (puts .charter/ on sys.path)
    import chain
    root = tree_for(data)
    if not (root / lib.TOOL_DIR).is_dir():
        return 0
    if resume:
        r = chain.owner_prompt(root, data)
        if r:
            print(json.dumps({"decision": "block", "reason": r["block"]}))
    elif ev == "UserPromptSubmit":
        r = chain.on_prompt(root, data)
        if r:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": ev, "additionalContext": r["additionalContext"]}}))
    elif ev == "PreToolUse":
        r = chain.on_pre_tool(root, data)
        if r:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": ev, "permissionDecision": "deny",
                                                     "permissionDecisionReason": r["deny"]}}))
    elif ev == "PostToolUse":
        r = chain.on_post_tool(root, data)
        if r:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": ev, "additionalContext": r["additionalContext"]}}))
    elif ev == "Stop":
        r = chain.on_stop(root, data)
        if r:
            print(json.dumps({"decision": "block", "reason": r["block"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
