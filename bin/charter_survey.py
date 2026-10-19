"""charter-pkg survey: measure a project before a charter migration.

Read-only on the project: every git call runs with GIT_OPTIONAL_LOCKS=0 and reads the main line through
`git cat-file`, never the index. The rehearsal clones the main line into a temporary directory, installs
the package there, commits as the owner and runs the gates; the clone is deleted afterwards unless
--keep-clone. Python 3 standard library only. The facts feed `charter_plan.render`, which writes the plan.
"""
from __future__ import annotations

import collections
import datetime as dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import lib
import checks

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
# The statuses the engines accept (VALID_STATUSES in tele-claude's services/project_tasket_reader.py).
ENGINE_STATUSES = ("now", "next", "later", "blocked", "done", "deleted", "superseded", "parked", "skipped", "realized", "deferred")
# Headings other tooling gives the acceptance checklist and the package does not read (it reads lib.ACCEPTANCE_HEADINGS).
OTHER_ACCEPTANCE = ("Definition of Done", "Success Criteria", "Exit Criteria", "Completion Criteria")
TEST_GLOBS = ("tests/**", "test/**", "spec/**", "*_test.go", "*_test.py", "test_*.py", "*.test.ts", "*.test.tsx",
              "*.test.js", "*.test.jsx", "*.spec.ts", "*.spec.tsx", "*.spec.js")
TOOLING_GLOBS = (".claude/skills/**", ".claude/commands/**", ".claude/agents/**", "_bmad/**", ".bmad-core/**")
VENDOR_GLOBS = ("vendor/**", "third_party/**", "third-party/**")
ARCHIVE_NAME_RE = re.compile(r"(?i)(progress|status|phase[-_ ]?\d|state[-_]of|next[-_]steps|completed|handoff|sprint[-_]|implementation[-_]plan|todo)")
DECISION_PATH_RE = re.compile(r"(?i)(^|/)(adrs?|decisions)/[^/]+\.md$|(^|/)[^/]*(adr[-_ ]?\d|decision)[^/]*\.md$")
CREDENTIALS = [
    ("stripe secret key", r"[sr]k_(test|live)_[A-Za-z0-9]{16,}"), ("stripe webhook secret", r"whsec_[A-Za-z0-9]{16,}"),
    ("hubspot token", r"pat-(na|eu)[0-9]-[A-Za-z0-9-]{20,}"), ("aws access key", r"AKIA[0-9A-Z]{16}"),
    ("github token", r"(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"), ("slack token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("google api key", r"AIza[0-9A-Za-z_-]{35}"), ("google oauth secret", r"GOCSPX-[A-Za-z0-9_-]{20,}"),
    ("anthropic key", r"sk-ant-[A-Za-z0-9_-]{20,}"), ("openai-style key", r"sk-(proj-)?[A-Za-z0-9]{32,}"),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), ("age secret key", r"AGE-SECRET-KEY-1[0-9A-Z]{50,}"),
    ("telegram bot token", r"[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}"),
]
# One-file change sets whose effect on each push-triggered workflow the survey reports.
CHANGESETS = {"ledger fold": ["charter/ledger.jsonl"], "legacy list edit": ["charter/legacy-taskets.txt"],
              "decision record": ["charter/decisions/example.md"], "tasket edit": [".taskets/example.md"]}


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None, inp: str | None = None, timeout: int = 120):
    try:
        return subprocess.run(cmd, cwd=cwd, env=env or ENV, input=inp, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return subprocess.CompletedProcess(cmd, 124, "", repr(e))


def g(root: Path, *args: str) -> str:
    return run(["git", "-C", str(root), *args]).stdout.strip()


def blobs(root: Path, ref: str, paths: list[str]) -> dict[str, bytes]:
    """Contents of `paths` at `ref`, through one `git cat-file --batch`; only blobs."""
    if not paths:
        return {}
    out = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"], input="".join(f"{ref}:{p}\n" for p in paths).encode(),
                         capture_output=True, env=ENV).stdout
    res, i = {}, 0
    for p in paths:
        nl = out.index(b"\n", i)
        head = out[i:nl].split()
        if len(head) < 3:   # "<name> missing"
            i = nl + 1
            continue
        size = int(head[2])
        if head[1] == b"blob":
            res[p] = out[nl + 1:nl + 1 + size]
        i = nl + 1 + size + 1
    return res


def tracked(root: Path, ref: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "-z", "--full-tree", ref], capture_output=True, env=ENV).stdout
    return [e.split(b"\t", 1)[1].decode("utf-8", "replace") for e in out.split(b"\0") if b"\t" in e and e.split()[1] == b"blob"]


def mainline(root: Path) -> str:
    head = g(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    names = ([head.split("/", 1)[1]] if "/" in head else []) + ["main", "master", "trunk"]
    for n in names:
        if run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"refs/heads/{n}"]).returncode == 0:
            return n
    return g(root, "rev-parse", "--abbrev-ref", "HEAD")


def text(b: bytes) -> str:
    return b.decode("utf-8", "replace")


# ---------------------------------------------------------------- sections

def s_checkout(root: Path, ref: str) -> dict:
    st = run(["git", "-C", str(root), "status", "--porcelain"]).stdout.splitlines()   # not stripped: column 1 may be a space
    ab = g(root, "rev-list", "--left-right", "--count", f"{ref}...HEAD").split()
    up = g(root, "rev-list", "--left-right", "--count", f"{ref}...origin/{ref}").split()
    panes = []
    if shutil.which("tmux"):
        for line in run(["tmux", "list-panes", "-a", "-F", "#{session_name}\t#{pane_current_path}\t#{pane_current_command}"]).stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and (parts[1] == str(root) or parts[1].startswith(str(root) + "/")):
                panes.append({"session": parts[0], "path": parts[1], "command": parts[2]})
    return {"branch": g(root, "rev-parse", "--abbrev-ref", "HEAD"), "head": g(root, "rev-parse", "--short=12", "HEAD"),
            "mainline": ref, "mainline_sha": g(root, "rev-parse", "--short=12", ref),
            "modified": [l[3:] for l in st if not l.startswith("??")], "untracked": [l[3:] for l in st if l.startswith("??")],
            "behind_mainline": int(ab[0]) if len(ab) == 2 else None, "ahead_of_mainline": int(ab[1]) if len(ab) == 2 else None,
            "mainline_vs_origin": {"ahead": int(up[0]), "behind": int(up[1])} if len(up) == 2 else None,
            "local_branches": len(g(root, "branch", "--format=%(refname:short)").splitlines()),
            "sessions": panes, "installed": text(blobs(root, ref, ["charter/VERSION"]).get("charter/VERSION", b"")).strip() or None}


def s_taskets(root: Path, ref: str, paths: list[str]) -> dict:
    tp = sorted(p for p in paths if p.startswith(".taskets/") and p.count("/") == 1 and p.endswith(".md"))
    content = blobs(root, ref, tp)
    by_status = collections.Counter()
    classes = collections.defaultdict(lambda: collections.Counter())
    items, ids = [], collections.Counter()
    for p in tp:
        t = text(content.get(p, b""))
        f, _, body = lib.split_frontmatter(t)
        st = str(f.get("status", ""))
        grp = "done" if st == "done" else "closed" if st in lib.TERMINAL_STATUSES else "open"   # an unknown status is open work
        acc = lib.section(body, "Acceptance")
        read = lib.acceptance(body)   # `## Acceptance`, else `## Done When`
        other = next((h for h in OTHER_ACCEPTANCE if lib.section(body, h)), None) if not read else None
        sect = read or (lib.section(body, other) if other else "")
        boxes = checks.CHECKBOX_RE.findall(sect)
        probes = checks.PROBE_RE.findall(sect)
        if acc:
            cls = "ready" if boxes and probes else "checklist" if boxes else "prose"
        elif read:
            cls = "done-when"   # the installer lists it as legacy; off the list it is read like `## Acceptance`
        else:
            cls = f"other:{other}" if other else "none"
        ev = checks.classify_anchors(root, lib.section(body, "Evidence") + "\n" + lib.section(body, "Log"))
        tid = str(f.get("id") or Path(p).stem)
        ids[tid] += 1
        by_status[st or "(empty)"] += 1
        classes[cls][grp] += 1
        items.append({"id": tid, "path": p, "status": st, "group": grp, "class": cls, "boxes": len(boxes),
                      "checked": sum(1 for b in boxes if b[0] != " "), "probes": len(probes),
                      "backtick_lines": sum(1 for l in sect.splitlines() if checks.CHECKBOX_RE.match(l) and "`" in l),
                      "evidence": bool(ev["sha"] or ev["run"]), "legacy": not lib.is_charter_unit(t),
                      "plan_group": str(f.get("group", "")), "no_id": "id" not in f, "inline_comments": lib.inline_comments(t),
                      "unknown_status": st not in ENGINE_STATUSES, "title": str(f.get("title", ""))[:100], "body": body})
    # taskets on disk but not tracked at `ref`: an ignored .taskets/ (or a file never `git add`-ed) is invisible to
    # every git-based read above, and so to the gates that read those reads (done, rails, synthesis) once installed
    d = root / ".taskets"
    on_disk = sorted(f".taskets/{p.name}" for p in d.glob("*.md")) if d.is_dir() else []
    untracked = [p for p in on_disk if p not in tp]
    ign = ignored_at(root, ref, paths, [".taskets/"]) if untracked else []
    return {"total": len(tp), "by_status": dict(by_status.most_common()), "classes": {k: dict(v) for k, v in sorted(classes.items())},
            "legacy_at_install": sum(1 for i in items if i["legacy"]), "duplicate_ids": sorted(k for k, n in ids.items() if n > 1),
            "untracked_on_disk": {"count": len(untracked),
                                  "ignored_by": {"source": ign[0]["source"], "pattern": ign[0]["pattern"]} if ign else None},
            "items": items}


def s_size(root: Path, ref: str, paths: list[str], cfg: dict) -> dict:
    content = blobs(root, ref, paths)
    lines = {}
    for p, b in content.items():
        if b"\0" in b[:8000]:
            continue
        lines[p] = b.count(b"\n") + (1 if b and not b.endswith(b"\n") else 0)
    present = lambda globs: [gl for gl in globs if any(lib.matches_any(p, [gl]) for p in paths)]
    groups = {"tests": present(TEST_GLOBS), "tooling": present(TOOLING_GLOBS), "vendor": present(VENDOR_GLOBS)}

    def frozen(extra: list[str]) -> list[dict]:
        c = dict(cfg, exempt_from_size=lib.as_list(cfg.get("exempt_from_size")) + extra)
        out = []
        for p, n in sorted(lines.items(), key=lambda x: -x[1]):
            if p.startswith(("charter/", ".charter/", ".claude/skills/charter-")):
                continue
            b = checks.size_budget_for(root, c, p)
            nb = len(content.get(p, b""))
            if b is not None and (n > b.lines or (b.bytes and nb > b.bytes)):
                out.append({"path": p, "lines": n, "limit": b.lines, "bytes": nb, "byte_limit": b.bytes})
        return out

    base = frozen([])
    variants = {"none": len(base)}
    for k, gl in groups.items():
        if gl:
            variants[k] = len(frozen(gl))
    every = [x for gl in groups.values() for x in gl]
    remaining = frozen(every)
    variants["all"] = len(remaining)
    for f in base:
        f["area"] = next((k for k, gl in groups.items() if gl and lib.matches_any(f["path"], gl)), "code or docs")
    gov = [{"path": p, "lines": lines.get(p, 0), "bytes": len(content.get(p, b"")), "limit": int(cfg["limits"]["governance_lines"]),
            "byte_limit": int(cfg["limits"].get("governance_bytes") or 0) or None}
           for p in paths if checks.is_governance(cfg, p) and (p == "charter/scope.md" or not p.startswith("charter/"))]
    nested = [{"path": p, "lines": lines.get(p, 0)} for p in paths if p.endswith("/CLAUDE.md") or p.endswith("/AGENTS.md")]
    return {"limits": cfg["limits"], "exempt_from_size": lib.as_list(cfg.get("exempt_from_size")), "exempt_groups": groups,
            "frozen": base, "variants": variants, "frozen_after_all_exempt": remaining, "governance": gov, "nested_governance": nested}


PATH_TOKEN = re.compile(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9]+")


def s_frozen_in_open_work(taskets: dict, size: dict, paths: list[str]) -> list[dict]:
    """Frozen files an open tasket names: by full path, by a path suffix of two segments or more, or by a basename
    no other tracked file shares."""
    base_count = collections.Counter(p.rsplit("/", 1)[-1] for p in paths)
    out = []
    for f in size["frozen"]:
        p = f["path"]
        name = p.rsplit("/", 1)[-1]
        hits = []
        for it in taskets["items"]:
            if it["group"] != "open":
                continue
            for tok in set(PATH_TOKEN.findall(it["body"])):
                tok = tok.lstrip("./")
                if tok == p or ("/" in tok and p.endswith("/" + tok)) or (tok == name and base_count[name] == 1):
                    hits.append(it["id"])
                    break
        if hits:
            out.append({"path": p, "lines": f["lines"], "taskets": hits})
    return out


RECENT_DAYS = 30
RECENT_MIN_COMMITS = 2   # one commit in the window is as likely an import or a rename as activity


def s_frozen_recently_changed(root: Path, ref: str, size: dict, days: int = RECENT_DAYS) -> list[dict]:
    """Frozen files that at least RECENT_MIN_COMMITS commits on `ref` changed in the last `days` days: the
    files work is happening in, whether or not an open tasket names them."""
    frozen = {f["path"] for f in size["frozen"]}
    # --since-as-filter, not --since: --since stops the walk at the first commit older than the window, so one
    # backdated commit would hide every recent commit behind it
    log = g(root, "log", ref, f"--since-as-filter={days}.days", "--format=", "--name-only")
    counts = collections.Counter(p for p in log.splitlines() if p in frozen)
    return [{"path": p, "commits": n} for p, n in sorted(counts.items()) if n >= RECENT_MIN_COMMITS]


def exceptions_needed(size: dict, open_work: list[dict], expires: str, recent: list[dict] = ()) -> list[dict]:
    """The `size_exceptions` entries that would let open work grow the frozen files it names, and recent work
    keep changing the frozen files it changes: each budget is the file's size now plus a quarter, a starting
    point for the owner, never a recommendation to keep."""
    by_path = {f["path"]: f for f in size["frozen"]}
    reasons: dict[str, list[str]] = {}
    for w in open_work:
        reasons.setdefault(w["path"], []).append(f"open work names it: {', '.join(w['taskets'][:3])}")
    for r in recent:
        reasons.setdefault(r["path"], []).append(f"changed in {r['commits']} commits in the last {RECENT_DAYS} days")
    out = []
    for path, why in reasons.items():
        f = by_path.get(path)
        if not f:
            continue
        e = {"path": f["path"], "lines": max(f["limit"], f["lines"] + f["lines"] // 4)}
        if f.get("byte_limit") and f.get("bytes", 0) > f["byte_limit"]:
            e["bytes"] = f["bytes"] + f["bytes"] // 4
        e.update({"because": "; ".join(why), "expires": expires})
        out.append(e)
    return out


def s_hooks(root: Path, ref: str, paths: list[str]) -> dict:
    """Hooks installed in the clone, and hook frameworks as `ref` configures them."""
    hp = lib.hooks_path(root)
    common = g(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    d = (root / hp) if hp else Path(common) / "hooks"
    found = []
    if d.is_dir():
        for p in sorted(d.iterdir()):
            if p.is_file() and not p.name.endswith(".sample") and os.access(p, os.X_OK):
                head = p.read_text(errors="replace")[:4000].lower()
                kind = next((k for k in ("lefthook", "husky", "pre-commit", "charter") if k in head), "script")
                found.append({"name": p.name, "kind": kind})
    frameworks = [f for f in lib.HOOK_FRAMEWORK_FILES if f in paths]
    content = blobs(root, ref, frameworks + (["package.json"] if "package.json" in paths else []))
    try:
        pj = json.loads(text(content.get("package.json", b"{}")))
    except json.JSONDecodeError:
        pj = {}
    others = [] if hp == lib.CHARTER_HOOKS_PATH else [lib.rel(root, d / x["name"]) for x in found]
    others += frameworks + [f"package.json ({k})" for k in ("husky", "simple-git-hooks") if isinstance(pj, dict) and k in pj]
    wired = next((f for f in frameworks if lib.CHARTER_HOOK_COMMAND in text(content.get(f, b""))), None)
    return {"hooks_path": hp or None, "hooks_dir": str(d), "installed": found, "other_hooks": others, "wired_by": wired}


def ignored_at(root: Path, ref: str, paths: list[str], candidates: list[str]) -> list[dict]:
    """Which candidates the `.gitignore` files at `ref` (and this clone's info/exclude) ignore: judged in a scratch
    repository holding only those files, so the project's working tree is neither read nor written."""
    tmp = Path(tempfile.mkdtemp(prefix="charter-ignore-"))
    try:
        run(["git", "init", "-q", str(tmp)])
        for p, b in blobs(root, ref, [p for p in paths if p == ".gitignore" or p.endswith("/.gitignore")]).items():
            (tmp / p).parent.mkdir(parents=True, exist_ok=True)
            (tmp / p).write_bytes(b)
        common = g(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        exclude = Path(common) / "info" / "exclude"
        if exclude.is_file():
            (tmp / ".git" / "info").mkdir(parents=True, exist_ok=True)
            (tmp / ".git" / "info" / "exclude").write_bytes(exclude.read_bytes())
        out = run(["git", "-C", str(tmp), "check-ignore", "-v", "--stdin"], inp="\n".join(c for c in candidates if c not in paths) + "\n").stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    res = []
    for line in out.splitlines():
        where, _, p = line.partition("\t")
        src, pattern = where.rsplit(":", 1) if ":" in where else (where, "")
        if pattern.startswith("!"):   # a negation pattern means NOT ignored, though check-ignore -v still prints it
            continue
        res.append({"path": p, "source": src, "pattern": pattern})
    return res


def s_claude_files(root: Path, ref: str, paths: list[str], install_paths: list[str]) -> dict:
    files = {}
    for p in (".claude/settings.json", ".claude/settings.local.json", "AGENTS.md", "CLAUDE.md", ".gitignore", ".mcp.json"):
        files[p] = {"tracked": p in paths, "exists": (root / p).exists()}
    sp = root / ".claude" / "settings.json"
    try:
        keys = sorted(json.loads(sp.read_text())) if sp.exists() else None
    except (json.JSONDecodeError, OSError):
        keys = ["(not JSON)"]
    ignored = ignored_at(root, ref, paths, install_paths)
    skills = sorted({p.split("/")[2] for p in paths if p.startswith(".claude/skills/") and p.count("/") >= 3})
    return {"files": files, "settings_keys": keys, "ignored_install_paths": ignored,
            "rules": [p for p in paths if p.startswith(".claude/rules/")], "agents": [p for p in paths if p.startswith(".claude/agents/")],
            "skills": skills}


def s_credentials(root: Path, ref: str) -> list[dict]:
    alt = "|".join(f"({r})" for _, r in CREDENTIALS)
    out = run(["git", "-C", str(root), "grep", "-nIE", "-o", "-e", alt, ref, "--"]).stdout
    found = []
    for line in out.splitlines():
        parts = line.split(":", 3)
        if len(parts) < 4:
            continue
        _, path, ln, val = parts
        kind = next((k for k, r in CREDENTIALS if re.fullmatch(r, val)), "credential")
        found.append({"path": path, "line": int(ln), "kind": kind, "prefix": val[:4], "length": len(val)})
    return found


def s_binaries(root: Path, ref: str) -> list[str]:
    out = g(root, "diff", "--numstat", EMPTY_TREE, ref)
    return [l.split("\t", 2)[2] for l in out.splitlines() if l.startswith("-\t-\t")]


def _yaml_list(lines: list[str], i: int, indent: int) -> tuple[list[str], int]:
    """Items of a block list under the key on line i, or the inline list on it."""
    val = lines[i].split(":", 1)[1].strip()
    if val:
        return [x.strip().strip("'\"") for x in val.strip("[]").split(",") if x.strip()], i + 1
    items, j = [], i + 1
    while j < len(lines):
        s = lines[j]
        if s.strip() and not s.strip().startswith("#"):
            ind = len(s) - len(s.lstrip())
            if ind <= indent:
                break
            if s.strip().startswith("- "):
                items.append(s.strip()[2:].split(" #")[0].strip().strip("'\""))
        j += 1
    return items, j


def parse_triggers(src: str) -> dict:
    """`on:` of a GitHub workflow, read from the text: events, and for push and pull_request their branches,
    paths and paths-ignore. Enough for the survey; not a YAML parser."""
    lines = src.splitlines()
    ev: dict = {}
    for i, l in enumerate(lines):
        m = re.match(r"^['\"]?(on|true)['\"]?:\s*(.*)$", l)
        if not m:
            continue
        if m.group(2).strip():
            for e in m.group(2).strip("[] ").split(","):
                if e.strip():
                    ev[e.strip()] = {}
            return ev
        j, cur, cur_ind = i + 1, None, None
        while j < len(lines):
            s = lines[j]
            if s.strip() and not s.strip().startswith("#"):
                ind = len(s) - len(s.lstrip())
                if ind == 0:
                    break
                key = s.strip().split(":", 1)[0].strip("'\"")
                if cur_ind is None or ind <= cur_ind:
                    cur, cur_ind = key, ind
                    ev[cur] = {}
                elif key in ("branches", "paths", "paths-ignore", "branches-ignore") and cur:
                    ev[cur][key], j = _yaml_list(lines, j, ind)
                    continue
            j += 1
        return ev
    return ev


def gh_glob(pattern: str) -> re.Pattern:
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            # zero or more directories: GitHub's `**/README.md` matches a root README.md
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def triggers(push: dict, changed: list[str]) -> bool:
    """Would a push changing these files start the workflow (GitHub's paths / paths-ignore rules)?"""
    if "paths" in push:
        return any(gh_glob(p).match(f) for f in changed for p in push["paths"] if not p.startswith("!"))
    if "paths-ignore" in push:
        return not all(any(gh_glob(p).match(f) for p in push["paths-ignore"]) for f in changed)
    return True


def s_ci(root: Path, ref: str, paths: list[str], install_paths: list[str], target: str) -> dict:
    """Workflows as they are at `ref`, judged for a push to `target`, the main line the work merges into."""
    wf = [p for p in paths if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml"))]
    content = blobs(root, ref, wf)
    out = []
    for p in wf:
        src = text(content.get(p, b""))
        ev = parse_triggers(src)
        push = ev.get("push")
        on_main = push is not None and (not push.get("branches") or any(fnmatch.fnmatch(target, b) for b in push.get("branches", [])))
        coe = [i + 1 for i, l in enumerate(src.splitlines()) if re.match(r"^\s*continue-on-error:\s*true", l)]
        deploys = "deploy" in p.lower() or bool(re.search(r"(?m)^\s*(run|uses):.*\b(dokku|deploy|ssh|rsync|kubectl|flyctl)\b", src))
        row = {"path": p, "events": sorted(ev), "push_branches": (push or {}).get("branches"), "paths": (push or {}).get("paths"),
               "paths_ignore": (push or {}).get("paths-ignore"), "push_on_mainline": on_main, "continue_on_error_lines": coe,
               "deploys": deploys}
        if on_main:
            row["install_triggers"] = triggers(push, install_paths)
            row["install_paths_not_ignored"] = [f for f in install_paths if "paths-ignore" in push and
                                                not any(gh_glob(x).match(f) for x in push["paths-ignore"])]
            row["changesets"] = {k: triggers(push, v) for k, v in CHANGESETS.items()}
        out.append(row)
    other = [p for p in (".gitlab-ci.yml", ".circleci/config.yml", "Jenkinsfile", ".drone.yml", "bitbucket-pipelines.yml") if p in paths]
    return {"workflows": out, "other_ci": other}


def s_remote(root: Path, offline: bool) -> dict:
    url = g(root, "remote", "get-url", "origin")
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(\.git)?$", url)
    res = {"origin": url or None, "github": f"{m.group(1)}/{m.group(2)}" if m else None, "visibility": None}
    if m and not offline and shutil.which("gh"):
        r = run(["gh", "repo", "view", res["github"], "--json", "visibility"], timeout=20)
        try:
            res["visibility"] = json.loads(r.stdout).get("visibility")
        except json.JSONDecodeError:
            res["visibility"] = None
    return res


def s_history(root: Path, ref: str) -> dict:
    authors = collections.Counter(g(root, "log", "--since=90.days", "--format=%an", ref).splitlines())
    fp = g(root, "log", "--first-parent", "-n", "50", "--format=%P%x09%s", ref).splitlines()
    merges = sum(1 for l in fp if len(l.split("\t")[0].split()) > 1)
    squashed = sum(1 for l in fp if len(l.split("\t")[0].split()) == 1 and re.search(r"\(#\d+\)\s*$", l))
    return {"authors_90d": dict(authors.most_common()), "first_parent_50": {"merge": merges, "squash": squashed, "direct": len(fp) - merges - squashed}}


def s_markdown(root: Path, ref: str, paths: list[str]) -> dict:
    md = [p for p in paths if p.endswith(".md") and ("/" not in p or p.startswith("docs/"))]
    last: dict[str, str] = {}
    date = None
    for line in g(root, "log", "--format=@%cs", "--name-only", ref, "--", *md).splitlines() if md else []:
        if line.startswith("@"):
            date = line[1:]
        elif line.strip() and line not in last:
            last[line] = date
    content = blobs(root, ref, md)
    today = dt.date.today()
    rows = []
    for p in md:
        d = last.get(p)
        age = (today - dt.date.fromisoformat(d)).days if d else None
        cand = bool(ARCHIVE_NAME_RE.search(p.rsplit("/", 1)[-1]))
        # a name is only a hint: a candidate that code, CI or other docs cite is probably a guide, not a progress file
        refs = [x.split(":", 1)[1] for x in g(root, "grep", "-l", "-F", p.rsplit("/", 1)[-1], ref, "--", ".", f":!{p}", ":!.taskets").splitlines()] if cand else []
        rows.append({"path": p, "lines": content.get(p, b"").count(b"\n"), "last_commit": d, "age_days": age,
                     "archive_candidate": cand, "cited_by": refs})
    return {"root": [r for r in rows if "/" not in r["path"]], "docs": [r for r in rows if "/" in r["path"]]}


def s_decisions(root: Path, ref: str, paths: list[str]) -> dict:
    recs = [p for p in paths if DECISION_PATH_RE.search(p) and not p.startswith((".claude/", "_bmad/", "charter/templates/", ".taskets/"))]
    content = blobs(root, ref, recs + (["CLAUDE.md"] if "CLAUDE.md" in paths else []))
    rows = []
    for p in recs:
        t = text(content.get(p, b""))
        f, _, body = lib.split_frontmatter(t)
        h1 = next((l[2:].strip() for l in body.splitlines() if l.startswith("# ")), "")
        m = re.search(r"(?im)^\W*status\W*:?\W*([A-Za-z-]+)", body)
        rows.append({"path": p, "title": h1[:90], "status": str(f.get("status") or (m.group(1) if m else ""))})
    sections = []
    for i, l in enumerate(text(content.get("CLAUDE.md", b"")).splitlines(), 1):
        if l.startswith("## "):
            if sections:
                sections[-1]["end"] = i - 1
            sections.append({"heading": l[3:].strip(), "start": i, "end": i})
    if sections:
        sections[-1]["end"] = text(content.get("CLAUDE.md", b"")).count("\n")
    return {"records": rows, "claude_md_sections": sections,
            "bmad": {"tracked": sum(1 for p in paths if p.startswith("_bmad/")),
                     "sprint_status": [p for p in paths if p.endswith("sprint-status.yaml") and not p.startswith(".claude/")],
                     "stories": sum(1 for p in paths if "/stories/" in p and p.endswith(".md") and not p.startswith(".claude/"))}}


def s_tests(root: Path, ref: str, paths: list[str]) -> list[str]:
    cands = []
    mk = text(blobs(root, ref, ["Makefile"]).get("Makefile", b"")) if "Makefile" in paths else ""
    cands += [f"make {t}" for t in re.findall(r"(?m)^(test[\w-]*|check):", mk)]
    if "package.json" in paths:
        try:
            if "test" in json.loads(text(blobs(root, ref, ["package.json"])["package.json"])).get("scripts", {}):
                cands.append("npm test")
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
    if any(p in paths for p in ("pytest.ini", "pyproject.toml", "setup.cfg")) or any(p.startswith("tests/") and p.endswith(".py") for p in paths):
        cands.append("python3 -m pytest -q")
    if "go.mod" in paths:
        cands.append("go test ./...")
    return cands


# ---------------------------------------------------------------- rehearsal

def rehearse(root: Path, ref: str, installer: Path, track: str, test_cmd: str | None, keep: bool, add: list[str]) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="charter-survey-"))
    clone = tmp / "clone"
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CHARTER_OWNER", "CHARTER_UNIT")}
    res: dict = {"track": track, "clone": str(clone) if keep else None}
    try:
        r = run(["git", "clone", "-q", "--no-hardlinks", "--branch", ref, str(root), str(clone)], env=env, timeout=600)
        if r.returncode != 0:
            res["error"] = f"clone failed: {r.stderr.strip()[:200]}"
            return res
        for k, v in (("user.name", g(root, "config", "user.name") or "charter survey"), ("user.email", g(root, "config", "user.email") or "survey@example.invalid")):
            run(["git", "-C", str(clone), "config", k, v], env=env)
        r = run([sys.executable, "-B", str(installer), "install", str(clone), "--track", track, "--replace-hooks"], env=env)
        res["install_exit"] = r.returncode
        res["install_ignored"] = [l.rsplit(": ", 1)[-1] for l in r.stdout.splitlines() if l.startswith("IGNORED by")]
        legacy = (clone / "charter" / "legacy-taskets.txt")
        res["legacy"] = sum(1 for l in legacy.read_text().splitlines() if l.strip() and not l.startswith("#")) if legacy.exists() else 0
        run(["git", "-C", str(clone), "add", "--", *add], env=env)   # by name, as the plan says; `git add -A` would sweep up drift
        res["committed_files"] = len(run(["git", "-C", str(clone), "diff", "--cached", "--name-only"], env=env).stdout.split())
        res["left_unstaged"] = [l[3:] for l in run(["git", "-C", str(clone), "status", "--porcelain"], env=env).stdout.splitlines()
                                if l[1:2] != " "]   # "A  x" is staged; "?? x" and " M x" are not
        r = run(["git", "-C", str(clone), "commit", "-q", "-m", "charter install (survey rehearsal)"], env=dict(env, CHARTER_OWNER="1"), timeout=300)
        res["commit_exit"] = r.returncode
        res["commit_summary"] = next((l for l in (r.stdout + r.stderr).splitlines() if l.startswith("charter check:")), "")
        cli = [sys.executable, "-B", str(clone / ".charter" / "bin" / "charter"), "--root", str(clone)]
        r = run(cli + ["check", "--all"], env=env, timeout=600)
        res["check_all"] = {"exit": r.returncode, "summary": next((l for l in r.stdout.splitlines() if l.startswith("charter check:")), ""),
                            "findings": [l for l in r.stdout.splitlines() if l.startswith("charter/")][:20]}
        r = run(cli + ["check", "--all", "--strict", "--size"], env=env, timeout=600)
        res["strict_size_blocks"] = sum(1 for l in r.stdout.splitlines() if l.startswith("charter/size block"))
        r = run(cli + ["synth"], env=env, timeout=600)
        res["synth"] = {"exit": r.returncode, "lines": len(r.stdout.splitlines()), "error": r.stderr.strip().splitlines()[:4]}
        if test_cmd:
            t0 = time.time()
            r = run(["/bin/sh", "-c", test_cmd], cwd=clone, env=env, timeout=3600)
            res["tests"] = {"command": test_cmd, "exit": r.returncode, "seconds": round(time.time() - t0),
                            "tail": (r.stdout + r.stderr).strip().splitlines()[-3:]}
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)
    return res


# ---------------------------------------------------------------- entry

def install_paths(pkg) -> list[str]:
    """What the installer writes into a project, relative to its root."""
    return list(pkg.OWNED) + list(pkg.SEEDED) + [pkg.LEGACY, "charter/VERSION", ".charter/manifest.json", ".claude/settings.json",
                                                "AGENTS.md", ".gitignore", "charter/decisions/.gitkeep", "charter/changes/.gitkeep"]


def add_paths(pkg, fresh_taskets: bool, settings_ignored: bool) -> list[str]:
    """The pathspecs that stage an install and nothing else, derived from the installer's own lists."""
    out = sorted({p.split("/")[0] if p.startswith((".charter/", "charter/")) else p for p in pkg.OWNED})
    out += ["AGENTS.md", ".gitignore"] + ([] if settings_ignored else [".claude/settings.json"])
    return out + ([".taskets/.gitkeep"] if fresh_taskets else [])


def survey(root: Path, pkg, track: str = "prototype", test_cmd: str | None = None, rehearsal: bool = True,
           offline: bool = False, keep_clone: bool = False, ref: str | None = None) -> dict:
    ref = ref or mainline(root)
    paths = tracked(root, ref)
    installed = bool(blobs(root, ref, ["charter/VERSION"]))
    cfg = lib.config_from(json.loads(text(blobs(root, ref, ["charter/config.json"]).get("charter/config.json", b"{}")) or "{}")) \
        if installed else lib.load_config(pkg.PKG)   # the config at `ref`, not the checkout's
    ip = install_paths(pkg)
    t = s_taskets(root, ref, paths)
    sz = s_size(root, ref, paths, cfg)
    res = {"survey": 1, "package_version": pkg.VERSION, "project": str(root), "name": root.name, "date": dt.date.today().isoformat(),
           "checkout": s_checkout(root, ref), "taskets": t, "size": sz, "frozen_in_open_work": s_frozen_in_open_work(t, sz, paths),
           "hooks": s_hooks(root, ref, paths), "claude": s_claude_files(root, ref, paths, ip), "credentials": s_credentials(root, ref),
           "binaries": s_binaries(root, ref), "ci": s_ci(root, ref, paths, ip, mainline(root)), "remote": s_remote(root, offline),
           "history": s_history(root, ref), "markdown": s_markdown(root, ref, paths), "decisions": s_decisions(root, ref, paths),
           "test_candidates": s_tests(root, ref, paths), "tracked_files": len(paths)}
    res["frozen_recently_changed"] = s_frozen_recently_changed(root, ref, sz)
    res["exceptions_needed"] = exceptions_needed(sz, res["frozen_in_open_work"], (dt.date.today() + dt.timedelta(days=90)).isoformat(),
                                                 res["frozen_recently_changed"])
    fresh = not any(p.startswith(".taskets/") for p in paths)
    res["add_paths"] = add_paths(pkg, fresh, any(x["path"] == ".claude/settings.json" for x in res["claude"]["ignored_install_paths"]))
    res["rehearsal"] = rehearse(root, ref, Path(pkg.__file__).resolve(), track, test_cmd, keep_clone, res["add_paths"]) if rehearsal else None
    for it in t["items"]:
        it.pop("body", None)
    return res
