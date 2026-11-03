# Owner acceptance integration validation — 2026-11-03

Charter 0.4.21 supplies a bound owner completion contract and verb; the corresponding Tele-Claude branch turns confirmation into that single Charter commit. Contract and limits are in `docs/design/owner-acceptance.md`; implementation tests are `tests/test_owner_acceptance.py` and Tele-Claude `tests/test_owner_acceptance.py`.

## Results

- At 2026-11-03 10:47:47 UTC, `$ tail -8 /tmp/charter-acceptance-full.log` reported the AGENTS.md suite: `Ran 724 tests in 924.910s`, `OK (skipped=1)`. It ran from `tests/`, with resolved TMPDIR, without `-q`, and retained full stdout/stderr. The launch command used the module list in `AGENTS.md`; there are no FAIL/ERROR blocks.
- `$ python3 -B -m unittest test_owner_acceptance test_owner_0_4_8 test_owner_gate test_json_verbs_0_4_13` — 81 tests, OK (initial integration and queue compatibility).
- `$ python3 -B -m unittest test_owner_acceptance test_owner_gate` — 35 tests, OK, after the final terminal/duplicate-unit checks and command-aware acceptance guard were added. Those final tests include denial of direct/nested owner acceptance commands and admission of quoted documentation mentions.
- Tele-Claude `$ CHARTER_PACKAGE_SOURCE=<candidate package> scripts/run-bounded.sh <deploy venv>/bin/python -m pytest -q tests/test_owner_acceptance.py tests/test_owner_desk_core.py tests/test_owner_desk_charter.py tests/test_owner_desk_human_checks.py tests/test_owner_desk_api.py tests/test_owner_desk_cli.py` — 306 passed. A later 60-test run of acceptance, Charter mapping and failure notices passed after the legacy guidance change and new HTTP test. The test using actual Charter code closes AC-10/AC-11 in separate receipt-bearing commits (`Tele-Claude tests/test_owner_acceptance.py`).
- Tele-Claude `$ scripts/run-bounded.sh python3 .charter/bin/charter probe 20261103-1030-owner-acceptance-writeback` with CHARTER_PACKAGE_SOURCE supplied — all three acceptance probes exit 0.
- Tele-Claude dashboard: 65 selected Owner Desk tests pass; `$ ./node_modules/.bin/tsc --noEmit` passes. The confirmation test changes the displayed card after selection and verifies that the original selected hash is submitted (`dashboard/src/components/OwnerDesk/CheckInstructions.vitest.tsx`).
- Tele-Claude `$ scripts/staging-smoke.sh HEAD` — exit 0 on implementation commit `3777341e`; the final tasket-only receipt commit is `40f0a18b`.
- Tele-Claude staged commit gates — zero blocking, three existing warnings. `$ python3 .charter/bin/charter check --all --base HEAD --no-probe` has an unrelated baseline block: decision sanitize-commits-ended-sessions-work's grep matches `rep["checkout"]` in unchanged `scripts/sanitize.py:640`. That line is present in baseline `5a8e20d0`; neither its code nor the decision was altered to silence it.
- `$ python3 package/.charter/bin/charter anchors docs/design/owner-acceptance.md` — eight claim lines anchored, zero unresolved. Maps regenerated with `$ python3 docs/assets/maps/build.py`.

## Delivery limits

No real owner acceptance was performed; all writeback tests use temporary repositories and stores. No main branch was merged, no remote was pushed, no service was restarted, and no installed project was upgraded. Tele-Claude was observed on installed Charter 0.4.19 at 2026-11-03 10:42:15 UTC via `$ python3 bin/charter-pkg status /home/gui/Projects/tele-claude`; the isolated candidate upgrade dry run reports nine changed files. Integration, deployment and installed upgrades remain separate owner/delivery steps (`docs/install.md` § Upgrade; Tele-Claude `docs/OWNER_DESK_ACCEPTANCE.md`).
