# CI size gate blocks files created before the install when the first push carries pre-install history

- Seen: 2026-09-27, hermes-custom at `4a4526a`, charter 0.4.6
- Status: open

## What happened

hermes-custom's local `main` was 30 commits ahead of `origin/main` (`9fbd8e1`) when charter was installed on top of it. The install, the owner config and two agent commits were fast-forwarded into `main`, and all 34 commits were pushed together. The `charter` workflow's `gates` job failed:

```
charter/size block [skills/_shared/property-scan/scripts/normalize.py]: skills/_shared/property-scan/scripts/normalize.py is 1166 lines, over the 800-line limit; the file is frozen for growth
charter/size block [skills/_shared/property-scan/scripts/report.py]: ... is 853 lines ...
charter/size block [skills/geo-property-scan/scripts/ingest_geojson.py]: ... is 823 lines ...
charter/size block [skills/geo-property-scan/scripts/map_panel.py]: ... is 910 lines ...
charter check: 4 blocking, 3 warning(s) [tree, track prototype, opt-ins: none]
```

(`gh run view <id> --log-failed`; the job ran `python3 .charter/bin/charter check --all --ci --base 9fbd8e1…` with `BASE` from `github.event.before`.)

None of the four files existed at `9fbd8e1`: they were created in the 30 pre-install commits. No charter commit touched them; each is the same size at `d4fdef9` (the commit the install branched from) and at `4a4526a`. The install-time survey had already listed them as frozen, and `charter check --all` on the branch before the push reported 0 blocking.

Expected: the first CI run judges only what happened since the install. A file that was already over the limit when charter arrived is frozen for growth, not blocked for existing.

## Reproduce

1. A repository whose local `main` is ahead of `origin/main` by commits that add a file over 800 lines.
2. `charter-pkg install` on a branch from local `main`, owner commit, fast-forward into `main`.
3. `git push origin main`. CI's `BASE` is the old remote head, which predates both the file and the install.

## Where

- `package/.github/workflows/charter.yml:17-18`: `BASE` is `pull_request.base.sha || github.event.before`.
- `package/.charter/bin/charter:122-133`: for each changed path, `old_lines = 0` when `prev is None`, that is, when the file is absent at the base. A new file over the limit therefore always "grows" from 0.
- `package/.charter/checks.py:260` (`check_size`): blocks when `new_lines > limit and new_lines > old_lines`.
- For comparison, `check_owner_commits` (`package/.charter/checks.py:754`) already special-cases a base without a config ("Only a base without a config (the install) falls back to the config under review").

## Workaround

None needed in hermes-custom: the next push's base is `4a4526a`, which contains the install, so the four files are compared against themselves. The red run stays red; re-running it uses the same base. A project that must have a green first run can push the pre-install history before the install commit.

## Suggested fix

When the base has no `charter/VERSION`, move the effective base for the size gate (and probably every gate that compares against the base) to the install commit: the first commit in `base..HEAD` that adds `charter/VERSION`. The Migrate workflow could also say to push the main line before installing when it is ahead of origin; the survey already measures that (`main against origin/main`).
