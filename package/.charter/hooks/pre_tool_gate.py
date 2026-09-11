#!/usr/bin/env python3
"""PreToolUse on Edit|Write. Hard gates before the edit lands:
scope (R6), size (R3), done-needs-evidence (R9) on taskets, retired-decision citations (R1).
Denies with the override named; warns otherwise. Fails open on its own errors."""
import json
import sys
sys.dont_write_bytecode = True

from _common import tree_for, post_edit_text, lib, checks


def main() -> int:
    data = lib.read_hook_input()
    try:
        root = tree_for(data)
        cfg = lib.load_config(root)
        ti = data.get("tool_input") or {}
        path = ti.get("file_path")
        if not path or not lib.inside(root, path):
            return 0
        rp = lib.rel(root, path)
        if rp.startswith(lib.STATE_DIR):
            return 0
        new_text = post_edit_text(data)
        rep = checks.Report()
        rep.add(*checks.check_scope(root, cfg, [rp]))
        if new_text is not None:
            new_lines = new_text.count("\n") + (0 if new_text.endswith("\n") or not new_text else 1)
            old_lines = lib.count_lines(root / rp)
            rep.add(*checks.check_size(root, cfg, rp, new_lines, old_lines))
            if rp.startswith(lib.TASKETS_DIR + "/") and rp.endswith(".md"):
                rep.add(*checks.check_unit_done(root, cfg, new_text, rp))
            rep.add(*checks.check_decisions_text(root, checks.decision_index(root), rp, new_text))
        for f in rep.findings:
            lib.log_event(root, "hook", f.gate, f.level, f.message, path=rp, event="PreToolUse",
                          session=data.get("session_id", ""), tool=data.get("tool_name", ""))
        if rep.blocks:
            reason = "charter gate refused this edit.\n" + "\n".join(f"- {f.line()}" for f in rep.blocks)
            if rep.warns:
                reason += "\nAlso: " + "; ".join(f.message for f in rep.warns)
            lib.deny(reason)
        if rep.warns:
            lib.allow_with_context("PreToolUse", "charter: " + " | ".join(f.line() for f in rep.warns))
        return 0
    except SystemExit:
        raise
    except Exception as e:  # fail open, but say so
        try:
            lib.log_event(lib.repo_root(), "hook", "error", "warn", f"pre_tool_gate: {e!r}")
        except Exception:
            pass
        print(json.dumps({"systemMessage": f"charter pre_tool_gate error (gate skipped): {e!r}"}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
