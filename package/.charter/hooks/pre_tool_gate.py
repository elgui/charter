#!/usr/bin/env python3
"""PreToolUse on Edit|Write|NotebookEdit (a notebook edit's result is not computed: path gates only). Hard gates before the edit lands:
owner-only files and fields (R3, R6, R7), scope (R6), size (R3), done-needs-evidence and
acceptance changes on taskets (R9), retired-decision citations and duplicate ids (R1).
Denies with the override named; warns otherwise. Fails open on its own errors."""
import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path

from _common import tree_for, post_edit_text, read_session, write_session, lib, checks


def main() -> int:
    data = lib.read_hook_input()
    try:
        root = tree_for(data)
        cfg = lib.load_config(root)
        ti = data.get("tool_input") or {}
        path = ti.get("file_path") or ti.get("notebook_path")   # NotebookEdit names its file notebook_path
        if not path:
            return 0
        inside = lib.inside(root, path)
        rp = lib.rel(root, path) if inside else str(path)
        if inside and rp.startswith(lib.STATE_DIR):
            return 0
        sid = data.get("session_id", "")
        cur = read_session(root, sid)   # an attempted edit makes this turn one the Stop gate judges
        if rp not in cur["turn_edited"]:
            cur["turn_edited"].append(rp)
            write_session(root, sid, cur)
        new_text = post_edit_text(data)
        try:
            old_text = Path(path).read_text(encoding="utf-8", errors="replace") if Path(path).exists() else ""
        except OSError:
            old_text = ""
        rep = checks.Report()
        if not lib.owner_session():
            # an Edit whose result cannot be computed still counts as a change to an owner-only path
            why = checks.owner_only_changes(rp, old_text, new_text if new_text is not None else old_text + "\n(unknown edit)", "edit",
                                            lib.as_list(cfg.get("done_statuses")))
            # 0.4.14: an owner act the project's delegate takes at its level (read from the committed config, never the tree)
            # is let through with a note; the commit is still refused to the agent, which hands it over
            kinds = checks.owner_act_kinds(rp, old_text, new_text, "edit", lib.as_list(cfg.get("done_statuses"))) \
                if why and inside and new_text is not None else []
            lv = lib.delegate_level(root)["level"] if kinds else "strict"
            if why and lib.delegable(kinds, lv):
                rep.add(checks.Finding("protected", "warn", f"{rp}: the owner's act ({', '.join(kinds)}), which this project's "
                                       f"delegate takes at level {lv}: leave it staged, run `python3 .charter/bin/charter handover` "
                                       "and then `--wait`; the delegate commits it or hands it back to the owner", path=rp))
            elif why:
                rep.add(checks.Finding("protected", "block", "; ".join(why), path=rp, override=checks.OWNER_OVERRIDE))
        if not inside:
            if rep.blocks:
                lib.log_event(root, "hook", "protected", "block", rep.blocks[0].message, path=rp, event="PreToolUse", session=data.get("session_id", ""))
                lib.deny("charter gate refused this edit.\n" + "\n".join(f"- {f.line()}" for f in rep.blocks))
            return 0
        rep.add(*checks.check_scope(root, cfg, [rp]))
        if new_text is not None:
            new_lines = lib.line_count(new_text)
            old_lines = lib.count_lines(root / rp)
            try:
                old_bytes = (root / rp).stat().st_size
            except OSError:
                old_bytes = 0
            rep.add(*checks.check_size(root, cfg, rp, new_lines, old_lines, len(new_text.encode("utf-8")), old_bytes))
            if rp.startswith(lib.TASKETS_DIR + "/") and rp.endswith(".md"):
                rep.add(*checks.check_unit_done(root, cfg, new_text, rp))
                rep.add(*checks.check_acceptance_change(old_text, new_text, rp))
                keys = lib.inline_comments(new_text)
                if keys:
                    rep.add(checks.Finding("done", "warn", f"inline comment on {', '.join(keys)}: tcv2's reader keeps it as part of the value; put the comment on its own line", path=rp))
            if rp.startswith((lib.CHARTER_DIR + "/decisions/", lib.CHARTER_DIR + "/changes/")) and rp.endswith(".md"):
                rep.add(*checks.id_collision(root, rp, new_text))
            if rp == lib.CHARTER_DIR + "/scope.md":
                rep.add(*[checks.Finding("scope", "warn", f"charter/scope.md: {p}", path=rp) for p in lib.parse_scope(new_text)["problems"]])
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
