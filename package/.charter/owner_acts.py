"""The owner's acts at a chain's wait (0.4.11; docs/design/continuous-chain.md § The owner's side of a wait).

A session that waits on the owner writes every act into `owner.md` beside its handoff: one `## <n>. <title>` per act,
the `— owner:` lines it closes, and, for an act that is a command, the command in a fenced block and the result it
expects. At the hand-over a reviewer of another model family (Codex, read-only) judges each act: whether the owner is
needed at all, the risk, what it touches, whether it can be undone. An act an agent could do goes back to the session.
The owner runs every act with one command, `charter owner run`, which records each one's outcome; `/resume-chain ok`
then closes exactly the lines whose acts passed. Nothing here closes a line or resumes a chain: the owner's
`/resume-chain` does, through `chain._resume`.

In the record that prompted it (chain 20261005-183724 of hermes-custom, 2026-10-05), two waits listed 16 acts. Ten were
commands under sudo or Touch ID that the owner pasted one at a time while an agent read each output; the resume line
named 7 lines by hand, because `ok` would also have closed one that failed and two not done.

Files, in the session's link directory (<git>/charter/chain/<id>/sNN/):
  owner.md            the acts, written by the session (template: charter/templates/owner.md)
  owner-review.json   the review, pinned to owner.md's SHA-256
  owner-run.json      the owner's runs, per step, pinned the same way
  owner-run.log       the full output of every run
Python 3 standard library only."""
from __future__ import annotations

import codecs
import datetime as dt
import hashlib
import json
import os
import re
import select
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import checks
import lib

OWNER_FILE, REVIEW_FILE, RUN_FILE, RUN_LOG = "owner.md", "owner-review.json", "owner-run.json", "owner-run.log"
TEMPLATE = "charter/templates/owner.md"
RUN_CMD = "python3 .charter/bin/charter owner run"
REVIEW_ENV = "CHARTER_OWNER_REVIEW"   # overrides the chain's setting; the tests set it to `off`
STEP_RE = re.compile(r"^##\s+(\d+)\.\s+(\S.*?)\s*$")
FIELD_RE = re.compile(r"^([a-z][a-z_-]*):(?:\s+(.*?))?\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)\s*([\w+-]*)\s*$")
FIELDS = ("closes", "do", "check", "expect-exit", "expect-output", "stop-on-fail", "later", "owner-because", "read", "timeout")
REF_RE = re.compile(r"^(?:([\w.-]+)[\s:]+)?(AC-\d+)$", re.I)
TEXT_REF_RE = re.compile(r'^([\w.-]+)\s+"([^"]+)"$')   # a line without an AC id, by its text: `u1 "FileVault is on"`
YES = ("yes", "true", "1")
PLACEHOLDER_RE = re.compile(r"<[A-Za-z][A-Za-z0-9_-]*>")   # as `chain.PLACEHOLDER_RE` (0.4.10): `<<EOF` and `< in.txt` are not one
# what `/resume-chain ok` closes: a command or a check that passed, a manual act the owner confirmed, or one they were not asked
OK_STATUSES = ("passed", "confirmed", "unasked")
CLASSES = ("agent_can_do", "owner_credential", "owner_judgement", "owner_outward")
RISKS = ("low", "medium", "high")
TAIL = 1500   # characters of a step's output kept in owner-run.json, and passed on to the next session when it failed


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def path(root: Path, cid: str, n: int, name: str = OWNER_FILE) -> Path:
    import chain
    return chain.link_dir(root, cid, n) / name


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_json(p: Path, data: dict) -> None:
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(p)


# ---------------------------------------------------------------- owner.md

def parse(text: str) -> tuple[list[dict], list[str]]:
    """(steps, problems) of owner.md. A step is {n, title, kind, closes [(unit, AC-n)], fields, command, text}; kind is
    `command` (a fenced block), `later` (`later: yes`, never run, never closed by `ok`) or `manual`."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    steps: list[dict] = []
    problems: list[str] = []
    cur, fence, code = None, None, []
    for raw in text.splitlines():
        if fence:
            if raw.strip() == fence:
                if cur["command"] is not None:
                    problems.append(f"step {cur['n']}: more than one fenced block; one command per act (join them with `&&`, or split the act)")
                cur["command"] = "\n".join(code).strip()
                fence, code = None, []
            else:
                code.append(raw)
            continue
        m = STEP_RE.match(raw)
        if m:
            cur = {"n": int(m.group(1)), "title": m.group(2), "fields": {}, "command": None, "text": []}
            steps.append(cur)
            continue
        if cur is None:
            continue
        f = FENCE_RE.match(raw)
        if f:
            fence = f.group(1)
            continue
        fm = FIELD_RE.match(raw.strip())
        if fm and not raw.startswith((" ", "\t")):
            key, val = fm.group(1), (fm.group(2) or "").strip()
            if key not in FIELDS:
                problems.append(f"step {cur['n']}: unknown field `{key}:` (known: {', '.join(FIELDS)}); prose goes under `do:`")
            elif key in cur["fields"]:
                problems.append(f"step {cur['n']}: `{key}:` twice")
            else:
                cur["fields"][key] = val
            continue
        if raw.strip():
            cur["text"].append(raw.strip())
    if fence:
        problems.append(f"step {cur['n']}: a fenced block that is not closed")
    for s in steps:
        fl = s["fields"]
        s["kind"] = "later" if fl.get("later", "").lower() in YES else ("command" if s["command"] is not None else "manual")
        s["closes"], bad = refs(fl.get("closes", ""))
        problems += [f"step {s['n']}: `closes:` {b!r} is not `<unit> AC-n` (or `<unit> \"<line text>\"` for a line without an id)" for b in bad]
        if s["kind"] == "manual" and not fl.get("do"):
            problems.append(f"step {s['n']}: an act that is not a command says how it is done under `do:`")
        if s["kind"] == "command" and not s["command"]:
            problems.append(f"step {s['n']}: its fenced block is empty")
        if "check" in fl and s["kind"] != "manual":
            problems.append(f"step {s['n']}: `check:` belongs to an act that is not a command; a command says what it expects with `expect-exit:` or `expect-output:`")
        if fl.get("expect-exit") and not re.fullmatch(r"nonzero|\d+(?:\s*,\s*\d+)*", fl["expect-exit"].strip()):
            problems.append(f"step {s['n']}: `expect-exit:` is `0`, `nonzero` or exit codes separated by commas, not {fl['expect-exit']!r}")
        if fl.get("expect-output"):
            try:
                re.compile(fl["expect-output"])
            except re.error as e:
                problems.append(f"step {s['n']}: `expect-output:` is not a regular expression ({e})")
        held = [m for c in (s["command"] or "", fl.get("check", "")) for m in PLACEHOLDER_RE.findall(_outside_heredocs(c))]
        if held:
            problems.append(f"step {s['n']}: its command holds {', '.join(f'`{h}`' for h in dict.fromkeys(held))}: pasted or run in a shell, "
                            "`<bucket>` is a redirection. Prompt with `read` (`read \"b?R2 bucket name: \"`) or set the value on a first line "
                            "to edit; a command is paste-ready (chain rules, section 5)")
        if fl.get("timeout") and not re.fullmatch(r"[0-9]+", fl["timeout"].strip()):
            problems.append(f"step {s['n']}: `timeout:` is a number of seconds")
    if not steps:
        problems.append(f"no act: one `## 1. <title>` per act (template: {TEMPLATE})")
    elif [s["n"] for s in steps] != list(range(1, len(steps) + 1)):
        problems.append(f"acts are numbered {', '.join(str(s['n']) for s in steps)}; number them 1 to {len(steps)} in the order the owner does them")
    return steps, problems


def _outside_heredocs(cmd: str) -> str:
    """The command without the bodies of its here-documents: a plist's `<dict>` there is text, not a placeholder."""
    out, end = [], None
    for line in cmd.splitlines():
        if end is not None:
            if line.strip() == end:
                end = None
            continue
        out.append(line)
        m = re.search(r"<<-?\s*(['\"]?)(\w+)\1", line)
        if m:
            end = m.group(2)
    return "\n".join(out)


def refs(field: str) -> tuple[list[tuple[str, str]], list[str]]:
    """`u1 AC-2, AC-3, u2:AC-1` -> [(u1, AC-2), (u1, AC-3), (u2, AC-1)]; `-` and `none` are none. An AC id without a unit
    takes the unit before it. A line without an id is named by its text, quoted: `u1 "FileVault is on"` (its key, as
    `checks.acceptance_boxes` gives it: the text before the first ` — `, lowercased)."""
    out, bad, unit = [], [], None
    if field.strip().lower() in ("", "-", "none", "nothing"):
        return out, bad
    for part in re.findall(r'(?:"[^"]*"|[^,])+', field):   # a comma inside a quoted line text does not split it
        t = TEXT_REF_RE.match(part.strip())
        if t:
            unit = t.group(1)
            out.append((unit, re.split(r"\s[—–]\s", t.group(2))[0].strip().lower()))
            continue
        m = REF_RE.match(part.strip())
        if not m or not (m.group(1) or unit):
            bad.append(part.strip())
            continue
        unit = m.group(1) or unit
        out.append((unit, m.group(2).upper()))
    return out, bad


def open_owner_lines(root: Path, tree: bool = False) -> set[tuple[str, str]]:
    """(unit, key) of every open `— owner:` line of an open unit, against the committed text (what the resume's commit
    starts from), or the working tree's with `tree` (a box the owner ticked by hand is no longer waited on)."""
    import chain
    units = chain._open_owner_units(root)
    if tree:
        units = [(uid, rp, (root / rp).read_text(encoding="utf-8", errors="replace") if (root / rp).exists() else "") for uid, rp, _ in units]
    return {(uid, k) for uid, _, text in units for _, k, checked, marked in checks.acceptance_boxes(text) if marked and not checked}


def validate(root: Path, text: str) -> list[str]:
    """What keeps owner.md from being accepted at the hand-over, in words."""
    steps, problems = parse(text)
    opened = open_owner_lines(root)
    ids = set(lib.taskets(root)) | set(lib.decisions(root)) | set(lib.change_requests(root))
    for s in steps:
        missing = [f"{u} {k}" for u, k in s["closes"] if (u, k) not in opened]
        if missing:
            problems.append(f"step {s['n']}: closes {', '.join(missing)}, which is not an open `— owner:` line of an open unit "
                            f"(mark the line `— owner: do|check|decide` and commit it; open ones: {', '.join(f'{u} {k}' for u, k in sorted(opened)[:8]) or 'none'})")
        words = " ".join([s["title"], s["fields"].get("do", ""), s["fields"].get("read", ""), " ".join(s["text"])])
        if not s["closes"] and not any(re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", words) for i in ids):
            problems.append(f"step {s['n']} ({s['title'][:50]}) closes no line and names no unit, decision or change request: "
                            "say what it is for, with `closes:` or the unit it prepares")
    return problems


def load(root: Path, cid: str, n: int) -> tuple[str, list[dict]] | None:
    """(text, steps) of session n's owner.md, None when it has none (a wait handed over before 0.4.11)."""
    p = path(root, cid, n)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    return text, parse(text)[0]


def waited_lines(steps: list[dict]) -> list[tuple[str, str]]:
    seen: list[tuple[str, str]] = []
    for s in steps:
        seen += [r for r in s["closes"] if r not in seen]
    return seen


def summary(steps: list[dict]) -> str:
    """One line for the chain's reason, the event log and the notification."""
    run = sum(1 for s in steps if s["kind"] == "command" or (s["kind"] == "manual" and s["fields"].get("check")))
    later = sum(1 for s in steps if s["kind"] == "later")
    return (f"{len(steps)} act(s) in owner.md ({run} to run with `charter owner run`" + (f", {later} for later" if later else "")
            + "): " + "; ".join(s["title"] for s in steps[:4]) + (f" (+{len(steps) - 4} more)" if len(steps) > 4 else ""))


# ---------------------------------------------------------------- the review

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["steps"], "properties": {"steps": {"type": "array", "items": {
    "type": "object", "additionalProperties": False,
    "required": ["n", "class", "why", "risk", "reversible", "touches", "read", "beyond_title"],
    "properties": {"n": {"type": "integer"}, "class": {"type": "string", "enum": list(CLASSES)}, "why": {"type": "string"},
                   "risk": {"type": "string", "enum": list(RISKS)}, "reversible": {"type": "boolean"},
                   "touches": {"type": "string"}, "read": {"type": "string"}, "beyond_title": {"type": "boolean"}}}}}}

PROMPT = """You review, read-only, the acts a coding agent handed to the owner of this repository. The agent is a Claude Code
session in a chain of sessions working on the owner's Mac. It runs commands as the owner's user but cannot type a
password, touch the Touch ID sensor, use a graphical interface, read the owner's secrets or password manager, or act on
accounts outside this machine. The owner will run the commands below in their own shell, one command for all of them,
and most often without reading them: your notes are what they read. Judge each act. Do not run anything that changes
state; you may read any file of the repository (a script an act runs, the units in .taskets/).

For each act, in order, one entry:
- class: agent_can_do (the agent could do it itself with its own rights: no password, Touch ID, graphical interface,
  secret or effect outside this machine, and nothing in it calls for the owner's judgement), owner_credential (it needs
  sudo, Touch ID, a password or a secret only the owner holds), owner_judgement (a choice, an approval or a check only
  the owner can make), owner_outward (an effect outside this machine: an account, a purchase, a publication, a push).
- why: one or two plain sentences: what the act does, and why it is that class.
- risk: high when it changes system or security configuration, root-owned files, accounts, sudoers or launchd, deletes
  data, or cannot be undone; medium when it changes the machine's state in a way that can be undone; low when it only
  reads, or changes temporary files or this repository.
- reversible: whether the change can be undone.
- touches: what it changes on the machine, in a few words.
- read: the one place the owner should read before running it (a path:line, or a command's part), or "" when none.
- beyond_title: true when the command does more than its title says (deletes, installs or sends something the title
  does not name).

A rule that lets a command run as root without a password (sudoers NOPASSWD) is high risk. Check that every command it
allows is a root-owned file in a root-owned directory that the owner's user cannot write; otherwise say in `why` that
anything able to edit that file gets root.

{sudo}

The owner lines the acts close, as the units have them:
{lines}

owner.md, verbatim:

{owner}
"""


def review_mode(chain: dict, cfg: dict) -> tuple[str, str]:
    """(mode, detail): codex, off or command; `auto` is codex when it is on PATH. The environment wins over the chain."""
    name = (os.environ.get(REVIEW_ENV) or chain.get("owner_review") or str((cfg.get("chain") or {}).get("owner_review", "auto"))).strip()
    if name in ("auto", "codex"):
        exe = shutil.which("codex")
        return ("codex", exe) if exe else ("off", "`codex` is not on PATH")
    if name == "off":
        return "off", "off"
    if "{out}" in name:
        return "command", name
    return "off", f"owner_review {name!r} is not auto, codex, off or a command template with {{out}}"


def _sudo_context() -> str:
    """What the owner's user may run as root without a password, so that the review can tell such a step from one that asks."""
    if not shutil.which("sudo"):
        return "sudo is not on this machine."
    try:
        r = subprocess.run(["sudo", "-n", "-l"], capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return "What sudo allows without a password is unknown."
    if r.returncode != 0:
        return "`sudo -n -l` needs a password here, so every sudo in these acts asks the owner (Touch ID or password)."
    return "`sudo -n -l` (what the owner's user may run as root, NOPASSWD entries run without asking):\n" + r.stdout.strip()[:3000]


def _line_texts(root: Path, steps: list[dict]) -> str:
    import chain
    texts = {}
    for uid, _, text in chain._open_owner_units(root):
        for off, k, checked, marked in checks.acceptance_boxes(text):
            if marked and not checked:
                end = text.find("\n", off)
                texts[(uid, k)] = text[off:end if end >= 0 else len(text)].strip()
    rows = [f"- {u} {k}: {texts.get((u, k), '(not found)')}" for u, k in waited_lines(steps)]
    return "\n".join(rows) or "- none"


def review(root: Path, chain: dict, n: int, cfg: dict, timeout: int | None = None) -> dict:
    """Review session n's owner.md, once per version of it: a review whose `sha` matches is reused. Never raises; a
    review that cannot run is recorded as not reviewed, with why, and the wait goes on without it."""
    text, steps = load(root, chain["id"], n) or ("", [])
    rp = path(root, chain["id"], n, REVIEW_FILE)
    old = _read_json(rp)
    if old.get("sha") == sha(text) and old.get("mode"):
        return old
    mode, detail = review_mode(chain, cfg)
    rec = {"sha": sha(text), "at": now(), "mode": mode, "reviewed": False, "why": "", "steps": []}
    if mode == "off":
        rec["why"] = "review off" if detail == "off" else f"review off: {detail}"
        _write_json(rp, rec)
        return rec
    d = rp.parent
    prompt_p, schema_p, out_p = d / "owner-review.prompt.md", d / "owner-review.schema.json", d / "owner-review.out.json"
    prompt_p.write_text(PROMPT.format(sudo=_sudo_context(), lines=_line_texts(root, steps), owner=text), encoding="utf-8")
    schema_p.write_text(json.dumps(SCHEMA), encoding="utf-8")
    out_p.unlink(missing_ok=True)
    cc = cfg.get("chain") or {}
    timeout = timeout or int(cc.get("owner_review_timeout_s", 300))
    if mode == "codex":
        argv = [detail, "exec", "-C", str(root), "-s", "read-only", "--ephemeral", "--output-schema", str(schema_p), "-o", str(out_p),
                "-c", f"model_reasoning_effort={cc.get('owner_review_effort', 'medium')}", "-"]
    else:
        argv = [a.format(prompt=str(prompt_p), schema=str(schema_p), out=str(out_p), root=str(root)) for a in shlex.split(detail)]
    t0 = time.monotonic()
    try:
        with open(prompt_p, encoding="utf-8") as stdin:
            r = subprocess.run(argv, stdin=stdin, capture_output=True, text=True, cwd=str(root), timeout=timeout)
        rec["seconds"] = round(time.monotonic() - t0)
        if r.returncode != 0:
            rec["why"] = f"the reviewer exited {r.returncode}: {(r.stderr or r.stdout).strip()[-300:]}"
    except subprocess.TimeoutExpired:
        rec["why"] = f"the reviewer did not finish in {timeout} s"
    except OSError as e:
        rec["why"] = f"the reviewer could not start: {e}"
    if not rec["why"]:
        got = _read_json(out_p)
        items = got.get("steps") if isinstance(got, dict) else None
        if not isinstance(items, list):
            rec["why"] = "the reviewer returned no `steps` list"
        else:
            by_n = {int(i["n"]): i for i in items if isinstance(i, dict) and str(i.get("n", "")).isdigit()}
            if sorted(by_n) != [s["n"] for s in steps]:
                rec["why"] = f"the reviewer judged acts {sorted(by_n)}, and owner.md has {[s['n'] for s in steps]}"
            else:
                rec["steps"] = [{k: by_n[s["n"]].get(k) for k in SCHEMA["properties"]["steps"]["items"]["properties"]} for s in steps]
                rec["reviewed"] = True
    _write_json(rp, rec)
    return rec


def load_review(root: Path, cid: str, n: int, text: str) -> dict:
    rec = _read_json(path(root, cid, n, REVIEW_FILE))
    return rec if rec.get("sha") == sha(text) else {}


def sent_back(rec: dict, steps: list[dict]) -> list[str]:
    """The acts the review says an agent could do, that the session did not keep with `owner-because:`."""
    by_n = {s["n"]: s for s in steps}
    return [f"step {i['n']} ({by_n[i['n']]['title'][:60]}): {i.get('why', '')}" for i in rec.get("steps") or []
            if i.get("class") == "agent_can_do" and not by_n[i["n"]]["fields"].get("owner-because")]


def note_line(item: dict | None) -> str:
    """The review of one act, as the owner reads it before running it."""
    if not item:
        return ""
    bits = [f"{item.get('risk', '?')} risk", "can be undone" if item.get("reversible") else "cannot be undone"]
    if item.get("beyond_title"):
        bits.append("does more than its title says")
    out = f"Codex: {', '.join(bits)}; touches {item.get('touches') or '?'}"
    if item.get("read"):
        out += f"; read {item['read']}"
    return out + (f". {item['why']}" if item.get("why") else "")


# ---------------------------------------------------------------- what the owner sees

def act_lines(root: Path, cid: str, n: int) -> tuple[list[str], str]:
    """(acts, note) of session n's owner.md as the owner reads them in `charter owner`, `charter next` and the closing
    message of the session that waits: one entry per act (its title and what it closes, the command or how it is done,
    Codex's note on it), and a note when no second model reviewed them. `chain.owner_steps` adds the commands."""
    got = load(root, cid, n)
    if got is None:
        return [], ""
    text, steps = got
    rec = load_review(root, cid, n, text)
    rev = {i["n"]: i for i in (rec.get("steps") or [])}
    ran = load_run(root, cid, n, text).get("steps") or {}
    acts = []
    for s in steps:
        tag = {"command": "run", "manual": "check" if s["fields"].get("check") else "you", "later": "later"}[s["kind"]]
        status = (ran.get(str(s["n"])) or {}).get("status")
        closes = ", ".join(f"{u} {k}" for u, k in s["closes"]) or "nothing"
        L = [f"{s['n']}. [{tag}] {s['title']} (closes {closes})" + (f" — last run: {status}" if status else "")]
        if s["fields"].get("do"):
            L.append(f"   do: {s['fields']['do']}")
        if s["fields"].get("read"):
            L.append(f"   read: {s['fields']['read']}")
        if s["kind"] == "command":
            first = s["command"].splitlines()
            L.append(f"   $ {first[0]}" + (f"  (+{len(first) - 1} lines)" if len(first) > 1 else ""))
        if rev.get(s["n"]):
            L.append(f"   {note_line(rev[s['n']])}")
        acts.append("\n".join(L))
    note = "" if rec.get("reviewed") else f"(not reviewed by a second model: {rec.get('why') or 'no review recorded'})"
    return acts, note


# ---------------------------------------------------------------- the owner's run

def load_run(root: Path, cid: str, n: int, text: str) -> dict:
    rec = _read_json(path(root, cid, n, RUN_FILE))
    return rec if rec.get("sha") == sha(text) else {}


def _expects(s: dict, code: int, output: str) -> tuple[bool, str]:
    if code < 0:
        # killed (a timeout, a signal): never a pass, even for `expect-exit: nonzero` (cross-review of 2026-10-05)
        return False, f"killed by signal {-code}" + (" (its timeout)" if "\n(stopped after " in output else "")
    want = (s["fields"].get("expect-exit") or "0").strip()
    ok_exit = code != 0 if want == "nonzero" else code in {int(x) for x in re.split(r"\s*,\s*", want)}
    if not ok_exit:
        return False, f"exit {code}, expected {want}"
    pat = s["fields"].get("expect-output")
    if pat and not re.search(pat, output):
        return False, f"output does not match `{pat}`"
    return True, f"exit {code}" + (f", output matches `{pat}`" if pat else "")


def _descendants(pid: int) -> list[int]:
    """Every process under pid, deepest first, from `ps`: what a timeout kills besides the shell."""
    try:
        rows = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True, timeout=5).stdout.split("\n")
    except (OSError, subprocess.TimeoutExpired):
        return []
    kids: dict[int, list[int]] = {}
    for row in rows:
        bits = row.split()
        if len(bits) == 2 and bits[0].isdigit() and bits[1].isdigit():
            kids.setdefault(int(bits[1]), []).append(int(bits[0]))
    out, todo = [], [pid]
    while todo:
        for c in kids.get(todo.pop(), []):
            out.append(c)
            todo.append(c)
    return out[::-1]


def _execute(cmd: str, root: Path, timeout: int | None, log, out) -> tuple[int, str]:
    """Run one command in the owner's shell, at the repository root, with the owner's terminal for sudo's prompt (the
    process group and the session stay the owner's, so sudo can read the terminal). Its output goes to the screen as it
    comes, a prompt without a newline included, and is kept. A `timeout:` kills the shell and everything under it; once
    the shell has exited, a process it left behind holding the output does not hold the run. Ctrl-C reaches the command
    and stops the run (cross-review of 2026-10-05)."""
    # zsh, as the paste-ready standard writes for (`read "b?name: "` is zsh's), and the terminal as stdin, so that a `read`
    # or a wizard reads the owner's keys even when `charter owner run` itself got no stdin (cross-review of 2026-10-05)
    shell = "/bin/zsh" if os.path.exists("/bin/zsh") else "/bin/sh"
    try:
        tty_in = open("/dev/tty", "rb")
    except OSError:
        tty_in = None
    proc = subprocess.Popen([shell, "-c", cmd], cwd=str(root), stdin=tty_in, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    fired = threading.Event()

    def kill():
        fired.set()
        for pid in _descendants(proc.pid) + [proc.pid]:
            try:
                os.kill(pid, 9)
            except OSError:
                pass

    timer = threading.Timer(timeout, kill) if timeout else None
    if timer:
        timer.start()
    buf: list[str] = []
    dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
    fd = proc.stdout.fileno()
    exited_at = None
    try:
        while True:
            ready = select.select([fd], [], [], 0.2)[0]
            if ready:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                text = dec.decode(chunk)
                buf.append(text)
                out.write(text)
                out.flush()
                log.write(text)
            elif proc.poll() is not None:
                exited_at = exited_at or time.monotonic()
                if time.monotonic() - exited_at > 1.0:
                    break
        tail = dec.decode(b"", final=True)
        if tail:
            buf.append(tail)
            out.write(tail)
            log.write(tail)
        code = proc.wait()
    except KeyboardInterrupt:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            kill()
        raise
    finally:
        if timer:
            timer.cancel()
        if tty_in:
            tty_in.close()
    if fired.is_set():
        buf.append(f"\n(stopped after {timeout} s)\n")
        code = code if code < 0 else -9
    return code, "".join(buf)


def _ask(question: str, inp, out) -> bool:
    out.write(f"   {question} [y/N] ")
    out.flush()
    ans = inp.readline()
    return ans.strip().lower() in ("y", "yes", "o", "oui")


def _one_act(s: dict, root: Path, rev: dict, stop: str, ask: bool, inp, out, log) -> dict:
    """The outcome of one act: status and why, and for a command its exit and the end of its output."""
    if stop:
        return {"status": "skipped", "why": stop}
    if s["kind"] == "later":
        print("   later: not run now; its lines stay open", file=out)
        return {"status": "later", "why": "for later: not run, stays open"}
    if s["kind"] == "manual" and not s["fields"].get("check"):
        print(f"   do: {s['fields'].get('do', '')}", file=out)
        if not ask:
            return {"status": "unasked", "why": "no terminal to ask: your `/resume-chain ok` says it is done"}
        done = _ask("Done?", inp, out)
        return {"status": "confirmed" if done else "declined", "why": "the owner said " + ("yes" if done else "no")}
    cmd = s["command"] if s["kind"] == "command" else s["fields"]["check"]
    if s["kind"] == "manual":
        print(f"   do: {s['fields'].get('do', '')}\n   check: {cmd}", file=out)
    else:
        if s["fields"].get("do"):   # the answers to an interactive command, before it runs (cross-review of 2026-10-05)
            print(f"   do: {s['fields']['do']}", file=out)
        for line in cmd.splitlines():
            print(f"   $ {line}", file=out)
    if ask and rev.get("risk") == "high" and not _ask("Codex rates this high risk. Run it?", inp, out):
        return {"status": "declined", "why": "the owner declined it at the prompt"}
    t = s["fields"].get("timeout")
    code, output = _execute(cmd, root, int(t) if t else None, log, out)
    ok, why = _expects(s, code, output)
    return {"status": "passed" if ok else "failed", "exit": code, "why": why, "tail": output[-TAIL:]}


def run(root: Path, chain: dict, only: list[int] | None = None, assume_yes: bool = False, inp=None, out=None) -> int:
    """`charter owner run`: the owner runs the acts of the waiting chain's owner.md in their shell, in order. A command
    passes when it exits and prints as its step expects; a manual act with a `check:` passes when the check exits 0;
    one without is confirmed by the owner at a terminal, else left to their `ok`. Records owner-run.json and owner-run.log."""
    out = out or sys.stdout
    if inp is None:
        # the terminal itself, as sudo reads it: there whenever the owner has one, stdin redirected or not; Claude Code
        # does not document whether a `!` command gets one (https://code.claude.com/docs/en/interactive-mode)
        try:
            inp = open("/dev/tty", "r", encoding="utf-8")
        except OSError:
            inp = None
    cid, n = chain["id"], int(chain.get("sessions") or 0)
    if chain.get("state") != "waiting":
        print(f"charter owner run: chain {cid} is {chain.get('state')}, not waiting on you; nothing to run", file=out)
        return 1
    got = load(root, cid, n)
    if got is None:
        print(f"charter owner run: session {n} of chain {cid} waits with no owner.md (handed over before charter 0.4.11): "
              "do its `## Wait` acts by hand (`python3 .charter/bin/charter owner` lists them)", file=out)
        return 1
    text, steps = got
    import chain as chainlib
    pinned = chainlib.link(root, cid, n).get("owner_sha")
    if pinned != sha(text):   # a missing pin too: an owner.md that `chain next` never reviewed (cross-review of 2026-10-05)
        print(f"charter owner run: refused: {path(root, cid, n)} changed after session {n} handed it over and Codex reviewed it. "
              "Nothing ran. A changed act is a session's work: stop the chain, or resume it with `skip` and a note", file=out)
        return 1
    if only is not None and not only:
        print("charter owner run: --only names no act; give act numbers (`--only 2` or `--only 2,5`)", file=out)
        return 2
    if only:
        unknown = [k for k in only if k not in {s["n"] for s in steps}]
        if unknown:
            print(f"charter owner run: no act {', '.join(map(str, unknown))} in owner.md (acts 1 to {len(steps)})", file=out)
            return 1
    tty = inp is not None and hasattr(inp, "isatty") and inp.isatty()
    rev = {i["n"]: i for i in (load_review(root, cid, n, text).get("steps") or [])}
    prev = load_run(root, cid, n, text)
    results: dict[str, dict] = dict(prev.get("steps") or {}) if only else {}
    todo = [s for s in steps if not only or s["n"] in only]
    print(f"chain {cid}, session {n}: {len(todo)} act(s) of {path(root, cid, n)}" + ("" if tty else " (no terminal: nothing is asked)"), file=out)
    stop, current = "", None

    def save() -> None:
        # after every act: a Ctrl-C or a crash later keeps what already ran (cross-review of 2026-10-05)
        _write_json(path(root, cid, n, RUN_FILE), {"sha": sha(text), "at": now(), "tty": tty, "steps": results})

    with open(path(root, cid, n, RUN_LOG), "a", encoding="utf-8") as log:
        log.write(f"\n=== run at {now()} (owner.md {sha(text)[:12]}){' only ' + ','.join(map(str, only)) if only else ''}\n")
        try:
            for s in todo:
                current = s
                closes = ", ".join(f"{u} {a}" for u, a in s["closes"]) or "nothing"
                print(f"\n── {s['n']}/{len(steps)} {s['title']}  (closes {closes})", file=out)
                if rev.get(s["n"]):
                    print(f"   {note_line(rev[s['n']])}", file=out)
                log.write(f"\n--- {s['n']}. {s['title']}\n")
                res = {"title": s["title"], "kind": s["kind"], "at": now()}
                res.update(_one_act(s, root, rev.get(s["n"]) or {}, stop, tty and not assume_yes, inp, out, log))
                if res["status"] in ("failed", "declined") and s["fields"].get("stop-on-fail", "").lower() in YES:
                    stop = f"act {s['n']} {res['status']} and says stop-on-fail"
                mark = {"passed": "✓", "confirmed": "✓", "unasked": "·", "later": "·"}.get(res["status"], "✗")
                print(f"   {mark} {res['status']}" + (f": {res['why']}" if res.get("why") and res["status"] != "unasked" else ""), file=out)
                log.write(f"--- {s['n']}: {res['status']} {res.get('why', '')}\n")
                results[str(s["n"])] = res
                save()
                current = None
        except KeyboardInterrupt:
            # at a prompt or in a command: the act in hand failed, the ones after are not run, what ran is kept
            if current is not None:
                results[str(current["n"])] = {"title": current["title"], "kind": current["kind"], "at": now(),
                                              "status": "failed", "why": "interrupted (Ctrl-C)"}
            save()
            print(f"\n   interrupted: the acts after {current['n'] if current else 'this one'} are not run; what ran is recorded", file=out)
            return 130
    plan = resume_plan(root, chain, n)
    print("\n" + "\n".join(plan_lines(plan)), file=out)
    print(f"\nNow type `/resume-chain ok` in Claude Code, in the chain's tab or a session of your own in {root}"
          + ("" if not plan["keep"] else "; the next session gets each failed act's output, so a note is needed only for what it cannot see")
          + f". Run one act again with `{RUN_CMD} --only <n>`.", file=out)
    return 0 if all(r["status"] in OK_STATUSES + ("later",) for r in results.values()) else 1


# ---------------------------------------------------------------- what `ok` closes

def resume_plan(root: Path, chain: dict, n: int) -> dict | None:
    """What `/resume-chain ok` closes for session n's wait: {close: ["u1 AC-2"], keep: [(line, why)], problem, run}.
    None when the session waited without owner.md (0.4.9: `ok` closes every line the wait names). A line closes when
    every act that names it passed or was confirmed; a failed, declined, skipped, unrun or `later` act keeps it open."""
    got = load(root, chain["id"], n)
    if got is None:
        return None
    text, steps = got
    import chain as chainlib
    plan = {"close": [], "keep": [], "problem": "", "run": []}
    pinned = chainlib.link(root, chain["id"], n).get("owner_sha")
    if pinned != sha(text):
        plan["problem"] = (f"{path(root, chain['id'], n)} changed after session {n} handed it over; `ok` cannot say which acts "
                           "passed. Name the lines you closed (`/resume-chain <unit>:AC-n … <note>`), or `skip`")
        return plan
    ran = (load_run(root, chain["id"], n, text).get("steps") or {})
    needs_run = [s for s in steps if s["kind"] == "command" or (s["kind"] == "manual" and s["fields"].get("check"))]
    if needs_run and not ran:
        plan["problem"] = (f"you have not run the acts yet: `{RUN_CMD}` in {root} runs them and records what passed "
                           f"({len(needs_run)} of {len(steps)} are commands or checks). Then `/resume-chain ok`. "
                           "Done by hand? Name the lines you closed (`/resume-chain <unit>:AC-n … <note>`)")
        return plan
    status = {s["n"]: (ran.get(str(s["n"])) or {}).get("status") or ("later" if s["kind"] == "later" else
                                                                     "not run" if s in needs_run else "unasked")
              for s in steps}
    opened = open_owner_lines(root)
    for line in waited_lines(steps):
        if line not in opened:
            continue
        holders = [s for s in steps if line in s["closes"]]
        bad = [s for s in holders if status[s["n"]] not in OK_STATUSES]
        if bad:
            plan["keep"].append((f"{line[0]} {line[1]}", "; ".join(f"act {s['n']} {status[s['n']]}" for s in bad)))
        else:
            plan["close"].append(f"{line[0]} {line[1]}")
    for s in steps:
        r = ran.get(str(s["n"])) or {}
        plan["run"].append({"n": s["n"], "title": s["title"], "status": status[s["n"]], "why": r.get("why", ""),
                            "exit": r.get("exit"), "tail": r.get("tail", "")[-600:] if status[s["n"]] == "failed" else ""})
    return plan


def plan_lines(plan: dict) -> list[str]:
    L = [f"`/resume-chain ok` closes: {', '.join(plan['close']) or 'nothing'}"]
    if plan["keep"]:
        L.append("and leaves open: " + "; ".join(f"{line} ({why})" for line, why in plan["keep"]))
    return L


def briefing_lines(run: list[dict]) -> list[str]:
    """The owner's run, for the session after the resume: each act's outcome, and the output of each one that failed."""
    if not run:
        return []
    L = ["## The owner's run of owner.md", "",
         "The owner ran the acts with `charter owner run`; `/resume-chain ok` closed the lines of the acts that passed. "
         "A failed act's output is below: diagnose it, fix what is yours, and put what is the owner's in your next owner.md.", ""]
    for r in run:
        L.append(f"- act {r['n']} ({r['title']}): {r['status']}" + (f", {r['why']}" if r.get("why") and r["status"] not in OK_STATUSES else ""))
        if r.get("tail"):
            L += ["", "  ```", *[f"  {x}" for x in r["tail"].strip().splitlines()[-25:]], "  ```", ""]
    return L + [""]
