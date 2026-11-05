# Owner inbox: ask the owner less, and make each ask one tap

Status: **proposed** 2026-09-29, not built. Decided by the owner in a tele-claude session on 2026-09-29 (operator report, 2026-09-29):
- approvals are same-user records, not signed by a separate account (operator report, 2026-09-29);
- changes that only tighten a gate become free, with a warning (operator report, 2026-09-29);
- this document and its taskets come first, and no code (operator report, 2026-09-29).

Brought to `main` on 2026-11-05 from the unmerged branch `owner-inbox-design` (`df6f769`, kept as the local tag `archive/owner-inbox-design`). The text is unchanged except that its line references into `package/.charter/` now point at the same lines in the current files. Its seven taskets, `.taskets/20260929-2000-tightening-is-free.md` to `.taskets/20260929-2006-tele-claude-trial.md`, stayed in that tag: they planned a 0.4.7 release, and the Tasket map below refers to them.

What `main` built instead, after this proposal: an owner queue with verbs (`docs/package.md:110`), a one-line owner commit of a handover (`docs/package.md:114`, `docs/design/owner-handover.md`) and the owner's delegate (`docs/package.md:116`). Part 1 (a change that only tightens a gate is free) and the one-tap Slate inbox of Part 2 remain unbuilt.

## The problem, measured on one session

A tele-claude session on 2026-09-29 filed 15 taskets from a Slate. It then handed the owner four
manual steps (reported in that session's final message). Checked against the gates, only two of them were
owner acts:

| Handed to the owner | Owner-only? | Why |
|---|---|---|
| add `check:` and `binds:` to `api-routes-in-known-api-paths` and `data-path-via-data-dir` | yes | `package/.charter/checks.py:1211` refuses any change to `check`/`binds` of an active decision |
| wire a test suite into the pre-commit hook | yes | `.charter/**` is `OWNER_ONLY_GLOBS` (`package/.charter/checks.py:46-48`) |
| edit an allowlist in another repository | no | outside the tree, so no gate applies (`package/.charter/hooks/pre_tool_gate.py:53-57` returns early for a path outside the tree) |
| raise a group's `group_order` | no | taskets' ordering fields are not owner-only (`package/.charter/checks.py:1177-1229`) |

That gives two findings:
1. **The rules ask for things that cannot hurt** (`package/.charter/checks.py:1211`). Adding a `check:` to a decision that has none makes the gate stricter, yet it is refused.
   - The package already treats that kind of change as free when removing a legacy id: "removing an entry only strengthens the done gate" (`package/.charter/checks.py:1194`).
   - It does the same when narrowing a split unit: "narrowing or closing a split unit is free" (`package/.charter/checks.py:1227`).
2. **When an ask is real, answering it is expensive** (`package/.charter/checks.py:1238-1239`). The override tells the agent to "propose it (a change request, a new decision) and say so", so the owner receives prose in a chat.
   - They then open the file, edit it by hand, and run `! CHARTER_OWNER=1 git commit …` (`package/.charter/lib.py:215-231` at commit `7758bec`, the code the proposal was written against); a batch of four asks means four such round-trips.

<!-- charter: opinion -->

## Part 1: a change that only tightens a gate is free

Apply `owner_only_changes` (`package/.charter/checks.py:1177`) in both edit and commit context, and
extend it so that these changes are no longer owner acts:

| Change | Today | Proposed |
|---|---|---|
| Removing an id from `charter/legacy-taskets.txt` | free | free (unchanged) |
| Narrowing or closing a `kind: split` unit | free | free (unchanged) |
| Adding a `check:` to an active decision that has none | owner | **free, warn** |
| Adding `binds:` paths to an active decision whose `check:` exists, when no path is removed | owner | **free, warn** |
| Changing or removing an existing `check:` | owner | owner (unchanged: it could weaken the check) |
| Removing a `binds:` path | owner | owner (unchanged) |

Why `binds:` is only free when it grows: `binds:` decides when the check runs at commit. Adding a path runs
it more often; removing one runs it less.

Why a new `check:` is free, and the risk that comes with it: a new check can only refuse commits that it would
have refused anyway once the owner adds it. The risk is a check that is **wrong** and blocks good work, which
is loud and cheap to undo. A check that is **weak** passes everything, which is no worse than having no check.
The warn line names the decision, and the next inbox lists it under "done for you, FYI" (Part 2).

## Part 2: the owner inbox

The owner inbox turns "propose it and say so" into a record the owner answers on a Slate page.

```
agent: Edit refused (owner-only)
  → charter propose <path> --from <file> --why "…" --unblocks <tasket-id>
      writes .git/charter/proposals/<id>.json   (the file itself is untouched)
owner: charter inbox --slate  (or the agent runs it)
  → one Slate page, one screen per proposal: diff, why, what it unblocks
  → Approve / Reject / Amend (note) — "Send to session"
relay: records the answer in ~/.crossroads/answers/<page>.json   (behind the Telegram login)
agent: charter apply <page>
  → verifies each approved proposal (content hash, base unchanged), writes, stages,
    records the approval for the commit gate, commits with an Owner-Approved trailer
```

### The proposal record

`.git/charter/proposals/<id>.json` lives under `.git/charter/`, next to the session and gate logs, so it is never
committed. Fields:
- `id`, `created`, `session`;
- `path`;
- `base_blob`: the `git hash-object` of the file when proposed, empty for a new file;
- `content`: the full proposed text;
- `sha256` of `content`;
- `why`;
- `unblocks`: tasket ids;
- `reasons`: the `owner_only_changes` output that made it an owner act.

A proposal whose `base_blob` no longer matches the file is **stale** and is never applied.

### The page

`charter inbox --slate` writes a Slate spec: one decision per open proposal, and a
first screen that lists the Part 1 tightenings applied since the last inbox. Each decision has:
- **essence:** the `why`;
- **what is blocked:** the `unblocks` list;
- **the change:** the unified diff;
- **options:**
  - `A` Approve;
  - `R` Reject;
  - `M` Amend (the note is required, and the agent re-proposes).

The proposal's `sha256` is written into the spec's option (`options[A].approves`). The relay therefore
records the hash that was on the screen, not a hash the agent chooses later.

Slate renders `background` and option `detail` as markdown-lite with inline `` `code` `` only
(`PageContract.md` § Markdown-lite in the Slate skill). A diff needs a fenced, monospaced block. That is a
Slate change, tasket `-2004`.

### Apply, and how the commit gate accepts it

`charter apply <page>` proceeds as follows:
1. It reads the answer record. The relay writes it to `~/.crossroads/answers/<page-file>.json`, in a
   `0700` directory (`CrossroadsAnswer.py:488-491` in the Crossroads skill).
2. It applies each proposal whose answer is `A` and whose `approves` hash equals the proposal's `sha256`
   **and** the file's current `base_blob`.
3. It writes the file and stages it.
4. It appends `{path, blob}` to `.git/charter/approved.jsonl`.
5. It commits by pathspec, with the trailer `Owner-Approved: <page> <sha256>`.

`check_owner_only_staged` (`package/.charter/checks.py:1385`) gains one rule: a staged owner-only
path whose staged blob is listed in `approved.jsonl` is not refused. CI's author check
(`check_owner_commits`, `package/.charter/checks.py:1396`) keeps working unchanged. On a solo machine the agent commits as the owner's
git identity, so the trailer is the audit trail, not the gate.

### What this trusts, said plainly

The agent, the relay and the Telegram-authenticated browser all end at the same Unix user, `gui`. An agent
that set out to forge an approval could write the answer record itself. So this design protects against
**drift and accidents**, the threat the gates already assume. It does not stop an agent working against the
owner: the Edit gate can already be bypassed through Bash, and nothing here makes that worse. A signed
approval (a key readable only by a separate system user) was considered and declined on 2026-09-29. It
stays the upgrade path if the threat model changes.

The relay does not record who answered today: `CrossroadsAnswer.py` reads only `Content-Length` from the
request headers (`:520`). Tasket `-2004` adds `answered_by` from the auth gate's user header, so each approval
names a Telegram identity.

## What the owner still does by hand

Nothing that needs typing. The owner opens one page, taps, and presses Send. Four kinds of change stay owner
acts: rails, scope, config, and loosening a gate. What changes is the effort per ask, not whose ask it is.

## Tasket map

| Tasket | What | Depends on |
|---|---|---|
| `-2000` | Part 1: tightenings are free, with a warning | none |
| `-2001` | `charter propose` and the proposal store; the override message names it | none |
| `-2002` | `charter inbox` (text) and `charter inbox --slate` (spec) | `-2001` |
| `-2003` | `charter apply` and the commit-gate rule for approved blobs | `-2001`, `-2004` |
| `-2004` | Slate and relay: fenced diff blocks, an `approves` hash on options, `answered_by` in the record | none (personal-layer skills) |
| `-2005` | Release 0.4.7 (or 0.5.0): version bump, docs, upgrade note | `-2000` … `-2004` |
| `-2006` | Trial on tele-claude: route its two pending owner acts through the inbox and count the owner's actions | `-2005` |

<!-- charter: /opinion -->
