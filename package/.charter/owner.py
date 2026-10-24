"""The owner's queue and the owner's verbs (0.4.8).

`queue` lists what waits on the owner, from the project's own files: proposed decisions and change
requests, rails whose every unit is finished, problems in charter/rails.md, staged owner-only files,
HUMAN-ONLY units, unchecked acceptance lines only the owner can close, and a chain that waits on the
owner or halted (0.4.9). `charter next` prints it
under "Waiting on the owner" and `charter owner [--json]` prints it alone, from this one function, so
the two cannot drift. It reports commands (a decision's `check:`, a line's probe); it never runs one.

`rule`, `approve` and `rail` record a ruling in one command: they write the status, a dated `## Ruling`
line (decisions and change requests) and the decision index, then commit exactly those paths as the
owner. The owner switch is set in the environment of that one `git commit` and nowhere else. A verb
never pushes, merges, or writes a settings or permission file.
"""
from __future__ import annotations

import datetime as dt
import difflib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import checks
import lib
import rails

CHARTER_BIN = ".charter/bin/charter"
KINDS = ("decide", "do", "check")
FIELDS = ("key", "kind", "title", "file", "line", "ask", "recommend", "options", "check", "probe", "marked", "perform", "run", "contract", "why", "because")
# `- [ ] AC-4: rows arrive — owner: check — probe: `...``: a line only the owner can close (spec §10.2 of
# tele-claude's docs/OWNER_DESK.md). The word after `owner:` is the kind; a bare `owner:` is a check.
OWNER_SEG_RE = re.compile(r"\s[—–]\s*owner:\s*(decide|do|check)?\b", re.I)
# a legacy line that names a human step without the segment
HUMAN_SEG_RE = re.compile(r"\s[—–]\s*human:", re.I)
DECISION_RULINGS = ("active", "rejected", "superseded")
CHANGE_RULINGS = ("approved", "rejected")
TRAILER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*: \S.*$")
OWNER_SWITCH = "CHARTER_OWNER"


# ---------------------------------------------------------------- the queue

def _item(**kw) -> dict:
    it = {f: None for f in FIELDS}
    it.update(options=[], marked=True, run=[], contract=1)
    it.update(kw)
    return it


def perform_argv(root: Path, *args: str) -> list[str]:
    """A charter command as an argv list that runs from any directory."""
    return ["python3", str(root / CHARTER_BIN), "--root", str(root), *args]


def _line_of(text: str, pattern: str) -> int:
    """1-based line of the first match of `pattern` (multiline), or 1."""
    m = re.search(pattern, text, re.M)
    return text.count("\n", 0, m.start()) + 1 if m else 1


def _read(root: Path, rp: str) -> str:
    p = lib.artifact_root(root) / rp
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


# Content belongs to this protocol; consumers need not parse the source documents.
_CONSEQUENCES = {
    ("rule", "active"): "Binds from now on; a later decision can supersede it.",
    ("rule", "rejected"): "Records rejection; the proposal does not bind.",
    ("approve", "approved"): "Permits work within the request's stated paths.",
    ("approve", "rejected"): "Records rejection; the requested work remains unapproved.",
    ("rail", "done"): "Closes this item of the road as completed.",
    ("rail", "parked"): "Parks this item of the road for later work.",
    ("rail", "dropped"): "Removes this item from the planned road.",
}


def _paragraph(text: str, heading: str) -> str | None:
    """First paragraph, at most 500 characters; prefer a complete sentence."""
    match = re.search(rf"^## {re.escape(heading)}[ \t]*\n(.*?)(?=^#{{1,2}} |\Z)", text, re.M | re.S)
    if not match:
        return None
    paragraph = " ".join(re.split(r"\n\s*\n", match[1].strip(), maxsplit=1)[0].split())
    if len(paragraph) <= 500:
        return paragraph or None
    ends = list(re.finditer(r"[.!?](?=\s|$)", paragraph[:500]))
    return paragraph[:ends[-1].end()] if ends else paragraph[:499].rstrip() + "…"


def _options(root: Path, verb: str, ident: str, values: tuple[str, ...], labels: dict[str, str]) -> list[dict]:
    return [{"value": v, "label": labels.get(v, v), "consequence": _CONSEQUENCES.get((verb, v)),
             "perform": perform_argv(root, verb, ident, v)} for v in values]


def owner_names(root: Path, cfg: dict) -> list[str]:
    """Who "the owner" is in prose: the config's `owner`, the decisions' `owner:` (who settles them) and git's user.name."""
    names = [n for n in lib.as_list(cfg.get("owner"))]
    names += [str(d.get("owner")) for d in lib.decisions(root).values() if d.get("owner")]
    names.append(lib.git(root, "config", "user.name").stdout.strip())
    out: list[str] = []
    for n in names:
        n = n.split("@", 1)[0].strip()
        if n and n.lower() not in (x.lower() for x in out) and not n.startswith("<"):
            out.append(n)
    return out


def _legacy_re(names: list[str]) -> re.Pattern:
    alts = "|".join(re.escape(n) for n in names + ["the owner"])
    return re.compile(rf"\((?:{alts})\)|\b(?:{alts}) runs\b|\bafter (?:{alts}) restarts\b", re.I)


def is_owner_line(line: str, legacy: re.Pattern) -> bool:
    """An acceptance line only the owner closes: marked `— owner:`, or (unmarked) naming a human step or the owner
    the way units did before the segment. `owner_lines` and `charter unit show --json` read it here (0.4.13)."""
    return bool(OWNER_SEG_RE.search(line) or HUMAN_SEG_RE.search(line) or legacy.search(line))


def legacy_re(root: Path, cfg: dict) -> re.Pattern:
    """The pattern of an unmarked owner line in this project, from `owner_names`."""
    return _legacy_re(owner_names(root, cfg))


def owner_lines(root: Path, uid: str, u: dict, legacy: re.Pattern) -> list[dict]:
    """Unchecked acceptance lines of an open unit that only the owner can close: marked with `— owner:`, or
    (unmarked, `marked: false`) naming a human step or the owner the way units did before the segment."""
    text = _read(root, u["_path"])
    lines = text.splitlines()
    first = len(lines) - len(u.get("_body", "").splitlines())   # the body's first line, past the frontmatter
    heads = tuple(h.lower() for h in lib.ACCEPTANCE_HEADINGS)
    out, level = [], 0
    for lineno, line in enumerate(lines[first:], first + 1):
        h = re.match(r"^(#{1,6})\s+(.*)", line)
        if h:
            if level and len(h.group(1)) <= level:
                level = 0
            if not level and len(h.group(1)) > 1 and h.group(2).strip().lower().startswith(heads):
                level = len(h.group(1))
            continue
        box = re.match(r"^\s*-\s*\[( )\]\s*(AC-\d+)?", line) if level else None
        if not box:
            continue
        seg = OWNER_SEG_RE.search(line)
        if not is_owner_line(line, legacy):
            continue
        ac = box.group(2) or f"L{lineno}"
        probe = checks.PROBE_RE.match(line)
        what = re.sub(r"^\s*-\s*\[ \]\s*(AC-\d+:?\s*)?", "", line)
        what = re.split(r"\s[—–]\s*(?:owner|human|probe):", what)[0].strip()
        out.append(_item(key=f"owner-line:{uid}:{ac}", kind=(seg.group(1) or "check").lower() if seg else "check",
                         title=f"{uid} {ac}: {what}"[:200], file=u["_path"], line=lineno,
                         probe=probe.group(2) if probe else None, marked=bool(seg)))
    return out


def queue(root: Path, cfg: dict, units: dict[str, dict], states: dict[str, str]) -> list[dict]:
    """What waits on the owner, in the order `charter next` prints it. `states` maps a unit id to its state
    (`_unit_state` in the CLI); a finished unit is accepted, closed or done before charter."""
    items: list[dict] = []
    import chain   # here, not at the top: every charter command loads this module, few need the chain engine
    for it in chain.owner_items(root):
        it.pop("resume")   # the owner types `/resume-chain` (in `ask`): no command of the queue's resumes a chain (0.4.9)
        items.append(_item(**it))
    finished = ("accepted", "closed", "done-before-charter")
    loaded = rails.load(root, cfg)
    if loaded is not None:
        ritems, problems = loaded
        keys = rails.config(cfg)["keys"]
        on = {uid: rails.rails_of(u, keys, ritems) for uid, u in units.items()}
        for rid, it in rails.ordered(ritems):
            if it["status"] in rails.CLOSED or it["status"] == "todo":
                continue
            citing = [uid for uid in units if rid in on[uid]]
            if citing and all(states.get(uid) in finished for uid in citing):
                items.append(_item(key=f"rail:{rid}", kind="decide", file=rails.FILE, line=it["line"], recommend="done",
                                   title=f"rail {rid} is {it['status']} and every unit on it is finished: close it, or a unit for what is left is written first",
                                   ask=f"Close rail {rid} ({it['title']})?",
                                   options=_options(root, "rail", rid, rails.CLOSED, {}),
                                   perform=perform_argv(root, "rail", rid, "{answer}")))
        if problems:
            items.append(_item(key="rails-file", kind="do", file=rails.FILE, line=1,
                               title=f"{rails.FILE}: " + "; ".join(problems)))
    for k, v in lib.decisions(root).items():
        if str(v.get("status")) != "proposed":
            continue
        rec = str(v.get("recommend") or "").strip().lower() or None
        items.append(_item(key=f"decision:{k}", kind="decide", title=str(v.get("title", "")), file=v["_path"],
                           line=_line_of(_read(root, v["_path"]), r"^status:"),
                           ask=str(v.get("ask") or "") or None, recommend=rec if rec in DECISION_RULINGS else None,
                           why=_paragraph(_read(root, v["_path"]), "Recommendation"),
                           because=_paragraph(_read(root, v["_path"]), "Because"),
                           options=_options(root, "rule", k, ("active", "rejected"), {"active": "adopt it", "rejected": "reject it"}),
                           check=str(v.get("check") or "") or None,
                           perform=perform_argv(root, "rule", k, "{answer}")))
    for k, v in lib.change_requests(root).items():
        if str(v.get("status")) != "proposed":
            continue
        items.append(_item(key=f"change:{k}", kind="decide", title=str(v.get("title", "")), file=v["_path"],
                           line=_line_of(_read(root, v["_path"]), r"^status:"), ask=str(v.get("ask") or "") or None,
                           recommend=str(v.get("recommend") or "").strip().lower() if str(v.get("recommend") or "").strip().lower() in CHANGE_RULINGS else None,
                           why=_paragraph(_read(root, v["_path"]), "Recommendation"),
                           because=_paragraph(_read(root, v["_path"]), "Why it is outside the scope"),
                           options=_options(root, "approve", k, CHANGE_RULINGS, {}),
                           perform=perform_argv(root, "approve", k, "{answer}")))
    staged = [x for x in lib.git(root, "diff", "--cached", "--name-only", "--no-renames", "-z").stdout.split("\0") if x]
    mine = list(checks.owner_only_staged(root, cfg, staged))
    if mine:
        # 0.4.12: once `charter handover` recorded it, the owner's line commits it; until then, that is the next step
        rec = lib.load_handover(root)
        handed = bool(rec) and not lib.handover_stale(root, rec) and set(mine) <= set(rec["paths"])
        with_delegate = handed and rec.get("delegable") and not _verdict(root, rec.get("id"))
        items.append(_item(key="staged", kind="do", file=mine[0], line=1,
                           title=("handed to the owner's delegate, which commits it or hands it back: " if with_delegate else
                                  "staged, for the owner to commit: ") + ', '.join(mine[:6]) + (f" and {len(mine) - 6} more" if len(mine) > 6 else ""),
                           run=[lib.owner_line(root)] if handed else [],
                           perform=["env", f"{OWNER_SWITCH}=1", "python3", str(root / CHARTER_BIN), "owner", "commit"] if handed else None))
    import delegate
    for m in delegate.pending(root):
        v = _verdict(root, m.get("id"))
        if m["type"] == "merge" and v and v.get("result") in ("escalated", "failed"):
            items.append(_item(key=f"merge:{m['pr']}", kind="do", file=lib.CHARTER_DIR, line=1,
                               title=f"merge PR #{m['pr']}: the delegate handed it back", ask=str(v.get("reason") or ""),
                               run=[delegate.fallback(root, m)]))
    closed = lib.as_list(cfg.get("done_statuses")) + list(lib.TERMINAL_STATUSES)
    legacy = legacy_re(root, cfg)
    for uid, u in units.items():
        if str(u.get("status", "")) in closed:
            continue
        reason = str(u.get("gate_reason") or "")
        if reason.upper().startswith("HUMAN-ONLY"):
            items.append(_item(key=f"human:{uid}", kind="do", title=str(u.get("title", "")), file=u["_path"],
                               line=_line_of(_read(root, u["_path"]), r"^gate_reason:"), ask=reason))
        items += owner_lines(root, uid, u, legacy)
    return items


def _verdict(root: Path, item_id) -> dict | None:
    import delegate
    return delegate.load_verdict(root, item_id) if item_id else None


def next_line(it: dict) -> str:
    """The item as `charter next` prints it under "Waiting on the owner"."""
    key = it["key"]
    if key.startswith("rail:"):
        return f"- {it['title']} ({it['file']}:{it['line']})"
    if key == "rails-file":
        return f"- {it['title']}"
    if key.startswith("decision:"):
        return f"- decision {key.split(':', 1)[1]} — {it['title']} is proposed ({it['file']})"
    if key.startswith("change:"):
        return f"- change request {key.split(':', 1)[1]} — {it['title']} is proposed ({it['file']})"
    if key == "staged":
        if it.get("run"):
            return f"- {it['title']}\n{lib.OWNER_LINE_LABEL}\n{it['run'][0]}"
        return f"- {it['title']}; `python3 .charter/bin/charter handover` records it and prints the owner's line"
    if key.startswith("chain:"):
        ask = ("\n" + "\n".join(f"    {l}" for l in it["ask"].splitlines())) if it["ask"] else ""
        return f"- {it['title']}" + ask + run_lines(it)
    if key.startswith("human:"):
        return f"- HUMAN-ONLY unit {key.split(':', 1)[1]} — {it['title']} ({it['file']}:{it['line']})"
    return f"- {'owner line' if it['marked'] else 'unmarked owner line'} {it['title']} ({it['file']}:{it['line']})"


def run_lines(it: dict) -> str:
    """The commands of a waiting chain's acts, each alone on its line so that a triple-click copies it whole (0.4.10),
    or the owner's line of a handover (0.4.12)."""
    if not it.get("run"):
        return ""
    if it["key"] == "staged":
        return "\n" + lib.OWNER_LINE_LABEL + "\n" + "\n".join(it["run"])
    return "\n    the commands, one per line, each to paste as is:\n" + "\n".join(it["run"])


def handover_message(root: Path, staged: list[str], mine: list[str]) -> str:
    """The default message of the owner's commit of what is staged: `charter <version>` for an upgrade."""
    vp = f"{lib.CHARTER_DIR}/VERSION"
    ver = checks.staged_text(root, vp) if vp in staged else None
    if ver:
        return f"charter {ver.strip()}"
    if mine:
        return f"Owner-only change: {mine[0]}" + (f" and {len(mine) - 1} more" if len(mine) > 1 else "")
    return "Staged changes"


def report(root: Path, cfg: dict, items: list[dict]) -> dict:
    """The queue as a tool reads it; `delegate` (0.4.14) is the delegate's level, as `charter delegate level` prints it."""
    ver = root / lib.CHARTER_DIR / "VERSION"
    lv = lib.delegate_level(root)
    return {"project": str(root), "charter": ver.read_text().strip() if ver.exists() else None,
            "owner": ", ".join(lib.as_list(cfg.get("owner"))) or None,
            "delegate": {"level": lv["level"], "from": lv["from"], "problems": lv["problems"], "levels": list(lib.DELEGATE_LEVELS),
                         "set": perform_argv(root, "delegate", "level", "{answer}")},
            "items": items}


def human(rep: dict) -> str:
    """The queue grouped by kind, each with the command that performs it."""
    L = [f"Waiting on the owner in {rep['project']} (charter {rep['charter']}): {len(rep['items'])} item(s)"]
    if rep.get("delegate") and rep["delegate"]["level"] != "strict":
        L.append(f"The owner's delegate works at level {rep['delegate']['level']} (from {rep['delegate']['from']}).")
    titles = {"decide": "Decide", "do": "Do", "check": "Check"}
    for kind in KINDS:
        its = [i for i in rep["items"] if i["kind"] == kind]
        if not its:
            continue
        L += ["", f"{titles[kind]}:"]
        for i in its:
            L.append(f"- [{i['key']}] {i['title']} ({i['file']}:{i['line']})" + ("" if i["marked"] else " (unmarked)"))
            if i["ask"]:
                L += [f"    ask: {l}" for l in i["ask"].splitlines()]
            if i["run"]:
                L.append(run_lines(i).lstrip("\n"))
            if i["recommend"]:
                L.append(f"    recommended: {i['recommend']}")
            if i["check"]:
                L.append(f"    check (not run): {i['check']}")
            if i["probe"]:
                L.append(f"    probe (not run): {i['probe']}")
            for o in i["options"]:
                L.append(f"    {o['value']}: {shlex.join(o['perform'])}")
            if i["perform"] and not i["options"]:
                L.append(f"    perform: {shlex.join(i['perform'])}")
    if not rep["items"]:
        L.append("- nothing")
    return "\n".join(L)


# ---------------------------------------------------------------- the verbs

class Refused(Exception):
    pass


def warn_in_session() -> None:
    """Until the tool path refuses these verbs (tele-claude's owner desk, unit od5), say what they are."""
    if lib.in_claude_code():
        print("charter: this is the owner's act. From Claude Code only the owner runs it, as a `!` command; "
              "an agent proposes the ruling and does not run it.", file=sys.stderr)


def owner_name(root: Path, cfg: dict) -> str:
    names = lib.as_list(cfg.get("owner"))
    return names[0] if names else (lib.git(root, "config", "user.name").stdout.strip() or "the owner")


def set_field(text: str, key: str, value: str) -> str:
    """Set a top-level frontmatter field, keeping every other line; a missing field goes after `status:`."""
    m = re.match(r"\A(---\s*\n)(.*?\n)(---\s*(?:\n|\Z))", text, re.S)
    if not m:
        raise Refused("the file has no frontmatter")
    fm = m.group(2)
    pat = re.compile(rf"^{re.escape(key)}:[^\n]*$", re.M)
    new = f"{key}: {value}"
    if pat.search(fm):
        fm = pat.sub(lambda _: new, fm, count=1)
    else:
        st = re.search(r"^status:[^\n]*\n", fm, re.M)
        at = st.end() if st else len(fm)
        fm = fm[:at] + new + "\n" + fm[at:]
    return m.group(1) + fm + m.group(3) + text[m.end():]


def add_ruling(text: str, line: str) -> str:
    """Append `line` under `## Ruling` at the end of the file, opening the section when it is not the last one."""
    heads = re.findall(r"^##\s+(.*)$", text, re.M)
    body = text.rstrip("\n")
    if heads and heads[-1].strip().lower().startswith("ruling"):
        return body + "\n" + line + "\n"
    return body + "\n\n## Ruling\n\n" + line + "\n"


def _clean(root: Path, rp: str) -> None:
    """The file ruled on must be the committed one: what the owner read is what is ruled."""
    if lib.git(root, "ls-files", "--error-unmatch", "--", rp).returncode != 0:
        raise Refused(f"{rp} is not committed; commit the proposal first, then rule on it")
    if lib.git(root, "status", "--porcelain", "--", rp).stdout.strip():
        raise Refused(f"{rp} has uncommitted changes; commit or discard them first, so the ruling is on what was proposed")


def _committed_decisions(root: Path, override: tuple[str, str]) -> dict[str, dict]:
    """The decisions as HEAD has them, with one file replaced by its new text: the index committed with a
    ruling lists no decision that another session has not committed yet."""
    d = f"{lib.CHARTER_DIR}/decisions"
    names = [p for p in lib.git(root, "ls-tree", "--name-only", "HEAD", f"{d}/").stdout.splitlines() if p.endswith(".md")]
    if override[0] not in names:
        names.append(override[0])
    out = {}
    for rp in sorted(names, key=lambda p: Path(p).name):
        if Path(rp).name.lower() in ("readme.md", "index.md"):
            continue
        text = override[1] if rp == override[0] else lib.git(root, "show", f"HEAD:{rp}").stdout
        fields, _, body = lib.split_frontmatter(text)
        fields["_path"], fields["_body"] = rp, body
        fields.setdefault("status", "active")
        out[str(fields.get("id") or Path(rp).stem)] = fields
    return out


def _commit(root: Path, writes: dict[str, str], message: str, trailer: str | None, dry_run: bool, delegate: bool = False) -> int:
    """Write the files, stage them and commit exactly them as the owner; roll back when the commit is refused. For the
    owner's delegate (0.4.14, delegate.perform) the commit is built from the new texts alone, the committer is the
    delegate and the owner switch is not set (_delegate_commit)."""
    if trailer and not TRAILER_RE.match(trailer):
        raise Refused(f"--trailer {trailer!r} is not a `Key: value` git trailer")
    old = {rp: ((root / rp).read_text(encoding="utf-8") if (root / rp).exists() else None) for rp in writes}
    # the paths are literal: a file named like a pattern never sweeps another into the commit (review of 2026-10-13, item 1)
    args = ["git", "-C", str(root), "--literal-pathspecs", "commit", "-q", "-m", message] + (["-m", trailer] if trailer else []) + ["--", *writes]
    if dry_run:
        for rp, new in writes.items():
            sys.stdout.writelines(difflib.unified_diff((old[rp] or "").splitlines(True), new.splitlines(True), f"a/{rp}", f"b/{rp}"))
        print(f"\nwould commit, " + ("as the owner's delegate (committer the delegate, no owner switch, exactly these files)" if delegate
              else "as the owner (the owner switch set for this one commit only)") + f":\n  {shlex.join(args)}")
        return 0
    if delegate:
        return _delegate_commit(root, writes, [message] + ([trailer] if trailer else []))
    before = set(lib.git(root, "--literal-pathspecs", "diff", "--cached", "--name-only", "-z", "--", *writes).stdout.split("\0")) - {""}
    staged = [l.split(None, 3) for l in lib.git(root, "--literal-pathspecs", "ls-files", "-s", "--", *before).stdout.splitlines()] if before else []
    for rp, new in writes.items():
        (root / rp).parent.mkdir(parents=True, exist_ok=True)
        (root / rp).write_text(new, encoding="utf-8")
    lib.git(root, "--literal-pathspecs", "add", "--", *writes, check=True)
    env = dict(os.environ, **{OWNER_SWITCH: "1"})
    r = subprocess.run(args, env=env, capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        for rp, text in old.items():
            if text is None:
                (root / rp).unlink(missing_ok=True)
            else:
                (root / rp).write_text(text, encoding="utf-8")
        unstage = [rp for rp in writes if rp not in before]
        if unstage:
            lib.git(root, "--literal-pathspecs", "reset", "-q", "--", *unstage)
        for mode, blob, _, rp in staged:   # what another session staged goes back into the index as it was
            lib.git(root, "update-index", "--cacheinfo", f"{mode},{blob},{rp}")
        raise Refused("the commit was refused, so nothing changed:\n" + (r.stdout + r.stderr).strip())
    sha = lib.git(root, "rev-parse", "--short", "HEAD").stdout.strip()
    print(f"committed {sha} as the owner: {message} ({', '.join(writes)}); not pushed")
    return 0


def _delegate_commit(root: Path, writes: dict[str, str], messages: list[str]) -> int:
    """The delegate's commit of a ruling (delegate.perform): the new texts as blobs, committed through a private index
    with the gate of this engine, never the project's hook (delegate.write_commit); then the tree and the index take
    the committed texts, so nothing shows as changed. Raises Refused when it is refused; then nothing changed."""
    import delegate
    modes, entries = {}, {}
    for entry in lib.git(root, "--literal-pathspecs", "ls-tree", "-z", "HEAD", "--", *writes).stdout.split("\0"):
        if "\t" in entry:
            meta, rp = entry.split("\t", 1)
            modes[rp] = meta.split()[0]
    for rp, new in writes.items():
        # from stdin, with no path: no filter of the project's config runs
        h = subprocess.run(["git", "-C", str(root), "hash-object", "-w", "--stdin"], input=new.encode("utf-8"), capture_output=True)
        if h.returncode != 0:
            raise Refused(f"git could not store {rp}: {h.stderr.decode(errors='replace').strip()}")
        entries[rp] = (modes.get(rp, "100644"), h.stdout.decode().strip())
    try:
        sha = delegate.write_commit(root, entries, messages, messages[-1])
    except delegate.Refused as e:   # delegate.Busy goes up: the watcher tries again on its next run
        raise Refused(f"the commit was refused, so nothing changed: {e}")
    for rp, new in writes.items():
        (root / rp).parent.mkdir(parents=True, exist_ok=True)
        (root / rp).write_text(new, encoding="utf-8")
    info = "".join(f"{m} {b}\t{rp}\0" for rp, (m, b) in entries.items())
    u = subprocess.run(["git", "-C", str(root), "update-index", "-z", "--index-info"], input=info.encode("utf-8"), capture_output=True)
    if u.returncode != 0:
        print(f"committed {sha[:7]}, but the index could not take it ({u.stderr.decode(errors='replace').strip()}): "
              f"`git reset -q -- {' '.join(shlex.quote(p) for p in writes)}` makes it match", file=sys.stderr)
    print(f"committed {sha[:7]} as the owner's delegate: {messages[0]} ({', '.join(writes)}); not pushed")
    return 0


def _run_check(root: Path, cfg: dict, did: str, cmd: str) -> None:
    timeout = int((cfg.get("probes") or {}).get("timeout_s", 120))
    try:
        r = subprocess.run(cmd, shell=True, cwd=str(root), capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Refused(f"decision {did}: its check did not finish in {timeout} s, so it cannot be made active: {cmd}")
    if r.returncode != 0:
        out = (r.stdout + r.stderr).strip()
        raise Refused(f"decision {did}: its check exits {r.returncode}, so it cannot be made active: {cmd}" + (f"\n{out}" if out else ""))


def rule(root: Path, cfg: dict, did: str, status: str, by: str | None = None, note: str | None = None,
         trailer: str | None = None, dry_run: bool = False, delegate: bool = False) -> int:
    decs = lib.decisions(root)
    d = decs.get(did)
    if d is None:
        raise Refused(f"no decision {did} in {lib.CHARTER_DIR}/decisions/")
    if status not in DECISION_RULINGS:
        raise Refused(f"a decision is ruled {', '.join(DECISION_RULINGS)}, not {status}")
    cur = str(d.get("status", "active"))
    if not (cur == "proposed" or (cur == "active" and status == "superseded")):
        raise Refused(f"decision {did} is {cur}; only a proposed decision is ruled, and an active one only superseded")
    if status == "superseded":
        if not by:
            raise Refused("superseded needs --by <decision> naming its successor")
        if by == did or by not in decs:
            raise Refused(f"--by {by}: no other decision has that id in {lib.CHARTER_DIR}/decisions/")
    elif by:
        raise Refused("--by is only for superseded")
    rp = d["_path"]
    _clean(root, rp)
    if status == "active" and d.get("check"):
        if dry_run:   # a check may write files: a dry run names it and does not run it
            print(f"would run the check first: {d['check']}")
        else:
            _run_check(root, cfg, did, str(d["check"]))
    text = set_field((root / rp).read_text(encoding="utf-8"), "status", status)
    if by:
        text = set_field(text, "superseded_by", by)
    who = owner_name(root, cfg)
    text = add_ruling(text, f"- {dt.date.today().isoformat()} {status}" + (f" (by {by})" if by else "") + f" by {who}" + (f": {note}" if note else ""))
    index = lib.decision_index_text(_committed_decisions(root, (rp, text)))
    ip = f"{lib.CHARTER_DIR}/decisions/INDEX.md"
    rc = _commit(root, {rp: text, ip: index}, f"decision {did}: {status}", trailer, dry_run, delegate)
    if not dry_run:
        live = lib.decision_index_text(lib.decisions(root))
        if live != index:   # another session's uncommitted decisions go back into its working copy of the index
            (root / ip).write_text(live, encoding="utf-8")
    return rc


def approve(root: Path, cfg: dict, cid: str, status: str = "approved", note: str | None = None,
            trailer: str | None = None, dry_run: bool = False, delegate: bool = False) -> int:
    c = lib.change_requests(root).get(cid)
    if c is None:
        raise Refused(f"no change request {cid} in {lib.CHARTER_DIR}/changes/")
    if status not in CHANGE_RULINGS:
        raise Refused(f"a change request is {' or '.join(CHANGE_RULINGS)}, not {status}")
    if str(c.get("status")) != "proposed":
        raise Refused(f"change request {cid} is {c.get('status')}; only a proposed one is approved or rejected")
    rp = c["_path"]
    _clean(root, rp)
    who, day = owner_name(root, cfg), dt.date.today().isoformat()
    text = (root / rp).read_text(encoding="utf-8")
    for k, v in (("status", status), ("approved_by", who), ("approved_on", day)):
        text = set_field(text, k, v)
    text = add_ruling(text, f"- {day} {status} by {who}" + (f": {note}" if note else ""))
    return _commit(root, {rp: text}, f"change {cid}: {status}", trailer, dry_run, delegate)


def rail(root: Path, cfg: dict, rid: str, status: str, note: str | None = None, trailer: str | None = None,
         dry_run: bool = False, delegate: bool = False) -> int:
    rid, status = rid.strip().lower(), status.strip().lower()
    loaded = rails.load(root, cfg)
    if loaded is None:
        raise Refused(f"{rails.FILE} does not exist")
    items, _ = loaded
    if rid not in items:
        raise Refused(f"no rail {rid} in {rails.FILE}")
    if status not in rails.STATUSES:
        raise Refused(f"a rail's status is one of {', '.join(rails.STATUSES)}, not {status}")
    if items[rid]["status"] == status:
        raise Refused(f"rail {rid} is already {status}")
    _clean(root, rails.FILE)
    lines = (root / rails.FILE).read_text(encoding="utf-8").split("\n")
    n = items[rid]["line"] - 1
    header = next(l for l in lines[:n] if l.lstrip().startswith("|") and all(c in [x.strip().lower() for x in l.split("|")] for c in rails.COLUMNS))
    col = [x.strip().lower() for x in header.split("|")].index("status")
    cells = lines[n].split("|")
    cells[col] = f" {status} "
    lines[n] = "|".join(cells)
    msg = f"rail {rid}: {status}" + (f"\n\n{note}" if note else "")   # rails.md has no Ruling section: the note is in the commit
    return _commit(root, {rails.FILE: "\n".join(lines)}, msg, trailer, dry_run, delegate)


def dumps(rep: dict) -> str:
    return json.dumps(rep, indent=2, ensure_ascii=False)
