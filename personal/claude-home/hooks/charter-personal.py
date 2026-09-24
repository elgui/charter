#!/usr/bin/env python3
"""Personal-layer SessionStart hook for charter projects (runs from ~/.claude, never from a repo).

Adds what only makes sense on Gui's machines: whether the installed package is behind the
package repository, how many ended sessions wait to be folded into the ledger, and where the
open decisions can be turned into a Crossroads or Slate page. Prints nothing outside a charter
project. Fails silent: it must never delay a session."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PKG_DIR = Path(os.environ.get("CHARTER_PKG_DIR", str(Path.home() / "Projects" / "charter")))


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        data = {}
    cwd = Path(data.get("cwd") or os.getcwd())
    try:
        root = Path(subprocess.run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or cwd)
    except Exception:
        root = cwd
    if not (root / ".charter").is_dir():
        return 0
    out = ["charter personal layer:"]
    installed = (root / "charter" / "VERSION").read_text().strip() if (root / "charter" / "VERSION").exists() else "?"
    latest = (PKG_DIR / "package" / "VERSION").read_text().strip() if (PKG_DIR / "package" / "VERSION").exists() else "?"
    if installed != latest:
        out.append(f"  package {latest} available, {installed} installed: python3 {PKG_DIR}/bin/charter-pkg upgrade {root} --dry-run")
    else:
        out.append(f"  package {installed} is current")
    common = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            capture_output=True, text=True).stdout.strip()
    sess = Path(common) / "charter" / "sessions.jsonl" if common else root / ".charter" / "state" / "sessions.jsonl"
    if not sess.exists():
        sess = root / ".charter" / "state" / "sessions.jsonl"   # a 0.1.0 install
    led = root / "charter" / "ledger.jsonl"
    n_s = sum(1 for _ in sess.open()) if sess.exists() else 0
    n_l = sum(1 for line in led.open() if '"source": "human"' not in line) if led.exists() else 0
    if n_s > n_l:
        out.append(f"  {n_s - n_l} ended session(s) not yet in the ledger: python3 .charter/bin/charter ledger fold")
    props = []
    for d in ("decisions", "changes"):
        p = root / "charter" / d
        if p.is_dir():
            for f in p.glob("*.md"):
                head = f.read_text(errors="replace")[:600]
                if "status: proposed" in head:
                    props.append(f"{d}/{f.stem}")
    if props:
        out.append(f"  waiting on you: {', '.join(props)} (use /crossroads or /slate to decide them; answers go back into the files)")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
