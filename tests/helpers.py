"""Test helpers: build a throwaway git project with the package installed."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PKG = REPO / "package"
INSTALLER = REPO / "bin" / "charter-pkg"
# a chain under test must not raise macOS notifications; tests of notify() set their own value
os.environ["CHARTER_NOTIFY"] = "off"
os.environ["CHARTER_OWNER_REVIEW"] = "off"   # no test calls Codex unless it sets a review command itself (0.4.11)

SCOPE = """# Scope

Summary of devis TB-1. Owner: Test Owner.

## In scope

### S1 — Health endpoint
paths: app/health.py, tests/**
What is delivered: a health endpoint.

## Out of scope

### X1 — Invoicing
paths: app/billing.py, app/billing/**
Why: kept in the ERP.

## Assumptions

- none
"""

DECISION = """---
id: retry-limit
title: Retries are capped at 3
status: active
date: 2026-09-11
owner: Test Owner
kind: design
binds: [app/health.py]
check: grep -q "MAX_RETRIES = 3" app/health.py
expires: 2027-03-01
---

## Decision

MAX_RETRIES stays at 3.

## Because

Incident: retries flooded upstream.

## Stops applying when

Rate limit lifted.
"""

RETIRED = """---
id: old-cache
title: In-memory cache
status: retired
superseded_by: retry-limit
expires: 2026-08-01
---

## Decision

Retired.

## Because

Replaced.
"""

UNIT = """---
id: u1
title: Health endpoint reports retries
status: next
priority: p1
scope: S1
perimeter: [app/health.py, tests/**]
decisions: [retry-limit]
kind: work
---

## Context

Client wants retries in /health.

## Acceptance

- [ ] AC-1: health() returns retries == 3 — probe: `python3 -c "from app.health import health; assert health()['retries']==3"`

## Evidence

## Log

- 2026-09-11 14:00 created
"""


def clean_env(**extra):
    """The test process may itself run inside Claude Code; keep its markers out of the hooks."""
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CHARTER_OWNER", "CHARTER_UNIT", "CLAUDE_CODE_SESSION_ID")}
    env.update(extra)
    return env


def git(root, *args, check=True, env=None):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=check,
                          env=env or clean_env())


def make_project(with_charter=True, track="client"):
    d = Path(tempfile.mkdtemp(prefix="charter-test-")).resolve()   # TMPDIR may go through the /var symlink
    (d / "app").mkdir()
    (d / "tests").mkdir()
    (d / "app" / "__init__.py").write_text("")
    (d / "app" / "health.py").write_text('"""Health. charter:retry-limit"""\nMAX_RETRIES = 3\n\n\ndef health():\n    return {"ok": True, "retries": MAX_RETRIES}\n')
    (d / "app" / "billing.py").write_text("def invoice(a):\n    return a\n")
    (d / "tests" / "test_health.py").write_text("from app.health import health\n\n\ndef test_ok():\n    assert health()['ok']\n")
    (d / "README.md").write_text("scratch\n")
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "user.name", "Test Owner")
    git(d, "config", "user.email", "t@example.com")
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "scratch project")
    if with_charter:
        r = subprocess.run([sys.executable, str(INSTALLER), "install", str(d), "--track", track], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        (d / "charter" / "scope.md").write_text(SCOPE)
        (d / "charter" / "decisions" / "retry-limit.md").write_text(DECISION)
        (d / "charter" / "decisions" / "old-cache.md").write_text(RETIRED)
        (d / ".taskets" / "u1.md").write_text(UNIT)
        git(d, "add", "-A")
        git(d, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "install charter")
    return d


def run_hook(root, name, payload, env=None):
    """Run a hook script the way Claude Code does: JSON on stdin, cwd at the project."""
    env = clean_env(CLAUDE_PROJECT_DIR=str(root), **(env or {}))
    payload = dict({"session_id": "test-session", "cwd": str(root), "hook_event_name": name}, **payload)
    r = subprocess.run([sys.executable, str(root / ".charter" / "hooks" / f"{name}.py")], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=str(root), env=env)
    out = {}
    try:
        out = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    except json.JSONDecodeError:
        out = {}
    return r.returncode, out, r.stdout, r.stderr


def charter(root, *args, env=None):
    return subprocess.run([sys.executable, str(root / ".charter" / "bin" / "charter"), "--root", str(root), *args],
                          capture_output=True, text=True, cwd=str(root), env=clean_env(**(env or {})))


def cleanup(d):
    shutil.rmtree(d, ignore_errors=True)
