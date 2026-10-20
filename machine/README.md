# Machine layer

What charter puts in `~/.claude`, once per user, from a checkout of this repository. The package (`package/`) is copied into each project and never references anything here; a project runs charter fully without this layer. The layer adds what only the machine can know: which charter checkout the projects came from, and so whether a project is behind, plus a skill that works across projects.

| File | Installed as | What it does |
|---|---|---|
| `hooks/charter-machine.py` | `~/.claude/hooks/charter-machine.py` | SessionStart, in a charter project only: names the checkout (`package repository: <path>`), says when it carries a newer package than the project and when the installed copy of this layer is older than the checkout's, and adds the `## Session` section of `~/.claude/charter-local.md`. Below 0.4.18 it also reports the ledger backlog and what waits on the owner, which the project's own hook does from 0.4.18 |
| `skills/CharterAdmin/` | `~/.claude/skills/CharterAdmin/` | Fleet status, install and upgrade across projects, the ledger fold, and the `Migrate` workflow (survey, rehearsal, one checked commit per step) |
| `settings-fragment.json` | merged into `~/.claude/settings.json` (`hooks.SessionStart`) | Runs the hook |

Claude Code reads user-level skills from `~/.claude/skills/` and user-level hooks from `~/.claude/settings.json` (https://code.claude.com/docs/en/skills, https://code.claude.com/docs/en/hooks).

## Install, check, remove

    python3 <checkout>/bin/charter-pkg machine install            # copies, records the checkout, wires settings (bin/charter_machine.py)
    python3 <checkout>/bin/charter-pkg machine install --link     # symlinks into the checkout: edits here are live
    python3 <checkout>/bin/charter-pkg machine status
    python3 <checkout>/bin/charter-pkg machine uninstall

- **Copy** is the default. The copy carries a sidecar, `~/.claude/hooks/charter-machine.json`, with the path of the checkout it came from, a hash of its `machine/` and a hash of every copied file. When the checkout's `machine/` changes (a `git pull`), the hook says so and `install` refreshes the copy. A branch switch in the checkout does not change what runs.
- **Link** suits someone who edits this layer: a linked hook finds the checkout from its own resolved path (`checkout` in `hooks/charter-machine.py`), and every edit or branch switch in the checkout changes the running hook and skill at once.
- `install` and `uninstall` take `--dry-run`. `install` refuses to replace a hook or skill of the same name that it did not write, or a copy changed since it wrote it, unless `--force`, and `uninstall` keeps either (`_ours` in `bin/charter_machine.py`); `--no-settings` leaves `~/.claude/settings.json` alone and prints the entry to add. Both are `bin/charter_machine.py`.
- A user who manages `~/.claude` with their own link manager or dotfiles repository can point it at `hooks/charter-machine.py` and `skills/CharterAdmin` instead, and add `settings-fragment.json` by hand. Any link name works for the hook; a linked hook finds its checkout from the target.
- `CHARTER_PKG_DIR` overrides the checkout the hook and the skill use (`checkout` in `hooks/charter-machine.py`, `skills/CharterAdmin/SKILL.md` § The checkout).

## Your own additions: `~/.claude/charter-local.md`

The layer is the same for everyone. What is particular to one user goes in `~/.claude/charter-local.md`, which no charter command writes or removes (`uninstall` in `bin/charter_machine.py`). Two sections are read:

- `## Session`: added to the context of every session in a charter project, by the hook (`section` in `hooks/charter-machine.py`). Keep it short: it is read at every start.
- `## Admin`: read by the CharterAdmin skill before its procedures (`skills/CharterAdmin/SKILL.md` § This machine's additions). Where the user's signed contracts are (for the `client` track), which tool puts decisions to them, notifications their setup expects.

Neither section relaxes a rule of `docs/install.md` or of a project's `.claude/rules/charter.md`. An example:

```markdown
## Session

- Progress on a charter project goes in the unit's `## Log`, not in my notes app.
- When decisions wait on me, offer to put them on a decision page.

## Admin

- Signed contracts are in ~/Documents/clients/<client>/; a project has the `client` track only if one is there.
- Put owner decisions on a decision page rather than asking in the terminal.
```
