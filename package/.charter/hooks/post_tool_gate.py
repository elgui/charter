#!/usr/bin/env python3
"""PostToolUse on Edit|Write|NotebookEdit. Warnings after the edit landed:
perimeter without a note (R4), decision `check:` commands bound to the file (R1),
and a per-session record of edited paths for the Stop hook."""
import json
import sys
sys.dont_write_bytecode = True

from _common import tree_for, read_session, write_session, lib, checks


def main() -> int:
    data = lib.read_hook_input()
    try:
        root = tree_for(data)
        cfg = lib.load_config(root)
        ti = data.get("tool_input") or {}
        path = ti.get("file_path") or ti.get("notebook_path")   # NotebookEdit names its file notebook_path
        if not path or not lib.inside(root, path):
            return 0
        rp = lib.rel(root, path)
        if rp.startswith(lib.STATE_DIR):
            return 0
        sid = data.get("session_id", "")
        # remember what this session and this turn edited (for the Stop hook and the ledger)
        cur = read_session(root, sid)
        for key in ("edited", "turn_edited"):
            if rp not in cur[key]:
                cur[key].append(rp)
        write_session(root, sid, cur)

        units = lib.taskets(root)
        unit = units.get(lib.active_unit(root) or "")
        rep = checks.Report()
        rep.add(*checks.check_perimeter(root, cfg, unit, [rp], at_commit=False))
        rep.add(*checks.run_decision_checks(root, checks.decision_index(root), only_bound_to=[rp]))
        for f in rep.findings:
            lib.log_event(root, "hook", f.gate, f.level, f.message, path=rp, event="PostToolUse", session=sid)
        if rep.blocks:
            # PostToolUse cannot undo the edit; exit 2 puts stderr in front of Claude.
            sys.stderr.write("charter: " + "\n".join(f.line() for f in rep.blocks) + "\n")
            return 2
        if rep.warns:
            lib.allow_with_context("PostToolUse", "charter: " + " | ".join(f.line() for f in rep.warns))
        return 0
    except SystemExit:
        raise
    except Exception as e:
        print(json.dumps({"systemMessage": f"charter post_tool_gate error (gate skipped): {e!r}"}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
