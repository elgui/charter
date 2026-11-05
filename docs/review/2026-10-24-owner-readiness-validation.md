# Proposal readiness candidate validation, 2026-10-24

The 0.4.19 candidate adds nullable per-item `readiness` to the owner JSON protocol. Proposed decisions and changes stay in the queue while untracked, staged-only or modified; the ruling verbs use the same prerequisite. The unattended check disables Git filters/fsmonitor and optional index refresh (`package/.charter/owner.py`, `tests/test_owner_0_4_8.py`). The implementation commit is `736cabd`.

Tele-Claude consumes the field and supplies a compatibility check for installed older charters, so its readiness UI and refusal notices can ship independently of a package upgrade (tele-claude commit `c21dba8ed5168b875cb3f146a45f1047a5481138`, `services/owner_desk/readiness.py`). Its final backend run passed 289 tests; its UI suite passed 116 tests, its production build passed, and the isolated boot/GET smoke exited 0 (operator report: `/tmp/owner-desk-readiness-complete.log`, `/tmp/owner-desk-readiness-ui-all.log`, `/tmp/owner-desk-readiness-build.log`, `/tmp/owner-desk-readiness-smoke.log`).

## Package verification

- `$ TMPDIR=/tmp/ python3 -B -m unittest test_owner_0_4_8 test_json_verbs_0_4_13`: final focused run **45 passed**, 128.824 s. It includes queue/verb parity, stable draft visibility, committed readiness and inert Git drivers (`/tmp/charter-readiness-final-focused.log`).
- `$ python3 docs/assets/maps/build.py`: regenerated the versioned text, HTML and five SVG maps. `$ python3 package/.charter/bin/charter anchors docs/package.md`: 0 unanchored, 0 unresolved anchors.
- The complete command from `AGENTS.md`, with resolved `TMPDIR=/tmp/` and `scripts/run-bounded.sh -m 4G`, ran **707 tests in 1628.566 s** and failed three. The captured failure blocks remain in `/tmp/charter-readiness-full.log` (operator report).

The full run is not reported as green. Its failures were (`/tmp/charter-readiness-full.log`):

1. `SquashedEvidence.test_synthesis_labels_a_squashed_sha_historical`: missing “historical” in the synthesis. Its isolated retry passed in 2.283 s (`/tmp/charter-readiness-squashed.log`). No production synthesis change is included for this intermittent result.
2. `Run.test_the_acts_run_in_zsh`: `/bin/sh` rejected the zsh expansion because `/bin/zsh` is absent. The implementation explicitly falls back to `/bin/sh`; the zsh-specific test now declares its optional `/bin/zsh` dependency (`package/.charter/owner_acts.py:493`, `tests/test_owner_acts_0_4_11.py`).
3. `MachineHook.test_says_when_the_checkout_is_ahead`: its “current” fixture hardcoded 0.4.18 while the package is 0.4.19. The fixture now uses `package/VERSION` (`tests/test_machine_0_4_18.py`).

The fresh affected-module run, including both fixture corrections and both historical-evidence cases, passed: **52 tests, one skip for absent `/bin/zsh`**, 131.307 s (`$ TMPDIR=/tmp/ python3 -B -m unittest test_machine_0_4_18 test_owner_acts_0_4_11 test_review_regressions.SquashedEvidence`, `/tmp/charter-readiness-affected.log`). The complete 707-test command was not repeated after these fixture-only changes; the full-run failure blocks above remain part of the validation record.

## Delivery boundary

This is a committed candidate on `owner-proposal-readiness-20261024`. Merge, tag, push and installed-project upgrades remain the owner's actions; `docs/install.md` is the only upgrade procedure. The Tele-Claude integration action is filed separately as `oa-r4ea` and verified with `$ scripts/owner show oa-r4ea` (operator report, this session).
