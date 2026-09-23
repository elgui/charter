"""Rails: the road a project without a devis is allowed to be on.

`charter/rails.md` holds a table of the road's items (id, title, status, order). Every open unit
names one with `rail:`, or with a `roadmap:` link whose anchor is the item's id. The check makes
off-road work visible at the moment it starts rather than in the next progress report:

- an open unit that names no rail, or only rails the file does not list, warns;
- with `rails.required` in the config, such a unit is refused when it is in the change set, so the
  backlog from before the rails never blocks an unrelated commit;
- an open unit whose only rails are closed (done, parked, dropped) warns.

Adding an item to the file is the recorded re-plan, and the file is owner-only
(checks.OWNER_ONLY_FILES). This is the client track's scope gate, with the roadmap as the scope set.
"""
from __future__ import annotations

from pathlib import Path

import lib
from checks import Finding

# Fixed, not configurable: the staged view (lib.index_view) copies only charter/ and .taskets/, and the
# owner-only list names this path, so a configured path elsewhere escaped both (review of 0.4.0).
FILE = "charter/rails.md"
STATUSES = ("todo", "next", "in-progress", "done", "parked", "dropped")
CLOSED = ("done", "parked", "dropped")
COLUMNS = ("id", "title", "status", "order")
OVERRIDE = ("add `rail: <id>` naming an open item of {file}; to start work the road does not name, "
            "the owner adds a rail item first (that is the recorded re-plan)")


def config(cfg: dict) -> dict:
    r = cfg.get("rails") or {}
    return {"file": FILE, "required": bool(r.get("required")),
            "keys": lib.as_list(r.get("keys")) or ["rail", "roadmap"]}


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse(text: str) -> tuple[dict[str, dict], list[str]]:
    """The first table whose header has the four columns; everything else in the file is prose."""
    items: dict[str, dict] = {}
    problems: list[str] = []
    header: list[str] | None = None
    for n, line in enumerate(text.splitlines(), 1):
        if not line.lstrip().startswith("|"):
            if header is not None and items:
                break
            continue
        cells = [c.lower() for c in _cells(line)]
        if header is None:
            if all(c in cells for c in COLUMNS):
                header = cells
            continue
        if set(line.replace("|", "").strip()) <= set("-: "):
            continue   # the separator row
        row = dict(zip(header, _cells(line)))
        rid = row.get("id", "").strip().lower()
        if not rid:
            problems.append(f"line {n} has no id")
            continue
        if rid in items:
            problems.append(f"line {n} names {rid} twice")
            continue
        status = row.get("status", "").strip().lower()
        if status not in STATUSES:
            problems.append(f"line {n}: status `{status}` of {rid} is not one of {', '.join(STATUSES)}")
        try:
            order = int(row.get("order", "").strip())
        except ValueError:
            order = None
            problems.append(f"line {n}: order of {rid} is not an integer")
        items[rid] = {"title": row.get("title", ""), "status": status, "order": order, "line": n}
    if header is None:
        problems.append("no table with the columns " + ", ".join(COLUMNS))
    return items, problems


def load(root: Path, cfg: dict) -> tuple[dict[str, dict], list[str]] | None:
    """The rails, or None when the project keeps none (the gate is then off)."""
    p = lib.artifact_root(root) / config(cfg)["file"]
    if not p.is_file():
        return None
    return parse(p.read_text(encoding="utf-8", errors="replace"))


def ordered(items: dict[str, dict]) -> list[tuple[str, dict]]:
    return sorted(items.items(), key=lambda kv: (kv[1]["order"] is None, kv[1]["order"] or 0, kv[1]["line"]))


def rail_ids(unit: dict, keys: list[str]) -> list[str]:
    """The rail ids a unit names: `rail: <id>`, or the anchor of `roadmap: <doc>#<id>`."""
    out = []
    for k in keys:
        for v in lib.as_list(unit.get(k)):
            v = str(v).strip()
            v = v.rsplit("#", 1)[1] if "#" in v else v
            v = v.strip().lower()
            if v and v not in out:
                out.append(v)
    return out


def is_open(unit: dict, cfg: dict) -> bool:
    status = str(unit.get("status", "")).strip()
    return status not in lib.as_list(cfg.get("done_statuses")) and status not in lib.TERMINAL_STATUSES


def check(root: Path, cfg: dict, units: dict[str, dict], changed: set[str] | None) -> list[Finding]:
    rc = config(cfg)
    loaded = load(root, cfg)
    if loaded is None:
        return []
    items, problems = loaded
    f = rc["file"]
    out = [Finding("rails", "warn", f"{f}: {p}", path=f, override=f"the owner fixes {f}") for p in problems]
    for uid, u in units.items():
        if not is_open(u, cfg):
            continue
        level = "block" if rc["required"] and changed is not None and u["_path"] in changed else "warn"
        ids = rail_ids(u, rc["keys"])
        known = [i for i in ids if i in items]
        if not ids:
            out.append(Finding("rails", level, f"unit {uid} names no rail from {f}", path=u["_path"], override=OVERRIDE.format(file=f)))
        elif not known:
            out.append(Finding("rails", level, f"unit {uid} names unknown rail {', '.join(ids)}", path=u["_path"],
                               override=OVERRIDE.format(file=f)))
        elif all(items[i]["status"] in CLOSED for i in known):
            i = known[0]
            out.append(Finding("rails", "warn", f"unit {uid} is open, and its rail {i} is {items[i]['status']}", path=u["_path"],
                               override=f"move the unit to an open rail, close the unit, or ask the owner to reopen {i}"))
    return out


def synth_lines(root: Path, cfg: dict, units: dict[str, dict], state_of) -> list[str]:
    """The Rails and Off-the-rails sections of the progress synthesis, or nothing without a rails file."""
    loaded = load(root, cfg)
    if loaded is None:
        return []
    items, _ = loaded
    rc = config(cfg)
    f = rc["file"]
    L = ["## Rails"]
    for rid, it in ordered(items):
        citing = [uid for uid, u in units.items() if rid in rail_ids(u, rc["keys"])]
        summary = ", ".join(f"{uid} ({state_of(uid)})" for uid in citing) or "no unit cites it"
        L.append(f"- {rid} — {it['title']} [{it['status']}]: {summary} ({f})")
    if not items:
        L.append(f"- none ({f})")
    L += ["", "## Off the rails"]
    off = [(uid, u) for uid, u in units.items() if is_open(u, cfg) and not any(i in items for i in rail_ids(u, rc["keys"]))]
    L += [f"- {uid} — {u.get('title', '')} [{u.get('status')}] ({u['_path']})" for uid, u in off] or [f"- none ({f})"]
    return L + [""]
