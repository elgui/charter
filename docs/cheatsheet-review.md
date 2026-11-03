# Desk sheet maintenance

The reference is two A4 landscape pages with four SVG views. Editable content, vector labels and styles live in `docs/cheatsheet.html`; PDF and standalone SVGs are generated from that source. This refresh describes Charter 0.4.22, its Owner Desk acceptance contract and the separate, unreleased spec-design recipe, reviewed on 2026-11-03 (`package/VERSION`, `docs/design/owner-acceptance.md`, `docs/assets/cheatsheet/sources.json`).

Page one focuses on daily use and the division between the project record, the workspace and the Owner Desk. Page two follows an approval across the boundary, distinguishes the four update layers and supplies maintenance/recovery prompts (`docs/cheatsheet.html`).

## Evidence by workflow

| Sheet content | Reviewed sources |
|---|---|
| Spec design (explicitly unreleased), source comparison, independent review and chain limit | `$ git show charter-spec-draft:package/.claude/skills/charter-spec/SKILL.md`, steps 2–10 and § Does this rail need it?; `$ git show charter-spec-draft:package/charter/templates/spec.md` |
| Unit loop, perimeter, protected criteria and delegation | `package/.claude/rules/charter.md`; `docs/design/owner-delegate.md` |
| AC identity, source path and completion commit | `package/.charter/owner.py`, functions `owner_lines`, `acceptance_contract`, `accept`; `docs/design/owner-acceptance.md` |
| Read-only project commands | `package/.charter/bin/charter`, functions `cmd_next`, `cmd_owner`, `cmd_unit`, `cmd_config` |
| Taskets versus asks; housekeeping | Tele-Claude [TASKETS.md](https://github.com/elgui/tele-claude/blob/main/docs/TASKETS.md), section Taskets and Owner Desk |
| Desk entry points, types and owner terminal | Tele-Claude [OWNER_DESK.md](https://github.com/elgui/tele-claude/blob/main/docs/OWNER_DESK.md), sections 2, 3, 6, 8 and 10; `services/owner_desk/cli.py` |
| Acceptance confirmation, failure, old installations | `docs/design/owner-acceptance.md`; Tele-Claude `docs/OWNER_DESK_ACCEPTANCE.md`; `services/owner_desk/runner.py`, function `check`; `services/owner_desk/detectors/charter.py`, function `item_to_ask` |
| Separate evidence, review, running code and observation | `docs/verification.md`; Tele-Claude `services/step_close.py` |
| Package/project/machine updates | `docs/install.md` § Upgrade; `bin/charter-pkg`; `machine/README.md` |
| Package chain resume | `docs/design/continuous-chain.md`; project rules |

The SVGs replace prose with four views: responsibilities, work loop, approval path and maintenance layers. Each exports selectable text and has a readable HTML alternative at narrow widths (`docs/cheatsheet.html`, `docs/assets/cheatsheet/build.cjs`).

## Refresh and rebuild

Run from this repository's root. Set `TC` to the Tele-Claude checkout being reviewed. Source hashes flag drift, including the two draft files read with `git show charter-spec-draft:<path>`; a matching hash does not establish explanatory correctness (`docs/assets/cheatsheet/check_sources.py`). The draft ref is currently local and unpublished. A clone without it reports those two sources missing; it cannot establish their freshness until the reviewed ref is available. Do not refresh their hashes to silence that result (`$ git branch -r --contains charter-spec-draft`; `docs/assets/cheatsheet/sources.json`).

```sh
python3 docs/assets/cheatsheet/check_sources.py --tele-claude "$TC"
node docs/assets/cheatsheet/build.cjs
pdfinfo docs/cheatsheet.pdf
pdftotext -layout docs/cheatsheet.pdf /tmp/charter-sheet.txt
sha256sum docs/cheatsheet.html docs/cheatsheet.pdf docs/assets/cheatsheet/*.svg
```

The renderer needs Playwright or playwright-core and Chromium. If normal Node resolution does not find them, set `PLAYWRIGHT_MODULE` to the module directory and `CHROMIUM_PATH` to the executable. `PREVIEW_DIR=/tmp/charter-sheet-preview` saves desktop and phone screenshots. No project dependency is installed by this workflow (`docs/assets/cheatsheet/build.cjs`).

When the freshness check names a change, review the affected claim against its implementation, update the HTML and review date/version, then replace the corresponding source hashes/revisions. Regenerate all formats together. Record output hashes with the same sha256sum command above into `docs/assets/cheatsheet/outputs.sha256`; that file hashes the outputs, not itself (`docs/assets/cheatsheet/sources.json`, renderer).

The HTML uses neighboring documentation links. The exported PDF's upgrade link targets the canonical repository guide; local maintenance links remain plain text to avoid exporting private worktree paths (`docs/assets/cheatsheet/build.cjs`).

## Validation and delivery record

- Chromium print validation: exactly two page containers fit; 1200px desktop and 390px phone widths have no horizontal overflow (`$ node docs/assets/cheatsheet/build.cjs`, with module/browser overrides).
- PDF metadata: two pages, A4 landscape (841.92 × 594.96 points). Text extraction includes both footers, SVG labels and readable punctuation (`$ pdfinfo docs/cheatsheet.pdf`; `$ pdftotext -layout docs/cheatsheet.pdf /tmp/charter-landscape-text.txt`).
- Both actual PDF pages and desktop/phone HTML renders were visually inspected. Four standalone SVGs parse as XML and retain their viewBox/text labels; output hashes are recorded (`docs/assets/cheatsheet/outputs.sha256`).
- The reference describes the supported flow, not a claim that every project or deployed service already runs it. Owner Desk receipt oa-q76v records integration of Charter and Tele-Claude on local main; installed project upgrades and backend/dashboard deployment remain separate (`docs/design/owner-acceptance.md`; Tele-Claude `docs/OWNER_DESK_ACCEPTANCE.md`).

## Spec-design refresh, 3 November 2026

The package stamp now reads 0.4.22. The daily preparation prompt covers a spec only where shared choices or binding text justify it. The sheet names the draft branch and exact skill path, says that 0.4.22 does not install it, and limits its execution paths to manual sessions and Run All. Its checkpoints do not stop the package chain (`package/VERSION`; `$ git show charter-spec-draft:package/.claude/skills/charter-spec/SKILL.md`, § Does this rail need it?).

The release remains subject to the approved evidence rule, rather than to successful regression tests alone (branch `charter-spec-draft`, `docs/proposals/2026-11-spec-step.md`, § How we would know; Owner Desk `oa-cr4y`). The earlier proposal is a dated record; its description of the old Desk Pass behavior predates the acceptance writeback now described in this sheet (`docs/design/owner-acceptance.md`).

Reviewed source drift in the Owner Desk documentation and CLI concerns current ask recipients and the new transfer/leave verbs. The sheet's `mine` command still reads the current session's asks; the acceptance flow and the other listed commands are unchanged (`$ git -C <tele-claude> diff <previous-reviewed-commit> HEAD -- docs/OWNER_DESK.md services/owner_desk/cli.py`). Source hashes were refreshed after that comparison.

Regeneration passed the renderer's two-page print bounds and both viewport widths. Both actual PDF pages and the desktop and phone renders were inspected; the PDF has two selectable-text A4 landscape pages (`$ node docs/assets/cheatsheet/build.cjs`; `$ pdfinfo docs/cheatsheet.pdf`; `$ pdftotext -layout docs/cheatsheet.pdf <output>`). Output hashes are recorded alongside the source hashes.
