"""The owner's delegate (0.4.14; docs/design/owner-delegate.md).

A session hands an owner act over as it always has (`charter handover`), records the owner's own answer for the
delegate to transcribe (`charter handover --ask`), or asks for a merge (`charter handover --merge`). A watcher outside
Claude Code (`bin/charter-delegate` in the charter repository, run by cron) reads `charter delegate plan --json`, judges
each pending item, and calls back `charter delegate commit`, `perform` or `settle`. This module is the engine's half:
what is pending, what the project's level lets the delegate take, and the acts themselves. Each act checks everything
again here, since a verdict is only the watcher's word, and each refuses inside Claude Code: an agent never acts as the
delegate.

The level (`delegate.level`, lib.delegate_level) is read from the config committed on the default branch; only the
owner changes it (`charter delegate level <name>`, refused to an agent), and no level delegates a config change.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import checks
import lib

ASKS, MERGES, VERDICTS = "asks", "merges", "delegate"
ASK_VERBS = ("rule", "approve", "rail")
MIN_QUOTE = 12            # the owner's words, as typed: long enough that a stray match is unlikely
DIFF_CAP = 60_000         # bytes of diff or context a plan carries for the judge
RESULTS = ("committed", "performed", "merged", "escalated", "failed")
DONE = ("committed", "performed", "merged")


class Refused(Exception):
    pass


class Busy(Exception):
    """Another git process holds the index: nothing was decided, the watcher tries again on its next run."""


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _id(prefix: str, *parts) -> str:
    return prefix + hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _sub(root: Path, name: str) -> Path:
    return lib.delegate_dir(root) / name


def _write(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, p)


def _read(p: Path) -> dict | None:
    try:
        obj = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def _cap(s: str) -> str:
    b = s.encode("utf-8", "replace")
    return s if len(b) <= DIFF_CAP else b[:DIFF_CAP].decode("utf-8", "ignore") + "\n[... cut at {} bytes]".format(DIFF_CAP)


def refuse_in_session(what: str) -> None:
    """The delegate's acts run outside Claude Code only: inside it, CLAUDECODE=1 marks an agent's tool, owner switch or not."""
    if lib.in_claude_code():
        raise Refused(f"{what}: refused: this is the owner's delegate, and it runs outside Claude Code (the watcher, "
                      "`bin/charter-delegate`, from cron). An agent never acts as the delegate; it hands over with "
                      "`python3 .charter/bin/charter handover` and waits with `--wait`.")


# ---------------------------------------------------------------- verdicts

def verdict_path(root: Path, item_id: str) -> Path:
    if not re.fullmatch(r"[ahm][0-9a-f]{12}", item_id or ""):
        raise Refused(f"{item_id!r} is not a delegate item id")
    return _sub(root, VERDICTS) / f"{item_id}.json"


def load_verdict(root: Path, item_id: str) -> dict | None:
    try:
        return _read(verdict_path(root, item_id))
    except Refused:
        return None


def settle(root: Path, item_id: str, result: str, by: str, reason: str, sha: str | None = None, **extra) -> dict:
    """Record the delegate's verdict on one item, where `charter handover --wait` reads it."""
    refuse_in_session("charter delegate settle")
    if result not in RESULTS:
        raise Refused(f"a result is one of {', '.join(RESULTS)}, not {result}")
    v = {"id": item_id, "result": result, "by": by, "reason": reason, "sha": sha, "at": _now(), **extra}
    _write(verdict_path(root, item_id), v)
    return v


# ---------------------------------------------------------------- what is pending

def _asks(root: Path) -> list[dict]:
    d = _sub(root, ASKS)
    return [r for r in (_read(p) for p in sorted(d.glob("*.json"))) if r] if d.is_dir() else []


def _merges(root: Path) -> list[dict]:
    d = _sub(root, MERGES)
    return [r for r in (_read(p) for p in sorted(d.glob("*.json"))) if r] if d.is_dir() else []


def pending(root: Path) -> list[dict]:
    """Every item recorded in this checkout, newest handover first: the handover, asks, merge requests. A recorded
    handover from before 0.4.14 has no id and is left to the owner's line."""
    out = []
    rec = lib.load_handover(root)
    if rec and rec.get("id"):
        out.append(dict(rec, type="commit"))
    out += [dict(r, type="ask") for r in _asks(root)]
    out += [dict(r, type="merge") for r in _merges(root)]
    return out


def find(root: Path, item_id: str) -> dict | None:
    return next((r for r in pending(root) if r.get("id") == item_id), None)


# ---------------------------------------------------------------- the plan the watcher reads

def _blob_now(root: Path, rp: str) -> str | None:
    if not (root / rp).exists() and not (root / rp).is_symlink():
        return None
    return lib.git(root, "hash-object", "--", rp).stdout.strip() or None


def _closed_probes(root: Path, rp: str, kinds_by_key: dict[str, str]) -> list[dict]:
    """The probe of each `— owner: check` line this change closes, read from the staged unit."""
    text = checks.staged_text(root, rp)
    lines = checks._probe_lines(text)
    out = []
    for key, kind in kinds_by_key.items():
        if kind != "owner-check":
            continue
        hit = next(((ac, cmd) for ac, cmd, whole in lines if ac == key or key in whole.lower()), None)
        out.append({"path": rp, "key": key, "probe": hit[1] if hit else None})
    return out


def _plan_commit(root: Path, cfg: dict, rec: dict, lv: dict) -> dict:
    paths = [str(p) for p in rec.get("paths") or []]
    recorded = rec.get("staged") or {}
    index = lib.staged_blobs(root, paths)
    changed = [p for p in paths if index.get(p) != recorded.get(p) or _blob_now(root, p) != recorded.get(p)]
    kinds = checks.owner_kinds_staged(root, cfg, paths)
    union = {k for v in kinds.values() for k in v}
    probes = []
    for rp in kinds:
        if rp.startswith(lib.TASKETS_DIR + "/") and "owner-check" in kinds[rp]:
            probes += _closed_probes(root, rp, checks.owner_line_kinds(checks.head_text(root, rp), checks.staged_text(root, rp)))
    stale = lib.handover_stale(root, rec)
    why = []
    if stale:
        why.append(f"stale: {stale}")
    if changed:
        why.append(f"changed since the handover, in the index or the tree: {', '.join(changed[:6])}")
    if not kinds:
        why.append("nothing staged is the owner's any more")
    elif not lib.delegable(union, lv["level"]):
        keep = sorted(union - lib.LEVEL_KINDS.get(lv["level"], frozenset()))
        why.append(f"level {lv['level']} (from {lv['from']}) keeps {', '.join(keep) or 'this'} for the owner")
    missing = [f"{p['path']} {p['key']}" for p in probes if not p["probe"]]
    if missing:
        why.append(f"no probe to rerun on {', '.join(missing)}")
    diff = lib.git(root, "diff", "--cached", "--no-color", "--", *paths).stdout
    units = {rp: _cap(checks.staged_text(root, rp)) for rp in kinds if rp.startswith(lib.TASKETS_DIR + "/")}
    return {"paths": paths, "message": rec.get("message"), "kinds": kinds, "probes": probes, "diff": _cap(diff),
            "units": units, "delegable": not why, "why_not": "; ".join(why)}


def _verb_diff(root: Path, cfg: dict, rec: dict) -> tuple[str, str]:
    """(the diff the ask's verb would commit, why it cannot) from a dry run of the verb."""
    import owner
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            _call_verb(root, cfg, rec, dry_run=True)
    except owner.Refused as e:
        return "", str(e)
    return buf.getvalue(), ""


def _call_verb(root: Path, cfg: dict, rec: dict, dry_run: bool, trailer: str | None = None, delegate: bool = False) -> int:
    import owner
    verb, target, status = rec["verb"], rec["target"], rec["status"]
    note = _ruling_note(rec)
    if verb == "rule":
        return owner.rule(root, cfg, target, status, by=rec.get("by_decision"), note=note, trailer=trailer, dry_run=dry_run, delegate=delegate)
    if verb == "approve":
        return owner.approve(root, cfg, target, status, note=note, trailer=trailer, dry_run=dry_run, delegate=delegate)
    return owner.rail(root, cfg, target, status, note=note, trailer=trailer, dry_run=dry_run, delegate=delegate)


def _ruling_note(rec: dict) -> str:
    """The ruling line names the owner's words the delegate transcribed."""
    words = f'the owner\'s words: "{rec["quote"]}" (transcribed by the delegate, {rec["id"]})'
    return f"{rec['note']}; {words}" if rec.get("note") else words


def _plan_ask(root: Path, cfg: dict, rec: dict, lv: dict) -> dict:
    why = []
    stale = lib.handover_stale(root, rec)
    if stale:
        why.append(f"stale: {stale}")
    if not lib.delegable({"ruling"}, lv["level"]):
        why.append(f"level {lv['level']} (from {lv['from']}) keeps the owner's rulings for the owner")
    diff, refused = _verb_diff(root, cfg, rec)
    if refused:
        why.append(f"`charter {rec['verb']}` refuses it now: {refused}")
    context = {p: _cap(checks.head_text(root, p)) for p in rec.get("paths") or [] if not p.endswith("INDEX.md")}
    return {"verb": rec["verb"], "target": rec["target"], "status": rec["status"], "quote": rec.get("quote"),
            "session": rec.get("session"), "cwd": rec.get("cwd"), "note": rec.get("note"), "diff": _cap(diff),
            "context": context, "delegable": not why, "why_not": "; ".join(why)}


def _plan_merge(root: Path, rec: dict, lv: dict) -> dict:
    why = [] if lib.delegable({"merge"}, lv["level"]) else [f"level {lv['level']} (from {lv['from']}) keeps merges for the owner"]
    return {"pr": rec.get("pr"), "method": rec.get("method"), "base": rec.get("base"),
            "delegable": not why, "why_not": "; ".join(why)}


def plan(root: Path, cfg: dict) -> dict:
    """What waits on the delegate in this checkout, with what the level allows and why not: data only, it changes nothing."""
    lv_branch = lib.delegate_level(root)
    lv_main = lib.delegate_level(root, branch_too=False)
    items = []
    for rec in pending(root):
        lv = lv_main if rec["type"] == "merge" else lv_branch
        base = {k: rec.get(k) for k in ("id", "type", "at", "by", "branch", "head")}
        base.update(level=lv["level"], level_from=lv["from"], verdict=load_verdict(root, rec["id"]), fallback=fallback(root, rec))
        if rec["type"] == "commit":
            base.update(_plan_commit(root, cfg, rec, lv))
        elif rec["type"] == "ask":
            base.update(_plan_ask(root, cfg, rec, lv))
        else:
            base.update(_plan_merge(root, rec, lv))
        items.append(base)
    return {"root": str(root), "project": lib.git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip(),
            "level": lv_branch["level"], "level_from": lv_branch["from"], "problems": lv_branch["problems"],
            "probe_timeout_s": int((cfg.get("probes") or {}).get("timeout_s", 120)), "items": items}


# ---------------------------------------------------------------- the session's records

def record_ask(root: Path, cfg: dict, verb: str, target: str, status: str, quote: str, session: str = "",
               by_decision: str | None = None, note: str | None = None) -> dict:
    """Record the owner's own answer for the delegate to transcribe as `charter <verb>`: the session that heard it, and
    the words as the owner typed them, which the watcher must find in a message the owner typed in that session."""
    if verb not in ASK_VERBS:
        raise Refused(f"--ask takes {', '.join(ASK_VERBS)}, not {verb}")
    lv = lib.delegate_level(root)
    if not lib.delegable({"ruling"}, lv["level"]):
        raise Refused(f"level {lv['level']} (from {lv['from']}) keeps the owner's rulings for the owner: the owner runs "
                      f"`python3 .charter/bin/charter {verb} {target} {status}` themselves")
    quote = " ".join((quote or "").split())
    if len(quote) < MIN_QUOTE:
        raise Refused(f"--quote carries the owner's own words, as typed, at least {MIN_QUOTE} characters; "
                      "the delegate transcribes an answer the owner gave, never one an agent infers")
    paths = {"rule": lambda: [_decision_path(root, target), f"{lib.CHARTER_DIR}/decisions/INDEX.md"],
             "approve": lambda: [_change_path(root, target)], "rail": lambda: [checks.RAILS_FILE]}[verb]()
    rec = {"at": _now(), "by": "charter handover --ask", "verb": verb, "target": target, "status": status,
           "by_decision": by_decision, "note": note, "quote": quote, "session": session, "cwd": str(root),
           "branch": lib.git(root, "branch", "--show-current").stdout.strip(),
           "head": lib.git(root, "rev-parse", "--verify", "-q", "HEAD").stdout.strip() or None, "paths": paths}
    rec["id"] = _id("a", rec["at"], verb, target, status, quote, rec["head"])
    diff, refused = _verb_diff(root, cfg, dict(rec))
    if refused:
        raise Refused(f"`charter {verb} {target} {status}` refuses it now: {refused}")
    _write(_sub(root, ASKS) / f"{rec['id']}.json", rec)
    return rec


def _decision_path(root: Path, did: str) -> str:
    d = lib.decisions(root).get(did)
    if not d:
        raise Refused(f"no decision {did} in {lib.CHARTER_DIR}/decisions/")
    return d["_path"]


def _change_path(root: Path, cid: str) -> str:
    c = lib.change_requests(root).get(cid)
    if not c:
        raise Refused(f"no change request {cid} in {lib.CHARTER_DIR}/changes/")
    return c["_path"]


def record_merge(root: Path, pr: int, method: str | None = None) -> dict:
    """Ask the delegate to merge pull request `pr` into the default branch. Refused where the level keeps merges for the
    owner; the watcher checks the rest (the PR is the owner's, CLEAN, green, marked reviewed at its head)."""
    lv = lib.delegate_level(root, branch_too=False)
    if not lib.delegable({"merge"}, lv["level"]):
        raise Refused(f"level {lv['level']} (from {lv['from']}) keeps merges for the owner: the owner merges PR #{pr}")
    if method not in (None, "merge", "squash", "rebase"):
        raise Refused(f"--method is merge, squash or rebase, not {method}")
    rec = {"at": _now(), "by": "charter handover --merge", "pr": int(pr), "method": method, "base": lib.default_branch(root),
           "branch": lib.git(root, "branch", "--show-current").stdout.strip(),
           "head": lib.git(root, "rev-parse", "--verify", "-q", "HEAD").stdout.strip() or None}
    rec["id"] = _id("m", rec["at"], rec["pr"])
    for old in _merges(root):   # one request per pull request: a new one replaces the old
        if old.get("pr") == rec["pr"]:
            (_sub(root, MERGES) / f"{old['pr']}.json").unlink(missing_ok=True)
    _write(_sub(root, MERGES) / f"{rec['pr']}.json", rec)
    return rec


# ---------------------------------------------------------------- the delegate's acts

def _trailer(level: str, by: str, item_id: str) -> str:
    return f"{lib.DELEGATE_TRAILER}: level {level}; judged by {by}; {item_id}"


def commit(root: Path, cfg: dict, item_id: str, by: str, reason: str) -> dict:
    """Commit a recorded handover as the delegate: exactly the blobs recorded (in the index and the tree), with the
    message recorded, the delegate as committer and the owner as author, and a trailer naming the verdict."""
    refuse_in_session("charter delegate commit")
    rec = lib.load_handover(root)
    if not rec or rec.get("id") != item_id:
        raise Refused(f"no handover {item_id} waits in {root}")
    v = load_verdict(root, item_id)
    if v and v.get("result") in DONE:
        raise Refused(f"handover {item_id} is already {v['result']}")
    lv = lib.delegate_level(root)
    p = _plan_commit(root, cfg, rec, lv)
    if not p["delegable"]:
        raise Refused(f"handover {item_id}: {p['why_not']}")
    if (lib.git_dir(root) / "index.lock").exists():
        raise Busy("another git process holds the index")
    paths, msg = p["paths"], str(rec.get("message") or "Staged changes")
    r = subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", msg, "-m", _trailer(lv["level"], by, item_id), "--", *paths],
                       env=lib.delegate_env(), capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        out = (r.stdout + r.stderr).strip()
        if "index.lock" in out:
            raise Busy(out)
        return settle(root, item_id, "failed", by, f"git refused the commit: {out[-1500:]}")
    sha = lib.git(root, "rev-parse", "HEAD").stdout.strip()
    lib.clear_handover(root)
    return settle(root, item_id, "committed", by, reason, sha=sha, level=lv["level"], paths=paths, kinds=p["kinds"])


def perform(root: Path, cfg: dict, item_id: str, by: str, reason: str) -> dict:
    """Write and commit a recorded ask as the delegate (`charter rule|approve|rail`, owner switch never set)."""
    import owner
    refuse_in_session("charter delegate perform")
    rec = next((r for r in _asks(root) if r.get("id") == item_id), None)
    if not rec:
        raise Refused(f"no ask {item_id} waits in {root}")
    lv = lib.delegate_level(root)
    p = _plan_ask(root, cfg, rec, lv)
    if not p["delegable"]:
        raise Refused(f"ask {item_id}: {p['why_not']}")
    if (lib.git_dir(root) / "index.lock").exists():
        raise Busy("another git process holds the index")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            _call_verb(root, cfg, rec, dry_run=False, trailer=_trailer(lv["level"], by, item_id), delegate=True)
    except owner.Refused as e:
        return settle(root, item_id, "failed", by, f"`charter {rec['verb']}` refused: {e}")
    sha = lib.git(root, "rev-parse", "HEAD").stdout.strip()
    (_sub(root, ASKS) / f"{item_id}.json").unlink(missing_ok=True)
    return settle(root, item_id, "performed", by, reason, sha=sha, level=lv["level"],
                  act=f"{rec['verb']} {rec['target']} {rec['status']}")


def drop_merge(root: Path, item_id: str) -> None:
    for rec in _merges(root):
        if rec.get("id") == item_id:
            (_sub(root, MERGES) / f"{rec['pr']}.json").unlink(missing_ok=True)


# ---------------------------------------------------------------- waiting on a verdict

def fallback(root: Path, item: dict) -> str:
    """What the owner runs when the delegate hands an item back or does not answer."""
    if item.get("type") == "ask":
        return " ".join(["python3", str(root / lib.CHARTER_BIN), item["verb"], item["target"], item["status"]]
                        + (["--by", item["by_decision"]] if item.get("by_decision") else []))
    if item.get("type") == "merge":
        return f"gh pr merge {item['pr']}" + (f" --{item['method']}" if item.get("method") else "")
    return lib.owner_line(root)


def wait(root: Path, item: dict, timeout: int, poll: float = 3.0, out=None) -> int:
    """Wait for the delegate's verdict on `item`: 0 when it acted, 3 when it handed the item back, 4 when it did not
    answer in time. Each but 0 ends with the owner's fallback, alone on the last line."""
    import time
    out = out or sys.stdout
    deadline = time.monotonic() + max(0, timeout)
    while True:
        v = load_verdict(root, item["id"])
        if v:
            break
        if time.monotonic() >= deadline:
            print(f"the delegate gave no verdict on {item['id']} in {timeout} s (is the watcher installed? `charter-delegate status`). "
                  "The owner's line:", file=out)
            print(fallback(root, item), file=out)
            return 4
        time.sleep(poll)
    if v["result"] in DONE:
        print(f"the delegate {v['result']} {item['id']}" + (f": {v['sha'][:10]}" if v.get("sha") else "") + f" ({v.get('reason') or 'no reason given'})", file=out)
        return 0
    print(f"the delegate handed {item['id']} back to the owner ({v['result']}, judged by {v.get('by')}): {v.get('reason')}", file=out)
    print("The owner's line:", file=out)
    print(fallback(root, item), file=out)
    return 3


# ---------------------------------------------------------------- the owner sets the level

def worktree_on(root: Path, branch: str) -> Path | None:
    """The checkout of this repository that has `branch` checked out, if any."""
    cur = None
    for line in lib.git(root, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            cur = Path(line[9:])
        elif line == f"branch refs/heads/{branch}" and cur is not None:
            return cur
    return None


def with_keys(text: str, updates: dict) -> str:
    """`text`, a JSON object, with top-level keys set; a one-line edit where the file allows it, so the owner's diff shows
    only what changed, else the whole object re-indented."""
    obj = json.loads(text)
    want = json.loads(json.dumps(obj))
    want.update(updates)
    new = text
    for k, v in updates.items():
        val = json.dumps(v, ensure_ascii=False)
        pat = re.compile(r'^(\s*)"' + re.escape(k) + r'"\s*:\s*(\{[^{}\n]*\}|"(?:[^"\\\n]|\\.)*"|\[[^\[\]\n]*\]|[^,\n{}\[]+?)(\s*,?\s*)$', re.M)
        if k in obj and pat.search(new):
            new = pat.sub(lambda m: f'{m.group(1)}"{k}": {val}{m.group(3)}', new, count=1)
        elif k not in obj:
            m = re.search(r'^(\s*)"owner"\s*:[^\n]*,\s*$', new, re.M) or re.search(r'^(\s*)"track"\s*:[^\n]*,\s*$', new, re.M)
            if m:
                new = new[:m.end()] + f'\n{m.group(1)}"{k}": {val},' + new[m.end():]
    try:
        if json.loads(new) == want:
            return new
    except ValueError:
        pass
    return json.dumps(want, indent=2, ensure_ascii=False) + "\n"


def set_config(root: Path, updates: dict, message: str, trailer: str | None = None) -> str:
    """Commit `updates` to charter/config.json on the default branch, as the owner: refused to an agent (inside Claude Code
    without the owner switch). Where a checkout has the default branch, the commit is made there, through the git hook;
    its config must have no uncommitted change. Where none has, the commit is written onto the branch directly, as git's
    plumbing does, leaving every checkout as it is. Returns the commit, or "" when nothing changed."""
    if lib.in_claude_code() and not lib.owner_session():
        raise Refused("this is the owner's act, refused to an agent; the owner runs it from their own prompt (`!`) with the "
                      "owner switch, or from a terminal or the owner desk")
    base = lib.default_branch(root)
    if not base:
        raise Refused("this repository has no main or master branch to set it on")
    rp = f"{lib.CHARTER_DIR}/config.json"
    cur = lib.git(root, "show", f"refs/heads/{base}:{rp}")
    if cur.returncode != 0:
        raise Refused(f"{rp} is not committed on {base}")
    new = with_keys(cur.stdout, updates)
    if new == cur.stdout:
        return ""
    probs = [p for p in lib.config_from(json.loads(new))[lib.PROBLEMS] if any(f"`{k}" in p for k in updates)]
    if probs:
        raise Refused("; ".join(probs))
    msg = [message] + ([trailer] if trailer else [])
    wt = worktree_on(root, base)
    if wt is not None:
        if lib.git(wt, "status", "--porcelain", "--", rp).stdout.strip():
            raise Refused(f"{wt / rp} has uncommitted changes; commit or discard them first")
        (wt / rp).write_text(new, encoding="utf-8")
        lib.git(wt, "add", "--", rp, check=True)
        r = subprocess.run(["git", "-C", str(wt), "commit", "-q"] + [x for m in msg for x in ("-m", m)] + ["--", rp],
                           capture_output=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            (wt / rp).write_text(cur.stdout, encoding="utf-8")
            lib.git(wt, "reset", "-q", "--", rp)
            raise Refused("the commit was refused, so nothing changed:\n" + (r.stdout + r.stderr).strip())
        return lib.git(wt, "rev-parse", "HEAD").stdout.strip()
    # no checkout has the branch: a commit on top of its tip, through a private index
    import tempfile
    tip = lib.git(root, "rev-parse", f"refs/heads/{base}").stdout.strip()
    blob_r = subprocess.run(["git", "-C", str(root), "hash-object", "-w", "--stdin"], input=new, capture_output=True, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="charter-level-") as td:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(td) / "index"))
        run = lambda *a, **k: subprocess.run(["git", "-C", str(root), *a], env=env, capture_output=True, encoding="utf-8", **k)
        steps = [run("read-tree", tip), run("update-index", "--cacheinfo", f"100644,{blob_r.stdout.strip()},{rp}")]
        tree = run("write-tree")
        steps.append(tree)
        c = run("commit-tree", tree.stdout.strip(), "-p", tip, *[x for m in msg for x in ("-m", m)])
        steps.append(c)
        if blob_r.returncode != 0 or any(s.returncode != 0 for s in steps):
            raise Refused("git refused the commit, so nothing changed: " + " ".join((s.stderr or "").strip() for s in steps if s.returncode))
        u = run("update-ref", f"refs/heads/{base}", c.stdout.strip(), tip)
        if u.returncode != 0:
            raise Refused(f"{base} moved while the commit was made, so nothing changed: {u.stderr.strip()}")
        return c.stdout.strip()


def set_level(root: Path, level: str, trailer: str | None = None) -> str:
    if level not in lib.DELEGATE_LEVELS:
        raise Refused(f"a level is one of {', '.join(lib.DELEGATE_LEVELS)}, not {level}")
    before = lib.delegate_level(root, branch_too=False)
    base = lib.default_branch(root)
    cur = lib.committed_level(root, f"refs/heads/{base}")[0] if base else None
    obj = {}
    if base:
        r = lib.git(root, "show", f"refs/heads/{base}:{lib.CHARTER_DIR}/config.json")
        with contextlib.suppress(ValueError):
            obj = json.loads(r.stdout) if r.returncode == 0 else {}
    d = dict(obj.get("delegate") or {}) if isinstance(obj.get("delegate"), dict) else {}
    d["level"] = level
    return set_config(root, {"delegate": d}, f"charter: delegate level {cur or before['level']} -> {level}", trailer)
