# Charter 0.4.19: prepared release and owner handoff

The release is prepared on `owner-json-content-payload-20261024`, implementation/release-preparation commit **`8ffb6a774af6c09717b0ea0d669cb18d6a2cb404`**. Gui approved it through `oa-6g4k`, answer `release`, owner-dashboard at 2026-10-24T13:47:40+00:00 (`$ /home/gui/Projects/tele-claude/scripts/owner show oa-6g4k`).

## Delivered changes

Per-item `contract: 1`, nullable `why` and `because`, and ruling consequences let consumers render authored meaning without parsing source headings. Decisions read Recommendation and Because; changes read Recommendation and Why it is outside the scope. First paragraphs stop at 500 characters, preferring a sentence boundary. Existing fields, ruling argv, top-level schema and text queue stay compatible (`package/.charter/owner.py`, `tests/test_owner_0_4_8.py`, commit `8ffb6a774af6c09717b0ea0d669cb18d6a2cb404`).

Version 0.4.19, required release metadata, upgrade note and generated maps are prepared. No new command, gate or owner act enters the installed package (`AGENTS.md`, `$ python3 docs/assets/maps/build.py`, commit `8ffb6a774af6c09717b0ea0d669cb18d6a2cb404`). The original patch at `docs/proposals/owner-json-content-contract.patch` is retained as a review artifact against 1100e7d; **do not reapply it**, because its code is already in this branch (`$ git show --stat 8ffb6a774af6c09717b0ea0d669cb18d6a2cb404`).

## Verification

- The exact 32-module command in `AGENTS.md`, from `tests/` with TMPDIR=/tmp/ under `scripts/run-bounded.sh -m 4G`, ran **709 tests in 1440.184 s**: 707 passed and two failed (`/tmp/charter-0.4.19-full-tests.log`).
- The zsh-only test failed because `/bin/zsh` is absent; unchanged 0.4.18 reproduces it. Production already supports `/bin/sh`. Guarded only that zsh-specific test (`tests/test_owner_acts_0_4_11.py`, `package/.charter/owner_acts.py`, `/tmp/charter-zsh-baseline.log`).
- The machine-hook fixture pinned 0.4.18 as current. It now reads `package/VERSION`, preserving the current-versus-outdated assertions across releases (`tests/test_machine_0_4_18.py`).
- Affected-module reruns: `$ TMPDIR=/tmp/ python3 -B -m unittest test_owner_acts_0_4_11`: **29 tests OK, one zsh-only skip**, 72.542 s. `$ TMPDIR=/tmp/ python3 -B -m unittest test_machine_0_4_18`: **21 tests OK**, 33.877 s. Both bounded at 4G. The other 707 passing cases and package code were unchanged; the full command was not repeated after these fixture-only fixes (`/tmp/charter-0.4.19-owner-acts-recheck.log`, `/tmp/charter-0.4.19-machine-recheck.log`).
- `$ bash -n docs/proposals/publish-owner-json-review.sh` checks the owner payload's syntax; `$ docs/proposals/publish-owner-json-review.sh --check` checks the prepared branch and immutable release ancestry without publishing.

## Present owner action

The interactive payload `docs/proposals/publish-owner-json-review.sh` validates this branch, version, origin and unchanged committed release content. It shows the exact head, asks for confirmation, then pushes that immutable head and opens the release PR with committed PR text. Publication reads immutable Git objects, so concurrent tracked and untracked working edits are preserved. It performs no merge, tag or installed upgrade (`docs/proposals/publish-owner-json-review.sh`).

## After publication: Gui's release and upgrade

1. Review the PR, including the transparent test record above, and merge it when ready. Review/merge remains the owner's call (`AGENTS.md`, `docs/install.md`).
2. Create/push the release tag and push main through Gui's release process. No tag or remote write was made during preparation (`$ git tag --list`, `$ git status --short`).
3. Upgrade tele-claude through `docs/install.md` § Upgrade, using a clean exclusive tree or separate worktree. Its live shared checkout has other sessions' work, so that precondition must be respected (`docs/install.md` Step 0).
4. Verify installed `charter owner --json` emits contract 1, why, because and consequences; the desk already consumes them. Keep the compatibility fallback until every watched project carries the protocol (tele-claude `docs/OWNER_DESK_DECISION_CARDS.md` §3.1).
