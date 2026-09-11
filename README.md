# methodo: the charter method

A working method for client projects run alone with agents. One written charter per project (scope, decisions, units of work with acceptance and evidence) that machines check in Claude Code hooks, git hooks and CI.

- `docs/method.md`: the method, artifacts, rules table, hard gates, accepted results, synthesis, tracks, cost, seams.
- `docs/gates.md`: every hook and gate, what it checks, what it blocks, the legitimate override and where it is recorded.
- `docs/package.md`: layout, commands, versioning, install and upgrade.
- `docs/migration.md`: a path for each starting point, orqueveaux as the worked example.
- `docs/trials/`: what the trial did, per gate, with costs.
- `docs/report-2026-09-11.md`: the report of the session that built it, with decisions for the owner and the evidence index.
- `package/`: the committed layer. `personal/`: the personal layer. `bin/charter-pkg`: the installer. `tests/`: the tests.

Install on a project:

    python3 ~/Projects/methodo/bin/charter-pkg install <project> --track client --dry-run
    python3 ~/Projects/methodo/bin/charter-pkg install <project> --track client

Tests:

    cd tests && python3 -m unittest -q test_gates test_installer
