#!/usr/bin/env python3
"""SessionEnd. Records tokens for the session into .charter/state/sessions.jsonl (R11).
Reads the transcript best-effort: the format is internal to Claude Code and may change,
so a failure here records the session with no token figures rather than nothing."""
import json
import sys
import datetime as dt
from pathlib import Path

from _common import tree_for, lib


def sum_usage(transcript: Path) -> dict:
    tot = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "turns": 0, "subagent_output": 0, "models": {}}
    seen = set()
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("type") != "assistant":
            continue
        m = o.get("message") or {}
        u = m.get("usage")
        if not u:
            continue
        key = (m.get("id"), o.get("requestId"))
        if key in seen:      # one API response is stored once per content block
            continue
        seen.add(key)
        tot["turns"] += 1
        tot["input"] += int(u.get("input_tokens", 0))
        tot["output"] += int(u.get("output_tokens", 0))
        tot["cache_read"] += int(u.get("cache_read_input_tokens", 0))
        tot["cache_write"] += int(u.get("cache_creation_input_tokens", 0))
        if o.get("isSidechain"):
            tot["subagent_output"] += int(u.get("output_tokens", 0))
        mdl = m.get("model") or "?"
        tot["models"][mdl] = tot["models"].get(mdl, 0) + 1
    return tot


def main() -> int:
    data = lib.read_hook_input()
    try:
        root = tree_for(data)
        if not (root / lib.TOOL_DIR).is_dir():
            return 0
        sid = data.get("session_id", "")
        rec = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "session": sid,
               "unit": lib.active_unit(root) or "", "reason": data.get("reason", ""), "usage": None, "note": ""}
        tp = data.get("transcript_path")
        if tp and Path(tp).exists():
            try:
                rec["usage"] = sum_usage(Path(tp))
            except Exception as e:
                rec["note"] = f"usage unreadable: {e!r}"
        else:
            rec["note"] = "no transcript path"
        st = root / lib.STATE_DIR
        st.mkdir(parents=True, exist_ok=True)
        with (st / "sessions.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
