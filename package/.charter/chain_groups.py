"""Groups of a continuous chain and their review (docs/design/continuous-chain.md § Groups and their review).

A group is the units of one item of `charter/rails.md`, or of one tasket `group:` where the project keeps no rails
file. A chain works one group at a time, on one branch. When the road goes on to another group, or ends, the group's
whole range of commits is reviewed by a reviewer of another model family (`codex exec review --base <start>`), in a
worktree of its own at the group's last commit. The session after answers every finding before any unit of the next
group starts, and the group is cleared at that session's last commit: a point the owner can merge up to. A defect
found later in an earlier group is fixed forward on the same branch, so no group ever needs a rebase or a merge.

What holds it is code: `charter unit start` refuses, in a chain session, a unit of a group that has not started;
`chain next` starts the review instead of the next session; the review's runner launches the next session; and
`chain next` refuses the answering session's handoff until `## Review` answers every finding.

State, in chain.json (written by `chain start`, `chain next`, `chain resume` and the review's runner, one at a time):
  review, review_effort, review_timeout_s   codex | off | a command template with {base} and {out}
  groups   [{k, key, start, first_session, state, end, base, reviewed_to, after, next_unit, last_session,
             findings, fix_session, cleared}]; state: working -> reviewing -> fixing -> cleared, or review-failed
  <id>/gNN/review.md    what the reviewer returned, paths relative to the repository
  <id>/gNN/review.log   the runner's output and the reviewer's
  <id>/gNN/review.pid   the runner's process while it runs
Python 3 standard library only."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import chain   # chain.py imports this module; every use of it here is at call time
import checks
import lib
import rails

# codex exec review, 0.147.0: "- [P1] <title> — <path>:<line>-<line>", then the body, indented (measured 2026-10-04)
FINDING_RE = re.compile(r"^\s*[-*]?\s*\[(P\d)\]\s*(.*)$")
WHERE_RE = re.compile(r"^(.*\S)\s+[—–]\s+(\S+?:\d+(?:-\d+)?)\s*$")


def current(ch: dict) -> dict | None:
    """The group the chain works now; None for a chain without groups (review off, or started before 0.4.9)."""
    gs = ch.get("groups") or []
    return gs[-1] if gs else None


def keys(ch: dict) -> list[str]:
    return [g["key"] for g in ch.get("groups") or []]


def label(key: str) -> str:
    return f"`{key or '(none)'}`"


def group_dir(root: Path, cid: str, k: int) -> Path:
    return chain.chain_dir(root, cid) / f"g{k:02d}"


def group_of(root: Path, cfg: dict, unit: dict) -> str:
    """The group a unit belongs to: its first open rail in the road's order, as `charter next` ranks it, else its first
    rail; without a rails file, its tasket `group:`; '' when it has neither."""
    loaded = rails.load(root, cfg)
    if loaded is None:
        return str(unit.get("group") or "").strip()
    items, _ = loaded
    on = [r for r in rails.rails_of(unit, rails.config(cfg)["keys"], items) if r in items]
    if not on:
        return ""
    seq = {rid: k for k, (rid, _) in enumerate(rails.ordered(items))}
    live = [r for r in on if items[r]["status"] not in rails.CLOSED]
    return min(live or on, key=lambda r: seq[r])


def unit_group(root: Path, uid: str) -> str | None:
    """The group of tasket uid; None when there is no such tasket."""
    u = lib.taskets(root).get(uid)
    return None if u is None else group_of(root, lib.load_config(root), u)


def resolve_review(name: str) -> tuple[str, str]:
    """(mode, detail): mode codex, off or command; ("", why) when the setting cannot work. `auto` is codex when it is
    on PATH, else off, and says so."""
    name = (name or "auto").strip()
    if name in ("auto", "codex"):
        exe = shutil.which("codex")
        if exe:
            return "codex", exe
        return ("off", "codex is not on PATH") if name == "auto" else (
            "", "`codex` is not on PATH: install the Codex CLI, or pass `--review off` to run the chain without group reviews")
    if name == "off":
        return "off", "off"
    if "{out}" in name:
        return "command", name
    return "", f"review {name!r} is not auto, codex, off or a command template with {{out}}"


def plan_line(mode: str, why: str, effort: str, first_key: str) -> str:
    if mode == "off":
        return f"review: off ({why}); the chain works the road without group boundaries"
    who = f"codex, effort {effort}" if mode == "codex" else "the configured review command"
    return (f"review: {who}, at the end of each group (the items of {rails.FILE}, else the tasket `group:`); "
            f"the chain starts on group {label(first_key)}")


def begin(root: Path, ch: dict, unit: str) -> None:
    """At `chain start`: the first group is the start unit's."""
    if ch.get("review") != "off":
        ch["groups"] = [{"k": 1, "key": unit_group(root, unit) or "", "start": chain.head(root), "first_session": 1, "state": "working"}]


# ---------------------------------------------------------------- what a session may do

def unit_start_refusal(root: Path, uid: str) -> str:
    """Why `charter unit start uid` is refused in this Claude Code session, or ''. Only a chain session is concerned,
    and only a unit of a group that has not started yet: units of the current group and of earlier ones (a fix
    carried forward) start as always."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    j = chain.joined(root, sid) if sid else None
    if not j:
        return ""
    ch, n, rec = j
    g = current(ch)
    if not g or ch.get("state") != "running" or rec.get("closed_at"):
        return ""
    key = unit_group(root, uid)
    if key is None or key in keys(ch):
        return ""
    hp = chain.link_dir(root, ch["id"], n) / "handoff.md"
    if g["state"] == "fixing":
        return (f"charter chain: this session answers the review of group {label(g['key'])}; unit {uid} is on group {label(key)}, "
                f"which starts in the next session. Answer every finding under `## Review` in {hp}, then hand over with "
                f"`next_unit: {uid}` (`python3 .charter/bin/charter chain next`).")
    return (f"charter chain: unit {uid} is on group {label(key)}, and this session works group {label(g['key'])}. A group ends with "
            f"its review before the next one starts: commit, write {hp} with `next_unit: {uid}`, run "
            "`python3 .charter/bin/charter chain next`, end your turn. Handing over here is allowed under the hand-over line.")


def ends_group(root: Path, ch: dict, status: str, next_unit: str) -> bool:
    """A handover that ends the session's group, or that answered its review and leaves it, is not early, whatever
    the context. An answering session that goes on inside its group is held to the early rule like any other."""
    g = current(ch)
    if not g:
        return False
    return status == "complete" or (status == "continue" and (unit_group(root, next_unit) or "") not in keys(ch)) or (
        g["state"] == "fixing" and status == "continue" and (unit_group(root, next_unit) or "") != g["key"])


def needs_commit(root: Path, ch: dict, status: str, next_unit: str) -> bool:
    """A group ends at a commit: the review sees the commit and the owner merges up to it, so nothing uncommitted may
    cross a group's end, nor the end of the session that answers its review."""
    g = current(ch)
    return bool(g) and status in ("continue", "complete") and (g["state"] == "fixing" or ends_group(root, ch, status, next_unit))


ANSWER_RE = re.compile(r"^\s*[-*]?\s*(R\d+)\b[\s:.,—–-]*(fixed|dismissed|halt)\b", re.I)


def check_review(root: Path, ch: dict, n: int, text: str) -> list[str]:
    """What keeps the answering session's handoff from being accepted: under `## Review`, one line per finding that
    starts with its id and then the answer, `fixed` with a commit made after the reviewed range, `dismissed` with a
    path:line or a `$ command`. A handoff with `status: halt` is not held to it: the session after the owner's answer
    is given the whole review again. That a fix fixes, or a dismissal holds, is the next session's to verify."""
    g = current(ch)
    if not g or g.get("fix_session") != n or not g.get("findings"):
        return []
    fields, _, body = lib.split_frontmatter(text)
    if str(fields.get("status", "")).strip() == "halt":
        return []
    answers: dict[str, list[tuple[str, str]]] = {}
    for line in lib.section(body, "Review").splitlines():
        m = ANSWER_RE.match(line)
        if m:
            answers.setdefault(m.group(1).upper(), []).append((m.group(2).lower(), line))
    problems: list[str] = []
    for f in g["findings"]:
        got = answers.get(f["id"]) or []
        if len(got) != 1:
            problems.append(f"`## Review` answers {f['id']} ([{f['sev']}] {f['title'][:70]}) {len(got)} times; one line, "
                            f"starting `{f['id']} fixed`, `{f['id']} dismissed` or `{f['id']} halt`")
            continue
        word, line = got[0]
        k = checks.classify_anchors(root, line)
        if k["bad"]:
            problems.append(f"`## Review`, {f['id']}: anchors that do not resolve: {', '.join(k['bad'][:3])}")
        elif word == "fixed" and any(_after(root, g["end"], s) for s in k["sha"]):
            continue
        elif word == "dismissed" and (k["fileline"] or k["run"]):
            continue
        elif word == "halt":
            problems.append(f"`## Review`, {f['id']}: `halt` needs the handoff's `status: halt`, with the question under `## Halt`")
        else:
            problems.append(f"`## Review`, {f['id']}: answer with `{f['id']} fixed <commit after {g['end'][:7]}>`, "
                            f"`{f['id']} dismissed <path:line or $ command> <why>`, or `{f['id']} halt <why>` with `status: halt`")
    return problems


def _after(root: Path, end: str, sha: str) -> bool:
    """A commit that descends from the reviewed range's last commit, is not that commit, and is on the chain's branch
    (an ancestor of HEAD): a fix on a side branch, or one reset away, fixes nothing the group is cleared at."""
    full = lib.git(root, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}").stdout.strip()
    return (bool(full) and full != end and lib.git(root, "merge-base", "--is-ancestor", end, full).returncode == 0
            and lib.git(root, "merge-base", "--is-ancestor", full, "HEAD").returncode == 0)


def crossing(root: Path, ch: dict, moved: list[tuple[str, str]], changed: list[str]) -> list[str]:
    """Facts lines for work that went round the boundary `charter unit start` holds: a unit of a group that has not
    started that moved, a unit whose group changed in the session (its `rail:` or `group:` edited), and a changed path
    that only units of groups that have not started name in their perimeter. `moved` is (unit id, its text at the
    session's start); `changed` is every path the session's commits touched."""
    g = current(ch)
    if not g:
        return []
    cfg, units, known = lib.load_config(root), lib.taskets(root), keys(ch)
    out = []
    for uid, before in moved:
        now_key = group_of(root, cfg, units[uid]) if uid in units else ""
        was = group_of(root, cfg, lib.split_frontmatter(before)[0]) if before else None
        if was is not None and was != now_key:
            out.append(f"- {uid} moved from group {label(was)} to group {label(now_key)} in this session")
        elif now_key not in known:
            out.append(f"- {uid} is on group {label(now_key)}, which has not started")
    later = {uid: u for uid, u in units.items() if group_of(root, cfg, u) not in known and rails.is_open(u, cfg)}
    ours = [u for uid, u in units.items() if uid not in later]
    for p in changed:
        names = [uid for uid, u in later.items() if lib.matches_any(p, lib.as_list(u.get("perimeter")))]
        if names and not p.startswith(lib.TASKETS_DIR + "/") and not any(lib.matches_any(p, lib.as_list(u.get("perimeter"))) for u in ours):
            out.append(f"- {p} is only in the perimeter of {', '.join(names)}, on a group that has not started")
    if not out:
        return []
    where = ("and no review covers it: the next group starts at this session's last commit" if g["state"] == "fixing"
             else f"so the review of {label(g['key'])} covers it")
    return [f"Group boundary crossed in a session of group {label(g['key'])}, {where}:"] + out


# ---------------------------------------------------------------- the briefing

def briefing_lines(root: Path, ch: dict, n: int) -> list[str]:
    """The briefing's part on groups: the session's group, and the review it answers, if any."""
    g = current(ch)
    if not g:
        return []
    if g["state"] == "fixing" and g.get("fix_session") == n:
        return [f"## Review of group {label(g['key'])}", ""] + _review_lines(root, ch, g)
    before = ""
    if g["k"] > 1 and g.get("first_session") == n:
        p = ch["groups"][-2]
        how = (f"{len(p['findings'])} review finding(s) answered by session {p['fix_session']}" if p.get("findings") else
               "the owner skipped its review" if p.get("skipped") else "its review found nothing")
        before = f"Group {label(p['key'])} is cleared at {(p.get('cleared') or '')[:7]} ({how}). "
    return ["## Group", "", before + f"You work group {label(g['key'])}. A unit of a group that has not started waits for this "
            "group's review: `charter unit start` refuses it, and you hand over with it as `next_unit:` (chain rules, section 6).", ""]


def _review_lines(root: Path, ch: dict, g: dict) -> list[str]:
    then = ("hand over with `status: complete`: the session before you found the road finished" if g.get("after") == "complete" else
            f"hand over with `next_unit: {g.get('next_unit')}`, the unit the road goes on with")
    L = [f"Group {label(g['key'])} ended with session {g.get('last_session')}, and its commits {g['base'][:7]}..{g['end'][:7]} were "
         f"reviewed by {_who(ch)}. This session answers that review, after verifying its predecessor (chain rules, section 1), "
         "and starts no unit of another group: `charter unit start` refuses one.", "",
         "- Open the code each finding cites and judge it against the code, not against the finding's wording.",
         "- A real defect: fix it inside its unit's perimeter (reopen the unit if it is done, with a dated `## Log` line), and commit.",
         "- Not a defect: dismiss it with the `path:line` or the `$ command` that shows why.",
         "- A defect that needs the owner: halt (chain rules, section 5).", "",
         "Under `## Review` in your handoff, one line per finding, starting with its id: `R1 fixed <commit>`, "
         "`R2 dismissed <path:line> <why>`. `chain next` refuses a handoff that leaves one unanswered, and anything left "
         f"uncommitted: the group ends at your last commit. On a halt, answer what you could. Then {then}.", "",
         f"### The review (verbatim; in full at {group_dir(root, ch['id'], g['k']) / 'review.md'})", ""]
    for f in g["findings"]:
        L += [f"{f['id']}. {f['text'].strip()}", ""]
    return L


def _who(ch: dict) -> str:
    if ch.get("review") == "codex":
        return f"Codex (`codex exec review`, effort {ch.get('review_effort')})"
    return "the review command"


# ---------------------------------------------------------------- the review

def parse(text: str) -> list[dict]:
    """The findings of a review, numbered R1..Rn: severity, title, location, and the block as written. A text that names
    a severity but no finding line is one finding, read whole, so a change in the reviewer's format is never a silent
    'nothing found'."""
    found: list[dict] = []
    for line in text.splitlines():
        m = FINDING_RE.match(line)
        if m:
            title, where = m.group(2).strip(), ""
            w = WHERE_RE.match(title)
            if w:
                title, where = w.group(1), w.group(2)
            found.append({"sev": m.group(1), "title": title, "where": where, "lines": [line.strip()]})
        elif found and line.strip():
            found[-1]["lines"].append("   " + line.strip())
        elif found and not line.strip() and len(found[-1]["lines"]) > 1:
            found[-1]["lines"].append("")
    if not found and re.search(r"\[P\d\]", text):
        found = [{"sev": "P?", "title": "a review this chain could not split into findings: read it whole", "where": "",
                  "lines": [text.strip()]}]
    return [{"id": f"R{i}", "sev": f["sev"], "title": f["title"], "where": f["where"], "text": "\n".join(f["lines"]).strip()}
            for i, f in enumerate(found, 1)]


def counts(findings: list[dict]) -> str:
    c: dict[str, int] = {}
    for f in findings:
        c[f["sev"]] = c.get(f["sev"], 0) + 1
    return ", ".join(f"{k} {v}" for k, v in sorted(c.items()))


def review_command(ch: dict, base: str, end: str, tree: Path, out: Path) -> list[str]:
    """The reviewer's command line. Codex's built-in review takes no prompt with `--base` (codex-cli 0.147.0 refuses
    the pair), so the review is Codex's own, over the diff from the group's start to the worktree's HEAD."""
    if ch.get("review") == "codex":
        exe = shutil.which("codex") or "codex"
        return [exe, "exec", "review", "--base", base, "-c", f"model_reasoning_effort={ch.get('review_effort') or 'high'}", "-o", str(out)]
    return [a.format(base=base, head=end, out=str(out), root=str(tree)) for a in shlex.split(ch["review"])]


def review_tmp(root: Path, ch: dict) -> Path:
    """The review worktree's directory: one per chain, which only one runner uses at a time. The repository's hash is
    in the name because a chain id is a timestamp, and two repositories can start a chain in the same second
    (cross-review, 2026-10-04)."""
    repo = hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:8]
    return Path(tempfile.gettempdir()) / f"charter-review-{repo}-{ch['id']}"


def run_review(root: Path, ch: dict, g: dict, d: Path) -> tuple[bool, str, str]:
    """(ok, review text with repository-relative paths, why not). The reviewer runs in a detached worktree at the
    group's last commit, so it sees the committed group and nothing of the live tree, where the chain goes on."""
    # what a runner killed before its cleanup left (the directory and its .git/worktrees entry) goes first
    tmp = review_tmp(root, ch)
    _drop_tree(root, tmp)
    tmp.mkdir(parents=True)
    tree, out = tmp / "tree", d / "review.out"
    out.unlink(missing_ok=True)
    try:
        r = lib.git(root, "worktree", "add", "--detach", str(tree), g["end"])
        if r.returncode != 0:
            return False, "", f"`git worktree add` failed: {r.stderr.strip()[:300]}"
        cmd = review_command(ch, g["base"], g["end"], tree, out)
        timeout = int(ch.get("review_timeout_s") or 1800)
        try:
            with (d / "review.log").open("ab") as log:
                p = subprocess.Popen(cmd, cwd=str(tree), stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        except OSError as e:
            return False, "", f"the reviewer did not start: {e!r}"
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(OSError):
                os.killpg(p.pid, signal.SIGKILL)   # the reviewer and what it started, not the reviewer alone
            p.wait()
            return False, "", f"the reviewer ran past {timeout} s (`chain.review_timeout_s`)"
        text = out.read_text(encoding="utf-8", errors="replace").strip() if out.exists() else ""
        if p.returncode != 0 or not text:
            tail = (d / "review.log").read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
            return False, "", f"the reviewer exited {p.returncode}" + ("" if text else " and returned nothing") + (f": {' / '.join(tail)[:300]}" if tail else "")
        for prefix in sorted({str(tree), os.path.realpath(tree)}, key=len, reverse=True):
            text = text.replace(prefix + os.sep, "").replace(prefix, ".")
        out.unlink(missing_ok=True)   # the caller keeps the text as review.md; a failed run leaves its output to read
        return True, text, ""
    finally:
        _drop_tree(root, tmp)


def _drop_tree(root: Path, tmp: Path) -> None:
    if tmp.exists():
        lib.git(root, "worktree", "remove", "--force", str(tmp / "tree"))
        shutil.rmtree(tmp, ignore_errors=True)
    lib.git(root, "worktree", "prune")


def start_review(root: Path, ch: dict, n: int, after: str, next_unit: str, note: str = "") -> None:
    """Session n ended the group (or the road): review the group's commits since its start, or since its last review,
    in a runner of its own. The runner launches the next session; `chain next` returns at once."""
    g = current(ch)
    end = chain.head(root)
    base = g.get("reviewed_to") or g["start"]
    g.update(state="reviewing", end=end, base=base, after=after, next_unit=next_unit, last_session=n, note=note, review_started=chain.now())
    if base == end:
        clear(root, ch, n, end, f"nothing to review: no commit since {base[:7]}")
        return
    d = group_dir(root, ch["id"], g["k"])
    d.mkdir(parents=True, exist_ok=True)
    chain.save(root, ch)   # before the runner starts: it reads the state, and from then on only it writes
    chain.event(root, ch["id"], "chain", "review", f"group {label(g['key'])}, sessions {g['first_session']}-{n}, "
                f"{base[:7]}..{end[:7]}: {_who(ch)} started; the next session starts when it ends")
    cmd = [sys.executable, "-B", str(root / lib.TOOL_DIR / "bin" / "charter"), "--root", str(root), "chain", "review-run",
           ch["id"], "--group", str(g["k"])]
    try:
        with (d / "review.log").open("ab") as log:
            subprocess.Popen(cmd, cwd=str(root), stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    except OSError as e:
        g["state"] = "review-failed"
        chain.halt(root, ch, f"the review of group {label(g['key'])} could not start: {e!r}")


def review_running(root: Path, ch: dict) -> bool:
    """A runner is alive for the current group, or was started under a minute ago and has not written its pid yet."""
    g = current(ch)
    if not g or g["state"] != "reviewing":
        return False
    p = group_dir(root, ch["id"], g["k"]) / "review.pid"
    try:
        os.kill(int(p.read_text().strip()), 0)
        return True
    except (OSError, ValueError):
        pass
    try:
        started = dt.datetime.fromisoformat(g.get("review_started") or "")
    except ValueError:
        return False
    return not p.exists() and (dt.datetime.now() - started).total_seconds() < 60


def cmd_review_run(root: Path, a) -> int:
    """The review's runner (started by `chain next`): review, record, then launch the session that answers it."""
    ch = chain.load(root, a.id)
    g = next((x for x in ch.get("groups") or [] if x["k"] == a.group), None)
    if not g or g["state"] != "reviewing" or g is not current(ch):
        print(f"chain {a.id}: group {a.group} is not under review")
        return 1
    d = group_dir(root, ch["id"], g["k"])
    pid = d / "review.pid"
    pid.write_text(f"{os.getpid()}\n")
    try:   # the pid stays until the state is saved, so `chain resume` never starts a second runner meanwhile
        try:
            ok, text, why = run_review(root, ch, g, d)
        except Exception as e:   # a runner that dies leaves the chain waiting on nothing: halt it, with the reason
            ok, text, why = False, "", f"the runner failed: {e!r}"
        with chain.chain_lock(root, a.id):
            return _record(root, a.id, d, ok, text, why)
    finally:
        pid.unlink(missing_ok=True)


def _record(root: Path, cid: str, d: Path, ok: bool, text: str, why: str) -> int:
    ch = chain.load(root, cid)   # the owner may have stopped the chain meanwhile: then record, and end nothing
    g = current(ch)
    n, live = int(g["last_session"]), ch.get("state") == "running"
    if not ok:
        g["state"] = "review-failed"
        why = (f"the review of group {label(g['key'])} could not run: {why}. Fix it and `charter chain resume`, which runs it "
               "again, or `charter chain resume --skip-review` to go on without it")
        if live:
            chain.halt(root, ch, why)
        else:
            chain.save(root, ch)
            chain.event(root, ch["id"], "chain", "review-failed", why)
        return 1
    rnd = len(g.get("rounds") or []) + 1
    name = "review.md" if rnd == 1 else f"review-{rnd}.md"
    (d / name).write_text(text + "\n", encoding="utf-8")
    g.update(findings=parse(text), reviewed_to=g["end"], review_file=name)
    if not g["findings"]:
        chain.event(root, ch["id"], "chain", "reviewed", f"group {label(g['key'])}: no findings")
        clear(root, ch, n, g["end"], "its review found nothing")
        return 0
    note = g.pop("note", "") or ""
    g.update(state="fixing", fix_session=n + 1)
    chain.save(root, ch)
    chain.event(root, ch["id"], "chain", "reviewed", f"group {label(g['key'])}: {len(g['findings'])} finding(s) ({counts(g['findings'])}); "
                f"session {n + 1} answers them ({d / name})")
    launch_next(root, ch, n, note)
    return 0


def clear(root: Path, ch: dict, n: int, at: str, why: str) -> None:
    """The group is done and reviewed at commit `at`: record it, then end the chain or open the next group. The owner's
    note from a resume, kept on the group while its review ran, goes to the next session."""
    g = current(ch)
    note = g.pop("note", "") or ""
    g.update(state="cleared", cleared=at)
    chain.event(root, ch["id"], "chain", "cleared", f"group {label(g['key'])} is cleared at {at[:7]} ({why}); "
                f"the owner can merge up to it")
    if g.get("after") == "complete":
        if ch.get("state") == "running":
            chain.halt(root, ch, f"session {n} found the road finished, and every group is reviewed", state="complete")
        else:
            chain.save(root, ch)   # stopped meanwhile: `chain resume` completes it (on_resume)
        return
    key = unit_group(root, g.get("next_unit") or "") or ""
    ch["groups"].append({"k": g["k"] + 1, "key": key, "start": at, "first_session": n + 1, "state": "working"})
    chain.save(root, ch)
    launch_next(root, ch, n, note)


def launch_next(root: Path, ch: dict, n: int, note: str = "") -> None:
    """Launch session n + 1 unless the chain stopped while the review ran, or reached its session limit."""
    ch = chain.load(root, ch["id"])
    if ch.get("state") != "running":
        return
    if (chain.chain_dir(root, ch["id"]) / "stop").exists():
        chain.halt(root, ch, "stopped by the owner", state="stopped")
    elif n >= int(ch["max_sessions"]):
        chain.halt(root, ch, f"reached max_sessions ({ch['max_sessions']}); the owner resumes with `charter chain resume`")
    else:
        chain.start_link(root, ch, n + 1, chain.prev_material(root, ch, n), note)


# ---------------------------------------------------------------- the chain's moves

def advance(root: Path, ch: dict, n: int, status: str, next_unit: str) -> None:
    """Session n handed over with continue or complete, and nothing halts the chain: review the group it ended,
    clear the group it answered the review of, or launch the next session."""
    g = current(ch)
    if not g:
        if status == "complete":
            chain.halt(root, ch, f"session {n} found the road finished", state="complete")
        else:
            chain.start_link(root, ch, n + 1, chain.prev_material(root, ch, n))
        return
    if g["state"] == "fixing":
        if status == "continue" and (unit_group(root, next_unit) or "") in keys(ch):
            # the group has work left: its next review starts where this one ended, and this round is kept
            g.setdefault("rounds", []).append({x: g.pop(x) for x in ("base", "end", "findings", "fix_session", "review_file") if x in g})
            g["state"] = "working"
            chain.save(root, ch)
            chain.start_link(root, ch, n + 1, chain.prev_material(root, ch, n))
            return
        g.update(after=status, next_unit=next_unit)
        clear(root, ch, n, chain.head(root), f"session {n} answered every finding")
        return
    if status == "complete" or (unit_group(root, next_unit) or "") not in keys(ch):
        start_review(root, ch, n, status, next_unit)
        return
    chain.start_link(root, ch, n + 1, chain.prev_material(root, ch, n))


def on_resume(root: Path, ch: dict, n: int, note: str, skip: bool) -> bool | None:
    """`chain resume` where groups decide what comes next: True or False when they launched (or started a review),
    None when the caller launches session n + 1 as always."""
    g = current(ch)
    if not g:
        return None
    if g["state"] in ("reviewing", "review-failed"):
        if skip:
            g.update(skipped=True, note=note)
            clear(root, ch, int(g["last_session"]), g["end"], "the owner skipped its review on resuming")
        else:
            start_review(root, ch, int(g["last_session"]), g.get("after") or "continue", g.get("next_unit") or "", note)
        return chain.load(root, ch["id"]).get("state") in ("running", "complete")
    if g["state"] == "cleared" and g.get("after") == "complete":   # the last review ended after a stop
        chain.halt(root, ch, f"session {g.get('last_session')} found the road finished, and every group is reviewed", state="complete")
        return True
    if g["state"] == "fixing":
        g["fix_session"] = n + 1   # a fix session that halted: the next one answers the whole review again
        chain.save(root, ch)
        return None
    hp = chain.link_dir(root, ch["id"], n) / "handoff.md"
    if hp.exists() and not chain.check_handoff(root, ch, n, hp.read_text(encoding="utf-8")):
        status, nu, _ = chain.handoff_status(hp.read_text(encoding="utf-8"))
        nums = chain.link(root, ch["id"], n).get("nums") or {}
        if status == "complete" and (nums.get("probe_failures") or nums.get("gates_blocked")):
            return None   # halted as broken (`chain next`): a session repairs it first, as in a chain without groups (cross-review, 2026-10-04)
        if status == "complete" or (status == "continue" and (unit_group(root, nu) or "") not in keys(ch)):
            start_review(root, ch, n, status, nu, note)   # stopped at a boundary: the review comes first
            return chain.load(root, ch["id"]).get("state") in ("running", "complete")
    return None


# ---------------------------------------------------------------- reports

def rounds(g: dict) -> list[dict]:
    """A group's reviews, oldest first: the rounds it went back to work after, then the current one, if reviewed."""
    cur = {x: g[x] for x in ("base", "end", "findings", "fix_session", "review_file") if x in g}
    return list(g.get("rounds") or []) + ([cur] if "findings" in cur else [])


def status_lines(root: Path, ch: dict) -> list[str]:
    if not ch.get("groups"):
        return []
    L = [f"groups ({_who(ch)}):"]
    for g in ch["groups"]:
        sessions = f"s{g['first_session']:02d}-" + (f"s{int(g['last_session']):02d}" if g.get("last_session") else "")
        rng = f"{g['start'][:7]}.." + (g.get("end") or "")[:7]
        answered = "; ".join(f"{len(r['findings'])} finding(s) ({counts(r['findings'])}), answered by s{int(r['fix_session']):02d}"
                             if r.get("findings") else "no findings" for r in rounds(g))
        what = {"working": "working" + (f" again after its review ({answered})" if g.get("rounds") else ""),
                "reviewing": "under review" if review_running(root, ch) or g is not current(ch) else
                             "review interrupted: `charter chain resume` runs it again",
                "review-failed": "review failed: `charter chain resume` runs it again",
                "fixing": answered,
                "cleared": f"cleared at {(g.get('cleared') or '')[:7]}, " + (
                    "review skipped by the owner" if g.get("skipped") else answered or "nothing to review")}.get(g["state"], g["state"])
        L.append(f"  g{g['k']:02d} {label(g['key'])}  {sessions}  {rng}  {what}")
    return L


def cmd_report(root: Path, a) -> int:
    """Each group's reviews and their answers, as one markdown comment for the pull request the owner opens."""
    ch = chain.load(root, a.id)
    if not ch or not ch.get("groups"):
        print("no chain with group reviews here")
        return 1
    L = [f"## Review: {_who(ch)}, one pass per group (charter chain {ch['id']}, branch `{ch.get('branch')}`)", "",
         "Each group of units was reviewed over its whole range of commits, in a worktree of its own at the group's last "
         "commit; the next session answered every finding before the next group started. A group can be merged up to the "
         "commit it was cleared at (a merge commit or a fast-forward, not a squash, so the later groups still apply).", ""]
    for g in ch["groups"]:
        done = f", cleared at {g['cleared'][:7]}" if g.get("cleared") else f", {g['state']}"
        if not rounds(g) and g.get("skipped"):
            L += [f"### Group {label(g['key'])}: {g['start'][:7]}..{(g.get('end') or '')[:7]}{done}", "", "Review skipped by the owner.", ""]
            continue
        if not rounds(g):
            L += [f"### Group {label(g['key'])}: {g['start'][:7]}..{done}, not reviewed yet", ""]
            continue
        for k, r in enumerate(rounds(g), 1):
            L += [f"### Group {label(g['key'])}" + (f", review {k}" if len(rounds(g)) > 1 else "") + f": {r['base'][:7]}..{r['end'][:7]}{done}", ""]
            rv = group_dir(root, ch["id"], g["k"]) / r.get("review_file", "review.md")
            L += [rv.read_text(encoding="utf-8").strip() if rv.exists() else "(no review recorded)", ""]
            if r.get("findings") and r.get("fix_session"):
                hp = chain.link_dir(root, ch["id"], int(r["fix_session"])) / "handoff.md"
                ans = lib.section(lib.split_frontmatter(hp.read_text(encoding="utf-8"))[2], "Review").strip() if hp.exists() else ""
                L += [f"Answers, session {int(r['fix_session'])} (verbatim):", "", ans or "(no answer recorded yet)", ""]
        if rounds(g) and g.get("skipped"):   # reviewed rounds before it are kept above (cross-review, 2026-10-04)
            L += [f"### Group {label(g['key'])}: {(g.get('base') or '')[:7]}..{(g.get('end') or '')[:7]}{done}", "",
                  "Review of this range skipped by the owner.", ""]
    print("\n".join(L).rstrip())
    return 0
