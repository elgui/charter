"""The continuous chain: a run of Claude Code sessions that work the road one unit after another, each under a
context budget, each verifying its predecessor, each handing over to a fresh session (docs/design/continuous-chain.md).

What holds the chain is code, not a prompt carried from session to session:
- the rules come from `.charter/chain-rules.md`, an owner-only file, injected verbatim into every session by the
  hook when the session joins; the chain halts if the file changes while it runs;
- the owner's mission is stored once and copied verbatim into every briefing;
- the handoff is a fixed template that `chain next` validates before it records anything or launches anyone;
- the predecessor's work is verified mechanically (commits, tree, gates, probes of closed units) by `chain next`,
  and the report lands in the next session's briefing, where that session judges what a gate cannot;
- the budget is measured from the session's transcript by the hooks: past `wrap_pct` the session is told to hand
  over; past `cap_pct` every tool but the handoff, the unit files, git and the charter CLI is refused.

State lives in the git common directory (`<git>/charter/chain/`), shared by worktrees and never committed:
  current                     id of the last chain started
  sessions/<claude session>   "<chain id> <n>": the hooks' lookup, one file per joined session
  <id>/chain.json             settings, mission, rules hash, state (running | waiting | halted | stopped | complete)
  <id>/events.log             one line per event; `chain watch` follows it
  <id>/sNN/briefing.md        what session NN received (written by code)
  <id>/sNN/handoff.md         what session NN hands over (written by the session)
  <id>/sNN/facts.md           the mechanical verification of session NN (written by `chain next`)
  <id>/sNN/link.json          the session's record: ids, heads, peak context, closing
Python 3 standard library only."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import lib
import checks
import chain_groups as groups

RULES = ".charter/chain-rules.md"
TEMPLATE = "charter/templates/handoff.md"
MARK_RE = re.compile(r"^charter-chain: (\S+) session (\d+)\s*$", re.M)
STATUSES = ("continue", "wait", "halt", "complete")
# a chain that is paused for the owner: it waits on an owner act, or it halted, or it is stopped
PAUSED = ("waiting", "halted", "stopped")
SECTIONS = ("Verified", "Done", "State", "Next", "Watch out")
MAX_LINES, MAX_BYTES = 80, 8192
EFFORTS = ("low", "medium", "high", "xhigh", "max")
ONE_M = 1_000_000
# what marks a process as part of this session, which a launched session must not inherit; the rest of
# the environment (auth, provider, CLAUDE_CONFIG_DIR) passes, as the spawn shim's PARENT_SESSION_ENV does
SESSION_ENV = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_ENTRYPOINT",
               "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
               "CLAUDE_PID", "CLAUDE_EFFORT", "CHARTER_OWNER", "CHARTER_UNIT")
# a Bash command that performs an owner act: one of the owner's verbs, or the owner switch set by hand
OWNER_ACT_RE = re.compile(r"\.charter/bin/charter\b[^\n;&|]*?\s(?:rule|approve|rail)\b|\bCHARTER_OWNER\b")
# the owner resumes a paused chain by typing this command; the prompt hook performs it (`owner_prompt`), and nothing else does
RESUME_CMD = "resume-chain"
RESUME_RE = re.compile(r"\A\s*/resume-chain(?=\s|\Z)(.*)\Z", re.S)
RESUME_HOW = "type `/resume-chain ok|skip [note]` in a Claude Code session of your own in this project"
CHARTER_CLI_RE = re.compile(r"^(?:python3?\s+(?:-B\s+)?)?(?:\./)?\.charter/bin/charter(?:\s|$)")


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- state

def base_dir(root: Path) -> Path:
    return lib.shared_state_dir(root) / "chain"


def chain_dir(root: Path, cid: str) -> Path:
    return base_dir(root) / cid


def link_dir(root: Path, cid: str, n: int) -> Path:
    return chain_dir(root, cid) / f"s{n:02d}"


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_json(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"{p.name}.{os.getpid()}.tmp")   # one per writer: a shared name tears under two
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def load(root: Path, cid: str | None = None) -> dict:
    """A chain's record, the last one started when no id is given; {} when there is none."""
    if not cid:
        cur = base_dir(root) / "current"
        cid = cur.read_text().strip() if cur.exists() else ""
    return _read_json(chain_dir(root, cid) / "chain.json") if cid else {}


def save(root: Path, chain: dict) -> None:
    _write_json(chain_dir(root, chain["id"]) / "chain.json", chain)


def link(root: Path, cid: str, n: int) -> dict:
    return _read_json(link_dir(root, cid, n) / "link.json")


def save_link(root: Path, cid: str, n: int, rec: dict) -> None:
    _write_json(link_dir(root, cid, n) / "link.json", rec)


@contextlib.contextmanager
def editing_link(root: Path, cid: str, n: int):
    """Read, change and write a link record under a lock. The hooks of parallel tool calls, the new session's join
    and `chain next` all write it, and a write from a stale copy would drop the others' fields (cross-review,
    2026-10-04). The record is saved when the block ends, early return included."""
    d = link_dir(root, cid, n)
    d.mkdir(parents=True, exist_ok=True)
    with (d / "link.lock").open("a") as f:
        try:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass   # no flock here: the last writer wins, as before
        rec = link(root, cid, n)
        yield rec
        save_link(root, cid, n, rec)


@contextlib.contextmanager
def chain_lock(root: Path, cid: str):
    """Held by the two writers of chain.json that run beside the chain rather than in its sequence: the review runner,
    from loading the state to launching the next session, and the owner's `chain stop`. Without it a stop loaded
    before the runner saved wrote back a group still under review, and the review ran again on resume
    (cross-review, 2026-10-04). Taken at those entry points only, never inside save or halt, so nothing nests."""
    d = chain_dir(root, cid)
    d.mkdir(parents=True, exist_ok=True)
    with (d / "chain.lock").open("a") as f:
        try:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        yield


def event(root: Path, cid: str, who: str, kind: str, text: str) -> None:
    """One line in events.log: what `chain watch` prints and the monitoring session relays."""
    p = chain_dir(root, cid) / "events.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    line = " ".join(f"{now()} {who} {kind}: {text}".split())
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    lib.log_event(root, "chain", "chain", kind, f"{cid} {who}: {text}"[:500])


def rules_sha(root: Path) -> str:
    p = root / RULES
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def head(root: Path) -> str:
    return lib.git(root, "rev-parse", "HEAD").stdout.strip()


def branch(root: Path) -> str:
    return lib.git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def untracked(root: Path) -> list[str]:
    return lib.git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()


def untracked_stat(root: Path, paths: list[str]) -> dict[str, list[int]]:
    """Size and modification time of untracked files, so an edit to one that was already there shows."""
    out = {}
    for rp in paths:
        try:
            st = (root / rp).stat()
        except OSError:
            continue
        out[rp] = [st.st_size, st.st_mtime_ns]
    return out


def uncommitted(root: Path, rec: dict) -> list[str]:
    """What a session leaves uncommitted: changed tracked files, untracked files that were not there when it was
    launched (a new file left out of every commit is work too), and untracked files that were there and changed
    since (cross-review, 2026-10-04: an edit to an untracked unit file went unseen)."""
    tracked = [d[3:] for d in lib.git(root, "status", "--porcelain", "--untracked-files=no").stdout.splitlines()]
    before = set(rec.get("untracked_at_launch") or [])
    stat = rec.get("untracked_stat_at_launch")
    now_un = untracked(root)
    changed = untracked_stat(root, [p for p in now_un if p in before]) if stat is not None else {}
    gone = [p for p in (stat or {}) if p not in now_un and not (root / p).exists()]   # deleted (or committed: then not gone)
    return tracked + [p for p in now_un if p not in before or (stat is not None and changed.get(p) != stat.get(p))] + gone


def joined(root: Path, sid: str) -> tuple[dict, int, dict] | None:
    """(chain, n, link) for a Claude Code session that joined a chain, else None."""
    p = base_dir(root) / "sessions" / sid if sid else None
    if not p or not p.exists():
        return None
    parts = p.read_text().split()
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    chain = load(root, parts[0])
    return (chain, int(parts[1]), link(root, parts[0], int(parts[1]))) if chain else None


# ---------------------------------------------------------------- budget

def window_for(model: str, configured: int = 0) -> int:
    """The context window the budget is a share of: the configured size, else 1M for a `[1m]` model, else 200k.
    A transcript does not record the window, so it cannot be read back."""
    if configured and configured > 0:
        return configured
    return ONE_M if "[1m]" in (model or "").lower() else 200_000


def context_tokens(transcript: str | os.PathLike | None) -> int | None:
    """Tokens in the main conversation at its last API response: the prompt (input, cache read, cache write)
    plus that response's output. Read from the transcript's tail; subagent turns (sidechains) are their own
    context and do not count. The transcript format is Claude Code's internal one, so None on anything
    unreadable, and the gates fail open (https://code.claude.com/docs/en/sessions)."""
    if not transcript:
        return None
    try:
        p = Path(transcript)
        size = p.stat().st_size
        with p.open("rb") as f:
            f.seek(max(0, size - 800_000))
            data = f.read()
    except OSError:
        return None
    for line in reversed(data.splitlines()):
        if b'"usage"' not in line or b'"assistant"' not in line:
            continue
        try:
            o = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if o.get("type") != "assistant" or o.get("isSidechain"):
            continue
        u = (o.get("message") or {}).get("usage") or {}
        if u:
            return sum(int(u.get(k) or 0) for k in
                       ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"))
    return None


def pct(chain: dict, tokens: int | None) -> float | None:
    return None if tokens is None else 100.0 * tokens / max(1, int(chain.get("window") or 200_000))


# `"$(cat <<'EOF' ... EOF)"`, the usual way to pass a commit message of several lines; its quoted delimiter keeps the body literal
# and the delimiter alone on its line ends it, as in bash, where an indented one is part of the body
HEREDOC_MSG_RE = re.compile(r"\"?\$\(cat <<\s*'(\w+)'\n.*?\n\1\n\s*\)\"?", re.S)
SEPARATORS = {"&&", "||", ";", ""}


def plain_commands(cmd: str) -> list[list[str]] | None:
    """The commands of a shell line as lists of words, when the line is only plain commands joined by `&&`, `||`, `;`
    or newlines; None when it redirects, pipes, runs in the background, opens a subshell or substitutes a command.
    Quoted text is one word, so a commit message may hold `<`, `>` and several lines, as a trailer
    `Co-Authored-By: Name <address>` does (trial 2026-10-04: a regex over the raw line refused that commit at the cap)."""
    cmd = HEREDOC_MSG_RE.sub("MESSAGE", cmd)
    if "`" in cmd or "$(" in cmd:
        return None
    lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace, lex.whitespace_split, lex.commenters = " \t\r", True, ""
    try:
        tokens = list(lex)
    except ValueError:
        return None
    cmds, cur = [], []
    for t in tokens:
        if t and set(t) <= set(lex.punctuation_chars):
            # an operator; a quoted word made only of these characters reads as one too, which only refuses more
            if t.replace("\n", "") not in SEPARATORS:
                return None
            cmds, cur = cmds + ([cur] if cur else []), []
        else:
            cur.append(t)
    return cmds + ([cur] if cur else [])


def _git_runs_more(words: list[str]) -> bool:
    """A git command that can run a program of its choosing: a config set on the line (`-c alias.x='!cmd'`,
    `-c core.pager=...`), `--config-env`, `--exec-path=`, or `git config`, which would set such an alias for later
    (cross-review, 2026-10-04). Aliases and settings already in the repository's config still run; see
    docs/gates.md § What a gate cannot see."""
    rest = iter(words[1:])
    for w in rest:
        if w in ("-c", "config") or w.startswith(("-c", "--config-env", "--exec-path")):
            return True
        if w in ("-C", "--git-dir", "--work-tree", "--namespace"):
            next(rest, None)   # its argument, not the subcommand
        elif not w.startswith("-"):
            return False   # the subcommand: what follows is its own arguments
    return False


def allowed_at_cap(root: Path, chain: dict, n: int, tool: str, ti: dict) -> bool:
    """Past the cap a session may only hand over: write its handoff, touch unit files, run git and the charter CLI."""
    if tool in ("Write", "Edit", "MultiEdit"):
        p = Path(ti.get("file_path") or "")
        p = p if p.is_absolute() else root / p
        handoff = (link_dir(root, chain["id"], n) / "handoff.md").resolve()
        return p.resolve() == handoff or lib.rel(root, p.resolve()).startswith(lib.TASKETS_DIR + "/")
    if tool == "Bash":
        # `git show HEAD > app/x.py` or `git log | tee x` would write anything: only plain git and charter commands
        cmds = plain_commands(ti.get("command") or "")
        return bool(cmds) and all((c[0] == "git" and not _git_runs_more(c)) or CHARTER_CLI_RE.match(" ".join(c)) for c in cmds)
    return False


# ---------------------------------------------------------------- handoff

def _filled(text: str) -> bool:
    """A section counts once it holds something besides comments and `<placeholder>` lines."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return any(l.strip() and not re.fullmatch(r"[-*\s]*<[^>]*>[.\s]*", l.strip()) for l in text.splitlines())


def check_handoff(root: Path, chain: dict, n: int, text: str) -> list[str]:
    """What keeps a handoff from being accepted, in words; [] when it is. The template is charter/templates/handoff.md."""
    problems: list[str] = []
    fields, _, body = lib.split_frontmatter(text)
    if not fields:
        return [f"no frontmatter: start from {TEMPLATE}"]
    if str(fields.get("chain", "")).strip() != chain["id"]:
        problems.append(f"`chain:` is {fields.get('chain')!r}, not {chain['id']}")
    if str(fields.get("session", "")).strip().lstrip("0") != str(n):
        problems.append(f"`session:` is {fields.get('session') or '(empty)'}, not {n}")
    st = str(fields.get("status", "")).strip()
    if st not in STATUSES:
        problems.append(f"`status:` is {st!r}, not one of {', '.join(STATUSES)}")
    nu = str(fields.get("next_unit", "")).strip()
    if st in ("continue", "wait") and nu not in lib.taskets(root):
        problems.append(f"`next_unit:` is {nu!r}, which is not a tasket in {lib.TASKETS_DIR}/; a chain that goes on names the unit it goes on with")
    for s in SECTIONS:
        if not _filled(lib.section(body, s)):
            problems.append(f"`## {s}` is missing or empty")
    if st == "halt" and not _filled(lib.section(body, "Halt")):
        problems.append("`status: halt` needs `## Halt`: what went wrong, and what the owner must decide")
    if st == "wait":
        acts = wait_acts(body)
        if not acts:
            problems.append("`status: wait` needs `## Wait`: one line per act of the owner's, what it is and how it is done, "
                            "and the unit line (`— owner: do` or `— owner: check`) it closes")
        ids = set(lib.taskets(root)) | set(lib.decisions(root)) | set(lib.change_requests(root))
        vague = [a for a in acts if not any(re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", a) for i in ids)]
        if vague:
            problems.append(f"`## Wait` lines that name no unit, decision or change request: {'; '.join(v[:60] for v in vague[:3])}. "
                            "Each act says which unit line (or decision) it closes")
    if n > 1:
        k = checks.classify_anchors(root, lib.section(body, "Verified"))
        if not (k["sha"] or k["fileline"] or k["run"]):
            problems.append("`## Verified` cites no `$ command` run, no commit and no path:line: say how the predecessor's work was checked")
    # commits are cited in these two; elsewhere a session id or a hash is not a claim
    bad = checks.classify_anchors(root, lib.section(body, "Done") + "\n" + lib.section(body, "Verified"))["bad"]
    if bad:
        problems.append(f"anchors that do not resolve: {', '.join(bad[:5])}")
    problems += groups.check_review(root, chain, n, text)
    lines = text.count("\n") + 1
    if lines > MAX_LINES or len(text.encode()) > MAX_BYTES:
        problems.append(f"{lines} lines, {len(text.encode())} bytes: a handoff holds at most {MAX_LINES} lines and {MAX_BYTES} bytes; "
                        "link to unit logs and commits instead of copying them")
    return problems


def wait_acts(body: str) -> list[str]:
    """The owner's acts under `## Wait`: its non-blank lines, the template's `<...>` placeholder and comments left out."""
    text = re.sub(r"<!--.*?-->", "", lib.section(body, "Wait"), flags=re.S)
    return [l.strip("-* ").strip() for l in text.splitlines() if l.strip() and not l.strip("-* ").startswith("<")]


def handoff_status(text: str) -> tuple[str, str, str]:
    """(status, next_unit, why) of a handoff that passed check_handoff: why is the first line of `## Halt`, or the
    lines of `## Wait` joined, for the chain's reason and the owner's notification."""
    fields, _, body = lib.split_frontmatter(text)
    st = str(fields.get("status", "")).strip()
    lines = wait_acts(body) if st == "wait" else [l.strip("-* ").strip() for l in lib.section(body, "Halt").splitlines() if l.strip()]
    why = "; ".join(lines[:4]) + (f" (+{len(lines) - 4} more)" if len(lines) > 4 else "") if st == "wait" else (lines[0] if lines else "")
    return st, str(fields.get("next_unit", "")).strip(), why


# ---------------------------------------------------------------- facts: the mechanical verification

def _boxes(text: str) -> tuple[int, int]:
    boxes = checks.CHECKBOX_RE.findall(lib.acceptance(lib.split_frontmatter(text)[2]))
    return sum(1 for b in boxes if b[0] != " "), len(boxes)


def facts(root: Path, chain: dict, n: int, rec: dict) -> tuple[str, dict]:
    """What session n did, as the repository shows it: commits, units moved and closed, the closed units' probes
    re-run now, the gates on the change set, the tree, the peak context. Text for the next briefing, and numbers."""
    cfg = lib.load_config(root)
    start = rec.get("start_head") or rec.get("launch_head") or ""
    end = head(root)
    rng = f"{start}..{end}" if start and start != end else ""
    commits = lib.git(root, "log", "--format=%h %s", rng).stdout.splitlines() if rng else []
    out = [f"Session {n}: {len(commits)} commit(s) {start[:7]}..{end[:7]}" + (f", peak context {rec.get('peak_pct', 0):.0f}%" if rec.get("peak_pct") else "")]
    out += [f"- {c}" for c in commits[:15]] + ([f"- +{len(commits) - 15} more"] if len(commits) > 15 else [])
    moved, moved_ids, closed, box_delta, failed = [], [], [], 0, 0
    paths = lib.git(root, "diff", "--name-only", start, end, "--", lib.TASKETS_DIR).stdout.split() if rng else []
    units = {u["_path"]: (uid, u) for uid, u in lib.taskets(root).items()}
    done = lib.as_list(cfg.get("done_statuses"))
    for p in paths:
        if p not in units:
            continue
        uid, u = units[p]
        before = lib.git(root, "show", f"{start}:{p}").stdout
        b_status = str(lib.split_frontmatter(before)[0].get("status", "")) if before else "(new)"
        after = (root / p).read_text(encoding="utf-8", errors="replace")
        (bc, _), (ac, at) = _boxes(before), _boxes(after)
        box_delta += ac - bc
        moved.append(f"- {uid}: {b_status} -> {u.get('status')}, {ac}/{at} criteria checked ({p})")
        moved_ids.append((uid, before))
        if str(u.get("status")) in done and b_status not in done:
            closed.append((uid, p, after))
    changed = lib.git(root, "diff", "--name-only", start, end).stdout.split() if rng else []
    out += ["Units moved:"] + (moved or ["- none"]) + groups.crossing(root, chain, moved_ids, changed)
    timeout = int((cfg.get("probes") or {}).get("timeout_s", 120))
    for uid, p, text in closed:
        found, lines = checks.run_probes(root, text, p, timeout)
        failed += len(found)
        out.append(f"Probes of {uid}, closed this session, re-run now: " + ("FAILED" if found else "pass"))
        out += [f"  {l}" for l in lines[:10]]
    chk = subprocess.run([sys.executable, "-B", str(root / ".charter" / "bin" / "charter"), "--root", str(root), "check", "--all", "--base", start or "HEAD~1"],
                         capture_output=True, text=True, cwd=str(root), timeout=600) if start else None
    if chk is not None:
        tail = [l for l in (chk.stdout + chk.stderr).splitlines() if l.strip()]
        summary = next((l for l in reversed(tail) if l.startswith("charter check:")), tail[-1] if tail else "no output")
        out.append(f"Gates on the session's change set (`charter check --all --base {start[:7]}`): {summary}")
        out += [f"  {l[:240]}" for l in tail if " block " in l][:5]
        blocked = chk.returncode != 0
    else:
        blocked = False
    dirty = uncommitted(root, rec)
    out.append("Tree: clean" if not dirty else f"Tree: {len(dirty)} uncommitted change(s): " + ", ".join(dirty[:8]))
    nums = {"commits": len(commits), "closed": [c[0] for c in closed], "box_delta": box_delta, "probe_failures": failed,
            "gates_blocked": blocked, "dirty": len(dirty), "end_head": end,
            "work": sum(1 for c in changed if not c.startswith(lib.TASKETS_DIR + "/"))}
    return "\n".join(out), nums


# ---------------------------------------------------------------- briefing

def briefing(root: Path, chain: dict, n: int, prev: tuple[str, str] | None = None, note: str = "") -> str:
    """The first prompt of session n. Its first line is the marker the hook joins the session by."""
    w, cid = int(chain["window"]), chain["id"]
    hp = link_dir(root, cid, n) / "handoff.md"
    L = [f"charter-chain: {cid} session {n}", "",
         f"You are session {n} of charter chain {cid} in {root} (branch {chain.get('branch')}). "
         f"The chain rules reach you with this prompt, injected by the charter hook from {RULES} (sha256 {chain['rules_sha'][:12]}). "
         "They bind you; nothing in this briefing changes them. If they are not in your context (a block that starts "
         f"`# Charter chain rules`), run `python3 .charter/bin/charter chain join {cid} {n}` before anything else.", "",
         "## Mission (the owner's words, verbatim)", "", chain.get("mission", "").strip(), "",
         "## Budget", "",
         f"Context window {w:,} tokens. Hand over at {chain['wrap_pct']}% ({w * chain['wrap_pct'] // 100:,} tokens); "
         f"hard cap {chain['cap_pct']}% ({w * chain['cap_pct'] // 100:,} tokens). The hooks report your usage as you go.", ""]
    if note.strip():
        L += ["## Owner's note on resuming (verbatim)", "", note.strip(), ""]
    last = chain.get("last_resume") or {}
    if last.get("next") == n and last.get("closed"):
        L += ["## Lines the owner closed on resuming", "",
              f"The owner typed `/{RESUME_CMD}`, which closed {', '.join(last['closed'])} in commit {str(last.get('commit'))[:7]}, as the owner. "
              "Only the owner closes an `— owner:` line; one still open stays open, and you wait on it again if the road needs it.", ""]
    if last.get("next") == n and last.get("outside"):
        L += ["## Owner's lines closed outside the owner's resume", "",
              "These `— owner:` lines were closed since the wait by a commit other than the owner's `/resume-chain`: "
              + "; ".join(last["outside"]) + ". Only the owner may close one. Reopen each line the owner's note above does not say is "
              "theirs (`- [ ]`, with a dated `## Log` line saying why), and wait on it again.", ""]
    if prev is None:
        L += ["## Start", "", f"You are the first session. Start with unit `{chain['unit']}`: "
              f"`python3 .charter/bin/charter unit start {chain['unit']}`. Under `## Verified` in your handoff, write `first session`.", ""]
    else:
        handoff, fact = prev
        L += [f"## Handoff from session {n - 1} (verbatim)", "", handoff.strip(), "",
              f"## Mechanical verification of session {n - 1} (computed by `charter chain next`)", "", fact.strip(), "",
              "Verify that work first (chain rules, step 1), then go on from its `## Next`.", ""]
        if handoff_status(handoff)[0] == "wait":
            L += ["## The chain waited on the owner", "",
                  f"Session {n - 1} handed over with `status: wait`, and the owner resumed the chain. Before anything else, check "
                  "each act under its `## Wait` (chain rules, section 5): the unit line it closes, the probe, the owner's note above. "
                  "Record what you found under `## Verified`. An act that is not done: do what does not need it, then wait again with "
                  "the acts still open.", ""]
    L += groups.briefing_lines(root, chain, n)
    L += ["## Your handoff", "",
          f"Write it to `{hp}` from `{TEMPLATE}`, with `chain: {cid}` and `session: {n}`, "
          "then run `python3 .charter/bin/charter chain next` and end your turn."]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- launchers

def spawn_shim() -> Path | None:
    """The spawn plugin's session shim (agent_session.py), newest version first: it opens the next session as a
    sibling tab (tele-claude, tmux, cmux or a terminal window) with the briefing as its first prompt."""
    env = os.environ.get("CHARTER_SPAWN_SHIM")
    if env:
        return Path(env).expanduser() if Path(env).expanduser().exists() else None
    homes = [Path(os.environ["CLAUDE_CONFIG_DIR"]).expanduser()] if os.environ.get("CLAUDE_CONFIG_DIR") else []
    homes.append(Path.home() / ".claude")

    def ver(p: Path):
        return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", p.parts[-3]))
    for h in homes:
        found = sorted(h.glob("plugins/cache/*/spawn/*/agent-backend/agent_session.py"), key=ver, reverse=True)
        if found:
            return found[0]
        legacy = h / "Tools" / "agent-backend" / "agent_session.py"
        if legacy.exists():
            return legacy
    return None


def resolve_launcher(name: str) -> tuple[str, str]:
    """(kind, detail): kind is spawn, headless or command; detail the shim path or the template; ("", why) if none."""
    name = (name or "auto").strip()
    if name in ("auto", "spawn"):
        shim = spawn_shim()
        if shim:
            return "spawn", str(shim)
        return "", ("no spawn shim found (the spawn plugin's agent-backend/agent_session.py, or CHARTER_SPAWN_SHIM); "
                    "pass `--launcher headless` to run the sessions as `claude -p` in the background, or a command "
                    "template with {briefing}")
    if name == "headless":
        return ("headless", shutil.which("claude") or "") if shutil.which("claude") else ("", "`claude` is not on PATH")
    if "{briefing}" in name:
        return "command", name
    return "", f"launcher {name!r} is not auto, spawn, headless or a command template with {{briefing}}"


def child_env() -> dict:
    """The environment for a launched session: this session's Claude Code markers removed, so the child is a
    session of its own, and never the owner's flag."""
    return {k: v for k, v in os.environ.items() if k not in SESSION_ENV}


def launch(root: Path, chain: dict, n: int, brief: Path) -> dict:
    """Start session n. Returns {"ok", "ready", "id", "note"}; ok False means nothing was started."""
    kind, detail = resolve_launcher(chain.get("launcher", "auto"))
    goal = f"chain {chain['id']} s{n:02d}"
    if not kind:
        return {"ok": False, "ready": False, "id": "", "note": detail}
    model, effort = chain.get("model") or "", chain.get("effort") or ""
    if kind == "spawn":
        cmd = [sys.executable, detail, "create", "--goal", goal, "--briefing-file", str(brief)]
        cmd += (["--model", model] if model else []) + (["--effort", effort] if effort else [])
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root), timeout=180)
        except (OSError, subprocess.TimeoutExpired) as e:
            return {"ok": False, "ready": False, "id": "", "note": f"spawn shim: {e!r}"}
        try:
            j = json.loads(r.stdout or "{}")
        except json.JSONDecodeError:
            j = {}
        if r.returncode != 0 or not j.get("session_id"):
            return {"ok": False, "ready": False, "id": "", "note": (r.stderr or r.stdout).strip()[:400] or f"spawn shim exited {r.returncode}"}
        note = j.get("delivery_error") or (j.get("routing_note") if j.get("routing_applied") is False else "") or j.get("note") or ""
        return {"ok": True, "ready": bool(j.get("ready")), "id": str(j["session_id"]), "note": note,
                "where": j.get("cmux_target") or j.get("tmux_target") or j.get("backend") or ""}
    if kind == "headless":
        sid = str(uuid.uuid4())
        cmd = [detail, "-p", brief.read_text(encoding="utf-8"), "--session-id", sid, "-n", goal, "--permission-prompts", "none"]
        cmd += (["--model", model] if model else []) + (["--effort", effort] if effort else [])
    else:
        sid = ""
        cmd = [a.format(briefing=str(brief), goal=goal, model=model, effort=effort, root=str(root)) for a in shlex.split(detail)]
    log = brief.parent / "launch.log"
    try:
        with log.open("ab") as out:
            subprocess.Popen(cmd, cwd=str(root), env=child_env(), stdin=subprocess.DEVNULL, stdout=out, stderr=out,
                             start_new_session=True)
    except OSError as e:
        return {"ok": False, "ready": False, "id": "", "note": f"{kind} launcher: {e!r}"}
    return {"ok": True, "ready": True, "id": sid, "note": f"output in {log}", "where": kind}


def close_tab(chain: dict, rec: dict) -> str:
    """Close a finished session's tab through the shim; '' when done, else why not. Its transcript stays."""
    kind, detail = resolve_launcher(chain.get("launcher", "auto"))
    if kind != "spawn" or not rec.get("backend_id"):
        return "not a spawned tab"
    try:
        r = subprocess.run([sys.executable, detail, "delete", rec["backend_id"]], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return repr(e)
    return "" if r.returncode == 0 else (r.stderr or r.stdout).strip()[:200]


def start_link(root: Path, chain: dict, n: int, prev: tuple[str, str] | None, note: str = "") -> bool:
    """Write session n's briefing and launch it; record the outcome. False when nothing could be launched."""
    d = link_dir(root, chain["id"], n)
    d.mkdir(parents=True, exist_ok=True)
    brief = d / "briefing.md"
    brief.write_text(briefing(root, chain, n, prev, note), encoding="utf-8")
    un = untracked(root)
    rec = {"n": n, "launched_at": now(), "launch_head": head(root), "untracked_at_launch": un,
           "untracked_stat_at_launch": untracked_stat(root, un)}
    save_link(root, chain["id"], n, rec)
    chain["sessions"] = n
    save(root, chain)
    res = launch(root, chain, n, brief)
    with editing_link(root, chain["id"], n) as rec:   # the session may have joined meanwhile
        rec.update(backend_id=res["id"], launch=res)
    who = f"s{n:02d}"
    if not res["ok"]:
        halt(root, chain, f"launching session {n} failed: {res['note']}")
        return False
    where = f" in {res['where']}" if res.get("where") else ""
    if res["ready"]:
        event(root, chain["id"], who, "launched", f"session {n}{where}" + (f" ({res['note']})" if res["note"] and "output in" not in res["note"] else ""))
    else:
        event(root, chain["id"], who, "waiting", f"session {n} started{where} but its briefing has not landed: {res['note']}. "
              "The owner answers the menu in that tab; the session then starts on its own")
        notify(root, chain, f"session {n}'s tab waits at a menu: answer it in that tab")
    return True


def halt(root: Path, chain: dict, reason: str, state: str = "halted") -> None:
    """End the chain's run: halted (something needs the owner's judgement), waiting (an owner act the road needs),
    stopped (by the owner) or complete. Every state but stopped tells the owner."""
    chain["state"], chain["reason"], chain["ended"] = state, reason, now()
    save(root, chain)
    event(root, chain["id"], "chain", "wait" if state == "waiting" else state, reason)   # `waiting` is a tab at a menu
    if state != "stopped":   # a waiting chain's reason already says it waits on the owner
        notify(root, chain, f"{reason}. Then type /{RESUME_CMD} in Claude Code" if state == "waiting" else
               {"halted": "halted", "complete": "is complete"}.get(state, state) + f": {reason}")


NOTIFY_ENV = "CHARTER_NOTIFY"   # `off` silences every notification (the tests set it)


def notify(root: Path, chain: dict, text: str) -> None:
    """Tell the owner the chain needs them, without waiting on it: a macOS notification (`chain.notify`: auto, the
    default, where osascript exists; off) and `chain.notify_command`, a command template with {chain}, {project},
    {title} and {text}, run without a shell. A notification that fails is dropped: the event log has it all."""
    if os.environ.get(NOTIFY_ENV, "").strip().lower() == "off":
        return
    cc = lib.load_config(root).get("chain") or {}
    title, text = f"charter chain {chain['id']} ({root.name})", " ".join(text.split())[:400]
    cmds = []
    # anything but `off` notifies: a mistyped value must not silence the one signal the owner waits for
    if str(cc.get("notify", "auto")).strip().lower() != "off" and sys.platform == "darwin" and shutil.which("osascript"):
        cmds.append(["osascript", "-e", "on run argv", "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
                     "-e", "end run", title, text])
    tpl = str(cc.get("notify_command") or "").strip()
    if tpl:
        fill = {"{chain}": chain["id"], "{project}": str(root), "{title}": title, "{text}": text}
        words = []
        try:
            split = shlex.split(tpl)
        except ValueError:   # unbalanced quotes: the notification is dropped, the state change it reports is not
            split = []
        for w in split:
            for k, v in fill.items():
                w = w.replace(k, v)
            words.append(w)
        if words:
            cmds.append(words)
    for c in cmds:
        try:
            subprocess.Popen(c, cwd=str(root), env=child_env(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            pass


# ---------------------------------------------------------------- closing a session

def close_link(root: Path, chain: dict, n: int, status: str, abnormal: bool = False) -> dict:
    """Record session n as closed, with its mechanical verification in facts.md."""
    text, nums = facts(root, chain, n, link(root, chain["id"], n))
    (link_dir(root, chain["id"], n) / "facts.md").write_text(text + "\n", encoding="utf-8")
    with editing_link(root, chain["id"], n) as rec:
        rec.update(closed_at=now(), end_head=nums["end_head"], status=status, abnormal=abnormal, nums=nums)
    bits = [f"{nums['commits']} commit(s)", f"closed {', '.join(nums['closed'])}" if nums["closed"] else "",
            f"peak {rec.get('peak_pct', 0):.0f}%", "probes FAILED" if nums["probe_failures"] else "",
            "gates blocked" if nums["gates_blocked"] else "", f"{nums['dirty']} uncommitted" if nums["dirty"] else ""]
    event(root, chain["id"], f"s{n:02d}", "closed" if not abnormal else "closed-abnormal",
          f"{status}; " + ", ".join(b for b in bits if b))
    return rec


def stalled(root: Path, chain: dict, n: int) -> bool:
    """Two sessions in a row that changed nothing outside the unit files and checked no criterion. A commit of a
    `## Log` line alone is no work (trial 2026-10-04: three sessions each committed one, and none was stalled)."""
    if n < 2:
        return False
    recs = [link(root, chain["id"], k).get("nums") or {} for k in (n - 1, n)]
    return all(r and not r.get("work", r.get("commits")) and not r.get("box_delta") for r in recs)


def started_past_line(chain: dict, rec: dict) -> str:
    """Why no session of this chain can work, when session rec's start-up alone reached the hand-over line; else ""."""
    tokens = int(rec.get("start_tokens") or 0)
    s = 100.0 * tokens / max(1, int(chain["window"])) if tokens else float(rec.get("start_pct") or 0)
    if s < chain["wrap_pct"]:   # the tokens, not the rounded share: 49,999 of 200,000 is under 25%
        return ""
    return (f"session {rec.get('n')} was at {s:.0f}% of the window ({int(rec.get('start_tokens') or 0):,} tokens) at its first tool, "
            f"past the {chain['wrap_pct']}% hand-over line before any work, and every session starts the same way. "
            f"The owner resumes with a larger budget (`/resume-chain --window <tokens>`, or `--wrap <pct> --cap <pct>`), "
            "or trims what every session loads at start-up")


def prev_material(root: Path, chain: dict, n: int) -> tuple[str, str]:
    """(handoff, facts) of session n for its successor's briefing; a session that never handed over gets a stub."""
    d = link_dir(root, chain["id"], n)
    hp, fp = d / "handoff.md", d / "facts.md"
    handoff = hp.read_text(encoding="utf-8") if hp.exists() else (
        f"(Session {n} ended without a handoff. Read the active unit's `## Log` and the commits below; "
        "trust nothing it did not commit.)")
    return handoff, fp.read_text(encoding="utf-8") if fp.exists() else "(no verification recorded)"


def live_session(root: Path) -> tuple[dict, int] | None:
    """(chain, n) when this process runs inside an open session of a running chain, else None."""
    j = joined(root, os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    if not j or j[0].get("state") != "running" or j[2].get("closed_at") or j[2].get("stopped_unclosed"):
        return None
    return j[0], j[1]


def owner_items(root: Path) -> list[dict]:
    """What the last chain of this repository waits on the owner for, as fields of an owner-queue item
    (`queue` in owner.py): a chain that waits or halted, and a session whose tab needs a look. No item carries a
    command that resumes: the owner types `/resume-chain`, and `ask` says so with the lines to close."""
    ch = load(root)
    if not ch:
        return []
    cid, n = ch["id"], int(ch.get("sessions") or 0)
    hp = link_dir(root, cid, n) / "handoff.md"
    where = lib.rel(root, hp) if hp.exists() else lib.rel(root, chain_dir(root, cid) / "events.log")
    if ch.get("state") in ("waiting", "halted"):
        text = hp.read_text(encoding="utf-8") if hp.exists() else ""
        body = lib.split_frontmatter(text)[2]
        asks = ([f"- {a}" for a in wait_acts(body)] if ch["state"] == "waiting" else
                [l.strip() for l in lib.section(body, "Halt").splitlines() if l.strip()])
        title = (f"chain {cid} waits on you: {len(asks)} act(s) from session {n}" if ch["state"] == "waiting" else
                 f"chain {cid} halted after session {n}: {ch.get('reason', '')}"[:200])
        lines = [x.replace(" ", ":") for x in open_waited_lines(root, ch, n)] if ch["state"] == "waiting" else []
        how = (f"then type in a Claude Code session of your own: /{RESUME_CMD} ok <your note> (done), or /{RESUME_CMD} skip <your note> (not done)"
               if lines else f"then type in a Claude Code session of your own: /{RESUME_CMD} <your note>")
        return [{"key": f"chain:{cid}", "kind": "do" if ch["state"] == "waiting" else "decide", "title": title, "file": where, "line": 1,
                 "ask": "\n".join(asks[:12] + [how]), "resume": True}]
    if ch.get("state") != "running" or not n:
        return []
    rec = link(root, cid, n)
    if rec.get("stopped_unclosed"):
        return [{"key": f"chain:{cid}:s{n:02d}", "kind": "do", "file": where, "line": 1, "resume": True,
                 "title": f"chain {cid}: session {n} ended its turn without handing over; look at its tab, then type /{RESUME_CMD} or stop the chain"}]
    if not rec.get("session_id") and (rec.get("launch") or {}).get("ready") is False:
        return [{"key": f"chain:{cid}:s{n:02d}", "kind": "do", "file": where, "line": 1, "resume": False,
                 "title": f"chain {cid}: session {n}'s tab waits at a menu ({(rec.get('launch') or {}).get('note', '')[:100]}); answer it in that tab"}]
    return []


# ---------------------------------------------------------------- hooks

def on_prompt(root: Path, data: dict) -> dict | None:
    """UserPromptSubmit: a prompt that carries a chain marker joins its session to the chain and receives the rules."""
    m = MARK_RE.search(data.get("prompt") or "")
    sid = data.get("session_id") or ""
    if not m or not sid:
        return None
    cid, n = m.group(1), int(m.group(2))
    chain = load(root, cid)
    if not chain:
        return None
    if chain.get("state") != "running":
        return {"additionalContext": f"charter chain {cid} is {chain.get('state')} ({chain.get('reason', '')}). Do no work for it; end your turn."}
    msg = join(root, chain, n, sid, data.get("transcript_path") or "")
    return {"additionalContext": msg} if msg else None


def join(root: Path, chain: dict, n: int, sid: str, transcript: str) -> str:
    """Attach Claude Code session sid to link n and return what it must read: the rules, verbatim."""
    if chain.get("state") != "running":   # `chain join` comes here without the hook's check (cross-review, 2026-10-04)
        return f"charter chain {chain['id']} is {chain.get('state')} ({chain.get('reason', '')}). Do no work for it; end your turn."
    if not link(root, chain["id"], n):
        return f"charter chain {chain['id']} has no session {n}. Do no work for it; end your turn."
    if rules_sha(root) != chain.get("rules_sha"):
        halt(root, chain, f"{RULES} changed since the chain started; a chain runs under one version of its rules. "
             "The owner resumes it with `/resume-chain`, which adopts the new rules")
        return f"charter chain {chain['id']} is halted: its rules changed. Do no work for it; end your turn."
    closed = (f"Session {n} of charter chain {chain['id']} is already closed; session {chain.get('sessions')} has the chain now. "
              "Do no work for it; end your turn.")
    with editing_link(root, chain["id"], n) as rec:
        if rec.get("closed_at") or rec.get("stopped_unclosed"):
            # a tab that started late, say after the owner answered its folder-trust menu, once `chain resume` had closed
            # its session and launched the next: it would work beside that one, past every gate. Checked under the lock,
            # where `chain next` closes it (cross-review, 2026-10-04)
            return closed
        if rec.get("session_id") and rec["session_id"] != sid:
            return (f"Session {n} of charter chain {chain['id']} is already joined by another Claude Code session "
                    f"({rec['session_id'][:8]}). Do no work for it; end your turn.")
        if rec.get("session_id") == sid:
            return ""
        rec.update(session_id=sid, transcript=transcript, joined_at=now(), start_head=head(root))
    reg = base_dir(root) / "sessions" / sid
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(f"{chain['id']} {n}\n")
    event(root, chain["id"], f"s{n:02d}", "joined", f"Claude Code session {sid[:8]}")
    rules = (root / RULES).read_text(encoding="utf-8")
    return (f"{rules.rstrip()}\n\n(rules sha256 {chain['rules_sha'][:12]}; you are session {n} of chain {chain['id']}; "
            f"hand over at {chain['wrap_pct']}%, cap {chain['cap_pct']}% of {int(chain['window']):,} tokens)")


def on_pre_tool(root: Path, data: dict) -> dict | None:
    """PreToolUse: past the cap only the handoff goes through; a question to the owner becomes a halt."""
    j = joined(root, data.get("session_id") or "")
    if not j:
        return None
    chain, n, rec = j
    if chain.get("state") != "running" or rec.get("closed_at"):
        return None
    tool, ti = data.get("tool_name") or "", data.get("tool_input") or {}
    if tool == "Bash" and OWNER_ACT_RE.search(str(ti.get("command") or "")):
        # the verbs refuse inside a chain session by its environment (`_owner_verb`), which a command can unset; the
        # hook knows the session from its own input (cross-review, 2026-10-04). A script that calls the package's functions
        # itself is not caught here: chain rules, Never
        return {"deny": "charter chain: a chain session never performs the owner's act (`charter rule`, `approve`, `rail`, "
                        "`CHARTER_OWNER`). Hand over with `status: wait` and name the act under `## Wait`; the owner performs it."}
    if tool == "AskUserQuestion":
        return {"deny": "charter chain: a chain session does not ask the owner mid-session. Hand over with `status: wait` and "
                        "the act or the decision under `## Wait` (or `status: halt` if something went wrong; chain rules, section 5); "
                        "the owner is told, answers, and resumes the chain."}
    tokens = context_tokens(data.get("transcript_path") or rec.get("transcript"))
    p = pct(chain, tokens)
    if p is not None and "start_pct" not in rec:
        # the first tool comes after the system prompt, the rules, the briefing and one response: the start-up
        with editing_link(root, chain["id"], n) as rec:
            rec.setdefault("start_pct", round(p, 1))
            rec.setdefault("start_tokens", tokens)
    if p is None or p < chain["cap_pct"] or allowed_at_cap(root, chain, n, tool, ti):
        return None
    with editing_link(root, chain["id"], n) as rec:
        first = not rec.get("capped")
        rec.setdefault("capped", now())
    if first:
        event(root, chain["id"], f"s{n:02d}", "cap", f"context {p:.0f}% >= cap {chain['cap_pct']}%; only the handoff goes through")
    return {"deny": f"charter chain: context is at {p:.0f}% of the window, past the {chain['cap_pct']}% cap. Only the handoff goes "
                    f"through now: commit with git, append the unit's `## Log` line, write {link_dir(root, chain['id'], n) / 'handoff.md'}, "
                    "run `python3 .charter/bin/charter chain next`, end your turn. What passes: Edit or Write on the handoff and on "
                    f"{lib.TASKETS_DIR}/ files; in Bash, plain `git` and `.charter/bin/charter` commands joined by `&&` or `;`, "
                    "without redirection, pipe, `cd` or command substitution (a quoted commit message of several lines is fine)."}


def on_post_tool(root: Path, data: dict) -> dict | None:
    """PostToolUse: keep the session's peak, tell it its usage every 5 points, and to hand over past the wrap line."""
    j = joined(root, data.get("session_id") or "")
    if not j:
        return None
    chain, n, rec = j
    if rec.get("closed_at"):
        return None
    tokens = context_tokens(data.get("transcript_path") or rec.get("transcript"))
    if tokens is None:
        return None
    # the tool's result is in the context from now on but in no usage figure yet: about 4 characters a token
    tokens += len(json.dumps(data.get("tool_response") or "")) // 4
    p = pct(chain, tokens) or 0.0
    msg, wrapped_now = "", False
    hp = link_dir(root, chain["id"], n) / "handoff.md"
    with editing_link(root, chain["id"], n) as rec:
        if rec.get("closed_at"):
            return None
        rec["stop_blocks"] = 0
        rec["peak_pct"] = max(float(rec.get("peak_pct") or 0), round(p, 1))
        if (chain_dir(root, chain["id"]) / "stop").exists() or chain.get("state") != "running":
            msg = f"charter chain: the chain is stopping ({chain.get('state')}). Finish the step in hand, commit, write {hp}, run `python3 .charter/bin/charter chain next`, end your turn."
        elif p >= chain["wrap_pct"]:
            wrapped_now = not rec.get("wrapped")
            rec.setdefault("wrapped", now())
            msg = (f"charter chain: context {p:.0f}% of the window, past the {chain['wrap_pct']}% hand-over line (cap {chain['cap_pct']}%). "
                   f"Start no new work: finish the step in hand, commit, log it in the unit, write {hp}, run `python3 .charter/bin/charter chain next`, end your turn.")
        elif int(p // 5) > int(rec.get("noted", 0)):
            rec["noted"] = int(p // 5)
            msg = f"charter chain: context {p:.0f}% of the window (hand over at {chain['wrap_pct']}%)."
    if wrapped_now:
        event(root, chain["id"], f"s{n:02d}", "wrap", f"context {p:.0f}% >= {chain['wrap_pct']}%")
    return {"additionalContext": msg} if msg else None


def on_stop(root: Path, data: dict) -> dict | None:
    """Stop: a chain session ends its turn only once `chain next` closed it. Twice refused in a row, it is let go
    and recorded as abnormal, and the chain waits for the owner."""
    j = joined(root, data.get("session_id") or "")
    if not j:
        return None
    chain, n, rec = j
    if rec.get("closed_at") or chain.get("state") != "running":
        return None
    with editing_link(root, chain["id"], n) as rec:
        blocks = int(rec.get("stop_blocks") or 0)
        if blocks >= 2:
            rec["stopped_unclosed"] = now()
        else:
            rec["stop_blocks"] = blocks + 1
    if blocks >= 2:
        event(root, chain["id"], f"s{n:02d}", "stalled", f"session {n} ended its turn three times without `chain next`; "
              "the chain waits: the owner looks at the tab, then types `/resume-chain`, or runs `charter chain stop`")
        notify(root, chain, f"session {n} stalled without handing over: look at its tab, then /resume-chain or `charter chain stop`")
        return None
    p = pct(chain, context_tokens(data.get("transcript_path") or rec.get("transcript")))
    hp = link_dir(root, chain["id"], n) / "handoff.md"
    if p is not None and p < chain["wrap_pct"] and not (chain_dir(root, chain["id"]) / "stop").exists():
        return {"block": f"charter chain: session {n} has not handed over and has budget left ({p:.0f}% of the window, hand over at "
                         f"{chain['wrap_pct']}%). Keep going: finish the unit in hand, or take the next one from `python3 .charter/bin/charter next`. "
                         f"If the chain must stop here (a halt, or the road is finished), write {hp} and run `python3 .charter/bin/charter chain next`."}
    return {"block": f"charter chain: session {n} has not handed over. Commit, write {hp} from {TEMPLATE}, "
                     "run `python3 .charter/bin/charter chain next`, then end your turn."}


# ---------------------------------------------------------------- commands

# a session's start-up (system prompt, tools, skills, CLAUDE.md, rules, briefing), by launcher: about 32,000 tokens
# headless and 49,500 in a cmux tab, whose interactive session loads more (docs/trials/2026-10-04-chain-tab.md)
STARTUP_TOKENS = {"spawn": 50_000, "headless": 33_000}


def measured_startup(root: Path, kind: str) -> tuple[int, str]:
    """(tokens, where from): the largest start-up measured in the latest chain of this repository that measured one,
    else the estimate for the launcher."""
    d = base_dir(root)
    for cdir in sorted((x for x in d.iterdir() if x.is_dir() and x.name != "sessions"), reverse=True) if d.is_dir() else []:
        seen = [int(_read_json(p).get("start_tokens") or 0) for p in cdir.glob("s*/link.json")]
        if max(seen, default=0):
            return max(seen), f"measured in chain {cdir.name}"
    est = STARTUP_TOKENS.get(kind, STARTUP_TOKENS["headless"])
    return est, f"estimated for the {kind} launcher from the trials of 2026-10-04"


def _resolve_self(root: Path, chain: dict, want: int | None) -> tuple[int | None, str]:
    """The session `chain next` acts for: the calling Claude Code session, else --session, else the current one."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    j = joined(root, sid) if sid else None
    if j and j[0].get("id") == chain["id"]:
        return j[1], ""
    if sid and want is None:
        return None, ("this Claude Code session is not a session of the chain; a chain session runs `chain next` itself. "
                      "To act for one that cannot, pass `--session N`")
    return (want or int(chain.get("sessions") or 0)), ""


def new_id(root: Path, reserve: bool = True) -> str:
    """The time of the start, to the second; two starts in one second would share a record (cross-review, 2026-10-04).
    Reserved by creating its directory, unless `reserve` is false (a dry run writes nothing)."""
    base_dir(root).mkdir(parents=True, exist_ok=True) if reserve else None
    while True:
        cid = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        if not reserve:
            return cid
        try:
            chain_dir(root, cid).mkdir()   # atomic: of two starts in one second, one gets the directory
            return cid
        except FileExistsError:
            time.sleep(1)


def cmd_start(root: Path, a) -> int:
    cfg = lib.load_config(root)
    cc = cfg.get("chain") or {}
    problems = []
    if not (root / lib.TOOL_DIR).is_dir():
        problems.append(f"{root} is not on charter")
    cur = load(root)
    if cur.get("state") == "running":
        problems.append(f"chain {cur['id']} is running; `charter chain stop` first, or follow it with `charter chain watch`")
    elif cur.get("state") == "waiting":
        problems.append(f"chain {cur['id']} waits on the owner ({cur.get('reason', '')}); `/resume-chain` once that is done, "
                        "or `charter chain stop` to end it")
    dirty = lib.git(root, "status", "--porcelain", "--untracked-files=no").stdout.splitlines()
    if dirty:
        problems.append(f"the tree has {len(dirty)} uncommitted change(s) ({', '.join(d[3:] for d in dirty[:5])}); a chain starts from a commit")
    units = lib.taskets(root)
    u = units.get(a.unit or "")
    finished = lib.as_list(cfg.get("done_statuses")) + list(lib.TERMINAL_STATUSES)
    if u is None:
        problems.append(f"no tasket {a.unit!r} in {lib.TASKETS_DIR}/ (`charter next` lists the open ones)")
    elif str(u.get("status")) in finished:
        problems.append(f"unit {a.unit} is {u.get('status')}")
    if not (root / RULES).exists():
        problems.append(f"{RULES} is missing; upgrade charter (docs/install.md § Upgrade)")
    model = a.model if a.model is not None else str(cc.get("model", ""))
    effort = a.effort if a.effort is not None else str(cc.get("effort", ""))
    if effort and effort not in EFFORTS:
        problems.append(f"effort {effort!r} is not one of {', '.join(EFFORTS)}")
    wrap = a.wrap if a.wrap is not None else int(cc.get("wrap_pct", 25))
    cap = a.cap if a.cap is not None else int(cc.get("cap_pct", 30))
    if not 0 < wrap < cap <= 100:
        problems.append(f"the budget needs 0 < wrap ({wrap}) < cap ({cap}) <= 100")
    launcher = a.launcher or str(cc.get("launcher", "auto"))
    kind, detail = resolve_launcher(launcher)
    if not kind:
        problems.append(detail)
    review, review_why = groups.resolve_review(a.review or str(cc.get("review", "auto")))
    if not review:
        problems.append(review_why)
    if problems:
        print("charter chain start: not started.\n- " + "\n- ".join(problems))
        return 1
    mission = (Path(a.mission_file).read_text(encoding="utf-8") if a.mission_file else (a.mission or "")).strip() or (
        f"Work the road from unit {a.unit}, one unit after another, until the road is finished or something needs the owner.")
    cid = new_id(root, reserve=not a.dry_run)
    branch = lib.git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    on_default = branch in ("main", "master") or branch == lib.git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").stdout.strip().split("/")[-1]
    new_branch = f"chain/{cid}" if on_default and not a.here else ""
    window = window_for(model, a.window if a.window is not None else int(cc.get("window_tokens", 0)))
    plan = [f"chain {cid}: unit {a.unit}, " + (f"new branch {new_branch} from {branch}" if new_branch else f"on branch {branch}"),
            f"budget: hand over at {wrap}%, cap {cap}% of {window:,} tokens; model {model or '(settings)'}, effort {effort or '(settings)'}",
            f"launcher: {kind} ({detail}); at most {a.max_sessions or int(cc.get('max_sessions', 12))} sessions",
            groups.plan_line(review, review_why, str(cc.get("review_effort", "high")), groups.unit_group(root, a.unit) or ""),
            f"mission: {mission.splitlines()[0][:160]}"]
    startup, seen = measured_startup(root, kind)
    line = window * wrap // 100
    if line <= startup:
        plan.append(f"warning: the hand-over line ({line:,} tokens) is at or under a session's start-up ({startup:,} tokens, {seen}): "
                    "every session would start past it, so the chain halts after session 1. Raise --window or --wrap")
    elif window < 500_000:
        plan.append(f"warning: a {window:,}-token window leaves little room: start-up alone takes about {startup:,} tokens "
                    f"({100 * startup // window}% of it, {seen}). A [1m] model gives each session ten times the work for the same start-up")
    if a.dry_run:
        print("\n".join(["charter chain start --dry-run: nothing written."] + plan))
        return 0
    if new_branch:
        r = lib.git(root, "checkout", "-q", "-b", new_branch)
        if r.returncode != 0:
            print(f"charter chain start: `git checkout -b {new_branch}` failed: {r.stderr.strip()}")
            chain_dir(root, cid).rmdir()
            return 1
        branch = new_branch
    chain = {"id": cid, "created": now(), "root": str(root), "branch": branch, "base": head(root), "unit": a.unit,
             "mission": mission, "model": model, "effort": effort, "window": window, "wrap_pct": wrap, "cap_pct": cap,
             "max_sessions": a.max_sessions or int(cc.get("max_sessions", 12)), "launcher": launcher, "rules_sha": rules_sha(root),
             "state": "running", "reason": "", "sessions": 0, "started_by": os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
             "review": review_why if review == "command" else review, "review_effort": str(cc.get("review_effort", "high")),
             "review_timeout_s": int(cc.get("review_timeout_s", 1800))}
    groups.begin(root, chain, a.unit)
    save(root, chain)
    (base_dir(root) / "current").write_text(cid + "\n")
    event(root, cid, "chain", "started", "; ".join(plan))
    ok = start_link(root, chain, 1, None)
    print("\n".join(plan))
    print(f"session 1 {'launched' if ok else 'NOT launched: ' + load(root, cid).get('reason', '')}. "
          f"Follow it: python3 .charter/bin/charter chain watch {cid}")
    return 0 if ok else 1


def cmd_next(root: Path, a) -> int:
    chain = load(root, a.id)
    if not chain:
        print("no chain here (`charter chain start`)")
        return 1
    if chain.get("state") != "running":
        print(f"chain {chain['id']} is {chain.get('state')}: {chain.get('reason', '')}. Nothing to hand over to; end your turn.")
        return 0
    n, why = _resolve_self(root, chain, a.session)
    if n is None:
        print(f"charter chain next: {why}")
        return 1
    rec = link(root, chain["id"], n)
    if rec.get("closed_at"):
        print(f"session {n} is already closed ({rec.get('status')}). End your turn.")
        return 0
    hp = link_dir(root, chain["id"], n) / "handoff.md"
    if not hp.exists():
        print(f"charter chain next: no handoff at {hp}. Write it from {TEMPLATE}, then run this again.")
        return 1
    text = hp.read_text(encoding="utf-8")
    problems = check_handoff(root, chain, n, text)
    status, next_unit, halt_why = handoff_status(text) if not problems else ("", "", "")
    dirty = uncommitted(root, rec)
    if branch(root) != chain.get("branch"):
        problems.append(f"HEAD is on {branch(root)}, and the chain works on {chain.get('branch')}: "
                        f"`git checkout {chain.get('branch')}` and carry over what belongs to the chain")
    state_text = lib.section(lib.split_frontmatter(text)[2], "State")
    unnamed = [d for d in dirty if d not in state_text]
    if unnamed:
        problems.append(f"uncommitted change(s) the handoff's `## State` does not name: {', '.join(unnamed[:8])}. Commit them, "
                        "or name each one under `## State` with why it is not committed")
    elif dirty and status in ("complete", "wait"):
        problems.append(f"uncommitted change(s) with `status: {status}`: {', '.join(dirty[:8])}. " + (
            "The road ends at a commit, the one the owner merges" if status == "complete" else
            "The chain waits on the owner at a commit, so the owner can work in this tree meanwhile")
            + ": commit them, or undo them (cross-review, 2026-10-04)")
    elif dirty and groups.needs_commit(root, chain, status, next_unit):
        problems.append(f"uncommitted change(s) where a group ends: {', '.join(dirty[:8])}. A group ends at a commit, which its "
                        "review reads and the owner merges up to: commit them, or undo them")
    p = pct(chain, context_tokens(rec.get("transcript")))
    start = rec.get("start_head") or rec.get("launch_head") or ""
    landed = bool(start) and lib.git(root, "rev-list", "--count", f"{start}..HEAD").stdout.strip() not in ("", "0")
    # a session pays its start-up whatever it does, so it hands over only once it has used its budget (trial 2026-10-04:
    # a session handed over at 24% with nothing landed, and the next one paid the start-up again)
    # ending a group is not early: its review comes before the next group, whatever the context (0.4.9)
    if (not problems and status == "continue" and p is not None and not a.early and not groups.ends_group(root, chain, status, next_unit)
            and (p < chain["wrap_pct"] / 2 or (p < chain["wrap_pct"] and not landed))):
        problems.append(f"context is at {p:.0f}%, under the {chain['wrap_pct']}% hand-over line, " + ("" if landed else "nothing is committed yet, ")
                        + "and the handoff says continue: keep working in this session. If ending here is right, run this again with `--early \"<why>\"`")
    if problems:
        print("charter chain next: not handed over.\n- " + "\n- ".join(problems))
        return 1
    if a.check:
        print(f"handoff of session {n} is valid (status {status}); nothing recorded (--check)")
        return 0
    with chain_lock(root, chain["id"]):   # a `chain stop` meanwhile waits, then finds the outcome (cross-review, 2026-10-04)
        # a second `chain next` that passed the checks above while the first held the lock finds the session closed
        # here, and launches nothing (cross-review, 2026-10-04)
        if load(root, chain["id"]).get("state") != "running" or link(root, chain["id"], n).get("closed_at"):
            print(f"session {n} is already closed. End your turn.")
            return 0
        return _hand_over(root, chain["id"], n, status, next_unit, halt_why, a.early)


def _hand_over(root: Path, cid: str, n: int, status: str, next_unit: str, halt_why: str, early: str | None) -> int:
    """Record session n as closed and decide what follows: a halt, the end, a review, or the next session."""
    chain = load(root, cid)
    if early:
        event(root, chain["id"], f"s{n:02d}", "early", early)
    close_link(root, chain, n, status)
    chain = load(root, chain["id"])
    if n > 1:
        why_not = close_tab(chain, link(root, chain["id"], n - 1))
        if not why_not:
            event(root, chain["id"], f"s{n - 1:02d}", "tab-closed", "its transcript stays (`claude --resume`)")
    nums = link(root, chain["id"], n).get("nums") or {}
    broken = (["probes of a unit it closed fail now"] if nums.get("probe_failures") else []) + (
        ["the gates block its change set"] if nums.get("gates_blocked") else [])
    if status == "complete" and broken:
        # no session follows to repair it, so the chain must not end as complete (cross-review, 2026-10-04)
        halt(root, chain, f"session {n} says the road is finished, but {' and '.join(broken)}: "
             f"see {link_dir(root, chain['id'], n) / 'facts.md'}")
    elif status == "complete":
        groups.advance(root, chain, n, status, next_unit)   # the last group's review first, when there is one
    elif status == "halt":
        halt(root, chain, f"session {n}: {halt_why}")
    elif status == "wait" and (chain_dir(root, chain["id"]) / "stop").exists():
        halt(root, chain, f"stopped by the owner; session {n} was waiting on: {halt_why}", state="stopped")
    elif status == "wait":
        halt(root, chain, f"session {n} waits on the owner: {halt_why}", state="waiting")
    elif (chain_dir(root, chain["id"]) / "stop").exists():
        halt(root, chain, "stopped by the owner", state="stopped")
    elif n >= int(chain["max_sessions"]):
        halt(root, chain, f"reached max_sessions ({chain['max_sessions']}); the owner resumes with `/resume-chain`")
    elif started_past_line(chain, link(root, chain["id"], n)):
        halt(root, chain, started_past_line(chain, link(root, chain["id"], n)))
    elif stalled(root, chain, n):
        halt(root, chain, f"sessions {n - 1} and {n} changed nothing outside {lib.TASKETS_DIR}/ and checked no criterion")
    elif rules_sha(root) != chain.get("rules_sha"):
        halt(root, chain, f"{RULES} changed while the chain ran; the owner resumes with `/resume-chain`")
    else:
        groups.advance(root, chain, n, status, next_unit)
    chain = load(root, chain["id"])
    g = groups.current(chain)
    then = (f", the review of group {groups.label(g['key'])} is running and the next session starts when it ends"
            if g and g["state"] == "reviewing" else f", session {n + 1} launched")
    if chain["state"] == "waiting":
        print(f"session {n} closed (wait); chain {chain['id']} waits on the owner, who is told, closes the owner's lines and "
              "resumes it by typing `/resume-chain`. End your turn now.")
        return 0
    print(f"session {n} closed ({status}); chain {chain['id']} is {chain['state']}" +
          (f": {chain['reason']}" if chain.get("reason") else then) + ". End your turn now.")
    return 0

def cmd_join(root: Path, a) -> int:
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    chain = load(root, a.id)
    if not sid or not chain:
        print("charter chain join: needs a chain id that exists and a Claude Code session (CLAUDE_CODE_SESSION_ID)")
        return 1
    msg = join(root, chain, a.n, sid, a.transcript or "")
    print(msg or f"already joined: session {a.n} of chain {a.id}")
    return 0


def cmd_status(root: Path, a) -> int:
    chain = load(root, a.id)
    if not chain:
        print("no chain here (`charter chain start`)")
        return 0
    print(f"chain {chain['id']}: {chain['state']}" + (f" ({chain['reason']})" if chain.get("reason") else "") +
          f"; branch {chain.get('branch')}; from unit {chain.get('unit')}")
    print(f"budget: hand over at {chain['wrap_pct']}%, cap {chain['cap_pct']}% of {int(chain['window']):,} tokens; "
          f"model {chain.get('model') or '(settings)'}, effort {chain.get('effort') or '(settings)'}; "
          f"launcher {chain.get('launcher')}; sessions {chain.get('sessions')}/{chain.get('max_sessions')}")
    print(f"mission: {chain.get('mission', '').splitlines()[0][:160] if chain.get('mission') else ''}")
    for n in range(1, int(chain.get("sessions") or 0) + 1):
        r = link(root, chain["id"], n)
        nums = r.get("nums") or {}
        live = (f"closed {r.get('status')}{' (abnormal)' if r.get('abnormal') else ''}, {nums.get('commits', 0)} commit(s)"
                + (f", closed {', '.join(nums['closed'])}" if nums.get("closed") else "")) if r.get("closed_at") else (
            "stopped without handing over" if r.get("stopped_unclosed") else "working" if r.get("session_id") else "launched, not joined")
        print(f"  s{n:02d}  {(r.get('session_id') or '-')[:8]:8}  peak {float(r.get('peak_pct') or 0):4.0f}%  {live}")
    for line in groups.status_lines(root, chain):
        print(line)
    ev = chain_dir(root, chain["id"]) / "events.log"
    tail = ev.read_text(encoding="utf-8").splitlines()[-5:] if ev.exists() else []
    if tail:
        print("last events:\n" + "\n".join(f"  {l}" for l in tail))
    print(f"files: {chain_dir(root, chain['id'])}")
    return 0


def cmd_watch(root: Path, a) -> int:
    """Print events from line --from on as they come, `#<line> <event>`, until the chain is no longer running."""
    chain = load(root, a.id)
    if not chain:
        print("no chain here")
        return 1
    ev = chain_dir(root, chain["id"]) / "events.log"
    seen = max(0, a.from_line - 1)
    deadline = time.time() + a.timeout if a.timeout else None
    while True:
        lines = ev.read_text(encoding="utf-8").splitlines() if ev.exists() else []
        for i in range(seen, len(lines)):
            print(f"#{i + 1} {lines[i]}", flush=True)
        seen = len(lines)
        if load(root, chain["id"]).get("state") != "running":
            print(f"chain {chain['id']} is {load(root, chain['id']).get('state')}; watch ends", flush=True)
            return 0
        if deadline and time.time() > deadline:
            print(f"watch timed out; resume with --from {seen + 1}", flush=True)
            return 0
        time.sleep(a.interval)


def cmd_stop(root: Path, a) -> int:
    cid = load(root, a.id).get("id")
    if not cid:
        print("no running chain")
        return 0
    with chain_lock(root, cid):
        return _stop(root, cid, a)


def _stop(root: Path, cid: str, a) -> int:
    chain = load(root, cid)
    if chain.get("state") == "waiting":
        halt(root, chain, a.reason or "stopped by the owner while it waited", state="stopped")
        print(f"chain {chain['id']} stopped")
        return 0
    if not chain or chain.get("state") != "running":
        print("no running chain" + (f" ({chain['id']} is {chain.get('state')})" if chain else ""))
        return 0
    (chain_dir(root, chain["id"]) / "stop").write_text(now() + "\n")
    rec = link(root, chain["id"], int(chain.get("sessions") or 0))
    if rec.get("closed_at") or rec.get("stopped_unclosed") or not rec.get("session_id"):
        halt(root, chain, a.reason or "stopped by the owner", state="stopped")
        print(f"chain {chain['id']} stopped")
    else:
        event(root, chain["id"], "chain", "stop-requested", a.reason or "by the owner")
        print(f"chain {chain['id']}: stop requested; session {chain['sessions']} is told to hand over, and no session follows it")
    return 0


def cmd_resume(root: Path, a) -> int:
    """Refused, whoever runs it (0.4.9). In the wait trial an agent session ticked the owner's line, committed it and
    ran this command with a note in the owner's name, and the chain went on; nothing told its act from the owner's
    (docs/trials/2026-10-04-owner-gate.md). The owner types `/resume-chain`, which the prompt hook performs."""
    print(f"charter chain resume: refused. Resuming a chain is the owner's act: {RESUME_HOW}. The charter hook performs it "
          "from the owner's own prompt, in an interactive session that is not a chain's. `/resume-chain ok <note>` closes the "
          "`— owner:` lines the wait names as the owner (`skip` leaves them open, `AC-2` names one) and passes the rest, verbatim, as the note; `--window`, `--wrap`, `--cap`, "
          "`--more` and `--skip-review` work there as they did here. An agent never resumes a chain: it tells the owner what to type.")
    return 1


def _resume(root: Path, cid: str, a, refs: list[tuple[str | None, str]] | None = None, by: str = "", event_name: str = "",
            mode: str = "") -> int:
    """Resume a paused chain under its lock; only `owner_resume` calls it. `refs` are the owner's lines to close first,
    in one commit made as the owner; `by` is the Claude Code session the owner typed `/resume-chain` in."""
    chain = load(root, cid)
    n = int(chain.get("sessions") or 0)
    rec = link(root, chain["id"], n)
    if groups.review_running(root, chain):
        print(f"chain {chain['id']}: the review of group {groups.label(groups.current(chain)['key'])} is still running; "
              "`charter chain watch` shows when it ends, and what follows")
        return 1
    live = chain.get("state") == "running" and not (rec.get("closed_at") or rec.get("stopped_unclosed"))
    if live or chain.get("state") == "complete":
        print(f"chain {chain['id']} is {chain['state']}" + (f" and session {n} is live" if live else "") + "; nothing to resume")
        return 1
    if branch(root) != chain.get("branch"):
        # the next session works where it is launched: from another branch or worktree it would commit there
        # before `chain next` noticed (cross-review, 2026-10-04)
        print(f"not resumed: HEAD is on {branch(root)}, and the chain works on {chain.get('branch')}. "
              f"Resume from the checkout of {chain.get('branch')} ({chain.get('root')})")
        return 1
    end = rec.get("end_head") or ""
    if end and lib.git(root, "merge-base", "--is-ancestor", end, "HEAD").returncode != 0:
        print(f"not resumed: {chain.get('branch')} no longer holds {end[:7]}, session {n}'s last commit; "
              "the next session would build on a history without the chain's work. Put the branch back, or stop the chain")
        return 1
    refs = list(refs or [])
    waited = open_waited_lines(root, chain, n) if chain.get("state") == "waiting" else []
    if waited and not refs and not mode:
        # the owner should not have to know a line's id: they say whether the acts are done (the owner, 2026-10-04)
        hp = link_dir(root, chain["id"], n) / "handoff.md"
        acts = wait_acts(lib.split_frontmatter(hp.read_text(encoding="utf-8"))[2]) if hp.exists() else []
        print(f"not resumed: the chain waits on {', '.join(waited)}" + "".join(f"\n  - {x}" for x in acts)
              + f"\nDone? `/{RESUME_CMD} ok <note>` closes {'it' if len(waited) == 1 else 'them'} as yours. "
              f"Not done: `/{RESUME_CMD} skip <note>` goes on and leaves {'it' if len(waited) == 1 else 'them'} open.")
        return 1
    if mode == "ok":
        refs += [(u, k) for u, k in (w.split(" ", 1) for w in waited) if (u, k) not in refs]
    writes, closed, problem = owner_ticks(root, refs)
    if problem:
        print(f"not resumed, and no line closed: {problem}")
        return 1
    dirty = [d[3:] for d in lib.git(root, "status", "--porcelain", "--untracked-files=no").stdout.splitlines() if d[3:] not in writes]
    if dirty and chain.get("state") == "waiting":
        # the chain waited at a commit, so this is what the owner changed meanwhile (a setting, a file): committed
        # as theirs, not taken up by a session. After a halt or a stall, a session's named leftovers go on as before
        print(f"not resumed: {len(dirty)} uncommitted change(s): {', '.join(dirty[:6])}. The next session starts from a commit, "
              "so commit them first from your own terminal, for instance:\n  git commit -m \"owner: done during the chain's wait\" -- "
              + " ".join(shlex.quote(d) for d in dirty) + "\nthen type `/resume-chain` again. An `— owner:` line the wait names is closed by `/resume-chain ok <note>`")
        return 1
    budget = {k: v for k, v in (("window", a.window), ("wrap_pct", a.wrap), ("cap_pct", a.cap)) if v is not None}
    new = dict(chain, **budget)
    if budget and not (int(new["window"]) > 0 and 0 < int(new["wrap_pct"]) < int(new["cap_pct"]) <= 100):
        print(f"not resumed: the budget needs a window above 0 and 0 < wrap ({new['wrap_pct']}) < cap ({new['cap_pct']}) <= 100")
        return 1
    note = (a.note or "").strip()
    outside = closed_outside(root, end, chain["id"])
    if not rec.get("closed_at"):
        close_link(root, chain, n, "abnormal", abnormal=True)   # before the owner's commit, which is not the session's work
    commit = ""
    if writes:
        import owner as ownerq
        try:
            ownerq._commit(root, writes, f"owner: closes {', '.join(closed)} (/resume-chain, chain {chain['id']})", None, False)
        except ownerq.Refused as e:
            print(f"not resumed, and no line closed: {e}")
            return 1
        commit = head(root)
    prev = chain.get("last_resume") or {}
    if not closed and prev.get("next") in (n, n + 1) and prev.get("closed"):
        closed, commit = prev["closed"], prev.get("commit", "")   # a retry after a launch that failed (cross-review, 2026-10-04)
    sha = rules_sha(root)
    if sha != chain.get("rules_sha"):
        event(root, chain["id"], "chain", "rules", f"resumed under new rules sha256 {sha[:12]} (was {chain.get('rules_sha', '')[:12]})")
        chain["rules_sha"] = sha
    if budget:
        event(root, chain["id"], "chain", "budget", f"hand over at {new['wrap_pct']}%, cap {new['cap_pct']}% of {int(new['window']):,} tokens "
              f"(was {chain['wrap_pct']}%, {chain['cap_pct']}% of {int(chain['window']):,})")
        chain.update(budget)
    (chain_dir(root, chain["id"]) / "stop").unlink(missing_ok=True)
    # at least one more session, and --more beyond that
    chain.update(state="running", reason="", max_sessions=max(int(chain["max_sessions"]), n + 1) + (a.more or 0),
                 last_resume={"at": now(), "via": f"/{RESUME_CMD}", "event": event_name, "session": by, "closed": closed,
                              "commit": commit, "outside": outside, "next": n + 1})
    save(root, chain)
    event(root, chain["id"], "chain", "resumed", f"by the owner's /{RESUME_CMD}" + (f" in session {by[:8]}" if by else "")
          + (f"; closed {', '.join(closed)} in {commit[:7]}" if closed else "") + (f"; note: {note[:200]}" if note else ""))
    if closed:
        print(f"closed {', '.join(closed)} as the owner in {commit[:7]}")
    if outside:
        print(f"closed since the wait by a commit that was not your /{RESUME_CMD}: {'; '.join(outside)}. "
              "The next session reopens each one your note does not say is yours")
    still = open_waited_lines(root, chain, n)
    if still:
        print(f"still open, and no chain session may close them: {', '.join(still)} (`/resume-chain <AC-n>` once done)")
    by_groups = groups.on_resume(root, chain, n, note, a.skip_review)
    if by_groups is not None:
        chain = load(root, chain["id"])
        g = groups.current(chain)
        what = (f"the review of group {groups.label(g['key'])} runs again" if g and g["state"] == "reviewing" else
                f"session {chain.get('sessions')} launched" if chain.get("state") == "running" else f"{chain['state']}: {chain.get('reason', '')}")
        print(f"chain {chain['id']} resumed: {what}")
        return 0 if by_groups else 1
    ok = start_link(root, chain, n + 1, prev_material(root, chain, n), note)
    print(f"chain {chain['id']} resumed: session {n + 1} " + ("launched" if ok else "NOT launched: " + load(root, chain["id"]).get("reason", "")))
    return 0 if ok else 1


# ---------------------------------------------------------------- the owner's resume

REF_RE = re.compile(r"(?:([\w.-]+):)?(AC-\d+)[,;.:]?", re.I)
INT_FLAGS = ("--window", "--wrap", "--cap", "--more")


def parse_resume(text: str) -> tuple[dict, list[tuple[str | None, str]], str, str]:
    """(options, line refs, note, problem) from what follows `/resume-chain`: a chain id first if any, the flags, the
    owner's lines to close (`ok` for every line the wait names, `skip` for none, or `AC-2`, `w1:AC-2`), then the note,
    kept verbatim. A note that starts with any other word closes nothing: `/resume-chain all good` is a note."""
    opts = {"id": None, "window": None, "wrap": None, "cap": None, "more": None, "skip_review": False, "mode": ""}
    refs: list[tuple[str | None, str]] = []
    rest = text
    while True:
        s = rest.lstrip()
        m = re.match(r"(\S+)(?:\s+|\Z)", s)
        if not m:
            return opts, refs, "", ""
        tok, after = m.group(1), s[m.end():]
        if tok == "--":
            return opts, refs, after.strip(), ""
        if refs and tok.startswith("--") and tok != "--":
            return opts, refs, s.strip(), ""   # flags come before the lines; after them, it is the note
        if tok == "--skip-review":
            opts["skip_review"] = True
        elif tok.split("=", 1)[0] in INT_FLAGS:
            name, _, val = tok.partition("=")
            if not val:
                m2 = re.match(r"(\S+)(?:\s+|\Z)", after)
                val, after = (m2.group(1), after[m2.end():]) if m2 else ("", "")
            if not re.fullmatch(r"[0-9]+", val):
                return opts, refs, "", f"{name} takes a whole number, not {val or 'nothing'!r}"
            opts[name[2:]] = int(val)
        elif not opts["mode"] and not refs and tok.lower() in ("ok", "skip"):
            opts["mode"] = tok.lower()
        elif opts["id"] is None and not refs and re.fullmatch(r"\d{8}-\d{6}", tok):
            opts["id"] = tok
        elif all(REF_RE.fullmatch(t) for t in tok.split(",") if t) and tok.strip(","):
            refs += [(r.group(1), r.group(2).upper()) for r in (REF_RE.fullmatch(t) for t in tok.split(",") if t)]
        else:
            return opts, refs, s.strip(), ""
        rest = after


def _open_owner_units(root: Path) -> list[tuple[str, str, str]]:
    """(unit id, path, text at HEAD) of the open units: the owner's lines are closed against the committed text, so
    a box the owner ticked by hand, uncommitted, is still found."""
    cfg = lib.load_config(root)
    finished = lib.as_list(cfg.get("done_statuses")) + list(lib.TERMINAL_STATUSES)
    out = []
    for uid, u in lib.taskets(root).items():
        if str(u.get("status", "")) in finished:
            continue
        r = lib.git(root, "show", f"HEAD:{u['_path']}")
        out.append((uid, u["_path"], r.stdout if r.returncode == 0 else ""))
    return out


def owner_ticks(root: Path, refs: list[tuple[str | None, str]]) -> tuple[dict[str, str], list[str], str]:
    """({path: text with the lines ticked}, ["w1 AC-2", ...], problem) for the owner's lines named by refs. A line is
    found among the open `— owner:` lines of open units, by its AC id, prefixed by its unit when two units have it."""
    if not refs:
        return {}, [], ""
    units = _open_owner_units(root)
    opened = [(uid, rp, k) for uid, rp, text in units for _, k, checked, marked in checks.acceptance_boxes(text)
              if marked and not checked]
    writes: dict[str, str] = {}
    closed: list[str] = []
    for unit, ac in refs:
        found = [x for x in opened if x[2] == ac and (unit is None or x[0] == unit)]
        if not found:
            return {}, [], (f"{unit + ':' if unit else ''}{ac} is not an open `— owner:` line of an open unit "
                            f"(open ones: {', '.join(f'{u}:{k}' for u, _, k in opened[:8]) or 'none'})")
        if len(found) > 1:
            return {}, [], f"{ac} is an owner line of {len(found)} units; name one: " + ", ".join(f"{u}:{ac}" for u, _, _ in found)
        uid, rp, _ = found[0]
        base = writes.get(rp) or next(t for u, p, t in units if p == rp)
        # the owner line itself, in the acceptance section: not a same-named box elsewhere (cross-review, 2026-10-04)
        at = next(o for o, k, checked, marked in checks.acceptance_boxes(base) if k == ac and marked and not checked)
        i = base.index("[ ]", at)
        writes[rp] = base[:i] + "[x]" + base[i + 3:]
        closed.append(f"{uid} {ac}")
    for rp, new in writes.items():
        at_head = next(t for u, p, t in units if p == rp)
        try:
            cur = (root / rp).read_text(encoding="utf-8")
        except OSError:
            cur = ""
        if cur not in (at_head, new):
            return {}, [], f"{rp} has uncommitted changes besides the owner's ticks; commit or undo them first"
    return writes, closed, ""


def closed_outside(root: Path, since: str, cid: str = "") -> list[str]:
    """The owner's lines closed by a commit after `since` (the commit the chain paused at), as "w1 AC-2 in <sha>
    (<subject>, <author>)": the owner from their own terminal, or an agent past the gates (docs/gates.md § What a
    gate cannot see). The resume names them and the next session reopens those the owner's note does not claim."""
    if not since:
        return []
    out = []
    for line in lib.git(root, "log", "--format=%H%x00%s%x00%an", f"{since}..HEAD", "--", lib.TASKETS_DIR).stdout.splitlines():
        sha, subject, author = (line.split("\0") + ["", ""])[:3]
        if cid and subject.startswith("owner: closes ") and subject.endswith(f"(/{RESUME_CMD}, chain {cid})"):
            continue   # the owner's own resume, whose launch failed; `last_resume` carries its lines
        for rp in lib.git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", sha, "--", lib.TASKETS_DIR).stdout.split():
            if not rp.endswith(".md"):
                continue
            old, new = lib.git(root, "show", f"{sha}^:{rp}"), lib.git(root, "show", f"{sha}:{rp}")
            for k in checks.owner_line_changes(old.stdout if old.returncode == 0 else "", new.stdout if new.returncode == 0 else ""):
                out.append(f"{Path(rp).stem} {k} in {sha[:7]} ({subject[:60]!r}, {author})")
    return out


def open_waited_lines(root: Path, chain: dict, n: int) -> list[str]:
    """The owner's lines still open in the units the last session's `## Wait` names."""
    hp = link_dir(root, chain["id"], n) / "handoff.md"
    if not hp.exists():
        return []
    acts = " ".join(wait_acts(lib.split_frontmatter(hp.read_text(encoding="utf-8"))[2]))
    out = []
    for uid, u in lib.taskets(root).items():
        if not re.search(rf"(?<![\w-]){re.escape(uid)}(?![\w-])", acts):
            continue
        text = (root / u["_path"]).read_text(encoding="utf-8", errors="replace")
        out += [f"{uid} {k}" for _, k, checked, marked in checks.acceptance_boxes(text) if marked and not checked]
    return out


def typed_by_owner(root: Path, sid: str) -> str:
    """Why a `/resume-chain` prompt in this session cannot be the owner's own typing; '' when it can. A headless
    session (`claude -p`, the SDK) takes its prompt from a program: Claude Code sets CLAUDE_CODE_ENTRYPOINT to
    `sdk-cli` and CLAUDE_CODE_SESSION_ATTENDED to 0 there, over what the caller passed (observed on 2.1.289; both
    are undocumented, docs/gates.md § What a gate cannot see). A chain session's prompts come from the chain."""
    ep, att = os.environ.get("CLAUDE_CODE_ENTRYPOINT", ""), os.environ.get("CLAUDE_CODE_SESSION_ATTENDED", "")
    if ep.startswith("sdk") or att == "0":
        return (f"this session is headless (CLAUDE_CODE_ENTRYPOINT={ep or '-'}, CLAUDE_CODE_SESSION_ATTENDED={att or '-'}): "
                "a program wrote this prompt, not the owner. Type it in an interactive Claude Code session")
    if not sid:
        return "no Claude Code session named this prompt; the owner types /resume-chain in an interactive session"
    j = joined(root, sid)
    if j:
        return (f"this is session {j[1]} of chain {j[0]['id']}, whose prompts come from the chain. "
                "Type it in a Claude Code session of your own")
    return ""


def owner_resume(root: Path, sid: str, args: str, event_name: str = "") -> tuple[bool, str]:
    """The owner's `/resume-chain <args>`, from the prompt hook. (resumed, what to show the owner)."""
    why = typed_by_owner(root, sid)
    if why:
        return False, why
    opts, refs, note, problem = parse_resume(args)
    if problem:
        return False, problem
    cid = load(root, opts["id"]).get("id")
    if not cid:
        return False, "no chain here" + (f" with id {opts['id']}" if opts["id"] else "")
    a = argparse.Namespace(window=opts["window"], wrap=opts["wrap"], cap=opts["cap"], more=opts["more"],
                           skip_review=opts["skip_review"], note=note)
    mode = opts["mode"]
    out = io.StringIO()
    # two resumes, or a resume and a stop, would each act on a stale state (cross-review, 2026-10-04)
    with chain_lock(root, cid), contextlib.redirect_stdout(out):
        code = _resume(root, cid, a, refs, sid, event_name, mode)
    return code == 0, out.getvalue().strip()


def _header(ok: bool, text: str) -> str:
    """done, refused (nothing changed), or partly done: the owner's lines were committed but no session started."""
    return "done" if ok else ("partly done" if "as the owner in" in text else "refused")


def owner_prompt(root: Path, data: dict) -> dict | None:
    """UserPromptSubmit and UserPromptExpansion: the owner typed `/resume-chain`. The hook resumes the chain itself and
    blocks the prompt, so the model never reads it and never acts on it; the owner reads the outcome. Claude Code runs
    no prompt hook for a skill the model invokes, and the command sets `disable-model-invocation`."""
    if data.get("hook_event_name") == "UserPromptExpansion":
        if (data.get("command_name") or "").lstrip("/") != RESUME_CMD:
            return None
        args = str(data.get("command_args") or "")
    else:
        m = RESUME_RE.match(data.get("prompt") or "")
        if not m:
            return None
        args = m.group(1)
    ok, text = owner_resume(root, data.get("session_id") or "", args, data.get("hook_event_name") or "")
    return {"block": f"charter /{RESUME_CMD}: {_header(ok, text)}\n{text}"}


def main(argv: list[str], root: Path) -> int:
    ap = argparse.ArgumentParser(prog="charter chain", description="A continuous chain of sessions over the road (docs/design/continuous-chain.md).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start", help="start a chain from a unit; launches session 1")
    s.add_argument("--unit", required=True)
    s.add_argument("--mission", default=None, help="the owner's instruction, verbatim")
    s.add_argument("--mission-file", default=None, help="the same, from a file (no shell quoting)")
    s.add_argument("--model", default=None); s.add_argument("--effort", default=None)
    s.add_argument("--window", type=int, default=None, help="context window in tokens (default: 1M for a [1m] model, else 200k)")
    s.add_argument("--wrap", type=int, default=None, help="hand-over line, percent of the window (default 25)")
    s.add_argument("--cap", type=int, default=None, help="hard cap, percent of the window (default 30)")
    s.add_argument("--max-sessions", type=int, default=None)
    s.add_argument("--launcher", default=None, help="auto | spawn | headless | a command template with {briefing}")
    s.add_argument("--here", action="store_true", help="stay on main/master instead of creating chain/<id>")
    s.add_argument("--review", default=None, help="review at the end of each group: auto | codex | off | a command template with {base} and {out}")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_start)
    n = sub.add_parser("next", help="validate this session's handoff, record its work, launch the next session")
    n.add_argument("--id", default=None); n.add_argument("--session", type=int, default=None)
    n.add_argument("--early", default=None, help="hand over under half the wrap line, and why")
    n.add_argument("--check", action="store_true", help="validate the handoff only; record nothing")
    n.set_defaults(fn=cmd_next)
    j = sub.add_parser("join", help="join this Claude Code session to a chain when the hook did not")
    j.add_argument("id"); j.add_argument("n", type=int); j.add_argument("--transcript", default=None); j.set_defaults(fn=cmd_join)
    st = sub.add_parser("status"); st.add_argument("id", nargs="?"); st.set_defaults(fn=cmd_status)
    w = sub.add_parser("watch", help="print events as they come until the chain ends (for Monitor)")
    w.add_argument("id", nargs="?"); w.add_argument("--from", dest="from_line", type=int, default=1)
    w.add_argument("--interval", type=float, default=3.0); w.add_argument("--timeout", type=float, default=None)
    w.set_defaults(fn=cmd_watch)
    sp = sub.add_parser("stop"); sp.add_argument("id", nargs="?"); sp.add_argument("--reason", default=None); sp.set_defaults(fn=cmd_stop)
    r = sub.add_parser("resume", help="after a wait, a halt or a stop: launch the next session, with the owner's note")
    r.add_argument("id", nargs="?"); r.add_argument("--note", default=None); r.add_argument("--note-file", default=None)
    r.add_argument("--more", type=int, default=None, help="raise max_sessions by this many")
    r.add_argument("--skip-review", action="store_true", help="after a review that could not run: clear the group without it")
    r.add_argument("--window", type=int, default=None, help="a new context window in tokens, for the sessions from now on")
    r.add_argument("--wrap", type=int, default=None, help="a new hand-over line, percent of the window")
    r.add_argument("--cap", type=int, default=None, help="a new hard cap, percent of the window")
    r.set_defaults(fn=cmd_resume)
    rr = sub.add_parser("review-run", help="(started by `chain next`) review a group, then launch the session that answers it")
    rr.add_argument("id"); rr.add_argument("--group", type=int, required=True); rr.set_defaults(fn=groups.cmd_review_run)
    rp = sub.add_parser("report", help="each group's review and its answers, as one pull-request comment")
    rp.add_argument("id", nargs="?"); rp.set_defaults(fn=groups.cmd_report)
    a = ap.parse_args(argv)
    return a.fn(root, a)
