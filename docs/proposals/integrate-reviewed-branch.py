#!/usr/bin/env python3
"""Owner Desk payload: merge a reviewed commit without borrowing a session's dirty index.

--check only inspects refs/worktree registration. Actual integration is the owner's act.
No push, tag, installed upgrade, stash, reset or edit of an existing unrelated file.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True,
                            stdin=subprocess.DEVNULL, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


def checkout_of(repo: Path, target: str) -> Path | None:
    path = None
    for line in git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree "):])
        elif line == f"branch refs/heads/{target}":
            return path
    return None


def inspect(repo: Path, candidate: str, target: str) -> tuple[str, str, Path | None]:
    # Resolve to immutable commits before any checkout; never treat a branch name as a shell string.
    reviewed = git(repo, "rev-parse", "--verify", f"{candidate}^{{commit}}")
    tip = git(repo, "rev-parse", "--verify", f"refs/heads/{target}^{{commit}}")
    return reviewed, tip, checkout_of(repo, target)


def integrate(repo: Path, candidate: str, target: str = "main") -> str:
    reviewed, tip, checkout = inspect(repo, candidate, target)
    scratch = Path(tempfile.mkdtemp(prefix="owner-reviewed-merge-"))
    added = False
    try:
        git(repo, "worktree", "add", "--detach", str(scratch), tip)
        added = True
        if checkout is None:
            # The default branch is not checked out: attach only this fresh, clean worktree.
            # Git refuses if another checkout claimed the branch in the meantime.
            git(scratch, "switch", target)
        git(scratch, "merge", "--no-ff", "--no-edit", reviewed)
        merged = git(scratch, "rev-parse", "HEAD")
        if checkout is not None:
            if git(checkout, "branch", "--show-current") != target:
                raise RuntimeError("The target checkout changed branches; no shared checkout was updated.")
            # Git refuses if HEAD moved concurrently or an overlapping local edit would be lost.
            # Unrelated staged/unstaged work remains in that checkout, outside the merge commit.
            git(checkout, "merge", "--ff-only", "--no-edit", merged)
        git(repo, "merge-base", "--is-ancestor", reviewed, f"refs/heads/{target}")
        return merged
    finally:
        if added:
            git(repo, "worktree", "remove", "--force", str(scratch))
        elif scratch.exists():
            shutil.rmtree(scratch)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--candidate", default=os.environ.get("REVIEWED_CANDIDATE"))
    parser.add_argument("--target", default="main")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.candidate:
        parser.error("--candidate is required")
    try:
        if args.check:
            reviewed, tip, checkout = inspect(args.repo, args.candidate, args.target)
            print(f"Reviewed commit: {reviewed}\nTarget: {args.target} at {tip}\n"
                  f"Target checkout: {checkout or 'a new temporary worktree on execution'}")
        else:
            merged = integrate(args.repo, args.candidate, args.target)
            print(f"Integrated {args.candidate} into {args.target}: {merged}")
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
