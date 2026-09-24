# charter

A working method for client projects run alone with agents. One written charter per project (scope, decisions, units of work with acceptance and evidence) that machines check in Claude Code hooks, git hooks and CI.

This repository was called `methodo` until 2026-09-24 (decision `package-name` in `docs/report-2026-09-11.md`). Dated records under `docs/` still say `methodo`; they are left as written.

## What is in here

Three things live in this one repository. Each goes to a different place and is tracked by a different git history.

| Part | Path | Where it ends up | Tracked by |
|---|---|---|---|
| **The package** (the committed layer) | `package/` | Copied into each project by `bin/charter-pkg install` as `.charter/`, `charter/`, `.claude/rules|skills|agents`, a CI workflow | The **project's** git: the project commits the copy. This repository only holds the source |
| **The personal layer** | `personal/` | `~/.claude`, through two symlinks back into this checkout (the `CharterAdmin` skill and the `charter-personal.py` hook) | **This** repository: an edit here is live on the machine at once |
| **The tooling around them** | `bin/`, `tests/` | Stays here. `bin/charter-pkg` installs, upgrades, surveys; `tests/` tests the package and the installer | This repository |

Everything else is documentation, in two kinds:

- **Reference** (read these to use the method): `docs/method.md` (the method), `docs/gates.md` (every gate, what it blocks, the override), `docs/package.md` (layout, commands, versioning), `docs/migration.md` (one path per starting point), `docs/design/migration-workflow.md` (the survey and the `Migrate` workflow), `docs/method-visual.html` (the method in diagrams, offline).
- **History** (how it was built and why; nothing reads these at run time): `docs/report-2026-09-11.md` (the build report and its decisions), `docs/session-log.md`, `docs/briefs/`, `docs/review/` (weakness evaluation, harmonization review, findings), `docs/trials/` (per-gate trial results with costs).

## Install

**The package, on a project.** Run from this checkout; the project needs a clean working tree.

    # a project that already has code, taskets or documents: survey first (read-only), follow the plan it writes
    python3 ~/Projects/charter/bin/charter-pkg survey <project> --out <dir>

    # a new project
    python3 ~/Projects/charter/bin/charter-pkg install <project> --track client --dry-run
    python3 ~/Projects/charter/bin/charter-pkg install <project> --track client

    # later
    python3 ~/Projects/charter/bin/charter-pkg status  <project>
    python3 ~/Projects/charter/bin/charter-pkg upgrade <project> --dry-run

Then commit the result in the project. In another clone of a project that already has the package: `python3 .charter/bin/charter setup` once (it installs the git hook, which git does not clone).

**The personal layer, on this machine.** Done once per machine: `personal/README.md`, option B (two lines in the PAI symlink manifest, then `~/.claude/rebuild-symlinks.sh`, plus the `SessionStart` entry from `personal/settings.fragment.json` in `~/.claude/settings.json`). On Gui's main machine all three are in place (the hook registered 2026-09-24).

**Changing the method.** Edit `package/`, run the tests, bump `package/VERSION`, commit here, then `charter-pkg upgrade` each project and commit there (`docs/migration.md`, last section).

## Tests

    cd tests && python3 -B -m unittest -q test_gates test_installer test_review_regressions test_harmonization_regressions test_batch1_regressions test_migration test_size_exceptions test_rails test_review_20260923
