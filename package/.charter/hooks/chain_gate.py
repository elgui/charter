#!/usr/bin/env python3
"""Chain gate: UserPromptSubmit, UserPromptExpansion, PreToolUse, PostToolUse and Stop for a charter chain (.charter/chain.py).

It runs on every prompt and every tool call of every session, so a session that is not in a chain leaves within a
few milliseconds: no git, no charter import, one file test. A prompt joins its session to a chain when it carries
the marker line `charter-chain: <id> session <n>`; from then on the hook measures the session's context, tells it
when to hand over, refuses everything but the handoff past the cap, and keeps it from ending its turn before
`charter chain next` closed it. In any session, the owner's `/resume-chain` prompt resumes a paused chain here, and
the prompt is blocked from the model (0.4.9); a Bash command that names CHARTER_OWNER, or runs `charter owner run` or
`charter owner commit`, is denied, since an agent never sets the one or runs the others (0.4.11, 0.4.12); so is one that
runs the owner's delegate (`charter delegate commit|perform|settle|level <name>`, `charter-delegate run`; 0.4.14) or
sets levels across the fleet (`charter-pkg fleet --levels`; 0.4.16). Fails open on its own errors, as every charter
gate does."""
import json
import os
import re
import shlex
import sys
sys.dont_write_bytecode = True
from pathlib import Path


# `charter owner run` and `charter owner commit` (0.4.12) in any spelling argparse takes: the charter CLI by any path
# (`.charter/bin/charter`, `./charter`, `charter`), then `owner` and the action with options anywhere between (`owner --yes
# run`; cross-review of 2026-10-05). Quotes are dropped first, so a quoted path matches; a commit message or a grep that
# spells the command is denied too
OWNER_RUN_RE = re.compile(r"(?:^|[\s;&|(`/=])charter\b[^\n;&|]*?\sowner\b[^\n;&|]*?\s(run|commit)\b", re.M)
# the owner's delegate (0.4.14): its acts (`charter delegate commit|perform|settle`), setting a level
# (`charter delegate level <name>`) and the watcher's run (`charter-delegate run`, `--dry-run` aside) are never an
# agent's. Read word by word (delegate_act), so a commit message or a grep that names them passes (review of 2026-10-13,
# item 9); the patterns are the fallback for a line the shell lexer cannot read
DELEGATE_ACT_RE = re.compile(r"(?:^|[\s;&|(`/=])charter\b[^\n;&|]*?\sdelegate\b[^\n;&|]*?\s(commit|perform|settle|level\s+(?:strict|routine|answers|open))\b", re.M)
WATCHER_RUN_RE = re.compile(r"charter-delegate\b[^\n;&|]*?\s(run)\b", re.M)
# the owner's fleet line that commits levels (`charter-pkg fleet --levels`, any abbreviation argparse takes): a session
# started with the owner switch passes the installer's own refusal, so the hook denies it (/reviewPR of #17, 2026-10-14)
FLEET_LEVELS_RE = re.compile(r"charter-pkg\b[^\n;&|]*?\sfleet\b[^\n;&|]*?\s--l", re.M)
LEVELS = ("strict", "routine", "answers", "open")
SHELLS = ("sh", "bash", "zsh", "dash", "ksh")


def _commands(line: str):
    """Each simple command of a shell line, as its words."""
    lex = shlex.shlex(line.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    cur = []
    for tok in list(lex) + [";"]:
        if tok and set(tok) <= set("();<>|&"):
            if cur:
                yield cur
            cur = []
        else:
            cur.append(tok)


def _substitutions(line: str) -> list[str]:
    """The text of each `$(...)` and backtick substitution outside single quotes: the shell runs them, even inside a
    double-quoted commit message."""
    out, i, q = [], 0, None
    while i < len(line):
        c = line[i]
        if q == "'":
            q = None if c == "'" else q
        elif c == "\\":
            i += 1
        elif c == "'" and q is None:
            q = "'"
        elif c == '"':
            q = None if q == '"' else '"'
        elif c == "`":
            j = line.find("`", i + 1)
            j = len(line) if j < 0 else j
            out.append(line[i + 1:j])
            i = j
        elif line.startswith("$(", i):
            depth, j = 1, i + 2
            while j < len(line) and depth:
                depth += {"(": 1, ")": -1}.get(line[j], 0)
                j += 1
            out.append(line[i + 2:j - 1])
            i = j - 1
        i += 1
    return out


def delegate_act(line: str, depth: int = 0) -> bool:
    """Whether a Bash line runs one of the delegate's acts or the watcher (DELEGATE_ACT_RE, WATCHER_RUN_RE): the charter
    CLI by any path, after any wrapper (`env -u X`, `timeout 30`, `python3 -B`), inside `sh -c`, `eval` or a command
    substitution. A quoted mention, as in a commit message or a grep pattern, is one word and does not count."""
    if depth > 3:
        return False
    if any(delegate_act(sub, depth + 1) for sub in _substitutions(line)):
        return True
    try:
        cmds = list(_commands(line))
    except ValueError:   # unbalanced quotes: the patterns decide
        bare = line.replace("'", "").replace('"', "")
        return bool(DELEGATE_ACT_RE.search(bare) or WATCHER_RUN_RE.search(bare) or FLEET_LEVELS_RE.search(bare))
    for words in cmds:
        for i, w in enumerate(words):
            name, rest = os.path.basename(w.strip("`")), words[i + 1:]
            if name in SHELLS and "-c" in rest and rest.index("-c") + 1 < len(rest):
                if delegate_act(rest[rest.index("-c") + 1], depth + 1):
                    return True
            elif name == "eval" and delegate_act(" ".join(rest), depth + 1):
                return True
            elif name == "charter" and "delegate" in rest:
                act = [x for x in rest[rest.index("delegate") + 1:] if not x.startswith("-")]
                if act and (act[0] in ("commit", "perform", "settle") or (act[0] == "level" and len(act) > 1 and act[1] in LEVELS)):
                    return True
            elif name == "charter-delegate" and "run" in rest and "--dry-run" not in rest:
                return True
            elif name == "charter-pkg" and "fleet" in rest and not any(len(x) >= 3 and "--dry-run".startswith(x) for x in rest):
                if any(len(x.split("=", 1)[0]) >= 3 and "--levels".startswith(x.split("=", 1)[0]) for x in rest):
                    return True
    return False


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
                          "and run `python3 .charter/bin/charter handover`: it prints the line the owner runs."}}))
        return 0
    bare = command.replace("'", "").replace('"', "")
    if ev == "PreToolUse" and command and delegate_act(command):
        # the delegate acts from cron, outside any session; an agent that ran it would clear its own owner act
        print(json.dumps({"hookSpecificOutput": {"hookEventName": ev, "permissionDecision": "deny", "permissionDecisionReason":
                          "charter: the owner's delegate runs outside Claude Code, from cron, and only the owner sets its level. "
                          "Hand over with `python3 .charter/bin/charter handover` (`--ask`, `--merge`) and wait with `--wait`; "
                          "never run the delegate's acts or the watcher yourself."}}))
        return 0
    m = OWNER_RUN_RE.search(bare) if ev == "PreToolUse" else None
    if m and m.group(1) == "commit":
        # the owner's commit of a handover (0.4.12): the owner types it with the switch; without it the gate refuses anyway
        print(json.dumps({"hookSpecificOutput": {"hookEventName": ev, "permissionDecision": "deny", "permissionDecisionReason":
                          "charter: `charter owner commit` is the owner's command: it commits what is handed over, as the owner. "
                          "Run `python3 .charter/bin/charter handover` and give the owner the line it prints; never run it yourself."}}))
        return 0
    if m:
        # the owner's acts run in the owner's shell: sudo or Touch ID prompts raised by an agent's command would ask the
        # owner to approve what they did not start (0.4.11). The owner's `!` command is not a tool call and is not seen here
        print(json.dumps({"hookSpecificOutput": {"hookEventName": ev, "permissionDecision": "deny", "permissionDecisionReason":
                          "charter: `charter owner run` is the owner's command: it runs the acts a chain waits on, sudo included, "
                          "in the owner's shell. Tell the owner to run it (as `!` in Claude Code, or in a terminal); never run it yourself."}}))
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
