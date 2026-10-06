# Owner's acts

<!--
Written by the chain session that waits on the owner, next to its handoff (chain rules, section 5). The owner runs
every act with one command, `python3 .charter/bin/charter owner run`, without pasting anything, and most often without
reading the commands: write each one so that it is safe to run as written, from the repository root, in zsh or sh.
`/resume-chain ok` then closes exactly the lines whose acts passed. Before the owner sees it, Codex reviews this file
read-only; an act it judges you could do yourself comes back to you.

One `## <n>. <title>` per act, numbered from 1 in the order the owner does them. Under the title, these fields, one
per line, then at most one fenced block:

  closes:         the `— owner:` lines the act closes: `<unit> AC-n`, several separated by commas (`u1 AC-2, AC-3`);
                  `-` for an act that only prepares another, which then names its unit in its title or `do:`
  do:             for an act that is not a command (a setting, a password manager, a choice): how it is done; for an
                  interactive command, the answers to give
  check:          for such an act, a one-line command that exits 0 once it is done (`fdesetup status | grep -q On`)
  expect-exit:    for a command: 0 (the default), nonzero, or exit codes separated by commas
  expect-output:  for a command: a regular expression its output must contain
  stop-on-fail:   yes when the acts after it make no sense if it fails (an install the checks rely on)
  later:          yes for an act that does not block the road now (a bucket to create "when ready"): never run,
                  never closed by `ok`, listed for the owner
  owner-because:  why the act is the owner's, when the review said you could do it yourself
  read:           the one place the owner should read before running it
  timeout:        seconds after which the command is stopped (none by default; an install may take minutes)

A command runs with zsh (`zsh -c`) at the repository root, with the owner's terminal, so `sudo` asks for Touch ID or the
password there. Each act is paste-ready (chain rules, section 5): no `<placeholder>` (`chain next` refuses one; read a
value with `read "b?R2 bucket name: "`, since owner.md is not edited after the hand-over), no secret on a command line,
an interactive command (a wizard) as an act of its own with the answers under `do:`, which the owner sees before it runs,
and the number of Touch ID prompts in its title. One command per act: join the steps of
one act with `&&`, and split acts that close different lines.

Example, from a real wait:

## 1. Reinstall the confidential zone (install.sh section 7 is new)
closes: 20261004-0040-confidential-backup-doctor AC-2
stop-on-fail: yes
read: ops/confidential/install.sh section 7 (the nightly LaunchDaemon)

```sh
sudo ops/confidential/install.sh
```

## 2. The drop box takes a file in
closes: 20261004-0030-confidential-inputs AC-3
expect-output: inbox: add inbox/conf-fixture

```sh
f=$(mktemp /tmp/conf-fixture.XXXX) && echo synthetic > "$f" && conf add --move "$f" && sleep 15 && conf git log -1 --format=%s
```

## 3. Turn on FileVault
closes: 20261004-0010-confidential-role-hermes AC-8
do: System Settings > Privacy & Security > FileVault; put the recovery key in your password manager.
check: fdesetup status | grep -q 'FileVault is On'

## 4. An R2 bucket and a token, for the off-site backup
later: yes
closes: 20261004-0040-confidential-backup-doctor AC-1, AC-5
do: An EU-jurisdiction R2 bucket and a token scoped to it. The session after configures rclone with them.
-->
