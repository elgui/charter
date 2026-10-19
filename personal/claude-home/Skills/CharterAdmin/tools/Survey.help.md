# charter-pkg survey

The survey lives in the charter repository (`bin/charter_survey.py`, rendered by `bin/charter_plan.py`), next to the installer it rehearses. This skill calls it; it has no tool of its own.

    python3 ~/Projects/charter/bin/charter-pkg survey <project> [options]

| Option | Effect |
|---|---|
| `--track client\|prototype` | Required. The track the rehearsal installs and the plan assumes |
| `--out DIR` | Write `survey.json`, `survey.md` and `plan.md` into DIR; refused inside the project |
| `--plan` | Print the plan instead of the report |
| `--json` | Print the facts as JSON |
| `--test-cmd CMD` | Run CMD in the rehearsal clone and report its exit and duration |
| `--ref BRANCH` | Survey a local branch instead of the main line, for example `charter/install` |
| `--keep-clone` | Keep the rehearsal clone and print its path |
| `--no-rehearse` | Skip the throwaway install |
| `--offline` | Do not ask GitHub for the repository's visibility |
| `--instructions PATH` | Repeatable. Also read this instruction file outside the project and what it imports: `~/.claude/CLAUDE.md`, `~/.claude/rules/*.md` |

Exit codes: 0 when both documents pass their own anchoring check; 2 for a directory that is not a git repository with a commit, an `--out` inside the project or an unknown `--ref`; 3 when a rendered line fails the anchoring check.

What it measures:

- **Checkout:** branch, drift from the main line and its origin, uncommitted files, and the tmux sessions working in the tree.
- **Taskets:** each classed by acceptance: none, a checklist under another heading such as `## Done When`, prose, a checklist, or a checklist with probes. Also statuses outside the engines' vocabulary, frontmatter comments, missing or duplicate ids, and the legacy count the installer would seed.
- **Size:** files frozen at install, with tests, agent tooling or vendored code exempt; governance files; frozen files an open tasket names.
- **Git hooks:** installed hooks and hook frameworks the charter hook path would stop.
- **Claude Code files:** what is tracked, and which installer paths `.gitignore` keeps out of a commit.
- **CI:** workflows that run on a push to the main line and whether they deploy. For each, whether the install commit or a one-file charter commit starts it, and its `continue-on-error` lines.
- **Remote and history:** the origin, GitHub visibility, authors over 90 days, the merge style of the last 50 first-parent commits, credential-shaped literals (prefix and length only), binaries, and test commands.
- **Instructions:** every instruction file a session loads in the project (`CLAUDE.md`, `CLAUDE.local.md`, nested ones, `.claude/rules/`, `AGENTS.md`, their `@` imports, and the files named with `--instructions`), and each line that overlaps a charter rule, with both lines cited (`bin/charter_instructions.py`). `charter-pkg instructions <project>` prints the same section on its own.
- **Documents:** root and `docs/` markdown with last-commit dates and archive candidates, decision records, `CLAUDE.md` sections, and BMAD files.
- **Rehearsal:** the install in a clone, staged by name, committed through the pre-commit gate, then `check --all`, `check --all --strict --size`, `synth` and the optional test command.
