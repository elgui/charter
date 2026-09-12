#!/usr/bin/env python3
"""SessionEnd. Records tokens for the session, per model, into sessions.jsonl in the shared state directory (R11).
Subagents count: Claude Code writes each subagent's transcript to `<session id>/subagents/*.jsonl` beside the
session's own, and the main transcript holds none of their usage.
Reads the transcripts best-effort: the format is internal to Claude Code and may change,
so a failure here records the session with no token figures rather than nothing."""
import json
import sys
sys.dont_write_bytecode = True
import datetime as dt
from pathlib import Path

from _common import tree_for, lib

FIELDS = (("input", "input_tokens"), ("output", "output_tokens"),
          ("cache_read", "cache_read_input_tokens"), ("cache_write", "cache_creation_input_tokens"))


def _totals() -> dict:
    return {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "turns": 0, "by_model": {}}


def _responses(transcript: Path, rows: dict, subagent_file: bool) -> None:
    """One row per API response, keyed by (message id, request id). Claude Code stores a response once per
    content block; in a subagent's transcript the early blocks carry the usage streamed so far (4 output
    tokens on a thinking block, 778 on the last), so each counter keeps its largest value."""
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
        r = rows.setdefault((m.get("id"), o.get("requestId")),
                            dict({k: 0 for k, _ in FIELDS}, model=m.get("model") or "?", one_h=0, sub=False))
        r["sub"] = r["sub"] or subagent_file or bool(o.get("isSidechain"))
        for k, src in FIELDS:
            r[k] = max(r[k], int(u.get(src, 0) or 0))
        # Claude Code writes much of its cache with the 1-hour TTL, priced at 2x input instead of 1.25x
        r["one_h"] = max(r["one_h"], int((u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) or 0))


def sum_usage(transcript: Path) -> dict:
    """The session's usage: its own transcript plus every subagent transcript, per model. `subagents` is
    the subagents' share, already included in the totals; `children_included` says the files were read."""
    rows: dict = {}
    _responses(transcript, rows, subagent_file=False)
    files = sorted((transcript.with_suffix("") / "subagents").glob("*.jsonl"))
    for p in files:
        _responses(p, rows, subagent_file=True)
    tot = dict(_totals(), models={})
    sub = _totals()
    for r in rows.values():
        for t in ((tot, sub) if r["sub"] else (tot,)):
            t["turns"] += 1
            per = t["by_model"].setdefault(r["model"], {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cache_write_1h": 0})
            for k, _ in FIELDS:
                t[k] += r[k]
                per[k] += r[k]
            per["cache_write"] -= r["one_h"]
            per["cache_write_1h"] += r["one_h"]
        tot["models"][r["model"]] = tot["models"].get(r["model"], 0) + 1
    tot.update(subagent_output=sub["output"], subagents=sub, children_included=True, subagent_files=len(files))
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
        st = lib.shared_state_dir(root)
        st.mkdir(parents=True, exist_ok=True)
        with (st / "sessions.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        sf = lib.local_state_dir(root) / f"session-{sid}.json"   # per-session scratch is spent
        if sf.exists():
            sf.unlink()
        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
