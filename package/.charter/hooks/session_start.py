#!/usr/bin/env python3
"""SessionStart. Prints the charter index: version, track, active unit with its
open criteria, active decisions, pending changes, recent gate activity (R5)."""
import json
import sys
sys.dont_write_bytecode = True
import datetime as dt

from _common import tree_for, read_session, write_session, head, lib, checks


def main() -> int:
    data = lib.read_hook_input()
    try:
        root = tree_for(data)
        if not (root / lib.TOOL_DIR).is_dir():
            return 0
        cfg = lib.load_config(root)
        sid = data.get("session_id", "")
        cur = read_session(root, sid)   # the Stop gate compares HEAD against this to see a commit land
        cur["head"] = head(root)
        write_session(root, sid, cur)
        ver = (root / lib.CHARTER_DIR / "VERSION").read_text().strip() if (root / lib.CHARTER_DIR / "VERSION").exists() else "?"
        out = [f"charter {ver}, track {cfg.get('track')}. Rules: .claude/rules/charter.md. CLI: python3 .charter/bin/charter --help"]
        if lib.git(root, "config", "--get", "core.hooksPath").stdout.strip() != ".charter/githooks":
            out.append("The charter git hook is not active in this clone, so commits are not gated until CI. "
                       "Run `python3 .charter/bin/charter setup` once (it sets core.hooksPath), or tell the owner.")
        if cfg.get("track") == "client" and not lib.as_list(cfg.get("owner")):
            out.append("charter/config.json names no owner, so CI cannot tell the owner's commits from anyone else's; "
                       "the owner sets `owner` to their git author name.")
        if lib.owner_session():
            out.append("Owner session (CHARTER_OWNER=1): owner-only files and fields may be edited.")
        units = lib.taskets(root)
        aid = lib.active_unit(root)
        if aid and aid in units:
            u = units[aid]
            acc = lib.section(u.get("_body", ""), "Acceptance")
            boxes = checks.CHECKBOX_RE.findall(acc)
            open_n = sum(1 for b in boxes if b[0] == " ")
            per = ", ".join(lib.as_list(u.get("perimeter"))) or "(none declared)"
            log = lib.section(u.get("_body", ""), "Log").splitlines()
            last = log[-1].strip() if log else "(no log line yet)"
            out.append(f"Active unit {aid}: {u.get('title', '')} [status {u.get('status')}] scope {u.get('scope', '(none)')}; "
                       f"{open_n}/{len(boxes)} acceptance criteria open; perimeter {per}; last log: {last}")
        else:
            out.append("No active unit. Start one with `python3 .charter/bin/charter unit start <tasket-id>` (edits are otherwise unattributed).")
        decs = [(k, v) for k, v in lib.decisions(root).items() if str(v.get("status", "active")) == "active"]
        if decs:
            out.append("Active decisions (cite with charter:<id> in code that depends on them):")
            for k, v in decs[:30]:
                out.append(f"  - {k}: {v.get('title', '')}" + (f" [check: {v.get('check')}]" if v.get('check') else ""))
        props = [(k, v) for k, v in lib.decisions(root).items() if str(v.get("status")) == "proposed"]
        if props:
            out.append("Proposed decisions waiting on the owner: " + ", ".join(k for k, _ in props))
        chg = [(k, v) for k, v in lib.change_requests(root).items() if str(v.get("status")) == "proposed"]
        if chg:
            out.append("Change requests waiting on the owner: " + ", ".join(k for k, _ in chg))
        logp = lib.shared_state_dir(root) / "log.jsonl"
        if logp.exists():
            since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).isoformat()
            counts = {}
            for line in logp.read_text().splitlines()[-2000:]:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("ts", "") >= since:
                    key = f"{r.get('gate')}/{r.get('decision')}"
                    counts[key] = counts.get(key, 0) + 1
            if counts:
                out.append("Gate activity, last 7 days: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        print("\n".join(out))
        return 0
    except Exception as e:
        print(f"charter session_start error: {e!r}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
