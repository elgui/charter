"""Render a survey (charter_survey.survey) as a report and as a migration plan, both in markdown.

Every claim line carries the command or file it was read from, so `charter anchors` passes on both;
`check()` runs that check in-process, read-only. The plan is generated from the facts: each step names
the fact it rests on, its check and its rollback. Judgement the facts cannot settle is listed as an
owner decision, never decided here.
"""
from __future__ import annotations

import json

import checks

CLASS_TEXT = {
    "none": "no acceptance section: listed as legacy at install, closes with a warning",
    "ready": "checklist with probes: ready",
    "checklist": "checklist without probes: gated, closes once every box is checked and evidence cites a run",
    "prose": "acceptance as prose: gated, and a done flip is refused until it is a checklist",
}


def cls_text(c: str) -> str:
    if c == "done-when":
        return ("checklist under `## Done When`: listed as legacy at install, so it closes with a warning; "
                "off the list, the gates read it as `## Acceptance`")
    if c.startswith("other:"):
        return (f"checklist under `## {c[6:]}`, which the gates do not read: listed as legacy at install; "
                "one created after the install cannot close")
    return CLASS_TEXT.get(c, c)


def src(cmd: str) -> str:
    return f"`$ {cmd}`"


def row(*cells) -> str:
    return "| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |"


def lst(xs, n=6) -> str:
    xs = list(xs)
    return ", ".join(str(x) for x in xs[:n]) + (f" and {len(xs) - n} more" if len(xs) > n else "") if xs else "none"


# ---------------------------------------------------------------- report

def report(s: dict) -> str:
    c, t, sz, h, cl, ci = s["checkout"], s["taskets"], s["size"], s["hooks"], s["claude"], s["ci"]
    ref = c["mainline"]
    L = [f"# Charter survey: {s['name']}", "",
         f"Read-only survey of `{s['project']}` on the main line `{ref}` at {c['mainline_sha']} ({src('git rev-parse --short=12 ' + ref)}), "
         f"charter package {s['package_version']}, {s['date']}. Regenerate with `charter-pkg survey`; do not edit.", ""]

    L += ["## Checkout", "", row("Fact", "Value", "Source"), row("---", "---", "---")]
    L.append(row("Checked out", f"{c['branch']} at {c['head']}; {c['ahead_of_mainline']} ahead of and {c['behind_mainline']} behind {ref}",
                 src(f"git rev-list --left-right --count {ref}...HEAD")))
    up = c["mainline_vs_origin"]
    L.append(row(f"{ref} against origin/{ref}", f"{up['ahead']} ahead, {up['behind']} behind" if up else "no origin branch",
                 src(f"git rev-list --left-right --count {ref}...origin/{ref}")))
    L.append(row("Uncommitted changes", f"{len(c['modified'])} modified ({lst(c['modified'], 4)}), {len(c['untracked'])} untracked ({lst(c['untracked'], 4)})",
                 src("git status --porcelain")))
    L.append(row("Sessions working in the tree", lst(f"{p['session']} ({p['command']})" for p in c["sessions"]),
                 src("tmux list-panes -a -F '#{session_name} #{pane_current_path}'")))
    L.append(row("Tracked files", s["tracked_files"], src(f"git ls-tree -r {ref}")))
    L.append(row("Charter installed", c["installed"] or "no", src(f"git show {ref}:charter/VERSION")))
    L.append("")

    L += ["## Taskets", "", row("Class", "Open", "Done", "Closed", "What it means", "Source"), row("---", "---:", "---:", "---:", "---", "---")]
    for k, v in t["classes"].items():
        L.append(row(k, v.get("open", 0), v.get("done", 0), v.get("closed", 0), cls_text(k), src(f"git show {ref}:.taskets/<id>.md")))
    L.append("")
    items = t["items"]
    uod = t["untracked_on_disk"]
    L += [row("Fact", "Value", "Source"), row("---", "---", "---"),
          row("Taskets by status", lst(f"{k} {v}" for k, v in t["by_status"].items()), src(f"git ls-tree -r --name-only {ref} .taskets")),
          row("Untracked on disk, not tracked at " + ref, f"{uod['count']}" +
              (f"; ignored by {uod['ignored_by']['source']} (`{uod['ignored_by']['pattern']}`)" if uod["ignored_by"] else ""),
              src("ls .taskets/*.md")),
          row("Listed as legacy by the installer", t["legacy_at_install"], src(f"charter-pkg install <clone> --dry-run")),
          row("Status outside the engines' vocabulary", lst(f"{i['path']} ({i['status'] or 'empty'})" for i in items if i["unknown_status"]),
              "~/Projects/tele-claude/services/project_tasket_reader.py"),
          row("Frontmatter comment on the value line", lst(f"{i['path']} ({', '.join(i['inline_comments'])})" for i in items if i["inline_comments"]),
              src(f"git show {ref}:.taskets/<id>.md")),
          row("No `id:` key", sum(1 for i in items if i["no_id"]), src(f"git show {ref}:.taskets/<id>.md")),
          row("Duplicate ids", lst(t["duplicate_ids"]), src(f"git show {ref}:.taskets/<id>.md"))]
    for c_ in sorted({i["class"] for i in items if i["class"] == "done-when" or i["class"].startswith("other:")}):
        head = "Done When" if c_ == "done-when" else c_[6:]
        dn = [i for i in items if i["class"] == c_ and i["group"] == "done" and i["boxes"]]
        op = [i for i in items if i["class"] == c_ and i["group"] == "open"]
        L.append(row(f"Done taskets with a checklist under `## {head}`",
                     f"{len(dn)}; every box checked in {sum(1 for i in dn if i['checked'] == i['boxes'])}; "
                     f"evidence citing a commit or a run in {sum(1 for i in dn if i['evidence'])}", src(f"git show {ref}:.taskets/<id>.md")))
        L.append(row(f"Open taskets with a checklist under `## {head}`",
                     f"{len(op)}; {sum(i['boxes'] for i in op)} checklist lines, {sum(i['backtick_lines'] for i in op)} of them with a command in backticks",
                     src(f"git show {ref}:.taskets/<id>.md")))
    L.append("")

    gb = sz['limits'].get('governance_bytes')
    L += ["## Size", "", f"Limits: {sz['limits']['file_lines']} lines for a file, {sz['limits']['governance_lines']} for governance"
          + (f" and {gb} bytes" if gb else "") +
          f" ({src('cat package/charter/config.json')}). A file over its limit is frozen for growth from the install.", "",
          row("Frozen file", "Lines", "Limit", "Area", "Source"), row("---", "---:", "---:", "---", "---")]
    for f in sz["frozen"]:
        L.append(row(f["path"], f["lines"], f["limit"], f["area"], src(f"git show {ref}:{f['path']}")))
    if not sz["frozen"]:
        L.append(row("none", 0, "", "", src(f"git ls-tree -r {ref}")))
    L += ["", row("Also exempt from size", "Frozen", "Globs", "Source"), row("---", "---:", "---", "---")]
    for k, n in sz["variants"].items():
        globs = sz["exempt_groups"].get(k) if k in sz["exempt_groups"] else (["every glob above"] if k == "all" else [])
        L.append(row(k, n, lst(globs, 8) if globs else "package defaults only", src(f"git ls-tree -r {ref}")))
    L += ["", row("Governance file", "Lines", "Bytes", "Limit", "Byte limit", "Source"), row("---", "---:", "---:", "---:", "---:", "---")]
    for f in sz["governance"]:
        L.append(row(f["path"], f["lines"], f["bytes"], f["limit"], f.get("byte_limit") or "", src(f"git show {ref}:{f['path']}")))
    for f in sz["nested_governance"]:
        L.append(row(f["path"] + " (nested, not gated)", f["lines"], "", "", "", src(f"git show {ref}:{f['path']}")))
    L += ["", "Frozen files an open tasket names:", ""]
    L += [f"- {f['path']} ({f['lines']} lines): {lst(f['taskets'])} ({src('git grep -n ' + f['path'].rsplit('/', 1)[-1] + ' ' + ref + ' -- .taskets')})"
          for f in s["frozen_in_open_work"]] or [f"- none ({src('git grep -n <frozen path> ' + ref + ' -- .taskets')})"]
    L.append("")
    rc = s.get("frozen_recently_changed") or []
    L += ["Frozen files recent commits change:", ""]
    L += [f"- {f['path']}: {f['commits']} commits in 30 days ({src('git log --since=30.days --name-only ' + ref)})" for f in rc] \
        or [f"- none ({src('git log --since=30.days --name-only ' + ref)})"]
    L.append("")
    ex = s.get("exceptions_needed") or []
    if ex:
        L += [f"Named exceptions that would let that work grow those files, budgets at their size now plus a quarter, expiring {ex[0]['expires']}, "
              f"a starting point for the owner's `size_exceptions` ({src('git grep -n <frozen path> ' + ref + ' -- .taskets')}):", "", "```json",
              *[json.dumps(e) + ("," if i < len(ex) - 1 else "") for i, e in enumerate(ex)], "```", ""]

    L += ["## Git hooks", "", row("Fact", "Value", "Source"), row("---", "---", "---"),
          row("core.hooksPath", h["hooks_path"] or "unset", src("git config --get core.hooksPath")),
          row("Hooks installed in this clone", lst(f"{x['name']} ({x['kind']})" for x in h["installed"]), src("ls " + h["hooks_dir"])),
          row("Hooks the charter hook path would stop", lst(h["other_hooks"]), src("ls " + h["hooks_dir"])),
          row("Framework file already running the charter gate", h["wired_by"] or "none", src("git grep -n 'charter check --staged'")), ""]

    L += ["## Claude Code and agent files", "", row("File", "Tracked", "In the checkout", "Source"), row("---", "---", "---", "---")]
    for p, v in cl["files"].items():
        L.append(row(p, "yes" if v["tracked"] else "no", "yes" if v["exists"] else "no", src(f"git ls-files {p}")))
    L += ["", row("Fact", "Value", "Source"), row("---", "---", "---"),
          row("Keys in .claude/settings.json (values not read)", lst(cl["settings_keys"]) if cl["settings_keys"] is not None else "no file",
              src("python3 -c 'print(list(json.load(open(\".claude/settings.json\"))))'")),
          row("Installer paths .gitignore keeps out of a commit", lst(f"{x['path']} ({x['source']}, `{x['pattern']}`)" for x in cl["ignored_install_paths"]),
              src("git check-ignore -v --stdin")),
          row("Project skills", f"{len(cl['skills'])}: {lst(cl['skills'], 5)}", src(f"git ls-tree -r --name-only {ref} .claude/skills")),
          row("Rules and agents", f"{len(cl['rules'])} rule file(s), {len(cl['agents'])} agent file(s)", src(f"git ls-tree -r --name-only {ref} .claude")), ""]

    L += ["## CI", "", row("Workflow", "Push to main line", "Deploys", "Install commit starts it", "One-file charter commits that start it", "continue-on-error", "Source"),
          row("---", "---", "---", "---", "---", "---", "---")]
    for w in ci["workflows"]:
        starts = lst(k for k, v in (w.get("changesets") or {}).items() if v) if w["push_on_mainline"] else "n/a"
        L.append(row(w["path"], "yes" if w["push_on_mainline"] else "no", "yes" if w["deploys"] else "no",
                     ("yes" if w.get("install_triggers") else "no") if w["push_on_mainline"] else "n/a", starts,
                     lst(f"line {n}" for n in w["continue_on_error_lines"]), src(f"git show {ref}:{w['path']}")))
    for w in ci["workflows"]:
        if w.get("install_paths_not_ignored") and w["deploys"]:
            L.append("")
            L.append(f"- {w['path']} ignores {lst(w['paths_ignore'], 10)}; the install commit adds paths outside that list, "
                     f"such as {lst(w['install_paths_not_ignored'], 5)} ({src('git show ' + ref + ':' + w['path'])})")
    if ci["other_ci"]:
        L.append(f"- Other CI configuration: {lst(ci['other_ci'])} ({src('git ls-files')})")
    L.append("")

    r_, hi = s["remote"], s["history"]
    L += ["## Remote and history", "", row("Fact", "Value", "Source"), row("---", "---", "---"),
          row("origin", r_["origin"] or "none", src("git remote get-url origin")),
          row("GitHub visibility", r_["visibility"] or "not read", src(f"gh repo view {r_['github']} --json visibility") if r_["github"] else src("git remote -v")),
          row("Authors on the main line, last 90 days", lst(f"{k} ({v})" for k, v in hi["authors_90d"].items()), src(f"git log --since=90.days --format=%an {ref}")),
          row("Last 50 first-parent commits", f"{hi['first_parent_50']['merge']} merge commits, {hi['first_parent_50']['squash']} squash merges, "
              f"{hi['first_parent_50']['direct']} direct", src(f"git log --first-parent -n 50 --format=%P {ref}")),
          row("Credential-shaped literals (prefix and length only)", lst(f"{x['path']}:{x['line']} {x['kind']}, {x['prefix']}…, {x['length']} chars" for x in s["credentials"]),
              src(f"git grep -nIE -o <patterns> {ref}")),
          row("Binary files tracked", f"{len(s['binaries'])}: {lst(s['binaries'], 4)}", src(f"git diff --numstat <empty tree> {ref}")),
          row("Test commands found", lst(f"`{x}`" for x in s["test_candidates"]), src(f"git show {ref}:Makefile")), ""]

    md, dec = s["markdown"], s["decisions"]
    L += ["## Documents", "", row("Root markdown", "Lines", "Last commit", "Archive candidate", "Source"), row("---", "---:", "---", "---", "---")]
    for m in md["root"]:
        L.append(row(m["path"], m["lines"], m["last_commit"], "yes" if m["archive_candidate"] else "no", src(f"git log -1 --format=%cs {ref} -- {m['path']}")))
    cand = [m for m in md["docs"] if m["archive_candidate"]]
    old = sorted((m for m in md["docs"] if (m["age_days"] or 0) > 90), key=lambda m: -(m["age_days"] or 0))
    L += ["", f"- docs/: {len(md['docs'])} markdown files; names suggesting progress or status: "
          f"{lst(m['path'] + ' (cited outside .taskets by ' + (lst(m['cited_by'], 3) if m['cited_by'] else 'nothing') + ')' for m in cand)} "
          f"({src('git grep -l <name> ' + ref + ' -- . :!.taskets')})",
          f"- docs/ files untouched for more than 90 days: {len(old)}, oldest {lst(m['path'] + ' ' + str(m['last_commit']) for m in old[:5])} "
          f"({src('git log --format=%cs --name-only ' + ref + ' -- docs')})", "",
          row("Decision record", "Status", "Title", "Source"), row("---", "---", "---", "---")]
    for d in dec["records"]:
        L.append(row(d["path"], d["status"] or "not stated", d["title"], src(f"git show {ref}:{d['path']}")))
    if not dec["records"]:
        L.append(row("none", "", "", src(f"git ls-tree -r --name-only {ref}")))
    L += ["", f"`CLAUDE.md` sections, read for decisions buried in prose ({src('git show ' + ref + ':CLAUDE.md')}):", ""]
    L += [f"- CLAUDE.md:{x['start']}-{x['end']} {x['heading']}" for x in dec["claude_md_sections"]] or ["- no CLAUDE.md"]
    b = dec["bmad"]
    L += ["", f"- BMAD: {b['tracked']} tracked files under `_bmad/`, sprint status files {lst(b['sprint_status'])}, "
          f"{b['stories']} story files ({src('git ls-tree -r --name-only ' + ref + ' _bmad')})", ""]

    rh = s.get("rehearsal")
    L += ["## Rehearsal", ""]
    if not rh:
        L.append("- skipped (--no-rehearse)")
    elif rh.get("error"):
        L.append(f"- {rh['error']} (in the clone)")
    else:
        L += [f"- Install with track {rh['track']}: exit {rh['install_exit']}, {rh['legacy']} legacy taskets, {rh['committed_files']} files staged by name; "
              f"left unstaged: {lst(rh['left_unstaged'])}; ignored and so not committed: {lst(rh['install_ignored'])} (in the clone)",
              f"- Owner commit through the pre-commit gate: exit {rh['commit_exit']}, {rh['commit_summary'] or 'no gate summary'} (in the clone)",
              f"- `charter check --all`: exit {rh['check_all']['exit']}, {rh['check_all']['summary']} (in the clone)"]
        L += [f"  - {f} (in the clone)" for f in rh["check_all"]["findings"] if " block " in f]
        L += [
              f"- `charter check --all --strict --size`: {rh['strict_size_blocks']} frozen (in the clone)",
              f"- `charter synth`: exit {rh['synth']['exit']}, {rh['synth']['lines']} lines" +
              (f"; {' / '.join(rh['synth']['error'])}" if rh["synth"]["exit"] else "") + " (in the clone)"]
        if rh.get("tests"):
            tt = rh["tests"]
            L.append(f"- `{tt['command']}` with no untracked files: exit {tt['exit']} in {tt['seconds']} s; {' / '.join(tt['tail'])} (in the clone)")
        if rh.get("clone"):
            L.append(f"- Clone kept at {rh['clone']} (in the clone)")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- plan

OPINION, END = "<!-- charter: opinion -->", "<!-- charter: /opinion -->"
TOOL = "python3 ~/Projects/methodo/bin/charter-pkg"
CLI = "python3 .charter/bin/charter"


def decisions(s: dict) -> list[dict]:
    """Owner decisions the facts raise: each with the measured fact, its source, the options and a default."""
    c, t, sz, h, cl, ci, ref = s["checkout"], s["taskets"], s["size"], s["hooks"], s["claude"], s["ci"], s["checkout"]["mainline"]
    out = []
    rh = s.get("rehearsal") or {}
    out.append({"id": "track", "q": "Which track does the project run?",
                "fact": f"no `charter/scope.md` on {ref}; the survey cannot see a signed devis or contract ({src('git show ' + ref + ':charter/scope.md')})",
                "options": ["client: `charter/scope.md` written from the signed devis or contract, never from a proposal, with no prices or rates",
                            "prototype: no scope gate; the perimeter and anchor gates warn"],
                "default": "client if a signed document exists, else prototype"})
    uod = t["untracked_on_disk"]
    if uod["count"]:
        why = (f"{uod['ignored_by']['source']} (`{uod['ignored_by']['pattern']}`) ignores it" if uod["ignored_by"]
               else "nothing in `.gitignore` ignores it, so these were never `git add`-ed")
        out.append({"id": "untracked-taskets", "q": "Should the tasket board on disk be tracked?",
                    "fact": f"{uod['count']} tasket(s) sit in `.taskets/` on disk but are not tracked at {ref}, {why} ({src('ls .taskets/*.md')}); "
                            "the done gate, the rails check and synthesis all read tracked taskets, so an install today would see none of them",
                    "options": ["track it: stop ignoring `.taskets/` (or `git add` the files), after first checking nothing in the board must stay out of git",
                                "keep it local: the board stays out of every commit, and the done gate, rails check and synthesis see no units"],
                    "default": "track it, once nothing in the board needs to stay out of git"})
    if h["other_hooks"] and not h["wired_by"]:
        out.append({"id": "hooks", "q": "How does the charter pre-commit gate run next to the hooks the project already has?",
                    "fact": f"the clone runs {lst(h['other_hooks'])}; the installer's hook path would stop them ({src('ls ' + h['hooks_dir'])})",
                    "options": ["wire: add `python3 -B .charter/bin/charter check --staged` to the existing framework's pre-commit; every clone that installs the framework gets the gate",
                                "replace: `--replace-hooks` points core.hooksPath at .charter/githooks, and the existing hooks stop",
                                "CI only: no local charter gate"],
                    "default": "wire"})
    for w in ci["workflows"]:
        if w["push_on_mainline"] and w["deploys"] and w.get("install_triggers"):
            every = [k for k, v in (w.get("changesets") or {}).items() if v]
            out.append({"id": f"deploy:{w['path']}", "q": f"Should charter commits start `{w['path']}`?",
                        "fact": f"a push to {ref} that changes {lst(w['install_paths_not_ignored'], 4)} starts it, and so does a commit with only a {lst(every)} "
                                f"({src('git show ' + ref + ':' + w['path'])})",
                        "options": ["extend its `paths-ignore` with `.charter/**`, `charter/**` and the other charter paths, as its own change merged before the install; "
                                    "that change edits the workflow file, which is not ignored, so its own merge starts the workflow once",
                                    "accept: the install merge and every later charter-only commit start it"],
                        "default": "extend paths-ignore"})
    for x in cl["ignored_install_paths"]:
        out.append({"id": f"ignored:{x['path']}", "q": f"Should `{x['path']}` be committed?",
                    "fact": f"`{x['pattern']}` in {x['source']} ignores it, so the install commit leaves it out ({src('git check-ignore -v ' + x['path'])})",
                    "options": ["commit it: stop ignoring it; what the file holds applies to every clone and every collaborator's session",
                                "keep it local: the installer merges its entries into each checkout's own copy; clones without it rely on the git hook and CI"],
                    "default": "commit it" if x["path"] == ".claude/settings.json" else "decide per file"})
    other = sorted({i["class"] for i in t["items"] if i["class"].startswith("other:") and i["group"] == "open"})
    for c_ in other:
        n = sum(1 for i in t["items"] if i["class"] == c_ and i["group"] == "open")
        dn = [i for i in t["items"] if i["class"] == c_ and i["group"] == "done" and i["boxes"]]
        out.append({"id": f"heading:{c_[6:]}", "q": f"How do taskets whose checklist sits under `## {c_[6:]}` close under charter?",
                    "fact": f"{n} open taskets use it; of {len(dn)} done ones with such a checklist, {sum(1 for i in dn if i['checked'] == i['boxes'] and i['evidence'])} "
                            f"had every box checked and evidence citing a commit or a run ({src('git show ' + ref + ':.taskets/<id>.md')})",
                    "options": [f"convert: each open one gets `## Acceptance` with probes when its work starts; the tooling that writes `## {c_[6:]}` writes `## Acceptance` in charter projects",
                                f"alias: the package reads `## {c_[6:]}` as the acceptance checklist; taskets listed as legacy at install still close with a warning",
                                "leave them legacy: only taskets written after the install carry `## Acceptance`"],
                    "default": "decide at package level: the same heading appears in every project that tooling writes"})
    v = sz["variants"]
    if v.get("none", 0) and (any(k in v for k in ("tests", "tooling", "vendor")) or s.get("exceptions_needed")):
        out.append({"id": "size", "q": "Which files are exempt from the size limit?",
                    "fact": f"{v['none']} files are frozen at install; with " + "; ".join(f"{k} exempt, {n}" for k, n in v.items() if k != "none") +
                            f" ({src('git ls-tree -r ' + ref)})",
                    "options": [f"exempt {k}: add {lst(sz['exempt_groups'][k], 8)} to `exempt_from_size`" for k in ("tooling", "tests", "vendor") if k in v] +
                               ([f"name exceptions: the {len(s['exceptions_needed'])} frozen file(s) open taskets name or recent commits change get a budget, `because:` and `expires:` in `size_exceptions` (the list under § Size), instead of a split unit each"]
                                if s.get("exceptions_needed") else []) +
                               ["exempt nothing: every frozen file needs a split unit before it grows"],
                    "default": "exempt tooling installed from elsewhere; tests as the owner prefers" +
                               ("; exceptions for the files open work must grow, each expiring, rather than a split unit per file" if s.get("exceptions_needed") else "")})
    authors = [a for a in s["history"]["authors_90d"]]
    if len(authors) > 1:
        out.append({"id": "people", "q": "Who is told before the install merges?",
                    "fact": f"{len(authors)} authors committed to {ref} in 90 days: {lst(authors)} ({src('git log --since=90.days --format=%an ' + ref)})",
                    "options": ["tell each of them: the rules file, the gates and the owner-only paths apply to their sessions and commits from the merge"],
                    "default": "tell them before the merge; that is the owner's act"})
    if s["credentials"]:
        out.append({"id": "credentials", "q": "Are the credential-shaped literals placeholders?",
                    "fact": f"{len(s['credentials'])} found, first at {s['credentials'][0]['path']}:{s['credentials'][0]['line']} ({src('git grep -nIE -o <patterns> ' + ref)})",
                    "options": ["confirm they are test placeholders", "rotate them before anything else"], "default": "confirm or rotate first"})
    return out


def plan(s: dict, track: str) -> str:
    c, t, sz, h, cl, ci, ref = s["checkout"], s["taskets"], s["size"], s["hooks"], s["claude"], s["ci"], s["checkout"]["mainline"]
    rh = s.get("rehearsal") or {}
    ver, proj = s["package_version"], s["project"]
    L = [f"# Charter migration plan: {s['name']}", "",
         f"Generated by `charter-pkg survey --plan` from the survey of `{proj}` on `{ref}` at {c['mainline_sha']} "
         f"({src('git rev-parse --short=12 ' + ref)}), charter package {ver}, track {track} as asked. "
         "Each step is one commit on the branch `charter/install`; its rollback is `git revert` of that commit unless stated.", ""]
    ds = decisions(s)
    L += ["## Owner decisions", ""]
    for i, d in enumerate(ds, 1):
        L += [f"### D{i}. {d['q']}", "", f"Measured: {d['fact']}.", "", OPINION]
        L += [f"- {o}" for o in d["options"]] + [f"- Default: {d['default']}.", END, ""]

    L += ["## Before anything", ""]
    busy = c["sessions"] or c["modified"] or c["untracked"]
    L.append(f"- Checkout: {len(c['sessions'])} session(s) in the tree ({lst(p['session'] for p in c['sessions'])}), "
             f"{len(c['modified'])} modified and {len(c['untracked'])} untracked files ({src('git status --porcelain')}). " +
             ("Whoever owns that work commits or parks it; the migration runs on a new branch from " + ref + "." if busy else "Clean."))
    if c["mainline_vs_origin"] and (c["mainline_vs_origin"]["ahead"] or c["mainline_vs_origin"]["behind"]):
        L.append(f"- {ref} differs from origin/{ref} ({src('git rev-list --left-right --count ' + ref + '...origin/' + ref)}); fetch and fast-forward first.")
    if rh.get("left_unstaged"):
        L.append(f"- Staging by name left {lst(rh['left_unstaged'])} out of the install commit; extend the `git add` list (in the clone).")
    for f in (rh.get("check_all") or {}).get("findings", []):
        if " block " in f:
            L.append(f"- The rehearsal's `charter check --all` refused: {f} (in the clone)")
    if rh.get("synth", {}).get("exit"):
        L.append(f"- The rehearsal's `charter synth` failed: {' / '.join(rh['synth']['error'][:2])}. Install from a package version that fixes it (in the clone).")
    if s["binaries"]:
        L.append(f"- {len(s['binaries'])} binary file(s) tracked, so the package must be 0.2.1 or later ({src('git diff --numstat <empty tree> ' + ref)}).")
    L.append("")

    rows = []

    def step(what, files, chk, back, rests):
        rows.append((what, files, chk, back, rests))

    step(f"`git switch -c charter/install {ref}` in a checkout nobody else is working in", "none", "`git status --porcelain` prints nothing",
         "`git branch -D charter/install`", src("git status --porcelain"))
    for d in ds:
        if d["id"].startswith("deploy:"):
            w = d["id"][7:]
            step(f"If D{ds.index(d) + 1} is extend: add the charter paths to `paths-ignore` of `{w}` on its own branch, merged to {ref} before the install",
                 w, "re-run the survey: the install commit no longer starts it", "revert", src(f"git show {ref}:{w}"))
    for d in ds:
        if d["id"] == "ignored:.claude/settings.json":
            step(f"If D{ds.index(d) + 1} is commit it: remove the `.claude/settings.json` line from `.gitignore` and commit `.gitignore` alone; "
                 "keep `.claude/settings.local.json` ignored. The install commit then stages the file, as the owner, because it is owner-only",
                 ".gitignore", "`git check-ignore .claude/settings.json` prints nothing", "revert", src("git check-ignore -v .claude/settings.json"))
    hooks = any(d["id"] == "hooks" for d in ds)
    add = "git add -- " + " ".join(s["add_paths"])
    ignored = any(x["path"] == ".claude/settings.json" for x in cl["ignored_install_paths"])
    step(f"`{TOOL} install {proj} --track {track}`" + (" (add `--replace-hooks` only if the hooks decision is replace)" if hooks else "") +
         f"; stage by name, `{add}`" + (" (plus `.claude/settings.json` once it is no longer ignored)" if ignored else "") +
         f"; commit `charter {ver}` as the owner (`CHARTER_OWNER=1 git commit`)",
         f"{rh.get('committed_files', 'about 30')} files: `.charter/`, `charter/`, `.claude/rules/`, three skills, one agent, `.github/workflows/charter.yml`, `AGENTS.md`, `.gitignore`",
         f"`{CLI} check --all` reports 0 blocking; the rehearsal said: {rh.get('check_all', {}).get('summary', 'not run')} (in the clone)",
         f"`{TOOL} uninstall {proj}`, commit", f"{rh.get('legacy', t['legacy_at_install'])} legacy taskets (in the clone)")
    if hooks:
        wf = next((x for x in h["other_hooks"] if not x.startswith(".git/")), "the hook framework's config")
        step(f"If the hooks decision is wire: add `python3 -B .charter/bin/charter check --staged` to the pre-commit of `{wf}` (.charter/githooks/README.md)",
             wf, "a commit prints the `charter check:` line; the SessionStart banner no longer says the hook is missing", "revert",
             src("ls " + h["hooks_dir"]))
    exempt = next((d for d in ds if d["id"] == "size"), None)
    names = lst(s["history"]["authors_90d"])
    step(f"Owner config in `charter/config.json`: `owner` lists the git author names the owner commits under, and no one else's "
         f"(every author on {ref} in 90 days: {names})" +
         (", `exempt_from_size` as decided" if exempt else "") +
         (", `probes.at_commit: true`" if (rh.get("tests") or {}).get("exit") == 0 else "") + "; commit as the owner",
         "charter/config.json", f"`{CLI} check --all --strict --size` lists the frozen files the decision leaves ({sz['variants'].get('all', 0)} with every group exempt)",
         "revert", src(f"git ls-tree -r {ref}") + (" and the test run (in the clone)" if rh.get("tests") else ""))
    fp = s["history"]["first_parent_50"]
    if fp["squash"]:
        step("Record `charter/decisions/merge-commits.md`: pull requests merge with a merge commit, because a squash merge removes the commits units cite",
             "charter/decisions/merge-commits.md", f"`{CLI} check --all --decisions` clean", "revert",
             f"{fp['squash']} of the last 50 first-parent commits are squash merges ({src('git log --first-parent -n 50 --format=%P ' + ref)})")
    op = [i for i in t["items"] if i["group"] == "open"]
    if op:
        by_cls = {}
        for i in op:
            by_cls[i["class"]] = by_cls.get(i["class"], 0) + 1
        groups = {}
        for i in op:
            groups[i["plan_group"] or "(no group)"] = groups.get(i["plan_group"] or "(no group)", 0) + 1
        step("Triage the open taskets, one commit per plan group: each gets a checklist with a probe per line, under `## Acceptance` or `## Done When`, "
             "when its work starts, or is parked with a line saying why; remove each converted id from `charter/legacy-taskets.txt`. "
             "Fix statuses outside the engines' vocabulary and frontmatter comments on value lines",
             f"{len(op)} open: " + lst(f"{k} {v}" for k, v in by_cls.items()) + "; groups: " + lst(f"{k} {v}" for k, v in sorted(groups.items(), key=lambda x: -x[1])),
             f"`{CLI} check --all --done` clean; `{CLI} probe <id>` runs each converted unit's probes", "revert the batch",
             src(f"git ls-tree -r --name-only {ref} .taskets"))
    dec = s["decisions"]
    if dec["records"] or dec["claude_md_sections"]:
        step("Decisions out of prose: existing decision records stay where they are as the rationale; each rule that code depends on and that a command can check "
             "becomes `charter/decisions/<slug>.md` citing its record, with `binds:` and `check:`; rules stated in `CLAUDE.md` move the same way. "
             "The `charter:<id>` markers in bound files wait until those files next change: a missing marker only warns, "
             f"and editing code here would make the migration's merge start the deploy workflows. `{CLI} decisions index`",
             f"{len(dec['records'])} records, {len(dec['claude_md_sections'])} `CLAUDE.md` sections to read", f"`{CLI} check --all --decisions` clean", "revert",
             src(f"git ls-tree -r --name-only {ref}"))
    cand = [m["path"] for m in s["markdown"]["root"] + s["markdown"]["docs"] if m["archive_candidate"] and not m.get("cited_by")]
    kept = [m["path"] for m in s["markdown"]["root"] + s["markdown"]["docs"] if m["archive_candidate"] and m.get("cited_by")]
    if cand:
        step("Archive the progress and status documents under `docs/history/` with a one-line index; the synthesis replaces them. "
             "Read each first: the name is only a hint" + (f"; {lst(kept)} stay, because code, CI or other docs cite them" if kept else ""),
             lst(cand, 8), "the survey's archive candidates are gone from `docs/`", "`git mv` back, or revert",
             src(f"git grep -l <name> {ref} -- . :!.taskets"))
    over = [g_ for g_ in sz["governance"] if g_["lines"] > g_["limit"] or (g_.get("byte_limit") and g_["bytes"] > g_["byte_limit"])]
    if over:
        step("Split the governance files over the limit; decisions moved out in the step above shrink them", lst(f"{g_['path']} {g_['lines']} lines, {g_['bytes']} bytes" for g_ in over),
             f"`{CLI} check --all --strict --size` no longer lists them", "revert", src(f"git show {ref}:CLAUDE.md"))
    if s["frozen_in_open_work"]:
        step("The owner opens one `kind: split` unit per frozen file that open work must grow, or names it in `size_exceptions` as decided",
             lst(f"{f['path']} ({lst(f['taskets'], 3)})" for f in s["frozen_in_open_work"]), f"`{CLI} check --all --strict --size` shows them as warnings",
             "close the split units", src(f"git grep -n <frozen path> {ref} -- .taskets"))
    coe = [w for w in ci["workflows"] if w["continue_on_error_lines"]]
    step("CI: `charter.yml` runs beside the existing workflows" +
         (f"; the `continue-on-error` gates in {lst(w['path'] for w in coe)} are a separate decision, not a charter step" if coe else ""),
         ".github/workflows/", "the pull request shows the charter job", "revert", src(f"git ls-tree -r --name-only {ref} .github/workflows"))
    step(f"`{CLI} synth --write`, commit; open the pull request with a body that passes `{CLI} anchors --pr`", "charter/progress.md",
         "CI green on `charter.yml`", "revert", f"synth exit {rh.get('synth', {}).get('exit', 'not run')} (in the clone)")

    L += ["## Steps", "", row("#", "Step", "Files", "Check afterwards", "Rollback", "Rests on"), row("---", "---", "---", "---", "---", "---")]
    L += [row(i, *r) for i, r in enumerate(rows, 1)]
    L += ["", "## After the merge", "",
          f"- Every clone that commits needs the gate: the framework's own install when the hook is wired, else `{CLI} setup` once ({src('git config --get core.hooksPath')}).",
          f"- Re-run the survey on {ref}: the legacy count falls as taskets convert, and the frozen list is what the size decision left ({src(TOOL[8:] + ' survey ' + proj)}).", ""]
    return "\n".join(L)


def check(root, text: str):
    """The anchoring check on a rendered document, read-only (the CLI would also log)."""
    return checks.check_anchors(root, text)
