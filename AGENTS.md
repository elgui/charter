# Agents in this repository

This repository is the source of charter: the package copied into projects (`package/`), the personal layer for this machine (`personal/`), and the tooling around them (`bin/`, `tests/`). It does not run charter itself. What charter is: `README.md`.

## Installing charter on a project

Follow `docs/install.md`, step by step. It is the only install, setup and upgrade procedure. The install and upgrade commits touch owner-only paths, so you stage them and the owner commits them. Never set `CHARTER_OWNER` and never pass `--no-verify`.

## Working on charter itself

- **Tests**, about 15 minutes (the chain tests launch sessions and wait on them; run them in the background), from `tests/`, with `TMPDIR` set to a resolved path (`TMPDIR=$(cd "${TMPDIR:-/tmp}" && pwd -P)/`: two tests fail when it goes through `/var`):

  ```
  python3 -B -m unittest test_gates test_installer test_review_regressions test_harmonization_regressions test_batch1_regressions test_migration test_size_exceptions test_rails test_review_20260923 test_probe_at_base test_review_required test_config_0_4_3 test_next_0_4_4 test_handover_0_4_5 test_release_commit_0_4_6 test_chain_0_4_7 test_groups_0_4_8 test_chain_reliability test_gate_noise_0_4_7 test_owner_0_4_8 test_chain_wait test_owner_gate test_owner_acts_0_4_11 test_owner_commit_0_4_12 test_json_verbs_0_4_13 test_delegate_0_4_14 test_delegate_watcher
  ```

  Add each new test module to this list. Run without `-q` and look for `^FAIL:` or `^ERROR:`, so that a failure block is kept. One test is known to be flaky: `docs/review/findings-2026-09-23.md:37`.
- **A change to `package/` is a release.** The installer copies it into projects and records the hash of each file it owns in the project's manifest (`OWNED` in `bin/charter-pkg`). Bump the version in `package/VERSION`, in `package/charter/config.json` and in the default config in `package/.charter/lib.py`. Update the version lines in `docs/method.md`, `docs/package.md` and `docs/method-visual.html`, and add an upgrade note to `docs/package.md` § Versioning and upgrade. Projects pick the release up through `docs/install.md` § Upgrade.
- **`personal/` is live.** On this machine, `~/.claude` links into this checkout (`personal/README.md`, option B), so an edit there, or a branch switch, changes the running skill and hook at once.
- **History is not rewritten.** `docs/report-2026-09-11.md`, `docs/session-log.md`, `docs/briefs/`, `docs/review/` and `docs/trials/` are dated records. Add new records; do not edit old ones.
- **Claims carry sources.** In reference docs, cite a `path:line`, a commit, a `$ command` or a URL. Facts about external tools, such as Claude Code hooks and GitHub, get a link to the vendor's page. `python3 package/.charter/bin/charter anchors <file>` checks a document.
- Commit on a branch, never on `main`. Pushing and merging are the owner's call (`package/.claude/rules/charter.md:44`).
