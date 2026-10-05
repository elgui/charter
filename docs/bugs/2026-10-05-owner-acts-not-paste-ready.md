# Owner acts are not paste-ready: labels instead of commands, and commands that do not parse

- Seen: 2026-10-05, hermes-custom at 96b3a5a (chain 20261005-183724, session 2), charter 0.4.9
- Status: fixed in f8d72ef and 4045b23 (charter 0.4.10). Tests: `tests/test_chain_wait.py` class `PasteReady` (A3 refusal and redirections, A4 `chain next` output, A5 `charter owner` lines, A6 notification, the standard in the rules and the template)

## What happened

1. At a wait, the session's closing message summarised six acts as labels ("Run the `conf add` round trip") and pointed
   at `.git/charter/chain/<id>/s02/handoff.md`, which the owner does not read. The owner asked twice how to run an act.
   `python3 .charter/bin/charter owner` had the commands all along; nothing in the terminal named it.
2. A `## Wait` act read: `sudo …/rclone config …`, then `echo <bucket> | sudo tee /opt/confidential/etc/r2-bucket`.
   Pasted as a block, zsh printed `zsh: parse error near '|'`: `<bucket>` is a redirection. The block also put an
   interactive wizard together with other commands.
3. `charter chain next` at a wait prints only "session 2 closed (wait); … waits on the owner, who is told …"
   (/Users/gui/dev/charter/package/.charter/chain.py:1201). `notify` cuts its text at 400 characters
   (/Users/gui/dev/charter/package/.charter/chain.py:674).

## The standard (use the same wording wherever it appears below)

An owner act is paste-ready when:
- each command runs as pasted in zsh, in its own fenced `sh` block (or after `run:` in a one-line act);
- it holds no `<placeholder>`: a value the owner supplies is read with a prompt (`read "b?R2 bucket name: "`) or set on
  a first line to edit (`BUCKET=my-bucket  # edit`);
- an interactive command (wizard, editor, TUI) stands alone, with the answers to give listed under it;
- it says what success prints (or its exit code) and how many Touch ID / password prompts to expect;
- no secret is typed on a command line (shell history, `ps`): a secret goes through an interactive prompt.

## Changes

### A. charter package (with tests; bump the version and note it in docs/package.md)

1. `package/.charter/chain-rules.md` §5 step 3: "how the owner does it" becomes "how the owner does it: a paste-ready
   command (the standard, in short) or the exact path of the setting". §4: add "At a wait, the closing message lists
   every `## Wait` act verbatim, each command in its own fenced block, then the `/resume-chain ok|skip <note>` line and
   `python3 .charter/bin/charter owner`; never a summary of the acts."
2. `package/charter/templates/handoff.md` `## Wait`: show the line format
   `- <what> — run: \`<command>\` — expect: <what success prints> — closes <unit-id> AC-n`, with one example that has a
   command and one that has a settings path.
3. `check_handoff` (`package/.charter/chain.py:351`): refuse a `## Wait` line whose backticked span matches
   `<[A-Za-z][A-Za-z0-9_-]*>`, naming the fix ("a `<bucket>` placeholder is a shell redirection: prompt with `read` or
   set it on its own line"). `cmd < file` and heredocs `<<EOF` must still pass.
4. `_hand_over` (`package/.charter/chain.py:1201`): on wait, print each `## Wait` line verbatim, then the `/resume-chain`
   line and "listed again by `python3 .charter/bin/charter owner`". It is the session's last tool output, so the
   closing message can copy it.
5. `charter owner`: under a waiting chain, print each act's `run:` command alone on its own line (no `- ` or `ask:`
   prefix, no surrounding prose) so a triple-click copies it whole.
6. `notify` (`package/.charter/chain.py:674`): at a wait, say "<n> acts wait: run `python3 .charter/bin/charter owner`
   in <project>" instead of a 400-character cut of the reason.
7. Optional, as a gate: the Stop hook, for the session that just closed with `status: wait`, blocks once a final
   message that does not contain each `run:` command verbatim (same mechanism as the anchor check).

### B. Outside charter: `~/.claude-lean/CLAUDE.md`, under "Working with Gui"

Add:

- When I have to run something myself, hand it over paste-ready in the message itself, never only in a file I don't
  read: one fenced block per command that runs as pasted in zsh (no `<placeholder>`: prompt with `read "x?…"` or a
  first line to edit), an interactive command alone with the answers listed, and what success prints.

## Acceptance

- New tests in `tests/test_chain_wait.py`, run with the repo's runner (likely `python3 -m unittest tests.test_chain_wait`), pin:
  (3) a handoff whose `## Wait` holds `` `echo <bucket> | sudo tee x` `` is refused by `charter chain next`, and one
  with `` `sort < in.txt` `` is accepted; (4) on wait, `chain next`'s stdout contains each act's command verbatim;
  (5) `charter owner` prints each `run:` command on a line of its own.
- `grep -n 'paste-ready' package/.charter/chain-rules.md package/charter/templates/handoff.md` finds the standard in both.
- B: `grep -n 'paste-ready' ~/.claude-lean/CLAUDE.md` finds the bullet.

## Fix (2026-10-05)

- A1–A6 as specified. The `charter owner --json` items gain a `run` list (A5); `charter next` prints the `run:` lines bare as well.
- A7 deferred: the Stop hook would have to read the final assistant message from the transcript, a format charter does not
  pin anywhere else, and A4 already makes the right closing message a copy of `chain next`'s last output, which the rules
  (§ 4) require. Revisit if a wait trial shows a session still summarising the acts.
- B applied to `~/.claude-lean/CLAUDE.md`, outside this repository.
- Not covered: a command that holds a backtick must be written in a double-backtick span (``` `` cmd `x` `` ```); an act
  without `run:` (a settings path) gets no bare command line, by design.
