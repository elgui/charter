# The owner's commit of an upgrade is handed over as a 17-path command, and the paste fails

- Seen: 2026-10-06, leCRM at its main of that day (reported in the leCRM session as `1372fcb2`), upgrading charter 0.4.8 to 0.4.11 in a worktree (https://github.com/elgui/lecrm/pull/99)
- Status: fixed on branch `owner-line-0.4.12` (charter 0.4.12). Tests: `tests/test_owner_commit_0_4_12.py`; `tests/test_handover_0_4_5.py` follows the new line

## What happened

The upgrade merged hooks into `.claude/settings.json`, an owner-only file, so the installer ended with the 0.4.5 block (operator report from the leCRM session, 2026-10-06):

```
Waiting on the owner: commit 17 staged file(s) on branch charter-0.4.11. The gate refuses this commit to an agent.
  in a Claude Code prompt:  ! CHARTER_OWNER=1 git -C <worktree> commit -m 'charter 0.4.11' -- <17 paths>
```

The commit took three round trips (operator report, 2026-10-06):

1. The agent handed the owner a `bash -euo pipefail <<'EOF'` block, and the owner found pasting it unreliable (operator report, 2026-10-06).
2. The auto-mode classifier refused the agent's own `CHARTER_OWNER=1 git commit`, "judged dangerous", even after the owner wrote "do it yourself". `personal/claude-home/Skills/CharterAdmin/SKILL.md:74` at 0.4.11 said that phrase had been enough on 2026-09-25.
3. A scratchpad script without the switch, run by the owner as `CHARTER_OWNER=1 bash <path>`, worked (operator report, 2026-10-06).

The owner: "I'm tired of copy-pasting blocks, because the copy-paste here is faulty." (operator report, 2026-10-06)

Expected: one short line for the owner, with nothing in it that depends on how a long line or a block survives the paste (operator report, 2026-10-06).

## Reproduce

Upgrade, with `python3 ~/Projects/charter/bin/charter-pkg upgrade <project>`, a project whose `.claude/settings.json` the new release changes. The block's command spells every staged path after `--` (`commit_command` and `handover` in `package/.charter/lib.py` at 0.4.11).

## Where

- `handover` in `package/.charter/lib.py` (0.4.11) composed the block. `cmd_handover` in `package/.charter/bin/charter` and `stage` in `bin/charter-pkg` printed it.
- `do_fleet` in `bin/charter-pkg` (0.4.11) joined one such command per project into a single line.
- `personal/claude-home/Skills/CharterAdmin/SKILL.md:74` (0.4.11) told the agent to copy the block verbatim, and carried the classifier note that 2026-10-06 contradicted.

## Workaround

On a project below 0.4.12, put the `git commit` of the block, without the switch, in a scratchpad script, and hand over `CHARTER_OWNER=1 bash <path>` (operator report, 2026-10-06: step 3 above).

## Fix

0.4.12 (`docs/design/owner-handover.md`). The installer and `charter handover` record the handover in `<git dir>/charter/handover.json` and end with one line, `CHARTER_OWNER=1 python3 <root>/.charter/bin/charter owner commit`. The new verb commits exactly the recorded paths with the recorded message. The switch stays on the owner's line. `charter-pkg fleet --upgrade` ends with one line for every project, `fleet --commit`.
