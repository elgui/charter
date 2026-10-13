# The owner's delegate (0.4.14)

The owner asked on 2026-10-12 to stop being handed basic owner commits and merges, and to keep only the ones that deserve him (reported in `~/.claude/MEMORY/WORK/20261012-073000_owner-delegate-sonnet-watcher/PRD.md`). He ruled the shape on 2026-10-13, on the Crossroads page `owner-delegate-levels-20261013`: strict by default, levels below it that only he sets, the level kept in the committed config, a watcher outside Claude Code, merges by that watcher, infrastructure always his (operator report, 2026-10-13). This document is how it is built. It supersedes the tele-claude decision `owner-acts-tiered-delegate-review` (`~/Projects/tele-claude/charter/decisions/owner-acts-tiered-delegate-review.md`), which chose codex as the reviewer and the tele-claude service as the runner and was never built.

## Levels

`delegate.level` in `charter/config.json` is one of four levels, strictest first (`DELEGATE_LEVELS` and `LEVEL_KINDS` in `package/.charter/lib.py`). Each adds to the one before it:

| Level | The delegate may take | Kind names (`package/.charter/lib.py:227`) |
|---|---|---|
| `strict` (no key) | nothing: every owner act goes to the owner, as before 0.4.14 | none (`package/.charter/lib.py:227`) |
| `routine` | closing an `— owner: check` line whose probe passes when the watcher reruns it; an upgrade's settings change exactly as the installer writes it | `owner-check`, `upgrade` (`package/.charter/lib.py:227`) |
| `answers` | also the owner's own answer, transcribed: `charter rule`, `approve`, `rail` | `ruling` (`package/.charter/lib.py:227`) |
| `open` | also an agent's edit of `charter/rails.md` or `charter/scope.md`, and a merge of the owner's own reviewed PR | `rails`, `scope`, `merge` (`package/.charter/lib.py:227`) |

Every other owner act is `structural`, which no level delegates (`owner_act_kinds` in `package/.charter/checks.py`): `charter/config.json` (so the level itself), `.charter/**`, any other settings change, charter's CI workflow, `legacy-taskets.txt`, a change request's or a decision's ruled fields edited by hand, a `kind: split` unit, a `— owner: do` or `decide` line, a reworded, removed or unmarked owner line, anything that sets `CHARTER_OWNER`. An `— owner: check` close is `owner-check` only when the one open line of that key is ticked and its words and probe are unchanged (`owner_line_kinds` in `package/.charter/checks.py`). An upgrade's settings change is `upgrade` only when it equals `merge_settings(HEAD's settings, fragment)` and the fragment, `.charter/settings-fragment.json`, matches the staged manifest (`settings_installer_exact`, `staged_fragment` in `package/.charter/checks.py`; the installer and the classifier share `merge_settings` in `package/.charter/lib.py`).

## Where the level is read

Only the owner sets the level, so it is read from what is committed, never the working tree (`delegate_level` in `package/.charter/lib.py`):

- the config committed on the default branch decides: the branch `origin/HEAD` names, else `main`, else `master`; no key there is `strict` (`package/.charter/lib.py:244`, `package/.charter/lib.py:277`);
- the checkout's own branch counts only when its committed config names a level, and then only to make it stricter, so a branch made before the owner set the level inherits it (`package/.charter/lib.py:277`);
- a value that is not a level, or a config that does not parse, reads as `strict` and is reported as a problem (`package/.charter/lib.py:256`).

The seeded `package/charter/config.json` names no level, on purpose: an explicit `strict` on every branch would narrow each of them below the level the owner later sets on main.

The owner sets it with `charter delegate level <name>` (refused inside Claude Code without the owner switch), or for the fleet with one line, `CHARTER_OWNER=1 python3 <checkout>/bin/charter-pkg fleet --levels NAME=LEVEL,... [--owner NAME=VALUE]`, which commits once per repository on its default branch (`set_config` in `package/.charter/delegate.py`, `do_fleet_levels` in `bin/charter-pkg`). Where no checkout has the default branch, the commit is written onto it with git's plumbing and every checkout is left as it is. A default branch not yet on 0.4.14 is refused, because an older engine reads the new key as a config problem (`config_from` in `package/.charter/lib.py`). `charter owner --json` carries the level and the command that sets it, for the owner desk (`report` in `package/.charter/owner.py`).

## The session's side

- `charter handover` records each owner-only path's kinds, the level, whether the delegate may take it, and an id (`record_handover` in `package/.charter/lib.py`). Where it may, the block says the delegate takes it and still ends with the owner's line, as the fallback; recording the same staged content again keeps the id.
- `charter handover --ask rule|approve|rail TARGET STATUS --quote "..."` records the owner's own answer, with the session (`CLAUDE_CODE_SESSION_ID`), for the delegate to transcribe (`record_ask` in `package/.charter/delegate.py`). It is refused below `answers`, with a quote under 12 characters, and when the verb would refuse it now (a dry run of the verb).
- `charter handover --merge N [--method merge|squash|rebase]` asks for a merge, refused below `open` (`package/.charter/delegate.py:307`).
- `--wait [--timeout S]` waits for the verdict (default 300 s): exit 0 when the delegate acted, 3 when it handed the item back, 4 when it did not answer; each but 0 ends with the owner's fallback line (`wait` in `package/.charter/delegate.py`).
- The edit gate lets through an edit whose kinds the level delegates, with a note; an edit whose result cannot be computed is denied at every level (`package/.charter/hooks/pre_tool_gate.py`). The commit gate is unchanged: inside Claude Code an owner-only commit is refused without the switch, so the agent hands it over.

The records live in the worktree's own git directory, `<git dir>/charter/`: `handover.json`, `asks/<id>.json`, `merges/<pr>.json`, and the verdicts in `delegate/<id>.json` (`delegate_dir` in `package/.charter/lib.py`).

## The watcher

`bin/charter-delegate run`, from cron each minute, outside Claude Code (`bin/charter-delegate`):

1. Lists every worktree of every charter project under `~/Projects` and `~/AI_tooling/PAI` (`git worktree list --porcelain`), and in each one the items that have no verdict, reading the records directly. A handover recorded where the level delegated nothing is not among them, so a `strict` project is never touched.
2. Asks that checkout's engine for its plan, `charter delegate plan --json`: each item's kinds recomputed now, the level, whether the rules allow it and why not, the staged diff, the closed lines' probes, the unit text (`package/.charter/delegate.py:242`).
3. Hands back, by the rules and without calling the judge, an item the plan does not allow, or whose staged blobs moved since the handover (in the index or the tree), or a ruling whose quote it cannot find in a message the owner typed in that session (`bin/charter-delegate:386`).
4. Asks the judge, Claude Sonnet, with no tools, no settings, no CLAUDE.md, a budget cap and a schema: `claude -p --model sonnet --safe-mode --tools "" --setting-sources "" --strict-mcp-config --no-session-persistence --output-format json --max-budget-usd 0.50 --system-prompt ... --json-schema ...`, from a neutral directory, with the agent marker and the owner switch taken out of its environment (`judge` in `bin/charter-delegate`). One such call from a cron-like environment (`env -i HOME=... PATH=...`) on 2026-10-13 took 5 s and cost $0.011, saw no CLAUDE.md and had only the structured-output tool (operator report, 2026-10-13). Any failure of the judge is a hand-back, never a commit.
5. Acts: reruns the probes of the closed `— owner: check` lines when the judge found them safe (timeout `probes.timeout_s`, scrubbed environment), then `charter delegate commit`; `charter delegate perform` for a ruling; `gh pr merge N --<method> --match-head-commit <sha>` for a merge, never `--admin` (`bin/charter-delegate:373`, `bin/charter-delegate:386`).
6. Records a verdict per item (`charter delegate settle`), a line in `~/.local/state/charter-delegate/ledger.jsonl`, and on a hand-back one Telegram message to the owner with the reason and his line (`bin/charter-delegate:343`, `bin/charter-delegate:293`, `package/.charter/delegate.py:101`).

`charter-delegate digest --since 24 --push` sends the owner what the delegate did, each act with its revert line, once a day (`bin/charter-delegate:494`). `charter-delegate status` prints the cron lines, the last run and what waits.

The delegate's commit: exactly the recorded blobs, the recorded message, the owner as author (git's user, so charter's CI owner check passes, `check_owner_commits` in `package/.charter/checks.py`), `charter delegate <charter-delegate@localhost>` as committer, and a trailer `Charter-Delegate: level <level>; judged by <model>; <id>` (`commit` in `package/.charter/delegate.py`, `DELEGATE_COMMITTER` in `package/.charter/lib.py`). A ruling goes through the owner's own verb with the same committer and no owner switch, and its `## Ruling` line quotes the owner's words (`perform`, `_ruling_note`). The verdict lives in the git directory, so `--wait` and `charter owner` read it.

## Merges

A merge is delegated at `open` only, and only when all of these hold (`check_pr` in `bin/charter-delegate`):

- the PR was opened from the owner's GitHub account (`gh api user`): a collaborator's PR waits for the owner's approval, as leCRM's REVIEW ruleset requires (`scripts/github/merge-rules.sh` in leCRM; `bin/charter-delegate:244`);
- it targets the default branch, is open and not a draft, and GitHub reports it `CLEAN`; the delegate never updates a branch or bypasses a rule (`bin/charter-delegate:244`);
- every check is `SUCCESS`, `NEUTRAL` or `SKIPPED`, and there is at least one (`bin/charter-delegate:244`);
- it changes no CI workflow, `.charter/`, `charter/config.json` or settings file (`PROTECTED_IN_PR` in `bin/charter-delegate`);
- a comment from the owner's account carries `<!-- charter-review: pass sha=<head> -->` for the PR's current head, which `/reviewPR` posts; a push after the review voids it (`MARK_RE` in `bin/charter-delegate`);
- the judge agrees.

A request whose checks still run, or whose merge state GitHub has not computed yet, is looked at again on each run and handed back only after 30 minutes (`PENDING_GRACE_S`, `bin/charter-delegate:245`).

## Infrastructure

OVH, Cloudflare, Dokku server administration, server work on the five machines and GitHub repository settings are not commits, so charter never sees them. They stay the owner's at every level through each skill's own rules and one `autoMode.soft_deny` rule in `~/.claude/settings.json` (operator report, 2026-10-13).

## What this cannot do

The delegate runs as the same Unix user as the agents. What keeps an agent from acting as the delegate is lexical, as for the owner switch (issues #2 and #12, https://github.com/elgui/charter/issues/12):

- the delegate's acts refuse when `CLAUDECODE=1` (`refuse_in_session` in `package/.charter/delegate.py`), and charter's hook denies a command that unsets it;
- the hook denies `charter delegate commit|perform|settle|level <name>` and `charter-delegate run` (`DELEGATE_ACT_RE` in `package/.charter/hooks/chain_gate.py`);
- an `autoMode.soft_deny` rule names forging a verdict or running the delegate by hand (`~/.claude/settings.json:343`).

The quote check is lexical too (`typed_texts` in `bin/charter-delegate`): it keeps transcript entries whose `origin.kind` is `human`, drops tool results, `isMeta` and sidechain entries, entries carrying a relay or notification marker, and text pasted into the prompt, except a Crossroads answer block. A message typed into a session through `tmux send-keys` reads as the owner's. The probes the watcher reruns are commands an agent wrote, run as the owner outside the classifier: the judge must call them safe first, they run with the project's timeout in a scrubbed environment, and they are the reason `routine` exists as a level the owner chooses.

## Tests

`tests/test_delegate_0_4_14.py` (the package: levels, kinds, handover, the delegate's acts, the edit gate, the hook, `fleet --levels`) and `tests/test_delegate_watcher.py` (the watcher, with a stub judge and a stub `gh`).
