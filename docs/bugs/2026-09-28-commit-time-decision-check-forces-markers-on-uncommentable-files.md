# A decision check can run at commit only by binding files, and binding files demands a marker even in JSON

- Seen: 2026-09-28, claude-plugins at 1f13180, charter 0.4.6
- Status: open

## What happened

claude-plugins wanted one decision to run `sh scripts/check-plugins.sh` whenever a file under `plugins/` is committed (a plugin changed without a version bump never reaches clients). A decision's `check:` runs at commit only when a staged path matches its `binds:`, but every bound file that lacks a `charter:<id>` marker also warns:

```
charter/decisions warn [<path>]: <path> is bound by decision `<id>` (...) but carries no `charter:<id>` marker
```

So `binds: [plugins/**]` would warn on every plugin commit, once per file, and `plugins/<name>/.claude-plugin/plugin.json` cannot carry a comment at all. `binds:` means two things at once: "these paths trigger the check at commit" and "these files depend on the decision and must say so".

## Reproduce

In a charter project: a decision with `check: true` and `binds: ["*.json"]`, then stage and commit any JSON file. The check runs, and the gate warns that the file carries no marker.

## Where

- `package/.charter/bin/charter:176-184`: at commit, only decisions whose `binds:` match a staged path have their `check:` run.
- `package/.charter/checks.py:527-532`: every active decision whose `binds:` match a changed file warns when the file lacks `charter:<id>`.

## Workaround

The decision carries no `binds:`, and the check compares against `origin/main` instead of the index, so it runs in `charter check --all` and in CI on every pull request but not at `git commit` (claude-plugins `charter/decisions/plugin-version-bumped.md`).

## Suggested fix

Separate the two meanings: a key such as `runs_on:` (paths that trigger the check at commit, no marker required) beside `binds:` (files that must carry the marker). Or exempt files whose format has no comment syntax (`*.json`) from the marker warning.
