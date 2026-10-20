#!/usr/bin/env python3
"""Machine-layer SessionStart hook for charter projects. It runs from ~/.claude, once per user, never from a project.

A project knows the package version it has installed; only the user's machine knows which charter checkout it came
from. This hook says when that checkout carries a newer package, names the checkout so the CharterAdmin skill can
find it, and adds the `## Session` section of `~/.claude/charter-local.md`, the user's own conventions, when that file
exists. Installs below 0.4.18 also get the ledger backlog and what waits on the owner, which the project's own hook
reports from 0.4.18. Prints nothing outside a charter project. Fails silent: it must never delay a session."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SIDECAR = "charter-machine.json"   # written next to a copied hook by `charter-pkg machine install`
LOCAL = Path.home() / ".claude" / "charter-local.md"


def checkout() -> Path | None:
    """The charter checkout: $CHARTER_PKG_DIR, else the one a copied hook's sidecar records, else the one a linked hook
    resolves into."""
    env = os.environ.get("CHARTER_PKG_DIR")
    if env:
        return Path(env).expanduser()
    side = Path(__file__).parent / SIDECAR
    if side.exists():
        try:
            return Path(json.loads(side.read_text())["source"])
        except (ValueError, KeyError, TypeError):
            pass
    here = Path(__file__).resolve().parents[2]
    return here if (here / "package" / "VERSION").exists() else None


def layer_hash(src: Path) -> str:
    """The machine layer as the checkout has it: one hash over every file under machine/, by relative path."""
    h = hashlib.sha256()
    for p in sorted(q for q in (src / "machine").rglob("*") if q.is_file() and "__pycache__" not in q.parts):
        h.update(str(p.relative_to(src)).encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def vtuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return ()


def section(text: str, name: str) -> str:
    """The body of a `## <name>` section, up to the next `## ` heading."""
    out, on = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            on = line[3:].strip().lower() == name.lower()
            continue
        if on:
            out.append(line)
    return "\n".join(out).strip()


def session_ids(p: Path) -> set:
    """The session ids a JSON-lines record names."""
    out = set()
    if p.exists():
        for line in p.read_text(errors="replace").splitlines():
            try:
                out.add(json.loads(line).get("session"))
            except (json.JSONDecodeError, AttributeError):
                pass
    out.discard(None)
    return out


def legacy_lines(root: Path) -> list[str]:
    """What the project's own SessionStart hook reports from 0.4.18: unfolded sessions, and records waiting on the owner."""
    out = []
    common = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            capture_output=True, text=True).stdout.strip()
    sess = Path(common) / "charter" / "sessions.jsonl" if common else root / ".charter" / "state" / "sessions.jsonl"
    if not sess.exists():
        sess = root / ".charter" / "state" / "sessions.jsonl"   # a 0.1.0 install
    # distinct session ids, as `unfolded_sessions` in the package's session_start.py: a resumed session ends, and is
    # recorded, more than once
    n = len(session_ids(sess) - session_ids(root / "charter" / "ledger.jsonl"))
    if n:
        out.append(f"{n} ended session(s) not yet in the ledger: python3 .charter/bin/charter ledger fold")
    props = []
    for d in ("decisions", "changes"):
        p = root / "charter" / d
        if p.is_dir():
            for f in sorted(p.glob("*.md")):
                if "status: proposed" in f.read_text(errors="replace")[:600]:
                    props.append(f"{d}/{f.stem}")
    if props:
        out.append(f"waiting on you: {', '.join(props)}")
    return out


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        data = {}
    cwd = Path(data.get("cwd") or os.getcwd())
    try:
        root = Path(subprocess.run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
                                   capture_output=True, text=True).stdout.strip() or cwd)
    except Exception:
        root = cwd
    if not (root / ".charter").is_dir():
        return 0
    src = checkout()
    out, seen = ["charter machine layer:"], []
    vf = root / "charter" / "VERSION"
    installed = vf.read_text().strip() if vf.exists() else "?"
    latest = (src / "package" / "VERSION").read_text().strip() if src and (src / "package" / "VERSION").exists() else ""
    if not latest:
        out.append("  no charter checkout found: set CHARTER_PKG_DIR, or run `charter-pkg machine install` from one")
    else:
        out.append(f"  package repository: {src}")
        if vtuple(latest) > vtuple(installed):
            line = f"package {latest} available, {installed} installed: python3 {src}/bin/charter-pkg upgrade {root} --dry-run"
            out.append("  " + line)
            seen.append(line)
        elif installed == latest:
            out.append(f"  package {installed} is current")
        else:   # the project is ahead of this checkout: never suggest a downgrade
            out.append(f"  package {installed} installed, newer than this checkout's {latest}: pull {src} before upgrading anything")
        side = Path(__file__).parent / SIDECAR
        try:   # against the checkout the copy came from, whatever $CHARTER_PKG_DIR says
            rec = json.loads(side.read_text()) if side.exists() else {}
            home = Path(rec["source"]) if rec.get("source") else None
            stale = bool(home) and (home / "machine").is_dir() and rec.get("hash") != layer_hash(home)
        except (ValueError, OSError, TypeError):
            stale = False
        if stale:
            line = f"machine layer changed in {home}: python3 {home}/bin/charter-pkg machine install"
            out.append("  " + line)
            seen.append(line)
    if vtuple(installed) < (0, 4, 18):
        for line in legacy_lines(root):
            out.append("  " + line)
            if line.startswith("waiting on you"):
                seen.append(line)
    if LOCAL.exists():
        local = section(LOCAL.read_text(errors="replace"), "Session")
        if local:
            out.append(f"  from {LOCAL}:")
            out.extend("  " + line for line in local.splitlines())
    # plain stdout reaches Claude only; `systemMessage` is what the person sees (https://code.claude.com/docs/en/hooks)
    msg = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(out)}}
    if seen:
        msg["systemMessage"] = "charter: " + "\n".join(seen)
    print(json.dumps(msg))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
