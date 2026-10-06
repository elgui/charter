# Survey cites a Makefile as the source of test commands it guessed from other files

- Seen: 2026-09-28, my-bench at 1d8003ab1091, charter 0.4.6
- Status: open

## What happened

`charter-pkg survey /Users/gui/dev/my-bench --track prototype --test-cmd "uv run pytest"` wrote this row in `survey.md` under *Remote and history*:

```
| Test commands found | `python3 -m pytest -q` | `$ git show main:Makefile` |
```

my-bench has no Makefile:

```
$ git show main:Makefile
fatal: path 'Makefile' does not exist in 'main'
```

The command was guessed from `pyproject.toml` and `tests/*.py`, not read from a Makefile. So the row's source anchor names a file that doesn't exist, and a reader who trusts the anchor is misled about where the command came from.

The guessed command is also wrong for this project:

- my-bench runs on `uv` (`uv sync`, `uv run pytest`, per its CLAUDE.md). `python3 -m pytest` runs outside the project venv.
- `pyproject.toml` already sets `addopts = "-q"`. The extra `-q` makes it `-qq`, which suppresses pytest's summary line entirely. A probe built on it would print nothing on success.

Expected: each test command is cited with the file it was actually derived from, and marked as a guess when no file declares it.

## Reproduce

Any project with a `pyproject.toml` or `tests/*.py` and no Makefile:

```bash
python3 ~/dev/charter/bin/charter-pkg survey <project> --track prototype --no-rehearse --offline --out /tmp/s
grep 'Test commands found' /tmp/s/survey.md
```

## Where

- `bin/charter_plan.py:175`: `row("Test commands found", lst(...s["test_candidates"]), src(f"git show {ref}:Makefile"))`, which hardcodes the Makefile as the source for every candidate.
- `bin/charter_survey.py:530-543` (`s_tests`): candidates come from four places (the `Makefile` targets, `package.json` scripts, `pytest.ini`/`pyproject.toml`/`setup.cfg`/`tests/*.py`, `go.mod`). The last three are guesses by file presence, and their origin isn't kept in the returned list.
- The pytest guess ignores `addopts` in `[tool.pytest.ini_options]` and ignores `uv` (a `[tool.uv]` table, a `uv.lock`, or `uv` in a CLAUDE.md commands block). (inference: I didn't check whether other runners like poetry or hatch have the same blind spot.)

## Workaround

The migration uses `uv run pytest`, which the owner confirmed and the rehearsal ran green (`--test-cmd "uv run pytest"`: exit 0 in 10 s, in the clone). The survey row is ignored.

## Suggested fix

Return `(command, source)` pairs from `s_tests` and render each with its own anchor. Mark presence-based guesses as `(inference)` rather than citing a file that doesn't exist. For pytest, drop `-q` when `addopts` already carries it, and prefer `uv run pytest` when the project is on uv.
