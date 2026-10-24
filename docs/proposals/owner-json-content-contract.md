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
