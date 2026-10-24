# Owner JSON content contract: tested release payload

The payload adds per-item `contract: 1`, nullable `why` and `because`, and ruling consequences. Decisions read the first paragraph of Recommendation and Because; change requests read Recommendation and Why it is outside the scope. Paragraphs stop at 500 characters, preferring a sentence boundary. Existing fields and argv remain intact (`docs/proposals/owner-json-content-contract.patch`).

This is an unreleased patch against `1100e7d`, prepared for tele-claude's settled Option A. It changes `package/.charter/owner.py` and `tests/test_owner_0_4_8.py` when applied; this branch itself changes neither installed tooling nor release metadata (`$ git diff --stat`, `AGENTS.md`).

Verification on an isolated clone with the patch applied: `$ TMPDIR=/tmp/ python3 -B -m unittest test_owner_0_4_8 test_json_verbs_0_4_13` from `tests/`, under tele-claude's `scripts/run-bounded.sh -m 4G`: **46 passed**, 124.034 s on 2026-10-24. Cases cover nullable/missing sections, first-paragraph boundaries, 500-character clipping, decisions, changes, rail consequences, additive shape and reporting without acting (`tests/test_owner_0_4_8.py` in the patch).

## Owner release handoff

1. Review and apply on this branch: `$ git apply --check docs/proposals/owner-json-content-contract.patch`, then `$ git apply docs/proposals/owner-json-content-contract.patch`.
2. Select the next version and follow `AGENTS.md`'s release rule: bump `package/VERSION`, `package/charter/config.json`, `package/.charter/lib.py`; update `docs/method.md`, `docs/package.md`, `docs/method-visual.html`; add the upgrade note; run `$ python3 docs/assets/maps/build.py` and the release test suite listed in `AGENTS.md`.
3. Commit the implementation and release metadata together, review/merge, tag and push as Gui chooses (`AGENTS.md`, `docs/install.md`). This payload commit is not a release or an implementation commit.
4. Upgrade projects using `docs/install.md` § Upgrade, starting with tele-claude; installed upgrades and commits remain Gui's acts under this task's explicit instructions. Verify `$ python3 .charter/bin/charter owner --json` emits `contract: 1`, `why`, `because` and consequences before treating the fleet fallback as removable (tele-claude `docs/OWNER_DESK_DECISION_CARDS.md` §3.1).

No release version, tag, push, merge or installed upgrade is performed by this payload (`$ git status --short`, `$ git diff --name-only`).


## Approved release preparation, 2026-10-24

Gui answered `oa-6g4k` with `release` from the Owner Desk at 2026-10-24T13:47:40+00:00 (verified with `$ /home/gui/Projects/tele-claude/scripts/owner show oa-6g4k`). The tested patch is now applied on this branch, with version 0.4.19, the required release metadata and generated map editions prepared. This supersedes the unreleased-patch-only state above; publication and installed upgrades remain Gui's acts (`AGENTS.md`, `docs/install.md`).

The release extends owner JSON without changing ruling argv, gates, the top-level schema or the text queue (`package/.charter/owner.py`, `tests/test_owner_0_4_8.py`). The patch file remains the original review artifact; do not reapply it after checking out the prepared release commit (`$ git diff --stat`).

The full release command exposed an existing environment assumption: `test_owner_acts_0_4_11.Run.test_the_acts_run_in_zsh` expects zsh syntax even on a host without `/bin/zsh`, where production deliberately falls back to `/bin/sh`. The same test fails on the unchanged 0.4.18 baseline (`$ TMPDIR=/tmp/ python3 -B -m unittest test_owner_acts_0_4_11.Run.test_the_acts_run_in_zsh`, `/tmp/charter-zsh-baseline.log`). Its guard now skips only that zsh-specific case when `/bin/zsh` is absent; production shell behavior is unchanged (`tests/test_owner_acts_0_4_11.py`, `package/.charter/owner_acts.py`).

The full command ran **709 tests in 1440.184 s** with two failures: the baseline zsh assumption above, and a machine-hook fixture that hard-coded 0.4.18 as the current version. That fixture now uses `package/VERSION`, preserving its current-versus-outdated assertions for every release (`tests/test_machine_0_4_18.py`). The other 707 cases passed; package implementation did not change during triage. The guarded owner-acts module rerun is **29 tests OK, one zsh-only skip**, 72.542 s (`$ TMPDIR=/tmp/ python3 -B -m unittest test_owner_acts_0_4_11`). Full-suite output is `/tmp/charter-0.4.19-full-tests.log`; affected-module reruns below record the final test fixes without repeating the other passing cases.

Final affected-module results: `$ TMPDIR=/tmp/ python3 -B -m unittest test_owner_acts_0_4_11` ran **29 tests, OK (skipped=1)** in 72.542 s; `$ TMPDIR=/tmp/ python3 -B -m unittest test_machine_0_4_18` ran **21 tests, OK** in 33.877 s. Both used the 4G wrapper. These reruns validate the only two test changes after the 709-case run; the other 707 passing cases and the package code were not changed. The full 709-case command was not repeated after those fixture-only corrections; its original failure output remains available for review (`/tmp/charter-0.4.19-full-tests.log`, `/tmp/charter-0.4.19-owner-acts-recheck.log`, `/tmp/charter-0.4.19-machine-recheck.log`).
