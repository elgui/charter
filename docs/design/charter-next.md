# `charter next` and the orientation split

This note explains why `charter next` exists, what it reads, and how it relates to the personal NowWhat skill. The command was built in package 0.4.4, on branch `charter-0.4.4` (commit b3cdd55). The owner chose this direction on 2026-09-24 (operator report, 2026-09-24).

## The question

NowWhat is a personal skill (`~/.claude/Skills/NowWhat`, source in the PAI_generic repository). It gives a fast, read-only orientation for any project: the roadmap, the taskets, git, pull requests, CI and automation runs. It ranks three next moves and keeps a journal in the gitignored `.nowwhat/`. The owner asked how it should work in a project that runs charter. Such a project already records its road (`charter/rails.md`), its units and their evidence, and the proposals waiting on the owner.

## What the NowWhat runs showed (2026-09-24)

- **No file of the skill mentions charter** (`$ grep -rli charter ~/.claude/Skills/NowWhat/ | wc -l` gives 0). Each run decided for itself where the road was. The skill-delivery run of 2026-09-24T16:30Z took `charter/rails.md` as its source (`~/Projects/skill-delivery/.nowwhat/journal.jsonl`). tcv2's runs of 2026-09-16 still took the docs roadmap (`~/Projects/tcv2/.nowwhat/journal.jsonl`).
- **It guesses links that charter computes exactly.** NowWhat links roadmap items to work by explicit reference, shared files, then slug similarity (`~/.claude/Skills/NowWhat/workflows/Rails.md:44-48`). Charter's `rails_of` is exact: `rail:`, a `roadmap:` anchor, or a `groups` glob (`package/.charter/rails.py:108`).
- **Pre-charter units read as unfinished work.** In skill-delivery, all 17 units under "Done but not accepted" predate charter; with 0.4.4 they move to "Done before charter" (`$ python3 package/.charter/bin/charter --root ~/Projects/skill-delivery synth`).
- **Its own journal reached the gate log.** leCRM's log holds a perimeter warning for `.nowwhat/briefs/20260914-1640.md`, dated 2026-09-14T16:38:43 (`$ grep nowwhat ~/Projects/leCRM/.git/charter/log.jsonl`).

## The decision

- **One option was rejected:** teaching NowWhat to read charter itself. It would carry a charter path next to its current one, with a table of what each installed version supports. The owner found that too heavy (operator report, 2026-09-24).
- **Another option was rejected:** moving all of NowWhat into charter. The package is copied into every project, client ones included, and never references the personal layer (`docs/method.md` § Where the personal layer stops). NowWhat's most useful checks are specific to this machine: abandoned `auto/` worktrees, automator runs, pull requests. So is its journal of stated next moves.
- **The split that was kept:** charter owns the read of the project's own files, as one tested, read-only command, `charter next` (`cmd_next` in `package/.charter/bin/charter`). The owner chose "`charter next` only, for now" (operator report, 2026-09-24). Once `charter next` has been used for a while, a small section in NowWhat can call it instead of re-deriving the road. Until then, NowWhat is unchanged.
- **The owner's answers for when NowWhat is revisited:** NowWhat edits go directly on PAI_generic's master branch, and small charter fixes ride along with the next release, which 0.4.4 is (operator report, 2026-09-24).
- **The `.nowwhat/` noise is fixed on charter's side only,** by the perimeter gate skipping files git ignores (`lib.ignored` in `package/.charter/lib.py`).

## What 0.4.4 built

| Piece | Where | Why |
|---|---|---|
| `charter next` | `cmd_next` in `package/.charter/bin/charter` | Active unit, open rails with their units, next units in road order, units off the road, what waits on the owner, gate log over 7 days. It writes nothing, not even the gate log |
| Done before charter | `_done_before_charter` and `_unit_state` in `package/.charter/bin/charter` | The synthesis lists units the done gate never judged apart from "Done but not accepted" |
| Perimeter skips ignored files | `check_perimeter` in `package/.charter/checks.py` | A tool's local journal is not a unit's work |
| Unreadable evidence path | `_exists` in `package/.charter/checks.py` | leCRM's synthesis crashed on a path under `/root`, with 0.3.0 and 0.4.3 alike (`$ python3 .charter/bin/charter synth` in `~/Projects/leCRM`) |
| Tests | `tests/test_next_0_4_4.py` | 19 tests: 16 fail on 0.4.3, and 3 guards pass there too |

The legacy list alone did not catch pre-charter units. 77 of karaokay's 79 pre-charter units carry `## Acceptance Criteria`, so the installer never listed them (`is_charter_unit` in `package/.charter/lib.py`). The rule therefore also covers any unit whose done status was committed before the commit that added `charter/VERSION`, and not reopened since. With it, the pre-charter units counted apart are 17 in skill-delivery, 79 in karaokay and 171 in leCRM (`$ python3 package/.charter/bin/charter --root ~/Projects/<project> next`).

## Commands a read-only tool may call

For NowWhat or any other tool that must not change a project (`package/.charter/bin/charter`, 0.4.4):

| Safe | Not safe, and why |
|---|---|
| `version`, `config`, `next`, `synth` without `--write`, `log`, `unit show` (it only creates `.git/charter/`) | `check --all` runs each decision's `check:` shell command and writes to the gate log (`package/.claude/rules/charter.md:15`) |
| `bin/charter-pkg status <project>`, from this repository | `probe` runs the probes and logs them; `anchors` logs too; `synth --write`, `ledger`, `unit start` and `unit stop`, `setup` and `decisions index` all write |

`charter config` exists from 0.4.3, and `charter next` from 0.4.4. On 2026-09-24 the four projects on this machine ran 0.3.0 or 0.4.0 on their main lines (`$ cat ~/Projects/*/charter/VERSION`).
