#!/usr/bin/env python3
"""Stop. Judges a turn only if it attempted an Edit or Write or moved HEAD (a commit landed):
a final message that claims completion must cite a commit, a path:line or a `$ command` run,
or say plainly what is not done (R9/R10); an active unit marked done must pass its own gate.
Blocks at most once per turn: stop_hook_active lets the second Stop through.
When a commit landed and the active unit's `## Log` did not move, it tells Claude once through
`additionalContext`, the Stop channel Claude reads (R5)."""
import json
import re
import sys
sys.dont_write_bytecode = True

from _common import tree_for, read_session, write_session, head, lib, checks

ADMITTED_RE = re.compile(r"\b(not (yet )?done|unverified|could not verify|did not run|no evidence|not complete)\b", re.I)


def main() -> int:
    data = lib.read_hook_input()
    try:
        root = tree_for(data)
        cfg = lib.load_config(root)
        sid = data.get("session_id", "")
        msg = data.get("last_assistant_message") or ""
        cur = read_session(root, sid)
        now = head(root)
        touched, before = list(cur["turn_edited"]), cur.get("head") or ""
        cur["turn_edited"], cur["head"] = [], now      # the next turn starts clean
        write_session(root, sid, cur)
        if data.get("stop_hook_active"):
            lib.log_event(root, "hook", "done", "passed", "second stop attempt let through (stop_hook_active)", session=sid, event="Stop")
            return 0
        moved = bool(before and now and before != now)
        if not touched and not moved:
            return 0     # a turn that changed nothing: an explanation is not a completion claim
        reasons = []
        if checks.DONE_CLAIM_RE.search(msg):
            k = checks.classify_anchors(root, msg)
            if not (k["sha"] or k["fileline"] or k["run"]) and not ADMITTED_RE.search(msg):
                reasons.append("the final message claims completion but cites no commit, no path:line and no `$ command` run "
                               "(a file name alone shows nothing); cite them, or say plainly what is not done")
            if k["bad"]:
                reasons.append(f"the final message cites anchors that do not resolve: {', '.join(k['bad'][:5])}")
        unit = lib.taskets(root).get(lib.active_unit(root) or "")
        if unit is not None and str(unit.get("status")) in lib.as_list(cfg.get("done_statuses")):
            for f in checks.check_unit_done(root, cfg, (root / unit["_path"]).read_text(encoding="utf-8"), unit["_path"]):
                if f.level == "block":
                    reasons.append(f.line())
        note = ""
        if moved and unit is not None:
            landed = lib.git(root, "diff", "--name-only", before, now).stdout.splitlines()
            if unit["_path"] not in landed and unit["_path"] not in touched:
                note = (f"charter: commit(s) landed this turn ({before[:7]}..{now[:7]}) and {unit['_path']} has no new `## Log` line. "
                        f"Append one dated line under `## Log` saying what landed, then stop.")
                lib.log_event(root, "hook", "log", "warn", f"commits landed without a log line in {unit['_path']}", session=sid, event="Stop")
        if reasons:
            lib.log_event(root, "hook", "done", "block", "; ".join(reasons)[:500], session=sid, event="Stop")
            lib.block_stop("charter stop gate (blocks once):\n- " + "\n- ".join(reasons) + (f"\n{note}" if note else ""))
        if note:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": note}}))
        return 0
    except SystemExit:
        raise
    except Exception as e:
        print(json.dumps({"systemMessage": f"charter stop_gate error (gate skipped): {e!r}"}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
