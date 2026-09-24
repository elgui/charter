# Personal layer

What belongs in `~/.claude` on Gui's machines and nowhere else. The committed layer (`package/`) never references any of this.

| File | Goes to | Why personal |
|---|---|---|
| `claude-home/hooks/charter-personal.py` | the directory `~/.claude/hooks` resolves to | Reads `~/Projects/charter`, points at Crossroads/Slate, and says the project's taskets are its record (no `MEMORY/WORK` or `PROJECTS.md` entry) |
| `claude-home/Skills/CharterAdmin/` (`SKILL.md`, `workflows/Migrate.md`, `tools/Survey.help.md`) | the directory `~/.claude/Skills` resolves to | Operates across `~/Projects/*`; `Migrate` calls this repository's installer and survey |
| `settings.fragment.json` | merged into `~/.claude/settings.json` (`hooks.SessionStart`) | User-level hook |
| `settings.trial.json` | nothing; used by the trial through `--settings` | Absolute path to this checkout |

`~/.claude` is assembled by `~/.claude/rebuild-symlinks.sh` from `~/AI_tooling/PAI/personal/host/claude-home/symlink-manifest.tsv`; `~/.claude/hooks` and `~/.claude/Skills` resolve to directories under `~/AI_tooling/PAI/generic/claude/` (lane 2 § A3). Two ways to install, for the owner to choose (decision `personal-layer-home` in the report):

## Option A: copy into the resolved directories (no manifest change)

    HOOKS=$(readlink -f ~/.claude/hooks); SKILLS=$(readlink -f ~/.claude/Skills)
    cp ~/Projects/charter/personal/claude-home/hooks/charter-personal.py "$HOOKS/"
    mkdir -p "$SKILLS/CharterAdmin" && cp -R ~/Projects/charter/personal/claude-home/Skills/CharterAdmin/. "$SKILLS/CharterAdmin/"
    # then add the SessionStart entry from settings.fragment.json to ~/.claude/settings.json

## Option B: symlink from this checkout (manifest lines)

Add to `symlink-manifest.tsv` (target then link, as the existing lines do):

    $HOME/AI_tooling/PAI/generic/claude/Hooks/charter-personal.py	$HOME/Projects/charter/personal/claude-home/hooks/charter-personal.py
    $HOME/AI_tooling/PAI/generic/claude/Skills/CharterAdmin	$HOME/Projects/charter/personal/claude-home/Skills/CharterAdmin

then `~/.claude/rebuild-symlinks.sh`, and add the SessionStart entry to `~/.claude/settings.json`.

Skill name `CharterAdmin` does not collide with anything in `~/.claude/Skills/` or `~/.claude/commands/` (checked 2026-09-11). The project skills are `charter-unit`, `charter-decision`, `charter-progress`; none shares a name with a personal skill, so project resolution is not shadowed.
