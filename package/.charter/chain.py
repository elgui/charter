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
  <id>/chain.json             settings, mission, rules hash, state (running | halted | stopped | complete)
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
STATUSES = ("continue", "halt", "complete")
SECTIONS = ("Verified", "Done", "State", "Next", "Watch out")
MAX_LINES, MAX_BYTES = 80, 8192
EFFORTS = ("low", "medium", "high", "xhigh", "max")
ONE_M = 1_000_000
# what marks a process as part of this session, which a launched session must not inherit; the rest of
# the environment (auth, provider, CLAUDE_CONFIG_DIR) passes, as the spawn shim's PARENT_SESSION_ENV does
SESSION_ENV = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_ENTRYPOINT",
               "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
               "CLAUDE_PID", "CLAUDE_EFFORT", "CHARTER_OWNER", "CHARTER_UNIT")
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


def uncommitted(root: Path, rec: dict) -> list[str]:
    """What a session leaves uncommitted: changed tracked files, and untracked files that were not there when it
    was launched (a new file left out of every commit is work too)."""
    tracked = [d[3:] for d in lib.git(root, "status", "--porcelain", "--untracked-files=no").stdout.splitlines()]
    before = set(rec.get("untracked_at_launch") or [])
    return tracked + [p for p in untracked(root) if p not in before]


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
    if st == "continue" and nu not in lib.taskets(root):
        problems.append(f"`next_unit:` is {nu!r}, which is not a tasket in {lib.TASKETS_DIR}/; a chain that goes on names the unit it goes on with")
    for s in SECTIONS:
        if not _filled(lib.section(body, s)):
            problems.append(f"`## {s}` is missing or empty")
    if st == "halt" and not _filled(lib.section(body, "Halt")):
        problems.append("`status: halt` needs `## Halt`: what the owner must decide or do")
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


def handoff_status(text: str) -> tuple[str, str, str]:
    """(status, next_unit, first line of `## Halt`) of a handoff that passed check_handoff."""
    fields, _, body = lib.split_frontmatter(text)
    halt = next((l.strip("-* ").strip() for l in lib.section(body, "Halt").splitlines() if l.strip()), "")
    return str(fields.get("status", "")).strip(), str(fields.get("next_unit", "")).strip(), halt


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
    if prev is None:
        L += ["## Start", "", f"You are the first session. Start with unit `{chain['unit']}`: "
              f"`python3 .charter/bin/charter unit start {chain['unit']}`. Under `## Verified` in your handoff, write `first session`.", ""]
    else:
        handoff, fact = prev
        L += [f"## Handoff from session {n - 1} (verbatim)", "", handoff.strip(), "",
              f"## Mechanical verification of session {n - 1} (computed by `charter chain next`)", "", fact.strip(), "",
              "Verify that work first (chain rules, step 1), then go on from its `## Next`.", ""]
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
    rec = {"n": n, "launched_at": now(), "launch_head": head(root), "untracked_at_launch": untracked(root)}
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
    return True


def halt(root: Path, chain: dict, reason: str, state: str = "halted") -> None:
    chain["state"], chain["reason"], chain["ended"] = state, reason, now()
    save(root, chain)
    event(root, chain["id"], "chain", state, reason)


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
            f"The owner resumes with a larger budget (`charter chain resume --window <tokens>`, or `--wrap <pct> --cap <pct>`), "
            "or trims what every session loads at start-up")


def prev_material(root: Path, chain: dict, n: int) -> tuple[str, str]:
    """(handoff, facts) of session n for its successor's briefing; a session that never handed over gets a stub."""
    d = link_dir(root, chain["id"], n)
    hp, fp = d / "handoff.md", d / "facts.md"
    handoff = hp.read_text(encoding="utf-8") if hp.exists() else (
        f"(Session {n} ended without a handoff. Read the active unit's `## Log` and the commits below; "
        "trust nothing it did not commit.)")
    return handoff, fp.read_text(encoding="utf-8") if fp.exists() else "(no verification recorded)"


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
    if not link(root, chain["id"], n):
        return f"charter chain {chain['id']} has no session {n}. Do no work for it; end your turn."
    if rules_sha(root) != chain.get("rules_sha"):
        halt(root, chain, f"{RULES} changed since the chain started; a chain runs under one version of its rules. "
             "The owner resumes it with `charter chain resume`, which adopts the new rules")
        return f"charter chain {chain['id']} is halted: its rules changed. Do no work for it; end your turn."
    with editing_link(root, chain["id"], n) as rec:
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
    if tool == "AskUserQuestion":
        return {"deny": "charter chain: a chain session does not ask the owner mid-session. Hand over with `status: halt` "
                        "and put the question under `## Halt`; the owner answers it and resumes the chain."}
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
              "the chain waits: the owner looks at the tab, then `charter chain resume` or `charter chain stop`")
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


def cmd_start(root: Path, a) -> int:
    cfg = lib.load_config(root)
    cc = cfg.get("chain") or {}
    problems = []
    if not (root / lib.TOOL_DIR).is_dir():
        problems.append(f"{root} is not on charter")
    cur = load(root)
    if cur.get("state") == "running":
        problems.append(f"chain {cur['id']} is running; `charter chain stop` first, or follow it with `charter chain watch`")
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
    cid = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
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
    elif (chain_dir(root, chain["id"]) / "stop").exists():
        halt(root, chain, "stopped by the owner", state="stopped")
    elif n >= int(chain["max_sessions"]):
        halt(root, chain, f"reached max_sessions ({chain['max_sessions']}); the owner resumes with `charter chain resume`")
    elif started_past_line(chain, link(root, chain["id"], n)):
        halt(root, chain, started_past_line(chain, link(root, chain["id"], n)))
    elif stalled(root, chain, n):
        halt(root, chain, f"sessions {n - 1} and {n} changed nothing outside {lib.TASKETS_DIR}/ and checked no criterion")
    elif rules_sha(root) != chain.get("rules_sha"):
        halt(root, chain, f"{RULES} changed while the chain ran; the owner resumes with `charter chain resume`")
    else:
        groups.advance(root, chain, n, status, next_unit)
    chain = load(root, chain["id"])
    g = groups.current(chain)
    then = (f", the review of group {groups.label(g['key'])} is running and the next session starts when it ends"
            if g and g["state"] == "reviewing" else f", session {n + 1} launched")
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
    chain = load(root, a.id)
    if not chain:
        print("no chain here")
        return 1
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
    budget = {k: v for k, v in (("window", a.window), ("wrap_pct", a.wrap), ("cap_pct", a.cap)) if v is not None}
    new = dict(chain, **budget)
    if budget and not (int(new["window"]) > 0 and 0 < int(new["wrap_pct"]) < int(new["cap_pct"]) <= 100):
        print(f"charter chain resume: not resumed: the budget needs a window above 0 and 0 < wrap ({new['wrap_pct']}) "
              f"< cap ({new['cap_pct']}) <= 100")
        return 1
    note = (Path(a.note_file).read_text(encoding="utf-8") if a.note_file else a.note or "").strip()
    if not rec.get("closed_at"):
        close_link(root, chain, n, "abnormal", abnormal=True)
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
    chain.update(state="running", reason="", max_sessions=max(int(chain["max_sessions"]), n + 1) + (a.more or 0))
    save(root, chain)
    event(root, chain["id"], "chain", "resumed", note[:200] or "by the owner")
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
    r = sub.add_parser("resume", help="after a halt or a stop: launch the next session, with the owner's note")
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
