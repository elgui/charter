"""The machine layer: what charter puts in ~/.claude once per user, from this checkout (machine/README.md).

`charter-pkg machine install` copies the SessionStart hook and the CharterAdmin skill into ~/.claude, records this
checkout in a sidecar next to the hook, and adds the hook to ~/.claude/settings.json; `--link` symlinks them into the
checkout instead, so an edit there is live. `uninstall` removes what install wrote and nothing else; `status` reads.
It never touches ~/.claude/charter-local.md, which is the user's. Python 3 standard library only."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LAYER = REPO / "machine"
HOOK_SRC = LAYER / "hooks" / "charter-machine.py"
SKILL_SRC = LAYER / "skills" / "CharterAdmin"
FRAGMENT = LAYER / "settings-fragment.json"
HOOK_NAME, SIDECAR, SKILL_NAME = "charter-machine.py", "charter-machine.json", "CharterAdmin"


def _hook_module():
    spec = importlib.util.spec_from_file_location("charter_machine_hook", HOOK_SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def layer_hash(root: Path) -> str:
    return _hook_module().layer_hash(root)   # the hook compares the same hash against the checkout it records


def source() -> Path:
    """The checkout a copied hook reads: the main worktree of this repository, so an install run from a linked worktree
    still follows the checkout that is kept up to date."""
    out = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         capture_output=True, text=True).stdout.strip()
    common = Path(out) if out else None
    return common.parent if common and common.name == ".git" and (common.parent / "package" / "VERSION").exists() else REPO


def paths(home: Path) -> dict:
    claude = home / ".claude"
    return {"settings": claude / "settings.json", "hook": claude / "hooks" / HOOK_NAME,
            "sidecar": claude / "hooks" / SIDECAR, "skill": claude / "skills" / SKILL_NAME}


def _ours(p: Path, src: Path, side: Path) -> bool:
    """A path install wrote: a link into a charter checkout's machine/, or a copy the sidecar records."""
    if p.is_symlink():
        return Path(p.readlink()).as_posix().endswith("machine/" + src.relative_to(LAYER).as_posix())
    return p.exists() and side.exists()


def _command_is_ours(h: dict) -> bool:
    return HOOK_NAME in str(h.get("command", "")) + " ".join(map(str, h.get("args") or []))


def _settings(p: Path) -> dict | None:
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def wired(s: dict) -> bool:
    return any(_command_is_ours(h) for g in (s.get("hooks") or {}).get("SessionStart") or [] for h in g.get("hooks") or [])


def _write_settings(p: Path, s: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(s, indent=2, ensure_ascii=False) + "\n"
    p.write_text(text)   # through a link: a linked settings.json stays a link


def install(home: Path, link: bool = False, settings: bool = True, force: bool = False, dry_run: bool = False) -> int:
    P = paths(home)
    blocked = [str(P[k]) for k, src in (("hook", HOOK_SRC), ("skill", SKILL_SRC))
               if (P[k].exists() or P[k].is_symlink()) and not _ours(P[k], src, P["sidecar"])]
    if blocked and not force:
        for b in blocked:
            print(f"refused: {b} exists and is not this layer's; move it aside, or pass --force to replace it")
        return 1
    s = _settings(P["settings"]) if settings else {}
    if s is None:
        print(f"refused: {P['settings']} is not a JSON object; add this to its hooks yourself, or pass --no-settings:")
        print(FRAGMENT.read_text().rstrip())
        return 1
    mode = "link" if link else "copy"
    act = "would " if dry_run else ""
    print(f"machine layer from {REPO} ({mode}){', dry run' if dry_run else ''}")
    for k, src in (("hook", HOOK_SRC), ("skill", SKILL_SRC)):
        print(f"  {act}{'link' if link else 'copy'} {P[k]} {'->' if link else '<-'} {src}")
        if dry_run:
            continue
        dest = P[k]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.is_dir():
            shutil.rmtree(dest)
        if link:
            dest.symlink_to(src, target_is_directory=src.is_dir())
        elif src.is_dir():
            shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dest)
            dest.chmod(0o755)
    if link:
        if P["sidecar"].exists():
            print(f"  {act}remove {P['sidecar']} (a linked hook finds its checkout itself)")
            if not dry_run:
                P["sidecar"].unlink()
    else:
        print(f"  {act}write {P['sidecar']}: source {source()}")
        if not dry_run:
            P["sidecar"].write_text(json.dumps({"source": str(source()), "hash": layer_hash(REPO), "mode": "copy",
                                                "installed": dt.date.today().isoformat()}, indent=2) + "\n")
    if not settings:
        print(f"  settings left alone (--no-settings); the hook runs once {P['settings']} has:")
        print(FRAGMENT.read_text().rstrip())
    elif wired(s):
        print(f"  {P['settings']}: the SessionStart hook is already wired")
    else:
        print(f"  {act}add the SessionStart hook to {P['settings']}")
        if not dry_run:
            entry = json.loads(FRAGMENT.read_text())["hooks"]["SessionStart"]
            s.setdefault("hooks", {}).setdefault("SessionStart", []).extend(entry)
            _write_settings(P["settings"], s)
    if not dry_run:
        print("done; a new Claude Code session picks it up. Your own additions go in ~/.claude/charter-local.md (machine/README.md)")
    return 0


def uninstall(home: Path, dry_run: bool = False) -> int:
    P = paths(home)
    act = "would " if dry_run else ""
    for k, src in (("hook", HOOK_SRC), ("skill", SKILL_SRC)):
        if not (P[k].exists() or P[k].is_symlink()):
            continue
        if not _ours(P[k], src, P["sidecar"]):
            print(f"  kept {P[k]}: not this layer's")
            continue
        print(f"  {act}remove {P[k]}")
        if not dry_run:
            if P[k].is_symlink() or P[k].is_file():
                P[k].unlink()
            else:
                shutil.rmtree(P[k])
    if P["sidecar"].exists():
        print(f"  {act}remove {P['sidecar']}")
        if not dry_run:
            P["sidecar"].unlink()
    s = _settings(P["settings"])
    if s and wired(s):
        print(f"  {act}remove the SessionStart hook from {P['settings']}")
        if not dry_run:
            groups = []
            for g in s["hooks"]["SessionStart"]:
                g = dict(g, hooks=[h for h in g.get("hooks") or [] if not _command_is_ours(h)])
                if g["hooks"]:
                    groups.append(g)
            if groups:
                s["hooks"]["SessionStart"] = groups
            else:
                del s["hooks"]["SessionStart"]
            _write_settings(P["settings"], s)
    print(f"{'dry run; ' if dry_run else ''}~/.claude/charter-local.md, if any, is yours and stays")
    return 0


def status(home: Path) -> int:
    P = paths(home)
    if P["hook"].is_symlink():
        mode = f"linked to {P['hook'].resolve().parents[2]}"
    elif P["hook"].exists() and P["sidecar"].exists():
        side = json.loads(P["sidecar"].read_text())
        src = Path(side.get("source", REPO))
        stale = (src / "machine").is_dir() and side.get("hash") != layer_hash(src)
        mode = f"copied {side.get('installed', '?')} from {side.get('source')}" + (
            "; this checkout's machine/ differs: run `charter-pkg machine install` again" if stale else ", current")
    elif P["hook"].exists():
        mode = f"{P['hook']} exists but is not this layer's"
    else:
        mode = "not installed"
    s = _settings(P["settings"])
    print(f"machine layer: {mode}")
    print(f"  skill: {'present' if P['skill'].exists() else 'absent'} ({P['skill']})")
    print(f"  settings: {'wired' if s and wired(s) else 'not wired'} ({P['settings']})")
    local = home / ".claude" / "charter-local.md"
    print(f"  local additions: {local if local.exists() else 'none'}")
    return 0
