#!/usr/bin/env python3
"""Stop. Blocks at most once per turn when the final message claims completion
without evidence (R9/R10), or when the active unit is marked done but its own
gate fails. Reads stop_hook_active so it can never loop."""
import json
import re
import sys

from _common import tree_for, lib, checks


def main() -> int:
    data = lib.read_hook_input()
    try:
        root = tree_for(data)
        cfg = lib.load_config(root)
        sid = data.get("session_id", "")
        msg = data.get("last_assistant_message") or ""
        if data.get("stop_hook_active"):
            lib.log_event(root, "hook", "done", "passed", "second stop attempt let through (stop_hook_active)", session=sid, event="Stop")
            return 0
        reasons = []
        claims = checks.DONE_CLAIM_RE.search(msg) is not None
        if claims:
            ok, bad = checks.evidence_anchors(root, msg)
            admitted = re.search(r"\b(not (yet )?done|unverified|could not verify|did not run|no evidence)\b", msg, re.I)
            if not ok and not admitted:
                reasons.append("the final message claims completion but cites no evidence: give the commit SHA, the file:line of the change, the test command and its result, or a URL; or say plainly what is not done")
            if bad:
                reasons.append(f"the final message cites anchors that do not resolve: {', '.join(bad[:5])}")
        unit = lib.taskets(root).get(lib.active_unit(root) or "")
        if unit is not None and str(unit.get("status")) in lib.as_list(cfg.get("done_statuses")):
            for f in checks.check_unit_done(root, cfg, (root / unit["_path"]).read_text(encoding="utf-8"), unit["_path"]):
                reasons.append(f.line())
        if reasons:
            lib.log_event(root, "hook", "done", "block", "; ".join(reasons)[:500], session=sid, event="Stop")
            lib.block_stop("charter stop gate (blocks once):\n- " + "\n- ".join(reasons))
        # non-blocking nag: code edited this turn, active unit's log not touched
        st = root / lib.STATE_DIR / f"session-{sid}.json"
        if unit is not None and st.exists():
            edited = json.loads(st.read_text()).get("edited", [])
            code = [p for p in edited if not p.startswith(lib.TASKETS_DIR) and not p.startswith(lib.CHARTER_DIR)]
            if code and unit["_path"] not in edited:
                lib.log_event(root, "hook", "log", "warn", f"session edited {len(code)} file(s) and did not append to {unit['_path']}", session=sid, event="Stop")
                print(json.dumps({"systemMessage": f"charter: {len(code)} file(s) edited this session; append a dated line under `## Log` in {unit['_path']}"}))
        return 0
    except SystemExit:
        raise
    except Exception as e:
        print(json.dumps({"systemMessage": f"charter stop_gate error (gate skipped): {e!r}"}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
