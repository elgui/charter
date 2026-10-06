# The personal layer points at a stale 0.4.2 checkout, and fleet does not see projects under ~/dev

- Seen: 2026-09-29, photogram (`~/dev/photogram`) at c656ca8, charter 0.4.6 installed from `~/dev/charter` at 7758bec
- Status: open

## What happened

The owner's global instructions name `~/dev/charter` as the method's home. The personal layer still defaults to `~/Projects/charter` in three places, and that path holds another clone, at 0.4.2:

```
$ cat ~/dev/charter/package/VERSION; cat ~/Projects/charter/package/VERSION
0.4.6
0.4.2
$ git -C ~/Projects/charter log --oneline -1
cbb55fe Docs housekeeping; charter 0.4.2 (documentation only)
```

1. The `CharterAdmin` skill (symlinked into `~/.claude-lean/skills/` from this repository) tells the agent to install from `~/Projects/charter`. An agent that follows it installs 0.4.2. Seen while installing charter on photogram: the agent noticed the version gap and used `~/dev/charter` instead.
2. `charter-personal.py` compares a project against `~/Projects/charter` by default. A project behind 0.4.6 but at or above 0.4.2 is not reported as behind (inference; the hook was not run for this report).
3. `charter-pkg fleet` scans `~/Projects` by default. Projects under `~/dev`, such as photogram and hermes-custom, are left out of the fleet table unless `--root ~/dev` is passed (inference from the default; `fleet` was not run for this report).

## Reproduce

```
grep -n 'Projects/charter' ~/dev/charter/personal/claude-home/Skills/CharterAdmin/SKILL.md
grep -n 'Projects' ~/dev/charter/personal/claude-home/hooks/charter-personal.py ~/dev/charter/bin/charter-pkg
```

## Where

- `personal/claude-home/Skills/CharterAdmin/SKILL.md:8`, `:52`, `:67-70`: `~/Projects/charter`
- `personal/claude-home/hooks/charter-personal.py:16`: `PKG_DIR` defaults to `~/Projects/charter`
- `bin/charter-pkg:547`: `fleet --root` defaults to `~/Projects`

## Workaround

Pass the checkout explicitly (`python3 ~/dev/charter/bin/charter-pkg ...`), set `CHARTER_PKG_DIR=~/dev/charter`, and run `fleet --root ~/dev` as well as the default.

## Suggested fix

Settle on one checkout and remove or archive the other. Have `fleet` scan both `~/Projects` and `~/dev`, or read its roots from a list, and have the hook and the skill derive the package directory from the skill's own symlink target instead of hard-coding a path.
