# Readiness integration repair, 2026-10-24

Owner action `oa-zzae` stopped at its global clean-checkout prerequisite, before its branch switch or merge. Its recorded output names concurrent changes to `docs/daily-use.md` and untracked taskets, examples and review/verification documents (`$ scripts/owner show oa-zzae`, owner-dashboard outcome 2026-10-24T15:26:06+00:00). Requiring every file in that shared checkout to be clean was too restrictive for the requested integration (inference from that output).

The source branch also advanced independently to the approved 0.4.19 content-contract release (`8ffb6a7`, `fca971b`). The old readiness candidate `9dadc09` independently named itself 0.4.19. This repair is **0.4.20**, based on `fca971b`, retaining contract 1, nullable reasons/context and ruling consequences while adding proposal readiness. It does not reapply the historical content-contract patch (`5d0274174ad677cf3bdc01d3692feb2f1b5577e1`, `package/.charter/owner.py`, `package/VERSION`).

## Integration method

The reviewed payload prepares the merge from committed objects in a clean temporary worktree. When main has an existing checkout, it fast-forwards that checkout only after the clean merge succeeds. When main has no checkout, it attaches main only to its own temporary worktree and merges there. The original checkout on another branch, its index and its tracked/untracked edits remain intact (`docs/proposals/integrate-reviewed-branch.py`, `$ python3 -B -m unittest test_owner_integration`). These use normal [Git merge](https://git-scm.com/docs/git-merge) and [Git worktree](https://git-scm.com/docs/git-worktree) operations.

An overlapping edit or conflicting concurrent target advance is refused through Git. The payload does not stash/reset session work, change global configuration, push, tag or upgrade an installed project. Its `--check` path inspects only registered worktrees and commit refs (`docs/proposals/integrate-reviewed-branch.py`, `tests/test_owner_integration.py`).

## Verification

- `$ TMPDIR=/tmp/ python3 -B -m unittest test_owner_0_4_8 test_json_verbs_0_4_13 test_installer test_machine_0_4_18`: **77 tests OK**, 139.768 s, bounded at 3G. These cover the combined content/readiness protocol, ruling guards, package installation and version behavior (`/tmp/charter-readiness-0.4.20-focused.log`).
- `$ python3 -B -m unittest test_owner_integration`: **5 tests OK**, 0.642 s. Fixtures cover a dirty main checkout, a dirty checkout on another branch, main advancing with unrelated committed work, an overlapping edit, and a read-only preflight. Staged patches, unstaged bytes and untracked files are compared before/after (`tests/test_owner_integration.py`).
- A clean verification branch over Tele-Claude main `5e7b4393` merged reviewed `c21dba8e` successfully as `627fa59548feb2cf332f69f18a3e08f9cc3db283`. `$ git diff --exit-code c21dba8e HEAD -- services/owner_desk dashboard/src/api/ownerDesk.ts dashboard/src/components/OwnerDesk tests/test_owner_desk_api.py tests/test_owner_desk_charter.py tests/test_owner_desk_readiness.py tests/test_owner_desk_failure_notices.py` exits 0 there. The live main ref was not changed (operator report, this session).
- `$ python3 docs/assets/maps/build.py` regenerated the versioned maps. `$ python3 package/.charter/bin/charter anchors docs/package.md`: 0 unanchored, 0 unresolved anchors.

The full release command from `AGENTS.md`, including `test_owner_integration`, passed: **717 tests in 1206.102 s, OK with one skip** for the optional absent `/bin/zsh`. It ran from `tests/` with resolved `TMPDIR=/tmp/`, without `-q`, under a 4G bound. No FAIL or ERROR block occurred; existing subprocess/file ResourceWarnings were retained (`/tmp/charter-readiness-0.4.20-full.log`).

## Owner handoff

Tele-Claude replacement `oa-5sos` is verified with `$ scripts/owner show oa-5sos`. It supersedes the execution method in `oa-r4ea`; both share the original implementation commit as their done condition, so normal probe refresh closes the earlier open ask after integration. The failed `oa-zzae` keeps its history; its copied payload is not rewritten. The charter replacement is filed only after the candidate's checks complete (operator report, this session).
