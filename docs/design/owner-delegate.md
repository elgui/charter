# The owner's delegate (0.4.14)

The owner asked on 2026-10-12 to stop being handed basic owner commits and merges, and to keep only the ones that deserve him (reported in `~/.claude/MEMORY/WORK/20261012-073000_owner-delegate-sonnet-watcher/PRD.md`). He ruled the shape on 2026-10-13, on the Crossroads page `owner-delegate-levels-20261013`: strict by default, levels below it that only he sets, the level kept in the committed config, a watcher outside Claude Code, merges by that watcher, infrastructure always his (operator report, 2026-10-13). This document is how it is built. It supersedes the tele-claude decision `owner-acts-tiered-delegate-review` (`~/Projects/tele-claude/charter/decisions/owner-acts-tiered-delegate-review.md`), which chose codex as the reviewer and the tele-claude service as the runner and was never built.

An independent review of the first build found four ways to defeat its guarantees and five smaller issues (https://github.com/elgui/charter/pull/17#issuecomment-6145352619), and a `/reviewPR` pass on the fixes found five more (codex, 2026-10-13: commits 4983f7d to 2f4f6c8). A second `/reviewPR` pass, after 0.4.15 was merged in, found six more, fixed one commit each (codex, 2026-10-14: commits 43ab704 to 8796d30), and three it filed (issues #21 to #23, https://github.com/elgui/charter/issues/21). Each is fixed below, and each has a regression test in `tests/test_delegate_0_4_14.py` (`Review20261013`) or `tests/test_delegate_watcher.py`. The owner chose where the level is anchored, and that probes stay judge-checked (operator report, 2026-10-13).

## Levels

`delegate.level` in `charter/config.json` is one of four levels, strictest first (`DELEGATE_LEVELS` and `LEVEL_KINDS` in `package/.charter/lib.py`). Each adds to the one before it:

| Level | The delegate may take | Kind names (`LEVEL_KINDS` in `package/.charter/lib.py`) |
|---|---|---|
| `strict` (no key) | nothing: every owner act goes to the owner, as before 0.4.14 | none (`LEVEL_KINDS` in `package/.charter/lib.py`) |
| `routine` | closing an `— owner: check` line whose probe passes when the watcher reruns it; an upgrade's settings change exactly as the installer writes it | `owner-check`, `upgrade` (`LEVEL_KINDS` in `package/.charter/lib.py`) |
| `answers` | also the owner's own answer, transcribed: `charter rule`, `approve`, `rail` | `ruling` (`LEVEL_KINDS` in `package/.charter/lib.py`) |
| `open` | also an agent's edit of `charter/rails.md` or `charter/scope.md`, and a merge of the owner's own reviewed PR | `rails`, `scope`, `merge` (`LEVEL_KINDS` in `package/.charter/lib.py`) |

Every other owner act is `structural`, which no level delegates (`owner_act_kinds` in `package/.charter/checks.py`): `charter/config.json` (so the level itself), `.charter/**`, any other settings change, charter's CI workflow, `legacy-taskets.txt`, a change request's or a decision's ruled fields edited by hand, a `kind: split` unit, a `— owner: do` or `decide` line, a reworded, removed or unmarked owner line, anything that sets `CHARTER_OWNER`. An `— owner: check` close is `owner-check` only when the one open line of that key is ticked and its words and probe are unchanged (`owner_line_kinds` in `package/.charter/checks.py`), and the delegate takes it only when its probe does more than print: a probe that is only `echo`, `printf`, `true` or `:` is a check the owner makes by hand, and goes to him (`MANUAL_PROBE_RE` in `package/.charter/delegate.py`). An upgrade's settings change is `upgrade` only when it equals `merge_settings(HEAD's settings, fragment)` and the staged `.charter/settings-fragment.json` is byte for byte the fragment that ships with the engine doing the classing (`staged_fragment` in `package/.charter/checks.py`). The watcher's engine is the charter checkout's own, so a fragment an agent staged, even with a manifest that vouches for it, never makes a settings change an `upgrade` (review item 4).

## Where the level is read

Only the owner sets the level, and a level an agent could raise with plain git is no level (review item 2: `git update-ref refs/heads/main` or `git symbolic-ref refs/remotes/origin/HEAD` set it to `open` without a commit). So the level the watcher acts on is the stricter of two readings (`delegate_level` in `package/.charter/lib.py`, `github_level` in `bin/charter-delegate`):

- **On GitHub.** The config committed on the repository's default branch on GitHub, which only a push changes. The watcher reads it each run with `gh api` (`github_level` in `bin/charter-delegate`) and passes it to the engine as `--cap` (`cmd_delegate` in `package/.charter/bin/charter`). A level set on the local main counts once that main is pushed; a stricter level counts at once, since the stricter reading wins. GitHub unreachable: the items wait, and go to the owner after 30 minutes (`PENDING_GRACE_S` in `bin/charter-delegate`).
- **Locally.** The config committed on the local default branch (the branch `origin/HEAD` names, else `main`, else `master`; no key there is `strict`), and the checkout's own branch only when its committed config names a level, and then only to make it stricter, so a branch made before the owner set the level inherits it (`_local_level` in `package/.charter/lib.py`). A value that is not a level, a `delegate` that is not an object, or a config that does not parse reads as `strict` and is reported as a problem (`committed_level` in `package/.charter/lib.py`). So does a config with any problem the gates block on, such as an unknown key or a value of the wrong type: `charter check` refuses it, so it delegates nothing, on GitHub as here (`config_from`, `committed_level` in `package/.charter/lib.py`; `github_level` in `bin/charter-delegate`).

The GitHub repository is the one `origin` named when the watcher first saw the project, pinned in `~/.local/state/charter-delegate/repos.json`, so changing or removing `origin` later moves nothing (`slug_of` in `bin/charter-delegate`). The owner pins the fleet once with `charter-delegate pins --record`, which lists each project's repository and both readings (`cmd_pins` in `bin/charter-delegate`). A project with no GitHub remote has only the local reading: the owner ruled that such a project is not critical (operator report, 2026-10-13). The session's own reads (the handover block, the edit gate, `--ask`, `--merge`) have no cap: they are advisory, and the watcher decides.

The seeded `package/charter/config.json` names no level, on purpose: an explicit `strict` on every branch would narrow each of them below the level the owner later sets on main.

The owner sets it with `charter delegate level <name>` (refused inside Claude Code without the owner switch), or for the fleet with one line, `CHARTER_OWNER=1 python3 <checkout>/bin/charter-pkg fleet --levels NAME=LEVEL,... [--owner NAME=VALUE]`, which commits once per repository on its default branch (`set_config` in `package/.charter/delegate.py`, `do_fleet_levels` in `bin/charter-pkg`); the owner then pushes that branch, and the watcher reads it from GitHub. Where no checkout has the default branch, the commit is written onto it with git's plumbing and every checkout is left as it is. A default branch not yet on 0.4.16, the first release that carries the delegate, is refused, because an older engine reads the new key as a config problem (`DELEGATE_SINCE` in `bin/charter-pkg`, `config_from` in `package/.charter/lib.py`). `charter owner --json` carries the local level and the command that sets it, for the owner desk (`report` in `package/.charter/owner.py`).

## The session's side

- `charter handover` records each owner-only path's kinds, its staged blob and mode, the level, whether the delegate may take it, and an id (`record_handover` in `package/.charter/lib.py`). It lists what is staged without rename detection, so a rename hands over its removal too (review item 9). Where the delegate may take it, the block says so and still ends with the owner's line, as the fallback; recording the same staged content again keeps the id.
- `charter handover --ask rule|approve|rail TARGET STATUS --quote "..."` records the owner's own answer for the delegate to transcribe, with the session the command runs in, `CLAUDE_CODE_SESSION_ID`; there is no flag to name another (`record_ask` in `package/.charter/delegate.py`). It is refused below `answers`, with a quote under 12 characters, when the verb would refuse it now (a dry run of the verb), and for a `rule <decision> active` whose decision has a `check:`, since that command runs as the ruling is made and its proposer wrote it (`_check_of` in `package/.charter/delegate.py`).
- `charter handover --merge N [--method merge|squash|rebase]` asks for a merge, refused below `open` (`record_merge` in `package/.charter/delegate.py`).
- `--wait [--timeout S]` waits for the verdict (default 300 s): exit 0 when the delegate acted, 3 when it handed the item back, 4 when it did not answer; each but 0 ends with the owner's fallback line (`wait` in `package/.charter/delegate.py`).
- The edit gate lets through an edit whose kinds the level delegates, with a note; an edit whose result cannot be computed is denied at every level (`package/.charter/hooks/pre_tool_gate.py`). The commit gate is unchanged: inside Claude Code an owner-only commit is refused without the switch, so the agent hands it over.

The records live in the worktree's own git directory, `<git dir>/charter/`: `handover.json`, `asks/<id>.json`, `merges/<pr>.json`, and the verdicts in `delegate/<id>.json` (`delegate_dir` in `package/.charter/lib.py`).

## The watcher

`bin/charter-delegate run`, from cron each minute, outside Claude Code (`cmd_run` in `bin/charter-delegate`). Nothing it runs comes from a project (review item 3):

- the engine is its own checkout's, `package/.charter/bin/charter`, run with `--root <worktree>`, never the worktree's `.charter/bin/charter` (`engine` in `bin/charter-delegate`);
- git runs with no hook, no fsmonitor and no signing program, and every filter and diff driver the project's config names made inert, set from the environment above the project's config (`git_config_env` in `bin/charter-delegate`, `SAFE_GIT` in `package/.charter/delegate.py`); the staged view the commit gate reads is written from the blobs, with no checkout (`index_view` in `package/.charter/lib.py`);
- git, gh and claude are named by absolute path, and the engine's `PATH` holds only system directories (`GIT`, `GH`, `CLAUDE`, `SAFE_PATH` in `bin/charter-delegate`);
- it looks only at worktrees that lie under its roots (`checkouts` in `bin/charter-delegate`);
- it acts only while its own checkout is on main with no uncommitted change under `bin/` or `package/`, else a run is a dry run (`own_checkout_problem` in `bin/charter-delegate`).

Each run:

1. Lists every worktree of every charter project under `~/Projects` and `~/AI_tooling/PAI`, and in each one the items that have no verdict, reading the records directly. A handover recorded where the level delegated nothing is not among them, so a `strict` project is never touched.
2. Reads the project's level on GitHub, then asks the engine for its plan, `charter delegate plan --json --cap <level>`: each item's kinds recomputed now, the level, whether the rules allow it and why not, the staged diff, the closed lines' probes, the unit text (`plan` in `package/.charter/delegate.py`).
3. Hands back, by the rules and without calling the judge, an item the plan does not allow: the level keeps it, the index no longer holds what was recorded, a symlink, a submodule or an owner-only mode change is among it, a probe only prints, or a field is longer than the 60 KB the plan carries (`_plan_commit`, `DIFF_CAP` in `package/.charter/delegate.py`); a ruling whose quote is not the owner's (below); a payload over 180,000 characters as a whole (`JUDGE_CAP` in `bin/charter-delegate`). A payload is never cut for the judge (review item 6).
4. Waits, without calling the judge, while another git process holds the index (`index_busy` in `bin/charter-delegate`).
5. Asks the judge, Claude Sonnet, with no tools, no settings, no CLAUDE.md, a budget cap and a schema: `claude -p --model sonnet --safe-mode --tools "" --setting-sources "" --strict-mcp-config --no-session-persistence --output-format json --max-budget-usd 0.50 --system-prompt ... --json-schema ...`, from a neutral directory, with the agent marker and the owner switch taken out of its environment (`judge` in `bin/charter-delegate`). The level, kinds and probes come first in its payload, the diff last. One such call from a cron-like environment (`env -i HOME=... PATH=...`) on 2026-10-13 took 5 s and cost $0.011, saw no CLAUDE.md and had only the structured-output tool (operator report, 2026-10-13). Any failure of the judge is a hand-back, never a commit. A verdict is kept per item and payload, so an act that waits for its next run does not ask again; a dry run keeps none, since a session may run one with a judge of its own choosing.
6. Acts: reruns the probes of the closed `— owner: check` lines when the judge found them safe (timeout `probes.timeout_s`, a scrubbed environment with a `HOME` of their own), then `charter delegate commit`; `charter delegate perform` for a ruling; `gh pr merge N -R <repository> --<method> --match-head-commit <sha>` for a merge, never `--admin` (`handle`, `run_probes`, `probe_env` in `bin/charter-delegate`).
7. Records a verdict per item (`charter delegate settle`), a line in `~/.local/state/charter-delegate/ledger.jsonl`, and on a hand-back one Telegram message to the owner with the reason and his line (`hand_back`, `notify` in `bin/charter-delegate`; `settle` in `package/.charter/delegate.py`).

`charter-delegate digest --since 24 --push` sends the owner what the delegate did, each act with its revert line, once a day (`cmd_digest` in `bin/charter-delegate`). `charter-delegate status` prints the cron lines, the last run and what waits.

### The owner's words

A ruling is transcribed only from words the owner typed (`find_quote`, `typed_texts`, `says` in `bin/charter-delegate`; review item 5):

- the transcript entry carries `origin.kind` `human`, which Claude Code writes on a typed prompt; an entry without it is not the owner's (a survey of the 60 latest transcripts on 2026-10-13 found it on every typed prompt, and missing on `-p` script prompts, `!` command echoes and interrupt markers: operator report, 2026-10-13; `typed_texts` in `bin/charter-delegate`);
- tool results, `isMeta` and sidechain entries, entries carrying a relay or notification marker, and text pasted into the prompt are dropped, except a Crossroads answer block (`RELAY_MARKERS`, `PASTE_RE` in `bin/charter-delegate`);
- the quote is a whole line of that message, or the whole message, once spacing, case, list bullets and the punctuation around it are set aside: a phrase picked out of a longer line ("no: I did not say …") is not an answer (`says`, `norm` in `bin/charter-delegate`);
- the message was typed in the day before the ask was recorded, in the session the ask was recorded from (`QUOTE_WINDOW_S`, `find_quote` in `bin/charter-delegate`);
- the judge reads the message and the assistant's words just before it, and hands back any ambiguity (`SYSTEM` in `bin/charter-delegate`).

### The delegate's commit

Exactly the recorded blobs and modes, built in a private index: `read-tree HEAD`, the recorded entries through `update-index --index-info`, then the commit gate of the delegate's own engine on that index (`charter check --staged --no-probe`, the probes having just been rerun), `write-tree`, a check that the tree changes no path outside the record, `commit-tree --no-gpg-sign`, and `update-ref HEAD <new> <old>`, which refuses if HEAD moved (`write_commit` in `package/.charter/delegate.py`). The index must still hold what was recorded; the working tree is never read, so an edit made there after the handover stays uncommitted. No pathspec is involved, so a staged file named `charter/config.json*` cannot sweep `charter/config.json` in (review item 1). The commit carries the recorded message, the owner as author (git's user, so charter's CI owner check passes, `check_owner_commits` in `package/.charter/checks.py`), `charter delegate <charter-delegate@localhost>` as committer, and a trailer `Charter-Delegate: level <level>; judged by <model>; <id>` (`commit` in `package/.charter/delegate.py`, `DELEGATE_COMMITTER` in `package/.charter/lib.py`).

A ruling goes through the owner's own verb with the same committer and no owner switch: the verb computes the new texts, and they are committed the same way, then written to the tree and the index (`_delegate_commit` in `package/.charter/owner.py`); its `## Ruling` line quotes the owner's words (`perform`, `_ruling_note` in `package/.charter/delegate.py`). The owner's own commits take literal paths too (`_commit` in `package/.charter/owner.py`, `_owner_commit` in `package/.charter/bin/charter`). The verdict lives in the git directory, so `--wait` and `charter owner` read it.

## Merges

A merge is delegated at `open` only, and only when all of these hold (`check_pr` in `bin/charter-delegate`; review item 8):

- the project has a GitHub repository, the one pinned for it, and every `gh` call names it with `-R` from a neutral directory (`check_pr`, `neutral` in `bin/charter-delegate`);
- the PR was opened from the owner's GitHub account (`gh api user`): a collaborator's PR waits for the owner's approval, as leCRM's REVIEW ruleset requires (`scripts/github/merge-rules.sh` in leCRM; `check_pr` in `bin/charter-delegate`);
- it targets the repository's default branch as GitHub reports it, is open and not a draft, and GitHub reports it `CLEAN`; the delegate never updates a branch or bypasses a rule (`check_pr` in `bin/charter-delegate`);
- every check is `SUCCESS`, `NEUTRAL` or `SKIPPED`, and at least one is `SUCCESS` (`check_pr` in `bin/charter-delegate`);
- GitHub lists every changed file (`pulls/<n>/files`, paginated, against `changedFiles`), a renamed file under both its names, and none is under `.github/`, `.charter/` or `.claude/`, nor `charter/config.json` or `charter/legacy-taskets.txt`, nor an owner-only change by the engine's own rule, read at the PR's base and head, with the done statuses the base's `charter/config.json` names, plus `done` (`base_done_statuses` in `bin/charter-delegate`); a file GitHub will not give at either end (a failed request, or one over 1 MB, which the contents API serves without its content) hands the merge back (`PROTECTED_IN_PR`, `pr_owner_only` in `bin/charter-delegate`); `charter/rails.md` and `charter/scope.md` are delegated at `open`;
- the method is `merge`, `squash` or `rebase`, checked again here since the request is a file a session can write; a request that names none takes the repository's default, and a lookup of it that fails hands the merge back (`merge_method` in `bin/charter-delegate`);
- a comment from the owner's account carries `<!-- charter-review: pass sha=<head> -->` for the PR's current head, which `/reviewPR` posts; a push after the review voids it (`MARK_RE` in `bin/charter-delegate`);
- the diff was fetched, carries one `diff --git` header per changed file, is short enough for the judge to read whole, and the judge agrees (`check_pr`, `judge` in `bin/charter-delegate`).

A request whose checks still run, or whose merge state GitHub has not computed yet, is looked at again on each run and handed back only after 30 minutes (`PENDING_GRACE_S` in `bin/charter-delegate`).

The ledger and the digest give a merge the revert line its method needs: `-m 1` for a merge commit, a plain revert for a squash, a revert PR for a rebase. The merge's commit is the one GitHub gives, never the PR's head; when GitHub gives none, the revert line says how to look it up (`revert_line`, `handle` in `bin/charter-delegate`).

## Infrastructure

OVH, Cloudflare, Dokku server administration, server work on the five machines and GitHub repository settings are not commits, so charter never sees them. They stay the owner's at every level through each skill's own rules and one `autoMode.soft_deny` rule in `~/.claude/settings.json` (operator report, 2026-10-13).

## What this cannot do

The delegate runs as the same Unix user as the agents, and the agents use the owner's git and GitHub credentials. What keeps an agent from acting as the delegate, or from widening what it may do, is lexical, as for the owner switch (issues #2 and #12, https://github.com/elgui/charter/issues/12):

- the delegate's acts refuse when `CLAUDECODE=1` (`refuse_in_session` in `package/.charter/delegate.py`), and charter's hook denies a command that unsets it;
- the hook denies `charter delegate commit|perform|settle|level <name>`, `charter-delegate run` and `charter-pkg fleet --levels` in any abbreviation argparse takes (`--dry-run` aside; a session started with the owner switch passes the installer's own refusal, /reviewPR of #17, 2026-10-14), read word by word, so a commit message or a grep that names them passes and a wrapper, `sh -c`, `eval` or a command substitution does not hide them (`delegate_act` in `package/.charter/hooks/chain_gate.py`);
- an `autoMode.soft_deny` rule names forging a verdict, running the delegate by hand, and writing its records or its state (`~/.claude/settings.json`, rule "Owner Delegate Forgery").

What remains open, by kind:

- **The level.** The GitHub reading rests on the default branch on GitHub, which only a push changes; but an agent can push, and 10 of the 11 fleet repositories had no ruleset on their default branch on 2026-10-13 (`$ gh api repos/elgui/<repo>/rulesets`; only leCRM has one). A pushed config change, or a pull request merged with the owner's `gh` token, raises it. Pushing to the main line and merging are the owner's call by charter's rules (`package/.claude/rules/charter.md`), and a ruleset that requires a pull request on each default branch would make a push refused by GitHub itself; setting one is repository settings, the owner's. A project with no GitHub remote has only the local reading, which plain git moves. The pins file is the owner's file in the owner's state directory, which the agent's user can write.
- **The watcher's own code.** It runs from the owner's charter checkout, which the agent's user can write. It acts only from main with no uncommitted change under `bin/` or `package/`, which catches a session that switched the checkout to a branch; a commit on main, or a moved main, is not caught.
- **The owner's words.** Transcripts are files the agent's user can write, `CLAUDE_CODE_SESSION_ID` is an environment variable a command can set, and a message typed into a session through `tmux send-keys` reads as the owner's (`typed_texts`, `find_quote` in `bin/charter-delegate`).
- **Probes.** The probes the watcher reruns are commands an agent wrote, run as the owner outside the classifier. The judge must call them safe first, but it reads the command, not the scripts the command runs; they run with the project's timeout, a scrubbed environment and a `HOME` of their own, not in a sandbox. The owner chose this over a sandbox (operator report, 2026-10-13); it is the reason `routine` is a level he chooses project by project.
- **Git.** The watcher defuses the hooks, filters, textconv and fsmonitor of a project's config; another config key that runs a program in a command it uses would not be (`git_config_env` in `bin/charter-delegate`).

## Tests

`tests/test_delegate_0_4_14.py` (the package: levels, kinds, handover, the delegate's acts, the edit gate, the hook, `fleet --levels`, and `Review20261013`, the review's findings turned around) and `tests/test_delegate_watcher.py` (the watcher, with a stub judge and a stub `gh` that plays GitHub).
